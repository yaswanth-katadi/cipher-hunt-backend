"""
ClueVerse Round 1 generator.

Round 1 workflow:

Workshop evidence
    ↓
Identify four nodes
    ↓
Stage 1
    ↓
Use the recorded-time ordering evidence
    ↓
Trace the four nodes chronologically
    ↓
Latitude

Secret answers are never placed in public_data.
"""

import random

from .datasets import (
    CCTV_STATUS,
    EVIDENCE_TAGS,
    OBJECTS,
    SHIFT_TIMES,
    WORKSHOPS,
    ZONES,
)


ALL_NODES = tuple(range(1, 10))


def _node_position(node):
    row = (node - 1) // 3 + 1
    column = (node - 1) % 3 + 1
    return row, column


def _build_node(node, rng):
    row, column = _node_position(node)

    return {
        "node": node,
        "row": row,
        "column": column,
        "object": rng.choice(OBJECTS),
        "zone": rng.choice(ZONES),
        "cctv": rng.choice(CCTV_STATUS),
        "time": rng.choice(SHIFT_TIMES),
        "evidence_tag": rng.choice(EVIDENCE_TAGS),
    }


def _build_map(rng):
    return [
        _build_node(node, rng)
        for node in ALL_NODES
    ]


def _matches_constraint(node, constraint):
    attribute = constraint["attribute"]
    operator = constraint["operator"]
    value = constraint["value"]

    actual = node[attribute]

    if operator == "equals":
        return actual == value

    if operator == "not_equals":
        return actual != value

    if operator == "in":
        return actual in value

    if operator == "not_in":
        return actual not in value

    raise ValueError(
        f"Unknown constraint operator: {operator}"
    )


def _solve_candidates(node_map, constraints):
    """
    Find every four-node combination satisfying
    all generated constraints.
    """

    import itertools

    valid_solutions = []

    for combination in itertools.combinations(
        node_map,
        4,
    ):
        if all(
            all(
                _matches_constraint(
                    node,
                    constraint,
                )
                for node in combination
            )
            for constraint in constraints
        ):
            valid_solutions.append(
                sorted(
                    node["node"]
                    for node in combination
                )
            )

    return valid_solutions


def _candidate_constraints(
    node_map,
    target_nodes,
):
    """
    Create public evidence constraints from the
    selected target nodes.

    The generated constraints must isolate exactly
    one four-node solution.
    """

    target_records = [
        node
        for node in node_map
        if node["node"] in target_nodes
    ]

    constraints = []

    target_objects = sorted(
        {
            node["object"]
            for node in target_records
        }
    )

    if len(target_objects) > 1:
        constraints.append(
            {
                "attribute": "object",
                "operator": "in",
                "value": target_objects,
            }
        )

    target_zones = sorted(
        {
            node["zone"]
            for node in target_records
        }
    )

    if len(target_zones) > 1:
        constraints.append(
            {
                "attribute": "zone",
                "operator": "in",
                "value": target_zones,
            }
        )

    target_cctv = sorted(
        {
            node["cctv"]
            for node in target_records
        }
    )

    if len(target_cctv) > 1:
        constraints.append(
            {
                "attribute": "cctv",
                "operator": "in",
                "value": target_cctv,
            }
        )

    target_times = sorted(
        {
            node["time"]
            for node in target_records
        }
    )

    if len(target_times) > 1:
        constraints.append(
            {
                "attribute": "time",
                "operator": "in",
                "value": target_times,
            }
        )

    return constraints


def _constraint_text(constraint):
    attribute = constraint["attribute"]
    operator = constraint["operator"]
    value = constraint["value"]

    labels = {
        "object": "equipment",
        "zone": "workshop zone",
        "cctv": "CCTV status",
        "time": "recorded time",
    }

    label = labels[attribute]

    if operator == "in":
        values = ", ".join(
            str(item)
            for item in value
        )

        return (
            f"The four relevant locations must match "
            f"the recorded {label} evidence: {values}."
        )

    if operator == "equals":
        return (
            f"The four relevant locations have "
            f"{label}: {value}."
        )

    if operator == "not_equals":
        return (
            f"Exclude locations with "
            f"{label}: {value}."
        )

    if operator == "not_in":
        values = ", ".join(
            str(item)
            for item in value
        )

        return (
            f"Exclude locations with "
            f"{label}: {values}."
        )

    raise ValueError(
        f"Unknown constraint operator: {operator}"
    )


def _generate_latitude(rng):
    """
    Generate latitude in degree/minute/hemisphere form.

    Decimal latitude remains server-side.
    """

    degrees = rng.randint(
        1,
        89,
    )

    minutes = rng.randint(
        0,
        59,
    )

    hemisphere = rng.choice(
        ["N", "S"]
    )

    decimal_value = (
        degrees
        + minutes / 60
    )

    if hemisphere == "S":
        decimal_value *= -1

    return {
        "decimal": round(
            decimal_value,
            6,
        ),
        "degrees": degrees,
        "minutes": minutes,
        "hemisphere": hemisphere,
    }


def generate_round1(
    rng=None,
    max_attempts=500,
):
    """
    Generate one valid Round 1 puzzle.
    """

    rng = rng or random.SystemRandom()

    for _ in range(max_attempts):

        # ---------------------------------------------------------
        # 1. Build the 3x3 workshop map.
        # ---------------------------------------------------------

        node_map = _build_map(rng)

        # ---------------------------------------------------------
        # 2. Choose four target nodes.
        # ---------------------------------------------------------

        target_nodes = sorted(
            rng.sample(
                list(ALL_NODES),
                4,
            )
        )

        target_records = [
            node
            for node in node_map
            if node["node"] in target_nodes
        ]

        # ---------------------------------------------------------
        # 3. The Stage 2 ordering rule requires unique times.
        # ---------------------------------------------------------

        target_times = [
            node["time"]
            for node in target_records
        ]

        if len(set(target_times)) != 4:
            continue

        # ---------------------------------------------------------
        # 4. Generate constraints.
        # ---------------------------------------------------------

        constraints = _candidate_constraints(
            node_map,
            target_nodes,
        )

        if not constraints:
            continue

        # ---------------------------------------------------------
        # 5. Independently check uniqueness inside generator.
        # ---------------------------------------------------------

        solutions = _solve_candidates(
            node_map,
            constraints,
        )

        if len(solutions) != 1:
            continue

        if solutions[0] != target_nodes:
            continue

        # ---------------------------------------------------------
        # 6. Stage 2 order:
        #
        # earliest recorded time → latest recorded time
        # ---------------------------------------------------------

        ordered_records = sorted(
            target_records,
            key=lambda node: node["time"],
        )

        correct_order = [
            node["node"]
            for node in ordered_records
        ]

        if len(correct_order) != 4:
            continue

        if len(set(correct_order)) != 4:
            continue

        # ---------------------------------------------------------
        # 7. Generate latitude.
        # ---------------------------------------------------------

        latitude = _generate_latitude(rng)

        # ---------------------------------------------------------
        # 8. Select workshop context.
        # ---------------------------------------------------------

        workshop = rng.choice(
            WORKSHOPS
        )

        # ---------------------------------------------------------
        # PUBLIC DATA
        # ---------------------------------------------------------

        public_data = {
            "round": 1,
            "title": "The Workshop Trail",
            "objective": (
                "Identify the four workshop locations "
                "connected to the thief's route."
            ),
            "workshop": {
                "name": workshop["name"],
                "description": workshop["description"],
            },
            "instructions": [
                (
                    "Use the workshop evidence to identify "
                    "the four relevant locations."
                ),
                (
                    "After identifying the four locations, "
                    "trace them from the earliest recorded "
                    "time to the latest."
                ),
            ],
            "map": {
                "rows": 3,
                "columns": 3,
                "nodes": node_map,
            },
            "clues": [
                {
                    "id": (
                        f"r1-clue-{index + 1}"
                    ),
                    "tag": (
                        EVIDENCE_TAGS[
                            index
                            % len(EVIDENCE_TAGS)
                        ]
                    ),
                    "text": _constraint_text(
                        constraint
                    ),
                    "constraint": constraint,
                }
                for index, constraint
                in enumerate(constraints)
            ],
            "ordering_rule": {
                "type": "time_ascending",
                "label": (
                    "Trace the four locations "
                    "from earliest to latest "
                    "recorded time."
                ),
            },
        }

        # ---------------------------------------------------------
        # SECRET DATA
        # ---------------------------------------------------------

        secret_data = {
            "correct_nodes": target_nodes,
            "correct_order": correct_order,
            "latitude": latitude,
        }

        return {
            "public": public_data,
            "secret": secret_data,
        }

    raise RuntimeError(
        "Unable to generate a valid Round 1 puzzle "
        f"after {max_attempts} attempts."
    )