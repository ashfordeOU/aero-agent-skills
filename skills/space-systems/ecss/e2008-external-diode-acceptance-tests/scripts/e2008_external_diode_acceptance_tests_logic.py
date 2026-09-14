#!/usr/bin/env python3
"""Acceptance programme for external protection diodes.

Anchor: ECSS-E-ST-20-08C clause 9.4.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The acceptance programme for an external protection diode is drawn from
a tabulated list of tests. The table is the authority in both
directions: a row left out of the programme is a gap, and a test that is
not a row at all is not a stricter programme but an unagreed one, paid
for in parts and schedule nobody costed.

Rows do not all have the same standing:

    mandatory     owed by every external diode acceptance programme
    conditional   owed only where the build configuration raises the
                  row's condition token
    optional      owed by nobody; admissible only where the project has
                  declared it for this build

Conditional rows are where programmes quietly go wrong. Resolved against
an assumption rather than against the declared configuration, they
either drop work the build needs or add work it does not, and both
outcomes read as a clean matrix afterwards.

The tabulated order is graded too, and on relative position rather than
absolute slot number: a project-specific step inserted between two
tabulated rows is not an ordering break, but electrical characterisation
moved after the environmental exposure it was meant to bracket is.

The table, the condition tokens and the coverage minimum below are
declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MANDATORY = "mandatory"
CONDITIONAL = "conditional"
OPTIONAL = "optional"
STANDINGS = (MANDATORY, CONDITIONAL, OPTIONAL)

TEST_TABLE = (
    {
        "test": "external-diode-visual-inspection",
        "standing": MANDATORY,
        "order": 1,
        "condition": None,
    },
    {
        "test": "external-diode-dimensional-check",
        "standing": MANDATORY,
        "order": 2,
        "condition": None,
    },
    {
        "test": "external-diode-forward-voltage-measurement",
        "standing": MANDATORY,
        "order": 3,
        "condition": None,
    },
    {
        "test": "external-diode-reverse-leakage-measurement",
        "standing": MANDATORY,
        "order": 4,
        "condition": None,
    },
    {
        "test": "external-diode-thermal-endurance-run",
        "standing": CONDITIONAL,
        "order": 5,
        "condition": "external-diode-bonded-to-substrate",
    },
    {
        "test": "external-diode-terminal-strength-pull",
        "standing": CONDITIONAL,
        "order": 6,
        "condition": "external-diode-wire-terminated",
    },
    {
        "test": "external-diode-insulation-resistance-check",
        "standing": CONDITIONAL,
        "order": 7,
        "condition": "external-diode-insulated-mounting",
    },
    {
        "test": "external-diode-humidity-exposure",
        "standing": OPTIONAL,
        "order": 8,
        "condition": None,
    },
    {
        "test": "external-diode-final-electrical-verification",
        "standing": MANDATORY,
        "order": 9,
        "condition": None,
    },
)

TABULATED_TESTS = tuple(row["test"] for row in TEST_TABLE)
CONDITION_TOKENS = tuple(
    row["condition"] for row in TEST_TABLE if row["condition"] is not None
)

PROGRAMME_COMPLETE = "external-diode-programme-complete"
PROGRAMME_INCOMPLETE = "external-diode-programme-incomplete"

DEFAULT_PROGRAMME_POLICY = {
    "min_covered_share": 1.0,
    "allow_untabulated_tests": False,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return list(value)


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_share(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 < value <= 1.0:
        raise ValueError(
            "%s must sit above zero and at or below one, got %r" % (name, value)
        )
    return float(value)


def _require_position(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer position, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be one or greater, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    The covered share is a quotient of two test counts, so a programme
    that covers exactly the declared fraction of the required set can
    evaluate a unit in the last place below it. The comparison absorbs
    that; the declared minimum itself is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def lookup_test(name):
    """Return the table row for one test, or raise if the table lacks it."""
    label = _require_label("test", name)
    for row in TEST_TABLE:
        if row["test"] == label:
            return dict(row)
    raise ValueError("%r is not a row of the external diode test table" % label)


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_PROGRAMME_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_share("min_covered_share", settings.get("min_covered_share"))
    _require_flag(
        "allow_untabulated_tests", settings.get("allow_untabulated_tests")
    )
    return settings


def validate_configuration(configuration):
    """Check the build configuration against the table's condition tokens."""
    _require_mapping("configuration", configuration)
    build_id = _require_label("build_id", configuration.get("build_id"))
    conditions = _require_sequence(
        "conditions", configuration.get("conditions") or []
    )
    declared_optional = _require_sequence(
        "declared_optional", configuration.get("declared_optional") or []
    )

    cleaned_conditions = []
    unreferenced = []
    for token in conditions:
        label = _require_label("condition token", token)
        if label in cleaned_conditions:
            raise ValueError("condition %r is declared twice" % label)
        cleaned_conditions.append(label)
        if label not in CONDITION_TOKENS:
            unreferenced.append(label)

    cleaned_optional = []
    for token in declared_optional:
        row = lookup_test(token)
        if row["standing"] != OPTIONAL:
            raise ValueError(
                "%r is a %s row and cannot be declared as an optional test"
                % (row["test"], row["standing"])
            )
        if row["test"] in cleaned_optional:
            raise ValueError("optional test %r is declared twice" % row["test"])
        cleaned_optional.append(row["test"])

    findings = [
        "configuration token %r is not referenced by the test table; the usual "
        "cause is a renamed condition" % token
        for token in unreferenced
    ]
    return {
        "build_id": build_id,
        "conditions": cleaned_conditions,
        "declared_optional": cleaned_optional,
        "unreferenced_conditions": unreferenced,
        "findings": findings,
    }


def required_tests(configuration):
    """Resolve the table into the set this build actually owes."""
    resolved = validate_configuration(configuration)
    declared = set(resolved["conditions"])
    required = []
    for row in TEST_TABLE:
        if row["standing"] == MANDATORY:
            required.append(row["test"])
        elif row["standing"] == CONDITIONAL and row["condition"] in declared:
            required.append(row["test"])
    return required


def admissible_tests(configuration):
    """Required rows plus the optional rows this build has declared."""
    resolved = validate_configuration(configuration)
    return required_tests(configuration) + list(resolved["declared_optional"])


def validate_programme(programme):
    """Check each programme entry names a tabulated test and a position."""
    entries = _require_sequence("programme", programme)
    if not entries:
        raise ValueError("programme must hold at least one entry")
    cleaned = []
    seen = set()
    positions = set()
    for entry in entries:
        _require_mapping("programme entry", entry)
        name = _require_label("test", entry.get("test"))
        position = _require_position("position", entry.get("position"))
        if name in seen:
            raise ValueError(
                "%r appears twice in the programme; a duplicate entry makes the "
                "coverage arithmetic lie and leaves the order ambiguous" % name
            )
        if position in positions:
            raise ValueError("two programme entries share position %d" % position)
        seen.add(name)
        positions.add(position)
        cleaned.append({"test": name, "position": position})
    cleaned.sort(key=lambda e: e["position"])
    return cleaned


def grade_coverage(programme, configuration, policy=None):
    """Compare the programme against the resolved required set."""
    settings = resolve_policy(policy)
    entries = validate_programme(programme)
    required = required_tests(configuration)
    admissible = set(admissible_tests(configuration))
    scheduled = [entry["test"] for entry in entries]

    present = [name for name in required if name in scheduled]
    missing = [name for name in required if name not in scheduled]
    untabulated = [name for name in scheduled if name not in TABULATED_TESTS]
    inadmissible = [
        name
        for name in scheduled
        if name in TABULATED_TESTS and name not in admissible
    ]

    covered_share = len(present) / len(required) if required else 1.0
    meets_coverage = _at_least(covered_share, settings["min_covered_share"])

    findings = []
    for name in missing:
        findings.append(
            "the programme omits %s, a row this build owes" % name
        )
    for name in untabulated:
        findings.append(
            "%s is not a row of the test table; that is unagreed scope, not a "
            "stricter programme" % name
        )
    for name in inadmissible:
        findings.append(
            "%s is tabulated but neither owed by this build nor declared as an "
            "optional test" % name
        )
    return {
        "required": required,
        "present": present,
        "missing": missing,
        "untabulated": untabulated,
        "inadmissible": inadmissible,
        "covered_share": covered_share,
        "meets_covered_share": meets_coverage,
        "findings": findings,
    }


def grade_sequence(programme):
    """Grade the running order against the tabulated order.

    Graded on relative position only, and only over entries the table
    actually holds. A project-specific step inserted between two
    tabulated rows is not an ordering break; a tabulated row that
    overtakes one the table places ahead of it is. An entry the table
    does not hold has no tabulated order to be judged against, so it is
    set aside here and reported by the coverage grade instead.
    """
    entries = validate_programme(programme)
    placed = []
    unplaced = []
    for entry in entries:
        if entry["test"] not in TABULATED_TESTS:
            unplaced.append(entry["test"])
            continue
        row = lookup_test(entry["test"])
        placed.append((entry["position"], row["order"], row["test"]))

    inversions = []
    for index, (_, earlier_order, earlier_name) in enumerate(placed):
        for _, later_order, later_name in placed[index + 1 :]:
            if later_order < earlier_order:
                inversions.append((earlier_name, later_name))

    findings = [
        "%s is scheduled ahead of %s, inverting the tabulated order"
        % (earlier, later)
        for earlier, later in inversions
    ]
    return {
        "scheduled": [name for _, _, name in placed],
        "untabulated": unplaced,
        "inversions": inversions,
        "in_tabulated_order": not inversions,
        "findings": findings,
    }


def build_programme(configuration):
    """Draw the canonical programme for a build straight from the table."""
    admissible = set(admissible_tests(configuration))
    position = 0
    programme = []
    for row in TEST_TABLE:
        if row["test"] in admissible:
            position += 1
            programme.append({"test": row["test"], "position": position})
    return programme


def assess_external_diode_programme(case):
    """Full clause 9.4.3 roll-up over one proposed acceptance programme."""
    _require_mapping("case", case)
    programme_id = _require_label("programme_id", case.get("programme_id"))
    configuration = case.get("configuration")
    programme = case.get("programme")
    settings = resolve_policy(case.get("policy"))

    resolved = validate_configuration(configuration)
    coverage = grade_coverage(programme, configuration, settings)
    sequence = grade_sequence(programme)

    findings = list(resolved["findings"])
    findings.extend(coverage["findings"])
    findings.extend(sequence["findings"])

    blocked = bool(coverage["missing"]) or not coverage["meets_covered_share"]
    if coverage["untabulated"] and not settings["allow_untabulated_tests"]:
        blocked = True
    if coverage["inadmissible"]:
        blocked = True
    if not sequence["in_tabulated_order"]:
        blocked = True

    return {
        "programme_id": programme_id,
        "build_id": resolved["build_id"],
        "configuration": resolved,
        "coverage": coverage,
        "sequence": sequence,
        "verdict": PROGRAMME_INCOMPLETE if blocked else PROGRAMME_COMPLETE,
        "findings": findings,
    }
