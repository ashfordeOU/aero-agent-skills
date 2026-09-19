"""Proof pressure test definition for two-phase heat transport equipment.

Anchor: ECSS-E-ST-31-02C clause 5.6.5 (proof pressure test: factor, test
temperature, acceptance criteria). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. The proof pressure is the maximum design pressure multiplied by the proof
   factor for the article category. A factor at or below unity is not a proof
   and is refused rather than applied.
2. When the test is run at a temperature other than the design temperature,
   the pressure is corrected by the ratio of the material allowable at the
   test temperature to the allowable at the design temperature, so the test
   imposes the same fraction of capability the design point sees.
3. The applied pressure is graded as a window, not a floor: it has to reach
   the corrected proof pressure and it has to stay below the pressure that
   yields the article, because a proof test that yields the hardware has
   destroyed the thing it was verifying.
4. The hold duration is graded against the minimum hold.
5. Acceptance is the conjunction of four conditions: the pressure window was
   met, the hold was long enough, no leakage was detected, and the permanent
   set left behind is within its allowance.
"""

import math

__all__ = [
    "PRESSURE_TOLERANCE",
    "MIN_PROOF_FACTOR",
    "DEFAULT_MINIMUM_HOLD_S",
    "DEFAULT_PERMANENT_SET_ALLOWANCE",
    "require_real",
    "require_positive",
    "require_non_negative",
    "validate_proof_factor",
    "required_proof_pressure_pa",
    "temperature_correction_factor",
    "corrected_proof_pressure_pa",
    "assess_applied_pressure",
    "assess_hold_duration",
    "permanent_set_fraction",
    "assess_permanent_set",
    "assess_leakage",
    "assess_proof_pressure_test",
]

# Pressure, duration and strain grades are float comparisons a correct test
# lands exactly on. Absorb the representation error, never the requirement.
PRESSURE_TOLERANCE = 1e-9

# A proof factor is a multiplier above the maximum design pressure; at or
# below unity the test proves nothing the service condition has not already.
MIN_PROOF_FACTOR = 1.0

DEFAULT_MINIMUM_HOLD_S = 300.0

# Permanent set left after the proof hold, as a fraction of the gauge
# dimension it was measured over.
DEFAULT_PERMANENT_SET_ALLOWANCE = 0.002


def require_real(label, value):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def require_positive(label, value):
    """Return value as a strictly positive finite float or raise ValueError."""
    out = require_real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def require_non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    out = require_real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def _at_least(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value > limit or math.isclose(value, limit, rel_tol=1e-12,
                                         abs_tol=PRESSURE_TOLERANCE)


def _at_most(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value < limit or math.isclose(value, limit, rel_tol=1e-12,
                                         abs_tol=PRESSURE_TOLERANCE)


def validate_proof_factor(proof_factor):
    """Return a usable proof factor or raise ValueError."""
    factor = require_positive("proof_factor", proof_factor)
    if _at_most(factor, MIN_PROOF_FACTOR):
        raise ValueError(
            "proof_factor must exceed %.3f to be a proof, got %r"
            % (MIN_PROOF_FACTOR, proof_factor)
        )
    return factor


def required_proof_pressure_pa(mdp_pa, proof_factor):
    """Return the proof pressure at the design temperature."""
    mdp = require_positive("mdp_pa", mdp_pa)
    factor = validate_proof_factor(proof_factor)
    return mdp * factor


def temperature_correction_factor(allowable_at_test_pa, allowable_at_design_pa):
    """Return the test-temperature correction on the proof pressure.

    The factor is the material allowable at the test temperature divided by
    the allowable at the design temperature: a colder, stronger test article
    needs more pressure to reach the same fraction of its capability.
    """
    at_test = require_positive("allowable_at_test_pa", allowable_at_test_pa)
    at_design = require_positive("allowable_at_design_pa", allowable_at_design_pa)
    return at_test / at_design


def corrected_proof_pressure_pa(mdp_pa, proof_factor, allowable_at_test_pa=None,
                                allowable_at_design_pa=None):
    """Return the proof pressure to apply at the actual test temperature."""
    base = required_proof_pressure_pa(mdp_pa, proof_factor)
    if allowable_at_test_pa is None and allowable_at_design_pa is None:
        return base
    if allowable_at_test_pa is None or allowable_at_design_pa is None:
        raise ValueError(
            "both material allowables are needed to correct for test temperature"
        )
    return base * temperature_correction_factor(allowable_at_test_pa,
                                                allowable_at_design_pa)


def assess_applied_pressure(applied_pa, target_pa, yield_pressure_pa=None):
    """Grade the applied pressure as a window between the target and yield."""
    applied = require_positive("applied_pa", applied_pa)
    target = require_positive("target_pa", target_pa)
    reached = _at_least(applied, target)
    below_yield = True
    findings = []
    if not reached:
        findings.append("applied pressure %.4f Pa did not reach the proof target %.4f Pa"
                        % (applied, target))
    yield_value = None
    if yield_pressure_pa is not None:
        yield_value = require_positive("yield_pressure_pa", yield_pressure_pa)
        if _at_most(yield_value, target):
            raise ValueError(
                "yield pressure %.4f Pa is not above the proof target %.4f Pa; "
                "the article cannot be proof tested as specified"
                % (yield_value, target)
            )
        below_yield = _at_most(applied, yield_value)
        if not below_yield:
            findings.append(
                "applied pressure %.4f Pa is above the yield pressure %.4f Pa; "
                "the proof test damaged the article" % (applied, yield_value)
            )
    return {
        "applied_pa": applied,
        "target_pa": target,
        "yield_pressure_pa": yield_value,
        "overshoot_pa": applied - target,
        "reached_target": reached,
        "below_yield": below_yield,
        "compliant": reached and below_yield,
        "findings": findings,
    }


def assess_hold_duration(applied_hold_s, minimum_hold_s=DEFAULT_MINIMUM_HOLD_S):
    """Grade the proof hold duration against the minimum."""
    applied = require_non_negative("applied_hold_s", applied_hold_s)
    minimum = require_positive("minimum_hold_s", minimum_hold_s)
    compliant = _at_least(applied, minimum)
    findings = []
    if not compliant:
        findings.append("proof hold of %.4f s is shorter than the required %.4f s"
                        % (applied, minimum))
    return {
        "applied_hold_s": applied,
        "minimum_hold_s": minimum,
        "margin_s": applied - minimum,
        "compliant": compliant,
        "findings": findings,
    }


def permanent_set_fraction(gauge_before, gauge_after):
    """Return the permanent set as a fraction of the original gauge length."""
    before = require_positive("gauge_before", gauge_before)
    after = require_positive("gauge_after", gauge_after)
    return (after - before) / before


def assess_permanent_set(gauge_before, gauge_after,
                         allowance=DEFAULT_PERMANENT_SET_ALLOWANCE):
    """Grade the permanent deformation left by the proof hold."""
    limit = require_positive("allowance", allowance)
    fraction = permanent_set_fraction(gauge_before, gauge_after)
    magnitude = abs(fraction)
    compliant = _at_most(magnitude, limit)
    findings = []
    if fraction < -PRESSURE_TOLERANCE:
        findings.append("gauge shrank after the proof hold; the measurement or the "
                        "reference dimension is suspect")
    if not compliant:
        findings.append("permanent set %.6f exceeds the allowance %.6f"
                        % (magnitude, limit))
    return {
        "permanent_set_fraction": fraction,
        "magnitude": magnitude,
        "allowance": limit,
        "compliant": compliant and fraction >= -PRESSURE_TOLERANCE,
        "findings": findings,
    }


def assess_leakage(leak_detected):
    """Grade the leakage observation taken during and after the proof hold."""
    if not isinstance(leak_detected, bool):
        raise ValueError("leak_detected must be a boolean observation, got %r"
                         % (leak_detected,))
    findings = []
    if leak_detected:
        findings.append("leakage observed at proof pressure; the article is rejected")
    return {
        "leak_detected": leak_detected,
        "compliant": not leak_detected,
        "findings": findings,
    }


def assess_proof_pressure_test(spec):
    """Run the whole clause 5.6.5 proof pressure test assessment.

    spec keys: mdp_pa, proof_factor, applied_pa, applied_hold_s,
    gauge_before, gauge_after, leak_detected; optional
    allowable_at_test_pa, allowable_at_design_pa, yield_pressure_pa,
    minimum_hold_s, permanent_set_allowance.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("mdp_pa", "proof_factor", "applied_pa", "applied_hold_s",
                "gauge_before", "gauge_after", "leak_detected"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    target = corrected_proof_pressure_pa(
        spec["mdp_pa"], spec["proof_factor"],
        spec.get("allowable_at_test_pa"), spec.get("allowable_at_design_pa"),
    )
    pressure = assess_applied_pressure(spec["applied_pa"], target,
                                       spec.get("yield_pressure_pa"))
    hold = assess_hold_duration(spec["applied_hold_s"],
                                spec.get("minimum_hold_s", DEFAULT_MINIMUM_HOLD_S))
    deformation = assess_permanent_set(
        spec["gauge_before"], spec["gauge_after"],
        spec.get("permanent_set_allowance", DEFAULT_PERMANENT_SET_ALLOWANCE),
    )
    leakage = assess_leakage(spec["leak_detected"])
    checks = {
        "pressure": pressure,
        "hold": hold,
        "permanent_set": deformation,
        "leakage": leakage,
    }
    findings = []
    for name in ("pressure", "hold", "permanent_set", "leakage"):
        for item in checks[name]["findings"]:
            findings.append("%s: %s" % (name, item))
    return {
        "target_pressure_pa": target,
        "checks": checks,
        "failed_checks": sorted(n for n in checks if not checks[n]["compliant"]),
        "findings": findings,
        "compliant": all(checks[n]["compliant"] for n in checks),
    }
