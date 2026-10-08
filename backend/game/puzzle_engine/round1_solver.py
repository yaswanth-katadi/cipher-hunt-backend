"""
Independent solver for ClueVerse Round 1.

This solver uses ONLY public puzzle data.

It never reads secret_data.
"""

import itertools


ALL_NODES = set(range(1, 10))


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


def _find_node_solutions(
    node_map,
    constraints,
):
    """
    Independently find all four-node solutions.
    """

    solutions = []

    for combination in itertools.combinations(
        node_map,
        4,
    ):
        valid = True

        for constraint in constraints:
            for node in combination:
                if not _matches_constraint(
                    node,
                    constraint,
                ):
                    valid = False
                    break

            if not valid:
                break

        if valid:
            solutions.append(
                sorted(
                    node["node"]
                    for node in combination
                )
            )

    return solutions


def _time_to_minutes(time_text):
    """
    Convert HH:MM into minutes from midnight.
    """

    hours, minutes = (
        int(part)
        for part in time_text.split(":")
    )

    return (
        hours * 60
        + minutes
    )


def solve_round1(public_data):
    """
    Solve the complete Round 1 puzzle.

    Returns:

    {
        "correct_nodes": [...],
        "correct_order": [...]
    }
    """

    node_map = public_data["map"]["nodes"]

    clues = public_data["clues"]

    constraints = [
        clue["constraint"]
        for clue in clues
        if "constraint" in clue
    ]

    if not constraints:
        raise ValueError(
            "Round 1 contains no solvable constraints."
        )

    solutions = _find_node_solutions(
        node_map,
        constraints,
    )

    if len(solutions) != 1:
        raise ValueError(
            "Round 1 must have exactly one "
            f"four-node solution, found {len(solutions)}."
        )

    correct_nodes = solutions[0]

    target_records = [
        node
        for node in node_map
        if node["node"] in correct_nodes
    ]

    if len(target_records) != 4:
        raise ValueError(
            "Round 1 solution must contain four nodes."
        )

    ordering_rule = public_data.get(
        "ordering_rule"
    )

    if not ordering_rule:
        raise ValueError(
            "Round 1 ordering rule is missing."
        )

    if ordering_rule.get("type") != "time_ascending":
        raise ValueError(
            "Unsupported Round 1 ordering rule."
        )

    times = [
        node["time"]
        for node in target_records
    ]

    if len(set(times)) != 4:
        raise ValueError(
            "Round 1 target nodes must have "
            "unique recorded times."
        )

    ordered_records = sorted(
        target_records,
        key=lambda node: _time_to_minutes(
            node["time"]
        ),
    )

    correct_order = [
        node["node"]
        for node in ordered_records
    ]

    if len(correct_order) != 4:
        raise ValueError(
            "Round 1 order must contain four nodes."
        )

    if len(set(correct_order)) != 4:
        raise ValueError(
            "Round 1 order contains duplicate nodes."
        )

    if not set(correct_order).issubset(
        ALL_NODES
    ):
        raise ValueError(
            "Round 1 contains an invalid node."
        )

    return {
        "correct_nodes": correct_nodes,
        "correct_order": correct_order,
    }