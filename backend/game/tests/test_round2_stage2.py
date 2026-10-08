from django.test import TestCase
from rest_framework.test import APIClient

from game.models import Attempt, GameSession, RoundState


class Round2Stage2Tests(TestCase):

    def setUp(self):
        self.client = APIClient()

        payload = {
            "participant_name": "Round Two Stage Two Player",
            "email": "round-two-stage-two@example.com",
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

        self.assertEqual(
            response.status_code,
            201,
        )

        self.session_token = (
            response.data["session"]["session_token"]
        )

        self.client.credentials(
            HTTP_X_SESSION_TOKEN=self.session_token
        )

        start_response = self.client.post(
            "/api/session/start/",
            {},
            format="json",
        )

        self.assertEqual(
            start_response.status_code,
            200,
        )

        self.game_session = GameSession.objects.get(
            session_token=self.session_token
        )

        self.round_1 = RoundState.objects.get(
            game_session=self.game_session,
            round_number=1,
        )

        self.round_2 = RoundState.objects.get(
            game_session=self.game_session,
            round_number=2,
        )

        self.puzzle = self.game_session.puzzle

        # Get Round 1 secret data for the test only.
        round_1_data = self.puzzle.secret_data[
            "round_1"
        ]

        # Solve Round 1 Stage 1.
        response = self.client.post(
            "/api/session/round-1/stage-1/",
            {
                "selected_nodes": round_1_data[
                    "correct_nodes"
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["solved"]
        )

        # Solve Round 1 Stage 2.
        response = self.client.post(
            "/api/session/round-1/stage-2/",
            {
                "selected_order": round_1_data[
                    "correct_order"
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["solved"]
        )

        # Refresh Round 2 after it has been activated.
        self.round_2.refresh_from_db()

        self.assertEqual(
            self.round_2.status,
            RoundState.Status.ACTIVE,
        )

        # Get Round 2 secret data for the test only.
        round_2_data = self.puzzle.secret_data[
            "round_2"
        ]

        self.round_2_correct_nodes = (
            round_2_data["correct_nodes"]
        )

        self.round_2_correct_order = (
            round_2_data["correct_order"]
        )

        self.expected_longitude = (
            round_2_data["longitude"]
        )

    def test_correct_order_completes_game(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": (
                    self.round_2_correct_nodes
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["solved"]
        )

        response = self.client.post(
            "/api/session/round-2/stage-2/",
            {
                "selected_order": (
                    self.round_2_correct_order
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["correct"]
        )

        self.assertTrue(
            response.data["solved"]
        )

        self.assertTrue(
            response.data["round_completed"]
        )

        self.assertTrue(
            response.data["game_completed"]
        )

        self.assertEqual(
            response.data["longitude"],
            self.expected_longitude,
        )

        self.round_2.refresh_from_db()
        self.game_session.refresh_from_db()

        self.assertEqual(
            self.round_2.status,
            RoundState.Status.SOLVED,
        )

        self.assertIsNotNone(
            self.round_2.solved_at
        )

        self.assertIsNotNone(
            self.round_2.elapsed_ms
        )

        self.assertEqual(
            self.game_session.status,
            GameSession.Status.FINAL,
        )

    def test_wrong_order_does_not_complete_game(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": (
                    self.round_2_correct_nodes
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["solved"]
        )

        wrong_order = list(
            reversed(
                self.round_2_correct_order
            )
        )

        if (
            wrong_order
            == self.round_2_correct_order
        ):
            wrong_order = (
                self.round_2_correct_order[1:]
                + self.round_2_correct_order[:1]
            )

        response = self.client.post(
            "/api/session/round-2/stage-2/",
            {
                "selected_order": wrong_order
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.data["correct"]
        )

        self.assertFalse(
            response.data["solved"]
        )

        self.assertFalse(
            response.data["game_completed"]
        )

        self.assertNotIn(
            "longitude",
            response.data,
        )

        self.round_2.refresh_from_db()
        self.game_session.refresh_from_db()

        self.assertEqual(
            self.round_2.status,
            RoundState.Status.ACTIVE,
        )

        self.assertEqual(
            self.game_session.status,
            GameSession.Status.ROUND_2,
        )

    def test_stage_two_requires_stage_one(self):
        # New independent game session.
        client = APIClient()

        payload = {
            "participant_name": "Stage Two Without Stage One",
            "email": "stage-two-without-stage-one@example.com",
            "college": "NIT Durgapur",
            "game_mode": "single",
            "team_name": "",
            "team_leader_name": "",
        }

        response = client.post(
            "/api/registration/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        token = response.data[
            "session"
        ]["session_token"]

        client.credentials(
            HTTP_X_SESSION_TOKEN=token
        )

        response = client.post(
            "/api/session/start/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        # Round 2 is still locked.
        response = client.post(
            "/api/session/round-2/stage-2/",
            {
                "selected_order": [
                    1,
                    2,
                    3,
                    4,
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

    def test_nodes_must_match_stage_one_nodes(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": (
                    self.round_2_correct_nodes
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["solved"]
        )

        outside_node = next(
            node
            for node in range(1, 10)
            if node not in self.round_2_correct_nodes
        )

        invalid_order = list(
            self.round_2_correct_order
        )

        invalid_order[0] = outside_node

        response = self.client.post(
            "/api/session/round-2/stage-2/",
            {
                "selected_order": invalid_order
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.round_2.refresh_from_db()

        self.assertEqual(
            self.round_2.status,
            RoundState.Status.ACTIVE,
        )

    def test_duplicate_nodes_are_rejected(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": (
                    self.round_2_correct_nodes
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["solved"]
        )

        duplicate_order = [
            self.round_2_correct_order[0],
            self.round_2_correct_order[1],
            self.round_2_correct_order[1],
            self.round_2_correct_order[3],
        ]

        response = self.client.post(
            "/api/session/round-2/stage-2/",
            {
                "selected_order": duplicate_order
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.round_2.refresh_from_db()

        self.assertEqual(
            self.round_2.status,
            RoundState.Status.ACTIVE,
        )

    def test_wrong_number_of_nodes_is_rejected(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": (
                    self.round_2_correct_nodes
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["solved"]
        )

        response = self.client.post(
            "/api/session/round-2/stage-2/",
            {
                "selected_order": (
                    self.round_2_correct_order[:3]
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.round_2.refresh_from_db()

        self.assertEqual(
            self.round_2.status,
            RoundState.Status.ACTIVE,
        )

    def test_wrong_attempt_is_recorded(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": (
                    self.round_2_correct_nodes
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["solved"]
        )

        wrong_order = list(
            reversed(
                self.round_2_correct_order
            )
        )

        if (
            wrong_order
            == self.round_2_correct_order
        ):
            wrong_order = (
                self.round_2_correct_order[1:]
                + self.round_2_correct_order[:1]
            )

        response = self.client.post(
            "/api/session/round-2/stage-2/",
            {
                "selected_order": wrong_order
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.data["correct"]
        )

        self.assertEqual(
            response.data["attempts_count"],
            2,
        )

        self.assertEqual(
            Attempt.objects.filter(
                round_state=self.round_2,
                stage=Attempt.Stage.STAGE_2,
            ).count(),
            1,
        )

    def test_correct_longitude_is_not_revealed_on_wrong_attempt(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": (
                    self.round_2_correct_nodes
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        wrong_order = list(
            reversed(
                self.round_2_correct_order
            )
        )

        if (
            wrong_order
            == self.round_2_correct_order
        ):
            wrong_order = (
                self.round_2_correct_order[1:]
                + self.round_2_correct_order[:1]
            )

        response = self.client.post(
            "/api/session/round-2/stage-2/",
            {
                "selected_order": wrong_order
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "longitude",
            response.data,
        )

        response_text = str(
            response.data
        ).lower()

        self.assertNotIn(
            "correct_order",
            response_text,
        )
        