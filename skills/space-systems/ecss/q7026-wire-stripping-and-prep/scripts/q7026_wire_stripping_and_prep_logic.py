#!/usr/bin/env python3
"""Stripped wire end preparation for a high-reliability crimped joint.

Anchor: ECSS-Q-ST-70-26 Preparation clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A crimp is a cold weld between the barrel and the strands, so every
defect that will ever limit the joint is already present in the wire end
before the tool closes. Five things are graded here:

strip length     the exposed conductor has to sit inside the band for
                 its own gauge. Short leaves the barrel unfilled; long
                 leaves bare conductor outside the barrel that neither
                 the grip nor the insulation supports.
strand integrity a strand nicked by the blade will work-harden and part
                 in service; a strand severed or never cut free is
                 conductor that was removed from the joint. The two are
                 counted separately against separate allowances.
conductor form   a birdcaged bundle does not enter the barrel round, and
                 a contaminated or oxidised conductor does not cold-weld
                 to it. Both are recoverable; neither is ignorable.
tinning          a solder-tinned conductor is not crimped. The solder
                 creeps under the barrel pressure and the joint relaxes.
process          the stripping method has to be one the process
                 qualification covers and the tool has to be in
                 calibration, or nothing measured afterwards is evidence.

Dispositions rank accept < rework < reject. Rework is only offered when
the wire has enough length left to be cut back and stripped again.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STRIP_METHODS = (
    "thermal",
    "mechanical-die",
    "mechanical-blade",
    "abrasive",
)

DISPOSITION_ACCEPT = "accept"
DISPOSITION_REWORK = "rework"
DISPOSITION_REJECT = "reject"

_RANK = {
    DISPOSITION_ACCEPT: 0,
    DISPOSITION_REWORK: 1,
    DISPOSITION_REJECT: 2,
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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A strip length specified to land exactly on the band edge can
    evaluate a few units in the last place below it after a unit
    conversion. The limit is never relaxed; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = DISPOSITION_ACCEPT
    for disposition in dispositions:
        if _RANK[disposition] > _RANK[worst]:
            worst = disposition
    return worst


def validate_gauge_table(table):
    """Normalise the per-gauge preparation table and refuse an unusable one.

    Every number in this clause is per gauge: strip band, strand count
    and the two damage allowances all move with the wire, so a table
    that is short of any of them cannot grade a wire end.
    """
    if not isinstance(table, dict) or not table:
        raise ValueError("gauge table must be a non-empty mapping of gauge to entry")
    normalised = {}
    for gauge, entry in table.items():
        if not isinstance(gauge, str) or not gauge.strip():
            raise ValueError("gauge key must be a non-empty string, got %r" % (gauge,))
        if not isinstance(entry, dict):
            raise ValueError("gauge %s entry must be a mapping, got %r" % (gauge, entry))
        low = _require_positive("gauge %s strip_min_mm" % gauge, entry.get("strip_min_mm"))
        high = _require_positive("gauge %s strip_max_mm" % gauge, entry.get("strip_max_mm"))
        if high < low:
            raise ValueError(
                "gauge %s strip band is inverted: max %g below min %g" % (gauge, high, low)
            )
        strands = _require_count("gauge %s strand_count" % gauge, entry.get("strand_count"))
        if strands <= 0:
            raise ValueError("gauge %s strand_count must be positive" % gauge)
        nicked = _require_count(
            "gauge %s max_nicked_strands" % gauge, entry.get("max_nicked_strands", 0)
        )
        severed = _require_count(
            "gauge %s max_severed_strands" % gauge, entry.get("max_severed_strands", 0)
        )
        if nicked >= strands:
            raise ValueError(
                "gauge %s allows %d nicked strands of %d; an allowance that reaches "
                "the strand count is not an allowance" % (gauge, nicked, strands)
            )
        if severed >= strands:
            raise ValueError(
                "gauge %s allows %d severed strands of %d; an allowance that reaches "
                "the strand count is not an allowance" % (gauge, severed, strands)
            )
        normalised[gauge] = {
            "gauge": gauge,
            "strip_min_mm": low,
            "strip_max_mm": high,
            "strand_count": strands,
            "max_nicked_strands": nicked,
            "max_severed_strands": severed,
        }
    return normalised


def lookup_gauge(table, gauge):
    """Return the entry for one gauge; an untabulated gauge has no band.

    The band for a gauge sitting between two tabulated ones is not the
    average of theirs, so nothing is interpolated here.
    """
    normalised = table if _looks_normalised(table) else validate_gauge_table(table)
    if gauge not in normalised:
        raise ValueError(
            "gauge %r is not tabulated (have %s); a band is not interpolated"
            % (gauge, ", ".join(sorted(normalised)))
        )
    return normalised[gauge]


def _looks_normalised(table):
    return (
        isinstance(table, dict)
        and bool(table)
        and all(
            isinstance(entry, dict) and "strip_min_mm" in entry and "gauge" in entry
            for entry in table.values()
        )
    )


def evaluate_strip_length(length_mm, entry, wire_margin_mm=0.0, min_rework_margin_mm=0.0):
    """Grade the exposed conductor length against the band for its gauge."""
    length = _require_non_negative("length_mm", length_mm)
    margin = _require_non_negative("wire_margin_mm", wire_margin_mm)
    needed = _require_non_negative("min_rework_margin_mm", min_rework_margin_mm)
    low = entry["strip_min_mm"]
    high = entry["strip_max_mm"]
    short = not _at_least(length, low)
    long_ = not _at_most(length, high)
    findings = []
    if short:
        findings.append(
            "exposed length %.2f mm is below the %.2f mm minimum for gauge %s; "
            "the barrel will not fill" % (length, low, entry["gauge"])
        )
    if long_:
        findings.append(
            "exposed length %.2f mm is above the %.2f mm maximum for gauge %s; "
            "bare conductor will sit outside the barrel" % (length, high, entry["gauge"])
        )
    if short or long_:
        reworkable = _at_least(margin, needed)
        disposition = DISPOSITION_REWORK if reworkable else DISPOSITION_REJECT
        if not reworkable:
            findings.append(
                "only %.2f mm of wire margin remains against the %.2f mm a re-strip "
                "needs, so the end cannot be cut back" % (margin, needed)
            )
    else:
        disposition = DISPOSITION_ACCEPT
    span = high - low
    position = (length - low) / span if span > 0.0 else 0.0
    return {
        "length_mm": length,
        "band_min_mm": low,
        "band_max_mm": high,
        "below_minimum": short,
        "above_maximum": long_,
        "band_position": position,
        "disposition": disposition,
        "findings": findings,
    }


def evaluate_strand_damage(entry, strands_in_bundle, nicked=0, severed=0):
    """Count nicked and severed strands against their separate allowances."""
    present = _require_count("strands_in_bundle", strands_in_bundle)
    nicked = _require_count("nicked", nicked)
    severed = _require_count("severed", severed)
    expected = entry["strand_count"]
    findings = []
    if present != expected:
        raise ValueError(
            "gauge %s carries %d strands but %d were counted in the bundle"
            % (entry["gauge"], expected, present)
        )
    if nicked + severed > expected:
        raise ValueError(
            "%d nicked plus %d severed exceeds the %d strands the gauge carries"
            % (nicked, severed, expected)
        )
    disposition = DISPOSITION_ACCEPT
    if nicked > entry["max_nicked_strands"]:
        disposition = DISPOSITION_REJECT
        findings.append(
            "%d nicked strands against an allowance of %d; a nicked strand "
            "work-hardens and parts later" % (nicked, entry["max_nicked_strands"])
        )
    if severed > entry["max_severed_strands"]:
        disposition = DISPOSITION_REJECT
        findings.append(
            "%d severed strands against an allowance of %d; severed conductor is "
            "current capacity the joint never gets"
            % (severed, entry["max_severed_strands"])
        )
    intact = expected - nicked - severed
    return {
        "strand_count": expected,
        "nicked": nicked,
        "severed": severed,
        "intact": intact,
        "intact_fraction": intact / expected,
        "disposition": disposition,
        "findings": findings,
    }


def evaluate_conductor_condition(
    birdcaged=False, insulation_damaged=False, contaminated=False, tinned=False
):
    """Grade the form and cleanliness of the exposed conductor."""
    birdcaged = _require_flag("birdcaged", birdcaged)
    insulation_damaged = _require_flag("insulation_damaged", insulation_damaged)
    contaminated = _require_flag("contaminated", contaminated)
    tinned = _require_flag("tinned", tinned)
    findings = []
    dispositions = [DISPOSITION_ACCEPT]
    if tinned:
        dispositions.append(DISPOSITION_REJECT)
        findings.append(
            "conductor is solder-tinned; solder creeps under barrel pressure and "
            "the crimp relaxes, so a tinned end is not crimped"
        )
    if birdcaged:
        dispositions.append(DISPOSITION_REWORK)
        findings.append(
            "conductor is birdcaged and will not enter the barrel round; re-lay "
            "the strands before insertion"
        )
    if contaminated:
        dispositions.append(DISPOSITION_REWORK)
        findings.append(
            "conductor is contaminated or oxidised, which prevents the cold weld"
        )
    if insulation_damaged:
        dispositions.append(DISPOSITION_REJECT)
        findings.append(
            "insulation is cut, melted or split beyond the strip zone, so the "
            "damage is on wire that stays in the harness"
        )
    return {
        "birdcaged": birdcaged,
        "insulation_damaged": insulation_damaged,
        "contaminated": contaminated,
        "tinned": tinned,
        "disposition": _worst(dispositions),
        "findings": findings,
    }


def evaluate_process(method, qualified_methods, calibration_days_remaining):
    """Refuse an unqualified stripping method and a lapsed tool calibration."""
    _require_choice("method", method, STRIP_METHODS)
    if not isinstance(qualified_methods, (list, tuple)) or not qualified_methods:
        raise ValueError("qualified_methods must be a non-empty sequence")
    for name in qualified_methods:
        _require_choice("qualified method", name, STRIP_METHODS)
    days = _require_number("calibration_days_remaining", calibration_days_remaining)
    findings = []
    dispositions = [DISPOSITION_ACCEPT]
    qualified = method in qualified_methods
    if not qualified:
        dispositions.append(DISPOSITION_REJECT)
        findings.append(
            "stripping method %s is outside the qualified set (%s)"
            % (method, ", ".join(qualified_methods))
        )
    # A tool due today is still in calibration: the comparison absorbs the
    # representation error of a date arithmetic that lands on zero.
    calibration_current = _at_least(days, 0.0)
    if not calibration_current:
        dispositions.append(DISPOSITION_REJECT)
        findings.append(
            "stripping tool calibration lapsed %.1f days ago, so nothing measured "
            "off this end is evidence" % (-days)
        )
    return {
        "method": method,
        "method_qualified": qualified,
        "calibration_days_remaining": days,
        "calibration_current": calibration_current,
        "disposition": _worst(dispositions),
        "findings": findings,
    }


def assess_wire_end(end, table):
    """Full preparation disposition for one stripped wire end."""
    if not isinstance(end, dict):
        raise ValueError("end must be a mapping, got %r" % (end,))
    normalised = validate_gauge_table(table) if not _looks_normalised(table) else table
    entry = lookup_gauge(normalised, end.get("gauge"))
    length = evaluate_strip_length(
        end.get("strip_length_mm"),
        entry,
        wire_margin_mm=end.get("wire_margin_mm", 0.0),
        min_rework_margin_mm=end.get("min_rework_margin_mm", 0.0),
    )
    strands = evaluate_strand_damage(
        entry,
        end.get("strands_in_bundle"),
        nicked=end.get("nicked", 0),
        severed=end.get("severed", 0),
    )
    condition = evaluate_conductor_condition(
        birdcaged=end.get("birdcaged", False),
        insulation_damaged=end.get("insulation_damaged", False),
        contaminated=end.get("contaminated", False),
        tinned=end.get("tinned", False),
    )
    process = evaluate_process(
        end.get("method"),
        end.get("qualified_methods"),
        end.get("calibration_days_remaining"),
    )
    parts = {
        "strip_length": length,
        "strand_damage": strands,
        "conductor_condition": condition,
        "process": process,
    }
    disposition = _worst(part["disposition"] for part in parts.values())
    driving = sorted(
        name
        for name, part in parts.items()
        if _RANK[part["disposition"]] == _RANK[disposition]
        and disposition != DISPOSITION_ACCEPT
    )
    findings = []
    for name in ("strip_length", "strand_damage", "conductor_condition", "process"):
        findings.extend("%s: %s" % (name, text) for text in parts[name]["findings"])
    return {
        "identifier": end.get("identifier", "unidentified"),
        "gauge": entry["gauge"],
        "disposition": disposition,
        "driving_checks": driving,
        "strip_length": length,
        "strand_damage": strands,
        "conductor_condition": condition,
        "process": process,
        "findings": findings,
    }


def assess_lot(lot):
    """Roll a prepared lot of wire ends up into one disposition."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    table = validate_gauge_table(lot.get("gauge_table"))
    ends = lot.get("ends")
    if not isinstance(ends, (list, tuple)) or not ends:
        raise ValueError("lot must carry a non-empty ends sequence")
    declared = lot.get("declared_end_count", len(ends))
    declared = _require_count("declared_end_count", declared)
    if declared < len(ends):
        raise ValueError(
            "%d ends were recorded against a declared population of %d"
            % (len(ends), declared)
        )
    results = [assess_wire_end(end, table) for end in ends]
    counts = {
        DISPOSITION_ACCEPT: 0,
        DISPOSITION_REWORK: 0,
        DISPOSITION_REJECT: 0,
    }
    for result in results:
        counts[result["disposition"]] += 1
    worst = _worst(result["disposition"] for result in results)
    unrecorded = declared - len(ends)
    return {
        "declared_end_count": declared,
        "recorded_end_count": len(results),
        "unrecorded_end_count": unrecorded,
        "record_complete": unrecorded == 0,
        "accepted": counts[DISPOSITION_ACCEPT],
        "rework": counts[DISPOSITION_REWORK],
        "rejected": counts[DISPOSITION_REJECT],
        "worst_disposition": worst,
        "not_accepted": [
            result["identifier"]
            for result in results
            if result["disposition"] != DISPOSITION_ACCEPT
        ],
        "ends": results,
    }
