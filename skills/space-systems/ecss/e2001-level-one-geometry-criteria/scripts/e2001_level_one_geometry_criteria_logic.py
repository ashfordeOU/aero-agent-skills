#!/usr/bin/env python3
"""Level-one multipactor geometry screen (ECSS-E-ST-20-01C clause 5.3.2.2.2).

Deterministic, offline, stdlib-only implementation of the geometry limits that
decide whether a radio-frequency gap may be assessed with the simpler first
analysis level, whose charts are built for parallel or coaxial gap shapes.

No standard text is reproduced here; the clause is cited as the anchor only and
the procedure below is a paraphrased, implementable restatement.
"""

import math

PARALLEL_PLATE = "parallel-plate"
COAXIAL = "coaxial"
UNCATEGORIZED = "uncategorized"

# Descriptors an electrical design database may carry for a gap, mapped onto
# the two shape families the first analysis level covers.
SHAPE_ALIASES = {
    "parallel-plate": PARALLEL_PLATE,
    "planar-gap": PARALLEL_PLATE,
    "plate-gap": PARALLEL_PLATE,
    "waveguide-height-gap": PARALLEL_PLATE,
    "coaxial": COAXIAL,
    "coaxial-gap": COAXIAL,
    "annular-gap": COAXIAL,
}

# Shapes that occur in real radio-frequency hardware but sit outside the
# level-one chart family: they are reported as uncategorized and escalated.
OUT_OF_SCOPE_SHAPES = frozenset(
    (
        "wedge-gap",
        "stepped-iris",
        "corrugated-surface",
        "dielectric-loaded-gap",
        "helix-gap",
        "comb-line-gap",
        "curved-taper-gap",
    )
)

# Quasi-infinite-plate assumption: the facing surfaces must extend far enough
# relative to their separation that edge leakage does not govern the electron
# trajectories the charts assume.
MIN_EXTENT_TO_GAP_RATIO = 10.0

# Quasi-parallel assumption: residual wedge angle between the facing surfaces.
MAX_TILT_DEG = 5.0

# Coaxial radius ratio band over which the annular gap behaves closely enough
# to a plane gap of the same radial separation.
MIN_COAXIAL_RADIUS_RATIO = 1.05
MAX_COAXIAL_RADIUS_RATIO = 5.0

# Charted frequency-gap band, in GHz.mm.
FD_MIN_GHZ_MM = 0.02
FD_MAX_GHZ_MM = 100.0

# Absorbs floating-point representation error on an exactly-compliant boundary;
# it never widens an engineering limit.
REL_TOL = 1e-9

NEXT_STEP_CHART = "level-one-chart-lookup"
NEXT_STEP_ESCALATE = "escalate-to-level-two"


def _require_number(name, value):
    """Return value as float or raise ValueError if it is not a real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_positive(name, value):
    """Return value as a strictly positive float or raise ValueError."""
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return value


def _below_limit(value, limit):
    """True when value is under limit beyond representation error."""
    return value < limit and not math.isclose(value, limit, rel_tol=REL_TOL)


def _above_limit(value, limit):
    """True when value is over limit beyond representation error."""
    return value > limit and not math.isclose(value, limit, rel_tol=REL_TOL)


def categorize_gap_shape(geometry):
    """Map a declared gap descriptor onto a level-one shape family.

    Returns PARALLEL_PLATE, COAXIAL or UNCATEGORIZED. Raises ValueError when
    the descriptor is missing or is not a shape the library recognizes at all.
    """
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (type(geometry),))
    raw = geometry.get("shape")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("geometry['shape'] must be a non-empty string")
    key = raw.strip().lower()
    if key in SHAPE_ALIASES:
        return SHAPE_ALIASES[key]
    if key in OUT_OF_SCOPE_SHAPES:
        return UNCATEGORIZED
    raise ValueError("unrecognized gap shape %r" % (raw,))


def effective_gap_mm(geometry):
    """Return the gap used by the level-one charts, in millimetres.

    Plane gap: the plate separation. Annular gap: the radial difference of the
    two conductor radii. Raises ValueError for an uncategorized shape or for
    radii that do not describe a physical annulus.
    """
    shape = categorize_gap_shape(geometry)
    if shape == PARALLEL_PLATE:
        return _require_positive("gap_mm", geometry.get("gap_mm"))
    if shape == COAXIAL:
        inner = _require_positive("inner_radius_mm", geometry.get("inner_radius_mm"))
        outer = _require_positive("outer_radius_mm", geometry.get("outer_radius_mm"))
        if outer <= inner:
            raise ValueError(
                "outer_radius_mm (%r) must exceed inner_radius_mm (%r)" % (outer, inner)
            )
        return outer - inner
    raise ValueError(
        "effective gap is undefined for shape %r outside the level-one families"
        % (geometry.get("shape"),)
    )


def check_parallel_plate_geometry(geometry):
    """Return the plane-gap findings; an empty list means the shape qualifies."""
    findings = []
    gap = _require_positive("gap_mm", geometry.get("gap_mm"))
    extent = _require_positive("surface_extent_mm", geometry.get("surface_extent_mm"))
    tilt = _require_number("tilt_deg", geometry.get("tilt_deg", 0.0))
    if tilt < 0.0 or tilt >= 90.0:
        raise ValueError("tilt_deg must sit in [0, 90), got %r" % (tilt,))
    ratio = extent / gap
    if _below_limit(ratio, MIN_EXTENT_TO_GAP_RATIO):
        findings.append(
            "surface-extent-to-gap ratio %.4f is under the edge-effect limit %.1f"
            % (ratio, MIN_EXTENT_TO_GAP_RATIO)
        )
    if _above_limit(tilt, MAX_TILT_DEG):
        findings.append(
            "facing surfaces tilt by %.4f deg, over the quasi-parallel limit %.1f deg"
            % (tilt, MAX_TILT_DEG)
        )
    return findings


def check_coaxial_geometry(geometry):
    """Return the annular-gap findings; an empty list means the shape qualifies."""
    findings = []
    inner = _require_positive("inner_radius_mm", geometry.get("inner_radius_mm"))
    outer = _require_positive("outer_radius_mm", geometry.get("outer_radius_mm"))
    if outer <= inner:
        raise ValueError(
            "outer_radius_mm (%r) must exceed inner_radius_mm (%r)" % (outer, inner)
        )
    ratio = outer / inner
    if _below_limit(ratio, MIN_COAXIAL_RADIUS_RATIO):
        findings.append(
            "radius ratio %.4f is under the charted band floor %.2f"
            % (ratio, MIN_COAXIAL_RADIUS_RATIO)
        )
    if _above_limit(ratio, MAX_COAXIAL_RADIUS_RATIO):
        findings.append(
            "radius ratio %.4f is over the charted band ceiling %.2f"
            % (ratio, MAX_COAXIAL_RADIUS_RATIO)
        )
    return findings


def frequency_gap_product_ghz_mm(frequency_ghz, gap_mm):
    """Return the frequency-gap product in GHz.mm."""
    frequency_ghz = _require_positive("frequency_ghz", frequency_ghz)
    gap_mm = _require_positive("gap_mm", gap_mm)
    return frequency_ghz * gap_mm


def check_chart_range(fd_ghz_mm):
    """Return the findings raised by a frequency-gap product outside the band."""
    fd = _require_positive("fd_ghz_mm", fd_ghz_mm)
    findings = []
    if _below_limit(fd, FD_MIN_GHZ_MM):
        findings.append(
            "frequency-gap product %.5f GHz.mm is below the charted floor %.3f"
            % (fd, FD_MIN_GHZ_MM)
        )
    if _above_limit(fd, FD_MAX_GHZ_MM):
        findings.append(
            "frequency-gap product %.5f GHz.mm is above the charted ceiling %.1f"
            % (fd, FD_MAX_GHZ_MM)
        )
    return findings


def evaluate_level_one_geometry(geometry, frequency_ghz):
    """Screen one critical-region gap against every level-one geometry limit.

    Returns a record carrying the shape family, the effective gap, the
    frequency-gap product, the findings, the eligibility verdict and the next
    step. A shape outside the level-one families is escalated without a gap.
    """
    frequency_ghz = _require_positive("frequency_ghz", frequency_ghz)
    shape = categorize_gap_shape(geometry)
    region_id = geometry.get("region_id", "unnamed-region")
    record = {
        "region_id": region_id,
        "shape": shape,
        "frequency_ghz": frequency_ghz,
        "effective_gap_mm": None,
        "frequency_gap_product_ghz_mm": None,
        "findings": [],
        "level_one_eligible": False,
        "next_step": NEXT_STEP_ESCALATE,
    }
    if shape == UNCATEGORIZED:
        record["findings"].append(
            "gap shape %r is outside the parallel and coaxial chart families"
            % (geometry.get("shape"),)
        )
        return record
    if shape == PARALLEL_PLATE:
        findings = check_parallel_plate_geometry(geometry)
    else:
        findings = check_coaxial_geometry(geometry)
    gap = effective_gap_mm(geometry)
    fd = frequency_gap_product_ghz_mm(frequency_ghz, gap)
    findings = findings + check_chart_range(fd)
    record["effective_gap_mm"] = gap
    record["frequency_gap_product_ghz_mm"] = fd
    record["findings"] = findings
    record["level_one_eligible"] = not findings
    record["next_step"] = NEXT_STEP_CHART if not findings else NEXT_STEP_ESCALATE
    return record


def select_driving_region(records):
    """Return the eligible record with the smallest frequency-gap product.

    The smallest product drives the first analysis level because it sits
    deepest in the susceptible part of the chart. Raises ValueError when no
    record qualifies.
    """
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    eligible = [r for r in records if r.get("level_one_eligible")]
    if not eligible:
        raise ValueError("no eligible record: every gap was escalated")
    return min(eligible, key=lambda r: (r["frequency_gap_product_ghz_mm"], r["region_id"]))


def screen_gap_inventory(geometries, frequency_ghz):
    """Screen a whole inventory of critical-region gaps at one frequency.

    Raises ValueError on an empty inventory or a repeated region identifier.
    """
    if not isinstance(geometries, (list, tuple)) or not geometries:
        raise ValueError("geometries must be a non-empty sequence")
    seen = set()
    records = []
    for geometry in geometries:
        if not isinstance(geometry, dict):
            raise ValueError("each geometry must be a mapping, got %r" % (type(geometry),))
        region_id = geometry.get("region_id", "unnamed-region")
        if region_id in seen:
            raise ValueError("duplicate region_id %r in inventory" % (region_id,))
        seen.add(region_id)
        records.append(evaluate_level_one_geometry(geometry, frequency_ghz))
    eligible = [r for r in records if r["level_one_eligible"]]
    escalated = [r["region_id"] for r in records if not r["level_one_eligible"]]
    summary = {
        "records": records,
        "eligible_count": len(eligible),
        "escalated_region_ids": escalated,
        "driving_region_id": None,
        "inventory_level_one_eligible": len(escalated) == 0,
    }
    if eligible:
        summary["driving_region_id"] = select_driving_region(records)["region_id"]
    return summary
