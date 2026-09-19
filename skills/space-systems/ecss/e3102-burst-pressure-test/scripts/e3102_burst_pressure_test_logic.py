"""Burst pressure test definition for two-phase heat transport equipment.

Anchor: ECSS-E-ST-31-02C clause 5.6.7 (burst test: method, minimum burst
factor, leak-before-burst evidence). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. The required burst pressure is the maximum design pressure times the burst
   factor for the article category, corrected to the test temperature by the
   ratio of the material allowables when the test is not run at the design
   point.
2. The method is graded: a monotonic ramp to failure on an article that has
   already been through its life cycling is the evidence the clause wants. A
   pristine article gives an end-of-manufacture number, not an end-of-life
   one, and a pneumatic ramp stores enough energy that it needs a declared
   hazard justification before it is an acceptable method.
3. The achieved burst factor is the actual burst pressure over the maximum
   design pressure, and is graded against the minimum burst factor.
4. Leak-before-burst is a separate demonstration. From the hoop stress at the
   grading pressure and the material fracture toughness, the critical
   through-wall crack length is formed and compared with the wall thickness:
   the crack has to become through-wall, and therefore leak, before it
   reaches the length at which it runs. The leak it produces then has to be
   larger than the detection threshold by a margin, otherwise the leak
   happens but nobody sees it.
"""

import math

__all__ = [
    "BURST_TOLERANCE",
    "MIN_BURST_FACTOR",
    "BURST_METHODS",
    "DEFAULT_LBB_LENGTH_MARGIN",
    "DEFAULT_LEAK_DETECTION_MARGIN",
    "require_real",
    "require_positive",
    "validate_burst_factor",
    "required_burst_pressure_pa",
    "temperature_correction_factor",
    "corrected_burst_pressure_pa",
    "achieved_burst_factor",
    "assess_burst_pressure",
    "validate_burst_method",
    "assess_method",
    "hoop_stress_pa",
    "critical_crack_length_m",
    "assess_leak_before_burst",
    "assess_burst_test",
]

# Pressure, length and factor grades are float comparisons a correct article
# lands exactly on. Absorb the representation error, never the requirement.
BURST_TOLERANCE = 1e-9

# A burst factor at or below unity would put the burst requirement at or
# under the maximum design pressure.
MIN_BURST_FACTOR = 1.0

# Recognised ramp methods and whether the stored energy makes the method
# hazardous enough to need a declared justification.
BURST_METHODS = {
    "hydraulic-monotonic-ramp": False,
    "hydraulic-ramp-after-life-cycling": False,
    "pneumatic-monotonic-ramp": True,
}

# The critical through-wall crack length has to be at least this multiple of
# the wall thickness for the flaw to leak before it runs.
DEFAULT_LBB_LENGTH_MARGIN = 1.0

# The through-wall leak has to be this much larger than the detection
# threshold for the leak to actually be found.
DEFAULT_LEAK_DETECTION_MARGIN = 10.0


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


def _at_least(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value > limit or math.isclose(value, limit, rel_tol=1e-12,
                                         abs_tol=BURST_TOLERANCE)


def _at_most(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value < limit or math.isclose(value, limit, rel_tol=1e-12,
                                         abs_tol=BURST_TOLERANCE)


def validate_burst_factor(burst_factor):
    """Return a usable burst factor or raise ValueError."""
    factor = require_positive("burst_factor", burst_factor)
    if _at_most(factor, MIN_BURST_FACTOR):
        raise ValueError(
            "burst_factor must exceed %.3f, got %r" % (MIN_BURST_FACTOR, burst_factor)
        )
    return factor


def required_burst_pressure_pa(mdp_pa, burst_factor):
    """Return the burst pressure requirement at the design temperature."""
    mdp = require_positive("mdp_pa", mdp_pa)
    factor = validate_burst_factor(burst_factor)
    return mdp * factor


def temperature_correction_factor(allowable_at_test_pa, allowable_at_design_pa):
    """Return the test-temperature correction on the burst requirement."""
    at_test = require_positive("allowable_at_test_pa", allowable_at_test_pa)
    at_design = require_positive("allowable_at_design_pa", allowable_at_design_pa)
    return at_test / at_design


def corrected_burst_pressure_pa(mdp_pa, burst_factor, allowable_at_test_pa=None,
                                allowable_at_design_pa=None):
    """Return the burst requirement at the actual test temperature."""
    base = required_burst_pressure_pa(mdp_pa, burst_factor)
    if allowable_at_test_pa is None and allowable_at_design_pa is None:
        return base
    if allowable_at_test_pa is None or allowable_at_design_pa is None:
        raise ValueError(
            "both material allowables are needed to correct for test temperature"
        )
    return base * temperature_correction_factor(allowable_at_test_pa,
                                                allowable_at_design_pa)


def achieved_burst_factor(actual_burst_pa, mdp_pa):
    """Return the burst factor the article actually demonstrated."""
    actual = require_positive("actual_burst_pa", actual_burst_pa)
    mdp = require_positive("mdp_pa", mdp_pa)
    return actual / mdp


def assess_burst_pressure(actual_burst_pa, required_burst_pa, mdp_pa):
    """Grade the achieved burst pressure against the requirement."""
    actual = require_positive("actual_burst_pa", actual_burst_pa)
    required = require_positive("required_burst_pa", required_burst_pa)
    factor = achieved_burst_factor(actual, mdp_pa)
    compliant = _at_least(actual, required)
    findings = []
    if not compliant:
        findings.append("article burst at %.4f Pa, below the required %.4f Pa"
                        % (actual, required))
    return {
        "actual_burst_pa": actual,
        "required_burst_pa": required,
        "achieved_factor": factor,
        "margin_pa": actual - required,
        "compliant": compliant,
        "findings": findings,
    }


def validate_burst_method(method):
    """Return the normalised burst ramp method or raise ValueError."""
    if not isinstance(method, str) or not method.strip():
        raise ValueError("burst method must be a non-empty string")
    name = method.strip().lower()
    if name not in BURST_METHODS:
        raise ValueError("unrecognised burst method %r; expected one of %s"
                         % (method, ", ".join(sorted(BURST_METHODS))))
    return name


def assess_method(method, preceded_by_life_cycling, hazard_justification=False):
    """Grade the burst method, the article history and the hazard case."""
    name = validate_burst_method(method)
    if not isinstance(preceded_by_life_cycling, bool):
        raise ValueError("preceded_by_life_cycling must be a boolean, got %r"
                         % (preceded_by_life_cycling,))
    if not isinstance(hazard_justification, bool):
        raise ValueError("hazard_justification must be a boolean, got %r"
                         % (hazard_justification,))
    needs_justification = BURST_METHODS[name]
    findings = []
    if not preceded_by_life_cycling:
        findings.append(
            "burst was run on an article that had not been through life cycling; "
            "the result is an end-of-manufacture strength, not end-of-life"
        )
    hazard_ok = True
    if needs_justification and not hazard_justification:
        hazard_ok = False
        findings.append(
            "method '%s' stores enough energy to need a declared hazard "
            "justification, and none is recorded" % name
        )
    return {
        "method": name,
        "preceded_by_life_cycling": preceded_by_life_cycling,
        "needs_hazard_justification": needs_justification,
        "hazard_justified": hazard_ok,
        "compliant": preceded_by_life_cycling and hazard_ok,
        "findings": findings,
    }


def hoop_stress_pa(pressure_pa, radius_m, thickness_m):
    """Return the thin-wall hoop stress in a pressurised cylinder."""
    pressure = require_positive("pressure_pa", pressure_pa)
    radius = require_positive("radius_m", radius_m)
    thickness = require_positive("thickness_m", thickness_m)
    if thickness >= radius:
        raise ValueError(
            "thickness %g m is not thin relative to radius %g m; the thin-wall "
            "hoop stress does not apply" % (thickness, radius)
        )
    return pressure * radius / thickness


def critical_crack_length_m(fracture_toughness_pa_sqrt_m, stress_pa):
    """Return the critical through-wall crack length at a stress level.

    The half-length follows from K = stress * sqrt(pi * a) at the toughness;
    the returned value is the full length, which is what a leak-before-burst
    argument compares against the wall thickness.
    """
    toughness = require_positive("fracture_toughness_pa_sqrt_m",
                                 fracture_toughness_pa_sqrt_m)
    stress = require_positive("stress_pa", stress_pa)
    ratio = toughness / stress
    half_length = (ratio * ratio) / math.pi
    return 2.0 * half_length


def assess_leak_before_burst(fracture_toughness_pa_sqrt_m, grading_pressure_pa,
                             radius_m, thickness_m, through_wall_leak_rate,
                             detection_threshold,
                             length_margin=DEFAULT_LBB_LENGTH_MARGIN,
                             detection_margin=DEFAULT_LEAK_DETECTION_MARGIN):
    """Grade the leak-before-burst evidence for the pressure boundary."""
    thickness = require_positive("thickness_m", thickness_m)
    stress = hoop_stress_pa(grading_pressure_pa, radius_m, thickness)
    critical = critical_crack_length_m(fracture_toughness_pa_sqrt_m, stress)
    margin = require_positive("length_margin", length_margin)
    if margin < 1.0:
        raise ValueError(
            "length_margin %g is below 1.0; leak-before-burst needs the "
            "critical crack to traverse the wall, so the required length "
            "may not be shorter than the thickness" % margin)
    detect_margin = require_positive("detection_margin", detection_margin)
    leak_rate = require_positive("through_wall_leak_rate", through_wall_leak_rate)
    threshold = require_positive("detection_threshold", detection_threshold)
    required_length = margin * thickness
    leaks_first = _at_least(critical, required_length)
    detectable = _at_least(leak_rate, detect_margin * threshold)
    findings = []
    if not leaks_first:
        findings.append(
            "critical through-wall crack length %.6g m is shorter than %.6g m; "
            "the flaw runs before it penetrates the wall"
            % (critical, required_length)
        )
    if not detectable:
        findings.append(
            "through-wall leak rate %.6g is not %.1fx the detection threshold "
            "%.6g; the leak occurs but is not found"
            % (leak_rate, detect_margin, threshold)
        )
    return {
        "hoop_stress_pa": stress,
        "critical_crack_length_m": critical,
        "required_crack_length_m": required_length,
        "length_ratio": critical / required_length,
        "leaks_before_break": leaks_first,
        "leak_detectable": detectable,
        "compliant": leaks_first and detectable,
        "findings": findings,
    }


def assess_burst_test(spec):
    """Run the whole clause 5.6.7 burst pressure test assessment.

    spec keys: mdp_pa, burst_factor, actual_burst_pa, method,
    preceded_by_life_cycling, fracture_toughness_pa_sqrt_m, radius_m,
    thickness_m, through_wall_leak_rate, detection_threshold; optional
    allowable_at_test_pa, allowable_at_design_pa, hazard_justification,
    grading_pressure_pa, length_margin, detection_margin.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("mdp_pa", "burst_factor", "actual_burst_pa", "method",
                "preceded_by_life_cycling", "fracture_toughness_pa_sqrt_m",
                "radius_m", "thickness_m", "through_wall_leak_rate",
                "detection_threshold"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = corrected_burst_pressure_pa(
        spec["mdp_pa"], spec["burst_factor"],
        spec.get("allowable_at_test_pa"), spec.get("allowable_at_design_pa"),
    )
    pressure = assess_burst_pressure(spec["actual_burst_pa"], required, spec["mdp_pa"])
    method = assess_method(spec["method"], spec["preceded_by_life_cycling"],
                           spec.get("hazard_justification", False))
    lbb = assess_leak_before_burst(
        spec["fracture_toughness_pa_sqrt_m"],
        spec.get("grading_pressure_pa", spec["mdp_pa"]),
        spec["radius_m"], spec["thickness_m"],
        spec["through_wall_leak_rate"], spec["detection_threshold"],
        spec.get("length_margin", DEFAULT_LBB_LENGTH_MARGIN),
        spec.get("detection_margin", DEFAULT_LEAK_DETECTION_MARGIN),
    )
    checks = {"burst_pressure": pressure, "method": method, "leak_before_burst": lbb}
    findings = []
    for name in ("method", "burst_pressure", "leak_before_burst"):
        for item in checks[name]["findings"]:
            findings.append("%s: %s" % (name, item))
    return {
        "required_burst_pa": required,
        "checks": checks,
        "failed_checks": sorted(n for n in checks if not checks[n]["compliant"]),
        "findings": findings,
        "compliant": all(checks[n]["compliant"] for n in checks),
    }
