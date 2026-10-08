from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .models import (
    Attempt,
    GameSession,
    LeaderboardEntry,
    PuzzleInstance,
    Registration,
    RoundState,
)

from .permissions import IsGameSessionAuthenticated

from .serializers import (
    GameSessionStatusSerializer,
    PublicPuzzleSerializer,
    RegistrationSerializer,
    GoogleAuthSerializer,
    RoundStateSerializer,
    Stage1SubmissionSerializer,
    Stage2SubmissionSerializer,
    Round2Stage2SubmissionSerializer,
    LeaderboardEntrySerializer,
)

from .puzzle_engine.generator import generate_puzzle

import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone
from .google_auth import verify_google_credential


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def create_leaderboard_entry(game_session):
    """
    Create the leaderboard entry for a completed game session.

    This function is intentionally idempotent:
    one GameSession can have only one LeaderboardEntry.
    """

    round_1 = RoundState.objects.get(
        game_session=game_session,
        round_number=RoundState.RoundNumber.ROUND_1,
    )

    round_2 = RoundState.objects.get(
        game_session=game_session,
        round_number=RoundState.RoundNumber.ROUND_2,
    )

    round_1_time = round_1.elapsed_ms or 0
    round_2_time = round_2.elapsed_ms or 0

    total_time = (
        round_1_time
        + round_2_time
    )

    total_attempts = (
        round_1.attempts_count
        + round_2.attempts_count
    )

    total_hints_used = (
        round_1.hints_used
        + round_2.hints_used
    )

    entry, created = LeaderboardEntry.objects.get_or_create(
        game_session=game_session,
        defaults={
            "round_1_time_ms": round_1_time,
            "round_2_time_ms": round_2_time,
            "total_time_ms": total_time,
            "total_attempts": total_attempts,
            "total_hints_used": total_hints_used,
            "completed_at": timezone.now(),
        },
    )

    return entry


# ============================================================
# HEALTH CHECK
# ============================================================


class HealthCheckView(APIView):

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "ClueVerse API",
            }
        )


# ============================================================
# REGISTRATION
# ============================================================

class GoogleAuthView(APIView):
    """
    Authenticate a participant using a verified Google ID token.

    Creates a new CIPHERHUNT registration/game session on first login.
    Returning participants resume their existing session.
    """

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        credential = serializer.validated_data["credential"]

        profile = verify_google_credential(credential)

        google_sub = profile["google_sub"]
        email = profile["email"]
        participant_name = profile["participant_name"]

        event_year = timezone.now().year

        with transaction.atomic():

            registration = (
                Registration.objects
                .select_for_update()
                .filter(
                    event_year=event_year,
                    google_sub=google_sub,
                )
                .first()
            )

            is_new_registration = False

            if registration is None:

                email_registration = (
                    Registration.objects
                    .select_for_update()
                    .filter(
                        event_year=event_year,
                        email=email,
                    )
                    .first()
                )

                if email_registration is not None:
                    return Response(
                        {
                            "detail": (
                                "This email is already registered "
                                "with another Google account."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                registration_code = (
                    f"CH-{secrets.token_hex(4).upper()}"
                )

                try:
                    with transaction.atomic():
                        registration = Registration.objects.create(
                            registration_code=registration_code,
                            google_sub=google_sub,
                            participant_name=participant_name,
                            email=email,
                            event_year=event_year,
                        )
                except IntegrityError:
                    registration = (
                        Registration.objects
                        .select_for_update()
                        .get(
                            event_year=event_year,
                            google_sub=google_sub,
                        )
                    )
                else:
                    is_new_registration = True

            game_session = (
                GameSession.objects
                .select_for_update()
                .filter(registration=registration)
                .first()
            )

            if game_session is None:

                game_session = GameSession.objects.create(
                    registration=registration,
                    status=GameSession.Status.NOT_STARTED,
                )

                RoundState.objects.create(
                    game_session=game_session,
                    round_number=RoundState.RoundNumber.ROUND_1,
                    status=RoundState.Status.LOCKED,
                )

                RoundState.objects.create(
                    game_session=game_session,
                    round_number=RoundState.RoundNumber.ROUND_2,
                    status=RoundState.Status.LOCKED,
                )

                puzzle = generate_puzzle()

                PuzzleInstance.objects.create(
                    game_session=game_session,
                    generation_version=puzzle["generation_version"],
                    public_data=puzzle["public_data"],
                    secret_data=puzzle["secret_data"],
                )

        return Response(
            {
                "registration": RegistrationSerializer(
                    registration
                ).data,

                "session": GameSessionStatusSerializer(
                    game_session
                ).data,

                "is_new_registration": is_new_registration,
            },
            status=(
                status.HTTP_201_CREATED
                if is_new_registration
                else status.HTTP_200_OK
            ),
        )

class RegistrationCreateView(APIView):

    def post(self, request):
        serializer = RegistrationSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        with transaction.atomic():

            # --------------------------------------------------
            # 1. Create registration
            # --------------------------------------------------

            registration = serializer.save()

            # --------------------------------------------------
            # 2. Create game session
            # --------------------------------------------------

            game_session = GameSession.objects.create(
                registration=registration,
                status=GameSession.Status.NOT_STARTED,
            )

            # --------------------------------------------------
            # 3. Create Round 1
            # --------------------------------------------------

            RoundState.objects.create(
                game_session=game_session,
                round_number=RoundState.RoundNumber.ROUND_1,
                status=RoundState.Status.LOCKED,
            )

            # --------------------------------------------------
            # 4. Create Round 2
            # --------------------------------------------------

            RoundState.objects.create(
                game_session=game_session,
                round_number=RoundState.RoundNumber.ROUND_2,
                status=RoundState.Status.LOCKED,
            )

            # --------------------------------------------------
            # 5. Generate unique puzzle for this session
            # --------------------------------------------------

            puzzle = generate_puzzle()

            # --------------------------------------------------
            # 6. Store puzzle
            #
            # public_data:
            #     safe player-facing information
            #
            # secret_data:
            #     server-only answers
            # --------------------------------------------------

            PuzzleInstance.objects.create(
                game_session=game_session,
                generation_version=puzzle[
                    "generation_version"
                ],
                public_data=puzzle[
                    "public_data"
                ],
                secret_data=puzzle[
                    "secret_data"
                ],
            )

        # ------------------------------------------------------
        # Return registration/session information only.
        #
        # IMPORTANT:
        # Do NOT return secret_data.
        # Do NOT return the entire puzzle yet.
        # ------------------------------------------------------

        return Response(
            {
                "registration": RegistrationSerializer(
                    registration
                ).data,

                "session": GameSessionStatusSerializer(
                    game_session
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# SESSION STATUS
# ============================================================


class SessionStatusView(APIView):
    permission_classes = [IsGameSessionAuthenticated]

    def get(self, request, session_id):

        game_session = request.auth

        if game_session.id != session_id:
            return Response(
                {
                    "detail": "Forbidden."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = GameSessionStatusSerializer(
            game_session
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ============================================================
# PUBLIC PUZZLE
# ============================================================


class PublicPuzzleView(APIView):

    permission_classes = [
        IsGameSessionAuthenticated
    ]

    def get(self, request):

        game_session = request.auth

        try:
            puzzle = game_session.puzzle

        except PuzzleInstance.DoesNotExist:

            return Response(
                {
                    "detail": "Puzzle not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PublicPuzzleSerializer(
            puzzle
        )

        return Response(
            serializer.data
        )


# ============================================================
# START GAME
# ============================================================


class StartGameView(APIView):
    permission_classes = [IsGameSessionAuthenticated]

    def post(self, request):
        authenticated_session = request.auth

        with transaction.atomic():
            game_session = (
                GameSession.objects
                .select_for_update()
                .get(id=authenticated_session.id)
            )

            round_1 = (
                RoundState.objects
                .select_for_update()
                .get(
                    game_session=game_session,
                    round_number=RoundState.RoundNumber.ROUND_1,
                )
            )

            # -------------------------------------------------
            # CASE 1:
            # Game has never started -> start Round 1
            # -------------------------------------------------
            if game_session.status == GameSession.Status.NOT_STARTED:
                if round_1.status != RoundState.Status.LOCKED:
                    return Response(
                        {
                            "detail": "Round 1 is not in a startable state."
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                now = timezone.now()

                round_1.status = RoundState.Status.ACTIVE
                round_1.started_at = now
                round_1.solved_at = None
                round_1.elapsed_ms = None

                round_1.save(
                    update_fields=[
                        "status",
                        "started_at",
                        "solved_at",
                        "elapsed_ms",
                    ]
                )

                game_session.status = GameSession.Status.ROUND_1

                game_session.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

            # -------------------------------------------------
            # CASE 2:
            # Frontend called start again.
            # Round 1 is already active.
            #
            # This is NOT an error.
            # Return the existing active state.
            # -------------------------------------------------
            elif (
                game_session.status == GameSession.Status.ROUND_1
                and round_1.status == RoundState.Status.ACTIVE
            ):
                pass

            # -------------------------------------------------
            # CASE 3:
            # Session is in some other state.
            # -------------------------------------------------
            else:
                return Response(
                    {
                        "detail": (
                            "Round 1 cannot be started from the "
                            "current game state."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        return Response(
            {
                "session": GameSessionStatusSerializer(
                    game_session
                ).data,
                "round": RoundStateSerializer(
                    round_1
                ).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# ROUND 1 — STAGE 1
# FIND FOUR NODES
# ============================================================

class Round1Stage1SubmitView(APIView):
    permission_classes = [IsGameSessionAuthenticated]

    def post(self, request):
        serializer = Stage1SubmissionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        selected_nodes = (
            serializer.validated_data["selected_nodes"]
        )

        game_session = request.auth

        with transaction.atomic():

            # -------------------------------------------------
            # Lock Round 1 so concurrent submissions cannot
            # corrupt the stage/attempt state.
            # -------------------------------------------------

            round_1 = (
                RoundState.objects
                .select_for_update()
                .get(
                    game_session=game_session,
                    round_number=(
                        RoundState.RoundNumber.ROUND_1
                    ),
                )
            )

            # -------------------------------------------------
            # Round 1 must currently be active.
            # -------------------------------------------------

            if (
                round_1.status
                != RoundState.Status.ACTIVE
            ):
                return Response(
                    {
                        "detail": "Round 1 is not active."
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # -------------------------------------------------
            # Check whether Stage 1 has already been solved.
            #
            # IMPORTANT:
            # This is now idempotent.
            #
            # A duplicate click / retry after a successful
            # submission must NOT produce an error.
            # -------------------------------------------------

            solved_attempt = (
                Attempt.objects
                .filter(
                    round_state=round_1,
                    stage=Attempt.Stage.STAGE_1,
                    correctly_placed=4,
                )
                .order_by("-submitted_at")
                .first()
            )

            if solved_attempt is not None:
                return Response(
                    {
                        "stage": "stage_2",
                        "correctly_placed": 4,
                        "incorrectly_placed": 0,
                        "solved": True,
                        "stage_1_solved": True,
                        "next_stage": "stage_2",
                        "attempts_count": (
                            round_1.attempts_count
                        ),
                    },
                    status=status.HTTP_200_OK,
                )

            # -------------------------------------------------
            # Get the private puzzle.
            # This data is NEVER returned to the player.
            # -------------------------------------------------

            puzzle = (
                PuzzleInstance.objects
                .select_for_update()
                .get(
                    game_session=game_session
                )
            )

            correct_nodes = set(
                puzzle.secret_data[
                    "round_1"
                ][
                    "correct_nodes"
                ]
            )

            selected_node_set = set(
                selected_nodes
            )

            correctly_placed = len(
                selected_node_set.intersection(
                    correct_nodes
                )
            )

            incorrectly_placed = (
                4 - correctly_placed
            )

            # -------------------------------------------------
            # Record the valid Stage 1 submission.
            # -------------------------------------------------

            Attempt.objects.create(
                round_state=round_1,
                stage=Attempt.Stage.STAGE_1,
                selected_nodes=selected_nodes,
                selected_order=[],
                correctly_placed=correctly_placed,
                incorrectly_placed=incorrectly_placed,
            )

            # -------------------------------------------------
            # Count this accepted submission as an attempt.
            # -------------------------------------------------

            round_1.attempts_count += 1

            round_1.save(
                update_fields=[
                    "attempts_count"
                ]
            )

            solved = (
                correctly_placed == 4
            )

        # -----------------------------------------------------
        # SUCCESS
        # -----------------------------------------------------

        if solved:
            return Response(
                {
                    "stage": "stage_2",
                    "correctly_placed": 4,
                    "incorrectly_placed": 0,
                    "solved": True,
                    "stage_1_solved": True,
                    "next_stage": "stage_2",
                    "attempts_count": (
                        round_1.attempts_count
                    ),
                },
                status=status.HTTP_200_OK,
            )

        # -----------------------------------------------------
        # INCORRECT SUBMISSION
        # -----------------------------------------------------

        return Response(
            {
                "stage": "stage_1",
                "correctly_placed": (
                    correctly_placed
                ),
                "incorrectly_placed": (
                    incorrectly_placed
                ),
                "solved": False,
                "stage_1_solved": False,
                "attempts_count": (
                    round_1.attempts_count
                ),
            },
            status=status.HTTP_200_OK,
        )

# ============================================================
# ROUND 1 — STAGE 2
# ORDER FOUR NODES
# ============================================================


class Round1Stage2SubmitView(APIView):

    permission_classes = [
        IsGameSessionAuthenticated
    ]

    def post(self, request):

        serializer = Stage2SubmissionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        selected_order = serializer.validated_data[
            "selected_order"
        ]

        game_session = request.auth

        with transaction.atomic():

            round_1 = (
                RoundState.objects
                .select_for_update()
                .get(
                    game_session=game_session,
                    round_number=RoundState.RoundNumber.ROUND_1,
                )
            )

            if (
                round_1.status
                != RoundState.Status.ACTIVE
            ):

                return Response(
                    {
                        "detail": (
                            "Round 1 is not active."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            stage_1_solved_attempt = (
                Attempt.objects
                .filter(
                    round_state=round_1,
                    stage=Attempt.Stage.STAGE_1,
                    correctly_placed=4,
                )
                .exists()
            )

            if not stage_1_solved_attempt:

                return Response(
                    {
                        "detail": (
                            "Round 1 Stage 1 must "
                            "be solved before Stage 2."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            stage_1_attempt = (
                Attempt.objects
                .filter(
                    round_state=round_1,
                    stage=Attempt.Stage.STAGE_1,
                    correctly_placed=4,
                )
                .order_by("-submitted_at")
                .first()
            )

            discovered_nodes = set(
                stage_1_attempt.selected_nodes
            )

            submitted_nodes = set(
                selected_order
            )

            if (
                submitted_nodes
                != discovered_nodes
            ):

                return Response(
                    {
                        "detail": (
                            "Stage 2 must use exactly "
                            "the four nodes discovered "
                            "in Stage 1."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            puzzle = (
                PuzzleInstance.objects
                .select_for_update()
                .get(
                    game_session=game_session
                )
            )

            correct_order = puzzle.secret_data[
                "round_1"
            ][
                "correct_order"
            ]

            is_correct = (
                selected_order
                == correct_order
            )

            Attempt.objects.create(
                round_state=round_1,
                stage=Attempt.Stage.STAGE_2,
                selected_nodes=selected_order,
                selected_order=selected_order,
                correctly_placed=(
                    4 if is_correct else 0
                ),
                incorrectly_placed=(
                    0 if is_correct else 4
                ),
            )

            round_1.attempts_count += 1

            if is_correct:

                now = timezone.now()

                round_1.status = (
                    RoundState.Status.SOLVED
                )

                round_1.solved_at = now

                if round_1.started_at is not None:

                    elapsed = (
                        now
                        - round_1.started_at
                    )

                    round_1.elapsed_ms = int(
                        elapsed.total_seconds()
                        * 1000
                    )

                round_1.save(
                    update_fields=[
                        "status",
                        "solved_at",
                        "elapsed_ms",
                        "attempts_count",
                    ]
                )

                round_2 = (
                    RoundState.objects
                    .select_for_update()
                    .get(
                        game_session=game_session,
                        round_number=(
                            RoundState
                            .RoundNumber
                            .ROUND_2
                        ),
                    )
                )

                round_2.status = (
                    RoundState.Status.ACTIVE
                )

                round_2.started_at = now
                round_2.solved_at = None
                round_2.elapsed_ms = None

                round_2.save(
                    update_fields=[
                        "status",
                        "started_at",
                        "solved_at",
                        "elapsed_ms",
                    ]
                )

                game_session.status = (
                    GameSession.Status.ROUND_2
                )

                game_session.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

            else:

                round_1.save(
                    update_fields=[
                        "attempts_count"
                    ]
                )

        if is_correct:

            return Response(
                {
                    "stage": "stage_2",
                    "correct": True,
                    "solved": True,
                    "round_completed": True,
                    "next_round": 2,
                    "attempts_count": (
                        round_1.attempts_count
                    ),
                    "round_time_ms": (
                        round_1.elapsed_ms
                    ),
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "stage": "stage_2",
                "correct": False,
                "solved": False,
                "round_completed": False,
                "attempts_count": (
                    round_1.attempts_count
                ),
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# ROUND 2 — STAGE 1
# FIND FOUR LONGITUDE NODES
# ============================================================


class Round2Stage1SubmitView(APIView):

    permission_classes = [
        IsGameSessionAuthenticated
    ]

    def post(self, request):

        serializer = Stage1SubmissionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        selected_nodes = serializer.validated_data[
            "selected_nodes"
        ]

        game_session = request.auth

        with transaction.atomic():

            round_2 = (
                RoundState.objects
                .select_for_update()
                .get(
                    game_session=game_session,
                    round_number=RoundState.RoundNumber.ROUND_2,
                )
            )

            if (
                round_2.status
                != RoundState.Status.ACTIVE
            ):

                return Response(
                    {
                        "detail": (
                            "Round 2 is not active."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            already_solved = (
                Attempt.objects
                .filter(
                    round_state=round_2,
                    stage=Attempt.Stage.STAGE_1,
                    correctly_placed=4,
                )
                .exists()
            )

            if already_solved:

                return Response(
                    {
                        "detail": (
                            "Round 2 Stage 1 "
                            "is already solved."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            puzzle = (
                PuzzleInstance.objects
                .select_for_update()
                .get(
                    game_session=game_session
                )
            )

            correct_nodes = set(
                puzzle.secret_data[
                    "round_2"
                ][
                    "correct_nodes"
                ]
            )

            selected_node_set = set(
                selected_nodes
            )

            correctly_placed = len(
                selected_node_set.intersection(
                    correct_nodes
                )
            )

            incorrectly_placed = (
                4 - correctly_placed
            )

            Attempt.objects.create(
                round_state=round_2,
                stage=Attempt.Stage.STAGE_1,
                selected_nodes=selected_nodes,
                selected_order=[],
                correctly_placed=correctly_placed,
                incorrectly_placed=incorrectly_placed,
            )

            round_2.attempts_count += 1

            round_2.save(
                update_fields=[
                    "attempts_count"
                ]
            )

            solved = (
                correctly_placed == 4
            )

        return Response(
            {
                "stage": "stage_1",
                "correctly_placed": correctly_placed,
                "incorrectly_placed": incorrectly_placed,
                "solved": solved,
                "attempts_count": (
                    round_2.attempts_count
                ),
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# ROUND 2 — STAGE 2
# FINAL ORDERED TRAIL
# ============================================================


class Round2Stage2SubmitView(APIView):

    permission_classes = [
        IsGameSessionAuthenticated
    ]

    def post(self, request):

        serializer = Round2Stage2SubmissionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        selected_order = serializer.validated_data[
            "selected_order"
        ]

        game_session = request.auth

        with transaction.atomic():

            round_2 = (
                RoundState.objects
                .select_for_update()
                .get(
                    game_session=game_session,
                    round_number=RoundState.RoundNumber.ROUND_2,
                )
            )

            if (
                round_2.status
                != RoundState.Status.ACTIVE
            ):

                return Response(
                    {
                        "detail": (
                            "Round 2 is not active."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            stage_1_attempt = (
                Attempt.objects
                .filter(
                    round_state=round_2,
                    stage=Attempt.Stage.STAGE_1,
                    correctly_placed=4,
                )
                .order_by("-submitted_at")
                .first()
            )

            if stage_1_attempt is None:

                return Response(
                    {
                        "detail": (
                            "Round 2 Stage 1 must "
                            "be solved before Stage 2."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            discovered_nodes = set(
                stage_1_attempt.selected_nodes
            )

            submitted_nodes = set(
                selected_order
            )

            if (
                submitted_nodes
                != discovered_nodes
            ):

                return Response(
                    {
                        "detail": (
                            "Stage 2 must use exactly "
                            "the four nodes discovered "
                            "in Stage 1."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            puzzle = (
                PuzzleInstance.objects
                .select_for_update()
                .get(
                    game_session=game_session
                )
            )

            correct_order = puzzle.secret_data[
                "round_2"
            ][
                "correct_order"
            ]

            is_correct = (
                selected_order
                == correct_order
            )

            Attempt.objects.create(
                round_state=round_2,
                stage=Attempt.Stage.STAGE_2,
                selected_nodes=selected_order,
                selected_order=selected_order,
                correctly_placed=(
                    4 if is_correct else 0
                ),
                incorrectly_placed=(
                    0 if is_correct else 4
                ),
            )

            round_2.attempts_count += 1

            if not is_correct:

                round_2.save(
                    update_fields=[
                        "attempts_count"
                    ]
                )

            else:

                now = timezone.now()

                round_2.status = (
                    RoundState.Status.SOLVED
                )

                round_2.solved_at = now

                if round_2.started_at is not None:

                    elapsed = (
                        now
                        - round_2.started_at
                    )

                    round_2.elapsed_ms = int(
                        elapsed.total_seconds()
                        * 1000
                    )

                round_2.save(
                    update_fields=[
                        "status",
                        "solved_at",
                        "elapsed_ms",
                        "attempts_count",
                    ]
                )

                game_session.status = (
                    GameSession.Status.FINAL
                )

                game_session.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

                # --------------------------------------------
                # Create leaderboard entry.
                #
                # This is idempotent because GameSession has
                # a OneToOne relationship with LeaderboardEntry.
                # --------------------------------------------

                leaderboard_entry = (
                    create_leaderboard_entry(
                        game_session
                    )
                )

                longitude = puzzle.secret_data[
                    "round_2"
                ][
                    "longitude"
                ]

        # ====================================================
        # SUCCESSFUL FINAL SUBMISSION
        # ====================================================

        if is_correct:

            return Response(
                {
                    "stage": "stage_2",
                    "correct": True,
                    "solved": True,
                    "round_completed": True,
                    "game_completed": True,

                    "round_time_ms": (
                        round_2.elapsed_ms
                    ),

                    "attempts_count": (
                        round_2.attempts_count
                    ),

                    "longitude": longitude,

                    "leaderboard": {
                        "round_1_time_ms": (
                            leaderboard_entry
                            .round_1_time_ms
                        ),

                        "round_2_time_ms": (
                            leaderboard_entry
                            .round_2_time_ms
                        ),

                        "total_time_ms": (
                            leaderboard_entry
                            .total_time_ms
                        ),

                        "total_attempts": (
                            leaderboard_entry
                            .total_attempts
                        ),

                        "total_hints_used": (
                            leaderboard_entry
                            .total_hints_used
                        ),
                    },
                },
                status=status.HTTP_200_OK,
            )

        # ====================================================
        # WRONG FINAL SUBMISSION
        # ====================================================

        return Response(
            {
                "stage": "stage_2",
                "correct": False,
                "solved": False,
                "round_completed": False,
                "game_completed": False,
                "attempts_count": (
                    round_2.attempts_count
                ),
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# FINAL RESULT
# ============================================================


class FinalResultView(APIView):
    permission_classes = [IsGameSessionAuthenticated]

    def get(self, request):
        game_session = request.auth

        # -----------------------------------------------------
        # Load the authoritative session from the database.
        # -----------------------------------------------------
        game_session = (
            GameSession.objects
            .select_related("registration")
            .get(id=game_session.id)
        )

        # -----------------------------------------------------
        # Final result is available only after both rounds
        # have been successfully completed.
        # -----------------------------------------------------
        if game_session.status != GameSession.Status.FINAL:
            return Response(
                {
                    "detail": (
                        "Final result is available only after "
                        "both investigation rounds are solved."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # -----------------------------------------------------
        # Load both round states.
        # -----------------------------------------------------
        round_1 = (
            RoundState.objects
            .get(
                game_session=game_session,
                round_number=(
                    RoundState.RoundNumber.ROUND_1
                ),
            )
        )

        round_2 = (
            RoundState.objects
            .get(
                game_session=game_session,
                round_number=(
                    RoundState.RoundNumber.ROUND_2
                ),
            )
        )

        # -----------------------------------------------------
        # Safety check: both rounds must be solved.
        # -----------------------------------------------------
        if (
            round_1.status != RoundState.Status.SOLVED
            or round_2.status != RoundState.Status.SOLVED
        ):
            return Response(
                {
                    "detail": (
                        "Final result cannot be released "
                        "until both rounds are solved."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # -----------------------------------------------------
        # Load the private puzzle.
        #
        # IMPORTANT:
        # secret_data is read only on the server.
        # It is never returned to the browser.
        # -----------------------------------------------------
        try:
            puzzle = (
                PuzzleInstance.objects
                .get(game_session=game_session)
            )
        except PuzzleInstance.DoesNotExist:
            return Response(
                {
                    "detail": "Puzzle not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # -----------------------------------------------------
        # Extract the earned coordinates from private data.
        # -----------------------------------------------------
        try:
            latitude = puzzle.secret_data[
                "round_1"
            ]["latitude"]

            longitude = puzzle.secret_data[
                "round_2"
            ]["longitude"]

        except (KeyError, TypeError):
            return Response(
                {
                    "detail": (
                        "Final coordinate data is unavailable."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # -----------------------------------------------------
        # Official server-calculated scoring values.
        # -----------------------------------------------------
        round_1_time_ms = (
            round_1.elapsed_ms or 0
        )

        round_2_time_ms = (
            round_2.elapsed_ms or 0
        )

        total_time_ms = (
            round_1_time_ms +
            round_2_time_ms
        )

        round_1_attempts = (
            round_1.attempts_count
        )

        round_2_attempts = (
            round_2.attempts_count
        )

        total_attempts = (
            round_1_attempts +
            round_2_attempts
        )

        # -----------------------------------------------------
        # Current implementation does not expose a player
        # hint workflow, so the authoritative count is zero.
        # This keeps the response compatible with the final UI.
        # -----------------------------------------------------
        total_hints_used = 0

        # -----------------------------------------------------
        # The Round 2 solve is the moment the session entered
        # FINAL, so updated_at is the best existing completion
        # timestamp in the current model implementation.
        # -----------------------------------------------------
        completed_at = (
            game_session.updated_at
        )

        # -----------------------------------------------------
        # Return ONLY player-safe final data.
        #
        # Do NOT return:
        # - secret_data
        # - correct_nodes
        # - correct_order
        # - generation seed
        # - private mappings
        # - extraction positions
        # -----------------------------------------------------
        data = {
            "registration_code": (
                game_session
                .registration
                .registration_code
            ),

            "participant_name": (
                game_session
                .registration
                .participant_name
            ),

            "round_1_time_ms": (
                round_1_time_ms
            ),

            "round_2_time_ms": (
                round_2_time_ms
            ),

            "total_time_ms": (
                total_time_ms
            ),

            "round_1_attempts": (
                round_1_attempts
            ),

            "round_2_attempts": (
                round_2_attempts
            ),

            "total_attempts": (
                total_attempts
            ),

            "total_hints_used": (
                total_hints_used
            ),

            "latitude": latitude,

            "longitude": longitude,

            "completed_at": completed_at,
        }

        return Response(
            data,
            status=status.HTTP_200_OK,
        )


# ============================================================
# LEADERBOARD
# ============================================================


class LeaderboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        entries = (
            LeaderboardEntry.objects
            .select_related(
                "game_session__registration"
            )
            .order_by(
                "total_time_ms",
                "total_attempts",
                "total_hints_used",
                "completed_at",
                "id",
            )
        )

        serializer = LeaderboardEntrySerializer(
            entries,
            many=True,
        )

        data = serializer.data

        return Response(
            {
                "count": len(data),
                "results": data,
            },
            status=status.HTTP_200_OK,
        )