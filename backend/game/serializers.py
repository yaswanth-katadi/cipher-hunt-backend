from rest_framework import serializers

from .models import (
    Registration,
    GameSession,
    PuzzleInstance,
    RoundState,
    Attempt,
    HintUsage,
    LeaderboardEntry,
)

class GoogleAuthSerializer(serializers.Serializer):
    credential = serializers.CharField(
        write_only=True,
        trim_whitespace=True,
    )

class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = [
            "id",
            "registration_code",
            "participant_name",
            "email",
            "event_year",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "registration_code",
            "participant_name",
            "email",
            "event_year",
            "created_at",
        ]


    def validate(self, attrs):
        game_mode = attrs.get("game_mode")

        if game_mode == Registration.GameMode.SINGLE:
            attrs["team_name"] = ""
            attrs["team_leader_name"] = ""

        elif game_mode == Registration.GameMode.TEAM:
            if not attrs.get("team_name"):
                raise serializers.ValidationError(
                    {
                        "team_name": (
                            "Team name is required for Team Mode."
                        )
                    }
                )

            if not attrs.get("team_leader_name"):
                raise serializers.ValidationError(
                    {
                        "team_leader_name": (
                            "Team leader name is required for Team Mode."
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        registration = Registration.objects.create(
            registration_code=self._generate_registration_code(),
            **validated_data,
        )

        return registration

    @staticmethod
    def _generate_registration_code():
        import secrets

        while True:
            code = f"CV-{secrets.token_hex(4).upper()}"

            if not Registration.objects.filter(
                registration_code=code
            ).exists():
                return code


class GameSessionStatusSerializer(serializers.ModelSerializer):
    registration_code = serializers.CharField(
        source="registration.registration_code",
        read_only=True,
    )

    participant_name = serializers.CharField(
        source="registration.participant_name",
        read_only=True,
    )

    round_1_status = serializers.SerializerMethodField()
    round_1_attempts = serializers.SerializerMethodField()
    round_1_stage = serializers.SerializerMethodField()

    round_2_status = serializers.SerializerMethodField()
    round_2_attempts = serializers.SerializerMethodField()
    round_2_stage = serializers.SerializerMethodField()

    class Meta:
        model = GameSession

        fields = [
            "id",
            "registration_code",
            "participant_name",
            "status",
            "session_token",
            "created_at",
            "updated_at",

            "round_1_status",
            "round_1_attempts",
            "round_1_stage",

            "round_2_status",
            "round_2_attempts",
            "round_2_stage",
        ]

        read_only_fields = fields

    def _get_round_state(self, obj, round_number):
        return obj.round_states.filter(
            round_number=round_number
        ).first()

    def _get_stage(self, round_state):
        if not round_state:
            return None

        if round_state.status == "SOLVED":
            return "completed"

        if round_state.status != "ACTIVE":
            return None

        from .models import Attempt

        stage_1_solved = Attempt.objects.filter(
            round_state=round_state,
            stage=Attempt.Stage.STAGE_1,
            correctly_placed=4,
        ).exists()

        if stage_1_solved:
            return "stage_2"

        return "stage_1"

    def get_round_1_status(self, obj):
        round_state = self._get_round_state(
            obj,
            1,
        )

        return (
            round_state.status
            if round_state
            else None
        )

    def get_round_1_attempts(self, obj):
        round_state = self._get_round_state(
            obj,
            1,
        )

        return (
            round_state.attempts_count
            if round_state
            else 0
        )

    def get_round_1_stage(self, obj):
        round_state = self._get_round_state(
            obj,
            1,
        )

        return self._get_stage(round_state)

    def get_round_2_status(self, obj):
        round_state = self._get_round_state(
            obj,
            2,
        )

        return (
            round_state.status
            if round_state
            else None
        )

    def get_round_2_attempts(self, obj):
        round_state = self._get_round_state(
            obj,
            2,
        )

        return (
            round_state.attempts_count
            if round_state
            else 0
        )

    def get_round_2_stage(self, obj):
        round_state = self._get_round_state(
            obj,
            2,
        )

        return self._get_stage(round_state)

class PublicPuzzleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuzzleInstance

        fields = [
            "id",
            "generation_version",
            "public_data",
            "generated_at",
        ]

        read_only_fields = fields


class RoundStateSerializer(serializers.ModelSerializer):
    round_number = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = RoundState

        fields = [
            "id",
            "round_number",
            "status",
            "started_at",
            "solved_at",
            "elapsed_ms",
            "attempts_count",
            "hints_used",
        ]

        read_only_fields = fields


class Stage1SubmissionSerializer(serializers.Serializer):
    selected_nodes = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )

    def validate_selected_nodes(self, value):
        if len(value) != 4:
            raise serializers.ValidationError(
                "Exactly four nodes must be selected."
            )

        if len(set(value)) != 4:
            raise serializers.ValidationError(
                "A node cannot be selected more than once."
            )

        if not all(1 <= node <= 9 for node in value):
            raise serializers.ValidationError(
                "Nodes must be between 1 and 9."
            )

        return value

class Stage2SubmissionSerializer(serializers.Serializer):
    selected_order = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )

    def validate_selected_order(self, value):
        if len(value) != 4:
            raise serializers.ValidationError(
                "Exactly four nodes must be selected."
            )

        if len(set(value)) != 4:
            raise serializers.ValidationError(
                "A node cannot be selected more than once."
            )

        if not all(1 <= node <= 9 for node in value):
            raise serializers.ValidationError(
                "Nodes must be between 1 and 9."
            )

        return value

class Round2Stage2SubmissionSerializer(serializers.Serializer):
    selected_order = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )

    def validate_selected_order(self, value):
        if len(value) != 4:
            raise serializers.ValidationError(
                "Exactly four nodes must be selected."
            )

        if len(set(value)) != 4:
            raise serializers.ValidationError(
                "A node cannot be selected more than once."
            )

        if not all(1 <= node <= 9 for node in value):
            raise serializers.ValidationError(
                "Nodes must be between 1 and 9."
            )

        return value

class FinalResultSerializer(serializers.Serializer):
    registration_code = serializers.CharField()
    participant_name = serializers.CharField()

    round_1_time_ms = serializers.IntegerField()
    round_2_time_ms = serializers.IntegerField()
    total_time_ms = serializers.IntegerField()

    round_1_attempts = serializers.IntegerField()
    round_2_attempts = serializers.IntegerField()
    total_attempts = serializers.IntegerField()

    total_hints_used = serializers.IntegerField()

    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

    completed_at = serializers.DateTimeField()


class LeaderboardEntrySerializer(serializers.ModelSerializer):
    registration_code = serializers.CharField(
        source="game_session.registration.registration_code",
        read_only=True,
    )

    participant_name = serializers.CharField(
        source="game_session.registration.participant_name",
        read_only=True,
    )

    game_mode = serializers.CharField(
        source="game_session.registration.game_mode",
        read_only=True,
    )

    class Meta:
        model = LeaderboardEntry

        fields = [
            "registration_code",
            "participant_name",
            "game_mode",
            "round_1_time_ms",
            "round_2_time_ms",
            "total_time_ms",
            "total_attempts",
            "total_hints_used",
            "completed_at",
        ]

        read_only_fields = fields