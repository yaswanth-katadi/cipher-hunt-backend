from django.test import TestCase
from rest_framework.test import APIClient

from game.models import PuzzleInstance


class PublicPuzzleAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.registration_payload = {
            "participant_name": "API Test Player",
            "email": "api-test@example.com",
            "college": "NIT Durgapur",
            "game_mode": "single",
            "team_name": "",
            "team_leader_name": "",
        }

        response = self.client.post(
            "/api/registration/",
            self.registration_payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.registration_response = response.data

        self.session_id = response.data["session"]["id"]
        self.session_token = response.data["session"]["session_token"]

    def test_puzzle_requires_session_token(self):
        response = self.client.get(
            "/api/session/puzzle/"
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

    def test_wrong_session_token_is_rejected(self):
        self.client.credentials(
            HTTP_X_SESSION_TOKEN="invalid-session-token"
        )

        response = self.client.get(
            "/api/session/puzzle/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_correct_session_token_returns_public_puzzle(self):
        self.client.credentials(
            HTTP_X_SESSION_TOKEN=self.session_token
        )

        response = self.client.get(
            "/api/session/puzzle/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "public_data",
            response.data,
        )

        self.assertIn(
            "generation_version",
            response.data,
        )

        self.assertIn(
            "id",
            response.data,
        )

        self.assertIn(
            "generated_at",
            response.data,
        )

    def test_secret_data_is_never_returned(self):
        self.client.credentials(
            HTTP_X_SESSION_TOKEN=self.session_token
        )

        response = self.client.get(
            "/api/session/puzzle/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        response_text = str(response.data).lower()

        self.assertNotIn(
            "secret_data",
            response_text,
        )

        self.assertNotIn(
            "correct_nodes",
            response_text,
        )

        self.assertNotIn(
            "correct_order",
            response_text,
        )

        self.assertNotIn(
            "latitude",
            response_text,
        )

        self.assertNotIn(
            "longitude",
            response_text,
        )

    def test_database_still_contains_secret_data(self):
        puzzle = PuzzleInstance.objects.get(
            game_session__id=self.session_id
        )

        self.assertTrue(
            puzzle.secret_data
        )

        self.assertIn(
            "round_1",
            puzzle.secret_data,
        )

        self.assertIn(
            "round_2",
            puzzle.secret_data,
        )