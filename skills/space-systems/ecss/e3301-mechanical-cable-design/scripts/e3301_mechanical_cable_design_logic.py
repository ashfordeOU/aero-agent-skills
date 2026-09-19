"""Cable-drive design sizing for spacecraft mechanisms.

Anchor: ECSS-E-ST-33-01C clause 4.7.3.4.3 (cable drives are designed for the
required life: preload, flexure life over the pulleys, and end fittings).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Split the drive force between the two runs of the loop around the preload
   and confirm the returning run still carries tension. A run that reaches
   zero tension goes slack, jumps the pulley groove and loses position
   reference, which is a functional failure long before the cable breaks.
2. Form the pulley-to-wire diameter ratio and compare it with the bend-ratio
   floor, then convert it into the bending stress the outer wire sees each
   time it wraps.
3. Accumulate the flexure passes the mission demands from the pulley count
   and the passes each pulley sees per mechanism cycle.
4. Read the allowable bending cycles from a bend-ratio life curve by log-log
   interpolation and derate them for the tension ratio actually run, which is
   how a cable at high tension loses life at a given bend ratio.
5. Grade the end fitting: a swaged or potted termination develops only a
   fraction of the cable breaking load, and that efficiency-derated strength
   is what the limit load and its safety factor are measured against.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "DEFAULT_TENSION_EXPONENT",
    "run_tensions_n",
    "bend_ratio",
    "bending_stress_pa",
    "flexure_cycles",
    "interpolate_log_log",
    "allowable_flexure_cycles",
    "termination_strength_n",
    "margin_of_safety",
    "assess_cable_drive",
]

# Margins are ratios of measured quantities; an exact zero margin can land a
# few ULPs on either side. Absorb the representation error here rather than by
# relaxing the safety factor.
MARGIN_TOLERANCE = 1e-12

# Flexure life falls off as a power of the tension ratio at a fixed bend
# ratio; this is the default exponent when a cable has no measured value.
DEFAULT_TENSION_EXPONENT = 3.0


def _require_real(label, value):
    """Return value as a finite float, refusing anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(label, value):
    """Return value as a strictly positive float."""
    out = _require_real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def _require_count(label, value):
    """Return value as a strictly positive integer count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def run_tensions_n(preload_n, drive_force_n):
    """Return the tight-run and slack-run tensions of a preloaded cable loop.

    The drive force is reacted differentially: one run gains half of it and
    the other loses half. The slack-run value is returned as computed, so a
    negative result is visible as the slack condition it is rather than being
    clamped to zero.
    """
    preload = _require_positive("preload_n", preload_n)
    drive = _require_real("drive_force_n", drive_force_n)
    if drive < 0.0:
        raise ValueError("drive_force_n must be non-negative, got %g" % drive)
    return {
        "tight_run_n": preload + drive / 2.0,
        "slack_run_n": preload - drive / 2.0,
    }


def bend_ratio(pulley_diameter_mm, cable_diameter_mm):
    """Return the pulley-to-cable diameter ratio D/d."""
    pulley = _require_positive("pulley_diameter_mm", pulley_diameter_mm)
    cable = _require_positive("cable_diameter_mm", cable_diameter_mm)
    if cable >= pulley:
        raise ValueError(
            "cable diameter %g mm is not smaller than pulley diameter %g mm"
            % (cable, pulley)
        )
    return pulley / cable


def bending_stress_pa(youngs_modulus_pa, strand_diameter_mm, pulley_diameter_mm):
    """Return the outer-strand bending stress when the cable wraps a pulley.

    The bend ratio is a cable-level number, but the fibre that actually
    fatigues is an individual strand, so the stress is formed on the strand
    diameter and not on the cable diameter.
    """
    modulus = _require_positive("youngs_modulus_pa", youngs_modulus_pa)
    strand = _require_positive("strand_diameter_mm", strand_diameter_mm)
    pulley = _require_positive("pulley_diameter_mm", pulley_diameter_mm)
    if strand >= pulley:
        raise ValueError(
            "strand diameter %g mm is not smaller than pulley diameter %g mm"
            % (strand, pulley)
        )
    return modulus * strand / pulley


def flexure_cycles(mission_cycles, pulleys, passes_per_pulley_per_cycle=2):
    """Return the total number of bend events the cable sees over the mission."""
    cycles = _require_count("mission_cycles", mission_cycles)
    count = _require_count("pulleys", pulleys)
    passes = _require_positive("passes_per_pulley_per_cycle", passes_per_pulley_per_cycle)
    return float(cycles) * count * passes


def _validate_curve(table, name):
    """Return a life curve of (bend_ratio, cycles) pairs increasing in x."""
    if not isinstance(table, (list, tuple)) or len(table) < 2:
        raise ValueError("%s needs at least two (bend_ratio, cycles) points" % name)
    points = []
    for i, item in enumerate(table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be a (bend_ratio, cycles) pair" % (name, i))
        x = _require_positive("%s[%d] bend ratio" % (name, i), item[0])
        y = _require_positive("%s[%d] cycles" % (name, i), item[1])
        points.append((x, y))
    for i in range(1, len(points)):
        if points[i][0] <= points[i - 1][0]:
            raise ValueError("%s bend ratios must strictly increase (index %d)" % (name, i))
    return points


def interpolate_log_log(table, x, name="curve"):
    """Log-log interpolate a life curve at x; refuse to extrapolate."""
    points = _validate_curve(table, name)
    xv = _require_positive("interpolation abscissa", x)
    lo, hi = points[0][0], points[-1][0]
    if xv < lo or xv > hi:
        raise ValueError(
            "%s is tabulated over [%g, %g]; %g is outside it, extrapolation refused"
            % (name, lo, hi, xv)
        )
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        if xv <= x1:
            if xv == x0:
                return y0
            if xv == x1:
                return y1
            t = (math.log(xv) - math.log(x0)) / (math.log(x1) - math.log(x0))
            return math.exp(math.log(y0) + t * (math.log(y1) - math.log(y0)))
    return points[-1][1]


def allowable_flexure_cycles(life_curve, ratio, tension_ratio,
                             reference_tension_ratio=0.10,
                             tension_exponent=DEFAULT_TENSION_EXPONENT):
    """Return the allowable bend events at a bend ratio and a tension ratio.

    The curve is read at the reference tension ratio; running the cable at a
    higher fraction of its breaking load costs life as a power of that ratio.
    """
    base = interpolate_log_log(life_curve, ratio, name="flexure-life-curve")
    tension = _require_positive("tension_ratio", tension_ratio)
    reference = _require_positive("reference_tension_ratio", reference_tension_ratio)
    exponent = _require_positive("tension_exponent", tension_exponent)
    if tension >= 1.0:
        raise ValueError(
            "tension_ratio %g reaches the breaking load; the cable is not a "
            "flexure-life case" % tension
        )
    return base * (reference / tension) ** exponent


def termination_strength_n(breaking_load_n, termination_efficiency):
    """Return the strength a swaged or potted end fitting actually develops."""
    breaking = _require_positive("breaking_load_n", breaking_load_n)
    efficiency = _require_positive("termination_efficiency", termination_efficiency)
    if efficiency > 1.0:
        raise ValueError(
            "termination_efficiency %g exceeds unity; a fitting cannot develop more "
            "than the cable breaking load" % efficiency
        )
    return breaking * efficiency


def margin_of_safety(allowable, applied, safety_factor):
    """Return the margin of safety, allowable / (applied * factor) - 1."""
    allow = _require_positive("allowable", allowable)
    load = _require_positive("applied", applied)
    factor = _require_positive("safety_factor", safety_factor)
    if factor < 1.0:
        raise ValueError("safety_factor must be at least 1.0, got %g" % factor)
    return allow / (load * factor) - 1.0


def _margin_ok(value):
    """Return True when a margin is non-negative within the named tolerance."""
    return value > 0.0 or math.isclose(value, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE)


def assess_cable_drive(spec):
    """Run the full clause 4.7.3.4.3 cable-drive assessment.

    spec keys: preload_n, drive_force_n, cable_diameter_mm, strand_diameter_mm,
    pulley_diameter_mm,
    min_bend_ratio, youngs_modulus_pa, mission_cycles, pulleys,
    breaking_load_n, termination_efficiency, safety_factor, flexure_life_curve;
    optional passes_per_pulley_per_cycle, reference_tension_ratio,
    tension_exponent, life_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "preload_n",
        "drive_force_n",
        "cable_diameter_mm",
        "strand_diameter_mm",
        "pulley_diameter_mm",
        "min_bend_ratio",
        "youngs_modulus_pa",
        "mission_cycles",
        "pulleys",
        "breaking_load_n",
        "termination_efficiency",
        "safety_factor",
        "flexure_life_curve",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    findings = []
    tensions = run_tensions_n(spec["preload_n"], spec["drive_force_n"])
    if tensions["slack_run_n"] <= 0.0:
        findings.append(
            "the returning run reaches %.4g N and goes slack; raise the preload above "
            "half the drive force" % tensions["slack_run_n"]
        )

    ratio = bend_ratio(spec["pulley_diameter_mm"], spec["cable_diameter_mm"])
    floor = _require_positive("min_bend_ratio", spec["min_bend_ratio"])
    if ratio < floor and not math.isclose(ratio, floor, rel_tol=1e-12, abs_tol=0.0):
        findings.append(
            "pulley-to-cable diameter ratio %.3g is below the %.3g floor" % (ratio, floor)
        )
    stress = bending_stress_pa(
        spec["youngs_modulus_pa"], spec["strand_diameter_mm"], spec["pulley_diameter_mm"]
    )

    breaking = _require_positive("breaking_load_n", spec["breaking_load_n"])
    tension_ratio = tensions["tight_run_n"] / breaking
    required_bends = flexure_cycles(
        spec["mission_cycles"], spec["pulleys"],
        spec.get("passes_per_pulley_per_cycle", 2),
    )
    life_factor = _require_positive("life_factor", spec.get("life_factor", 2.0))
    if life_factor < 1.0:
        raise ValueError("life_factor must be at least 1.0, got %g" % life_factor)
    allowable_bends = allowable_flexure_cycles(
        spec["flexure_life_curve"], ratio, tension_ratio,
        spec.get("reference_tension_ratio", 0.10),
        spec.get("tension_exponent", DEFAULT_TENSION_EXPONENT),
    )
    demanded_bends = required_bends * life_factor
    if allowable_bends < demanded_bends and not math.isclose(
        allowable_bends, demanded_bends, rel_tol=1e-12, abs_tol=0.0
    ):
        findings.append(
            "allowable flexure life %.4g bends is short of the %.4g the mission needs "
            "at a life factor of %.2f" % (allowable_bends, demanded_bends, life_factor)
        )

    cable_margin = margin_of_safety(breaking, tensions["tight_run_n"], spec["safety_factor"])
    if not _margin_ok(cable_margin):
        findings.append("cable strength margin of safety is %+.3f" % cable_margin)
    fitting_strength = termination_strength_n(breaking, spec["termination_efficiency"])
    fitting_margin = margin_of_safety(
        fitting_strength, tensions["tight_run_n"], spec["safety_factor"]
    )
    if not _margin_ok(fitting_margin):
        findings.append("end-fitting margin of safety is %+.3f" % fitting_margin)

    governing = min(
        (("cable-strength", cable_margin), ("end-fitting", fitting_margin)),
        key=lambda item: item[1],
    )
    return {
        "tight_run_n": tensions["tight_run_n"],
        "slack_run_n": tensions["slack_run_n"],
        "bend_ratio": ratio,
        "bending_stress_pa": stress,
        "tension_ratio": tension_ratio,
        "required_flexure_bends": required_bends,
        "demanded_flexure_bends": demanded_bends,
        "allowable_flexure_bends": allowable_bends,
        "cable_margin_of_safety": cable_margin,
        "end_fitting_strength_n": fitting_strength,
        "end_fitting_margin_of_safety": fitting_margin,
        "governing_strength_item": governing[0],
        "compliant": not findings,
        "findings": findings,
    }
