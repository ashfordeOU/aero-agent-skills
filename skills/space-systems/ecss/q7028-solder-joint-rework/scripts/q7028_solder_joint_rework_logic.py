"""Solder joint rework permission and post-rework grading for a printed board.

Anchor: ECSS-Q-ST-70-28 Methods (rework of solder joints, graded against the
soldering workmanship criteria of ECSS-Q-ST-70-61). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the pad condition, the rework history and the iron settings.
2. Convert the planned iron dwell into thermal exposure units with a doubling
   rule: time at the reference tip temperature counts once, and every
   doubling interval above it counts double, so a short hot touch and a long
   warm one can be added on the same scale.
3. Add that to the exposure the joint has already taken and compare the total
   with the budget the laminate and the component allow.
4. Decide whether the rework may proceed: refused on a lifted pad, an
   exhausted cycle count, an iron outside its window or an exceeded exposure
   budget; with-approval on the last permitted cycle or a pad already damaged.
5. Where post-rework measurements are supplied, grade the finished joint on
   wetting contact angle, fillet coverage and lead protrusion, and return the
   worst characteristic rather than an average of them.
"""

import math

__all__ = [
    "TEMPERATURE_TOLERANCE_C",
    "TIME_TOLERANCE_S",
    "ANGLE_TOLERANCE_DEG",
    "FRACTION_TOLERANCE",
    "EXPOSURE_TOLERANCE",
    "PAD_CONDITIONS",
    "REFERENCE_TIP_C",
    "DOUBLING_INTERVAL_C",
    "require_real",
    "require_count",
    "require_band",
    "rework_cycle_state",
    "tip_within_window",
    "thermal_exposure_units",
    "cumulative_exposure_units",
    "grade_wetting",
    "grade_fillet_coverage",
    "grade_lead_protrusion",
    "grade_reworked_joint",
    "assess_solder_joint_rework",
]

TEMPERATURE_TOLERANCE_C = 1e-9
TIME_TOLERANCE_S = 1e-9
ANGLE_TOLERANCE_DEG = 1e-9
FRACTION_TOLERANCE = 1e-12
EXPOSURE_TOLERANCE = 1e-9

# A pad that has separated from the laminate carries no rework; a pad that is
# damaged but still bonded can be reworked under an approved deviation.
PAD_CONDITIONS = ("sound", "damaged-bonded", "lifted")

# Exposure reference: dwell seconds at this tip temperature count once.
REFERENCE_TIP_C = 300.0
# Every interval of this many degrees above the reference doubles the rate.
DOUBLING_INTERVAL_C = 20.0


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


def require_count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def require_band(label, band, minimum=None):
    """Return a validated (low, high) pair with low <= high."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair, got %r" % (label, band))
    low = require_real("%s low" % label, band[0], minimum=minimum)
    high = require_real("%s high" % label, band[1], minimum=minimum)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def rework_cycle_state(cycles_used, max_cycles):
    """Return the rework cycle budget state for one joint."""
    used = require_count("cycles_used", cycles_used)
    maximum = require_count("max_cycles", max_cycles)
    if maximum == 0:
        raise ValueError("max_cycles must be at least 1 for a reworkable joint")
    remaining = maximum - used
    return {
        "cycles_used": used,
        "max_cycles": maximum,
        "remaining_after_this_cycle": remaining - 1,
        "exhausted": remaining <= 0,
        "last_allowed": remaining == 1,
    }


def tip_within_window(tip_temperature_c, window_c):
    """Report whether the iron tip setting sits inside its qualified window."""
    tip = require_real("tip_temperature_c", tip_temperature_c, minimum=0.0,
                       allow_equal=False)
    low, high = require_band("temperature_window_c", window_c, minimum=0.0)
    below = tip < low - TEMPERATURE_TOLERANCE_C
    above = tip > high + TEMPERATURE_TOLERANCE_C
    return {
        "tip_temperature_c": tip,
        "window_c": (low, high),
        "below_window": below,
        "above_window": above,
        "within_window": not (below or above),
    }


def thermal_exposure_units(dwell_s, tip_temperature_c,
                           reference_c=REFERENCE_TIP_C,
                           doubling_interval_c=DOUBLING_INTERVAL_C):
    """Convert an iron dwell at a tip temperature into exposure units."""
    dwell = require_real("dwell_s", dwell_s, minimum=0.0)
    tip = require_real("tip_temperature_c", tip_temperature_c, minimum=0.0,
                       allow_equal=False)
    reference = require_real("reference_c", reference_c, minimum=0.0,
                             allow_equal=False)
    interval = require_real("doubling_interval_c", doubling_interval_c, minimum=0.0,
                            allow_equal=False)
    return dwell * math.pow(2.0, (tip - reference) / interval)


def cumulative_exposure_units(events, reference_c=REFERENCE_TIP_C,
                              doubling_interval_c=DOUBLING_INTERVAL_C):
    """Sum the exposure units of a sequence of (dwell_s, tip_temperature_c) events."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence of (dwell_s, tip_c) pairs")
    total = 0.0
    for index, item in enumerate(events):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("events[%d] must be a (dwell_s, tip_c) pair" % index)
        total += thermal_exposure_units(item[0], item[1], reference_c,
                                        doubling_interval_c)
    return total


def grade_wetting(contact_angle_deg, max_contact_angle_deg, marginal_band_deg=5.0):
    """Grade the solder contact angle of the finished joint."""
    angle = require_real("contact_angle_deg", contact_angle_deg, minimum=0.0)
    limit = require_real("max_contact_angle_deg", max_contact_angle_deg, minimum=0.0,
                         allow_equal=False)
    band = require_real("marginal_band_deg", marginal_band_deg, minimum=0.0)
    if angle > 180.0:
        raise ValueError("contact_angle_deg must not exceed 180, got %g" % angle)
    if angle > limit + ANGLE_TOLERANCE_DEG:
        outcome = "dewetted"
    elif angle > limit - band - ANGLE_TOLERANCE_DEG:
        outcome = "marginal"
    else:
        outcome = "wetted"
    return {
        "contact_angle_deg": angle,
        "max_contact_angle_deg": limit,
        "outcome": outcome,
        "acceptable": outcome != "dewetted",
    }


def grade_fillet_coverage(coverage_fraction, min_coverage_fraction):
    """Grade the fraction of the joint circumference the fillet covers."""
    coverage = require_real("coverage_fraction", coverage_fraction, minimum=0.0)
    minimum = require_real("min_coverage_fraction", min_coverage_fraction, minimum=0.0,
                           allow_equal=False)
    if coverage > 1.0 + FRACTION_TOLERANCE:
        raise ValueError("coverage_fraction must not exceed 1.0, got %g" % coverage)
    if minimum > 1.0:
        raise ValueError("min_coverage_fraction must not exceed 1.0, got %g" % minimum)
    short = coverage < minimum - FRACTION_TOLERANCE
    return {
        "coverage_fraction": coverage,
        "min_coverage_fraction": minimum,
        "outcome": "short-fillet" if short else "full-fillet",
        "acceptable": not short,
    }


def grade_lead_protrusion(protrusion_mm, band_mm):
    """Grade the through-hole lead protrusion against its band."""
    protrusion = require_real("protrusion_mm", protrusion_mm, minimum=0.0)
    low, high = require_band("protrusion_band_mm", band_mm, minimum=0.0)
    if protrusion < low - 1e-9:
        outcome = "under-protrusion"
    elif protrusion > high + 1e-9:
        outcome = "over-protrusion"
    else:
        outcome = "in-band"
    return {
        "protrusion_mm": protrusion,
        "band_mm": (low, high),
        "outcome": outcome,
        "acceptable": outcome == "in-band",
    }


def grade_reworked_joint(measurements):
    """Grade the finished joint and return the worst of its characteristics.

    measurements keys: contact_angle_deg, max_contact_angle_deg,
    fillet_coverage, min_fillet_coverage, optional lead_protrusion_mm with
    protrusion_band_mm.
    """
    if not isinstance(measurements, dict):
        raise ValueError("measurements must be a mapping")
    for key in ("contact_angle_deg", "max_contact_angle_deg", "fillet_coverage",
                "min_fillet_coverage"):
        if key not in measurements:
            raise ValueError("measurements missing required key '%s'" % key)
    wetting = grade_wetting(
        measurements["contact_angle_deg"],
        measurements["max_contact_angle_deg"],
        measurements.get("marginal_band_deg", 5.0),
    )
    fillet = grade_fillet_coverage(
        measurements["fillet_coverage"], measurements["min_fillet_coverage"]
    )
    protrusion = None
    if "lead_protrusion_mm" in measurements:
        if "protrusion_band_mm" not in measurements:
            raise ValueError(
                "a lead_protrusion_mm reading needs a protrusion_band_mm band"
            )
        protrusion = grade_lead_protrusion(
            measurements["lead_protrusion_mm"], measurements["protrusion_band_mm"]
        )
    characteristics = {"wetting": wetting, "fillet": fillet}
    if protrusion is not None:
        characteristics["protrusion"] = protrusion
    driving = [name for name, rec in characteristics.items() if not rec["acceptable"]]
    return {
        "characteristics": characteristics,
        "driving": sorted(driving),
        "verdict": "reject" if driving else "accept",
    }


def assess_solder_joint_rework(spec):
    """Decide whether a joint may be reworked and grade the result if measured.

    spec keys: pad_condition, cycles_used, max_cycles, tip_temperature_c,
    temperature_window_c, dwell_s, prior_exposure_units, max_exposure_units,
    optional reference_c, doubling_interval_c and post_rework measurements.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("pad_condition", "cycles_used", "max_cycles", "tip_temperature_c",
                "temperature_window_c", "dwell_s", "prior_exposure_units",
                "max_exposure_units"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    pad = spec["pad_condition"]
    if pad not in PAD_CONDITIONS:
        raise ValueError(
            "pad_condition must be one of %s, got %r" % (", ".join(PAD_CONDITIONS), pad)
        )
    cycles = rework_cycle_state(spec["cycles_used"], spec["max_cycles"])
    tip = tip_within_window(spec["tip_temperature_c"], spec["temperature_window_c"])
    reference = spec.get("reference_c", REFERENCE_TIP_C)
    interval = spec.get("doubling_interval_c", DOUBLING_INTERVAL_C)
    event_units = thermal_exposure_units(
        spec["dwell_s"], spec["tip_temperature_c"], reference, interval
    )
    prior = require_real("prior_exposure_units", spec["prior_exposure_units"],
                         minimum=0.0)
    budget = require_real("max_exposure_units", spec["max_exposure_units"],
                          minimum=0.0, allow_equal=False)
    cumulative = prior + event_units
    over_budget = cumulative > budget + EXPOSURE_TOLERANCE

    findings = []
    if pad == "lifted":
        findings.append("the pad has separated from the laminate; no rework applies")
    if cycles["exhausted"]:
        findings.append(
            "the joint has already taken its %d permitted rework cycles"
            % cycles["max_cycles"]
        )
    if not tip["within_window"]:
        findings.append(
            "iron tip at %.1f C sits outside the qualified window %.1f-%.1f C"
            % (tip["tip_temperature_c"], tip["window_c"][0], tip["window_c"][1])
        )
    if over_budget:
        findings.append(
            "cumulative thermal exposure %.3f units exceeds the %.3f unit budget"
            % (cumulative, budget)
        )

    refused = pad == "lifted" or cycles["exhausted"] or not tip["within_window"] \
        or over_budget
    if refused:
        permission = "rework-refused"
    elif pad == "damaged-bonded" or cycles["last_allowed"]:
        permission = "rework-with-approval"
        if pad == "damaged-bonded":
            findings.append("a damaged but bonded pad is reworked under approval only")
        if cycles["last_allowed"]:
            findings.append("this cycle consumes the last of the joint's allowance")
    else:
        permission = "rework-permitted"

    post = None
    if "post_rework" in spec and spec["post_rework"] is not None:
        post = grade_reworked_joint(spec["post_rework"])
        if post["verdict"] == "reject":
            findings.append(
                "finished joint rejected on: %s" % ", ".join(post["driving"])
            )

    return {
        "pad_condition": pad,
        "cycles": cycles,
        "tip": tip,
        "event_exposure_units": event_units,
        "cumulative_exposure_units": cumulative,
        "max_exposure_units": budget,
        "over_exposure_budget": over_budget,
        "permission": permission,
        "post_rework": post,
        "findings": findings,
    }
