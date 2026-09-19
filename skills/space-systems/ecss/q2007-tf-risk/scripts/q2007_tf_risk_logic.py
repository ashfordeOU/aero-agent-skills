#!/usr/bin/env python3
"""Hazard identification and risk assessment of a test facility.

Anchor: ECSS-Q-ST-20-07 clause 5.6.5, the requirement that the hazards
a test facility presents are identified and their risk assessed, with
the residual risk carried into the safety case. The procedure below is
a paraphrase into implementable steps; no standard text is reproduced.

Four things follow from what the clause is for.

Identification comes before assessment. A facility owes a declared set
of hazard categories for what it actually operates, and an assessment
covering fewer of them is short however careful the hazards it did
cover are.

Risk is a pair placed in a band, not a number. Severity and likelihood
indices give a product, the band table turns that product into the
band, and the band is what the acceptance decision uses, because the
band table is where the test centre's tolerance is written down.

Only implemented mitigations may be credited. A planned interlock
reduces nothing on the day of the run, and a mitigation cannot drive an
index below the floor of its own scale; an unclamped credit makes a
severe hazard vanish arithmetically.

Above the acceptance line a residual needs a named authority. Naming
records who carries an undesirable risk; it does not move the band, so
a signature against an unacceptable residual is itself a finding.

The policy numbers below are declared test-centre values, not physical
constants: a test centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BAND_ACCEPTABLE = "test-facility-risk-band-acceptable"
BAND_UNDESIRABLE = "test-facility-risk-band-undesirable"
BAND_UNACCEPTABLE = "test-facility-risk-band-unacceptable"

HAZARDS_NOT_IDENTIFIED = "test-facility-hazards-not-identified"
SAFETY_CASE_STALE = "test-facility-safety-case-stale"
RESIDUAL_UNACCEPTABLE = "test-facility-residual-risk-unacceptable"
ACCEPTANCE_AUTHORITY_MISSING = "test-facility-residual-risk-not-accepted"
CATEGORY_COVERAGE_SHORT = "test-facility-hazard-category-coverage-short"
RISK_REDUCTION_OUTSTANDING = "test-facility-risk-reduction-outstanding"
RESIDUAL_RISK_ACCEPTED = "test-facility-residual-risk-accepted"

DEFAULT_RISK_POLICY = {
    "severity_min": 1,
    "severity_max": 5,
    "likelihood_min": 1,
    "likelihood_max": 5,
    "undesirable_threshold": 6,
    "unacceptable_threshold": 15,
    "acceptance_line": 6,
    "review_interval_days": 365,
    "min_category_coverage": 1.0,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    count = _require_count(name, value)
    if count == 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return count


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    label = value.strip()
    if not label:
        raise ValueError("%s must not be blank" % name)
    return label


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_risk_policy(policy):
    """Check the scales, the band table and the acceptance line."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for low, high in (
        ("severity_min", "severity_max"),
        ("likelihood_min", "likelihood_max"),
    ):
        floor = _require_positive_count(low, policy.get(low))
        ceiling = _require_positive_count(high, policy.get(high))
        if ceiling <= floor:
            raise ValueError(
                "%s must sit above %s, got %r and %r"
                % (high, low, policy.get(high), policy.get(low))
            )
    undesirable = _require_positive_count(
        "undesirable_threshold", policy.get("undesirable_threshold")
    )
    unacceptable = _require_positive_count(
        "unacceptable_threshold", policy.get("unacceptable_threshold")
    )
    if unacceptable <= undesirable:
        raise ValueError(
            "the band thresholds do not ascend: undesirable %r against "
            "unacceptable %r" % (undesirable, unacceptable)
        )
    _require_positive_count("acceptance_line", policy.get("acceptance_line"))
    _require_positive_count(
        "review_interval_days", policy.get("review_interval_days")
    )
    _require_fraction(
        "min_category_coverage", policy.get("min_category_coverage")
    )
    return policy


def risk_band(index, policy=None):
    """Turn a severity-likelihood index product into its band."""
    policy = validate_risk_policy(policy or DEFAULT_RISK_POLICY)
    value = _require_count("risk index", index)
    if value >= int(policy["unacceptable_threshold"]):
        return BAND_UNACCEPTABLE
    if value >= int(policy["undesirable_threshold"]):
        return BAND_UNDESIRABLE
    return BAND_ACCEPTABLE


def validate_mitigation(mitigation, policy=None):
    """Read one mitigation: what it moves, by how many matrix steps."""
    policy = validate_risk_policy(policy or DEFAULT_RISK_POLICY)
    if not isinstance(mitigation, dict):
        raise ValueError("mitigation must be a mapping, got %r" % (mitigation,))
    target = _require_label("target", mitigation.get("target"))
    if target not in ("severity", "likelihood"):
        raise ValueError(
            "a mitigation moves severity or likelihood, got %r" % (target,)
        )
    return {
        "mitigation_id": _require_label(
            "mitigation_id", mitigation.get("mitigation_id")
        ),
        "target": target,
        "steps": _require_positive_count("steps", mitigation.get("steps")),
        "implemented": _require_flag(
            "implemented", mitigation.get("implemented", False)
        ),
    }


def validate_hazard(hazard, policy=None):
    """Read one facility hazard and the mitigations declared against it."""
    policy = validate_risk_policy(policy or DEFAULT_RISK_POLICY)
    if not isinstance(hazard, dict):
        raise ValueError("hazard must be a mapping, got %r" % (hazard,))
    severity = _require_count("severity", hazard.get("severity"))
    likelihood = _require_count("likelihood", hazard.get("likelihood"))
    if not int(policy["severity_min"]) <= severity <= int(policy["severity_max"]):
        raise ValueError(
            "severity %r sits outside the scale %r to %r"
            % (severity, policy["severity_min"], policy["severity_max"])
        )
    if (
        not int(policy["likelihood_min"])
        <= likelihood
        <= int(policy["likelihood_max"])
    ):
        raise ValueError(
            "likelihood %r sits outside the scale %r to %r"
            % (likelihood, policy["likelihood_min"], policy["likelihood_max"])
        )
    mitigations = hazard.get("mitigations", ())
    if not isinstance(mitigations, (list, tuple)):
        raise ValueError("mitigations must be a sequence of mitigation records")
    accepted_by = hazard.get("accepted_by")
    if accepted_by is not None:
        accepted_by = _require_label("accepted_by", accepted_by)
    return {
        "hazard_id": _require_label("hazard_id", hazard.get("hazard_id")),
        "category": _require_label("category", hazard.get("category")),
        "severity": severity,
        "likelihood": likelihood,
        "mitigations": tuple(
            validate_mitigation(item, policy) for item in mitigations
        ),
        "accepted_by": accepted_by,
    }


def validate_hazards(hazards, policy=None):
    """Read every hazard, refusing the same hazard label twice."""
    if not isinstance(hazards, (list, tuple)):
        raise ValueError("hazards must be a sequence of hazard records")
    checked = []
    seen = set()
    for hazard in hazards:
        record = validate_hazard(hazard, policy)
        if record["hazard_id"] in seen:
            raise ValueError("hazard %r appears twice" % record["hazard_id"])
        seen.add(record["hazard_id"])
        checked.append(record)
    if not checked:
        raise ValueError("the assessment identifies no hazards at all")
    return tuple(checked)


def initial_index(hazard, policy=None):
    """Severity times likelihood before any mitigation is credited."""
    record = validate_hazard(hazard, policy)
    return record["severity"] * record["likelihood"]


def residual_indices(hazard, policy=None):
    """Severity and likelihood after the implemented mitigations only."""
    policy = validate_risk_policy(policy or DEFAULT_RISK_POLICY)
    record = validate_hazard(hazard, policy)
    severity = record["severity"]
    likelihood = record["likelihood"]
    for mitigation in record["mitigations"]:
        if not mitigation["implemented"]:
            continue
        if mitigation["target"] == "severity":
            severity = max(
                int(policy["severity_min"]), severity - mitigation["steps"]
            )
        else:
            likelihood = max(
                int(policy["likelihood_min"]), likelihood - mitigation["steps"]
            )
    return severity, likelihood


def residual_index(hazard, policy=None):
    """Residual severity-likelihood product after implemented mitigations."""
    severity, likelihood = residual_indices(hazard, policy)
    return severity * likelihood


def planned_mitigations(hazard, policy=None):
    """Mitigations declared but not yet implemented at the facility."""
    record = validate_hazard(hazard, policy)
    return tuple(
        mitigation["mitigation_id"]
        for mitigation in record["mitigations"]
        if not mitigation["implemented"]
    )


def category_coverage(hazards, required_categories, policy=None):
    """Share of the categories the facility operates that were assessed."""
    if not isinstance(required_categories, (list, tuple, set, frozenset)):
        raise ValueError("required_categories must be a sequence of labels")
    required = {
        _require_label("required category", item) for item in required_categories
    }
    if not required:
        raise ValueError("the facility declares no hazard categories to cover")
    covered = {record["category"] for record in validate_hazards(hazards, policy)}
    return len(required & covered) / float(len(required))


def uncovered_categories(hazards, required_categories, policy=None):
    """Categories the facility operates that no hazard record assessed."""
    required = {
        _require_label("required category", item) for item in required_categories
    }
    covered = {record["category"] for record in validate_hazards(hazards, policy)}
    return tuple(sorted(required - covered))


def safety_case_is_current(
    assessed_day, as_of_day, last_modification_day=None, policy=None
):
    """True when the assessment postdates the facility and its interval."""
    policy = validate_risk_policy(policy or DEFAULT_RISK_POLICY)
    day = _require_count("as_of_day", as_of_day)
    if assessed_day is None:
        return False
    assessed = _require_count("assessed_day", assessed_day)
    if assessed > day:
        raise ValueError(
            "assessed_day %d sits after as_of_day %d" % (assessed, day)
        )
    if last_modification_day is not None:
        modified = _require_count("last_modification_day", last_modification_day)
        if modified > assessed:
            return False
    return (day - assessed) <= int(policy["review_interval_days"])


def assess_facility_risk(case):
    """Grade a facility risk assessment and say what its residual obliges."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_risk_policy(case.get("policy") or DEFAULT_RISK_POLICY)

    findings = []
    advisories = []
    result = {
        "hazards_assessed": 0,
        "category_coverage": None,
        "uncovered_categories": (),
        "safety_case_current": False,
        "hazard_bands": (),
        "unacceptable": (),
        "unaccepted": (),
        "planned_mitigations": (),
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    assessment = case.get("assessment")
    if assessment is None:
        findings.append(
            "no risk assessment was supplied, so the facility hazards stand "
            "unidentified"
        )
        result["verdict"] = HAZARDS_NOT_IDENTIFIED
        return result
    if not isinstance(assessment, dict):
        raise ValueError("assessment must be a mapping, got %r" % (assessment,))

    hazards = assessment.get("hazards")
    if not hazards:
        findings.append(
            "the assessment identifies no hazards, which is an empty sheet "
            "rather than a facility without hazards"
        )
        result["verdict"] = HAZARDS_NOT_IDENTIFIED
        return result

    checked = validate_hazards(hazards, policy)
    result["hazards_assessed"] = len(checked)

    as_of_day = _require_count("as_of_day", assessment.get("as_of_day"))
    current = safety_case_is_current(
        assessment.get("assessed_day"),
        as_of_day,
        assessment.get("last_modification_day"),
        policy,
    )
    result["safety_case_current"] = current
    if not current:
        findings.append(
            "the safety case predates the last facility modification or its "
            "%d day review interval, so it describes a facility that has "
            "moved on" % int(policy["review_interval_days"])
        )
        result["verdict"] = SAFETY_CASE_STALE
        return result

    bands = []
    unacceptable = []
    unaccepted = []
    planned = []
    for record in checked:
        residual = residual_index(record, policy)
        band = risk_band(residual, policy)
        bands.append(
            {
                "hazard_id": record["hazard_id"],
                "category": record["category"],
                "initial_index": initial_index(record, policy),
                "residual_index": residual,
                "residual_band": band,
            }
        )
        if band == BAND_UNACCEPTABLE:
            unacceptable.append(record["hazard_id"])
        elif residual >= int(policy["acceptance_line"]) and not record["accepted_by"]:
            unaccepted.append(record["hazard_id"])
        planned.extend(planned_mitigations(record, policy))

    result["hazard_bands"] = tuple(bands)
    result["unacceptable"] = tuple(sorted(unacceptable))
    result["unaccepted"] = tuple(sorted(unaccepted))
    result["planned_mitigations"] = tuple(sorted(planned))

    required = assessment.get("required_categories")
    if required:
        result["category_coverage"] = category_coverage(checked, required, policy)
        result["uncovered_categories"] = uncovered_categories(
            checked, required, policy
        )

    if unacceptable:
        findings.append(
            "hazard(s) %s sit in the unacceptable band after the implemented "
            "mitigations, which no signature moves"
            % ", ".join(result["unacceptable"])
        )
        result["verdict"] = RESIDUAL_UNACCEPTABLE
        return result

    if unaccepted:
        findings.append(
            "hazard(s) %s carry a residual at or above the acceptance line "
            "with nobody recorded as accepting it"
            % ", ".join(result["unaccepted"])
        )
        result["verdict"] = ACCEPTANCE_AUTHORITY_MISSING
        return result

    if result["category_coverage"] is not None and not _at_least(
        result["category_coverage"], float(policy["min_category_coverage"])
    ):
        findings.append(
            "the assessment covers %.3g of the hazard categories the facility "
            "operates; %s were never assessed"
            % (
                result["category_coverage"],
                ", ".join(result["uncovered_categories"]),
            )
        )
        result["verdict"] = CATEGORY_COVERAGE_SHORT
        return result

    if result["planned_mitigations"]:
        advisories.append(
            "mitigation(s) %s are declared but not implemented, so they were "
            "credited with nothing and remain outstanding"
            % ", ".join(result["planned_mitigations"])
        )
        result["verdict"] = RISK_REDUCTION_OUTSTANDING
        return result

    result["verdict"] = RESIDUAL_RISK_ACCEPTED
    return result
