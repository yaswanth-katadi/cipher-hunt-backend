from django.test import TestCase
from rest_framework.test import APIClient

from game.models import Attempt, GameSession, RoundState


class Round1Stage2Tests(TestCase):

    def setUp(self):
        self.client = APIClient()

        payload = {
            "participant_name": "Stage Two Player",
            "email": "stage-two@example.com",
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

        self.puzzle = self.game_session.puzzle

        self.correct_nodes = (
            self.puzzle.secret_data[
                "round_1"
            ]["correct_nodes"]
        )

        self.correct_order = (
            self.puzzle.secret_data[
                "round_1"
            ]["correct_order"]
        )

        stage_1_response = self.client.post(
            "/api/session/round-1/stage-1/",
            {
                "selected_nodes": self.correct_nodes
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

    def test_correct_order_solves_round_one(self):
        response = self.client.post(
            "/api/session/round-1/stage-2/",
            {
                "selected_order": self.correct_order
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

        self.assertEqual(
            response.data["next_round"],
            2,
        )

        self.round_1.refresh_from_db()

        self.assertEqual(
            self.round_1.status,
            RoundState.Status.SOLVED,
        )

        self.assertIsNotNone(
            self.round_1.solved_at
        )

        self.assertIsNotNone(
            self.round_1.elapsed_ms
        )

    def test_wrong_order_does_not_solve_round_one(self):
        wrong_order = list(
            reversed(self.correct_order)
        )

        if wrong_order == self.correct_order:
            wrong_order = (
                self.correct_order[1:]
                + self.correct_order[:1]
            )

        response = self.client.post(
            "/api/session/round-1/stage-2/",
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

        self.round_1.refresh_from_db()

        self.assertEqual(
            self.round_1.status,
            RoundState.Status.ACTIVE,
        )

        self.assertEqual(
            self.round_1.attempts_count,
            2,
        )

    def test_stage_two_requires_stage_one(self):
        self.client = APIClient()

        payload = {
            "participant_name": "No Stage One",
            "email": "no-stage-one@example.com",
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

        token = response.data[
            "session"
        ]["session_token"]

        self.client.credentials(
            HTTP_X_SESSION_TOKEN=token
        )

        self.client.post(
            "/api/session/start/",
            {},
            format="json",
        )

        session = GameSession.objects.get(
            session_token=token
        )

        puzzle = session.puzzle

        correct_order = (
            puzzle.secret_data[
                "round_1"
            ]["correct_order"]
        )

        response = self.client.post(
            "/api/session/round-1/stage-2/",
            {
                "selected_order": correct_order
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

    def test_duplicate_nodes_are_rejected(self):
        response = self.client.post(
            "/api/session/round-1/stage-2/",
            {
                "selected_order": [
                    self.correct_order[0],
                    self.correct_order[1],
                    self.correct_order[1],
                    self.correct_order[3],
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.round_1.refresh_from_db()

        self.assertEqual(
            self.round_1.attempts_count,
            1,
        )

    def test_wrong_number_of_nodes_is_rejected(self):
        response = self.client.post(
            "/api/session/round-1/stage-2/",
            {
                "selected_order": self.correct_order[:3]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.round_1.refresh_from_db()

        self.assertEqual(
            self.round_1.attempts_count,
            1,
        )

    def test_stage_two_cannot_use_nodes_outside_stage_one(self):
        outside_node = next(
            node
            for node in range(1, 10)
            if node not in self.correct_nodes
        )

        invalid_order = list(
            self.correct_order
        )

        invalid_order[0] = outside_node

        response = self.client.post(
            "/api/session/round-1/stage-2/",
            {
                "selected_order": invalid_order
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.round_1.refresh_from_db()

        self.assertEqual(
            self.round_1.attempts_count,
            1,
        )

    def test_response_does_not_reveal_correct_order(self):
        response = self.client.post(
            "/api/session/round-1/stage-2/",
            {
                "selected_order": self.correct_order
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
            "correct_order",
            response_text,
        )

        self.assertNotIn(
            str(self.correct_order),
            response_text,
        )