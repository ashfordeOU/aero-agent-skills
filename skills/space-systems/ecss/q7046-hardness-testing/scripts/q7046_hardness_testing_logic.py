#!/usr/bin/env python3
"""Hardness acceptance for a lot of threaded fasteners.

Anchor: ECSS-Q-ST-70-46 testing clause on threaded fasteners. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

A property class allows a band of hardness with a floor and a ceiling.
Too soft means the heat treatment fell short of the strength the class
promises; too hard means low ductility and, on a plated fastener, a
raised susceptibility to delayed failure under sustained load.

Readings only compare on one scale. Vickers is the reference scale
here; a Rockwell C or Brinell reading is brought onto it by linear
interpolation of a tabulated curve, and a reading outside the span of
that curve is refused rather than extrapolated.

An indentation is only a measurement if the section under it could
contain it. The Vickers diagonal follows from the applied load and the
hardness itself,

    d = sqrt(1.8544 * F / HV)

so the minimum usable section is a function of both, not a constant.

Surface and core are two results. Their difference names carbon loss
during heat treatment or carbon pick-up, which neither number shows on
its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

#: Relative slack on a comparison whose two sides are both computed.
HARDNESS_REL_TOL = 1e-9

SCALE_HV = "HV"
SCALE_HRC = "HRC"
SCALE_HB = "HB"
SCALES = (SCALE_HV, SCALE_HRC, SCALE_HB)

#: Vickers constant relating load in kgf and diagonal in mm.
VICKERS_CONSTANT = 1.8544

#: Section must contain the indentation with this margin on the diagonal.
SECTION_DIAGONAL_FACTOR = 1.5

#: Vickers spread across one lot beyond which the furnace load is suspect.
SPREAD_ALLOWANCE_HV = 40.0

#: Surface may differ from core by at most this much before it is a fault.
SURFACE_DELTA_LIMIT_HV = 30.0

MIN_READINGS = 3

SURFACE_OK = "surface-matches-core"
SURFACE_CARBON_LOSS = "surface-carbon-loss"
SURFACE_CARBON_PICKUP = "surface-carbon-pickup"

VERDICT_ACCEPT = "hardness-accepted"
VERDICT_OUT_OF_BAND = "hardness-out-of-band"
VERDICT_SURFACE_FAULT = "surface-condition-fault"
VERDICT_METHOD_INVALID = "measurement-method-invalid"

#: Hardness band per property class, on the Vickers reference scale.
_CLASS_BANDS_HV = {
    "8.8": (250.0, 320.0),
    "10.9": (320.0, 380.0),
    "12.9": (385.0, 435.0),
    "A2-70": (210.0, 320.0),
    "A4-80": (240.0, 350.0),
}

PROPERTY_CLASSES = tuple(sorted(_CLASS_BANDS_HV))

#: Tabulated Vickers-to-Rockwell-C curve for hardened steel, ascending.
_HV_HRC_CURVE = (
    (240.0, 20.3),
    (250.0, 22.2),
    (270.0, 25.6),
    (290.0, 28.5),
    (310.0, 31.0),
    (320.0, 32.2),
    (340.0, 34.4),
    (360.0, 36.6),
    (380.0, 38.8),
    (400.0, 40.8),
    (420.0, 42.7),
    (440.0, 44.5),
    (460.0, 46.1),
    (480.0, 47.7),
    (500.0, 49.1),
)

#: Brinell tracks Vickers closely below the ball-flattening ceiling.
_HB_PER_HV = 0.95
HB_VALID_CEILING_HV = 450.0

#: Loads each scale supports, in kgf, and the bare minimum section.
_SCALE_RULES = {
    SCALE_HV: {"loads": (1.0, 5.0, 10.0, 30.0), "min_section_mm": 0.5},
    SCALE_HRC: {"loads": (150.0,), "min_section_mm": 1.0},
    SCALE_HB: {"loads": (187.5, 3000.0), "min_section_mm": 2.0},
}


def _require_positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be finite and positive, got %r" % (name, value))
    return float(value)


def _require_scale(scale):
    if scale not in SCALES:
        raise ValueError(
            "scale must be one of %s, got %r" % (", ".join(SCALES), scale)
        )
    return scale


def _at_least(value, bound, rel_tol=HARDNESS_REL_TOL):
    return value >= bound - abs(bound) * rel_tol


def _at_most(value, bound, rel_tol=HARDNESS_REL_TOL):
    return value <= bound + abs(bound) * rel_tol


def _interpolate(curve, value, index_from, index_to):
    low = curve[0][index_from]
    high = curve[-1][index_from]
    if value < low or value > high:
        raise ValueError(
            "%.2f is outside the tabulated curve span %.2f..%.2f; the curve "
            "is interpolated, never extended" % (value, low, high)
        )
    for first, second in zip(curve, curve[1:]):
        a, b = first[index_from], second[index_from]
        if a <= value <= b:
            if b == a:
                return first[index_to]
            fraction = (value - a) / (b - a)
            return first[index_to] + fraction * (second[index_to] - first[index_to])
    raise ValueError("%.2f could not be placed on the curve" % value)


def hv_to_hrc(hv):
    """Rockwell C equivalent of a Vickers reading, by interpolation."""
    value = _require_positive("hv", hv)
    return _interpolate(_HV_HRC_CURVE, value, 0, 1)


def hrc_to_hv(hrc):
    """Vickers equivalent of a Rockwell C reading, by interpolation."""
    value = _require_positive("hrc", hrc)
    return _interpolate(_HV_HRC_CURVE, value, 1, 0)


def hb_to_hv(hb):
    """Vickers equivalent of a Brinell reading."""
    value = _require_positive("hb", hb)
    return value / _HB_PER_HV


def hv_to_hb(hv):
    """Brinell equivalent of a Vickers reading, below the ball ceiling."""
    value = _require_positive("hv", hv)
    if value > HB_VALID_CEILING_HV:
        raise ValueError(
            "%.1f HV is above the %.1f HV ceiling where the Brinell ball "
            "flattens; a Brinell reading is not a valid measurement there"
            % (value, HB_VALID_CEILING_HV)
        )
    return value * _HB_PER_HV


def to_vickers(reading, scale):
    """Bring a reading on any supported scale onto the Vickers axis."""
    _require_scale(scale)
    if scale == SCALE_HV:
        return _require_positive("reading", reading)
    if scale == SCALE_HRC:
        return hrc_to_hv(reading)
    return hb_to_hv(reading)


def hardness_band(property_class, scale=SCALE_HV):
    """Floor and ceiling of the class band, on the requested scale."""
    if property_class not in _CLASS_BANDS_HV:
        raise ValueError(
            "property_class must be one of %s, got %r"
            % (", ".join(PROPERTY_CLASSES), property_class)
        )
    _require_scale(scale)
    floor_hv, ceiling_hv = _CLASS_BANDS_HV[property_class]
    if scale == SCALE_HV:
        return {"scale": scale, "floor": floor_hv, "ceiling": ceiling_hv}
    if scale == SCALE_HRC:
        return {
            "scale": scale,
            "floor": hv_to_hrc(floor_hv),
            "ceiling": hv_to_hrc(ceiling_hv),
        }
    return {
        "scale": scale,
        "floor": hv_to_hb(floor_hv),
        "ceiling": hv_to_hb(ceiling_hv),
    }


def vickers_diagonal_mm(test_load_kgf, hardness_hv):
    """Indentation diagonal a Vickers test leaves, in mm."""
    load = _require_positive("test_load_kgf", test_load_kgf)
    hardness = _require_positive("hardness_hv", hardness_hv)
    return math.sqrt(VICKERS_CONSTANT * load / hardness)


def method_validity(scale, section_thickness_mm, test_load_kgf, hardness_hv):
    """Whether the load, section and scale support the reading taken."""
    _require_scale(scale)
    thickness = _require_positive("section_thickness_mm", section_thickness_mm)
    load = _require_positive("test_load_kgf", test_load_kgf)
    hardness = _require_positive("hardness_hv", hardness_hv)
    rules = _SCALE_RULES[scale]
    findings = []
    if load not in rules["loads"]:
        findings.append(
            "%.1f kgf is not a load the %s scale supports (%s)"
            % (load, scale, ", ".join("%.1f" % v for v in rules["loads"]))
        )
    required = rules["min_section_mm"]
    if scale == SCALE_HV:
        diagonal = vickers_diagonal_mm(load, hardness)
        required = max(required, SECTION_DIAGONAL_FACTOR * diagonal)
    if not _at_least(thickness, required):
        findings.append(
            "section of %.3f mm cannot contain the indentation; %.3f mm is "
            "needed at this load and hardness" % (thickness, required)
        )
    if scale == SCALE_HB and hardness > HB_VALID_CEILING_HV:
        findings.append(
            "%.1f HV is above the Brinell ball-flattening ceiling of %.1f HV"
            % (hardness, HB_VALID_CEILING_HV)
        )
    return {
        "scale": scale,
        "valid": not findings,
        "required_section_mm": required,
        "findings": findings,
    }


def evaluate_readings(readings, property_class, scale=SCALE_HV):
    """Convert a reading set, compare with the band, measure the spread."""
    if isinstance(readings, (str, dict)) or not isinstance(readings, (list, tuple)):
        raise ValueError(
            "readings must be a sequence of numbers, got %r" % (readings,)
        )
    if len(readings) < MIN_READINGS:
        raise ValueError(
            "%d reading(s) given; a lot result needs at least %d"
            % (len(readings), MIN_READINGS)
        )
    converted = [to_vickers(value, scale) for value in readings]
    band = hardness_band(property_class, SCALE_HV)
    lowest = min(converted)
    highest = max(converted)
    spread = highest - lowest
    findings = []
    below = [v for v in converted if not _at_least(v, band["floor"])]
    above = [v for v in converted if not _at_most(v, band["ceiling"])]
    if below:
        findings.append(
            "%d reading(s) below the %.1f HV floor of class %s, lowest %.1f HV"
            % (len(below), band["floor"], property_class, lowest)
        )
    if above:
        findings.append(
            "%d reading(s) above the %.1f HV ceiling of class %s, highest "
            "%.1f HV" % (len(above), band["ceiling"], property_class, highest)
        )
    if not _at_most(spread, SPREAD_ALLOWANCE_HV):
        findings.append(
            "spread of %.1f HV across the lot exceeds the %.1f HV allowance; "
            "the furnace load was not uniform"
            % (spread, SPREAD_ALLOWANCE_HV)
        )
    return {
        "property_class": property_class,
        "readings_hv": converted,
        "lowest_hv": lowest,
        "highest_hv": highest,
        "mean_hv": sum(converted) / len(converted),
        "spread_hv": spread,
        "band": band,
        "in_band": not (below or above),
        "findings": findings,
    }


def surface_versus_core(core_hv, surface_hv, limit_hv=SURFACE_DELTA_LIMIT_HV):
    """Name a decarburized or carbon-enriched surface from the difference."""
    core = _require_positive("core_hv", core_hv)
    surface = _require_positive("surface_hv", surface_hv)
    limit = _require_positive("limit_hv", limit_hv)
    delta = surface - core
    if not _at_most(abs(delta), limit):
        state = SURFACE_CARBON_PICKUP if delta > 0.0 else SURFACE_CARBON_LOSS
        note = (
            "surface %.1f HV against a core of %.1f HV, a difference of "
            "%.1f HV beyond the %.1f HV allowance (%s)"
            % (surface, core, delta, limit, state.replace("-", " "))
        )
        return {"state": state, "delta_hv": delta, "findings": [note]}
    return {"state": SURFACE_OK, "delta_hv": delta, "findings": []}


def assess_hardness(case):
    """Band, method and surface condition rolled up to one lot verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    scale = _require_scale(case.get("scale", SCALE_HV))
    property_class = case.get("property_class")
    reading_set = evaluate_readings(
        case.get("readings"), property_class, scale
    )
    findings = list(reading_set["findings"])

    method = None
    if "section_thickness_mm" in case or "test_load_kgf" in case:
        method = method_validity(
            scale,
            case.get("section_thickness_mm"),
            case.get("test_load_kgf"),
            reading_set["mean_hv"],
        )
        findings.extend(method["findings"])

    surface = None
    if case.get("surface_hv") is not None:
        surface = surface_versus_core(
            case.get("core_hv", reading_set["mean_hv"]),
            case["surface_hv"],
            case.get("surface_limit_hv", SURFACE_DELTA_LIMIT_HV),
        )
        findings.extend(surface["findings"])

    if method is not None and not method["valid"]:
        verdict = VERDICT_METHOD_INVALID
    elif not reading_set["in_band"]:
        verdict = VERDICT_OUT_OF_BAND
    elif surface is not None and surface["state"] != SURFACE_OK:
        verdict = VERDICT_SURFACE_FAULT
    else:
        verdict = VERDICT_ACCEPT

    return {
        "scale": scale,
        "property_class": property_class,
        "readings": reading_set,
        "method": method,
        "surface": surface,
        "findings": findings,
        "verdict": verdict,
    }
