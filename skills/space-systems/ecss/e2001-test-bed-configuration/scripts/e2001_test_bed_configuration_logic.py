#!/usr/bin/env python3
"""Multipactor test-bed minimum configuration check (ECSS-E-ST-20-01C 8.2).

Deterministic, offline, python3 standard library only. The procedure below is
a paraphrase of the clause intent into implementable logic; no standard text is
reproduced.

The bed is admissible only when five families of condition hold at once:
vacuum readiness, instrument calibration validity, rf-chain headroom above the
maximum applied power, an active electron-seeding source, and multipactor
detection coverage spanning both a global and a local method.
"""

from __future__ import annotations

import datetime
import math

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

#: Relative tolerance absorbing binary-floating-point representation error on
#: an exact-limit comparison. It never widens the engineering limit: a rating
#: that is physically equal to the requirement must not fail on the last bits.
REL_TOL = 1e-9

#: Element type -> family. Anything absent from this map is not part of the
#: clause 8.2 configuration record and is rejected.
ELEMENT_FAMILIES = {
    "vacuum-chamber": "vacuum-system",
    "turbomolecular-pump": "vacuum-system",
    "ion-pump": "vacuum-system",
    "roughing-pump": "vacuum-system",
    "rf-source": "rf-chain",
    "travelling-wave-tube-amplifier": "rf-chain",
    "solid-state-power-amplifier": "rf-chain",
    "circulator": "rf-chain",
    "directional-coupler": "rf-chain",
    "matched-load": "rf-chain",
    "power-meter": "instrumentation",
    "spectrum-analyser": "instrumentation",
    "network-analyser": "instrumentation",
    "vacuum-gauge": "instrumentation",
    "residual-gas-analyser": "instrumentation",
    "thermocouple": "instrumentation",
    "ultraviolet-lamp": "electron-seeding",
    "radioactive-source": "electron-seeding",
    "electron-gun": "electron-seeding",
    "forward-reverse-nulling": "detection-method",
    "third-harmonic-monitor": "detection-method",
    "close-to-carrier-noise": "detection-method",
    "phase-noise-monitor": "detection-method",
    "electron-probe": "detection-method",
}

#: Detection methods observing the device as a whole.
GLOBAL_DETECTION = frozenset(
    {
        "forward-reverse-nulling",
        "third-harmonic-monitor",
        "close-to-carrier-noise",
        "phase-noise-monitor",
    }
)

#: Detection methods observing the gap region directly.
LOCAL_DETECTION = frozenset({"electron-probe"})

FAMILIES = frozenset(ELEMENT_FAMILIES.values())


# ----------------------------------------------------------------------------
# Element categorization
# ----------------------------------------------------------------------------

def categorize_bed_element(element_type):
    """Return the clause 8.2 family of one bed element type.

    Raises ValueError on a blank or unrecognized element type: a record that
    names hardware the procedure does not know cannot be assessed.
    """
    if not isinstance(element_type, str):
        raise ValueError("element type must be a string, got %r" % (element_type,))
    key = element_type.strip().lower()
    if not key:
        raise ValueError("element type must not be blank")
    if key not in ELEMENT_FAMILIES:
        raise ValueError("unrecognized bed element type: %r" % (element_type,))
    return ELEMENT_FAMILIES[key]


def summarize_families(element_types):
    """Return {family: [element, ...]} for a sequence of element types."""
    if not isinstance(element_types, (list, tuple)):
        raise ValueError("element_types must be a list or tuple")
    if not element_types:
        raise ValueError("element_types must not be empty")
    summary = {family: [] for family in sorted(FAMILIES)}
    for element in element_types:
        summary[categorize_bed_element(element)].append(str(element).strip().lower())
    return summary


# ----------------------------------------------------------------------------
# Vacuum readiness
# ----------------------------------------------------------------------------

def check_vacuum_readiness(measured_pressure_pa, required_pressure_pa, bakeout_done):
    """Check the chamber holds at or below the required pressure level.

    Pressures are in pascal and must be strictly positive. An exact-limit
    measurement is compliant; the tolerance absorbs representation error only.
    """
    for name, value in (
        ("measured_pressure_pa", measured_pressure_pa),
        ("required_pressure_pa", required_pressure_pa),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a number, got %r" % (name, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % name)
        if float(value) <= 0.0:
            raise ValueError("%s must be strictly positive, got %r" % (name, value))
    if not isinstance(bakeout_done, bool):
        raise ValueError("bakeout_done must be a boolean, got %r" % (bakeout_done,))

    measured = float(measured_pressure_pa)
    required = float(required_pressure_pa)
    at_or_below = measured <= required or math.isclose(
        measured, required, rel_tol=REL_TOL
    )
    findings = []
    if not at_or_below:
        findings.append(
            "chamber pressure %.3e Pa exceeds required level %.3e Pa"
            % (measured, required)
        )
    if not bakeout_done:
        findings.append("no bake-out or equivalent outgassing treatment on record")
    return {
        "measured_pressure_pa": measured,
        "required_pressure_pa": required,
        "pressure_ok": at_or_below,
        "bakeout_done": bakeout_done,
        "compliant": not findings,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Calibration validity
# ----------------------------------------------------------------------------

def _parse_date(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO date (YYYY-MM-DD): %r" % (label, value))


def days_to_calibration_expiry(calibration_due, run_date):
    """Return days remaining between the planned run date and the due date.

    Zero means the certificate expires on the run date and is still valid;
    a negative value means it has already expired.
    """
    due = _parse_date(calibration_due, "calibration_due")
    run = _parse_date(run_date, "run_date")
    return (due - run).days


def check_instrument_calibration(instruments, run_date):
    """Check every measurement instrument is in calibration on the run date.

    ``instruments`` is a sequence of mappings with keys ``id``, ``type`` and
    ``calibration_due``. Instruments outside the instrumentation family are a
    record error and raise ValueError.
    """
    if not isinstance(instruments, (list, tuple)):
        raise ValueError("instruments must be a list or tuple")
    if not instruments:
        raise ValueError("instruments must not be empty: clause 8.2 needs measurements")
    _parse_date(run_date, "run_date")

    rows = []
    findings = []
    seen = set()
    for entry in instruments:
        if not isinstance(entry, dict):
            raise ValueError("each instrument must be a mapping, got %r" % (entry,))
        ident = entry.get("id")
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError("instrument entry missing a non-blank 'id'")
        ident = ident.strip()
        if ident in seen:
            raise ValueError("duplicate instrument id: %r" % (ident,))
        seen.add(ident)
        family = categorize_bed_element(entry.get("type"))
        if family != "instrumentation":
            raise ValueError(
                "instrument %r is family %r, not instrumentation" % (ident, family)
            )
        remaining = days_to_calibration_expiry(entry.get("calibration_due"), run_date)
        in_date = remaining >= 0
        if not in_date:
            findings.append(
                "instrument %s calibration expired %d day(s) before the run date"
                % (ident, -remaining)
            )
        rows.append(
            {
                "id": ident,
                "type": str(entry.get("type")).strip().lower(),
                "days_remaining": remaining,
                "in_date": in_date,
            }
        )
    return {
        "instruments": rows,
        "expired": [row["id"] for row in rows if not row["in_date"]],
        "compliant": not findings,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# RF chain sizing
# ----------------------------------------------------------------------------

def required_source_rating_w(max_applied_power_w, run_margin_db):
    """Return the source rating the rf-chain needs, in watt.

    The run-margin is a ratio expressed in decibel and is applied
    multiplicatively: rating = applied power * 10 ** (margin / 10).
    """
    if not isinstance(max_applied_power_w, (int, float)) or isinstance(
        max_applied_power_w, bool
    ):
        raise ValueError(
            "max_applied_power_w must be a number, got %r" % (max_applied_power_w,)
        )
    if not isinstance(run_margin_db, (int, float)) or isinstance(run_margin_db, bool):
        raise ValueError("run_margin_db must be a number, got %r" % (run_margin_db,))
    power = float(max_applied_power_w)
    margin = float(run_margin_db)
    if not math.isfinite(power) or power <= 0.0:
        raise ValueError(
            "max_applied_power_w must be finite and strictly positive, got %r"
            % (max_applied_power_w,)
        )
    if not math.isfinite(margin) or margin < 0.0:
        raise ValueError(
            "run_margin_db must be finite and non-negative, got %r" % (run_margin_db,)
        )
    return power * (10.0 ** (margin / 10.0))


def check_rf_chain_capability(source_rating_w, max_applied_power_w, run_margin_db):
    """Check the installed source covers applied power plus the run-margin."""
    if not isinstance(source_rating_w, (int, float)) or isinstance(
        source_rating_w, bool
    ):
        raise ValueError("source_rating_w must be a number, got %r" % (source_rating_w,))
    rating = float(source_rating_w)
    if not math.isfinite(rating) or rating <= 0.0:
        raise ValueError(
            "source_rating_w must be finite and strictly positive, got %r"
            % (source_rating_w,)
        )
    required = required_source_rating_w(max_applied_power_w, run_margin_db)
    sufficient = rating >= required or math.isclose(rating, required, rel_tol=REL_TOL)
    findings = []
    if not sufficient:
        findings.append(
            "rf-chain source rating %.4f W below required %.4f W "
            "(%.2f dB margin over %.4f W)"
            % (rating, required, float(run_margin_db), float(max_applied_power_w))
        )
    return {
        "source_rating_w": rating,
        "required_rating_w": required,
        "shortfall_w": max(0.0, required - rating),
        "compliant": sufficient,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Electron seeding
# ----------------------------------------------------------------------------

def check_electron_seeding(sources):
    """Check at least one active electron-seeding source is aimed at the gap."""
    if not isinstance(sources, (list, tuple)):
        raise ValueError("sources must be a list or tuple")
    active = []
    for entry in sources:
        if not isinstance(entry, dict):
            raise ValueError("each seeding source must be a mapping, got %r" % (entry,))
        family = categorize_bed_element(entry.get("type"))
        if family != "electron-seeding":
            raise ValueError(
                "source %r is family %r, not electron-seeding"
                % (entry.get("type"), family)
            )
        state = entry.get("active")
        if not isinstance(state, bool):
            raise ValueError("seeding source 'active' must be a boolean, got %r" % (state,))
        aimed = entry.get("aimed_at_gap")
        if not isinstance(aimed, bool):
            raise ValueError(
                "seeding source 'aimed_at_gap' must be a boolean, got %r" % (aimed,)
            )
        if state and aimed:
            active.append(str(entry.get("type")).strip().lower())
    findings = []
    if not active:
        findings.append(
            "no active electron-seeding source directed at the device gap region"
        )
    return {
        "active_sources": active,
        "compliant": not findings,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Detection coverage
# ----------------------------------------------------------------------------

def check_detection_coverage(methods, expired_instruments=()):
    """Check detection spans a global and a local multipactor-detection method.

    A method whose supporting instrument appears in ``expired_instruments`` is
    not counted: an out-of-calibration instrument cannot carry a verdict.
    """
    if not isinstance(methods, (list, tuple)):
        raise ValueError("methods must be a list or tuple")
    if not isinstance(expired_instruments, (list, tuple, set, frozenset)):
        raise ValueError("expired_instruments must be a sequence or set")
    expired = {str(i).strip() for i in expired_instruments}

    global_ok = []
    local_ok = []
    discounted = []
    for entry in methods:
        if not isinstance(entry, dict):
            raise ValueError("each detection method must be a mapping, got %r" % (entry,))
        kind = entry.get("type")
        family = categorize_bed_element(kind)
        if family != "detection-method":
            raise ValueError(
                "method %r is family %r, not detection-method" % (kind, family)
            )
        key = str(kind).strip().lower()
        instrument = entry.get("instrument_id")
        if instrument is not None and not isinstance(instrument, str):
            raise ValueError("detection 'instrument_id' must be a string or None")
        if instrument is not None and instrument.strip() in expired:
            discounted.append(key)
            continue
        if key in GLOBAL_DETECTION:
            global_ok.append(key)
        elif key in LOCAL_DETECTION:
            local_ok.append(key)

    findings = []
    if not global_ok:
        findings.append("no global multipactor-detection method available")
    if not local_ok:
        findings.append("no local multipactor-detection method available")
    return {
        "global_methods": global_ok,
        "local_methods": local_ok,
        "discounted": discounted,
        "compliant": not findings,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Aggregate assessment
# ----------------------------------------------------------------------------

_REQUIRED_KEYS = (
    "elements",
    "measured_pressure_pa",
    "required_pressure_pa",
    "bakeout_done",
    "instruments",
    "run_date",
    "source_rating_w",
    "max_applied_power_w",
    "run_margin_db",
    "seeding_sources",
    "detection_methods",
)


def assess_test_bed_configuration(record):
    """Run every clause 8.2 check over one bed record and aggregate findings."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    missing = [key for key in _REQUIRED_KEYS if key not in record]
    if missing:
        raise ValueError("bed record missing keys: %s" % ", ".join(sorted(missing)))

    families = summarize_families(record["elements"])
    vacuum = check_vacuum_readiness(
        record["measured_pressure_pa"],
        record["required_pressure_pa"],
        record["bakeout_done"],
    )
    calibration = check_instrument_calibration(record["instruments"], record["run_date"])
    rf_chain = check_rf_chain_capability(
        record["source_rating_w"],
        record["max_applied_power_w"],
        record["run_margin_db"],
    )
    seeding = check_electron_seeding(record["seeding_sources"])
    detection = check_detection_coverage(
        record["detection_methods"], calibration["expired"]
    )

    findings = []
    for label, block in (
        ("vacuum", vacuum),
        ("calibration", calibration),
        ("rf-chain", rf_chain),
        ("electron-seeding", seeding),
        ("detection", detection),
    ):
        for item in block["findings"]:
            findings.append("%s: %s" % (label, item))

    return {
        "families": families,
        "vacuum": vacuum,
        "calibration": calibration,
        "rf_chain": rf_chain,
        "seeding": seeding,
        "detection": detection,
        "compliant": not findings,
        "findings": findings,
        "verdict": "BED-READY" if not findings else "BED-NOT-READY",
    }
