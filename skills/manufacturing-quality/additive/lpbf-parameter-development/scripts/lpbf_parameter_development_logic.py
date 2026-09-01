"""Laser powder bed fusion (LPBF) process parameter development.

LPBF builds are driven by four process parameters: laser power (W),
scan speed (mm/s), hatch spacing (mm), and layer thickness (mm). The
volumetric energy density ties them together:

    VED = laser power / (scan speed x hatch spacing x layer thickness)

in J/mm^3. VED maps to the melt pool regime: low to moderate VED keeps
the melt pool in conduction mode (shallow, wide, stable); high VED
drives the pool into keyhole mode (deep, narrow, vapor depression)
with porosity risk. Hatch overlap checks that adjacent melt tracks
overlap so that un-melted gaps do not remain between scan lines.

This module implements the parameter development model exercised by
scripts/test_lpbf_parameter_development.py (stdlib unittest, offline):
the volumetric energy density computation, hatch overlap and melt pool
penetration checks, the conduction/transition/keyhole process window
classification, the parameter development matrix across power, speed,
and hatch grids, and the qualification test matrix (coupon builds,
density, mechanical testing) per the additive manufacturing
qualification framework.

All functions are deterministic, validate their inputs, and raise
ValueError on malformed values instead of returning a silent result.
"""

# Default process window heuristics in J/mm^3 (material dependent; the
# caller may override them per alloy).
DEFAULT_CONDUCTION_VED = 60.0
DEFAULT_KEYHOLE_VED = 100.0

# Qualification test matrix per candidate parameter set: test name and
# the default coupon count built for that test. Density coupons check
# part density; tensile, fatigue, and hardness coupons check mechanical
# properties. One spare coupon per test type is included for re-test.
QUALIFICATION_TESTS = (
    ("density", 3, "Archimedes density on density coupons"),
    ("tensile", 5, "ambient tensile properties"),
    ("fatigue", 5, "load-controlled fatigue"),
    ("hardness", 2, "macro hardness"),
)


def _positive_float(value, name):
    """Return float(value) when value is numeric and > 0; else ValueError."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric" % name)
    if number <= 0:
        raise ValueError("%s must be > 0" % name)
    return number


def volumetric_energy_density(laser_power, scan_speed, hatch_spacing, layer_thickness):
    """Volumetric energy density of the LPBF process, in J/mm^3.

    VED = laser power / (scan speed x hatch spacing x layer thickness).
    Units: laser_power in W, scan_speed in mm/s, hatch_spacing in mm,
    layer_thickness in mm. Raises ValueError when a value is missing,
    non-numeric, or not positive.
    """
    power = _positive_float(laser_power, "laser power")
    speed = _positive_float(scan_speed, "scan speed")
    hatch = _positive_float(hatch_spacing, "hatch spacing")
    layer = _positive_float(layer_thickness, "layer thickness")
    return power / (speed * hatch * layer)


def hatch_overlap_fraction(melt_pool_width, hatch_spacing):
    """Overlap fraction between adjacent melt tracks.

    overlap = (melt_pool_width - hatch_spacing) / melt_pool_width.
    Positive when the melt pool is wider than the hatch spacing (tracks
    overlap), zero when they just touch, negative when the hatch spacing
    leaves un-melted gaps between tracks. A negative overlap flags
    incomplete fusion risk. Units in mm; values must be positive.
    """
    width = _positive_float(melt_pool_width, "melt pool width")
    hatch = _positive_float(hatch_spacing, "hatch spacing")
    return (width - hatch) / width


def melt_pool_penetration(melt_pool_depth, layer_thickness):
    """Melt pool depth relative to the layer thickness.

    ratio = melt_pool_depth / layer_thickness. A ratio well above 1
    means the pool penetrates several layers, which is the deep
    penetration signature of keyhole mode. Values in mm, positive.
    """
    depth = _positive_float(melt_pool_depth, "melt pool depth")
    layer = _positive_float(layer_thickness, "layer thickness")
    return depth / layer


def classify_process_window(
    ved,
    conduction_ved=DEFAULT_CONDUCTION_VED,
    keyhole_ved=DEFAULT_KEYHOLE_VED,
):
    """Map a volumetric energy density to the melt pool regime.

    conduction_ved and keyhole_ved are material dependent window bounds
    in J/mm^3. Regimes:

    - conduction: ved <= conduction_ved. Shallow stable melt pool, low
      porosity expectation when hatch overlap is positive.
    - transition: conduction_ved < ved < keyhole_ved. Mixed mode,
      intermittent keyholing possible; porosity expectation rises with
      VED.
    - keyhole: ved >= keyhole_ved. Deep narrow pool with vapor
      depression; porosity from trapped vapor and keyhole collapse.

    Returns a dict with 'ved', 'regime', 'porosity_expectation', and
    'note'. Raises ValueError when ved is not positive or the window
    bounds are inverted (conduction_ved >= keyhole_ved).
    """
    value = _positive_float(ved, "volumetric energy density")
    low = _positive_float(conduction_ved, "conduction window bound")
    high = _positive_float(keyhole_ved, "keyhole window bound")
    if low >= high:
        raise ValueError("conduction_ved must be < keyhole_ved")
    if value <= low:
        regime = "conduction"
        porosity = "low, provided hatch overlap is positive"
        note = "shallow stable melt pool; conduction mode window"
    elif value >= high:
        regime = "keyhole"
        porosity = "high; trapped vapor and keyhole collapse porosity"
        note = "deep narrow melt pool with vapor depression; keyhole window"
    else:
        regime = "transition"
        porosity = "moderate; intermittent keyholing possible"
        note = "mixed mode between the conduction and keyhole windows"
    return {
        "ved": value,
        "regime": regime,
        "porosity_expectation": porosity,
        "note": note,
    }


def build_parameter_matrix(
    power_values,
    speed_values,
    hatch_values,
    layer_thickness,
    conduction_ved=DEFAULT_CONDUCTION_VED,
    keyhole_ved=DEFAULT_KEYHOLE_VED,
):
    """Parameter development matrix across power, speed, and hatch grids.

    Builds every combination of the three lists (power x speed x hatch)
    at the fixed layer thickness, computes the volumetric energy density
    and the process window regime for each combination, and returns rows
    sorted deterministically by (power, scan_speed, hatch_spacing).

    Each row: {'power', 'scan_speed', 'hatch_spacing', 'layer_thickness',
    'volumetric_energy_density', 'regime'}. Raises ValueError when a grid
    is empty, non-list, or holds a non-positive value.
    """
    if not isinstance(power_values, (list, tuple)) or not power_values:
        raise ValueError("power_values must be a non-empty list")
    if not isinstance(speed_values, (list, tuple)) or not speed_values:
        raise ValueError("speed_values must be a non-empty list")
    if not isinstance(hatch_values, (list, tuple)) or not hatch_values:
        raise ValueError("hatch_values must be a non-empty list")
    layer = _positive_float(layer_thickness, "layer thickness")
    rows = []
    for power in power_values:
        p = _positive_float(power, "laser power")
        for speed in speed_values:
            s = _positive_float(speed, "scan speed")
            for hatch in hatch_values:
                h = _positive_float(hatch, "hatch spacing")
                ved = volumetric_energy_density(p, s, h, layer)
                regime = classify_process_window(
                    ved, conduction_ved, keyhole_ved
                )["regime"]
                rows.append(
                    {
                        "power": p,
                        "scan_speed": s,
                        "hatch_spacing": h,
                        "layer_thickness": layer,
                        "volumetric_energy_density": ved,
                        "regime": regime,
                    }
                )
    rows.sort(key=lambda r: (r["power"], r["scan_speed"], r["hatch_spacing"]))
    return rows


def process_window_verdict(matrix, material=""):
    """Summarize the process window coverage of a parameter matrix.

    matrix: list of rows from build_parameter_matrix(). Returns a dict
    with the total row count, per-regime counts, 'any_keyhole' (bool),
    and a one-line 'verdict'. Raises ValueError when matrix is not a
    non-empty list of mappings or a row carries an unknown regime.
    """
    if not isinstance(matrix, list) or not matrix:
        raise ValueError("matrix must be a non-empty list of rows")
    total = len(matrix)
    counts = {"conduction": 0, "transition": 0, "keyhole": 0}
    for row in matrix:
        if not isinstance(row, dict):
            raise ValueError("each matrix row must be a mapping")
        regime = row.get("regime")
        if regime not in counts:
            raise ValueError("unknown regime %r in matrix row" % (regime,))
        counts[regime] += 1
    any_keyhole = counts["keyhole"] > 0
    if any_keyhole:
        verdict = (
            "keyhole risk: %d of %d combinations fall in the keyhole window; "
            "screen for porosity" % (counts["keyhole"], total)
        )
    elif counts["transition"]:
        verdict = (
            "transition band: %d of %d combinations fall between the windows; "
            "confirm with melt pool checks" % (counts["transition"], total)
        )
    else:
        verdict = "all combinations inside the conduction window"
    return {
        "material": material,
        "total": total,
        "conduction_count": counts["conduction"],
        "transition_count": counts["transition"],
        "keyhole_count": counts["keyhole"],
        "any_keyhole": any_keyhole,
        "verdict": verdict,
    }


def build_qualification_test_matrix(
    parameter_sets,
    coupon_counts=None,
):
    """Qualification test matrix per candidate parameter set.

    parameter_sets: non-empty list of dicts, each with 'parameter_set_id'
    and the four LPBF parameters ('laser_power', 'scan_speed',
    'hatch_spacing', 'layer_thickness'), typically rows produced during
    parameter development. coupon_counts: optional mapping of test name
    to coupon count; defaults to QUALIFICATION_TESTS. Each candidate
    parameter set gets density, tensile, fatigue, and hardness coupons
    per the additive manufacturing qualification framework.

    Returns rows sorted by (parameter_set_id, test): {'parameter_set_id',
    'test', 'coupon_count', 'purpose'}. Raises ValueError on a malformed
    parameter set or an unknown or non-positive coupon count.
    """
    if not isinstance(parameter_sets, list) or not parameter_sets:
        raise ValueError("parameter_sets must be a non-empty list")
    counts = {}
    for test, default_count, purpose in QUALIFICATION_TESTS:
        counts[test] = coupon_counts.get(test, default_count) if coupon_counts else default_count
    for test, count in counts.items():
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError("coupon count for %r must be a positive int" % test)
    rows = []
    for index, candidate in enumerate(parameter_sets):
        if not isinstance(candidate, dict):
            raise ValueError("each parameter set must be a mapping")
        set_id = candidate.get("parameter_set_id")
        if not isinstance(set_id, str) or not set_id.strip():
            raise ValueError("parameter_set_id must be a non-empty string")
        for key in ("laser_power", "scan_speed", "hatch_spacing", "layer_thickness"):
            _positive_float(candidate.get(key), key)
        for test, count, purpose in QUALIFICATION_TESTS:
            rows.append(
                {
                    "parameter_set_id": set_id.strip(),
                    "test": test,
                    "coupon_count": counts[test],
                    "purpose": purpose,
                }
            )
    rows.sort(key=lambda r: (r["parameter_set_id"], r["test"]))
    return rows
