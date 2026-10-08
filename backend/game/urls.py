from django.urls import path


from .views import (
    HealthCheckView,
    GoogleAuthView,
    PublicPuzzleView,
    Round1Stage1SubmitView,
    Round1Stage2SubmitView,
    Round2Stage1SubmitView,
    Round2Stage2SubmitView,
    FinalResultView,
    LeaderboardView,
    SessionStatusView,
    StartGameView,
)

urlpatterns = [
    path(
        "health/",
        HealthCheckView.as_view(),
        name="api-health",
    ),

    path("auth/google/", 
         GoogleAuthView.as_view(), 
         name="google-auth"),

    path(
        "session/puzzle/",
        PublicPuzzleView.as_view(),
        name="public-puzzle",
    ),

    path(
        "session/start/",
        StartGameView.as_view(),
        name="session-start",
    ),

    path(
        "session/round-1/stage-1/",
        Round1Stage1SubmitView.as_view(),
        name="round-1-stage-1-submit",
    ),

    path(
    "session/round-1/stage-1/",
    Round1Stage1SubmitView.as_view(),
    name="round-1-stage-1-submit",
),

path(
    "session/round-1/stage-2/",
    Round1Stage2SubmitView.as_view(),
    name="round-1-stage-2-submit",
),

path(
    "session/round-2/stage-1/",
    Round2Stage1SubmitView.as_view(),
    name="round-2-stage-1-submit",
),

path(
    "session/round-2/stage-2/",
    Round2Stage2SubmitView.as_view(),
    name="round-2-stage-2-submit",
),

path("session/final-result/", FinalResultView.as_view(), name="final-result"),
path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),

path(
    "session/<uuid:session_id>/",
    SessionStatusView.as_view(),
    name="session-status",
),

    path(
        "session/<uuid:session_id>/",
        SessionStatusView.as_view(),
        name="session-status",
    ),
]