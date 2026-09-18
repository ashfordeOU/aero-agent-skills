#!/usr/bin/env python3
"""Radiated magnetic susceptibility setup, ECSS-E-ST-20-07C 5.4.10.3.

Paraphrased procedure, no verbatim standard text. The clause fixes where the
radiating loop is held during a magnetic exposure run and how the arrangement
is proven before the sweep starts:

  exposure positions -> surface normalization and validation
  loop standoff      -> windowed grading, conforming / marginal / deviation
  grid spacing       -> swept-point count over each exposed surface
  loop orientations  -> the orthogonal presentations each position needs
  sense loop         -> the verification read-back the arrangement must give

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Dimensional comparison tolerance. Window edges are differences of float
# lengths, so a dimension sitting exactly on an edge can land a few units in
# the last place outside it. The tolerance absorbs representation error only.
LENGTH_REL_TOL = 1e-12

# Nominal radiating loop diameter the grid spacing is referred to, metres.
DEFAULT_LOOP_DIAMETER_M = 0.12

# Standoff window between the loop plane and the exposed surface, metres.
DEFAULT_STANDOFF_WINDOW_M = (0.04, 0.06)

# Fraction of a window's width at each edge that counts as marginal rather
# than conforming outright.
DEFAULT_MARGIN_FRACTION = 0.10

# Orthogonal loop presentations every exposure position must receive.
REQUIRED_ORIENTATIONS = ("x-normal", "y-normal", "z-normal")

# Surfaces and runs the clause recognizes as exposure positions.
RECOGNIZED_SURFACES = (
    "forward-face",
    "aft-face",
    "port-face",
    "starboard-face",
    "upper-face",
    "lower-face",
    "harness-run",
)

# Smallest sense-loop read-back the verification monitor can resolve, volt.
DEFAULT_MONITOR_FLOOR_V = 1.0e-6

GRADE_CONFORMING = "conforming"
GRADE_MARGINAL = "marginal"
GRADE_DEVIATION = "deviation"

VERDICT_CONFORMS = "setup-conforms"
VERDICT_DEVIATES = "setup-deviates"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _positive(value, name):
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, value))
    return value


def _at_least(value, bound):
    """True when value reaches a lower bound, absorbing float error only."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=LENGTH_REL_TOL, abs_tol=0.0)


def _at_most(value, bound):
    """True when value stays under an upper bound, absorbing float error only."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=LENGTH_REL_TOL, abs_tol=0.0)


def _ceil_units(value, unit):
    """Whole units spanning a length, with an exact fit left un-rounded up.

    math.ceil on a ratio of floats tips to the next integer when the division
    lands a single unit in the last place high, which differs between
    platforms. The tolerance keeps an exact fit an exact fit.
    """
    ratio = value / unit
    nearest = round(ratio)
    if nearest >= 1 and math.isclose(ratio, nearest, rel_tol=1e-9, abs_tol=0.0):
        return int(nearest)
    return max(1, int(math.ceil(ratio)))


def normalize_surface(surface):
    """Return the recognized exposure surface for a raw designation."""
    if not isinstance(surface, str):
        raise ValueError("exposure surface must be a string, got %r" % (surface,))
    key = surface.strip().lower()
    if key not in RECOGNIZED_SURFACES:
        raise ValueError(
            "unrecognized exposure surface %r; recognized: %s"
            % (surface, ", ".join(RECOGNIZED_SURFACES))
        )
    return key


def normalize_orientation(orientation):
    """Return the recognized loop presentation for a raw orientation."""
    if not isinstance(orientation, str):
        raise ValueError("loop orientation must be a string, got %r" % (orientation,))
    key = orientation.strip().lower()
    if key not in REQUIRED_ORIENTATIONS:
        raise ValueError(
            "unrecognized loop orientation %r; recognized: %s"
            % (orientation, ", ".join(REQUIRED_ORIENTATIONS))
        )
    return key


def validate_window(window, where="window"):
    """Validate a (minimum, maximum) dimensional window."""
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("%s: window must be a (minimum, maximum) pair" % where)
    low = _number({"v": window[0]}, "v", "%s.minimum" % where)
    high = _number({"v": window[1]}, "v", "%s.maximum" % where)
    if low < 0.0:
        raise ValueError("%s: minimum must be >= 0, got %g" % (where, low))
    if high <= low:
        raise ValueError("%s: maximum %g must exceed minimum %g" % (where, high, low))
    return (low, high)


def grade_dimension(value, window, margin_fraction=DEFAULT_MARGIN_FRACTION):
    """Grade a dimension against its window as conforming, marginal or a deviation.

    A value outside the window is a deviation. A value inside it but within a
    margin band of either edge is marginal: worth carrying in the report, not
    worth rebuilding the bench over.
    """
    measured = _number({"v": value}, "v", "value")
    low, high = validate_window(window)
    fraction = _number({"v": margin_fraction}, "v", "margin_fraction")
    if fraction < 0.0 or fraction >= 0.5:
        raise ValueError("margin_fraction must be in [0, 0.5), got %g" % fraction)
    if not _at_least(measured, low) or not _at_most(measured, high):
        return {
            "grade": GRADE_DEVIATION,
            "value": measured,
            "window": (low, high),
            "edge_distance": min(abs(measured - low), abs(measured - high)),
        }
    band = (high - low) * fraction
    distance = min(measured - low, high - measured)
    grade = GRADE_MARGINAL if distance < band and not math.isclose(
        distance, band, rel_tol=LENGTH_REL_TOL, abs_tol=0.0
    ) else GRADE_CONFORMING
    return {
        "grade": grade,
        "value": measured,
        "window": (low, high),
        "edge_distance": distance,
    }


def grid_spacing_ceiling_m(loop_diameter_m=DEFAULT_LOOP_DIAMETER_M):
    """Widest step that still leaves no unswept strip between loop positions.

    Successive loop positions have to overlap, so the step cannot exceed the
    loop diameter; stepping wider leaves a lane of the surface never exposed.
    """
    diameter = _positive(
        _number({"v": loop_diameter_m}, "v", "loop_diameter_m"), "loop_diameter_m"
    )
    return diameter


def scan_point_count(width_m, height_m, spacing_m):
    """Loop positions needed to sweep a rectangular exposure surface."""
    width = _positive(_number({"v": width_m}, "v", "width_m"), "width_m")
    height = _positive(_number({"v": height_m}, "v", "height_m"), "height_m")
    spacing = _positive(_number({"v": spacing_m}, "v", "spacing_m"), "spacing_m")
    across = _ceil_units(width, spacing)
    down = _ceil_units(height, spacing)
    return {"across": across, "down": down, "positions": across * down}


def sense_loop_voltage_v(turns, area_m2, flux_density_t, frequency_hz):
    """Read-back a sense loop gives for a sinusoidal flux density.

    The loop integrates the rate of change of flux, so the amplitude scales
    with frequency as well as with the turns-area product.
    """
    count = _number({"v": turns}, "v", "turns")
    if count < 1.0:
        raise ValueError("turns must be >= 1, got %g" % count)
    area = _positive(_number({"v": area_m2}, "v", "area_m2"), "area_m2")
    flux = _positive(
        _number({"v": flux_density_t}, "v", "flux_density_t"), "flux_density_t"
    )
    frequency = _positive(
        _number({"v": frequency_hz}, "v", "frequency_hz"), "frequency_hz"
    )
    return 2.0 * math.pi * frequency * count * area * flux


def flux_density_for_sense_voltage(voltage_v, turns, area_m2, frequency_hz):
    """Flux density a sense-loop read-back corresponds to."""
    voltage = _positive(_number({"v": voltage_v}, "v", "voltage_v"), "voltage_v")
    unit = sense_loop_voltage_v(turns, area_m2, 1.0, frequency_hz)
    return voltage / unit


def validate_position(record, standoff_window=DEFAULT_STANDOFF_WINDOW_M):
    """Validate one exposure position record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("position: record must be a mapping")
    surface = normalize_surface(record.get("surface"))
    where = "position[%s]" % surface
    width = _positive(_number(record, "width_m", where), "%s.width_m" % where)
    height = _positive(_number(record, "height_m", where), "%s.height_m" % where)
    standoff = _number(record, "standoff_m", where)
    if standoff < 0.0:
        raise ValueError("%s: standoff_m must be >= 0, got %g" % (where, standoff))
    spacing = _positive(
        _number(record, "grid_spacing_m", where), "%s.grid_spacing_m" % where
    )
    raw = record.get("orientations")
    if not isinstance(raw, (list, tuple)) or len(raw) == 0:
        raise ValueError("%s: orientations must be a non-empty list" % where)
    seen = []
    for orientation in raw:
        key = normalize_orientation(orientation)
        if key in seen:
            raise ValueError(
                "%s: orientation %r presented twice; each is presented once"
                % (where, key)
            )
        seen.append(key)
    return {
        "surface": surface,
        "width_m": width,
        "height_m": height,
        "standoff_m": standoff,
        "grid_spacing_m": spacing,
        "orientations": seen,
        "missing_orientations": [
            o for o in REQUIRED_ORIENTATIONS if o not in seen
        ],
        "standoff_grade": grade_dimension(standoff, standoff_window),
    }


def assess_setup(
    positions,
    loop_diameter_m=DEFAULT_LOOP_DIAMETER_M,
    standoff_window_m=DEFAULT_STANDOFF_WINDOW_M,
    verification=None,
    monitor_floor_v=DEFAULT_MONITOR_FLOOR_V,
):
    """Full clause 5.4.10.3 conformance assessment of the exposure arrangement.

    ``verification`` describes the sense-loop arrangement that proves the field
    before the sweep: turns, area_m2, flux_density_t and frequency_hz.
    """
    if not isinstance(positions, (list, tuple)) or len(positions) == 0:
        raise ValueError("positions: at least one exposure position is required")
    window = validate_window(standoff_window_m, "standoff_window_m")
    diameter = _positive(
        _number({"v": loop_diameter_m}, "v", "loop_diameter_m"), "loop_diameter_m"
    )
    floor = _positive(
        _number({"v": monitor_floor_v}, "v", "monitor_floor_v"), "monitor_floor_v"
    )
    ceiling = grid_spacing_ceiling_m(diameter)

    findings = []
    limitations = []
    graded = []
    seen = []
    total_positions = 0
    for record in positions:
        item = validate_position(record, window)
        if item["surface"] in seen:
            raise ValueError(
                "positions: surface %r appears twice; merge the two runs first"
                % item["surface"]
            )
        seen.append(item["surface"])

        standoff = item["standoff_grade"]
        if standoff["grade"] == GRADE_DEVIATION:
            findings.append(
                "loop standoff %g m on the %s is outside the %g-%g m window"
                % (standoff["value"], item["surface"], window[0], window[1])
            )
        elif standoff["grade"] == GRADE_MARGINAL:
            limitations.append(
                "loop standoff %g m on the %s sits %g m from a window edge"
                % (standoff["value"], item["surface"], standoff["edge_distance"])
            )

        if not _at_most(item["grid_spacing_m"], ceiling):
            findings.append(
                "grid spacing %g m on the %s exceeds the %g m loop overlap ceiling"
                % (item["grid_spacing_m"], item["surface"], ceiling)
            )

        for orientation in item["missing_orientations"]:
            findings.append(
                "loop presentation %s never made on the %s"
                % (orientation, item["surface"])
            )

        grid = scan_point_count(
            item["width_m"], item["height_m"], item["grid_spacing_m"]
        )
        item["grid"] = grid
        item["exposures"] = grid["positions"] * len(item["orientations"])
        total_positions += item["exposures"]
        graded.append(item)

    verification_report = None
    if verification is not None:
        if not isinstance(verification, dict):
            raise ValueError("verification: must be a mapping")
        turns = _number(verification, "turns", "verification")
        area = _number(verification, "area_m2", "verification")
        flux = _number(verification, "flux_density_t", "verification")
        frequency = _number(verification, "frequency_hz", "verification")
        voltage = sense_loop_voltage_v(turns, area, flux, frequency)
        resolvable = _at_least(voltage, floor)
        verification_report = {
            "sense_voltage_v": voltage,
            "monitor_floor_v": floor,
            "resolvable": resolvable,
        }
        if not resolvable:
            findings.append(
                "sense-loop read-back %.3e V is under the %.3e V monitor floor"
                % (voltage, floor)
            )
        elif voltage < floor * 10.0:
            limitations.append(
                "sense-loop read-back %.3e V is within a decade of the monitor floor"
                % voltage
            )
    else:
        findings.append("no system verification arrangement described")

    return {
        "surfaces": seen,
        "positions": graded,
        "grid_spacing_ceiling_m": ceiling,
        "total_exposures": total_positions,
        "verification": verification_report,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_CONFORMS if not findings else VERDICT_DEVIATES,
    }
