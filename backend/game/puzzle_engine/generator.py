"""
Main ClueVerse puzzle generator.

One generated puzzle contains:

Round 1
    -> four nodes
    -> correct order
    -> latitude

Round 2
    -> four nodes
    -> correct order
    -> longitude

Secret answers are never intended to be sent directly to the player.
"""

from .round1 import generate_round1
from .round2 import generate_round2
from .validation import validate_puzzle


GENERATION_VERSION = "v4"


def generate_puzzle():
    round1 = generate_round1()
    round2 = generate_round2()

    puzzle = {
        "generation_version": GENERATION_VERSION,

        "public_data": {
            "round_1": round1["public"],
            "round_2": round2["public"],
        },

        "secret_data": {
            "round_1": round1["secret"],
            "round_2": round2["secret"],
        },
    }

    # Nothing gets stored until the complete puzzle
    # passes independent validation.
    validate_puzzle(puzzle)

    return puzzle