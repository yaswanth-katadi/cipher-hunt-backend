"""
Independent solver for ClueVerse Round 2.

IMPORTANT:
This solver uses ONLY public_data.

It never reads secret_data.
"""

ALL_NODES = set(range(1, 10))


def _count_emojis(emoji_text):
    """
    Emojis are separated by spaces in the generated evidence.
    """

    return len(
        emoji_text.split()
    )


def _extract_letter(word, position):
    """
    Extract a 1-based character from a word.
    """

    if position < 1:
        raise ValueError(
            "Character position must be positive."
        )

    if position > len(word):
        raise ValueError(
            f"Position {position} exceeds "
            f"word length for {word!r}."
        )

    return word[position - 1]


def solve_round2(public_data):
    """
    Solve the Round 2 public puzzle.

    Returns:

    {
        "extracted_letters": [...],
        "correct_nodes": [...],
        "correct_order": [...]
    }
    """

    clues = public_data["clues"]
    letter_to_node = public_data["letter_to_node"]

    if len(clues) != 4:
        raise ValueError(
            "Round 2 must contain exactly four clues."
        )

    extracted_letters = []

    for clue in clues:

        emoji_count = _count_emojis(
            clue["emoji_text"]
        )

        letter = _extract_letter(
            clue["display_word"],
            emoji_count,
        )

        extracted_letters.append(letter)

    if len(set(extracted_letters)) != 4:
        raise ValueError(
            "Extracted letters must be unique."
        )

    try:
        correct_order = [
            letter_to_node[letter]
            for letter in extracted_letters
        ]
    except KeyError as exc:
        raise ValueError(
            f"Missing letter mapping for {exc.args[0]!r}."
        ) from exc

    if len(correct_order) != 4:
        raise ValueError(
            "Exactly four nodes are required."
        )

    if len(set(correct_order)) != 4:
        raise ValueError(
            "Round 2 nodes must be unique."
        )

    if not set(correct_order).issubset(ALL_NODES):
        raise ValueError(
            "Round 2 contains an invalid node."
        )

    return {
        "extracted_letters": extracted_letters,
        "correct_nodes": sorted(correct_order),
        "correct_order": correct_order,
    }