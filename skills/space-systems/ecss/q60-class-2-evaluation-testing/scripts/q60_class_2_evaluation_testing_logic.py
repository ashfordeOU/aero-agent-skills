"""Which inspections and tests a Class 2 part evaluation actually requires.

Anchor: ECSS-Q-ST-60C clause 5.2.3.4 (the inspections and tests an evaluated
Class 2 electrical, electronic and electromechanical part has to be put
through, and the conditions that decide which of them apply).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A small core of the programme is owed by every evaluated part whatever it is
  and wherever it flies. Nothing in the use conditions removes it.
* Everything else is owed because some declared condition asks for it: a
  mission longer than the endurance trigger, a dose above the radiation
  trigger, a particle environment on an active technology, a package that can
  be opened or that takes up moisture, a termination finish with a known
  failure mode, an operating span the manufacturer never characterised, or a
  mechanical environment nobody tested higher up.
* Each triggered item carries the condition that triggered it, so the
  programme can be defended item by item rather than cited as a template.
* A test already performed only carries credit when it was performed on the
  same procurement lot and is still inside its validity window. A record from
  another lot, or an expired one, leaves the item outstanding and is reported
  rather than quietly dropped.
* Credit offered for an item the programme never asked for is a finding too,
  because it usually means the wrong programme was run.
"""

from __future__ import annotations

import math

PART_FAMILIES = (
    "discrete-semiconductor",
    "monolithic-integrated-circuit",
    "hybrid-microcircuit",
    "passive-component",
    "electromechanical-component",
    "connector",
)

# Technologies whose junctions can be upset or damaged by single particles.
ACTIVE_FAMILIES = (
    "discrete-semiconductor",
    "monolithic-integrated-circuit",
    "hybrid-microcircuit",
)

PACKAGE_TYPES = (
    "hermetic-metal-or-ceramic",
    "plastic-encapsulated",
    "bare-die-or-chip-scale",
)

TERMINATION_FINISHES = (
    "tin-lead-solder-coated",
    "pure-tin",
    "gold-plated",
    "palladium-nickel",
)

# Owed by every evaluated part, whatever the use conditions say.
ALWAYS_REQUIRED_TESTS = (
    "external-visual-inspection",
    "electrical-measurement-at-reference-temperature",
    "destructive-physical-analysis",
)

# Owed only when a declared condition asks for them.
CONDITIONAL_TESTS = (
    "electrical-characterisation-over-temperature-extremes",
    "endurance-life-test",
    "total-ionising-dose-characterisation",
    "single-event-effects-characterisation",
    "hermeticity-and-seal-test",
    "moisture-sensitivity-and-preconditioning-bake",
    "tin-whisker-mitigation-assessment",
    "gold-embrittlement-assessment",
    "wire-bond-and-die-shear-strength-test",
    "mechanical-shock-and-vibration-test",
)

TEST_CATALOGUE = ALWAYS_REQUIRED_TESTS + CONDITIONAL_TESTS

# A mission longer than this asks for an endurance life test.
LIFE_TEST_MISSION_MONTHS = 24.0

# A mission dose above this asks for a total ionising dose characterisation.
TID_TRIGGER_KRAD = 1.0

# A performed test older than this no longer carries credit.
PRIOR_TEST_VALIDITY_MONTHS = 36.0

# Conditions are compared as declared quantities; a case meant to sit on a
# trigger can land a few units in the last place away from it.
CONDITION_TOLERANCE = 1e-9


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def _label(value, label):
    """Return a required non-empty string field or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _choice(value, allowed, label):
    """Return a value drawn from a closed set or raise."""
    if value not in allowed:
        raise ValueError(
            "unknown %s %r (known: %s)" % (label, value, ", ".join(allowed))
        )
    return value


def normalize_use_context(context):
    """Validate the declared use conditions of the part under evaluation."""
    if not isinstance(context, dict):
        raise ValueError(
            "context must be a mapping, got %r" % (type(context).__name__,)
        )
    duration = _real(context.get("mission_duration_months"), "mission_duration_months")
    if duration < 0.0:
        raise ValueError(
            "mission_duration_months must not be negative, got %r" % (duration,)
        )
    required_span = _real(
        context.get("required_operating_span_k"), "required_operating_span_k"
    )
    if required_span <= 0.0:
        raise ValueError(
            "required_operating_span_k must be positive, got %r" % (required_span,)
        )
    characterised_span = _real(
        context.get("characterised_operating_span_k"), "characterised_operating_span_k"
    )
    if characterised_span <= 0.0:
        raise ValueError(
            "characterised_operating_span_k must be positive, got %r"
            % (characterised_span,)
        )
    dose = _real(context.get("mission_total_dose_krad"), "mission_total_dose_krad")
    if dose < 0.0:
        raise ValueError(
            "mission_total_dose_krad must not be negative, got %r" % (dose,)
        )
    return {
        "part_family": _choice(
            context.get("part_family"), PART_FAMILIES, "part_family"
        ),
        "package_type": _choice(
            context.get("package_type"), PACKAGE_TYPES, "package_type"
        ),
        "termination_finish": _choice(
            context.get("termination_finish"),
            TERMINATION_FINISHES,
            "termination_finish",
        ),
        "mission_duration_months": duration,
        "required_operating_span_k": required_span,
        "characterised_operating_span_k": characterised_span,
        "mission_total_dose_krad": dose,
        "particle_environment": _flag(context, "particle_environment"),
        "covered_by_higher_level_assembly_test": _flag(
            context, "covered_by_higher_level_assembly_test"
        ),
    }


def triggered_tests(context):
    """Conditional items the declared conditions ask for, with their reason."""
    use = normalize_use_context(context)
    triggered = []

    if (
        use["required_operating_span_k"]
        > use["characterised_operating_span_k"] + CONDITION_TOLERANCE
    ):
        triggered.append(
            (
                "electrical-characterisation-over-temperature-extremes",
                "required-operating-span-exceeds-characterised-span",
            )
        )
    if use["mission_duration_months"] > LIFE_TEST_MISSION_MONTHS + CONDITION_TOLERANCE:
        triggered.append(
            ("endurance-life-test", "mission-longer-than-the-endurance-trigger")
        )
    if use["mission_total_dose_krad"] > TID_TRIGGER_KRAD + CONDITION_TOLERANCE:
        triggered.append(
            (
                "total-ionising-dose-characterisation",
                "mission-dose-above-the-radiation-trigger",
            )
        )
    if use["particle_environment"] and use["part_family"] in ACTIVE_FAMILIES:
        triggered.append(
            (
                "single-event-effects-characterisation",
                "active-technology-in-a-particle-environment",
            )
        )
    if use["package_type"] == "hermetic-metal-or-ceramic":
        triggered.append(
            ("hermeticity-and-seal-test", "sealed-cavity-package-declared")
        )
    if use["package_type"] == "plastic-encapsulated":
        triggered.append(
            (
                "moisture-sensitivity-and-preconditioning-bake",
                "moisture-absorbing-package-declared",
            )
        )
    if use["termination_finish"] == "pure-tin":
        triggered.append(
            (
                "tin-whisker-mitigation-assessment",
                "pure-tin-finish-declared-on-the-terminations",
            )
        )
    if use["termination_finish"] == "gold-plated":
        triggered.append(
            (
                "gold-embrittlement-assessment",
                "gold-finish-declared-on-the-terminations",
            )
        )
    if use["part_family"] == "hybrid-microcircuit":
        triggered.append(
            (
                "wire-bond-and-die-shear-strength-test",
                "internal-interconnect-built-during-part-assembly",
            )
        )
    if not use["covered_by_higher_level_assembly_test"]:
        triggered.append(
            (
                "mechanical-shock-and-vibration-test",
                "mechanical-environment-not-covered-higher-up",
            )
        )
    return tuple(triggered)


def required_test_programme(context):
    """Full programme owed: the core plus everything the conditions trigger."""
    programme = [
        {"test": name, "basis": "always-required", "reason": "owed-by-every-evaluation"}
        for name in ALWAYS_REQUIRED_TESTS
    ]
    for name, reason in triggered_tests(context):
        programme.append({"test": name, "basis": "condition-triggered", "reason": reason})
    return programme


def not_required_tests(context):
    """Conditional items no declared condition asked for."""
    asked = {name for name, _ in triggered_tests(context)}
    return tuple(name for name in CONDITIONAL_TESTS if name not in asked)


def normalize_prior_tests(prior_tests):
    """Validate the tests already performed and offered for credit."""
    if isinstance(prior_tests, str) or not isinstance(prior_tests, (list, tuple)):
        raise ValueError(
            "prior_tests must be a list or tuple of mappings, got %r" % (prior_tests,)
        )
    records = []
    for record in prior_tests:
        if not isinstance(record, dict):
            raise ValueError(
                "each prior test must be a mapping, got %r" % (type(record).__name__,)
            )
        age = _real(record.get("age_months"), "age_months")
        if age < 0.0:
            raise ValueError("age_months must not be negative, got %r" % (age,))
        records.append(
            {
                "test": _choice(record.get("test"), TEST_CATALOGUE, "test name"),
                "procurement_lot": _label(
                    record.get("procurement_lot"), "procurement_lot"
                ),
                "age_months": age,
            }
        )
    return records


def prior_test_credit(record, procurement_lot):
    """Decide whether one performed test still carries credit.

    Returns ``(carries, reasons)``; ``reasons`` names every rule that failed.
    """
    if not isinstance(record, dict):
        raise ValueError(
            "prior test must be a mapping, got %r" % (type(record).__name__,)
        )
    lot = _label(procurement_lot, "procurement_lot")
    reasons = []
    if record["procurement_lot"] != lot:
        reasons.append("prior-test-from-another-procurement-lot")
    if record["age_months"] > PRIOR_TEST_VALIDITY_MONTHS + CONDITION_TOLERANCE:
        reasons.append("prior-test-outside-validity-window")
    return (len(reasons) == 0, reasons)


def determine_class_2_test_programme(part_id, procurement_lot, context, prior_tests):
    """Return the inspections and tests this Class 2 evaluation still owes."""
    _label(part_id, "part_id")
    lot = _label(procurement_lot, "procurement_lot")
    use = normalize_use_context(context)
    programme = required_test_programme(context)
    required_names = [item["test"] for item in programme]
    records = normalize_prior_tests(prior_tests)

    findings = []
    covered = []
    for record in records:
        carries, reasons = prior_test_credit(record, lot)
        if record["test"] not in required_names:
            findings.append(
                {
                    "subject": record["test"],
                    "finding": "prior-test-not-in-the-required-programme",
                    "reasons": [],
                }
            )
            continue
        if carries:
            if record["test"] not in covered:
                covered.append(record["test"])
        else:
            findings.append(
                {
                    "subject": record["test"],
                    "finding": "prior-test-does-not-carry-credit",
                    "reasons": reasons,
                }
            )

    outstanding = [name for name in required_names if name not in covered]

    for item in programme:
        if item["basis"] == "condition-triggered":
            findings.append(
                {
                    "subject": item["test"],
                    "finding": "test-triggered-by-declared-condition",
                    "reasons": [item["reason"]],
                }
            )
    if use["covered_by_higher_level_assembly_test"]:
        findings.append(
            {
                "subject": "mechanical-shock-and-vibration-test",
                "finding": "mechanical-programme-delegated-to-higher-level-assembly",
                "reasons": [],
            }
        )

    return {
        "part_id": part_id,
        "procurement_lot": lot,
        "context": use,
        "required_tests": programme,
        "required_test_names": required_names,
        "not_required_tests": list(not_required_tests(context)),
        "covered_by_prior_testing": covered,
        "outstanding_tests": outstanding,
        "programme_size": len(required_names),
        "findings": findings,
        "evaluation_testing_complete": not outstanding,
    }
