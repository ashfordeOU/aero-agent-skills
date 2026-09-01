#!/usr/bin/env python3
"""DO-178C requirements-based testing logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, do-178c): requirements-based
testing exercises every software requirement with normal-range and robustness
test cases; structural coverage depth scales with the software level: level A
requires MC/DC, level B decision coverage, level C statement coverage, levels
D and E none. For a compound boolean condition with n independent terms:

- statement coverage needs 1 test case (execute the statement once);
- decision coverage needs 2 (the decision takes both outcomes);
- MC/DC needs n + 1 (every term independently affects the outcome).

Worked anchor examples (verified by scripts/test_software_testing.py):

- mc_dc_test_cases(3) == 4: "A AND B AND C" needs 4 cases: TTT, FTT, TFT, TTF.
- mc_dc_test_cases(4) == 5: "A OR B OR C OR D" needs 5 cases: FFFF, TFFF,
  FTFF, FFTF, FFFT.
- required_test_cases("A", "AND", ["A", "B", "C"]) == 4 (MC/DC depth).
- required_test_cases("B", "AND", ["A", "B", "C"]) == 2 (decision depth).
- required_test_cases("C", "AND", ["A", "B", "C"]) == 1 (statement depth).
- required_test_cases("D", "AND", ["A", "B", "C"]) == 0 (no structural
  coverage objectives at levels D and E).
"""

DAL_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}

# Structural coverage objectives per software level (DO-178C Table A-7,
# summarized; the proprietary table text is not reproduced).
COVERAGE_OBJECTIVES = {
    "A": ("statement", "decision", "mc/dc"),
    "B": ("statement", "decision"),
    "C": ("statement",),
    "D": (),
    "E": (),
}

OPERATORS = ("AND", "OR")

METRICS = ("statement", "decision", "mc/dc")


def _check_dal(dal):
    if dal not in DAL_ORDER:
        raise ValueError(
            "invalid software level %r: must be one of A, B, C, D, E" % (dal,)
        )


def validate_operator(operator):
    """Return the normalized operator ('AND' or 'OR') or raise ValueError.

    >>> validate_operator("and")
    'AND'
    """
    if not isinstance(operator, str):
        raise ValueError("operator must be a string, got %r" % (operator,))
    op = operator.strip().upper()
    if op not in OPERATORS:
        raise ValueError(
            "unsupported operator %r: must be AND or OR" % (operator,)
        )
    return op


def validate_conditions(conditions):
    """Return the validated condition list (non-empty, non-blank, unique).

    >>> validate_conditions(["A", "B", "C"])
    ['A', 'B', 'C']
    """
    if not isinstance(conditions, (list, tuple)):
        raise ValueError("conditions must be a list of condition names")
    names = []
    for c in conditions:
        if not isinstance(c, str) or not c.strip():
            raise ValueError(
                "each condition must be a non-blank string, got %r" % (c,)
            )
        name = c.strip()
        if name in names:
            raise ValueError("duplicate condition name %r" % (name,))
        names.append(name)
    if not names:
        raise ValueError("a boolean condition needs at least one term")
    return names


def statement_test_cases():
    """Test cases required for statement coverage of one statement: 1.

    Executing the statement once satisfies statement coverage for it.
    """
    return 1


def decision_test_cases():
    """Test cases required for decision coverage of one decision: 2.

    The decision must take both the true and the false outcome.
    """
    return 2


def mc_dc_test_cases(n_conditions):
    """MC/DC test cases for a compound condition: n + 1.

    For n independent terms, n + 1 assignments prove each term
    independently affects the decision outcome.
    Anchor: n=3 (A AND B AND C) -> 4 (TTT, FTT, TFT, TTF).
    """
    if not isinstance(n_conditions, int) or n_conditions < 1:
        raise ValueError(
            "n_conditions must be an int >= 1, got %r" % (n_conditions,)
        )
    return n_conditions + 1


def test_cases_for_metric(metric, n_conditions):
    """Test cases for one coverage metric and n independent terms.

    metric in statement|decision|mc/dc. Anchors: statement 1,
    decision 2, mc/dc = n + 1 (3-term AND -> 4).
    """
    m = str(metric).strip().lower().replace("_", "/")
    if m == "mc/dc":
        m = "mc/dc"
    if m not in METRICS:
        raise ValueError(
            "unsupported coverage metric %r: must be statement, decision, "
            "or mc/dc" % (metric,)
        )
    if m == "statement":
        return statement_test_cases()
    if m == "decision":
        return decision_test_cases()
    return mc_dc_test_cases(n_conditions)


def required_test_cases(dal, operator, conditions):
    """Structural-coverage test cases the level demands for one decision.

    Level A: MC/DC depth -> n + 1. Level B: decision depth -> 2.
    Level C: statement depth -> 1. Levels D and E: no structural
    coverage objectives -> 0.
    Anchor: ("A", "AND", ["A","B","C"]) -> 4; ("B", ...) -> 2;
    ("C", ...) -> 1; ("D", ...) -> 0.
    """
    _check_dal(dal)
    validate_operator(operator)
    names = validate_conditions(conditions)
    n = len(names)
    depth = COVERAGE_OBJECTIVES[dal]
    if not depth:
        return 0
    if "mc/dc" in depth:
        return mc_dc_test_cases(n)
    if "decision" in depth:
        return decision_test_cases()
    return statement_test_cases()


def coverage_objectives(dal):
    """Structural coverage objectives that apply at the software level.

    Level A: statement, decision, MC/DC. Level B: statement, decision.
    Level C: statement. Levels D and E: none.
    Anchor: coverage_objectives("A") == ("statement", "decision", "mc/dc").
    """
    _check_dal(dal)
    return COVERAGE_OBJECTIVES[dal]


def coverage_depth(dal):
    """The deepest coverage metric required at the software level.

    Returns 'mc/dc' (A), 'decision' (B), 'statement' (C), or 'none' (D/E).
    """
    _check_dal(dal)
    objs = COVERAGE_OBJECTIVES[dal]
    if "mc/dc" in objs:
        return "mc/dc"
    if "decision" in objs:
        return "decision"
    if objs:
        return "statement"
    return "none"


def evaluate_expression(operator, assignment):
    """Evaluate an AND/OR expression under a boolean assignment dict.

    AND: every term true. OR: at least one term true.
    Anchor: evaluate_expression("AND", {"A": True, "B": False}) is False.
    """
    op = validate_operator(operator)
    names = validate_conditions(list(assignment.keys()))
    for name in names:
        if not isinstance(assignment[name], bool):
            raise ValueError(
                "assignment[%r] must be a bool, got %r"
                % (name, assignment[name])
            )
    values = [assignment[n] for n in names]
    if op == "AND":
        return all(values)
    return any(values)


def generate_mc_dc_vectors(operator, conditions):
    """Minimal MC/DC vector set for a compound condition: n + 1 dicts.

    AND: the all-true vector plus n vectors with exactly one term false.
    OR: the all-false vector plus n vectors with exactly one term true.
    Each dict maps condition name to bool.
    Anchor: generate_mc_dc_vectors("AND", ["A","B","C"]) has 4 vectors,
    the first all-true, and each later vector flips exactly one term.
    """
    op = validate_operator(operator)
    names = validate_conditions(conditions)
    n = len(names)
    if op == "AND":
        base = {name: True for name in names}
        vectors = [dict(base)]
        for i, name in enumerate(names):
            v = dict(base)
            v[name] = False
            vectors.append(v)
    else:
        base = {name: False for name in names}
        vectors = [dict(base)]
        for i, name in enumerate(names):
            v = dict(base)
            v[name] = True
            vectors.append(v)
    if len(vectors) != n + 1:
        raise AssertionError("internal error: MC/DC vector count mismatch")
    return vectors
