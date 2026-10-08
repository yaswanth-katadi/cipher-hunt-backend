import uuid

from django.db import models


class Registration(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    registration_code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
    )

    # Stable Google account identifier.
    # This is obtained from the verified Google ID token.
    google_sub = models.CharField(
         max_length=255,
         db_index=True,
    )
    participant_name = models.CharField(
        max_length=120,
    )

    email = models.EmailField()

    event_year = models.PositiveIntegerField(
        default=2026,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event_year", "google_sub"],
                name="unique_google_registration_per_event",
            ),
            models.UniqueConstraint(
                fields=["event_year", "email"],
                name="unique_registration_per_event_email",
            ),
        ]

    def __str__(self):
        return f"{self.registration_code} - {self.participant_name}"


class GameSession(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        ROUND_1 = "round_1", "Round 1"
        ROUND_2 = "round_2", "Round 2"
        FINAL = "final", "Final"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    registration = models.OneToOneField(
        Registration,
        on_delete=models.CASCADE,
        related_name="game_session",
    )

    session_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=Status,
        default=Status.NOT_STARTED,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session {self.id}"


class PuzzleInstance(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    game_session = models.OneToOneField(
        GameSession,
        on_delete=models.CASCADE,
        related_name="puzzle",
    )

    generation_version = models.CharField(
        max_length=30,
        default="v1",
    )

    # Safe information that may be sent to the player.
    public_data = models.JSONField(
        default=dict,
    )

    # Private solution information.
    # This must NEVER be sent to the frontend.
    secret_data = models.JSONField(
        default=dict,
    )

    generated_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Puzzle {self.id}"


class RoundState(models.Model):
    class RoundNumber(models.IntegerChoices):
        ROUND_1 = 1, "Round 1"
        ROUND_2 = 2, "Round 2"

    class Status(models.TextChoices):
        LOCKED = "locked", "Locked"
        ACTIVE = "active", "Active"
        SOLVED = "solved", "Solved"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    game_session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="round_states",
    )

    round_number = models.PositiveSmallIntegerField(
        choices=RoundNumber,
    )

    status = models.CharField(
        max_length=10,
        default=Status.LOCKED,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    solved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    elapsed_ms = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    attempts_count = models.PositiveIntegerField(
        default=0,
    )

    hints_used = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["round_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["game_session", "round_number"],
                name="unique_round_per_session",
            ),
        ]

    def __str__(self):
        return f"{self.game_session_id} - Round {self.round_number}"


class Attempt(models.Model):
    class Stage(models.TextChoices):
        STAGE_1 = "stage_1", "Stage 1"
        STAGE_2 = "stage_2", "Stage 2"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    round_state = models.ForeignKey(
        RoundState,
        on_delete=models.CASCADE,
        related_name="attempts",
    )

    stage = models.CharField(
        max_length=10,
    )

    selected_nodes = models.JSONField(
        default=list,
    )

    selected_order = models.JSONField(
        default=list,
    )

    correctly_placed = models.PositiveSmallIntegerField(
        default=0,
    )

    incorrectly_placed = models.PositiveSmallIntegerField(
        default=0,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["submitted_at"]
        indexes = [
            models.Index(
                fields=["round_state", "stage"],
                name="attempt_round_stage_idx",
            ),
        ]

    def __str__(self):
        return f"{self.stage} attempt - {self.round_state_id}"


class HintUsage(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    round_state = models.ForeignKey(
        RoundState,
        on_delete=models.CASCADE,
        related_name="hint_usages",
    )

    hint_code = models.CharField(
        max_length=50,
    )

    used_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.hint_code} - {self.round_state_id}"


class LeaderboardEntry(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    game_session = models.OneToOneField(
        GameSession,
        on_delete=models.CASCADE,
        related_name="leaderboard_entry",
    )

    round_1_time_ms = models.PositiveBigIntegerField(
        default=0,
    )

    round_2_time_ms = models.PositiveBigIntegerField(
        default=0,
    )

    total_time_ms = models.PositiveBigIntegerField(
        default=0,
    )

    total_attempts = models.PositiveIntegerField(
        default=0,
    )

    total_hints_used = models.PositiveIntegerField(
        default=0,
    )

    completed_at = models.DateTimeField()

    class Meta:
        ordering = [
            "total_time_ms",
            "total_attempts",
            "total_hints_used",
            "completed_at",
        ]

    def __str__(self):
        return f"Leaderboard - {self.game_session_id}"