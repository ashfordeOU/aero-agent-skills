#!/usr/bin/env python3
"""Radiated magnetic susceptibility equipment, ECSS-E-ST-20-07C 5.4.10.2.

Paraphrased procedure, no verbatim standard text. The clause names what the
magnetic exposure field is generated with: a signal source, a power amplifier
driving it, and a radiating loop of stated diameter and turn count. This
module turns that list into a deterministic readiness decision:

  instrument records -> role normalization and validation
  role coverages     -> intersection with the required exposure band
  loop geometry      -> turns-area product and on-axis flux density
  wanted flux level  -> loop current, drive level and the gain needed

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Frequency comparison tolerance. Band edges are differences and ratios of
# float frequencies, so an exactly-met edge can land a few units in the last
# place short. The tolerance absorbs representation error only.
FREQ_REL_TOL = 1e-12

# Decibel comparison tolerance, same reasoning on the level side.
DB_TOL = 1e-9

# Permeability of free space, henry per metre.
MU0 = 4.0e-7 * math.pi

# Required radiated magnetic susceptibility exposure band, hertz.
DEFAULT_BAND_HZ = (30.0, 100.0e3)

# Nominal radiating loop as the clause dimensions it: diameter in metres and
# the number of turns wound on it.
DEFAULT_LOOP_DIAMETER_M = 0.12
DEFAULT_LOOP_TURNS = 20.0

# Nominal standoff from the loop plane to the exposed surface, metres.
DEFAULT_STANDOFF_M = 0.05

ROLE_SOURCE = "signal-source"
ROLE_AMPLIFIER = "power-amplifier"
ROLE_LOOP = "radiating-loop"
REQUIRED_ROLES = (ROLE_SOURCE, ROLE_AMPLIFIER, ROLE_LOOP)

VERDICT_READY = "equipment-ready"
VERDICT_INCOMPLETE = "equipment-incomplete"


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


def normalize_role(role):
    """Return the recognized equipment role for a raw role designation."""
    if not isinstance(role, str):
        raise ValueError("equipment role must be a string, got %r" % (role,))
    key = role.strip().lower()
    if key not in REQUIRED_ROLES:
        raise ValueError(
            "unrecognized equipment role %r; recognized: %s"
            % (role, ", ".join(REQUIRED_ROLES))
        )
    return key


def validate_band(band, where="band"):
    """Validate a (low, high) frequency band and return it as floats."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s: band must be a (low_hz, high_hz) pair" % where)
    low = _number({"v": band[0]}, "v", "%s.low_hz" % where)
    high = _number({"v": band[1]}, "v", "%s.high_hz" % where)
    if low <= 0.0:
        raise ValueError("%s: low_hz must be > 0, got %g" % (where, low))
    if high <= low:
        raise ValueError("%s: high_hz %g must exceed low_hz %g" % (where, high, low))
    return (low, high)


def validate_equipment(record):
    """Validate one equipment record and return a normalized copy.

    Every record carries role, frequency_min_hz, frequency_max_hz and
    calibration_days_remaining. A signal-source and a power-amplifier add
    max_output_dbm, the amplifier also gain_db; a radiating-loop adds
    diameter_m, turns, dc_resistance_ohm and inductance_h.
    """
    if not isinstance(record, dict):
        raise ValueError("equipment: record must be a mapping")
    role = normalize_role(record.get("role"))
    where = "equipment[%s]" % role
    band = validate_band(
        (_number(record, "frequency_min_hz", where),
         _number(record, "frequency_max_hz", where)),
        where,
    )
    days = _number(record, "calibration_days_remaining", where)
    out = {
        "role": role,
        "frequency_min_hz": band[0],
        "frequency_max_hz": band[1],
        "calibration_days_remaining": days,
        "calibration_current": days > 0.0,
    }
    if role in (ROLE_SOURCE, ROLE_AMPLIFIER):
        out["max_output_dbm"] = _number(record, "max_output_dbm", where)
    if role == ROLE_AMPLIFIER:
        gain = _number(record, "gain_db", where)
        if gain <= 0.0:
            raise ValueError("%s: gain_db must be > 0, got %g" % (where, gain))
        out["gain_db"] = gain
    if role == ROLE_LOOP:
        out["diameter_m"] = _positive(
            _number(record, "diameter_m", where), "%s.diameter_m" % where
        )
        turns = _number(record, "turns", where)
        if turns < 1.0:
            raise ValueError("%s: turns must be >= 1, got %g" % (where, turns))
        if abs(turns - round(turns)) > 1e-9:
            raise ValueError("%s: turns must be a whole number, got %g" % (where, turns))
        out["turns"] = float(round(turns))
        out["dc_resistance_ohm"] = _positive(
            _number(record, "dc_resistance_ohm", where), "%s.dc_resistance_ohm" % where
        )
        out["inductance_h"] = _positive(
            _number(record, "inductance_h", where), "%s.inductance_h" % where
        )
        out["rated_current_a"] = _positive(
            _number(record, "rated_current_a", where), "%s.rated_current_a" % where
        )
    return out


def band_overlap(first, second):
    """Return the overlapping band of two bands, or None when disjoint."""
    low_a, high_a = validate_band(first, "band_a")
    low_b, high_b = validate_band(second, "band_b")
    low = max(low_a, low_b)
    high = min(high_a, high_b)
    if high <= low:
        return None
    return (low, high)


def band_decades(band):
    """Width of a band expressed in frequency decades."""
    low, high = validate_band(band)
    return math.log10(high) - math.log10(low)


def uncovered_sub_bands(band, coverage):
    """Sub-bands of the required band left outside the equipment coverage."""
    low, high = validate_band(band)
    if coverage is None:
        return [(low, high)]
    cov_low, cov_high = validate_band(coverage, "coverage")
    gaps = []
    if cov_low > low and not math.isclose(
        cov_low, low, rel_tol=FREQ_REL_TOL, abs_tol=0.0
    ):
        gaps.append((low, min(cov_low, high)))
    if cov_high < high and not math.isclose(
        cov_high, high, rel_tol=FREQ_REL_TOL, abs_tol=0.0
    ):
        gaps.append((max(cov_high, low), high))
    return gaps


def chain_coverage(equipment, band=DEFAULT_BAND_HZ):
    """Intersect every equipment coverage with the required exposure band."""
    required = validate_band(band, "required_band")
    if not isinstance(equipment, (list, tuple)) or len(equipment) == 0:
        raise ValueError("chain_coverage: at least one equipment record is required")
    coverage = required
    for record in equipment:
        item = record if "role" in record and "calibration_current" in record \
            else validate_equipment(record)
        if coverage is None:
            break
        coverage = band_overlap(
            coverage, (item["frequency_min_hz"], item["frequency_max_hz"])
        )
    gaps = uncovered_sub_bands(required, coverage)
    covered = 0.0 if coverage is None else band_decades(coverage)
    return {
        "required_band_hz": required,
        "coverage_hz": coverage,
        "gaps_hz": gaps,
        "required_decades": band_decades(required),
        "covered_decades": covered,
    }


def limiting_equipment(equipment, band=DEFAULT_BAND_HZ):
    """Name the item that removes the most decades from the exposure band.

    Ties resolve to the role order the clause lists the chain in, so the
    result is stable for identical coverages.
    """
    required = validate_band(band, "required_band")
    normalized = [
        record if "role" in record and "calibration_current" in record
        else validate_equipment(record)
        for record in equipment
    ]
    if len(normalized) == 0:
        raise ValueError("limiting_equipment: at least one record is required")
    best = None
    for record in normalized:
        overlap = band_overlap(
            required, (record["frequency_min_hz"], record["frequency_max_hz"])
        )
        lost = band_decades(required) - (
            0.0 if overlap is None else band_decades(overlap)
        )
        order = REQUIRED_ROLES.index(record["role"])
        key = (-lost, order)
        if best is None or key < best[0]:
            best = (key, record["role"], lost)
    return {"role": best[1], "lost_decades": best[2]}


def loop_turns_area_m2(diameter_m=DEFAULT_LOOP_DIAMETER_M, turns=DEFAULT_LOOP_TURNS):
    """Turns-area product of the radiating loop, square metres.

    The loop couples through the product of its turn count and the area each
    turn encloses, so diameter and turns are one figure, not two.
    """
    diameter = _positive(_number({"v": diameter_m}, "v", "diameter_m"), "diameter_m")
    count = _number({"v": turns}, "v", "turns")
    if count < 1.0:
        raise ValueError("turns must be >= 1, got %g" % count)
    radius = diameter / 2.0
    return count * math.pi * radius * radius


def axial_flux_density_tesla(
    current_a,
    diameter_m=DEFAULT_LOOP_DIAMETER_M,
    turns=DEFAULT_LOOP_TURNS,
    standoff_m=DEFAULT_STANDOFF_M,
):
    """On-axis flux density a loop current produces at a standoff distance."""
    current = _positive(_number({"v": current_a}, "v", "current_a"), "current_a")
    diameter = _positive(_number({"v": diameter_m}, "v", "diameter_m"), "diameter_m")
    count = _number({"v": turns}, "v", "turns")
    if count < 1.0:
        raise ValueError("turns must be >= 1, got %g" % count)
    standoff = _number({"v": standoff_m}, "v", "standoff_m")
    if standoff < 0.0:
        raise ValueError("standoff_m must be >= 0, got %g" % standoff)
    radius = diameter / 2.0
    denominator = 2.0 * (radius * radius + standoff * standoff) ** 1.5
    return MU0 * count * current * radius * radius / denominator


def loop_current_for_flux_density(
    flux_density_t,
    diameter_m=DEFAULT_LOOP_DIAMETER_M,
    turns=DEFAULT_LOOP_TURNS,
    standoff_m=DEFAULT_STANDOFF_M,
):
    """Loop current that reaches a wanted flux density at the standoff."""
    flux = _positive(
        _number({"v": flux_density_t}, "v", "flux_density_t"), "flux_density_t"
    )
    unit = axial_flux_density_tesla(1.0, diameter_m, turns, standoff_m)
    return flux / unit


def loop_impedance_ohm(dc_resistance_ohm, inductance_h, frequency_hz):
    """Magnitude of the loop impedance at a tune frequency."""
    resistance = _positive(
        _number({"v": dc_resistance_ohm}, "v", "dc_resistance_ohm"), "dc_resistance_ohm"
    )
    inductance = _positive(
        _number({"v": inductance_h}, "v", "inductance_h"), "inductance_h"
    )
    frequency = _positive(
        _number({"v": frequency_hz}, "v", "frequency_hz"), "frequency_hz"
    )
    reactance = 2.0 * math.pi * frequency * inductance
    return math.sqrt(resistance * resistance + reactance * reactance)


def drive_level_dbm(current_a, impedance_ohm):
    """Apparent drive level that pushes a current through the loop impedance."""
    current = _positive(_number({"v": current_a}, "v", "current_a"), "current_a")
    impedance = _positive(
        _number({"v": impedance_ohm}, "v", "impedance_ohm"), "impedance_ohm"
    )
    watts = current * current * impedance
    return 10.0 * math.log10(watts / 1.0e-3)


def required_gain_db(drive_dbm, source_dbm):
    """Gain the amplifier must supply between the source and the loop."""
    drive = _number({"v": drive_dbm}, "v", "drive_dbm")
    source = _number({"v": source_dbm}, "v", "source_dbm")
    return drive - source


def meets(value, requirement, tol=DB_TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value >= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=0.0, abs_tol=tol)


def assess_equipment_set(
    equipment,
    band=DEFAULT_BAND_HZ,
    required_flux_density_t=1.0e-6,
    standoff_m=DEFAULT_STANDOFF_M,
    worst_case_frequency_hz=None,
):
    """Full clause 5.4.10.2 readiness assessment of the field-generating chain."""
    if not isinstance(equipment, (list, tuple)):
        raise ValueError("equipment: must be a list of equipment records")
    required = validate_band(band, "required_band")
    flux = _positive(
        _number({"v": required_flux_density_t}, "v", "required_flux_density_t"),
        "required_flux_density_t",
    )
    standoff = _number({"v": standoff_m}, "v", "standoff_m")
    if standoff < 0.0:
        raise ValueError("standoff_m must be >= 0, got %g" % standoff)
    tune = required[1] if worst_case_frequency_hz is None else _positive(
        _number({"v": worst_case_frequency_hz}, "v", "worst_case_frequency_hz"),
        "worst_case_frequency_hz",
    )

    by_role = {}
    for record in equipment:
        item = validate_equipment(record)
        if item["role"] in by_role:
            raise ValueError(
                "equipment: role %r appears twice; the clause lists one of each"
                % item["role"]
            )
        by_role[item["role"]] = item

    findings = []
    limitations = []
    missing = [role for role in REQUIRED_ROLES if role not in by_role]
    for role in missing:
        findings.append("required equipment absent from the chain: %s" % role)

    for role in REQUIRED_ROLES:
        item = by_role.get(role)
        if item is None:
            continue
        if not item["calibration_current"]:
            findings.append(
                "calibration lapsed on the %s by %g day(s)"
                % (role, -item["calibration_days_remaining"])
            )
        elif item["calibration_days_remaining"] < 30.0:
            limitations.append(
                "calibration on the %s expires in %g day(s)"
                % (role, item["calibration_days_remaining"])
            )

    coverage = None
    limiting = None
    geometry = None
    drive = None
    gain_needed = None
    loop_current = None
    if not missing:
        present = [by_role[role] for role in REQUIRED_ROLES]
        coverage = chain_coverage(present, required)
        for gap in coverage["gaps_hz"]:
            findings.append("exposure band not covered from %g Hz to %g Hz" % gap)
        limiting = limiting_equipment(present, required)

        loop = by_role[ROLE_LOOP]
        geometry = {
            "diameter_m": loop["diameter_m"],
            "turns": loop["turns"],
            "turns_area_m2": loop_turns_area_m2(loop["diameter_m"], loop["turns"]),
            "standoff_m": standoff,
        }
        loop_current = loop_current_for_flux_density(
            flux, loop["diameter_m"], loop["turns"], standoff
        )
        if not meets(
            loop["rated_current_a"], loop_current, tol=FREQ_REL_TOL * loop_current
        ):
            findings.append(
                "loop rated for %g A cannot carry the %g A the wanted field needs"
                % (loop["rated_current_a"], loop_current)
            )
        impedance = loop_impedance_ohm(
            loop["dc_resistance_ohm"], loop["inductance_h"], tune
        )
        geometry["impedance_ohm"] = impedance
        geometry["tune_frequency_hz"] = tune
        drive = drive_level_dbm(loop_current, impedance)

        source = by_role[ROLE_SOURCE]
        amplifier = by_role[ROLE_AMPLIFIER]
        gain_needed = required_gain_db(drive, source["max_output_dbm"])
        if not meets(amplifier["gain_db"], gain_needed):
            findings.append(
                "amplifier gain %.2f dB falls short of the %.2f dB the loop drive "
                "needs" % (amplifier["gain_db"], gain_needed)
            )
        if not meets(amplifier["max_output_dbm"], drive):
            findings.append(
                "amplifier tops out at %.2f dBm, below the %.2f dBm the loop drive "
                "needs" % (amplifier["max_output_dbm"], drive)
            )
        elif amplifier["max_output_dbm"] - drive < 3.0:
            limitations.append(
                "amplifier headroom is only %.2f dB above the loop drive"
                % (amplifier["max_output_dbm"] - drive)
            )

    return {
        "roles_present": sorted(by_role),
        "missing_roles": missing,
        "coverage": coverage,
        "limiting_equipment": limiting,
        "loop_geometry": geometry,
        "loop_current_a": loop_current,
        "loop_drive_dbm": drive,
        "required_gain_db": gain_needed,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_READY if not findings else VERDICT_INCOMPLETE,
    }
