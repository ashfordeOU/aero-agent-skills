#!/usr/bin/env python3
"""Conducted-emission instrument set, ECSS-E-ST-20-07C clause 5.4.3.2.

Paraphrased procedure, no verbatim standard text. The clause lists the items
the higher-band conducted-emission method is run with: a measurement receiver,
a current probe, a signal generator, a recorder for the results and an
oscilloscope. This module turns that list into a deterministic readiness
assessment:

  declared items -> role completeness, one item per role
  usable spans   -> intersection -> comparison with the method band
  bounding item  -> the instrument that limits the usable span
  probe factor   -> receiver reading converted to a lead current
  calibration    -> validity over the whole campaign window

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel and hertz comparison tolerance, absorbing float representation
# error only. It never widens an instrument span or a calibration window.
TOL = 1e-9

# Roles the method depends on. Every one must be declared exactly once.
REQUIRED_ROLES = (
    "measurement-receiver",
    "current-probe",
    "signal-generator",
    "data-recorder",
    "oscilloscope",
)

# Default span of the higher-band conducted-emission method, hertz.
DEFAULT_METHOD_BAND_HZ = (2.0e6, 100.0e6)

# Default number of days the calibration of every item must still be valid
# for, counted from the first day of the campaign.
DEFAULT_CAMPAIGN_DAYS = 30

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
    if key not in REQUIRED_ROLES:
        raise ValueError(
            "unrecognized instrument role %r; recognized: %s"
            % (role, ", ".join(REQUIRED_ROLES))
        )
    return key


def validate_instrument(item):
    """Validate one declared instrument record and return a normalized copy."""
    where = "instrument"
    if not isinstance(item, dict):
        raise ValueError("%s: record must be a mapping" % where)
    role = normalize_role(item.get("role"))
    tag = "%s[%s]" % (where, role)
    low = _number(item, "span_low_hz", tag)
    high = _number(item, "span_high_hz", tag)
    if low <= 0.0:
        raise ValueError("%s: span_low_hz must be > 0, got %g" % (tag, low))
    if high <= low:
        raise ValueError(
            "%s: span_high_hz %g must exceed span_low_hz %g" % (tag, high, low)
        )
    days = _number(item, "calibration_valid_days", tag)
    if days < 0.0:
        raise ValueError(
            "%s: calibration_valid_days must be >= 0, got %g" % (tag, days)
        )
    identifier = item.get("identifier", role)
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("%s: identifier must be a non-empty string" % tag)
    return {
        "role": role,
        "identifier": identifier.strip(),
        "span_hz": (low, high),
        "calibration_valid_days": days,
    }


def instrument_covers_band(item, band=DEFAULT_METHOD_BAND_HZ, tol=TOL):
    """True when one instrument's usable span spans the whole method band."""
    record = validate_instrument(item) if "span_hz" not in item else item
    low, high = validate_method_band(band)
    span_low, span_high = record["span_hz"]
    reaches_low = span_low <= low or math.isclose(
        span_low, low, rel_tol=0.0, abs_tol=tol
    )
    reaches_high = span_high >= high or math.isclose(
        span_high, high, rel_tol=0.0, abs_tol=tol
    )
    return reaches_low and reaches_high


def span_intersection(records):
    """Intersect the usable spans of the declared instruments."""
    if not isinstance(records, (list, tuple)) or len(records) == 0:
        raise ValueError("span_intersection: at least one instrument is required")
    low = max(record["span_hz"][0] for record in records)
    high = min(record["span_hz"][1] for record in records)
    if high <= low:
        raise ValueError(
            "span_intersection: the declared instruments share no usable span "
            "(%g Hz lower bound above %g Hz upper bound)" % (low, high)
        )
    return (low, high)


def bounding_instruments(records):
    """Name the instruments that set each edge of the shared usable span."""
    low, high = span_intersection(records)
    at_low = min(
        (r for r in records if math.isclose(r["span_hz"][0], low, rel_tol=0.0, abs_tol=TOL)),
        key=lambda r: r["role"],
    )
    at_high = min(
        (r for r in records if math.isclose(r["span_hz"][1], high, rel_tol=0.0, abs_tol=TOL)),
        key=lambda r: r["role"],
    )
    return {
        "intersection_hz": (low, high),
        "sets_low_edge": at_low["role"],
        "sets_high_edge": at_high["role"],
    }


def apply_probe_factor(receiver_level_dbuv, transfer_impedance_dbohm, cable_loss_db=0.0):
    """Convert a receiver reading into the lead current it represents.

    The current probe reports a voltage; the current on the lead follows from
    the probe transfer impedance, with the cable loss between probe and
    receiver added back. Result is in decibels above one microampere.
    """
    level = _number({"v": receiver_level_dbuv}, "v", "receiver_level_dbuv")
    impedance = _number(
        {"v": transfer_impedance_dbohm}, "v", "transfer_impedance_dbohm"
    )
    loss = _number({"v": cable_loss_db}, "v", "cable_loss_db")
    if loss < 0.0:
        raise ValueError("cable_loss_db must be >= 0, got %g" % loss)
    return level + loss - impedance


def injection_margin_db(generator_output_dbm, required_injection_dbm):
    """Headroom of the generator over the level the probe check needs."""
    output = _number({"v": generator_output_dbm}, "v", "generator_output_dbm")
    required = _number(
        {"v": required_injection_dbm}, "v", "required_injection_dbm"
    )
    return output - required


def missing_roles(records):
    """Roles the method needs that the declared set does not carry."""
    present = set(record["role"] for record in records)
    return tuple(role for role in REQUIRED_ROLES if role not in present)


def assess_equipment_set(
    items,
    band=DEFAULT_METHOD_BAND_HZ,
    campaign_days=DEFAULT_CAMPAIGN_DAYS,
    required_injection_dbm=None,
    generator_output_dbm=None,
):
    """Full clause 5.4.3.2 instrument-set readiness assessment."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items: the declared instrument set must be a list")
    if len(items) == 0:
        raise ValueError("items: at least one instrument must be declared")
    days = _number({"v": campaign_days}, "v", "campaign_days")
    if days <= 0.0:
        raise ValueError("campaign_days must be > 0, got %g" % days)

    records = []
    seen = set()
    for item in items:
        record = validate_instrument(item)
        if record["role"] in seen:
            raise ValueError(
                "items: role %r declared more than once" % record["role"]
            )
        seen.add(record["role"])
        records.append(record)

    gaps = missing_roles(records)
    if gaps:
        raise ValueError(
            "items: the method cannot be run without %s" % ", ".join(gaps)
        )

    span = validate_method_band(band)
    records.sort(key=lambda r: r["role"])

    findings = []
    limitations = []
    coverage = []
    for record in records:
        covers = instrument_covers_band(record, span)
        coverage.append(
            {
                "role": record["role"],
                "identifier": record["identifier"],
                "span_hz": record["span_hz"],
                "covers_method_band": covers,
                "calibration_valid_days": record["calibration_valid_days"],
            }
        )
        if not covers:
            findings.append(
                "%s span %g-%g Hz does not reach across the method band"
                % (record["role"], record["span_hz"][0], record["span_hz"][1])
            )
        if record["calibration_valid_days"] < days:
            if math.isclose(
                record["calibration_valid_days"], days, rel_tol=0.0, abs_tol=TOL
            ):
                limitations.append(
                    "%s calibration expires on the last campaign day"
                    % record["role"]
                )
            else:
                findings.append(
                    "%s calibration lapses %g days into a %g day campaign"
                    % (record["role"], record["calibration_valid_days"], days)
                )

    try:
        bounds = bounding_instruments(records)
    except ValueError as exc:
        findings.append(str(exc))
        bounds = None

    injection = None
    if required_injection_dbm is not None or generator_output_dbm is not None:
        if required_injection_dbm is None or generator_output_dbm is None:
            raise ValueError(
                "injection check needs both generator_output_dbm and "
                "required_injection_dbm"
            )
        margin = injection_margin_db(generator_output_dbm, required_injection_dbm)
        injection = {"margin_db": margin}
        if margin < 0.0 and not math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=TOL):
            findings.append(
                "signal-generator falls %.1f dB short of the injection level"
                % (-margin,)
            )
        elif math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=TOL):
            limitations.append(
                "signal-generator meets the injection level with no headroom"
            )

    return {
        "band_hz": span,
        "instruments": coverage,
        "bounds": bounds,
        "injection": injection,
        "findings": findings,
        "limitations": limitations,
        "status": STATUS_READY if not findings else STATUS_NOT_READY,
    }
