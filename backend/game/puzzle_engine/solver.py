"""
Independent solver for ClueVerse Round 1.

IMPORTANT:
This solver uses ONLY public puzzle data.

It must never read:
- secret_data
- correct_nodes
- correct_order
- coordinates
- generation seed
"""

import itertools


ALL_NODES = tuple(range(1, 10))


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

    raise ValueError(f"Unknown constraint operator: {operator}")


def solve_round1(public_data):
    """
    Return every four-node solution that satisfies all public clues.

    Example:
        [[2, 4, 5, 9]]
    """

    node_map = public_data["map"]["nodes"]
    constraints = []

    for clue in public_data["clues"]:
        constraint = clue.get("constraint")

        if constraint is not None:
            constraints.append(constraint)

    solutions = []

    for combination in itertools.combinations(node_map, 4):
        valid = True

        for constraint in constraints:
            if not all(
                _matches_constraint(node, constraint)
                for node in combination
            ):
                valid = False
                break

        if valid:
            solutions.append(
                sorted(node["node"] for node in combination)
            )

    return solutions