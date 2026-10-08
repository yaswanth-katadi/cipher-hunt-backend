from django.test import TestCase
from rest_framework.test import APIClient

from game.models import GameSession, RoundState


class GameStartTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        payload = {
            "participant_name": "Start Test Player",
            "email": "start-test@example.com",
            "college": "NIT Durgapur",
            "game_mode": "single",
            "team_name": "",
            "team_leader_name": "",
        }

        response = self.client.post(
            "/api/registration/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.session_id = response.data["session"]["id"]
        self.session_token = response.data["session"]["session_token"]

    def authenticate(self):
        self.client.credentials(
            HTTP_X_SESSION_TOKEN=self.session_token
        )

    def test_game_starts_round_1(self):
        self.authenticate()

        response = self.client.post(
            "/api/session/start/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        session = GameSession.objects.get(
            id=self.session_id
        )

        round_1 = RoundState.objects.get(
            game_session=session,
            round_number=1,
        )

        round_2 = RoundState.objects.get(
            game_session=session,
            round_number=2,
        )

        self.assertEqual(
            session.status,
            GameSession.Status.ROUND_1,
        )

        self.assertEqual(
            round_1.status,
            RoundState.Status.ACTIVE,
        )

        self.assertIsNotNone(
            round_1.started_at
        )

        self.assertIsNone(
            round_1.solved_at
        )

        self.assertIsNone(
            round_1.elapsed_ms
        )

        self.assertEqual(
            round_2.status,
            RoundState.Status.LOCKED,
        )

    def test_game_cannot_be_started_twice(self):
        self.authenticate()

        first_response = self.client.post(
            "/api/session/start/",
            {},
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            200,
        )

        first_round = RoundState.objects.get(
            game_session__id=self.session_id,
            round_number=1,
        )

        first_started_at = first_round.started_at

        second_response = self.client.post(
            "/api/session/start/",
            {},
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            409,
        )

        first_round.refresh_from_db()

        self.assertEqual(
            first_round.started_at,
            first_started_at,
        )

    def test_unauthenticated_user_cannot_start_game(self):
        response = self.client.post(
            "/api/session/start/",
            {},
            format="json",
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

    def test_client_cannot_supply_timer_value(self):
        self.authenticate()

        response = self.client.post(
            "/api/session/start/",
            {
                "elapsed_ms": 999999999,
                "started_at": "2000-01-01T00:00:00Z",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        round_1 = RoundState.objects.get(
            game_session__id=self.session_id,
            round_number=1,
        )

        self.assertNotEqual(
            round_1.elapsed_ms,
            999999999,
        )

        self.assertNotEqual(
            str(round_1.started_at),
            "2000-01-01 00:00:00+00:00",
        )