from django.test import TestCase
from rest_framework.test import APIClient

from game.models import (
    GameSession,
    PuzzleInstance,
    Registration,
    RoundState,
)


class RegistrationPuzzleCreationTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.payload = {
            "participant_name": "Test Player",
            "email": "testplayer@example.com",
            "college": "NIT Durgapur",
            "game_mode": "single",
            "team_name": "",
            "team_leader_name": "",
        }

    def test_registration_creates_complete_game_session(self):
        response = self.client.post(
            "/api/registration/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(GameSession.objects.count(), 1)
        self.assertEqual(RoundState.objects.count(), 2)
        self.assertEqual(PuzzleInstance.objects.count(), 1)

        registration = Registration.objects.first()
        session = GameSession.objects.first()
        puzzle = PuzzleInstance.objects.first()

        self.assertEqual(session.registration, registration)
        self.assertEqual(puzzle.game_session, session)

        self.assertEqual(
            RoundState.objects.filter(
                game_session=session,
                round_number=1,
            ).count(),
            1,
        )

        self.assertEqual(
            RoundState.objects.filter(
                game_session=session,
                round_number=2,
            ).count(),
            1,
        )

    def test_secret_data_is_not_returned_by_registration_api(self):
        response = self.client.post(
            "/api/registration/",
            {
                **self.payload,
                "email": "secretcheck@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        response_text = str(response.data).lower()

        self.assertNotIn("secret_data", response_text)
        self.assertNotIn("correct_nodes", response_text)
        self.assertNotIn("correct_order", response_text)
        self.assertNotIn("latitude", response_text)
        self.assertNotIn("longitude", response_text)

    def test_two_registrations_get_different_puzzles(self):
        response_1 = self.client.post(
            "/api/registration/",
            self.payload,
            format="json",
        )

        response_2 = self.client.post(
            "/api/registration/",
            {
                **self.payload,
                "email": "secondplayer@example.com",
            },
            format="json",
        )

        self.assertEqual(response_1.status_code, 201)
        self.assertEqual(response_2.status_code, 201)

        puzzles = list(
            PuzzleInstance.objects.order_by("generated_at")
        )

        self.assertEqual(len(puzzles), 2)

        puzzle_1 = puzzles[0]
        puzzle_2 = puzzles[1]

        self.assertNotEqual(
            puzzle_1.id,
            puzzle_2.id,
        )

        self.assertNotEqual(
            puzzle_1.secret_data,
            puzzle_2.secret_data,
        )