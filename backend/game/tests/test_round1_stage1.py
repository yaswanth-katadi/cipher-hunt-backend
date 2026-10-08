from django.test import TestCase
from rest_framework.test import APIClient

from game.models import Attempt, GameSession, RoundState


class Round1Stage1Tests(TestCase):

    def setUp(self):
        self.client = APIClient()

        payload = {
            "participant_name": "Stage One Player",
            "email": "stage-one@example.com",
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

        self.client.credentials(
            HTTP_X_SESSION_TOKEN=self.session_token
        )

        start_response = self.client.post(
            "/api/session/start/",
            {},
            format="json",
        )

        self.assertEqual(start_response.status_code, 200)

    def test_stage_1_accepts_four_nodes(self):
        response = self.client.post(
            "/api/session/round-1/stage-1/",
            {
                "selected_nodes": [1, 2, 3, 4]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            "correctly_placed",
            response.data,
        )

        self.assertIn(
            "incorrectly_placed",
            response.data,
        )

        self.assertIn(
            "solved",
            response.data,
        )

        self.assertEqual(
            response.data["correctly_placed"]
            + response.data["incorrectly_placed"],
            4,
        )

        self.assertEqual(
            Attempt.objects.count(),
            1,
        )

    def test_wrong_or_partial_attempt_does_not_reveal_nodes(self):
        response = self.client.post(
            "/api/session/round-1/stage-1/",
            {
                "selected_nodes": [1, 2, 3, 4]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        response_text = str(
            response.data
        ).lower()

        self.assertNotIn(
            "correct_nodes",
            response_text,
        )

        self.assertNotIn(
            "correct_order",
            response_text,
        )

    def test_duplicate_nodes_are_rejected(self):
        response = self.client.post(
            "/api/session/round-1/stage-1/",
            {
                "selected_nodes": [1, 2, 2, 4]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            Attempt.objects.count(),
            0,
        )

    def test_wrong_number_of_nodes_is_rejected(self):
        response = self.client.post(
            "/api/session/round-1/stage-1/",
            {
                "selected_nodes": [1, 2, 3]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            Attempt.objects.count(),
            0,
        )

    def test_attempt_count_increases(self):
        round_1 = RoundState.objects.get(
            game_session__id=self.session_id,
            round_number=1,
        )

        self.assertEqual(
            round_1.attempts_count,
            0,
        )

        self.client.post(
            "/api/session/round-1/stage-1/",
            {
                "selected_nodes": [1, 2, 3, 4]
            },
            format="json",
        )

        round_1.refresh_from_db()

        self.assertEqual(
            round_1.attempts_count,
            1,
        )
        