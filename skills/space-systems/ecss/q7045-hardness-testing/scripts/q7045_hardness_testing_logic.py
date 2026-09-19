"""Hardness testing of metallic materials and conversion between scales.

Anchor: ECSS-Q-ST-70-45, methods clause -- hardness is taken by pressing a
ball or a diamond into a prepared surface under a defined force and reading
the indentation, on the Brinell, Vickers or Rockwell scale as the product
requires. Paraphrased into an implementable procedure; no standard text is
reproduced.

What this module decides
------------------------
Whether an indentation is a valid reading, what hardness it corresponds to,
and whether that reading may be carried onto another scale.

1. An indentation has to be the right size. Too small and the reading sits on
   a few grains; too large and the ball is bottoming into the bulk. The
   diameter ratio band is what separates a reading from a dent.
2. The force and the ball go together. The load index ties them, and a force
   that does not pair with its ball puts the reading on a different curve
   from every other reading in the report.
3. An indentation needs room. Too close to its neighbour or to an edge, it
   relaxes into already worked metal and reads low.
4. Conversion is interpolation inside a table, never beyond it. Outside the
   tabulated range, and on a scale the table does not carry at that level,
   there is no conversion to report.
"""

import math

__all__ = [
    "SCALES",
    "BRINELL_RATIO_BAND",
    "STANDARD_LOAD_INDICES",
    "SPACING_FACTOR",
    "EDGE_FACTOR",
    "DIAGONAL_ASYMMETRY_LIMIT",
    "CONVERSION_TABLE",
    "brinell_hardness",
    "brinell_load_index",
    "vickers_hardness",
    "rockwell_c_from_depth",
    "indentation_spacing_findings",
    "convert_hardness",
    "assess_hardness_test",
]

# The scales this module reads and converts between.
SCALES = ("HBW", "HV", "HRC")

# Indentation diameter as a fraction of the ball diameter.
BRINELL_RATIO_BAND = (0.24, 0.60)

# Force and ball pair through the load index 0.102 F / D^2.
STANDARD_LOAD_INDICES = (30.0, 10.0, 5.0, 2.5, 1.0)

# An index this far from a standard one is not a standard pairing.
LOAD_INDEX_TOLERANCE = 0.01

# Room an indentation needs, as multiples of its own size.
SPACING_FACTOR = 3.0
EDGE_FACTOR = 2.5

# A Vickers impression whose diagonals differ by more than this was not
# pressed into a flat, normal surface.
DIAGONAL_ASYMMETRY_LIMIT = 0.05

# Conversion table rows: (HV, HBW, HRC). A None means the scale carries no
# tabulated value at that level and no conversion may be reported there.
CONVERSION_TABLE = (
    (150.0, 143.0, None),
    (200.0, 190.0, None),
    (250.0, 238.0, 22.2),
    (300.0, 285.0, 29.8),
    (350.0, 333.0, 35.5),
    (400.0, 380.0, 40.8),
    (450.0, 428.0, 45.3),
    (500.0, 475.0, 49.1),
)

_COLUMN = {"HV": 0, "HBW": 1, "HRC": 2}

# Comparisons at a band edge are inclusive; absorb representation error there.
REL_TOLERANCE = 1e-9


def _as_finite_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_finite_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _slack(reference):
    return REL_TOLERANCE * max(abs(reference), 1.0)


def brinell_hardness(force_n, ball_diameter_mm, indent_diameter_mm):
    """Return the Brinell number from the ball, the force and the impression."""
    force = _as_positive_float(force_n, "force_n")
    ball = _as_positive_float(ball_diameter_mm, "ball_diameter_mm")
    indent = _as_positive_float(indent_diameter_mm, "indent_diameter_mm")
    if indent >= ball:
        raise ValueError(
            "impression %g mm is not smaller than the ball %g mm" % (indent, ball)
        )
    cap = ball - math.sqrt(ball * ball - indent * indent)
    return 0.102 * 2.0 * force / (math.pi * ball * cap)


def brinell_load_index(force_n, ball_diameter_mm):
    """Return the load index that pairs a force with a ball diameter."""
    force = _as_positive_float(force_n, "force_n")
    ball = _as_positive_float(ball_diameter_mm, "ball_diameter_mm")
    return 0.102 * force / (ball * ball)


def vickers_hardness(force_n, diagonal_mm):
    """Return the Vickers number from the force and the mean diagonal."""
    force = _as_positive_float(force_n, "force_n")
    diagonal = _as_positive_float(diagonal_mm, "diagonal_mm")
    return 0.1891 * force / (diagonal * diagonal)


def rockwell_c_from_depth(permanent_depth_mm):
    """Return the Rockwell C number from the permanent indentation depth."""
    depth = _as_positive_float(permanent_depth_mm, "permanent_depth_mm")
    value = 100.0 - depth / 0.002
    if value <= 0.0:
        raise ValueError(
            "permanent depth %g mm is deeper than the Rockwell C range" % depth
        )
    return value


def indentation_spacing_findings(indent_size_mm, spacing_mm=None, edge_distance_mm=None):
    """Return findings for an impression that was pressed too close to something."""
    size = _as_positive_float(indent_size_mm, "indent_size_mm")
    findings = []
    if spacing_mm is not None:
        spacing = _as_positive_float(spacing_mm, "spacing_mm")
        needed = SPACING_FACTOR * size
        if spacing < needed - _slack(needed):
            findings.append(
                "centre spacing %.4f mm is below the %.1f x impression minimum "
                "of %.4f mm" % (spacing, SPACING_FACTOR, needed)
            )
    if edge_distance_mm is not None:
        edge = _as_positive_float(edge_distance_mm, "edge_distance_mm")
        needed = EDGE_FACTOR * size
        if edge < needed - _slack(needed):
            findings.append(
                "edge distance %.4f mm is below the %.1f x impression minimum "
                "of %.4f mm" % (edge, EDGE_FACTOR, needed)
            )
    return findings


def convert_hardness(value, from_scale, to_scale):
    """Return a hardness carried onto another scale by table interpolation.

    Interpolation happens inside the tabulated range only. A value outside it,
    or a level where the target scale carries no tabulated entry, has no
    conversion and raises rather than returning an invented one.
    """
    if from_scale not in _COLUMN:
        raise ValueError("'%s' is not a covered scale" % (from_scale,))
    if to_scale not in _COLUMN:
        raise ValueError("'%s' is not a covered scale" % (to_scale,))
    number = _as_positive_float(value, "value")
    source = _COLUMN[from_scale]
    target = _COLUMN[to_scale]
    if from_scale == to_scale:
        return number
    rows = [row for row in CONVERSION_TABLE if row[source] is not None]
    lowest = rows[0][source]
    highest = rows[-1][source]
    if number < lowest - _slack(lowest) or number > highest + _slack(highest):
        raise ValueError(
            "%.4f %s is outside the tabulated range %.4f to %.4f; no conversion "
            "is defined there" % (number, from_scale, lowest, highest)
        )
    for row in rows:
        if abs(row[source] - number) <= _slack(row[source]):
            if row[target] is None:
                raise ValueError(
                    "the table carries no %s value at %.4f %s"
                    % (to_scale, number, from_scale)
                )
            return float(row[target])
    for i in range(1, len(rows)):
        low = rows[i - 1]
        high = rows[i]
        if low[source] < number < high[source]:
            if low[target] is None or high[target] is None:
                raise ValueError(
                    "the table carries no %s value bracketing %.4f %s"
                    % (to_scale, number, from_scale)
                )
            fraction = (number - low[source]) / (high[source] - low[source])
            return low[target] + fraction * (high[target] - low[target])
    raise ValueError("no tabulated bracket found for %.4f %s" % (number, from_scale))


def _assess_brinell(spec):
    force = _as_positive_float(spec["force_n"], "force_n")
    ball = _as_positive_float(spec["ball_diameter_mm"], "ball_diameter_mm")
    indent = _as_positive_float(spec["indent_diameter_mm"], "indent_diameter_mm")
    value = brinell_hardness(force, ball, indent)
    index = brinell_load_index(force, ball)
    ratio = indent / ball
    findings = []
    low, high = BRINELL_RATIO_BAND
    if ratio < low - _slack(low) or ratio > high + _slack(high):
        findings.append(
            "impression to ball ratio %.4f is outside the band %.2f to %.2f"
            % (ratio, low, high)
        )
    nearest = min(STANDARD_LOAD_INDICES, key=lambda s: abs(s - index))
    if abs(nearest - index) > LOAD_INDEX_TOLERANCE * nearest:
        findings.append(
            "load index %.4f pairs with no standard force and ball combination"
            % index
        )
    findings.extend(
        indentation_spacing_findings(
            indent, spec.get("spacing_mm"), spec.get("edge_distance_mm")
        )
    )
    return {
        "value": value,
        "diameter_ratio": ratio,
        "load_index": index,
        "nearest_load_index": nearest,
        "findings": findings,
    }


def _assess_vickers(spec):
    force = _as_positive_float(spec["force_n"], "force_n")
    diagonals = spec["diagonals_mm"]
    if not isinstance(diagonals, (list, tuple)) or len(diagonals) != 2:
        raise ValueError("diagonals_mm must be a pair of measured diagonals")
    first = _as_positive_float(diagonals[0], "first diagonal")
    second = _as_positive_float(diagonals[1], "second diagonal")
    mean = (first + second) / 2.0
    value = vickers_hardness(force, mean)
    asymmetry = abs(first - second) / mean
    findings = []
    if asymmetry > DIAGONAL_ASYMMETRY_LIMIT + _slack(DIAGONAL_ASYMMETRY_LIMIT):
        findings.append(
            "diagonals differ by %.2f%% of their mean, above the %.2f%% limit; "
            "the surface was not flat and normal to the indenter"
            % (asymmetry * 100.0, DIAGONAL_ASYMMETRY_LIMIT * 100.0)
        )
    findings.extend(
        indentation_spacing_findings(
            mean, spec.get("spacing_mm"), spec.get("edge_distance_mm")
        )
    )
    return {
        "value": value,
        "mean_diagonal_mm": mean,
        "diagonal_asymmetry": asymmetry,
        "findings": findings,
    }


def _assess_rockwell(spec):
    value = rockwell_c_from_depth(spec["permanent_depth_mm"])
    findings = []
    if value < 20.0:
        findings.append(
            "Rockwell C of %.2f is below the usable part of the scale; take the "
            "reading on a lower-force scale instead" % value
        )
    return {
        "value": value,
        "permanent_depth_mm": _as_positive_float(
            spec["permanent_depth_mm"], "permanent_depth_mm"
        ),
        "findings": findings,
    }


_REQUIRED = {
    "HBW": ("force_n", "ball_diameter_mm", "indent_diameter_mm"),
    "HV": ("force_n", "diagonals_mm"),
    "HRC": ("permanent_depth_mm",),
}


def assess_hardness_test(spec):
    """Read one indentation, validate it and carry it onto a reporting scale.

    spec keys: scale (one of SCALES) plus that scale's measurements; optional
    spacing_mm, edge_distance_mm, report_scale and an acceptance (low, high)
    band expressed on the measured scale.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "scale" not in spec:
        raise ValueError("spec missing required key 'scale'")
    scale = spec["scale"]
    if scale not in SCALES:
        raise ValueError("'%s' is not a covered scale" % (scale,))
    for key in _REQUIRED[scale]:
        if key not in spec:
            raise ValueError("a %s reading needs '%s'" % (scale, key))
    if scale == "HBW":
        detail = _assess_brinell(spec)
    elif scale == "HV":
        detail = _assess_vickers(spec)
    else:
        detail = _assess_rockwell(spec)

    findings = list(detail["findings"])
    converted = None
    report_scale = spec.get("report_scale")
    if report_scale is not None:
        try:
            converted = convert_hardness(detail["value"], scale, report_scale)
        except ValueError as problem:
            findings.append("conversion refused: %s" % problem)

    band = spec.get("acceptance_band")
    if band is not None:
        if not isinstance(band, (list, tuple)) or len(band) != 2:
            raise ValueError("acceptance_band must be a (low, high) pair")
        low = _as_finite_float(band[0], "acceptance_band low")
        high = _as_finite_float(band[1], "acceptance_band high")
        if low > high:
            raise ValueError("acceptance_band low %g exceeds high %g" % (low, high))
        if detail["value"] < low - _slack(low) or detail["value"] > high + _slack(high):
            findings.append(
                "reading %.4f %s is outside the acceptance band %.4f to %.4f"
                % (detail["value"], scale, low, high)
            )

    result = {
        "scale": scale,
        "hardness": detail["value"],
        "report_scale": report_scale,
        "converted_hardness": converted,
        "findings": findings,
        "reading_accepted": not findings,
    }
    for key, value in detail.items():
        if key not in ("findings", "value"):
            result[key] = value
    return result
