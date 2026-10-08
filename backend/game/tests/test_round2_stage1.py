from django.test import TestCase
from rest_framework.test import APIClient

from game.models import Attempt, GameSession, RoundState


class Round2Stage1Tests(TestCase):

    def setUp(self):
        self.client = APIClient()

        payload = {
            "participant_name": "Round Two Player",
            "email": "round-two@example.com",
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

        self.round_1_correct_nodes = (
            self.puzzle.secret_data[
                "round_1"
            ]["correct_nodes"]
        )

        self.round_1_correct_order = (
            self.puzzle.secret_data[
                "round_1"
            ]["correct_order"]
        )

        # Solve Round 1 Stage 1.
        stage_1_response = self.client.post(
            "/api/session/round-1/stage-1/",
            {
                "selected_nodes": (
                    self.round_1_correct_nodes
                )
            },
            format="json",
        )

        self.assertEqual(
            stage_1_response.status_code,
            200,
        )

        self.assertTrue(
            stage_1_response.data["solved"]
        )

        # Solve Round 1 Stage 2.
        stage_2_response = self.client.post(
            "/api/session/round-1/stage-2/",
            {
                "selected_order": (
                    self.round_1_correct_order
                )
            },
            format="json",
        )

        self.assertEqual(
            stage_2_response.status_code,
            200,
        )

        self.assertTrue(
            stage_2_response.data["solved"]
        )

        self.round_2.refresh_from_db()

        self.assertEqual(
            self.round_2.status,
            RoundState.Status.ACTIVE,
        )

        self.round_2_correct_nodes = (
            self.puzzle.secret_data[
                "round_2"
            ]["correct_nodes"]
        )

    def test_round_2_stage_1_accepts_four_nodes(self):
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

        self.assertTrue(
            response.data["solved"]
        )

    def test_round_2_stage_1_attempt_is_recorded(self):
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

        self.round_2.refresh_from_db()

        self.assertEqual(
            self.round_2.attempts_count,
            1,
        )

        self.assertEqual(
            Attempt.objects.filter(
                round_state=self.round_2,
                stage=Attempt.Stage.STAGE_1,
            ).count(),
            1,
        )

    def test_duplicate_nodes_are_rejected(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": [
                    1,
                    2,
                    2,
                    4,
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            Attempt.objects.filter(
                round_state=self.round_2,
                stage=Attempt.Stage.STAGE_1,
            ).count(),
            0,
        )

    def test_wrong_number_of_nodes_is_rejected(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": [
                    1,
                    2,
                    3,
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            Attempt.objects.filter(
                round_state=self.round_2,
                stage=Attempt.Stage.STAGE_1,
            ).count(),
            0,
        )

    def test_round_2_cannot_be_used_before_round_1(self):
        # Create a completely fresh session.
        client = APIClient()

        payload = {
            "participant_name": "Locked Round Player",
            "email": "locked-round@example.com",
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

        client.post(
            "/api/session/start/",
            {},
            format="json",
        )

        response = client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": [1, 2, 3, 4]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

    def test_response_does_not_reveal_correct_nodes(self):
        response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": [
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

    def test_multiple_attempts_are_allowed(self):
        first_nodes = [
            1,
            2,
            3,
            4,
        ]

        second_nodes = [
            5,
            6,
            7,
            8,
        ]

        first_response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": first_nodes
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            200,
        )

        # If the first attempt happened to solve the puzzle,
        # a second submission is correctly blocked.
        if first_response.data["solved"]:
            return

        second_response = self.client.post(
            "/api/session/round-2/stage-1/",
            {
                "selected_nodes": second_nodes
            },
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            200,
        )

        self.round_2.refresh_from_db()

        self.assertEqual(
            self.round_2.attempts_count,
            2,
        )
        