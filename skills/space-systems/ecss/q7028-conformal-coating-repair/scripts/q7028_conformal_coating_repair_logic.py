"""Conformal coating removal, re-application and cure check after board rework.

Anchor: ECSS-Q-ST-70-28 Methods (repair and re-application of conformal
coating over an area that has been reworked). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the reworked footprint, the area of coating actually removed and
   the re-application record.
2. Check the removal window on both sides: the removed area must clear the
   footprint by a working margin, and must not run so far past it that sound
   coating is stripped from parts that were never touched.
3. Grade the re-applied film on its thickness readings -- every individual
   reading against the band, and the mean separately, because a film that
   averages well can still be bare at one point.
4. Check the new film overlaps the surrounding sound coating by at least the
   specified lap, so the repair has no seam open to moisture.
5. Read the cure schedule: interpolate the cure time the chosen temperature
   demands, and compare it with the time actually held.
6. Return accept, re-coat or refuse together with the findings.
"""

import math

__all__ = [
    "LENGTH_TOLERANCE_MM",
    "THICKNESS_TOLERANCE_UM",
    "TIME_TOLERANCE_H",
    "require_real",
    "require_band",
    "removal_margin_mm",
    "assess_removal_window",
    "assess_thickness_readings",
    "assess_overlap",
    "required_cure_hours",
    "assess_cure",
    "assess_conformal_coating_repair",
]

LENGTH_TOLERANCE_MM = 1e-9
THICKNESS_TOLERANCE_UM = 1e-9
TIME_TOLERANCE_H = 1e-9


def require_real(label, value, minimum=None, allow_equal=True):
    """Return value as a float, raising ValueError on anything unusable."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if allow_equal and out < minimum:
            raise ValueError("%s must be at least %g, got %g" % (label, minimum, out))
        if not allow_equal and out <= minimum:
            raise ValueError("%s must exceed %g, got %g" % (label, minimum, out))
    return out


def require_band(label, band, minimum=None):
    """Return a validated (low, high) pair with low <= high."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair, got %r" % (label, band))
    low = require_real("%s low" % label, band[0], minimum=minimum)
    high = require_real("%s high" % label, band[1], minimum=minimum)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def removal_margin_mm(removal_span_mm, footprint_span_mm):
    """Return the per-side margin by which the removal clears the footprint."""
    removal = require_real("removal_span_mm", removal_span_mm, minimum=0.0,
                           allow_equal=False)
    footprint = require_real("footprint_span_mm", footprint_span_mm, minimum=0.0,
                             allow_equal=False)
    if removal < footprint - LENGTH_TOLERANCE_MM:
        raise ValueError(
            "removal span %g mm is smaller than the footprint %g mm it must clear"
            % (removal, footprint)
        )
    return (removal - footprint) / 2.0


def assess_removal_window(footprint_length_mm, footprint_width_mm,
                          removal_length_mm, removal_width_mm,
                          min_margin_mm, max_margin_mm):
    """Grade the removed coating area against its minimum and maximum margins."""
    low, high = require_band("margin_mm", (min_margin_mm, max_margin_mm), minimum=0.0)
    along = removal_margin_mm(removal_length_mm, footprint_length_mm)
    across = removal_margin_mm(removal_width_mm, footprint_width_mm)
    worst_short = min(along, across)
    worst_long = max(along, across)
    under = worst_short < low - LENGTH_TOLERANCE_MM
    over = worst_long > high + LENGTH_TOLERANCE_MM
    return {
        "margin_along_mm": along,
        "margin_across_mm": across,
        "min_margin_mm": low,
        "max_margin_mm": high,
        "under_margin": under,
        "over_margin": over,
        "acceptable": not (under or over),
    }


def assess_thickness_readings(readings_um, band_um):
    """Grade every re-applied film thickness reading and their mean."""
    if not isinstance(readings_um, (list, tuple)) or not readings_um:
        raise ValueError("readings_um must be a non-empty sequence of thicknesses")
    low, high = require_band("thickness_band_um", band_um, minimum=0.0)
    values = [
        require_real("readings_um[%d]" % i, v, minimum=0.0)
        for i, v in enumerate(readings_um)
    ]
    mean = sum(values) / len(values)
    thin = [i for i, v in enumerate(values) if v < low - THICKNESS_TOLERANCE_UM]
    thick = [i for i, v in enumerate(values) if v > high + THICKNESS_TOLERANCE_UM]
    mean_in_band = (mean >= low - THICKNESS_TOLERANCE_UM
                    and mean <= high + THICKNESS_TOLERANCE_UM)
    return {
        "readings_um": values,
        "mean_um": mean,
        "band_um": (low, high),
        "thin_points": thin,
        "thick_points": thick,
        "mean_in_band": mean_in_band,
        "acceptable": not thin and not thick and mean_in_band,
    }


def assess_overlap(overlap_mm, min_overlap_mm):
    """Grade the lap of the new film onto the surrounding sound coating."""
    overlap = require_real("overlap_mm", overlap_mm, minimum=0.0)
    minimum = require_real("min_overlap_mm", min_overlap_mm, minimum=0.0,
                           allow_equal=False)
    short = overlap < minimum - LENGTH_TOLERANCE_MM
    return {
        "overlap_mm": overlap,
        "min_overlap_mm": minimum,
        "acceptable": not short,
    }


def required_cure_hours(schedule, temperature_c):
    """Interpolate the cure time the schedule demands at a temperature."""
    if not isinstance(schedule, (list, tuple)) or len(schedule) < 2:
        raise ValueError("schedule needs at least two (temperature_c, hours) points")
    points = []
    for i, item in enumerate(schedule):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("schedule[%d] must be a (temperature_c, hours) pair" % i)
        t = require_real("schedule[%d] temperature_c" % i, item[0], minimum=0.0,
                         allow_equal=False)
        h = require_real("schedule[%d] hours" % i, item[1], minimum=0.0,
                         allow_equal=False)
        points.append((t, h))
    for i in range(1, len(points)):
        if points[i][0] <= points[i - 1][0]:
            raise ValueError(
                "schedule temperatures must strictly increase (index %d)" % i
            )
    temp = require_real("temperature_c", temperature_c, minimum=0.0, allow_equal=False)
    low_t, high_t = points[0][0], points[-1][0]
    if temp < low_t or temp > high_t:
        raise ValueError(
            "cure schedule is tabulated over [%g, %g] C; %g C is outside it, "
            "extrapolation refused" % (low_t, high_t, temp)
        )
    for i in range(1, len(points)):
        t0, h0 = points[i - 1]
        t1, h1 = points[i]
        if temp <= t1:
            if temp == t0:
                return h0
            if temp == t1:
                return h1
            fraction = (temp - t0) / (t1 - t0)
            return h0 + fraction * (h1 - h0)
    return points[-1][1]


def assess_cure(schedule, temperature_c, held_hours):
    """Compare the cure time actually held with the time the schedule demands."""
    required = required_cure_hours(schedule, temperature_c)
    held = require_real("held_hours", held_hours, minimum=0.0)
    short = held < required - TIME_TOLERANCE_H
    return {
        "temperature_c": float(temperature_c),
        "required_hours": required,
        "held_hours": held,
        "shortfall_hours": max(0.0, required - held),
        "acceptable": not short,
    }


def assess_conformal_coating_repair(spec):
    """Run the whole coating removal, re-application and cure assessment.

    spec keys: footprint_length_mm, footprint_width_mm, removal_length_mm,
    removal_width_mm, min_margin_mm, max_margin_mm, thickness_readings_um,
    thickness_band_um, overlap_mm, min_overlap_mm, cure_schedule,
    cure_temperature_c, cure_held_hours.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "footprint_length_mm", "footprint_width_mm", "removal_length_mm",
        "removal_width_mm", "min_margin_mm", "max_margin_mm",
        "thickness_readings_um", "thickness_band_um", "overlap_mm",
        "min_overlap_mm", "cure_schedule", "cure_temperature_c", "cure_held_hours",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    removal = assess_removal_window(
        spec["footprint_length_mm"], spec["footprint_width_mm"],
        spec["removal_length_mm"], spec["removal_width_mm"],
        spec["min_margin_mm"], spec["max_margin_mm"],
    )
    thickness = assess_thickness_readings(
        spec["thickness_readings_um"], spec["thickness_band_um"]
    )
    overlap = assess_overlap(spec["overlap_mm"], spec["min_overlap_mm"])
    cure = assess_cure(
        spec["cure_schedule"], spec["cure_temperature_c"], spec["cure_held_hours"]
    )

    findings = []
    if removal["under_margin"]:
        findings.append(
            "coating removal clears the footprint by only %.3f mm against a %.3f mm "
            "minimum" % (min(removal["margin_along_mm"], removal["margin_across_mm"]),
                         removal["min_margin_mm"])
        )
    if removal["over_margin"]:
        findings.append(
            "coating removal runs %.3f mm past the footprint, over the %.3f mm "
            "maximum" % (max(removal["margin_along_mm"], removal["margin_across_mm"]),
                         removal["max_margin_mm"])
        )
    if thickness["thin_points"]:
        findings.append(
            "re-applied film is under the band at reading(s) %s"
            % ", ".join(str(i) for i in thickness["thin_points"])
        )
    if thickness["thick_points"]:
        findings.append(
            "re-applied film is over the band at reading(s) %s"
            % ", ".join(str(i) for i in thickness["thick_points"])
        )
    if not thickness["mean_in_band"]:
        findings.append(
            "mean film thickness %.2f um is outside the band %.2f-%.2f um"
            % (thickness["mean_um"], thickness["band_um"][0], thickness["band_um"][1])
        )
    if not overlap["acceptable"]:
        findings.append(
            "new film laps the sound coating by only %.3f mm against a %.3f mm "
            "minimum" % (overlap["overlap_mm"], overlap["min_overlap_mm"])
        )
    if not cure["acceptable"]:
        findings.append(
            "cure held %.2f h at %.1f C against the %.2f h the schedule demands"
            % (cure["held_hours"], cure["temperature_c"], cure["required_hours"])
        )

    # Stripping sound coating off untouched hardware cannot be undone by
    # re-coating, so it is the one outcome that refuses rather than re-works.
    if removal["over_margin"]:
        verdict = "refuse"
    elif findings:
        verdict = "re-coat"
    else:
        verdict = "accept"

    return {
        "removal": removal,
        "thickness": thickness,
        "overlap": overlap,
        "cure": cure,
        "verdict": verdict,
        "findings": findings,
    }
