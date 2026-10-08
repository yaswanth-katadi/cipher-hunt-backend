"""
Validation for ClueVerse generated puzzles.

Validation happens before a generated puzzle is stored in the database.
"""

from .round1_solver import solve_round1 as solve_complete_round1
from .round2_solver import solve_round2


def _assert_not_leaked(public_data, forbidden_terms):
    public_text = str(public_data).lower()

    for term in forbidden_terms:
        if term.lower() in public_text:
            raise ValueError(
                f"SECURITY ERROR: {term} leaked into public data."
            )


def validate_round1(puzzle):
    if not isinstance(puzzle, dict):
        raise ValueError("Round 1 puzzle must be a dictionary.")

    if "public" not in puzzle:
        raise ValueError("Round 1 public data is missing.")

    if "secret" not in puzzle:
        raise ValueError("Round 1 secret data is missing.")

    public_data = puzzle["public"]
    secret_data = puzzle["secret"]

    node_map = public_data["map"]["nodes"]
    correct_nodes = secret_data["correct_nodes"]
    correct_order = secret_data["correct_order"]
    latitude = secret_data["latitude"]

    if len(node_map) != 9:
        raise ValueError("Round 1 must contain exactly 9 nodes.")

    node_ids = [node["node"] for node in node_map]

    if sorted(node_ids) != list(range(1, 10)):
        raise ValueError(
            "Round 1 nodes must contain exactly 1 through 9."
        )

    if len(correct_nodes) != 4:
        raise ValueError(
            "Round 1 must contain exactly four correct nodes."
        )

    if len(set(correct_nodes)) != 4:
        raise ValueError(
            "Round 1 correct nodes must be unique."
        )

    if not set(correct_nodes).issubset(set(node_ids)):
        raise ValueError(
            "Round 1 correct nodes must exist on the map."
        )

    if len(correct_order) != 4:
        raise ValueError(
            "Round 1 correct order must contain four nodes."
        )

    if len(set(correct_order)) != 4:
        raise ValueError(
            "Round 1 correct order must contain unique nodes."
        )

    if sorted(correct_order) != sorted(correct_nodes):
        raise ValueError(
            "Round 1 correct order must contain the same nodes as correct_nodes."
        )

    if not isinstance(latitude, dict):
        raise ValueError(
            "Round 1 latitude must be a dictionary."
        )

    required_latitude_fields = {
        "decimal",
        "degrees",
        "minutes",
        "hemisphere",
    }

    if not required_latitude_fields.issubset(latitude):
        raise ValueError(
            "Round 1 latitude is missing required fields."
        )

    if latitude["hemisphere"] not in {"N", "S"}:
        raise ValueError(
            "Round 1 latitude hemisphere must be N or S."
        )

    if not 0 <= latitude["minutes"] <= 59:
        raise ValueError(
            "Round 1 latitude minutes must be between 0 and 59."
        )

    # Independently solve the public puzzle.
    result = solve_complete_round1(public_data)

    if result["correct_nodes"] != correct_nodes:
        raise ValueError(
            "Round 1 independent solver does not match generated nodes."
        )

    if result["correct_order"] != correct_order:
        raise ValueError(
            "Round 1 independent solver does not match generated order."
        )

    _assert_not_leaked(
        public_data,
        [
            "correct_nodes",
            "correct_order",
            "latitude",
        ],
    )

    return True


def validate_round2(puzzle):
    if not isinstance(puzzle, dict):
        raise ValueError("Round 2 puzzle must be a dictionary.")

    if "public" not in puzzle:
        raise ValueError("Round 2 public data is missing.")

    if "secret" not in puzzle:
        raise ValueError("Round 2 secret data is missing.")

    public_data = puzzle["public"]
    secret_data = puzzle["secret"]

    correct_nodes = secret_data["correct_nodes"]
    correct_order = secret_data["correct_order"]
    longitude = secret_data["longitude"]

    if len(correct_nodes) != 4:
        raise ValueError(
            "Round 2 must contain exactly four correct nodes."
        )

    if len(set(correct_nodes)) != 4:
        raise ValueError(
            "Round 2 correct nodes must be unique."
        )

    if not set(correct_nodes).issubset(set(range(1, 10))):
        raise ValueError(
            "Round 2 contains an invalid node."
        )

    if len(correct_order) != 4:
        raise ValueError(
            "Round 2 correct order must contain four nodes."
        )

    if len(set(correct_order)) != 4:
        raise ValueError(
            "Round 2 correct order must contain unique nodes."
        )

    if sorted(correct_order) != sorted(correct_nodes):
        raise ValueError(
            "Round 2 correct order must contain the same nodes as correct_nodes."
        )

    if not isinstance(longitude, dict):
        raise ValueError(
            "Round 2 longitude must be a dictionary."
        )

    required_longitude_fields = {
        "decimal",
        "degrees",
        "minutes",
        "hemisphere",
    }

    if not required_longitude_fields.issubset(longitude):
        raise ValueError(
            "Round 2 longitude is missing required fields."
        )

    if longitude["hemisphere"] not in {"E", "W"}:
        raise ValueError(
            "Round 2 longitude hemisphere must be E or W."
        )

    if not 0 <= longitude["minutes"] <= 59:
        raise ValueError(
            "Round 2 longitude minutes must be between 0 and 59."
        )

    # Independently solve the public puzzle.
    result = solve_round2(public_data)

    if result["correct_nodes"] != correct_nodes:
        raise ValueError(
            "Round 2 independent solver does not match generated nodes."
        )

    if result["correct_order"] != correct_order:
        raise ValueError(
            "Round 2 independent solver does not match generated order."
        )

    _assert_not_leaked(
        public_data,
        [
            "correct_nodes",
            "correct_order",
            "longitude",
        ],
    )

    return True


def validate_puzzle(puzzle):
    """
    Validate the complete generated ClueVerse puzzle.
    """

    if not isinstance(puzzle, dict):
        raise ValueError("Puzzle must be a dictionary.")

    if "generation_version" not in puzzle:
        raise ValueError("Puzzle generation version is missing.")

    if "public_data" not in puzzle:
        raise ValueError("Puzzle public data is missing.")

    if "secret_data" not in puzzle:
        raise ValueError("Puzzle secret data is missing.")

    public_data = puzzle["public_data"]
    secret_data = puzzle["secret_data"]

    if "round_1" not in public_data:
        raise ValueError("Round 1 public data is missing.")

    if "round_2" not in public_data:
        raise ValueError("Round 2 public data is missing.")

    if "round_1" not in secret_data:
        raise ValueError("Round 1 secret data is missing.")

    if "round_2" not in secret_data:
        raise ValueError("Round 2 secret data is missing.")

    validate_round1(
        {
            "public": public_data["round_1"],
            "secret": secret_data["round_1"],
        }
    )

    validate_round2(
        {
            "public": public_data["round_2"],
            "secret": secret_data["round_2"],
        }
    )

    return True