"""Procurement test table selection for commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 8.2 (choosing which per-family procurement
test matrix applies to a given commercial part). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the part: a component type, a technology, a part number, a
   declared assurance class and the tests the procurement proposes to waive.
2. Resolve the part family from the component type and the technology
   together. Neither field decides alone: the same technology token appears
   under more than one component type, and the same component type splits
   across technologies with different matrices.
3. Map the resolved family to its procurement test table.
4. Split the table's test groups into those applicable at the declared class
   and those the table defers to a higher class, and express applicability as
   a fraction judged under a named tolerance.
5. Resolve every additional function the part carries, and when those pull in
   a second table report the conflict so the governing matrix is agreed
   before the purchase order goes out rather than after delivery.
6. Reconcile the proposed waivers against the applicable groups, naming a
   waiver against a group that is not applicable anyway and a waiver against
   a group the class does require.
"""

import math

__all__ = [
    "COMPONENT_TYPES",
    "TECHNOLOGIES",
    "FAMILY_BY_TYPE_AND_TECHNOLOGY",
    "TEST_TABLES",
    "ASSURANCE_CLASSES",
    "APPLICABILITY_TOLERANCE",
    "normalize_token",
    "validate_assurance_class",
    "validate_component_type",
    "validate_technology",
    "resolve_family",
    "table_for_family",
    "table_groups",
    "applicable_groups",
    "deferred_groups",
    "applicability_fraction",
    "reconcile_waivers",
    "select_procurement_test_table",
]

# The assurance classes a commercial part may be procured against.
ASSURANCE_CLASSES = (1, 2, 3)

# (component type, technology) -> part family. The pair decides, never one
# field: 'film' appears under both capacitor and resistor, and 'microcircuit'
# splits into two families with different matrices.
FAMILY_BY_TYPE_AND_TECHNOLOGY = {
    ("microcircuit", "monolithic"): "monolithic-microcircuit",
    ("microcircuit", "hybrid"): "hybrid-microcircuit",
    ("semiconductor", "discrete"): "discrete-semiconductor",
    ("semiconductor", "optocoupler"): "optocoupler",
    ("capacitor", "ceramic"): "ceramic-capacitor",
    ("capacitor", "tantalum"): "tantalum-capacitor",
    ("capacitor", "film"): "film-capacitor",
    ("resistor", "film"): "film-resistor",
    ("resistor", "wirewound"): "wirewound-resistor",
    ("magnetics", "wound"): "wound-magnetic-component",
    ("relay", "electromechanical"): "electromechanical-relay",
    ("connector", "separable"): "separable-connector",
    ("crystal", "oscillator"): "crystal-oscillator",
}

COMPONENT_TYPES = tuple(
    sorted({pair[0] for pair in FAMILY_BY_TYPE_AND_TECHNOLOGY})
)
TECHNOLOGIES = tuple(
    sorted({pair[1] for pair in FAMILY_BY_TYPE_AND_TECHNOLOGY})
)

# Each family's procurement test table: the table identifier and the test
# groups it carries, each group naming the assurance classes at which it
# applies.
TEST_TABLES = {
    "monolithic-microcircuit": {
        "table": "procurement-table-a",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("electrical-measurement-room-temperature", (1, 2, 3)),
            ("electrical-measurement-temperature-extremes", (1, 2)),
            ("burn-in", (1, 2)),
            ("seal-fine-and-gross", (1, 2)),
            ("destructive-physical-analysis", (1,)),
            ("radiation-verification", (1,)),
        ),
    },
    "hybrid-microcircuit": {
        "table": "procurement-table-b",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("internal-visual-inspection", (1,)),
            ("electrical-measurement-room-temperature", (1, 2, 3)),
            ("electrical-measurement-temperature-extremes", (1, 2)),
            ("burn-in", (1, 2)),
            ("seal-fine-and-gross", (1, 2)),
            ("particle-impact-noise-detection", (1,)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
    "discrete-semiconductor": {
        "table": "procurement-table-c",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("electrical-measurement-room-temperature", (1, 2, 3)),
            ("electrical-measurement-temperature-extremes", (1, 2)),
            ("burn-in", (1, 2)),
            ("thermal-shock", (1, 2)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
    "optocoupler": {
        "table": "procurement-table-d",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("current-transfer-ratio-measurement", (1, 2, 3)),
            ("electrical-measurement-temperature-extremes", (1, 2)),
            ("burn-in", (1, 2)),
            ("radiation-verification", (1,)),
        ),
    },
    "ceramic-capacitor": {
        "table": "procurement-table-e",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("capacitance-and-dissipation-measurement", (1, 2, 3)),
            ("insulation-resistance-measurement", (1, 2, 3)),
            ("voltage-conditioning", (1, 2)),
            ("thermal-shock", (1, 2)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
    "tantalum-capacitor": {
        "table": "procurement-table-f",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("capacitance-and-dissipation-measurement", (1, 2, 3)),
            ("leakage-current-measurement", (1, 2, 3)),
            ("surge-current-conditioning", (1, 2)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
    "film-capacitor": {
        "table": "procurement-table-g",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("capacitance-and-dissipation-measurement", (1, 2, 3)),
            ("insulation-resistance-measurement", (1, 2)),
            ("thermal-shock", (1, 2)),
        ),
    },
    "film-resistor": {
        "table": "procurement-table-h",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("resistance-measurement", (1, 2, 3)),
            ("short-time-overload", (1, 2)),
            ("thermal-shock", (1, 2)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
    "wirewound-resistor": {
        "table": "procurement-table-j",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("resistance-measurement", (1, 2, 3)),
            ("short-time-overload", (1, 2)),
            ("terminal-strength", (1, 2)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
    "wound-magnetic-component": {
        "table": "procurement-table-k",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("winding-resistance-measurement", (1, 2, 3)),
            ("dielectric-withstanding-voltage", (1, 2)),
            ("insulation-resistance-measurement", (1, 2)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
    "electromechanical-relay": {
        "table": "procurement-table-l",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("contact-resistance-measurement", (1, 2, 3)),
            ("pickup-and-dropout-measurement", (1, 2, 3)),
            ("seal-fine-and-gross", (1, 2)),
            ("particle-impact-noise-detection", (1,)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
    "separable-connector": {
        "table": "procurement-table-m",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("contact-resistance-measurement", (1, 2, 3)),
            ("insulation-resistance-measurement", (1, 2)),
            ("contact-retention", (1, 2)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
    "crystal-oscillator": {
        "table": "procurement-table-n",
        "groups": (
            ("external-visual-inspection", (1, 2, 3)),
            ("frequency-and-stability-measurement", (1, 2, 3)),
            ("electrical-measurement-temperature-extremes", (1, 2)),
            ("seal-fine-and-gross", (1, 2)),
            ("destructive-physical-analysis", (1,)),
        ),
    },
}

# Applicability is a quotient of two counts; a table whose every group applies
# must not fail on representation alone.
APPLICABILITY_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_assurance_class(value):
    """Return the validated declared assurance class."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("assurance class must be a whole number, got %r" % (value,))
    if value not in ASSURANCE_CLASSES:
        raise ValueError(
            "assurance class %d is not recognized; expected one of %s"
            % (value, ", ".join(str(c) for c in ASSURANCE_CLASSES))
        )
    return value


def validate_component_type(value):
    """Return the validated component type token."""
    token = normalize_token(value, "component type")
    if token not in COMPONENT_TYPES:
        raise ValueError(
            "component type '%s' is not recognized; expected one of %s"
            % (token, ", ".join(COMPONENT_TYPES))
        )
    return token


def validate_technology(value):
    """Return the validated technology token."""
    token = normalize_token(value, "technology")
    if token not in TECHNOLOGIES:
        raise ValueError(
            "technology '%s' is not recognized; expected one of %s"
            % (token, ", ".join(TECHNOLOGIES))
        )
    return token


def resolve_family(component_type, technology):
    """Return the part family the component type and technology name together.

    The pair decides. A technology token alone is ambiguous across component
    types, and a component type alone is ambiguous across technologies.
    """
    type_token = validate_component_type(component_type)
    technology_token = validate_technology(technology)
    key = (type_token, technology_token)
    if key not in FAMILY_BY_TYPE_AND_TECHNOLOGY:
        raise ValueError(
            "no part family is defined for a '%s' of technology '%s'"
            % (type_token, technology_token)
        )
    return FAMILY_BY_TYPE_AND_TECHNOLOGY[key]


def table_for_family(family):
    """Return the procurement test table identifier for a part family."""
    token = normalize_token(family, "family")
    if token not in TEST_TABLES:
        raise ValueError("part family '%s' has no procurement test table" % token)
    return TEST_TABLES[token]["table"]


def table_groups(family):
    """Return every test group the family's table carries, in table order."""
    token = normalize_token(family, "family")
    if token not in TEST_TABLES:
        raise ValueError("part family '%s' has no procurement test table" % token)
    return [name for name, _classes in TEST_TABLES[token]["groups"]]


def applicable_groups(family, assurance_class):
    """Return the table's test groups that apply at the declared class."""
    token = normalize_token(family, "family")
    if token not in TEST_TABLES:
        raise ValueError("part family '%s' has no procurement test table" % token)
    declared = validate_assurance_class(assurance_class)
    return [
        name
        for name, classes in TEST_TABLES[token]["groups"]
        if declared in classes
    ]


def deferred_groups(family, assurance_class):
    """Return the table's groups the declared class does not call for."""
    applicable = set(applicable_groups(family, assurance_class))
    return [name for name in table_groups(family) if name not in applicable]


def applicability_fraction(family, assurance_class):
    """Return the share of the family's table that applies at the class."""
    total = len(table_groups(family))
    if total == 0:
        raise ValueError("part family '%s' has an empty test table" % family)
    return len(applicable_groups(family, assurance_class)) / float(total)


def reconcile_waivers(proposed_waivers, applicable, table_all):
    """Return the waiver reconciliation against the applicable group set.

    A waiver against a group the table never carries is a drafting error; a
    waiver against a group the table carries but the class defers is already
    satisfied; a waiver against an applicable group is a real relaxation and
    has to be carried into the verdict.
    """
    if proposed_waivers is None:
        proposed_waivers = []
    if not isinstance(proposed_waivers, (list, tuple)):
        raise ValueError("proposed_waivers must be a sequence")
    seen = []
    unknown = []
    redundant = []
    effective = []
    for index, value in enumerate(proposed_waivers):
        token = normalize_token(value, "proposed_waivers[%d]" % index)
        if token in seen:
            raise ValueError("test group '%s' is waived twice" % token)
        seen.append(token)
        if token not in table_all:
            unknown.append(token)
        elif token in applicable:
            effective.append(token)
        else:
            redundant.append(token)
    return {
        "requested": seen,
        "unknown_groups": unknown,
        "already_deferred": redundant,
        "effective_waivers": effective,
    }


def _validate_function(function, label):
    """Return the family named by one additional function declaration."""
    if not isinstance(function, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("component_type", "technology"):
        if key not in function:
            raise ValueError("%s missing required key '%s'" % (label, key))
    return resolve_family(function["component_type"], function["technology"])


def select_procurement_test_table(part):
    """Run the full clause 8.2 selection for one commercial part.

    part keys: part_number, component_type, technology, assurance_class, and
    optionally additional_functions and proposed_waivers.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("part_number", "component_type", "technology", "assurance_class"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)

    part_number = _require_text(part["part_number"], "part_number")
    declared = validate_assurance_class(part["assurance_class"])
    family = resolve_family(part["component_type"], part["technology"])
    table = table_for_family(family)

    extra = part.get("additional_functions", [])
    if extra is None:
        extra = []
    if not isinstance(extra, (list, tuple)):
        raise ValueError("additional_functions must be a sequence")
    extra_families = []
    for index, function in enumerate(extra):
        resolved = _validate_function(function, "additional_functions[%d]" % index)
        if resolved != family and resolved not in extra_families:
            extra_families.append(resolved)

    findings = []
    extra_tables = [table_for_family(f) for f in extra_families]
    if extra_families:
        findings.append(
            "part '%s' carries functions from %s, so table(s) %s apply "
            "alongside %s; agree the governing matrix before procurement"
            % (
                part_number,
                ", ".join(extra_families),
                ", ".join(extra_tables),
                table,
            )
        )

    applicable = applicable_groups(family, declared)
    deferred = deferred_groups(family, declared)
    all_groups = table_groups(family)
    fraction = applicability_fraction(family, declared)
    whole_table = math.isclose(
        fraction, 1.0, rel_tol=0.0, abs_tol=APPLICABILITY_TOLERANCE
    )

    waivers = reconcile_waivers(
        part.get("proposed_waivers"), set(applicable), set(all_groups)
    )
    for token in waivers["unknown_groups"]:
        findings.append(
            "waiver names test group '%s', which table %s does not carry"
            % (token, table)
        )
    for token in waivers["already_deferred"]:
        findings.append(
            "waiver for test group '%s' is redundant: class %d does not call "
            "for it" % (token, declared)
        )
    for token in waivers["effective_waivers"]:
        findings.append(
            "test group '%s' applies at class %d and is being waived; the "
            "relaxation needs an approved justification" % (token, declared)
        )

    return {
        "part_number": part_number,
        "assurance_class": declared,
        "family": family,
        "table": table,
        "table_groups": all_groups,
        "applicable_groups": applicable,
        "deferred_groups": deferred,
        "applicability_fraction": fraction,
        "whole_table_applies": whole_table,
        "additional_families": extra_families,
        "additional_tables": extra_tables,
        "single_table_governs": not extra_families,
        "waivers": waivers,
        "selection_settled": not findings,
        "findings": findings,
    }
