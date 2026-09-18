#!/usr/bin/env python3
"""Radiated electric-emission instrument set, ECSS-E-ST-20-07C clause 5.4.6.2.

Paraphrased procedure, no verbatim standard text. The clause names what a
radiated electric-field emission run is made with: a measurement receiver, a
recorder for what the receiver reads, and the polarized receive antennas that
couple the field into it. Unlike a conducted method, no single antenna spans
the band, so the antennas are a SET that has to tile the band -- in each
polarization separately -- rather than a single item whose span is intersected
with the others.

  declared items      -> validated roles, spans, calibration windows
  antennas per plane  -> tiled union -> uncovered segments of the method band
  receiver reading    -> antenna factor + cable loss -> field strength
  campaign window     -> calibration shortfall per item
  aggregate           -> readiness with findings and limitations

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Span edges and calibration windows are floats, so an
# item whose span ends exactly on a band edge can land a few units in the last
# place either side of it. The tolerance absorbs that only; it never widens a
# declared span.
TOL = 1e-9

# Default span of the radiated electric-field emission method, hertz.
DEFAULT_METHOD_BAND_HZ = (30.0e6, 18.0e9)

# Default campaign window the calibration certificates have to outlast, days.
DEFAULT_CAMPAIGN_DAYS = 30.0

# Roles that must be declared exactly once. Declaring one of them twice means
# the run plan has not said which item does the job.
SINGLETON_ROLES = ("measurement-receiver", "data-recorder")

# The antenna role is the one role that may -- and normally must -- be
# declared several times, because no single antenna covers the method band.
ANTENNA_ROLE = "receive-antenna"

ROLES = SINGLETON_ROLES + (ANTENNA_ROLE,)

# An antenna is built for a plane; the set has to reach both of them.
POLARIZATIONS = ("vertical", "horizontal")

STATUS_READY = "equipment-ready"
STATUS_NOT_READY = "equipment-not-ready"


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


def validate_method_band(band=DEFAULT_METHOD_BAND_HZ):
    """Validate the declared method band and return it as a float pair."""
    where = "method_band_hz"
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s: band must be a (low, high) pair" % where)
    low = _number({"v": band[0]}, "v", "%s.low" % where)
    high = _number({"v": band[1]}, "v", "%s.high" % where)
    if low <= 0.0:
        raise ValueError("%s: low edge must be > 0, got %g" % (where, low))
    if high <= low:
        raise ValueError(
            "%s: high edge %g Hz must exceed low edge %g Hz" % (where, high, low)
        )
    return (low, high)


def normalize_role(role):
    """Return the recognized instrument role for a raw designation."""
    if not isinstance(role, str):
        raise ValueError("instrument role must be a string, got %r" % (role,))
    key = role.strip().lower()
    if key not in ROLES:
        raise ValueError(
            "unrecognized instrument role %r; recognized: %s"
            % (role, ", ".join(ROLES))
        )
    return key


def normalize_polarization(polarization):
    """Return the recognized antenna polarization for a raw designation."""
    if not isinstance(polarization, str):
        raise ValueError("polarization must be a string, got %r" % (polarization,))
    key = polarization.strip().lower()
    if key not in POLARIZATIONS:
        raise ValueError(
            "unrecognized polarization %r; recognized: %s"
            % (polarization, ", ".join(POLARIZATIONS))
        )
    return key


def validate_instrument(item):
    """Validate one declared instrument and return it normalized."""
    where = "instrument"
    if not isinstance(item, dict):
        raise ValueError("%s: must be a mapping" % where)
    identifier = item.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("%s: 'id' must be a non-empty string, got %r" % (where, identifier))
    tag = "instrument[%s]" % identifier
    role = normalize_role(item.get("role"))
    low = _number(item, "span_low_hz", tag)
    high = _number(item, "span_high_hz", tag)
    if low <= 0.0:
        raise ValueError("%s: span_low_hz must be > 0, got %g" % (tag, low))
    if high <= low:
        raise ValueError(
            "%s: span_high_hz %g Hz must exceed span_low_hz %g Hz" % (tag, high, low)
        )
    days = _number(item, "calibration_valid_days", tag)
    if days < 0.0:
        raise ValueError("%s: calibration_valid_days must be >= 0, got %g" % (tag, days))
    normalized = {
        "id": identifier.strip(),
        "role": role,
        "span_low_hz": low,
        "span_high_hz": high,
        "calibration_valid_days": days,
    }
    if role == ANTENNA_ROLE:
        planes = item.get("polarizations")
        if not isinstance(planes, (list, tuple)) or len(planes) == 0:
            raise ValueError(
                "%s: an antenna must declare the polarizations it is used in" % tag
            )
        resolved = []
        for plane in planes:
            key = normalize_polarization(plane)
            if key in resolved:
                raise ValueError("%s: polarization %r declared twice" % (tag, key))
            resolved.append(key)
        normalized["polarizations"] = tuple(
            plane for plane in POLARIZATIONS if plane in resolved
        )
        normalized["antenna_factor_db_per_m"] = _number(
            item, "antenna_factor_db_per_m", tag
        )
    return normalized


def validate_instrument_set(items):
    """Validate every declared item and reject a duplicated singleton role."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("instrument set: must be a list of declared items")
    if len(items) == 0:
        raise ValueError("instrument set: at least one item must be declared")
    records = []
    seen_ids = set()
    seen_singletons = set()
    for item in items:
        record = validate_instrument(item)
        if record["id"] in seen_ids:
            raise ValueError(
                "instrument set: identifier %r declared more than once" % record["id"]
            )
        seen_ids.add(record["id"])
        if record["role"] in SINGLETON_ROLES:
            if record["role"] in seen_singletons:
                raise ValueError(
                    "instrument set: role %r declared more than once; the run plan "
                    "must name one item for it" % record["role"]
                )
            seen_singletons.add(record["role"])
        records.append(record)
    return records


def missing_roles(records):
    """Return the roles the declared set never fills."""
    present = set(record["role"] for record in records)
    return tuple(role for role in ROLES if role not in present)


def antennas_for_polarization(records, polarization):
    """Return the declared antennas usable in one polarization."""
    plane = normalize_polarization(polarization)
    return [
        record
        for record in records
        if record["role"] == ANTENNA_ROLE and plane in record["polarizations"]
    ]


def band_gaps(antennas, band=DEFAULT_METHOD_BAND_HZ, tol=TOL):
    """Return the segments of the method band no declared antenna reaches."""
    low, high = validate_method_band(band)
    if not isinstance(antennas, (list, tuple)):
        raise ValueError("band_gaps: antennas must be a list")
    spans = sorted(
        (record["span_low_hz"], record["span_high_hz"]) for record in antennas
    )
    gaps = []
    cursor = low
    for span_low, span_high in spans:
        if span_high <= cursor:
            continue
        if span_low >= high:
            break
        if span_low > cursor and not math.isclose(
            span_low, cursor, rel_tol=tol, abs_tol=0.0
        ):
            gaps.append((cursor, span_low))
        cursor = max(cursor, min(span_high, high))
        if cursor >= high:
            break
    if cursor < high and not math.isclose(cursor, high, rel_tol=tol, abs_tol=0.0):
        gaps.append((cursor, high))
    return tuple(gaps)


def bounding_antennas(antennas):
    """Name the antenna at each edge of the union the antenna set reaches."""
    if not isinstance(antennas, (list, tuple)) or len(antennas) == 0:
        raise ValueError("bounding_antennas: at least one antenna is required")
    lowest = min(antennas, key=lambda r: (r["span_low_hz"], r["id"]))
    highest = max(antennas, key=lambda r: (r["span_high_hz"], r["id"]))
    return {
        "low_edge_item": lowest["id"],
        "low_edge_hz": lowest["span_low_hz"],
        "high_edge_item": highest["id"],
        "high_edge_hz": highest["span_high_hz"],
    }


def field_strength_dbuv_m(receiver_level_dbuv, antenna_factor_db_per_m, cable_loss_db=0.0):
    """Turn a receiver reading into the field strength at the antenna.

    The receiver reads a voltage at its input; the limit is written against a
    field strength. The antenna factor converts one into the other, and the
    loss of the cable between antenna and receiver is added back rather than
    ignored -- it made the reading lower than the field actually was.
    """
    level = _number({"v": receiver_level_dbuv}, "v", "receiver_level_dbuv")
    factor = _number({"v": antenna_factor_db_per_m}, "v", "antenna_factor_db_per_m")
    loss = _number({"v": cable_loss_db}, "v", "cable_loss_db")
    if loss < 0.0:
        raise ValueError("cable_loss_db must be >= 0, got %g" % loss)
    return level + factor + loss


def calibration_shortfall_days(valid_days, campaign_days=DEFAULT_CAMPAIGN_DAYS):
    """Days by which a certificate falls short of outlasting the campaign."""
    valid = _number({"v": valid_days}, "v", "valid_days")
    window = _number({"v": campaign_days}, "v", "campaign_days")
    if valid < 0.0:
        raise ValueError("valid_days must be >= 0, got %g" % valid)
    if window <= 0.0:
        raise ValueError("campaign_days must be > 0, got %g" % window)
    if valid >= window or math.isclose(valid, window, rel_tol=0.0, abs_tol=TOL):
        return 0.0
    return window - valid


def assess_equipment_set(
    items,
    band=DEFAULT_METHOD_BAND_HZ,
    campaign_days=DEFAULT_CAMPAIGN_DAYS,
    tol=TOL,
):
    """Full clause 5.4.6.2 readiness assessment of the declared instrument set."""
    records = validate_instrument_set(items)
    absent = missing_roles(records)
    if absent:
        raise ValueError(
            "instrument set: the run cannot be made without %s" % ", ".join(absent)
        )
    span = validate_method_band(band)
    window = _number({"v": campaign_days}, "v", "campaign_days")
    if window <= 0.0:
        raise ValueError("campaign_days must be > 0, got %g" % window)

    findings = []
    limitations = []

    receiver = [r for r in records if r["role"] == "measurement-receiver"][0]
    receiver_gaps = band_gaps([receiver], span, tol)
    for gap_low, gap_high in receiver_gaps:
        findings.append(
            "receiver %s does not reach %g-%g Hz of the method band"
            % (receiver["id"], gap_low, gap_high)
        )

    coverage = {}
    for plane in POLARIZATIONS:
        usable = antennas_for_polarization(records, plane)
        if not usable:
            findings.append("no declared antenna is used in %s polarization" % plane)
            coverage[plane] = {"antennas": (), "gaps": (span,), "bounds": None}
            continue
        gaps = band_gaps(usable, span, tol)
        for gap_low, gap_high in gaps:
            findings.append(
                "%s polarization has no antenna over %g-%g Hz"
                % (plane, gap_low, gap_high)
            )
        coverage[plane] = {
            "antennas": tuple(record["id"] for record in usable),
            "gaps": gaps,
            "bounds": bounding_antennas(usable),
        }

    for record in records:
        shortfall = calibration_shortfall_days(
            record["calibration_valid_days"], window
        )
        if shortfall > 0.0:
            findings.append(
                "calibration of %s lapses %g day(s) before the campaign ends"
                % (record["id"], shortfall)
            )
        elif math.isclose(
            record["calibration_valid_days"], window, rel_tol=0.0, abs_tol=TOL
        ):
            limitations.append(
                "calibration of %s expires on the last campaign day" % record["id"]
            )

    return {
        "band_hz": span,
        "campaign_days": window,
        "items": records,
        "receiver": receiver["id"],
        "recorder": [r for r in records if r["role"] == "data-recorder"][0]["id"],
        "polarization_coverage": coverage,
        "findings": findings,
        "limitations": limitations,
        "status": STATUS_READY if not findings else STATUS_NOT_READY,
    }
