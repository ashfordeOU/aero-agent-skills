#!/usr/bin/env python3
"""Low-frequency conducted-emission equipment set, ECSS-E-ST-20-07C 5.4.2.2.

Paraphrased procedure, no verbatim standard text. The clause names the
instruments a low-frequency conducted-emission run is built from: a
measurement receiver, a current probe clamped on the harness, and a signal
source used to drive the system check. This module turns that list into a
deterministic readiness decision:

  instrument records -> role normalization and validation
  role coverages     -> intersection with the required measurement band
  uncovered sub-band -> the instrument that limits the chain
  probe + current    -> the source drive level the system check needs

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

# Required low-frequency conducted-emission measurement band, hertz.
DEFAULT_BAND_HZ = (30.0, 100.0e3)

# Smallest probe transfer impedance that still leaves the receiver a usable
# voltage for a harness current at the low end of the band, ohm.
DEFAULT_MIN_TRANSFER_IMPEDANCE_OHM = 1.0

# Reference impedance of the receiver and source ports, ohm.
SYSTEM_IMPEDANCE_OHM = 50.0

ROLE_RECEIVER = "measurement-receiver"
ROLE_PROBE = "current-probe"
ROLE_SOURCE = "signal-source"
REQUIRED_ROLES = (ROLE_RECEIVER, ROLE_PROBE, ROLE_SOURCE)

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


def normalize_role(role):
    """Return the recognized instrument role for a raw role designation."""
    if not isinstance(role, str):
        raise ValueError("instrument role must be a string, got %r" % (role,))
    key = role.strip().lower()
    if key not in REQUIRED_ROLES:
        raise ValueError(
            "unrecognized instrument role %r; recognized: %s"
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
        raise ValueError(
            "%s: high_hz %g must exceed low_hz %g" % (where, high, low)
        )
    return (low, high)


def validate_instrument(record):
    """Validate one instrument record and return a normalized copy.

    Every record carries role, frequency_min_hz, frequency_max_hz and
    calibration_days_remaining. A current-probe adds transfer_impedance_ohm
    and rated_current_a; a signal-source adds max_output_dbm.
    """
    if not isinstance(record, dict):
        raise ValueError("instrument: record must be a mapping")
    role = normalize_role(record.get("role"))
    where = "instrument[%s]" % role
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
    if role == ROLE_PROBE:
        transfer = _number(record, "transfer_impedance_ohm", where)
        if transfer <= 0.0:
            raise ValueError(
                "%s: transfer_impedance_ohm must be > 0, got %g" % (where, transfer)
            )
        rated = _number(record, "rated_current_a", where)
        if rated <= 0.0:
            raise ValueError(
                "%s: rated_current_a must be > 0, got %g" % (where, rated)
            )
        out["transfer_impedance_ohm"] = transfer
        out["rated_current_a"] = rated
    if role == ROLE_SOURCE:
        out["max_output_dbm"] = _number(record, "max_output_dbm", where)
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
    """Sub-bands of the required band left outside the instrument coverage."""
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


def chain_coverage(instruments, band=DEFAULT_BAND_HZ):
    """Intersect every instrument coverage with the required band."""
    required = validate_band(band, "required_band")
    if not isinstance(instruments, (list, tuple)) or len(instruments) == 0:
        raise ValueError("chain_coverage: at least one instrument is required")
    coverage = required
    for record in instruments:
        instrument = record if "role" in record else validate_instrument(record)
        coverage = band_overlap(
            coverage,
            (instrument["frequency_min_hz"], instrument["frequency_max_hz"]),
        ) if coverage is not None else None
        if coverage is None:
            break
    gaps = uncovered_sub_bands(required, coverage)
    covered = 0.0 if coverage is None else band_decades(coverage)
    return {
        "required_band_hz": required,
        "coverage_hz": coverage,
        "gaps_hz": gaps,
        "required_decades": band_decades(required),
        "covered_decades": covered,
    }


def limiting_instrument(instruments, band=DEFAULT_BAND_HZ):
    """Name the instrument that removes the most decades from the band.

    Ties resolve to the role order the clause lists the instruments in, so
    the result is stable for identical coverages.
    """
    required = validate_band(band, "required_band")
    normalized = [
        record if "role" in record else validate_instrument(record)
        for record in instruments
    ]
    if len(normalized) == 0:
        raise ValueError("limiting_instrument: at least one instrument is required")
    best = None
    for record in normalized:
        overlap = band_overlap(
            required, (record["frequency_min_hz"], record["frequency_max_hz"])
        )
        lost = band_decades(required) - (0.0 if overlap is None else band_decades(overlap))
        order = REQUIRED_ROLES.index(record["role"])
        key = (-lost, order)
        if best is None or key < best[0]:
            best = (key, record["role"], lost)
    return {"role": best[1], "lost_decades": best[2]}


def system_check_drive_dbm(
    current_a, transfer_impedance_ohm, system_impedance_ohm=SYSTEM_IMPEDANCE_OHM
):
    """Source level that injects a wanted probe current during the check.

    The probe develops current_a * transfer_impedance_ohm volts across the
    receiver port; the level is that voltage referred to one milliwatt in the
    system impedance.
    """
    current = _number({"v": current_a}, "v", "current_a")
    transfer = _number({"v": transfer_impedance_ohm}, "v", "transfer_impedance_ohm")
    impedance = _number({"v": system_impedance_ohm}, "v", "system_impedance_ohm")
    if current <= 0.0:
        raise ValueError("current_a must be > 0, got %g" % current)
    if transfer <= 0.0:
        raise ValueError("transfer_impedance_ohm must be > 0, got %g" % transfer)
    if impedance <= 0.0:
        raise ValueError("system_impedance_ohm must be > 0, got %g" % impedance)
    volts = current * transfer
    watts = (volts * volts) / impedance
    return 10.0 * math.log10(watts / 1.0e-3)


def meets(value, requirement, tol=DB_TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value >= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=0.0, abs_tol=tol)


def assess_equipment_set(
    instruments,
    band=DEFAULT_BAND_HZ,
    harness_current_a=1.0,
    system_check_current_a=0.01,
    min_transfer_impedance_ohm=DEFAULT_MIN_TRANSFER_IMPEDANCE_OHM,
):
    """Full clause 5.4.2.2 readiness assessment of the instrument set."""
    if not isinstance(instruments, (list, tuple)):
        raise ValueError("instruments: must be a list of instrument records")
    required = validate_band(band, "required_band")
    harness = _number({"v": harness_current_a}, "v", "harness_current_a")
    if harness <= 0.0:
        raise ValueError("harness_current_a must be > 0, got %g" % harness)
    check_current = _number({"v": system_check_current_a}, "v", "system_check_current_a")
    if check_current <= 0.0:
        raise ValueError("system_check_current_a must be > 0, got %g" % check_current)
    minimum_transfer = _number(
        {"v": min_transfer_impedance_ohm}, "v", "min_transfer_impedance_ohm"
    )
    if minimum_transfer <= 0.0:
        raise ValueError("min_transfer_impedance_ohm must be > 0")

    by_role = {}
    for record in instruments:
        instrument = validate_instrument(record)
        if instrument["role"] in by_role:
            raise ValueError(
                "instruments: role %r appears twice; the clause lists one of each"
                % instrument["role"]
            )
        by_role[instrument["role"]] = instrument

    findings = []
    limitations = []
    missing = [role for role in REQUIRED_ROLES if role not in by_role]
    for role in missing:
        findings.append("required instrument absent from the set: %s" % role)

    for role in REQUIRED_ROLES:
        instrument = by_role.get(role)
        if instrument is None:
            continue
        if not instrument["calibration_current"]:
            findings.append(
                "calibration lapsed on the %s by %g day(s)"
                % (role, -instrument["calibration_days_remaining"])
            )
        elif instrument["calibration_days_remaining"] < 30.0:
            limitations.append(
                "calibration on the %s expires in %g day(s)"
                % (role, instrument["calibration_days_remaining"])
            )

    coverage = None
    limiting = None
    if not missing:
        present = [by_role[role] for role in REQUIRED_ROLES]
        coverage = chain_coverage(present, required)
        for gap in coverage["gaps_hz"]:
            findings.append(
                "measurement band not covered from %g Hz to %g Hz" % gap
            )
        limiting = limiting_instrument(present, required)

        probe = by_role[ROLE_PROBE]
        if probe["transfer_impedance_ohm"] < minimum_transfer and not math.isclose(
            probe["transfer_impedance_ohm"], minimum_transfer, rel_tol=0.0, abs_tol=DB_TOL
        ):
            findings.append(
                "probe transfer impedance %g ohm is below the %g ohm floor"
                % (probe["transfer_impedance_ohm"], minimum_transfer)
            )
        if not meets(probe["rated_current_a"], harness, tol=FREQ_REL_TOL * harness):
            findings.append(
                "probe rated for %g A cannot clamp a harness carrying %g A"
                % (probe["rated_current_a"], harness)
            )

        drive = system_check_drive_dbm(check_current, probe["transfer_impedance_ohm"])
        source = by_role[ROLE_SOURCE]
        if not meets(source["max_output_dbm"], drive):
            findings.append(
                "signal source tops out at %.2f dBm, below the %.2f dBm the "
                "system check needs" % (source["max_output_dbm"], drive)
            )
    else:
        drive = None

    return {
        "roles_present": sorted(by_role),
        "missing_roles": missing,
        "coverage": coverage,
        "limiting_instrument": limiting,
        "system_check_drive_dbm": drive,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_READY if not findings else VERDICT_INCOMPLETE,
    }
