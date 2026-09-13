#!/usr/bin/env python3
"""Test conditions and methods for a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Every test run on a photovoltaic assembly (PVA) is governed by the
source control drawing (SCD): the drawing fixes which method is used
and the conditions the method is run at. A result produced under a
method the drawing does not name, or at a condition outside the band
the drawing allows, is not evidence against the drawing.

Two things are checked for each test:

    the method      named by the drawing, invoked by it through a
                    standard, or substituted with an approved deviation
    the conditions  each declared value sits inside the band the
                    drawing sets around the specified value

Illumination is the condition most often mis-stated, because it is
specified as a fraction of the air-mass-zero reference irradiance
rather than in watt per square metre. A measured irradiance is
converted to that ratio before the band is applied.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONDITION_KINDS = (
    "temperature",
    "illumination-intensity",
    "pressure",
    "relative-humidity",
    "cycle-count",
    "dwell-duration",
)

TEST_PURPOSES = (
    "electrical-performance",
    "thermal-cycling",
    "mechanical-strength",
    "environmental-exposure",
)

METHOD_SOURCES = (
    "scd-named-method",
    "scd-invoked-standard-method",
    "equivalent-method-with-approved-deviation",
    "equivalent-method-without-approval",
    "supplier-internal-method",
)

GOVERNING_DOCUMENTS = (
    "source-control-drawing",
    "scd-invoked-specification",
    "supplier-internal-procedure",
)

AM0_REFERENCE_IRRADIANCE_W_PER_M2 = 1367.0

TEST_GOVERNED = "test-governed"
CONDITION_OUT_OF_BAND = "condition-out-of-band"
CONDITION_SET_INCOMPLETE = "condition-set-incomplete"
METHOD_NOT_ADMISSIBLE = "method-not-admissible"
NOT_GOVERNED_BY_DRAWING = "not-governed-by-drawing"

PROGRAMME_GOVERNED = "test-programme-governed"
PROGRAMME_NOT_GOVERNED = "test-programme-not-governed"

_APPROVAL_REQUIRED_SOURCES = ("equivalent-method-with-approved-deviation",)

DEFAULT_TEST_GOVERNANCE_POLICY = {
    "mandatory_condition_kinds": {
        "electrical-performance": ("temperature", "illumination-intensity"),
        "thermal-cycling": ("temperature", "cycle-count"),
        "mechanical-strength": ("temperature",),
        "environmental-exposure": ("relative-humidity", "dwell-duration"),
    },
    "admissible_method_sources": (
        "scd-named-method",
        "scd-invoked-standard-method",
        "equivalent-method-with-approved-deviation",
    ),
    "governing_documents": ("source-control-drawing", "scd-invoked-specification"),
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A deviation that is meant to land exactly on the tolerance is built
    from a subtraction of two declared values and can miss the bound by
    a few units in the last place. The drawing tolerance is never
    widened; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_test_governance_policy(policy):
    """Check a governance policy names sane methods, documents and conditions."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    table = policy.get("mandatory_condition_kinds")
    if not isinstance(table, dict):
        raise ValueError("policy mandatory_condition_kinds must be a mapping")
    missing = set(TEST_PURPOSES) - set(table)
    if missing:
        raise ValueError(
            "policy mandatory_condition_kinds is missing purposes: %s"
            % ", ".join(sorted(missing))
        )
    for purpose in TEST_PURPOSES:
        kinds = table[purpose]
        if not isinstance(kinds, (list, tuple)) or not kinds:
            raise ValueError(
                "policy mandatory_condition_kinds[%s] must be a non-empty sequence"
                % purpose
            )
        for kind in kinds:
            _require_choice(
                "policy mandatory_condition_kinds[%s] entry" % purpose,
                kind,
                CONDITION_KINDS,
            )
    sources = policy.get("admissible_method_sources")
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError("policy admissible_method_sources must be a non-empty sequence")
    for source in sources:
        _require_choice("policy admissible_method_sources entry", source, METHOD_SOURCES)
    documents = policy.get("governing_documents")
    if not isinstance(documents, (list, tuple)) or not documents:
        raise ValueError("policy governing_documents must be a non-empty sequence")
    for document in documents:
        _require_choice(
            "policy governing_documents entry", document, GOVERNING_DOCUMENTS
        )
    return policy


def illumination_intensity_ratio(
    measured_irradiance_w_per_m2, reference_irradiance_w_per_m2=AM0_REFERENCE_IRRADIANCE_W_PER_M2
):
    """Measured irradiance expressed as a fraction of the reference spectrum."""
    measured = _require_positive("measured_irradiance_w_per_m2", measured_irradiance_w_per_m2)
    reference = _require_positive(
        "reference_irradiance_w_per_m2", reference_irradiance_w_per_m2
    )
    return measured / reference


def condition_deviation(specified_value, actual_value):
    """Signed departure of the declared condition from the specified one."""
    specified = _require_number("specified_value", specified_value)
    actual = _require_number("actual_value", actual_value)
    return actual - specified


def condition_within_band(specified_value, tolerance, actual_value):
    """Whether the declared condition sits inside the drawing tolerance band."""
    band = _require_non_negative("tolerance", tolerance)
    return _at_most(abs(condition_deviation(specified_value, actual_value)), band)


def tolerance_utilisation(specified_value, tolerance, actual_value):
    """How much of the tolerance band the declared condition consumes."""
    band = _require_non_negative("tolerance", tolerance)
    deviation = abs(condition_deviation(specified_value, actual_value))
    if band == 0.0:
        return 0.0 if math.isclose(deviation, 0.0, abs_tol=_ABS_TOL) else 1.0
    return deviation / band


def evaluate_condition(condition):
    """Deviation, band check and band usage for one declared test condition."""
    if not isinstance(condition, dict):
        raise ValueError("condition must be a mapping, got %r" % (condition,))
    kind = _require_choice("condition kind", condition.get("kind"), CONDITION_KINDS)
    specified = _require_number("specified_value", condition.get("specified_value"))
    tolerance = _require_non_negative("tolerance", condition.get("tolerance"))
    actual = condition.get("actual_value")
    irradiance = condition.get("measured_irradiance_w_per_m2")
    findings = []
    if irradiance is not None:
        if kind != "illumination-intensity":
            raise ValueError(
                "measured_irradiance_w_per_m2 only applies to an illumination-intensity "
                "condition, got kind %r" % kind
            )
        if actual is not None:
            raise ValueError(
                "declare either actual_value or measured_irradiance_w_per_m2 for an "
                "illumination-intensity condition, not both"
            )
        actual = illumination_intensity_ratio(irradiance)
        findings.append(
            "illumination declared as %.1f W/m2 and read as %.4f of the reference "
            "spectrum" % (irradiance, actual)
        )
    if actual is None:
        raise ValueError("condition %s declares no value to check against the band" % kind)
    actual = _require_number("actual_value", actual)
    deviation = condition_deviation(specified, actual)
    within = condition_within_band(specified, tolerance, actual)
    if not within:
        findings.append(
            "%s condition deviates by %.4f against a tolerance of %.4f"
            % (kind, deviation, tolerance)
        )
    return {
        "kind": kind,
        "specified_value": specified,
        "actual_value": actual,
        "tolerance": tolerance,
        "deviation": deviation,
        "within_band": within,
        "tolerance_utilisation": tolerance_utilisation(specified, tolerance, actual),
        "findings": findings,
    }


def document_is_governing(document, policy=DEFAULT_TEST_GOVERNANCE_POLICY):
    """Whether the cited document carries the authority of the drawing."""
    validate_test_governance_policy(policy)
    _require_choice("governing_document", document, GOVERNING_DOCUMENTS)
    return document in tuple(policy["governing_documents"])


def method_admissibility(
    method_source,
    deviation_approval_reference=None,
    policy=DEFAULT_TEST_GOVERNANCE_POLICY,
):
    """Whether the declared method may stand as evidence against the drawing."""
    validate_test_governance_policy(policy)
    _require_choice("method_source", method_source, METHOD_SOURCES)
    findings = []
    if method_source in _APPROVAL_REQUIRED_SOURCES:
        if deviation_approval_reference is None or (
            isinstance(deviation_approval_reference, str)
            and not deviation_approval_reference.strip()
        ):
            raise ValueError(
                "method source %s cites no deviation_approval_reference" % method_source
            )
        reference = _require_text(
            "deviation_approval_reference", deviation_approval_reference
        )
        findings.append(
            "method substitutes an equivalent under approval %s" % reference
        )
    admissible = method_source in tuple(policy["admissible_method_sources"])
    if not admissible:
        findings.append(
            "method source %s does not carry the authority of the drawing" % method_source
        )
    return {
        "method_source": method_source,
        "admissible": admissible,
        "findings": findings,
    }


def missing_condition_kinds(purpose, conditions, policy=DEFAULT_TEST_GOVERNANCE_POLICY):
    """Condition kinds the purpose demands that the test never declares."""
    validate_test_governance_policy(policy)
    _require_choice("purpose", purpose, TEST_PURPOSES)
    if not isinstance(conditions, (list, tuple)) or not conditions:
        raise ValueError("conditions must be a non-empty sequence of mappings")
    declared = set()
    for condition in conditions:
        if not isinstance(condition, dict):
            raise ValueError("each condition must be a mapping, got %r" % (condition,))
        declared.add(
            _require_choice("condition kind", condition.get("kind"), CONDITION_KINDS)
        )
    mandatory = set(policy["mandatory_condition_kinds"][purpose])
    return sorted(mandatory - declared)


def evaluate_test(test, policy=DEFAULT_TEST_GOVERNANCE_POLICY):
    """Governance verdict for one declared test: document, method, conditions."""
    if not isinstance(test, dict):
        raise ValueError("test must be a mapping, got %r" % (test,))
    validate_test_governance_policy(policy)
    name = _require_text("test name", test.get("name"))
    purpose = _require_choice("test purpose", test.get("purpose"), TEST_PURPOSES)
    conditions = test.get("conditions")
    if not isinstance(conditions, (list, tuple)) or not conditions:
        raise ValueError("test %s declares no conditions" % name)
    evaluations = [evaluate_condition(condition) for condition in conditions]
    gaps = missing_condition_kinds(purpose, conditions, policy)
    governed = document_is_governing(test.get("governing_document"), policy)
    method = method_admissibility(
        test.get("method_source"), test.get("deviation_approval_reference"), policy
    )
    out_of_band = [record["kind"] for record in evaluations if not record["within_band"]]
    findings = []
    for record in evaluations:
        findings.extend(record["findings"])
    findings.extend(method["findings"])
    if not governed:
        findings.append(
            "test %s cites %s, which does not carry the authority of the drawing"
            % (name, test.get("governing_document"))
        )
    for kind in gaps:
        findings.append("test %s declares no %s condition" % (name, kind))
    if not governed:
        verdict = NOT_GOVERNED_BY_DRAWING
    elif not method["admissible"]:
        verdict = METHOD_NOT_ADMISSIBLE
    elif gaps:
        verdict = CONDITION_SET_INCOMPLETE
    elif out_of_band:
        verdict = CONDITION_OUT_OF_BAND
    else:
        verdict = TEST_GOVERNED
    governing_condition = max(
        evaluations, key=lambda record: record["tolerance_utilisation"]
    )
    return {
        "name": name,
        "purpose": purpose,
        "verdict": verdict,
        "governed": verdict == TEST_GOVERNED,
        "document_is_governing": governed,
        "method_admissible": method["admissible"],
        "condition_evaluations": evaluations,
        "out_of_band_conditions": out_of_band,
        "missing_condition_kinds": gaps,
        "governing_condition_kind": governing_condition["kind"],
        "findings": findings,
    }


def evaluate_test_matrix(case, policy=DEFAULT_TEST_GOVERNANCE_POLICY):
    """Full clause 5.2 sweep over a declared PVA test matrix."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    tests = case.get("tests")
    if not isinstance(tests, (list, tuple)) or not tests:
        raise ValueError("case tests must be a non-empty sequence of mappings")
    results = [evaluate_test(test, policy) for test in tests]
    grouped = {}
    for record in results:
        grouped.setdefault(record["verdict"], []).append(record["name"])
    governed = [record for record in results if record["governed"]]
    findings = []
    for record in results:
        findings.extend(record["findings"])
    all_governed = len(governed) == len(results)
    return {
        "verdict": PROGRAMME_GOVERNED if all_governed else PROGRAMME_NOT_GOVERNED,
        "test_results": results,
        "grouped_by_verdict": grouped,
        "governed_count": len(governed),
        "test_count": len(results),
        "governed_fraction": len(governed) / float(len(results)),
        "ungoverned_tests": [
            record["name"] for record in results if not record["governed"]
        ],
        "findings": findings,
    }
