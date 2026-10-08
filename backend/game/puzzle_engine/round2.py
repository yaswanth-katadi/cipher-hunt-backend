"""
ClueVerse Round 2 generator.

Round 2 workflow:

Emoji count
    ↓
Character position in displayed word
    ↓
Extracted letter
    ↓
Letter-to-node mapping
    ↓
Four nodes
    ↓
Extraction order becomes Stage 2 order
    ↓
Longitude

Secret answers are never placed in public_data.
"""

import random


ALL_NODES = tuple(range(1, 10))

EMOJI_POOL = [
    "🔑",
    "🔦",
    "📷",
    "🧤",
    "📻",
    "🔋",
    "🧰",
    "🎥",
    "🚗",
    "🏃",
    "🚨",
    "🕵️",
]

WORD_POOL = [
    "CAMERA",
    "GARAGE",
    "WORKSHOP",
    "FLASHLIGHT",
    "BLUEPRINT",
    "KEYRING",
    "TOOLBOX",
    "EVIDENCE",
    "BACKDOOR",
    "ALIBI",
    "SUSPECT",
    "VEHICLE",
    "WITNESS",
    "FOOTPRINT",
    "SECURITY",
]


def _extract_letter(word, position):
    """
    Extract a character using a 1-based position.
    """

    if position < 1 or position > len(word):
        raise ValueError(
            f"Position {position} is invalid for word {word!r}."
        )

    return word[position - 1]


def _build_emoji_sequence(count, emoji):
    """
    Build the visible emoji evidence.
    """

    return " ".join([emoji] * count)


def _build_clue(rng, clue_number):
    """
    Build one public evidence clue.

    The player must count the visible emojis.
    """

    word = rng.choice(WORD_POOL)

    position = rng.randint(
        1,
        min(len(word), 9),
    )

    emoji = rng.choice(EMOJI_POOL)

    emoji_text = _build_emoji_sequence(
        position,
        emoji,
    )

    extracted_letter = _extract_letter(
        word,
        position,
    )

    return {
        "id": f"r2-clue-{clue_number}",
        "tag": "EVIDENCE",
        "emoji_text": emoji_text,
        "display_word": word,
        "extracted_letter": extracted_letter,
        "position": position,
    }


def _build_letter_mapping(target_letters, target_nodes, rng):
    """
    Build the public letter → node mapping.

    Four extracted letters receive the four target nodes.

    Five additional letters receive the remaining five nodes
    and act as decoys.
    """

    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    required_letters = list(target_letters)

    available_letters = [
        letter
        for letter in alphabet
        if letter not in required_letters
    ]

    remaining_nodes = [
        node
        for node in ALL_NODES
        if node not in target_nodes
    ]

    rng.shuffle(remaining_nodes)

    mapping = {}

    # Real mappings.
    for letter, node in zip(
        required_letters,
        target_nodes,
    ):
        mapping[letter] = node

    # Five decoy mappings.
    decoy_letters = rng.sample(
        available_letters,
        5,
    )

    for letter, node in zip(
        decoy_letters,
        remaining_nodes,
    ):
        mapping[letter] = node

    return mapping


def _generate_longitude(rng):
    """
    Generate longitude in degree/minute/hemisphere form.

    Decimal longitude remains server-side.
    """

    degrees = rng.randint(1, 179)
    minutes = rng.randint(0, 59)
    hemisphere = rng.choice(["E", "W"])

    decimal_value = degrees + (
        minutes / 60
    )

    if hemisphere == "W":
        decimal_value *= -1

    return {
        "decimal": round(decimal_value, 6),
        "degrees": degrees,
        "minutes": minutes,
        "hemisphere": hemisphere,
    }


def generate_round2(
    rng=None,
    max_attempts=500,
):
    """
    Generate one valid Round 2 puzzle.
    """

    rng = rng or random.SystemRandom()

    for _ in range(max_attempts):

        # ---------------------------------------------------------
        # 1. Generate four clues.
        # ---------------------------------------------------------

        clues = [
            _build_clue(
                rng,
                clue_number=index + 1,
            )
            for index in range(4)
        ]

        # ---------------------------------------------------------
        # 2. Extracted letters must be unique.
        # ---------------------------------------------------------

        extracted_letters = [
            clue["extracted_letter"]
            for clue in clues
        ]

        if len(set(extracted_letters)) != 4:
            continue

        # ---------------------------------------------------------
        # 3. Choose FOUR UNIQUE nodes in RANDOM ORDER.
        #
        # IMPORTANT:
        # Do NOT sort these.
        #
        # Their order becomes the correct Stage 2 trail.
        # ---------------------------------------------------------

        target_nodes = rng.sample(
            list(ALL_NODES),
            4,
        )

        # ---------------------------------------------------------
        # 4. Build letter → node mapping.
        #
        # Because target_nodes is random-order:
        #
        # clue 1 letter → target_nodes[0]
        # clue 2 letter → target_nodes[1]
        # clue 3 letter → target_nodes[2]
        # clue 4 letter → target_nodes[3]
        #
        # Therefore the extraction sequence itself determines
        # the correct Stage 2 order.
        # ---------------------------------------------------------

        letter_mapping = _build_letter_mapping(
            extracted_letters,
            target_nodes,
            rng,
        )

        # ---------------------------------------------------------
        # 5. Generate longitude.
        # ---------------------------------------------------------

        longitude = _generate_longitude(rng)

        # ---------------------------------------------------------
        # PUBLIC DATA
        # ---------------------------------------------------------

        public_clues = [
            {
                "id": clue["id"],
                "tag": clue["tag"],
                "emoji_text": clue["emoji_text"],
                "display_word": clue["display_word"],
            }
            for clue in clues
        ]

        public_data = {
            "round": 2,
            "title": "The Ciphered Trail",
            "objective": (
                "Decode the evidence, identify four nodes, "
                "then trace the thief's route."
            ),
            "instructions": [
                "Count the emojis in each evidence line.",
                "Use that count as the character position "
                "in the displayed word.",
                "Extract the resulting letters.",
                "Use the letter-to-node evidence to identify "
                "the four nodes.",
                "Trace the four nodes in the same order "
                "as the four extracted clues.",
            ],
            "clues": public_clues,
            "letter_to_node": letter_mapping,
            "map": {
                "rows": 3,
                "columns": 3,
                "nodes": [
                    {"node": node}
                    for node in ALL_NODES
                ],
            },
        }

        # ---------------------------------------------------------
        # SECRET DATA
        # ---------------------------------------------------------

        secret_data = {
            "extracted_letters": extracted_letters,
            "correct_nodes": sorted(target_nodes),
            "correct_order": target_nodes,
            "longitude": longitude,
        }

        return {
            "public": public_data,
            "secret": secret_data,
        }

    raise RuntimeError(
        "Unable to generate a valid Round 2 puzzle "
        f"after {max_attempts} attempts."
    )