"""Multi-layer-insulation blanket design over a moving mechanism.

Anchor: ECSS-E-ST-33-01C clause 4.7.4.3 (MLI on a mechanism is designed with
the cut-outs, clearances and grounding it needs, and never impedes the
motion). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Build the blanket thickness from its layer count, layer pitch and outer
   cover, because the blanket occupies real space next to a moving part.
2. Stack the sweep envelope, that thickness, the tolerance chain and a billow
   allowance into the clearance the installation actually needs, and compare
   it with the gap available. A blanket in vacuum is not the thickness it was
   folded to: it relaxes, and the relaxed state is the one that touches.
3. Size the cut-out around a shaft or a moving arm so the swept diameter plus
   a radial clearance fits through it, and confirm the cut-out edge itself
   never enters the swept path.
4. Convert the cut-out area into an open-area fraction and an effective
   emittance, then into the parasitic heat the openings cost, so a blanket
   perforated for clearance is graded against the thermal budget it was
   installed to protect.
5. Grade the grounding: enough ground points for the blanket area, and a
   series path resistance to structure inside the limit, so no layer floats.
"""

import math

__all__ = [
    "STEFAN_BOLTZMANN",
    "CLEARANCE_TOLERANCE_MM",
    "blanket_thickness_mm",
    "required_clearance_mm",
    "clearance_margin_mm",
    "swept_diameter_mm",
    "required_cutout_diameter_mm",
    "cutout_margin_mm",
    "open_area_fraction",
    "effective_emittance",
    "parasitic_heat_w",
    "grounding_points_required",
    "ground_path_resistance_ohm",
    "assess_mli_design",
]

STEFAN_BOLTZMANN = 5.670374419e-8

# Clearance comparisons are sums of measured lengths; an exact zero margin can
# land a few ULPs on either side.
CLEARANCE_TOLERANCE_MM = 1e-9


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


def _require_non_negative(label, value):
    """Return value as a non-negative float."""
    out = _require_real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def _require_count(label, value):
    """Return value as a strictly positive integer count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def blanket_thickness_mm(layer_count, layer_pitch_mm, cover_thickness_mm=0.0):
    """Return the relaxed thickness a blanket occupies next to the mechanism."""
    layers = _require_count("layer_count", layer_count)
    pitch = _require_positive("layer_pitch_mm", layer_pitch_mm)
    cover = _require_non_negative("cover_thickness_mm", cover_thickness_mm)
    return layers * pitch + cover


def required_clearance_mm(sweep_envelope_mm, thickness_mm, tolerance_stack_mm,
                          billow_allowance_mm):
    """Return the gap the installation needs between structure and the sweep."""
    sweep = _require_non_negative("sweep_envelope_mm", sweep_envelope_mm)
    thickness = _require_positive("thickness_mm", thickness_mm)
    tolerance = _require_non_negative("tolerance_stack_mm", tolerance_stack_mm)
    billow = _require_non_negative("billow_allowance_mm", billow_allowance_mm)
    return sweep + thickness + tolerance + billow


def clearance_margin_mm(available_gap_mm, required_mm):
    """Return how much gap is left once the installation has taken its share."""
    available = _require_positive("available_gap_mm", available_gap_mm)
    required = _require_positive("required_mm", required_mm)
    return available - required


def swept_diameter_mm(moving_part_diameter_mm, radial_excursion_mm=0.0):
    """Return the diameter a moving part actually sweeps through the blanket."""
    diameter = _require_positive("moving_part_diameter_mm", moving_part_diameter_mm)
    excursion = _require_non_negative("radial_excursion_mm", radial_excursion_mm)
    return diameter + 2.0 * excursion


def required_cutout_diameter_mm(swept_mm, radial_clearance_mm):
    """Return the smallest cut-out the swept path can pass through."""
    swept = _require_positive("swept_mm", swept_mm)
    clearance = _require_positive("radial_clearance_mm", radial_clearance_mm)
    return swept + 2.0 * clearance


def cutout_margin_mm(cutout_diameter_mm, required_diameter_mm):
    """Return the diametral margin of a cut-out over the smallest acceptable one."""
    actual = _require_positive("cutout_diameter_mm", cutout_diameter_mm)
    required = _require_positive("required_diameter_mm", required_diameter_mm)
    return actual - required


def open_area_fraction(open_areas_m2, blanket_area_m2):
    """Return the fraction of the blanket that the cut-outs leave open."""
    if not isinstance(open_areas_m2, (list, tuple)):
        raise ValueError("open_areas_m2 must be a sequence of areas")
    total_area = _require_positive("blanket_area_m2", blanket_area_m2)
    opened = 0.0
    for index, area in enumerate(open_areas_m2):
        opened += _require_non_negative("open_areas_m2[%d]" % index, area)
    if opened > total_area:
        raise ValueError(
            "cut-outs total %g m2, more than the %g m2 blanket they are cut from"
            % (opened, total_area)
        )
    return opened / total_area


def effective_emittance(mli_emittance, open_emittance, fraction_open):
    """Return the area-weighted effective emittance of a perforated blanket."""
    mli = _require_positive("mli_emittance", mli_emittance)
    if mli > 1.0:
        raise ValueError("mli_emittance %g exceeds unity" % mli)
    opened = _require_positive("open_emittance", open_emittance)
    if opened > 1.0:
        raise ValueError("open_emittance %g exceeds unity" % opened)
    fraction = _require_non_negative("fraction_open", fraction_open)
    if fraction > 1.0:
        raise ValueError("fraction_open %g exceeds unity" % fraction)
    if opened < mli:
        raise ValueError(
            "open_emittance %g is below mli_emittance %g; a cut-out cannot insulate "
            "better than the blanket" % (opened, mli)
        )
    return mli * (1.0 - fraction) + opened * fraction


def parasitic_heat_w(emittance, area_m2, hot_temperature_k, sink_temperature_k):
    """Return the radiative heat a blanketed area exchanges with its sink."""
    eps = _require_positive("emittance", emittance)
    if eps > 1.0:
        raise ValueError("emittance %g exceeds unity" % eps)
    area = _require_positive("area_m2", area_m2)
    hot = _require_positive("hot_temperature_k", hot_temperature_k)
    sink = _require_positive("sink_temperature_k", sink_temperature_k)
    return STEFAN_BOLTZMANN * eps * area * (hot ** 4 - sink ** 4)


def grounding_points_required(blanket_area_m2, max_area_per_point_m2):
    """Return how many ground points a blanket of this area needs."""
    area = _require_positive("blanket_area_m2", blanket_area_m2)
    per_point = _require_positive("max_area_per_point_m2", max_area_per_point_m2)
    return int(math.ceil(area / per_point - 1e-12))


def ground_path_resistance_ohm(segment_resistances_ohm):
    """Return the series resistance a layer sees on its way to structure."""
    if not isinstance(segment_resistances_ohm, (list, tuple)) or not segment_resistances_ohm:
        raise ValueError("segment_resistances_ohm must be a non-empty sequence")
    total = 0.0
    for index, value in enumerate(segment_resistances_ohm):
        total += _require_non_negative("segment_resistances_ohm[%d]" % index, value)
    return total


def assess_mli_design(spec):
    """Run the full clause 4.7.4.3 MLI-on-a-mechanism assessment.

    spec keys: layer_count, layer_pitch_mm, sweep_envelope_mm,
    tolerance_stack_mm, billow_allowance_mm, available_gap_mm,
    moving_part_diameter_mm, radial_clearance_mm, cutout_diameter_mm,
    blanket_area_m2, cutout_areas_m2, mli_emittance, open_emittance,
    hot_temperature_k, sink_temperature_k, parasitic_budget_w,
    ground_points, max_area_per_point_m2, ground_segment_resistances_ohm,
    max_ground_resistance_ohm; optional cover_thickness_mm,
    radial_excursion_mm.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "layer_count",
        "layer_pitch_mm",
        "sweep_envelope_mm",
        "tolerance_stack_mm",
        "billow_allowance_mm",
        "available_gap_mm",
        "moving_part_diameter_mm",
        "radial_clearance_mm",
        "cutout_diameter_mm",
        "blanket_area_m2",
        "cutout_areas_m2",
        "mli_emittance",
        "open_emittance",
        "hot_temperature_k",
        "sink_temperature_k",
        "parasitic_budget_w",
        "ground_points",
        "max_area_per_point_m2",
        "ground_segment_resistances_ohm",
        "max_ground_resistance_ohm",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    findings = []
    thickness = blanket_thickness_mm(
        spec["layer_count"], spec["layer_pitch_mm"], spec.get("cover_thickness_mm", 0.0)
    )
    required_gap = required_clearance_mm(
        spec["sweep_envelope_mm"], thickness, spec["tolerance_stack_mm"],
        spec["billow_allowance_mm"],
    )
    gap_margin = clearance_margin_mm(spec["available_gap_mm"], required_gap)
    if gap_margin < 0.0 and not math.isclose(
        gap_margin, 0.0, rel_tol=0.0, abs_tol=CLEARANCE_TOLERANCE_MM
    ):
        findings.append(
            "the blanket installation needs %.3f mm and only %.3f mm is available; the "
            "relaxed blanket would foul the motion"
            % (required_gap, float(spec["available_gap_mm"]))
        )

    swept = swept_diameter_mm(
        spec["moving_part_diameter_mm"], spec.get("radial_excursion_mm", 0.0)
    )
    needed_cutout = required_cutout_diameter_mm(swept, spec["radial_clearance_mm"])
    cut_margin = cutout_margin_mm(spec["cutout_diameter_mm"], needed_cutout)
    if cut_margin < 0.0 and not math.isclose(
        cut_margin, 0.0, rel_tol=0.0, abs_tol=CLEARANCE_TOLERANCE_MM
    ):
        findings.append(
            "cut-out is %.3f mm across where %.3f mm is needed; its edge enters the "
            "swept path" % (float(spec["cutout_diameter_mm"]), needed_cutout)
        )

    fraction = open_area_fraction(spec["cutout_areas_m2"], spec["blanket_area_m2"])
    eps_eff = effective_emittance(
        spec["mli_emittance"], spec["open_emittance"], fraction
    )
    parasitic = parasitic_heat_w(
        eps_eff, spec["blanket_area_m2"], spec["hot_temperature_k"],
        spec["sink_temperature_k"],
    )
    budget = _require_positive("parasitic_budget_w", spec["parasitic_budget_w"])
    if parasitic > budget and not math.isclose(
        parasitic, budget, rel_tol=1e-12, abs_tol=0.0
    ):
        findings.append(
            "cut-outs raise the parasitic leak to %.4g W against a %.4g W budget"
            % (parasitic, budget)
        )

    points_needed = grounding_points_required(
        spec["blanket_area_m2"], spec["max_area_per_point_m2"]
    )
    points = _require_count("ground_points", spec["ground_points"])
    if points < points_needed:
        findings.append(
            "blanket has %d ground points where %d are needed for its area"
            % (points, points_needed)
        )
    resistance = ground_path_resistance_ohm(spec["ground_segment_resistances_ohm"])
    limit = _require_positive("max_ground_resistance_ohm", spec["max_ground_resistance_ohm"])
    if resistance > limit and not math.isclose(
        resistance, limit, rel_tol=1e-12, abs_tol=0.0
    ):
        findings.append(
            "ground path to structure measures %.4g ohm against a %.4g ohm limit"
            % (resistance, limit)
        )

    return {
        "blanket_thickness_mm": thickness,
        "required_clearance_mm": required_gap,
        "clearance_margin_mm": gap_margin,
        "swept_diameter_mm": swept,
        "required_cutout_diameter_mm": needed_cutout,
        "cutout_margin_mm": cut_margin,
        "open_area_fraction": fraction,
        "effective_emittance": eps_eff,
        "parasitic_heat_w": parasitic,
        "ground_points_required": points_needed,
        "ground_path_resistance_ohm": resistance,
        "motion_unimpeded": gap_margin >= 0.0 and cut_margin >= 0.0,
        "compliant": not findings,
        "findings": findings,
    }
