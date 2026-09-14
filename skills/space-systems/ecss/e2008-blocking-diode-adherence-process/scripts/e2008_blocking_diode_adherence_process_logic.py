#!/usr/bin/env python3
"""Getting every blocking diode of a lot into the ambient pressure chamber
before contact adherence is examined.

Anchor: ECSS-E-ST-20-08C clause 12.6.4.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The purpose clause says why a planar blocking diode attachment is
examined at all. This one says what goes into the chamber first, and it
says every device rather than a sample. That single word is the whole
difference between a lot result and a coupon result, and it is the part
of the procedure that is normally satisfied by a sentence rather than by
a record.

Entry is therefore a reconciliation, not a count:

    the roster     the serials the lot declares. A count alone cannot
                   tell a full tray from a tray with one device swapped
    the load       the serials actually put in. Three things can go
                   wrong and only one of them is visible in a total: a
                   device is missing, a device belongs to another lot,
                   or a serial appears twice because one part was logged
                   on two trays
    the batches    a lot too big for one chamber is split, and every
                   batch has to hold the residence dwell in its own
                   right. Splitting is allowed; shortening is not
    the pressure   a band around ambient, held while the devices sit
                   there, because a drifting volume conditions the
                   attachment by a route the examination never accounts
                   for

A missing device is the finding that outranks the rest, because the lot
sentence is handed out afterwards to devices that were never in the
chamber, and no downstream record says which ones they were. A foreign
or repeated serial comes next: the pull data is real, it simply belongs
to a different population than the one it will be filed under.

The bands, dwells and batch limits below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LOT_ENTRY_INCOMPLETE = "blocking-diode-lot-entry-incomplete"
FOREIGN_DEVICE_IN_CHAMBER = "blocking-diode-foreign-device-in-chamber"
CHAMBER_ENTRY_DEFICIENT = "blocking-diode-chamber-entry-deficient"
CHAMBER_ENTRY_ACCEPTED = "blocking-diode-chamber-entry-accepted"

ENTRY_VERDICTS = (
    LOT_ENTRY_INCOMPLETE,
    FOREIGN_DEVICE_IN_CHAMBER,
    CHAMBER_ENTRY_DEFICIENT,
    CHAMBER_ENTRY_ACCEPTED,
)

DEFAULT_BLOCKING_DIODE_ENTRY_POLICY = {
    "min_lot_entry_completeness": 1.0,
    "min_chamber_pressure_kpa": 86.0,
    "max_chamber_pressure_kpa": 106.0,
    "min_residence_dwell_h": 24.0,
    "max_entry_batches": 4,
    "max_batch_changeover_h": 2.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r"
            % (name, value)
        )
    return number


def _require_serials(name, value):
    if isinstance(value, (str, bytes)) or not hasattr(value, "__iter__"):
        raise ValueError("%s must be a sequence of serials, got %r" % (name, value))
    serials = list(value)
    for serial in serials:
        if not isinstance(serial, str) or not serial.strip():
            raise ValueError(
                "%s holds %r, which is not a device serial" % (name, serial)
            )
    return [serial.strip() for serial in serials]


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_blocking_diode_entry_policy(policy):
    """Check a blocking diode chamber entry policy is self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "min_lot_entry_completeness", policy.get("min_lot_entry_completeness")
    )
    low = _require_positive(
        "min_chamber_pressure_kpa", policy.get("min_chamber_pressure_kpa")
    )
    high = _require_positive(
        "max_chamber_pressure_kpa", policy.get("max_chamber_pressure_kpa")
    )
    if not low < high:
        raise ValueError(
            "min_chamber_pressure_kpa %g must sit below max_chamber_pressure_kpa "
            "%g" % (low, high)
        )
    _require_positive("min_residence_dwell_h", policy.get("min_residence_dwell_h"))
    _require_count("max_entry_batches", policy.get("max_entry_batches"))
    _require_positive(
        "max_batch_changeover_h", policy.get("max_batch_changeover_h")
    )
    return policy


def reconcile_entry_manifest(lot_serials, loaded_serials):
    """Compare the serials put in the chamber against the lot roster."""
    roster = _require_serials("lot_serials", lot_serials)
    loaded = _require_serials("loaded_serials", loaded_serials)
    if not roster:
        raise ValueError("lot_serials declares no device to put in the chamber")
    roster_set = set(roster)
    if len(roster_set) != len(roster):
        raise ValueError(
            "lot_serials repeats a serial, so the roster cannot say how many "
            "devices the lot holds"
        )

    seen = set()
    repeated = set()
    for serial in loaded:
        if serial in seen:
            repeated.add(serial)
        seen.add(serial)

    entered = sorted(seen & roster_set)
    return {
        "lot_size": len(roster),
        "entered": entered,
        "entered_count": len(entered),
        "missing": sorted(roster_set - seen),
        "foreign": sorted(seen - roster_set),
        "repeated": sorted(repeated),
    }


def lot_entry_completeness(entered_count, lot_size):
    """Share of the declared lot that actually went into the chamber."""
    lot = _require_count("lot_size", lot_size)
    if not isinstance(entered_count, int) or isinstance(entered_count, bool):
        raise ValueError(
            "entered_count must be a whole number, got %r" % (entered_count,)
        )
    if entered_count < 0:
        raise ValueError(
            "entered_count must not be negative, got %r" % (entered_count,)
        )
    if entered_count > lot:
        raise ValueError(
            "entered_count %d cannot exceed the %d devices the lot declares"
            % (entered_count, lot)
        )
    return entered_count / lot


def batch_residence_schedule(batches, changeover_h):
    """Devices, shortest dwell and total chamber time across every batch."""
    if isinstance(batches, dict) or not hasattr(batches, "__iter__"):
        raise ValueError("batches must be a sequence of batches, got %r" % (batches,))
    entries = list(batches)
    if not entries:
        raise ValueError("batches declares no batch, so nothing entered the chamber")
    changeover = _require_non_negative("changeover_h", changeover_h)

    devices_total = 0
    dwells = []
    for index, batch in enumerate(entries):
        if not isinstance(batch, dict):
            raise ValueError("batch %d must be a mapping, got %r" % (index, batch))
        devices_total += _require_count(
            "batch %d devices" % (index,), batch.get("devices")
        )
        dwells.append(
            _require_positive("batch %d dwell_h" % (index,), batch.get("dwell_h"))
        )

    return {
        "batch_count": len(entries),
        "devices_total": devices_total,
        "shortest_dwell_h": min(dwells),
        "total_chamber_time_h": sum(dwells) + changeover * (len(entries) - 1),
    }


def pressure_in_ambient_band(
    chamber_pressure_kpa, policy=DEFAULT_BLOCKING_DIODE_ENTRY_POLICY
):
    """True when the chamber sits inside the declared ambient band."""
    validate_blocking_diode_entry_policy(policy)
    pressure = _require_positive("chamber_pressure_kpa", chamber_pressure_kpa)
    return _at_least(
        pressure, float(policy["min_chamber_pressure_kpa"])
    ) and _at_most(pressure, float(policy["max_chamber_pressure_kpa"]))


def assess_blocking_diode_chamber_entry(
    case, policy=DEFAULT_BLOCKING_DIODE_ENTRY_POLICY
):
    """Full clause 12.6.4.2.2 judgement for one chamber entry."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_blocking_diode_entry_policy(policy)
    lot = case.get("lot")
    if not isinstance(lot, dict):
        raise ValueError("case is missing a lot block")
    entry = case.get("entry")
    if not isinstance(entry, dict):
        raise ValueError("case is missing an entry block")

    manifest = reconcile_entry_manifest(
        lot.get("serials"), entry.get("loaded_serials")
    )
    completeness = lot_entry_completeness(
        manifest["entered_count"], manifest["lot_size"]
    )
    schedule = batch_residence_schedule(
        entry.get("batches"), entry.get("changeover_h")
    )
    pressure = _require_positive(
        "entry chamber_pressure_kpa", entry.get("chamber_pressure_kpa")
    )

    findings = []
    result = {
        "lot_size": manifest["lot_size"],
        "entered_count": manifest["entered_count"],
        "missing": manifest["missing"],
        "foreign": manifest["foreign"],
        "repeated": manifest["repeated"],
        "lot_entry_completeness": completeness,
        "batch_count": schedule["batch_count"],
        "devices_total": schedule["devices_total"],
        "shortest_dwell_h": schedule["shortest_dwell_h"],
        "total_chamber_time_h": schedule["total_chamber_time_h"],
        "chamber_pressure_kpa": pressure,
        "pressure_in_band": pressure_in_ambient_band(pressure, policy),
        "findings": findings,
    }

    incomplete = not _at_least(
        completeness, float(policy["min_lot_entry_completeness"])
    )
    if incomplete:
        findings.append(
            "%d of the %d declared devices entered the chamber, a share of "
            "%.4f against the %.4f this clause asks for; absent: %s"
            % (
                manifest["entered_count"],
                manifest["lot_size"],
                completeness,
                float(policy["min_lot_entry_completeness"]),
                ", ".join(manifest["missing"]) or "none named",
            )
        )

    contaminated = bool(manifest["foreign"]) or bool(manifest["repeated"])
    if manifest["foreign"]:
        findings.append(
            "the chamber holds %d device(s) that are not on the lot roster: %s"
            % (len(manifest["foreign"]), ", ".join(manifest["foreign"]))
        )
    if manifest["repeated"]:
        findings.append(
            "%d serial(s) are logged onto more than one tray: %s"
            % (len(manifest["repeated"]), ", ".join(manifest["repeated"]))
        )

    if schedule["devices_total"] != manifest["entered_count"]:
        findings.append(
            "the batch sheets account for %d devices against the %d serials "
            "reconciled into the chamber"
            % (schedule["devices_total"], manifest["entered_count"])
        )
    if not _at_least(
        schedule["shortest_dwell_h"], float(policy["min_residence_dwell_h"])
    ):
        findings.append(
            "the shortest batch sat %.3f h against the %.3f h residence dwell "
            "every batch has to hold in its own right"
            % (
                schedule["shortest_dwell_h"],
                float(policy["min_residence_dwell_h"]),
            )
        )
    if schedule["batch_count"] > int(policy["max_entry_batches"]):
        findings.append(
            "the lot is split across %d batches against the %d allowed, so the "
            "population is spread over more chamber runs than the sentence "
            "covers"
            % (schedule["batch_count"], int(policy["max_entry_batches"]))
        )
    if not _at_most(
        _require_non_negative("entry changeover_h", entry.get("changeover_h")),
        float(policy["max_batch_changeover_h"]),
    ):
        findings.append(
            "the changeover between batches runs %.3f h against the %.3f h "
            "allowed, so later batches start from a different ambient"
            % (
                float(entry.get("changeover_h")),
                float(policy["max_batch_changeover_h"]),
            )
        )
    if not result["pressure_in_band"]:
        findings.append(
            "the chamber holds %.2f kPa, outside the %.2f to %.2f kPa ambient "
            "band the residence is run in"
            % (
                pressure,
                float(policy["min_chamber_pressure_kpa"]),
                float(policy["max_chamber_pressure_kpa"]),
            )
        )

    if incomplete:
        result["verdict"] = LOT_ENTRY_INCOMPLETE
    elif contaminated:
        result["verdict"] = FOREIGN_DEVICE_IN_CHAMBER
    elif findings:
        result["verdict"] = CHAMBER_ENTRY_DEFICIENT
    else:
        result["verdict"] = CHAMBER_ENTRY_ACCEPTED
    return result
