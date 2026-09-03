"""Icing flight test envelope logic (pure stdlib, deterministic).

Categorizes an icing encounter against a simplified typical summary of
the FAR/CS 25 Appendix C continuous maximum and intermittent maximum
icing envelopes, rates encounter severity, screens natural icing search
conditions, checks an artificial ice shape test matrix over the critical
surfaces, and pairs ice protection effectiveness test configurations
with the envelope rows that must be flown.

The full Appendix C table is authority-controlled regulation text. This
module implements paraphrased representative boundary points only, for
flight test planning support at reference level.
"""

import math

# Total air temperature band of the reference Appendix C envelopes (C).
TAT_MIN_C = -30.0
TAT_MAX_C = 0.0

# Continuous maximum (stratiform) envelope: representative LWC limits.
LWC_CM_MAX = 0.44    # g/m3 at -10 C (peak)
LWC_CM_0C = 0.20     # g/m3 at 0 C
LWC_CM_N30C = 0.15   # g/m3 at -30 C
CM_MVD_MIN = 15.0    # micron
CM_MVD_MAX = 40.0    # micron

# Intermittent maximum (cumuliform) envelope: representative LWC limits.
LWC_IM_MAX = 1.40    # g/m3 at -10 C (peak)
LWC_IM_0C = 0.65     # g/m3 at 0 C
LWC_IM_N30C = 0.35   # g/m3 at -30 C
IM_MVD_MIN = 15.0    # micron
IM_MVD_MAX = 50.0    # micron

# Supercooled large droplet threshold: above this MVD the encounter is
# outside the Appendix C envelope by this model.
SLD_MVD_MIN = 50.0   # micron

# Natural icing search: minimum forecast LWC as a fraction of the
# continuous maximum LWC limit at the flight total air temperature.
SEARCH_LWC_FRACTION = 0.1

# Artificial shape matrix: minimum coverage fraction per critical
# unprotected surface and the critical surface list.
COVERAGE_MIN = 0.8
CRITICAL_SURFACES = [
    "wing",
    "horizontal-tail",
    "vertical-tail",
    "windshield",
    "probe",
]

# Allowed artificial ice shape types.
SHAPE_TYPES = ("glaze", "rime", "runback", "mixed")

# Encounter severity: duration above this many minutes steps the label up.
SEVERE_DURATION_MIN = 30.0

SLD_REASON = (
    "supercooled-large-droplet conditions exceed the appendix C envelope"
)

SEVERITY_LABELS = ("trace", "light", "moderate", "severe")


def _require_finite(*values):
    """Raise ValueError when any value is not a finite number."""
    for value in values:
        if value is None or not math.isfinite(value):
            raise ValueError("icing envelope inputs must be finite numbers")


def _lerp(t, t0, v0, t1, v1):
    """Linearly interpolate value v0 at t0 to v1 at t1, evaluated at t."""
    return v0 + (v1 - v0) * (t - t0) / (t1 - t0)


def cm_lwc_limit(tat):
    """Continuous maximum LWC limit (g/m3) at total air temperature tat.

    Piecewise linear through (-30, 0.15), (-10, 0.44), (0, 0.20); the
    temperature is clamped to [-30, 0] C. Non-finite tat raises
    ValueError.
    """
    _require_finite(tat)
    if tat <= TAT_MIN_C:
        return LWC_CM_N30C
    if tat >= TAT_MAX_C:
        return LWC_CM_0C
    if tat == -10.0:
        return LWC_CM_MAX
    if tat < -10.0:
        return _lerp(tat, TAT_MIN_C, LWC_CM_N30C, -10.0, LWC_CM_MAX)
    return _lerp(tat, -10.0, LWC_CM_MAX, TAT_MAX_C, LWC_CM_0C)


def im_lwc_limit(tat):
    """Intermittent maximum LWC limit (g/m3) at total air temperature tat.

    Piecewise linear through (-30, 0.35), (-10, 1.40), (0, 0.65); the
    temperature is clamped to [-30, 0] C. Non-finite tat raises
    ValueError.
    """
    _require_finite(tat)
    if tat <= TAT_MIN_C:
        return LWC_IM_N30C
    if tat >= TAT_MAX_C:
        return LWC_IM_0C
    if tat == -10.0:
        return LWC_IM_MAX
    if tat < -10.0:
        return _lerp(tat, TAT_MIN_C, LWC_IM_N30C, -10.0, LWC_IM_MAX)
    return _lerp(tat, -10.0, LWC_IM_MAX, TAT_MAX_C, LWC_IM_0C)


def _governing_limit(lwc, tat):
    """Pick the governing LWC limit for margin reporting."""
    cm_lim = cm_lwc_limit(tat)
    if lwc <= cm_lim:
        return cm_lim
    return im_lwc_limit(tat)


def envelope_verdict(lwc, mvd, tat):
    """Categorize an icing encounter against the Appendix C envelopes.

    Returns a dict with in_envelope (bool), regime ("continuous-max" |
    "intermittent-max" | "outside"), margin (governing LWC limit minus
    lwc) and reasons (list of str). Negative or non-finite lwc, mvd or
    tat raise ValueError.
    """
    _require_finite(lwc, mvd, tat)
    if lwc < 0.0 or mvd < 0.0:
        raise ValueError("lwc and mvd must be non-negative")
    cm_lim = cm_lwc_limit(tat)
    im_lim = im_lwc_limit(tat)
    reasons = []

    if mvd > SLD_MVD_MIN:
        return {
            "in_envelope": False,
            "regime": "outside",
            "margin": _governing_limit(lwc, tat) - lwc,
            "reasons": [SLD_REASON],
        }

    in_cm_band = CM_MVD_MIN <= mvd <= CM_MVD_MAX
    in_im_band = IM_MVD_MIN <= mvd <= IM_MVD_MAX

    if lwc <= cm_lim and in_cm_band:
        return {
            "in_envelope": True,
            "regime": "continuous-max",
            "margin": cm_lim - lwc,
            "reasons": reasons,
        }

    if lwc <= im_lim and in_im_band:
        return {
            "in_envelope": True,
            "regime": "intermittent-max",
            "margin": im_lim - lwc,
            "reasons": reasons,
        }

    if lwc > im_lim:
        reasons.append("liquid water content above the intermittent maximum limit")
    if not in_im_band:
        reasons.append("median volumetric diameter outside the intermittent maximum band")
    if not reasons:
        reasons.append("encounter outside both appendix C envelopes")
    return {
        "in_envelope": False,
        "regime": "outside",
        "margin": _governing_limit(lwc, tat) - lwc,
        "reasons": reasons,
    }


def encounter_severity(lwc, tat, duration_min):
    """Rate encounter severity from the LWC to continuous-max ratio.

    Returns (severity_index, label): index 0..3 with labels trace, light,
    moderate, severe. Ratio below 0.5 is trace, below 1.0 light, below
    1.5 moderate when also within the intermittent LWC envelope (else
    severe), at or above 1.5 severe. A duration above
    SEVERE_DURATION_MIN steps the label up one level, capped at severe.
    Negative or non-finite inputs raise ValueError.
    """
    _require_finite(lwc, tat, duration_min)
    if lwc < 0.0 or duration_min < 0.0:
        raise ValueError("lwc and duration must be non-negative")
    ratio = lwc / cm_lwc_limit(tat)
    if ratio < 0.5:
        index = 0
    elif ratio < 1.0:
        index = 1
    elif ratio < 1.5 and lwc <= im_lwc_limit(tat):
        index = 2
    else:
        index = 3
    if duration_min > SEVERE_DURATION_MIN:
        index = min(3, index + 1)
    return index, SEVERITY_LABELS[index]


def natural_icing_search_ok(tat, cloud_base_ft, freezing_level_ft, lwc_forecast):
    """Screen natural icing search conditions.

    Returns (ok_bool, reasons). Search is acceptable when the total air
    temperature is within [-30, 0] C, the forecast LWC is at least
    SEARCH_LWC_FRACTION times the continuous maximum limit, and the
    freezing level is at or above the cloud base (the check condition is
    freezing_level_ft < cloud_base_ft as input). Non-finite values raise
    ValueError.
    """
    _require_finite(tat, cloud_base_ft, freezing_level_ft, lwc_forecast)
    if lwc_forecast < 0.0 or cloud_base_ft < 0.0 or freezing_level_ft < 0.0:
        raise ValueError("altitudes and forecast lwc must be non-negative")
    ok = True
    reasons = []
    if tat > TAT_MAX_C:
        ok = False
        reasons.append("total air temperature above 0 C")
    if tat < TAT_MIN_C:
        ok = False
        reasons.append("total air temperature below -30 C")
    if lwc_forecast < SEARCH_LWC_FRACTION * cm_lwc_limit(tat):
        ok = False
        reasons.append(
            "forecast liquid water content below 10 percent of the continuous maximum limit"
        )
    if freezing_level_ft < cloud_base_ft:
        ok = False
        reasons.append("freezing level below the cloud base")
    return ok, reasons


def artificial_shape_check(shapes):
    """Check an artificial ice shape matrix against the critical surfaces.

    Each shape is a dict with surface (str), type ("glaze" | "rime" |
    "runback" | "mixed"), coverage_frac (0..1) and roughness_ok (bool).
    Issues are raised when a critical surface is missing, has coverage
    below COVERAGE_MIN, or has roughness_ok False. Returns a dict with
    verdict ("pass" | "fail") and issues (list of str). Coverage outside
    [0, 1], unknown surfaces and unknown shape types raise ValueError.
    """
    issues = []
    seen = {}
    for shape in shapes:
        surface = shape.get("surface")
        coverage = shape.get("coverage_frac")
        shape_type = shape.get("type")
        roughness_ok = shape.get("roughness_ok")
        if surface not in CRITICAL_SURFACES:
            raise ValueError("unknown surface in an artificial shape: %r" % (surface,))
        if shape_type not in SHAPE_TYPES:
            raise ValueError("unknown artificial shape type: %r" % (shape_type,))
        if coverage is None or not math.isfinite(coverage):
            raise ValueError("coverage_frac must be a finite number")
        if coverage < 0.0 or coverage > 1.0:
            raise ValueError("coverage_frac must be within [0, 1]")
        if not isinstance(roughness_ok, bool):
            raise ValueError("roughness_ok must be a bool")
        seen[surface] = (coverage, roughness_ok)
    for surface in CRITICAL_SURFACES:
        if surface not in seen:
            issues.append("missing artificial shape on %s" % surface)
            continue
        coverage, roughness_ok = seen[surface]
        if coverage < COVERAGE_MIN:
            issues.append("coverage below 0.8 on %s" % surface)
        if not roughness_ok:
            issues.append("roughness not representative on %s" % surface)
    return {"verdict": "pass" if not issues else "fail", "issues": issues}


def standard_envelope_rows():
    """Representative envelope rows that must be flown for effectiveness.

    One row per boundary condition of the simplified continuous maximum
    and intermittent maximum envelopes; each row carries the condition
    name, the flight condition inputs and the expected regime.
    """
    return [
        {
            "condition": "continuous-maximum-peak-lwc",
            "tat": -10.0,
            "lwc": LWC_CM_MAX,
            "mvd": 20.0,
            "regime": "continuous-max",
        },
        {
            "condition": "continuous-maximum-warm-limit",
            "tat": 0.0,
            "lwc": LWC_CM_0C,
            "mvd": 20.0,
            "regime": "continuous-max",
        },
        {
            "condition": "intermittent-maximum-peak-lwc",
            "tat": -10.0,
            "lwc": LWC_IM_MAX,
            "mvd": 25.0,
            "regime": "intermittent-max",
        },
        {
            "condition": "intermittent-maximum-cold-limit",
            "tat": -30.0,
            "lwc": LWC_IM_N30C,
            "mvd": 25.0,
            "regime": "intermittent-max",
        },
    ]


def effectiveness_test_points(configs, envelope_rows):
    """Pair test configurations with the envelope rows to be flown.

    Each config is a dict with name (str), anti_ice ("on" | "off") and
    de_ice_cycle (str). Returns one row per (config, envelope row) as
    {config, condition, expected_regime}. Configs missing name or with
    anti_ice outside on/off raise ValueError.
    """
    rows = []
    for config in configs:
        name = config.get("name")
        anti_ice = config.get("anti_ice")
        if not name or anti_ice not in ("on", "off"):
            raise ValueError("config requires name and anti_ice on/off")
        if "de_ice_cycle" not in config:
            raise ValueError("config requires a de_ice_cycle setting")
        for env_row in envelope_rows:
            rows.append(
                {
                    "config": name,
                    "condition": env_row["condition"],
                    "expected_regime": env_row["regime"],
                }
            )
    return rows


def summarize(lwc, mvd, tat, duration_min):
    """One-line encounter summary dict for the SKILL worked example."""
    verdict = envelope_verdict(lwc, mvd, tat)
    severity_index, severity_label = encounter_severity(lwc, tat, duration_min)
    return {
        "in_envelope": verdict["in_envelope"],
        "regime": verdict["regime"],
        "margin": verdict["margin"],
        "reasons": verdict["reasons"],
        "severity_index": severity_index,
        "severity_label": severity_label,
    }
