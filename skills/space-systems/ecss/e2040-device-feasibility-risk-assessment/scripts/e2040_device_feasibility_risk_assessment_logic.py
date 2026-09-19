#!/usr/bin/env python3
"""Device feasibility and risk assessment (ECSS-E-ST-20-40C clause 5.2.6).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The clause asks two questions at once and they have to be answered
together. Can the device actually be developed with the technology,
people, money and time available? And what is carried forward as risk if
the answer is a qualified yes?

* feasibility is judged driver by driver -- technology, resources,
  schedule, cost, supply -- and one driver reported as unachievable is
  enough to sink the development however comfortable the others look;
* technology readiness is the driver with a number behind it. A device
  entering architecture work below the readiness the programme requires
  is feasible only while a maturation action is actually named, and two
  readiness steps short is not recoverable inside the phase;
* risk is banded from a severity and a likelihood, and the band that
  matters is the RESIDUAL one, after the declared mitigation is applied.
  Banding the initial risk and then filing the mitigation separately is
  how an unacceptable residual reaches the next phase unnoticed;
* a mitigation with no owner is not a mitigation. It reduces the number
  on the page and nothing in the project.

Exposure is a mean of residual indices over the maximum index, so it is a
fraction that lands on representable boundaries only by accident;
comparisons against a tolerance absorb that rather than failing on it.
"""

import math

# Feasibility drivers the assessment has to cover.
FEASIBILITY_DRIVERS = ("technology", "resources", "schedule", "cost", "supply")

# Driver verdicts, worst last.
DRIVER_VERDICTS = ("achievable", "achievable-with-action", "unachievable")

_DRIVER_ALIASES = {
    "technology": "technology",
    "technical": "technology",
    "resources": "resources",
    "resource": "resources",
    "people": "resources",
    "schedule": "schedule",
    "time": "schedule",
    "cost": "cost",
    "budget": "cost",
    "supply": "supply",
    "supply chain": "supply",
    "procurement": "supply",
}

_VERDICT_ALIASES = {
    "achievable": "achievable",
    "yes": "achievable",
    "feasible": "achievable",
    "achievable-with-action": "achievable-with-action",
    "achievable with action": "achievable-with-action",
    "qualified": "achievable-with-action",
    "unachievable": "unachievable",
    "no": "unachievable",
    "infeasible": "unachievable",
}

# Severity and likelihood are both 1..5.
SCORE_MIN = 1
SCORE_MAX = 5
MAX_RISK_INDEX = SCORE_MAX * SCORE_MAX

_SEVERITY_ALIASES = {
    "negligible": 1,
    "minor": 2,
    "significant": 2,
    "major": 3,
    "critical": 4,
    "catastrophic": 5,
}

_LIKELIHOOD_ALIASES = {
    "minimum": 1,
    "low": 2,
    "medium": 3,
    "high": 4,
    "maximum": 5,
    "a": 1,
    "b": 2,
    "c": 3,
    "d": 4,
    "e": 5,
}

# Residual band per (severity, likelihood). Rows are severity 1..5,
# columns likelihood 1..5. Bands are ordered low < medium < high <
# unacceptable.
LOW = "low"
MEDIUM = "medium"
HIGH = "high"
UNACCEPTABLE = "unacceptable"
RISK_BANDS = (LOW, MEDIUM, HIGH, UNACCEPTABLE)

_BAND_TABLE = (
    (LOW, LOW, LOW, LOW, MEDIUM),
    (LOW, LOW, MEDIUM, MEDIUM, HIGH),
    (LOW, MEDIUM, MEDIUM, HIGH, HIGH),
    (MEDIUM, MEDIUM, HIGH, HIGH, UNACCEPTABLE),
    (MEDIUM, HIGH, HIGH, UNACCEPTABLE, UNACCEPTABLE),
)

# Readiness scale and the step short of the requirement that a maturation
# action can still recover inside the definition phase.
TRL_MIN = 1
TRL_MAX = 9
RECOVERABLE_TRL_GAP = 1

REL_TOL = 1e-12
ABS_TOL = 1e-18

_CASE_REQUIRED_KEYS = ("drivers", "risks")
_CASE_OPTIONAL_KEYS = ("technology_readiness", "required_readiness", "exposure_limit")
_DRIVER_KEYS = ("driver", "verdict", "action", "rationale")
_RISK_KEYS = ("id", "severity", "likelihood", "mitigation")
_MITIGATION_KEYS = ("owner", "severity_reduction", "likelihood_reduction", "summary")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(name, value):
    return " ".join(_text(name, value).lower().replace("_", " ").split())


def _whole(name, value, low, high):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if not low <= value <= high:
        raise ValueError("%s must lie in [%d, %d], got %d" % (name, low, high, value))
    return value


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def normalize_driver(value):
    """Fold a feasibility driver name onto one of the five covered."""
    key = _key("driver", value)
    if key in _DRIVER_ALIASES:
        return _DRIVER_ALIASES[key]
    raise ValueError(
        "unknown feasibility driver %r; use one of %s"
        % (value, ", ".join(FEASIBILITY_DRIVERS))
    )


def normalize_verdict(value):
    """Fold a driver verdict onto one of the three recognised outcomes."""
    key = _key("verdict", value)
    if key in _VERDICT_ALIASES:
        return _VERDICT_ALIASES[key]
    raise ValueError(
        "unknown driver verdict %r; use one of %s"
        % (value, ", ".join(DRIVER_VERDICTS))
    )


def normalize_score(name, value):
    """Fold a severity or likelihood onto the 1..5 scale."""
    if isinstance(value, bool):
        raise ValueError("%s must be a score, got %r" % (name, value))
    if isinstance(value, int):
        return _whole(name, value, SCORE_MIN, SCORE_MAX)
    key = _key(name, value)
    table = _SEVERITY_ALIASES if name == "severity" else _LIKELIHOOD_ALIASES
    if key.startswith("s") and key[1:].isdigit() and name == "severity":
        return _whole(name, int(key[1:]), SCORE_MIN, SCORE_MAX)
    if key.isdigit():
        return _whole(name, int(key), SCORE_MIN, SCORE_MAX)
    if key in table:
        return table[key]
    raise ValueError("unknown %s %r; use %d..%d" % (name, value, SCORE_MIN, SCORE_MAX))


def risk_index(severity, likelihood):
    """Index of a risk: severity times likelihood on the 1..5 scales."""
    return normalize_score("severity", severity) * normalize_score(
        "likelihood", likelihood
    )


def risk_band(severity, likelihood):
    """Band a risk from its severity and likelihood."""
    row = normalize_score("severity", severity) - 1
    column = normalize_score("likelihood", likelihood) - 1
    return _BAND_TABLE[row][column]


def band_rank(band):
    """Ordinal of a band, so two bands can be compared."""
    name = _key("band", band)
    if name not in RISK_BANDS:
        raise ValueError("unknown risk band %r; use one of %s" % (band, ", ".join(RISK_BANDS)))
    return RISK_BANDS.index(name)


def validate_mitigation(mitigation, where="mitigation"):
    """Check a mitigation block and return its owner and reductions."""
    if mitigation is None:
        return None
    if not isinstance(mitigation, dict):
        raise ValueError("%s must be a mapping" % where)
    unknown = sorted(set(mitigation) - set(_MITIGATION_KEYS))
    if unknown:
        raise ValueError("%s has unknown keys: %s" % (where, ", ".join(unknown)))
    return {
        "owner": _text("%s.owner" % where, mitigation.get("owner", ""), allow_empty=True),
        "severity_reduction": _whole(
            "%s.severity_reduction" % where,
            mitigation.get("severity_reduction", 0),
            0,
            SCORE_MAX - 1,
        ),
        "likelihood_reduction": _whole(
            "%s.likelihood_reduction" % where,
            mitigation.get("likelihood_reduction", 0),
            0,
            SCORE_MAX - 1,
        ),
        "summary": _text("%s.summary" % where, mitigation.get("summary", ""), allow_empty=True),
    }


def residual_scores(severity, likelihood, mitigation):
    """Severity and likelihood left after the declared mitigation."""
    sev = normalize_score("severity", severity)
    lik = normalize_score("likelihood", likelihood)
    resolved = validate_mitigation(mitigation)
    if resolved is None:
        return (sev, lik)
    sev = max(SCORE_MIN, sev - resolved["severity_reduction"])
    lik = max(SCORE_MIN, lik - resolved["likelihood_reduction"])
    return (sev, lik)


def validate_drivers(entries):
    """Check the driver list and return it folded, one entry per driver."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("drivers must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("drivers[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_DRIVER_KEYS))
        if unknown:
            raise ValueError("drivers[%d] has unknown keys: %s" % (index, ", ".join(unknown)))
        for key in ("driver", "verdict"):
            if key not in entry:
                raise ValueError("drivers[%d] missing key: %s" % (index, key))
        name = normalize_driver(entry["driver"])
        if name in resolved:
            raise ValueError("duplicate feasibility driver %r" % name)
        resolved[name] = {
            "driver": name,
            "verdict": normalize_verdict(entry["verdict"]),
            "action": _text("drivers[%d].action" % index, entry.get("action", ""), allow_empty=True),
            "rationale": _text(
                "drivers[%d].rationale" % index, entry.get("rationale", ""), allow_empty=True
            ),
        }
    return resolved


def validate_risks(entries):
    """Check the risk register and return it resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("risks must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("risks[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_RISK_KEYS))
        if unknown:
            raise ValueError("risks[%d] has unknown keys: %s" % (index, ", ".join(unknown)))
        for key in ("id", "severity", "likelihood"):
            if key not in entry:
                raise ValueError("risks[%d] missing key: %s" % (index, key))
        risk_id = _text("risks[%d].id" % index, entry["id"])
        if risk_id in seen:
            raise ValueError("duplicate risk id %r" % risk_id)
        seen.add(risk_id)
        severity = normalize_score("severity", entry["severity"])
        likelihood = normalize_score("likelihood", entry["likelihood"])
        mitigation = validate_mitigation(entry.get("mitigation"), "risks[%d].mitigation" % index)
        res_sev, res_lik = residual_scores(severity, likelihood, entry.get("mitigation"))
        resolved.append(
            {
                "id": risk_id,
                "severity": severity,
                "likelihood": likelihood,
                "initial_index": severity * likelihood,
                "initial_band": risk_band(severity, likelihood),
                "residual_severity": res_sev,
                "residual_likelihood": res_lik,
                "residual_index": res_sev * res_lik,
                "residual_band": risk_band(res_sev, res_lik),
                "mitigation": mitigation,
            }
        )
    return resolved


def risk_exposure(risks):
    """Mean residual index over the maximum index, as a fraction."""
    if not risks:
        raise ValueError("risk_exposure needs at least one risk")
    total = sum(r["residual_index"] for r in risks)
    return total / (len(risks) * MAX_RISK_INDEX)


def within_exposure_limit(exposure, limit):
    """True when exposure sits at or under the limit, exact landings included."""
    exposure = _fraction("exposure", exposure)
    limit = _fraction("limit", limit)
    return exposure < limit or math.isclose(exposure, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def readiness_gap(actual, required):
    """Readiness steps the device is short of what the programme requires."""
    actual = _whole("technology_readiness", actual, TRL_MIN, TRL_MAX)
    required = _whole("required_readiness", required, TRL_MIN, TRL_MAX)
    return max(0, required - actual)


def assess_feasibility(case):
    """Full clause 5.2.6 judgement on one device development case.

    Returns the folded drivers, the banded risk register, the exposure and
    the verdict, together with every finding that shaped it.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping of drivers, risks and readiness")
    known = set(_CASE_REQUIRED_KEYS) | set(_CASE_OPTIONAL_KEYS)
    unknown = sorted(set(case) - known)
    if unknown:
        raise ValueError("unknown case keys: %s" % ", ".join(unknown))
    missing = [key for key in _CASE_REQUIRED_KEYS if key not in case]
    if missing:
        raise ValueError("case missing required keys: %s" % ", ".join(missing))

    drivers = validate_drivers(case["drivers"])
    risks = validate_risks(case["risks"])
    if not risks:
        raise ValueError("case must carry at least one risk to assess")

    findings = []
    blocking = False
    qualified = False

    for name in FEASIBILITY_DRIVERS:
        if name not in drivers:
            findings.append(
                {
                    "code": "driver-not-assessed",
                    "driver": name,
                    "detail": "the %s driver carries no verdict, so feasibility is "
                    "asserted over a gap" % name,
                }
            )
            blocking = True
            continue
        entry = drivers[name]
        if entry["verdict"] == "unachievable":
            findings.append(
                {
                    "code": "driver-unachievable",
                    "driver": name,
                    "detail": "the %s driver is reported unachievable, which sinks the "
                    "development whatever the other drivers say" % name,
                }
            )
            blocking = True
        elif entry["verdict"] == "achievable-with-action":
            qualified = True
            if not entry["action"]:
                findings.append(
                    {
                        "code": "qualified-driver-without-action",
                        "driver": name,
                        "detail": "the %s driver is achievable only with an action and "
                        "no action is named" % name,
                    }
                )
                blocking = True

    readiness = case.get("technology_readiness")
    required = case.get("required_readiness")
    gap = None
    if readiness is not None and required is not None:
        gap = readiness_gap(readiness, required)
        if gap > RECOVERABLE_TRL_GAP:
            findings.append(
                {
                    "code": "readiness-gap-not-recoverable",
                    "gap": gap,
                    "detail": "the device is %d readiness steps short of the required "
                    "level, more than a maturation action recovers in the phase" % gap,
                }
            )
            blocking = True
        elif gap > 0:
            qualified = True
            technology = drivers.get("technology")
            if technology is None or not technology["action"]:
                findings.append(
                    {
                        "code": "readiness-gap-without-maturation-action",
                        "gap": gap,
                        "detail": "the device is %d readiness step short and the "
                        "technology driver names no maturation action" % gap,
                    }
                )
                blocking = True

    for risk in risks:
        rank = band_rank(risk["residual_band"])
        if rank == band_rank(UNACCEPTABLE):
            findings.append(
                {
                    "code": "residual-risk-unacceptable",
                    "risk": risk["id"],
                    "band": risk["residual_band"],
                    "detail": "risk %s still bands %s after mitigation and cannot be "
                    "carried into architecture work" % (risk["id"], risk["residual_band"]),
                }
            )
            blocking = True
        elif rank == band_rank(HIGH):
            qualified = True
            findings.append(
                {
                    "code": "residual-risk-high",
                    "risk": risk["id"],
                    "band": risk["residual_band"],
                    "detail": "risk %s bands %s after mitigation and needs an owned "
                    "action carried forward" % (risk["id"], risk["residual_band"]),
                }
            )
        if risk["mitigation"] is not None and not risk["mitigation"]["owner"]:
            findings.append(
                {
                    "code": "mitigation-without-owner",
                    "risk": risk["id"],
                    "detail": "the mitigation on risk %s reduces the band with nobody "
                    "accountable for delivering it" % risk["id"],
                }
            )
            blocking = True
        if (
            risk["mitigation"] is None
            and band_rank(risk["initial_band"]) >= band_rank(HIGH)
        ):
            findings.append(
                {
                    "code": "high-risk-without-mitigation",
                    "risk": risk["id"],
                    "detail": "risk %s bands %s and carries no mitigation at all"
                    % (risk["id"], risk["initial_band"]),
                }
            )
            blocking = True

    exposure = risk_exposure(risks)
    limit = case.get("exposure_limit")
    if limit is not None:
        limit_value = _fraction("exposure_limit", limit)
        if not within_exposure_limit(exposure, limit_value):
            findings.append(
                {
                    "code": "exposure-limit-exceeded",
                    "exposure": exposure,
                    "limit": limit_value,
                    "detail": "residual exposure reaches %.1f %% against a %.1f %% limit"
                    % (100.0 * exposure, 100.0 * limit_value),
                }
            )
            blocking = True

    if blocking:
        verdict = "not-feasible"
    elif qualified or findings:
        verdict = "feasible-with-actions"
    else:
        verdict = "feasible"

    return {
        "drivers": drivers,
        "risks": risks,
        "readiness_gap": gap,
        "risk_exposure": exposure,
        "worst_residual_band": max(
            (r["residual_band"] for r in risks), key=band_rank
        ),
        "findings": findings,
        "verdict": verdict,
        "feasible": verdict != "not-feasible",
    }
