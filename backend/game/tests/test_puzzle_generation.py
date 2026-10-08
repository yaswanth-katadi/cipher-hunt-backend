from django.test import SimpleTestCase

from game.puzzle_engine.generator import generate_puzzle
from game.puzzle_engine.solver import solve_round1
from game.puzzle_engine.round1_solver import solve_round1 as solve_complete_round1
from game.puzzle_engine.round2 import generate_round2
from game.puzzle_engine.round2_solver import solve_round2


class PuzzleGenerationTests(SimpleTestCase):

    def test_500_round1_puzzles_are_uniquely_solvable(self):
        for index in range(500):
            puzzle = generate_puzzle()

            public_data = puzzle["public_data"]["round_1"]
            secret_data = puzzle["secret_data"]["round_1"]

            # Stage 1: independently solve the four-node set.
            solutions = solve_round1(public_data)

            self.assertEqual(
                len(solutions),
                1,
                f"Round 1 puzzle {index + 1} has "
                f"{len(solutions)} solutions.",
            )

            self.assertEqual(
                solutions[0],
                secret_data["correct_nodes"],
                f"Round 1 puzzle {index + 1} node solution "
                f"does not match the secret.",
            )

            # Complete Round 1: independently solve node order.
            result = solve_complete_round1(public_data)

            self.assertEqual(
                result["correct_nodes"],
                secret_data["correct_nodes"],
                f"Round 1 puzzle {index + 1} complete node "
                f"solution does not match the secret.",
            )

            self.assertEqual(
                result["correct_order"],
                secret_data["correct_order"],
                f"Round 1 puzzle {index + 1} order does not "
                f"match the secret.",
            )

            # Correct order must contain exactly four unique nodes.
            self.assertEqual(
                len(result["correct_order"]),
                4,
                f"Round 1 puzzle {index + 1} does not have "
                f"four ordered nodes.",
            )

            self.assertEqual(
                len(set(result["correct_order"])),
                4,
                f"Round 1 puzzle {index + 1} contains "
                f"duplicate ordered nodes.",
            )

            # Latitude must exist only in secret data.
            self.assertIn(
                "latitude",
                secret_data,
            )

            self.assertNotIn(
                "latitude",
                str(public_data).lower(),
                f"Round 1 puzzle {index + 1} leaks latitude.",
            )

            # Other secret values must not leak.
            self.assertNotIn(
                "correct_nodes",
                str(public_data),
                f"Round 1 puzzle {index + 1} leaks correct_nodes.",
            )

            self.assertNotIn(
                "correct_order",
                str(public_data),
                f"Round 1 puzzle {index + 1} leaks correct_order.",
            )

    def test_500_round2_puzzles_are_uniquely_solvable(self):
        for index in range(500):
            puzzle = generate_round2()

            public_data = puzzle["public"]
            secret_data = puzzle["secret"]

            result = solve_round2(public_data)

            self.assertEqual(
                len(result["correct_order"]),
                4,
                f"Round 2 puzzle {index + 1} does not have "
                f"exactly four ordered nodes.",
            )

            self.assertEqual(
                len(set(result["correct_order"])),
                4,
                f"Round 2 puzzle {index + 1} contains "
                f"duplicate nodes.",
            )

            self.assertEqual(
                result["correct_nodes"],
                secret_data["correct_nodes"],
                f"Round 2 puzzle {index + 1} node solution "
                f"does not match the secret.",
            )

            self.assertEqual(
                result["correct_order"],
                secret_data["correct_order"],
                f"Round 2 puzzle {index + 1} order solution "
                f"does not match the secret.",
            )

            self.assertNotIn(
                "correct_nodes",
                str(public_data),
                f"Round 2 puzzle {index + 1} leaks correct_nodes.",
            )

            self.assertNotIn(
                "correct_order",
                str(public_data),
                f"Round 2 puzzle {index + 1} leaks correct_order.",
            )

            self.assertNotIn(
                "longitude",
                str(public_data).lower(),
                f"Round 2 puzzle {index + 1} leaks longitude.",
            )