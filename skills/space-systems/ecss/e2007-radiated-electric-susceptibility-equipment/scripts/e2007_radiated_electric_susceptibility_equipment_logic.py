#!/usr/bin/env python3
"""Radiated electric susceptibility equipment, ECSS-E-ST-20-07C clause 5.4.11.2.

Paraphrased procedure, no verbatim standard text. The clause lists the items a
radiated electric field exposure is made with: a signal generator, a power
amplifier, a transmit antenna and an isotropic field probe. This module turns
that list into a deterministic readiness assessment:

  declared items       -> one item per role, none missing, none doubled
  usable spans         -> intersection, and the item bounding each edge
  field requirement    -> forward power the antenna needs at the separation
  generator+amplifier  -> power delivered, and its margin over that need
  probe                -> isotropic, and its range covers the required field
  calibration validity -> graded against the campaign window, not against today

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. Powers are compared after a logarithm, so a
# chain that exactly meets its requirement can land a few units in the last
# place either side of equality. This absorbs representation error only.
DB_TOL = 1e-9

# Relative slack allowed at a band edge before a span is called short of it.
BAND_EDGE_REL_TOL = 1e-9

# Free-space relation between radiated power and field strength: the field at a
# distance is the square root of thirty times the power-gain product, divided
# by the distance. The constant is in volts squared per watt.
FREE_SPACE_CONSTANT = 30.0

ROLE_GENERATOR = "signal-generator"
ROLE_AMPLIFIER = "power-amplifier"
ROLE_ANTENNA = "transmit-antenna"
ROLE_PROBE = "isotropic-field-probe"
REQUIRED_ROLES = (ROLE_GENERATOR, ROLE_AMPLIFIER, ROLE_ANTENNA, ROLE_PROBE)

# Numeric fields each role must declare beyond its span and calibration.
ROLE_NUMERIC_FIELDS = {
    ROLE_GENERATOR: ("output_dbm",),
    ROLE_AMPLIFIER: ("gain_db", "rated_output_dbm"),
    ROLE_ANTENNA: ("gain_dbi",),
    ROLE_PROBE: ("range_min_v_m", "range_max_v_m"),
}

READY = "exposure-chain-ready"
NOT_READY = "exposure-chain-not-ready"


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


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def at_least_db(value, bound):
    """True when a decibel quantity reaches a bound, float error aside."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=0.0, abs_tol=DB_TOL)


def normalize_role(role):
    """Return the recognized instrument role for a raw designation."""
    if not isinstance(role, str):
        raise ValueError("role must be a string, got %r" % (role,))
    key = role.strip().lower()
    if key not in REQUIRED_ROLES:
        raise ValueError(
            "unrecognized role %r; recognized: %s" % (role, ", ".join(REQUIRED_ROLES))
        )
    return key


def validate_instrument(item):
    """Validate one declared instrument and return it normalized.

    Every item declares a role, an identifier, a usable span and how many days
    its calibration still runs. Each role then declares the few numbers that
    make it usable in the chain, and the probe declares whether it is isotropic.
    """
    where = "instrument"
    if not isinstance(item, dict):
        raise ValueError("%s: item must be a mapping" % where)
    if "role" not in item:
        raise ValueError("%s: missing required field 'role'" % where)
    role = normalize_role(item["role"])
    where = "instrument[%s]" % role

    identifier = item.get("identifier")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("%s: identifier must be a non-empty string" % where)

    low = _number(item, "span_low_hz", where)
    high = _number(item, "span_high_hz", where)
    if low <= 0.0:
        raise ValueError("%s: span_low_hz must be > 0, got %g" % (where, low))
    if high <= low:
        raise ValueError(
            "%s: span_high_hz (%g) must exceed span_low_hz (%g)" % (where, high, low)
        )

    validity = _number(item, "calibration_valid_days", where)
    if validity < 0.0:
        raise ValueError(
            "%s: calibration_valid_days must be >= 0, got %g" % (where, validity)
        )

    out = {
        "role": role,
        "identifier": identifier.strip(),
        "span_low_hz": low,
        "span_high_hz": high,
        "calibration_valid_days": validity,
    }
    for key in ROLE_NUMERIC_FIELDS[role]:
        out[key] = _number(item, key, where)
    if role == ROLE_PROBE:
        out["is_isotropic"] = _flag(item, "is_isotropic", where)
        if out["range_min_v_m"] <= 0.0:
            raise ValueError(
                "%s: range_min_v_m must be > 0, got %g" % (where, out["range_min_v_m"])
            )
        if out["range_max_v_m"] <= out["range_min_v_m"]:
            raise ValueError(
                "%s: range_max_v_m (%g) must exceed range_min_v_m (%g)"
                % (where, out["range_max_v_m"], out["range_min_v_m"])
            )
    return out


def collect_instrument_set(items):
    """Validate every declared item and index it by role, refusing a duplicate."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("instrument set must be a list")
    if len(items) == 0:
        raise ValueError("instrument set must declare at least one item")
    by_role = {}
    for item in items:
        instrument = validate_instrument(item)
        role = instrument["role"]
        if role in by_role:
            raise ValueError(
                "role %r declared twice (%s and %s); the run plan has not said "
                "which item does what"
                % (role, by_role[role]["identifier"], instrument["identifier"])
            )
        by_role[role] = instrument
    return by_role


def absent_roles(by_role):
    """Roles the clause lists that the declared set does not fill."""
    if not isinstance(by_role, dict):
        raise ValueError("by_role must be a mapping")
    return [role for role in REQUIRED_ROLES if role not in by_role]


def span_intersection(by_role):
    """Band the declared items can work over together, and what bounds it."""
    if not by_role:
        raise ValueError("span_intersection: no instruments declared")
    low_item = max(by_role.values(), key=lambda i: i["span_low_hz"])
    high_item = min(by_role.values(), key=lambda i: i["span_high_hz"])
    low = low_item["span_low_hz"]
    high = high_item["span_high_hz"]
    if high <= low:
        raise ValueError(
            "declared spans do not overlap: %s starts at %g Hz, %s stops at %g Hz"
            % (low_item["identifier"], low, high_item["identifier"], high)
        )
    return {
        "low_hz": low,
        "high_hz": high,
        "low_bounded_by": low_item["identifier"],
        "low_bounded_role": low_item["role"],
        "high_bounded_by": high_item["identifier"],
        "high_bounded_role": high_item["role"],
    }


def band_coverage_findings(intersection, band, rel_tol=BAND_EDGE_REL_TOL):
    """Edges of the method band the declared chain cannot reach."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("band must be a (low, high) pair")
    low = _scalar(band[0], "band.low")
    high = _scalar(band[1], "band.high")
    if low <= 0.0:
        raise ValueError("band.low must be > 0, got %g" % low)
    if high <= low:
        raise ValueError("band.high (%g) must exceed band.low (%g)" % (high, low))
    slack = _scalar(rel_tol, "rel_tol")
    if slack < 0.0:
        raise ValueError("rel_tol must be >= 0, got %g" % slack)
    out = []
    chain_low = intersection["low_hz"]
    chain_high = intersection["high_hz"]
    if chain_low > low and not math.isclose(chain_low, low, rel_tol=slack, abs_tol=0.0):
        out.append(
            "the chain starts at %g Hz, above the %g Hz band edge; %s bounds it"
            % (chain_low, low, intersection["low_bounded_by"])
        )
    if chain_high < high and not math.isclose(
        chain_high, high, rel_tol=slack, abs_tol=0.0
    ):
        out.append(
            "the chain stops at %g Hz, below the %g Hz band edge; %s bounds it"
            % (chain_high, high, intersection["high_bounded_by"])
        )
    return out


def required_forward_power_w(field_v_m, distance_m, antenna_gain_dbi):
    """Forward power the transmit antenna needs to raise a field at a distance."""
    field = _scalar(field_v_m, "field_v_m")
    distance = _scalar(distance_m, "distance_m")
    gain_dbi = _scalar(antenna_gain_dbi, "antenna_gain_dbi")
    if field <= 0.0:
        raise ValueError("field_v_m must be > 0, got %g" % field)
    if distance <= 0.0:
        raise ValueError("distance_m must be > 0, got %g" % distance)
    gain_linear = math.pow(10.0, gain_dbi / 10.0)
    return (field * distance) * (field * distance) / (FREE_SPACE_CONSTANT * gain_linear)


def watts_to_dbm(power_w):
    """Convert a power in watts to decibels above one milliwatt."""
    power = _scalar(power_w, "power_w")
    if power <= 0.0:
        raise ValueError("power_w must be > 0, got %g" % power)
    return 10.0 * math.log10(power * 1000.0)


def dbm_to_watts(power_dbm):
    """Convert a power in decibels above one milliwatt back to watts."""
    power = _scalar(power_dbm, "power_dbm")
    return math.pow(10.0, power / 10.0) / 1000.0


def delivered_power_dbm(generator, amplifier, cable_loss_db=0.0):
    """Power the generator and amplifier actually put into the antenna feed.

    The amplifier cannot give back more than it is rated for, so the drive it
    is offered is capped at that rating before the feed loss is taken off.
    """
    loss = _scalar(cable_loss_db, "cable_loss_db")
    if loss < 0.0:
        raise ValueError("cable_loss_db must be >= 0, got %g" % loss)
    drive = _number(generator, "output_dbm", "generator") + _number(
        amplifier, "gain_db", "amplifier"
    )
    rated = _number(amplifier, "rated_output_dbm", "amplifier")
    capped = min(drive, rated)
    return {
        "uncapped_drive_dbm": drive,
        "rated_output_dbm": rated,
        "amplifier_saturated": drive > rated + DB_TOL,
        "delivered_dbm": capped - loss,
        "cable_loss_db": loss,
    }


def power_margin_db(delivered_dbm, required_dbm):
    """Margin of the power delivered over the power the field requirement needs."""
    delivered = _scalar(delivered_dbm, "delivered_dbm")
    required = _scalar(required_dbm, "required_dbm")
    return delivered - required


def probe_findings(probe, field_required_v_m):
    """Ways the declared field probe cannot report the required exposure."""
    field = _scalar(field_required_v_m, "field_required_v_m")
    if field <= 0.0:
        raise ValueError("field_required_v_m must be > 0, got %g" % field)
    out = []
    if not probe["is_isotropic"]:
        out.append(
            "field probe %s is not isotropic, so the reading depends on how it is "
            "oriented in the field" % probe["identifier"]
        )
    if field > probe["range_max_v_m"] and not math.isclose(
        field, probe["range_max_v_m"], rel_tol=0.0, abs_tol=1e-12
    ):
        out.append(
            "field probe %s reads to %g V/m, under the %g V/m the exposure requires"
            % (probe["identifier"], probe["range_max_v_m"], field)
        )
    if field < probe["range_min_v_m"] and not math.isclose(
        field, probe["range_min_v_m"], rel_tol=0.0, abs_tol=1e-12
    ):
        out.append(
            "field probe %s reads from %g V/m, above the %g V/m the exposure "
            "requires" % (probe["identifier"], probe["range_min_v_m"], field)
        )
    return out


def calibration_findings(by_role, campaign_days):
    """Items whose calibration lapses before the campaign window closes."""
    days = _scalar(campaign_days, "campaign_days")
    if days <= 0.0:
        raise ValueError("campaign_days must be > 0, got %g" % days)
    out = []
    for role in REQUIRED_ROLES:
        instrument = by_role.get(role)
        if instrument is None:
            continue
        validity = instrument["calibration_valid_days"]
        if validity < days and not math.isclose(
            validity, days, rel_tol=0.0, abs_tol=1e-9
        ):
            out.append(
                "%s %s is calibrated for %g more days against a %g day campaign"
                % (role, instrument["identifier"], validity, days)
            )
    return out


def assess_radiated_electric_susceptibility_equipment(items, requirement):
    """Full clause 5.4.11.2 readiness assessment of an exposure instrument chain.

    requirement keys: band_hz (a low/high pair), field_required_v_m,
    separation_m, campaign_days and the optional cable_loss_db.
    """
    where = "requirement"
    if not isinstance(requirement, dict):
        raise ValueError("%s: requirement must be a mapping" % where)
    for key in ("band_hz", "field_required_v_m", "separation_m", "campaign_days"):
        if key not in requirement:
            raise ValueError("%s: missing required field %r" % (where, key))

    by_role = collect_instrument_set(items)
    absent = absent_roles(by_role)
    field = _number(requirement, "field_required_v_m", where)
    if field <= 0.0:
        raise ValueError("%s: field_required_v_m must be > 0, got %g" % (where, field))

    findings = []
    limitations = []
    for role in absent:
        findings.append(
            "no %s is declared; the exposure cannot be raised at all" % role
        )
    if absent:
        return {
            "instruments": by_role,
            "absent_roles": absent,
            "span_intersection": None,
            "required_power": None,
            "delivered_power": None,
            "power_margin_db": None,
            "findings": findings,
            "limitations": limitations,
            "verdict": NOT_READY,
        }

    intersection = span_intersection(by_role)
    findings.extend(band_coverage_findings(intersection, requirement["band_hz"]))

    required_w = required_forward_power_w(
        field,
        _number(requirement, "separation_m", where),
        by_role[ROLE_ANTENNA]["gain_dbi"],
    )
    required_dbm = watts_to_dbm(required_w)
    delivered = delivered_power_dbm(
        by_role[ROLE_GENERATOR],
        by_role[ROLE_AMPLIFIER],
        requirement.get("cable_loss_db", 0.0),
    )
    margin = power_margin_db(delivered["delivered_dbm"], required_dbm)

    if not at_least_db(margin, 0.0):
        findings.append(
            "the chain delivers %g dBm against the %g dBm needed for %g V/m, a %g dB "
            "shortfall" % (delivered["delivered_dbm"], required_dbm, field, -margin)
        )
    elif math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=DB_TOL):
        limitations.append(
            "the chain meets the %g dBm the field requirement needs exactly, leaving "
            "nothing for feed-loss drift" % required_dbm
        )
    if delivered["amplifier_saturated"]:
        limitations.append(
            "generator drive exceeds the amplifier rating, so the delivered power is "
            "capped at %g dBm and the level is set by the amplifier, not the dial"
            % delivered["rated_output_dbm"]
        )

    findings.extend(probe_findings(by_role[ROLE_PROBE], field))
    findings.extend(
        calibration_findings(by_role, _number(requirement, "campaign_days", where))
    )

    return {
        "instruments": by_role,
        "absent_roles": absent,
        "span_intersection": intersection,
        "required_power": {"watts": required_w, "dbm": required_dbm},
        "delivered_power": delivered,
        "power_margin_db": margin,
        "findings": findings,
        "limitations": limitations,
        "verdict": READY if not findings else NOT_READY,
    }
