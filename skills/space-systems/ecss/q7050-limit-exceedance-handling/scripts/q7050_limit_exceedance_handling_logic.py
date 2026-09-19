"""Handling of a cleanliness limit exceedance: impact, action, re-verification.

Anchor: ECSS-Q-ST-70-50C, the clause on handling results above the limit.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Establish that there is an exceedance at all, as a ratio of the measured
   result to the limit rather than as a difference, because the limits span
   orders of magnitude.
2. Weight that ratio by the sensitivity of the hardware exposed. The same
   ratio over a bare optic and over a structural bracket are not the same
   event, and the severity follows from the pair, not from the ratio alone.
3. Estimate what the exposure actually deposited, from the airborne
   concentration, the deposition velocity of the size of interest and the
   exposure duration, so the impact statement carries a number and not only
   an adjective.
4. Select the disposition the severity owes, constrained by whether the
   hardware can be cleaned and whether it can be re-verified afterwards --
   an uncleanable critical exposure is not dispositioned by cleaning it.
5. Require a stated number of consecutive conforming re-verifications, and
   grade the trailing run actually achieved against it: a conforming result
   after a non-conforming one restarts the run.
6. Grade the closure package for the pieces it is missing, so a disposition
   cannot be closed on a corrective action with no impact assessment behind
   it.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "SENSITIVITY_WEIGHTS",
    "SEVERITIES",
    "DISPOSITIONS",
    "CLOSURE_ITEMS",
    "require_real",
    "require_int",
    "exceedance_ratio",
    "is_exceedance",
    "sensitivity_weight",
    "severity_category",
    "deposition_number_per_m2",
    "select_disposition",
    "required_consecutive_reverifications",
    "grade_reverification",
    "closure_completeness",
    "assess_exceedance",
]

# A measured result landing exactly on its limit is not an exceedance; an
# exact equality can still land a few ULPs above. Absorb that here, never by
# raising the limit.
RATIO_TOLERANCE = 1e-9

# How much harder the same ratio bites on more sensitive hardware.
SENSITIVITY_WEIGHTS = {
    "tolerant": 0.5,
    "standard": 1.0,
    "sensitive": 2.0,
    "critical": 4.0,
}

SEVERITIES = ("none", "minor", "major", "critical")

DISPOSITIONS = (
    "accept-as-is",
    "clean-and-reverify",
    "engineering-assessment",
    "reject",
)

CLOSURE_ITEMS = (
    "impact_assessment",
    "root_cause",
    "corrective_action",
    "reverification",
    "approval",
)

# Weighted-ratio boundaries between the severity bands.
MINOR_CEILING = 2.0
MAJOR_CEILING = 10.0

# Consecutive conforming re-verifications each severity owes.
_REVERIFICATIONS = {"none": 0, "minor": 1, "major": 2, "critical": 3}


def require_real(value, label, positive=False, non_negative=False):
    """Return value as a float, rejecting booleans, strings and non-finites."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and result <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, result))
    if non_negative and result < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, result))
    return result


def require_int(value, label, non_negative=False, positive=False):
    """Return value as an int, rejecting booleans and floats."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if positive and value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    if non_negative and value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def exceedance_ratio(measured, limit):
    """Return the measured result as a multiple of its limit."""
    value = require_real(measured, "measured", non_negative=True)
    bound = require_real(limit, "limit", positive=True)
    return value / bound


def is_exceedance(measured, limit):
    """True when the measured result is above its limit, not merely on it."""
    ratio = exceedance_ratio(measured, limit)
    return ratio > 1.0 and not math.isclose(
        ratio, 1.0, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    )


def sensitivity_weight(sensitivity):
    """Return the weight of a hardware sensitivity category."""
    if sensitivity not in SENSITIVITY_WEIGHTS:
        raise ValueError(
            "sensitivity must be one of %s, got %r"
            % (tuple(sorted(SENSITIVITY_WEIGHTS)), sensitivity)
        )
    return SENSITIVITY_WEIGHTS[sensitivity]


def severity_category(measured, limit, sensitivity="standard"):
    """Categorize the severity from the exceedance ratio and the sensitivity."""
    ratio = exceedance_ratio(measured, limit)
    weight = sensitivity_weight(sensitivity)
    if not is_exceedance(measured, limit):
        return {
            "ratio": ratio,
            "weighted_ratio": ratio * weight,
            "sensitivity": sensitivity,
            "severity": "none",
        }
    weighted = ratio * weight
    if weighted <= MINOR_CEILING or math.isclose(
        weighted, MINOR_CEILING, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    ):
        severity = "minor"
    elif weighted <= MAJOR_CEILING or math.isclose(
        weighted, MAJOR_CEILING, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    ):
        severity = "major"
    else:
        severity = "critical"
    return {
        "ratio": ratio,
        "weighted_ratio": weighted,
        "sensitivity": sensitivity,
        "severity": severity,
    }


def deposition_number_per_m2(concentration_per_m3, deposition_velocity_m_s,
                             exposure_hours):
    """Estimate the areal number density the exposure deposited."""
    concentration = require_real(
        concentration_per_m3, "concentration_per_m3", non_negative=True
    )
    velocity = require_real(
        deposition_velocity_m_s, "deposition_velocity_m_s", positive=True
    )
    hours = require_real(exposure_hours, "exposure_hours", non_negative=True)
    return concentration * velocity * hours * 3600.0


def select_disposition(severity, cleanable=True, reverifiable=True):
    """Select the disposition a severity owes, given what the hardware permits."""
    if severity not in SEVERITIES:
        raise ValueError("severity must be one of %s, got %r" % (SEVERITIES, severity))
    for label, flag in (("cleanable", cleanable), ("reverifiable", reverifiable)):
        if not isinstance(flag, bool):
            raise ValueError("%s must be a boolean, got %r" % (label, flag))
    if severity == "none":
        return "accept-as-is"
    if not reverifiable:
        # Nothing can be shown to have been fixed, so the exposure has to be
        # argued on analysis or the item stood down.
        return "engineering-assessment" if severity == "minor" else "reject"
    if severity == "minor":
        return "clean-and-reverify" if cleanable else "engineering-assessment"
    if severity == "major":
        return "clean-and-reverify" if cleanable else "engineering-assessment"
    return "engineering-assessment" if cleanable else "reject"


def required_consecutive_reverifications(severity):
    """Return how many consecutive conforming re-verifications a severity owes."""
    if severity not in SEVERITIES:
        raise ValueError("severity must be one of %s, got %r" % (SEVERITIES, severity))
    return _REVERIFICATIONS[severity]


def grade_reverification(results, limit, required_consecutive):
    """Grade the trailing run of conforming re-verification results."""
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a sequence of measured values")
    required = require_int(required_consecutive, "required_consecutive",
                           non_negative=True)
    bound = require_real(limit, "limit", positive=True)
    values = [
        require_real(value, "results[%d]" % index, non_negative=True)
        for index, value in enumerate(results)
    ]
    run = 0
    for value in reversed(values):
        if is_exceedance(value, bound):
            break
        run += 1
    return {
        "results": values,
        "trailing_conforming_run": run,
        "required_consecutive": required,
        "satisfied": run >= required,
    }


def closure_completeness(package):
    """Grade an exceedance closure package for the pieces it is missing."""
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    present = []
    missing = []
    for item in CLOSURE_ITEMS:
        value = package.get(item)
        if value is None or value is False or value == "":
            missing.append(item)
        else:
            present.append(item)
    return {
        "present": present,
        "missing": missing,
        "fraction_complete": len(present) / len(CLOSURE_ITEMS),
        "complete": not missing,
    }


def assess_exceedance(spec):
    """Turn a limit exceedance into an impact, a disposition and a closure grade.

    spec keys: measured, limit, optional sensitivity, cleanable, reverifiable,
    exposure (concentration_per_m3, deposition_velocity_m_s, exposure_hours),
    reverification_results, closure_package.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("measured", "limit"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    severity = severity_category(
        spec["measured"], spec["limit"], spec.get("sensitivity", "standard")
    )
    cleanable = spec.get("cleanable", True)
    reverifiable = spec.get("reverifiable", True)
    disposition = select_disposition(severity["severity"], cleanable, reverifiable)
    required = required_consecutive_reverifications(severity["severity"])
    findings = []
    deposition = None
    exposure = spec.get("exposure")
    if exposure is not None:
        if not isinstance(exposure, dict):
            raise ValueError("spec['exposure'] must be a mapping")
        for key in ("concentration_per_m3", "deposition_velocity_m_s",
                    "exposure_hours"):
            if key not in exposure:
                raise ValueError("exposure missing required key '%s'" % key)
        deposition = deposition_number_per_m2(
            exposure["concentration_per_m3"],
            exposure["deposition_velocity_m_s"],
            exposure["exposure_hours"],
        )
    elif severity["severity"] != "none":
        findings.append(
            "no exposure data supplied; the impact statement carries an adjective "
            "and no deposited quantity"
        )
    reverification = grade_reverification(
        spec.get("reverification_results", []), spec["limit"], required
    )
    if not reverification["satisfied"]:
        findings.append(
            "re-verification shows %d consecutive conforming results; %d are owed "
            "for a %s exceedance"
            % (reverification["trailing_conforming_run"], required,
               severity["severity"])
        )
    closure = closure_completeness(spec.get("closure_package", {}))
    if severity["severity"] != "none" and not closure["complete"]:
        findings.append(
            "closure package is missing: %s" % ", ".join(closure["missing"])
        )
    if disposition == "reject":
        findings.append(
            "the exposure cannot be cleaned or re-verified at this severity; the "
            "item is not dispositionable by cleaning"
        )
    return {
        "severity": severity,
        "disposition": disposition,
        "deposited_per_m2": deposition,
        "reverification": reverification,
        "closure": closure,
        "findings": findings,
        "closed": severity["severity"] == "none" or not findings,
    }
