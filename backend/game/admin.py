from django.contrib import admin

from .models import (
    Attempt,
    GameSession,
    HintUsage,
    LeaderboardEntry,
    PuzzleInstance,
    Registration,
    RoundState,
)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "registration_code",
        "participant_name",
        "email",
        "event_year",
        "created_at",
    )

    search_fields = (
        "registration_code",
        "participant_name",
        "email",
        "google_sub",
    )

    list_filter = (
        "event_year",
        "created_at",
    )

    readonly_fields = (
        "id",
        "registration_code",
        "google_sub",
        "participant_name",
        "email",
        "event_year",
        "created_at",
    )


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "registration",
        "status",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "id",
        "registration__registration_code",
        "registration__participant_name",
        "registration__email",
    )

    list_filter = (
        "status",
        "created_at",
    )

    readonly_fields = (
        "id",
        "registration",
        "session_token",
        "status",
        "created_at",
        "updated_at",
    )


@admin.register(PuzzleInstance)
class PuzzleInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "game_session",
        "generation_version",
        "generated_at",
    )

    search_fields = (
        "id",
        "game_session__id",
        "game_session__registration__registration_code",
    )

    list_filter = (
        "generation_version",
        "generated_at",
    )

    readonly_fields = (
        "id",
        "game_session",
        "generation_version",
        "public_data",
        "secret_data",
        "generated_at",
    )


@admin.register(RoundState)
class RoundStateAdmin(admin.ModelAdmin):
    list_display = (
        "game_session",
        "round_number",
        "status",
        "started_at",
        "solved_at",
        "elapsed_ms",
        "attempts_count",
        "hints_used",
    )

    search_fields = (
        "game_session__id",
        "game_session__registration__registration_code",
        "game_session__registration__participant_name",
    )

    list_filter = (
        "round_number",
        "status",
    )

    readonly_fields = (
        "id",
        "game_session",
        "round_number",
        "status",
        "started_at",
        "solved_at",
        "elapsed_ms",
        "attempts_count",
        "hints_used",
    )


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "round_state",
        "stage",
        "correctly_placed",
        "incorrectly_placed",
        "submitted_at",
    )

    search_fields = (
        "id",
        "round_state__game_session__registration__registration_code",
        "round_state__game_session__registration__participant_name",
    )

    list_filter = (
        "stage",
        "submitted_at",
    )

    readonly_fields = (
        "id",
        "round_state",
        "stage",
        "selected_nodes",
        "selected_order",
        "correctly_placed",
        "incorrectly_placed",
        "submitted_at",
    )


@admin.register(HintUsage)
class HintUsageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "round_state",
        "hint_code",
        "used_at",
    )

    search_fields = (
        "id",
        "hint_code",
        "round_state__game_session__registration__registration_code",
    )

    list_filter = (
        "hint_code",
        "used_at",
    )

    readonly_fields = (
        "id",
        "round_state",
        "hint_code",
        "used_at",
    )


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = (
        "game_session",
        "round_1_time_ms",
        "round_2_time_ms",
        "total_time_ms",
        "total_attempts",
        "total_hints_used",
        "completed_at",
    )

    search_fields = (
        "game_session__registration__registration_code",
        "game_session__registration__participant_name",
        "game_session__registration__email",
    )

    ordering = (
        "total_time_ms",
        "total_attempts",
        "total_hints_used",
        "completed_at",
    )

    readonly_fields = (
        "id",
        "game_session",
        "round_1_time_ms",
        "round_2_time_ms",
        "total_time_ms",
        "total_attempts",
        "total_hints_used",
        "completed_at",
    )