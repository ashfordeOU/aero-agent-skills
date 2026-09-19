"""Performance verification of a capillary driven loop / loop heat pipe.

Anchor: ECSS-E-ST-31-02C clause 5.5.5.2d (performance verification of a
capillary driven two-phase loop). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Start-up: the loop has to prime from a cold, flooded evaporator at the
   lowest heat load it is specified to start on. The demonstrated start-up
   power is graded against the declared minimum start heat load, and the
   demonstration only counts when it carried the qualification attached
   thermal mass rather than a bare evaporator.
2. Thermal-mass sensitivity: the minimum start heat load rises with the mass
   bolted to the evaporator. A sensitivity series is fitted to a slope in
   W per (J/K) and extrapolation past the tested mass span is refused.
3. Subcooling: the liquid arriving at the evaporator inlet must sit below the
   loop saturation temperature by at least the required subcooling, otherwise
   vapour is ingested into the wick and the loop deprimes.
4. Adverse tilt / elevation: the capillary pressure the wick can raise has to
   cover the liquid, vapour and groove losses plus the static head of the
   adverse elevation the loop is verified at.
5. Off-mode heat leak: with the evaporator unpowered the loop still conducts
   and the parasitic leak into the cold side is graded against its allowance.
6. Regulation: the declared set-point regulation method must be one of the
   recognised reservoir control methods and must actually have been
   demonstrated over the regulated temperature band.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "STANDARD_GRAVITY",
    "REGULATION_METHODS",
    "require_positive",
    "require_real",
    "assess_start_up",
    "thermal_mass_sensitivity",
    "minimum_start_load_at_mass",
    "subcooling_k",
    "assess_subcooling",
    "adverse_head_pa",
    "capillary_pressure_balance",
    "assess_off_mode_leak",
    "assess_regulation_method",
    "assess_performance_verification",
]

# Every grade in this module is a difference of two floats that a correct
# design can land exactly on. Absorb the representation error with a named
# tolerance instead of relaxing the engineering limit.
MARGIN_TOLERANCE = 1e-9

STANDARD_GRAVITY = 9.80665

# Reservoir / compensation-chamber set-point control methods a capillary
# driven loop is recognised as regulating with.
REGULATION_METHODS = (
    "active-reservoir-heater",
    "cold-biased-reservoir",
    "thermoelectric-reservoir-control",
    "passive-two-phase-reservoir",
)


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


def _meets(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value > limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE)


def assess_start_up(demonstrated_power_w, minimum_start_load_w,
                    attached_mass_j_per_k, qualification_mass_j_per_k):
    """Grade a start-up demonstration against the minimum start heat load.

    A start-up counts only when the loop primed at or below the declared
    minimum start heat load AND the evaporator carried at least the
    qualification attached thermal mass while it did so.
    """
    demonstrated = require_positive("demonstrated_power_w", demonstrated_power_w)
    minimum = require_positive("minimum_start_load_w", minimum_start_load_w)
    attached = require_non_negative("attached_mass_j_per_k", attached_mass_j_per_k)
    qualification = require_non_negative("qualification_mass_j_per_k", qualification_mass_j_per_k)
    power_ok = _meets(minimum, demonstrated)
    mass_ok = _meets(attached, qualification)
    findings = []
    if not power_ok:
        findings.append(
            "start-up demonstrated at %.4f W, above the declared minimum start "
            "heat load of %.4f W" % (demonstrated, minimum)
        )
    if not mass_ok:
        findings.append(
            "start-up carried %.4f J/K of attached mass, below the qualification "
            "mass of %.4f J/K" % (attached, qualification)
        )
    return {
        "demonstrated_power_w": demonstrated,
        "minimum_start_load_w": minimum,
        "attached_mass_j_per_k": attached,
        "qualification_mass_j_per_k": qualification,
        "power_margin_w": minimum - demonstrated,
        "compliant": power_ok and mass_ok,
        "findings": findings,
    }


def _validate_series(series):
    """Return a mass-ordered list of (mass_j_per_k, min_start_load_w) points."""
    if not isinstance(series, (list, tuple)) or len(series) < 2:
        raise ValueError("sensitivity series needs at least two (mass, power) points")
    points = []
    for index, item in enumerate(series):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("series[%d] must be a (mass_j_per_k, power_w) pair" % index)
        mass = require_non_negative("series[%d] mass_j_per_k" % index, item[0])
        power = require_positive("series[%d] power_w" % index, item[1])
        points.append((mass, power))
    points.sort(key=lambda p: p[0])
    for index in range(1, len(points)):
        if math.isclose(points[index][0], points[index - 1][0],
                        rel_tol=0.0, abs_tol=MARGIN_TOLERANCE):
            raise ValueError("sensitivity series repeats the attached mass %g J/K"
                             % points[index][0])
    return points


def thermal_mass_sensitivity(series):
    """Return the start-load sensitivity to attached thermal mass.

    The slope is the least-squares gradient in W per (J/K) over the tested
    span. A series whose minimum start load falls as mass is added is
    reported as a non-monotonic finding rather than silently fitted.
    """
    points = _validate_series(series)
    n = float(len(points))
    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n
    numerator = sum((p[0] - mean_x) * (p[1] - mean_y) for p in points)
    denominator = sum((p[0] - mean_x) ** 2 for p in points)
    if denominator <= 0.0:
        raise ValueError("sensitivity series has no spread in attached thermal mass")
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    monotonic = all(points[i][1] >= points[i - 1][1] - MARGIN_TOLERANCE
                    for i in range(1, len(points)))
    findings = []
    if not monotonic:
        findings.append("minimum start heat load falls as attached thermal mass rises; "
                        "the series is not a usable sensitivity")
    return {
        "points": points,
        "slope_w_per_j_per_k": slope,
        "intercept_w": intercept,
        "mass_span_j_per_k": (points[0][0], points[-1][0]),
        "monotonic": monotonic,
        "findings": findings,
    }


def minimum_start_load_at_mass(series, mass_j_per_k):
    """Interpolate the minimum start heat load at an attached mass.

    Extrapolation outside the tested mass span is refused: the start-up of a
    capillary loop is not linear once the evaporator mass leaves the range
    the loop was actually started at.
    """
    points = _validate_series(series)
    mass = require_non_negative("mass_j_per_k", mass_j_per_k)
    low, high = points[0][0], points[-1][0]
    if mass < low - MARGIN_TOLERANCE or mass > high + MARGIN_TOLERANCE:
        raise ValueError(
            "attached mass %g J/K is outside the tested span [%g, %g]; "
            "extrapolation refused" % (mass, low, high)
        )
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        if mass <= x1 or index == len(points) - 1:
            if math.isclose(x1, x0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE):
                return y1
            fraction = (mass - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)
    return points[-1][1]


def subcooling_k(saturation_temperature_k, inlet_temperature_k):
    """Return the liquid subcooling at the evaporator inlet in kelvin."""
    saturation = require_positive("saturation_temperature_k", saturation_temperature_k)
    inlet = require_positive("inlet_temperature_k", inlet_temperature_k)
    return saturation - inlet


def assess_subcooling(saturation_temperature_k, inlet_temperature_k, required_k):
    """Grade the evaporator inlet subcooling against its requirement."""
    required = require_non_negative("required_k", required_k)
    achieved = subcooling_k(saturation_temperature_k, inlet_temperature_k)
    compliant = _meets(achieved, required)
    findings = []
    if achieved < 0.0:
        findings.append("evaporator inlet is above the loop saturation temperature; "
                        "vapour ingestion into the wick is expected")
    if not compliant:
        findings.append("subcooling %.4f K is below the required %.4f K"
                        % (achieved, required))
    return {
        "achieved_k": achieved,
        "required_k": required,
        "margin_k": achieved - required,
        "compliant": compliant,
        "findings": findings,
    }


def adverse_head_pa(density_kg_per_m3, elevation_m, gravity=STANDARD_GRAVITY):
    """Return the static head the wick must lift for an adverse elevation.

    A negative elevation is a favourable (gravity assisted) orientation and
    returns a negative head, which relieves the capillary budget.
    """
    density = require_positive("density_kg_per_m3", density_kg_per_m3)
    elevation = require_real("elevation_m", elevation_m)
    g = require_positive("gravity", gravity)
    return density * g * elevation


def capillary_pressure_balance(capillary_limit_pa, liquid_drop_pa, vapour_drop_pa,
                               groove_drop_pa, adverse_head_value_pa):
    """Close the capillary pressure budget of the loop at an orientation."""
    limit = require_positive("capillary_limit_pa", capillary_limit_pa)
    liquid = require_non_negative("liquid_drop_pa", liquid_drop_pa)
    vapour = require_non_negative("vapour_drop_pa", vapour_drop_pa)
    groove = require_non_negative("groove_drop_pa", groove_drop_pa)
    head = require_real("adverse_head_value_pa", adverse_head_value_pa)
    demand = liquid + vapour + groove + head
    margin = limit - demand
    compliant = _meets(limit, demand)
    findings = []
    if not compliant:
        findings.append(
            "capillary limit %.4f Pa does not cover the %.4f Pa demand at the "
            "verified adverse elevation" % (limit, demand)
        )
    ratio = None
    if demand > 0.0:
        ratio = limit / demand
    return {
        "capillary_limit_pa": limit,
        "demand_pa": demand,
        "margin_pa": margin,
        "ratio": ratio,
        "compliant": compliant,
        "findings": findings,
    }


def assess_off_mode_leak(measured_leak_w, allowable_leak_w):
    """Grade the unpowered (off-mode) parasitic heat leak of the loop."""
    measured = require_non_negative("measured_leak_w", measured_leak_w)
    allowable = require_positive("allowable_leak_w", allowable_leak_w)
    compliant = _meets(allowable, measured)
    findings = []
    if not compliant:
        findings.append("off-mode heat leak %.4f W exceeds the allowance of %.4f W"
                        % (measured, allowable))
    return {
        "measured_leak_w": measured,
        "allowable_leak_w": allowable,
        "margin_w": allowable - measured,
        "compliant": compliant,
        "findings": findings,
    }


def assess_regulation_method(method, demonstrated_band_k, required_band_k):
    """Grade the declared set-point regulation method and its demonstration."""
    if not isinstance(method, str) or not method.strip():
        raise ValueError("regulation method must be a non-empty string")
    name = method.strip().lower()
    if name not in REGULATION_METHODS:
        raise ValueError("unrecognised regulation method %r; expected one of %s"
                         % (method, ", ".join(REGULATION_METHODS)))
    demonstrated = require_non_negative("demonstrated_band_k", demonstrated_band_k)
    required = require_positive("required_band_k", required_band_k)
    compliant = _meets(demonstrated, required)
    findings = []
    if not compliant:
        findings.append(
            "regulation demonstrated over %.4f K, short of the required %.4f K band"
            % (demonstrated, required)
        )
    return {
        "method": name,
        "demonstrated_band_k": demonstrated,
        "required_band_k": required,
        "compliant": compliant,
        "findings": findings,
    }


def assess_performance_verification(spec):
    """Run the whole clause 5.5.5.2d performance verification assessment.

    spec keys: start_up, sensitivity_series, subcooling, orientation,
    off_mode, regulation. Each is the argument mapping of the matching
    routine above.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("start_up", "sensitivity_series", "subcooling", "orientation",
                "off_mode", "regulation"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    start = spec["start_up"]
    if not isinstance(start, dict):
        raise ValueError("spec['start_up'] must be a mapping")
    start_result = assess_start_up(
        start.get("demonstrated_power_w"),
        start.get("minimum_start_load_w"),
        start.get("attached_mass_j_per_k"),
        start.get("qualification_mass_j_per_k"),
    )

    sensitivity = thermal_mass_sensitivity(spec["sensitivity_series"])

    sub = spec["subcooling"]
    if not isinstance(sub, dict):
        raise ValueError("spec['subcooling'] must be a mapping")
    subcooling_result = assess_subcooling(
        sub.get("saturation_temperature_k"),
        sub.get("inlet_temperature_k"),
        sub.get("required_k"),
    )

    orientation = spec["orientation"]
    if not isinstance(orientation, dict):
        raise ValueError("spec['orientation'] must be a mapping")
    head = adverse_head_pa(
        orientation.get("density_kg_per_m3"),
        orientation.get("elevation_m"),
        orientation.get("gravity", STANDARD_GRAVITY),
    )
    balance = capillary_pressure_balance(
        orientation.get("capillary_limit_pa"),
        orientation.get("liquid_drop_pa"),
        orientation.get("vapour_drop_pa"),
        orientation.get("groove_drop_pa"),
        head,
    )
    balance["adverse_head_pa"] = head

    off = spec["off_mode"]
    if not isinstance(off, dict):
        raise ValueError("spec['off_mode'] must be a mapping")
    off_result = assess_off_mode_leak(
        off.get("measured_leak_w"), off.get("allowable_leak_w")
    )

    reg = spec["regulation"]
    if not isinstance(reg, dict):
        raise ValueError("spec['regulation'] must be a mapping")
    regulation_result = assess_regulation_method(
        reg.get("method"), reg.get("demonstrated_band_k"), reg.get("required_band_k")
    )

    checks = {
        "start_up": start_result,
        "thermal_mass_sensitivity": sensitivity,
        "subcooling": subcooling_result,
        "adverse_orientation": balance,
        "off_mode_leak": off_result,
        "regulation": regulation_result,
    }
    findings = []
    for name in ("start_up", "thermal_mass_sensitivity", "subcooling",
                 "adverse_orientation", "off_mode_leak", "regulation"):
        for item in checks[name]["findings"]:
            findings.append("%s: %s" % (name, item))
    compliant = (
        start_result["compliant"]
        and sensitivity["monotonic"]
        and subcooling_result["compliant"]
        and balance["compliant"]
        and off_result["compliant"]
        and regulation_result["compliant"]
    )
    return {
        "checks": checks,
        "findings": findings,
        "failed_checks": sorted(
            name for name in checks
            if not checks[name].get("compliant", checks[name].get("monotonic", True))
        ),
        "compliant": compliant,
    }
