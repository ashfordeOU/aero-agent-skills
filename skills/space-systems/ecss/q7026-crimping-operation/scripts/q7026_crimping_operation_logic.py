#!/usr/bin/env python3
"""The crimp cycle itself: tool setup, full cycle, and compression.

Anchor: ECSS-Q-ST-70-26 Process clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The cycle is short and it is not adjustable. What decides whether a
crimp is a cold weld or a mechanical clamp is settled before the handles
move and cannot be recovered afterwards:

tooling        the die and the positioner belong to the contact part
               number, not to the wire. The wrong die closes the wrong
               profile and the resulting height means nothing.
selector       the selector or indent setting belongs to the wire gauge
               inside that contact. One setting across a mixed-gauge
               harness over-crimps the fine wire and under-crimps the
               heavy one.
calibration    a tool is due on a date and on a cycle count, whichever
               arrives first. Either lapsing voids the crimps taken
               after it, because the compression they applied is
               unknown rather than wrong.
full cycle     a ratchet tool releases only when the cycle completes. A
               cycle interrupted and released by hand applied part of
               the compression, and the crimp looks finished.
one cycle      a barrel crimped twice is work-hardened along a second
               profile. More compression is not better compression.
compression    the resulting height has a target and a two-sided
               tolerance. Under the band the barrel never closed and the
               joint is mechanical; over it the barrel has been driven
               into the strands and cut them.

Dispositions rank accept < remake < reject. Remake means cutting the
contact off and re-terminating, which needs wire length; reject is what
is left when there is none, or when the process record cannot support
any disposition at all.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CRIMP_ACCEPT = "accept"
CRIMP_REMAKE = "remake"
CRIMP_REJECT = "reject"

_RANK = {
    CRIMP_ACCEPT: 0,
    CRIMP_REMAKE: 1,
    CRIMP_REJECT: 2,
}

COMPRESSION_IN_BAND = "in-band"
COMPRESSION_UNDER = "under-crimp"
COMPRESSION_OVER = "over-crimp"

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


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


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


def _worst(dispositions):
    worst = CRIMP_ACCEPT
    for disposition in dispositions:
        if _RANK[disposition] > _RANK[worst]:
            worst = disposition
    return worst


def validate_setup_table(table):
    """Normalise the per-contact tooling and compression table.

    Keyed by contact part number, because the die and positioner belong
    to the contact. Each contact carries the gauges it accepts, and each
    gauge its own selector setting and crimp height target.
    """
    if not isinstance(table, dict) or not table:
        raise ValueError("setup table must be a non-empty mapping")
    normalised = {}
    for part, entry in table.items():
        _require_text("contact part", part)
        if not isinstance(entry, dict):
            raise ValueError("contact %s entry must be a mapping" % part)
        die = _require_text("contact %s die_part" % part, entry.get("die_part"))
        positioner = _require_text(
            "contact %s positioner" % part, entry.get("positioner")
        )
        gauges = entry.get("gauges")
        if not isinstance(gauges, dict) or not gauges:
            raise ValueError("contact %s must tabulate at least one gauge" % part)
        gauge_entries = {}
        for gauge, spec in gauges.items():
            _require_text("contact %s gauge key" % part, gauge)
            if not isinstance(spec, dict):
                raise ValueError(
                    "contact %s gauge %s spec must be a mapping" % (part, gauge)
                )
            selector = spec.get("selector")
            if isinstance(selector, bool) or not isinstance(selector, int):
                raise ValueError(
                    "contact %s gauge %s selector must be an integer setting"
                    % (part, gauge)
                )
            target = _require_positive(
                "contact %s gauge %s height_target_mm" % (part, gauge),
                spec.get("height_target_mm"),
            )
            tol = _require_positive(
                "contact %s gauge %s height_tolerance_mm" % (part, gauge),
                spec.get("height_tolerance_mm"),
            )
            if tol >= target:
                raise ValueError(
                    "contact %s gauge %s tolerance %g reaches the %g mm target, so "
                    "no height could ever be out of band" % (part, gauge, tol, target)
                )
            gauge_entries[gauge] = {
                "gauge": gauge,
                "selector": selector,
                "height_target_mm": target,
                "height_tolerance_mm": tol,
                "height_min_mm": target - tol,
                "height_max_mm": target + tol,
            }
        normalised[part] = {
            "contact": part,
            "die_part": die,
            "positioner": positioner,
            "gauges": gauge_entries,
        }
    return normalised


def _looks_normalised(table):
    return (
        isinstance(table, dict)
        and bool(table)
        and all(
            isinstance(entry, dict) and "die_part" in entry and "contact" in entry
            for entry in table.values()
        )
    )


def lookup_setup(table, contact, gauge):
    """Return the (contact, gauge) setup entry; nothing is interpolated."""
    normalised = table if _looks_normalised(table) else validate_setup_table(table)
    if contact not in normalised:
        raise ValueError(
            "contact %r is not tabulated (have %s)"
            % (contact, ", ".join(sorted(normalised)))
        )
    entry = normalised[contact]
    if gauge not in entry["gauges"]:
        raise ValueError(
            "contact %s does not accept gauge %r (accepts %s); a selector setting "
            "is not interpolated between gauges"
            % (contact, gauge, ", ".join(sorted(entry["gauges"])))
        )
    return entry, entry["gauges"][gauge]


def evaluate_tooling(entry, die_part, positioner):
    """Check the die and positioner fitted against the ones the contact needs."""
    die = _require_text("die_part", die_part)
    pos = _require_text("positioner", positioner)
    findings = []
    die_ok = die == entry["die_part"]
    pos_ok = pos == entry["positioner"]
    if not die_ok:
        findings.append(
            "die %s is fitted where contact %s needs %s; the profile closed is "
            "not the profile the height band describes"
            % (die, entry["contact"], entry["die_part"])
        )
    if not pos_ok:
        findings.append(
            "positioner %s is fitted where contact %s needs %s, so the crimp "
            "lands at the wrong position along the barrel"
            % (pos, entry["contact"], entry["positioner"])
        )
    return {
        "die_part": die,
        "positioner": positioner,
        "die_correct": die_ok,
        "positioner_correct": pos_ok,
        "correct": die_ok and pos_ok,
        "findings": findings,
    }


def evaluate_selector(setting, gauge_entry):
    """Check the selector or indent setting against the one for this gauge."""
    if isinstance(setting, bool) or not isinstance(setting, int):
        raise ValueError("selector setting must be an integer, got %r" % (setting,))
    expected = gauge_entry["selector"]
    correct = setting == expected
    findings = []
    if not correct:
        findings.append(
            "selector is set to %d where gauge %s needs %d; one setting across a "
            "mixed-gauge harness cannot be right for both"
            % (setting, gauge_entry["gauge"], expected)
        )
    return {
        "setting": setting,
        "expected": expected,
        "correct": correct,
        "findings": findings,
    }


def evaluate_calibration(days_remaining, cycles_since_calibration, cycle_interval):
    """A tool is due on a date and on a cycle count, whichever comes first."""
    days = _require_number("days_remaining", days_remaining)
    cycles = _require_count("cycles_since_calibration", cycles_since_calibration)
    interval = _require_count("cycle_interval", cycle_interval)
    if interval <= 0:
        raise ValueError("cycle_interval must be a positive number of cycles")
    # A tool due today is still in calibration: the comparison absorbs the
    # representation error of a date arithmetic that lands on zero.
    date_current = _at_least(days, 0.0)
    cycles_current = cycles <= interval
    findings = []
    if not date_current:
        findings.append(
            "tool calibration lapsed %.1f days ago" % (-days)
        )
    if not cycles_current:
        findings.append(
            "tool has run %d cycles against a %d cycle interval" % (cycles, interval)
        )
    return {
        "days_remaining": days,
        "cycles_since_calibration": cycles,
        "cycle_interval": interval,
        "cycles_remaining": interval - cycles,
        "date_current": date_current,
        "cycles_current": cycles_current,
        "current": date_current and cycles_current,
        "findings": findings,
    }


def authorize_cycle(entry, gauge_entry, setup):
    """Decide whether the cycle may be run at all, before the handles move."""
    if not isinstance(setup, dict):
        raise ValueError("setup must be a mapping, got %r" % (setup,))
    tooling = evaluate_tooling(entry, setup.get("die_part"), setup.get("positioner"))
    selector = evaluate_selector(setup.get("selector_setting"), gauge_entry)
    calibration = evaluate_calibration(
        setup.get("calibration_days_remaining"),
        setup.get("cycles_since_calibration", 0),
        setup.get("cycle_interval"),
    )
    blockers = []
    blockers.extend("tooling: %s" % text for text in tooling["findings"])
    blockers.extend("selector: %s" % text for text in selector["findings"])
    blockers.extend("calibration: %s" % text for text in calibration["findings"])
    return {
        "authorized": not blockers,
        "tooling": tooling,
        "selector": selector,
        "calibration": calibration,
        "blockers": blockers,
    }


def evaluate_cycle_completion(cycle_completed, crimps_on_barrel=1, ratchet_fitted=True):
    """A ratchet tool releases on completion; a barrel takes exactly one cycle."""
    completed = _require_flag("cycle_completed", cycle_completed)
    ratchet = _require_flag("ratchet_fitted", ratchet_fitted)
    crimps = _require_count("crimps_on_barrel", crimps_on_barrel)
    findings = []
    dispositions = [CRIMP_ACCEPT]
    if crimps == 0:
        raise ValueError("a barrel with no crimp on it has no cycle to grade")
    if not completed:
        dispositions.append(CRIMP_REMAKE)
        findings.append(
            "the cycle was released before it completed, so only part of the "
            "compression was applied and the crimp looks finished"
        )
    if crimps > 1:
        dispositions.append(CRIMP_REMAKE)
        findings.append(
            "%d cycles were run on one barrel; the second profile work-hardens "
            "the first and more compression is not better compression" % crimps
        )
    if not ratchet:
        dispositions.append(CRIMP_REMAKE)
        findings.append(
            "no ratchet was fitted, so nothing enforced the full cycle and "
            "completion rests on the operator's hand"
        )
    return {
        "cycle_completed": completed,
        "crimps_on_barrel": crimps,
        "ratchet_fitted": ratchet,
        "disposition": _worst(dispositions),
        "findings": findings,
    }


def evaluate_compression(height_mm, gauge_entry):
    """Grade the resulting crimp height against its two-sided band."""
    height = _require_positive("height_mm", height_mm)
    low = gauge_entry["height_min_mm"]
    high = gauge_entry["height_max_mm"]
    target = gauge_entry["height_target_mm"]
    under = not _at_most(height, high)
    over = not _at_least(height, low)
    findings = []
    if over:
        state = COMPRESSION_OVER
        findings.append(
            "crimp height %.3f mm is below the %.3f mm floor; the barrel has been "
            "driven into the strands" % (height, low)
        )
    elif under:
        state = COMPRESSION_UNDER
        findings.append(
            "crimp height %.3f mm is above the %.3f mm ceiling; the barrel never "
            "closed and the joint is mechanical rather than a cold weld"
            % (height, high)
        )
    else:
        state = COMPRESSION_IN_BAND
    return {
        "height_mm": height,
        "target_mm": target,
        "band_min_mm": low,
        "band_max_mm": high,
        "deviation_mm": height - target,
        "state": state,
        "disposition": CRIMP_ACCEPT if state == COMPRESSION_IN_BAND else CRIMP_REMAKE,
        "findings": findings,
    }


def perform_crimp(job, table):
    """Authorize, run and grade one crimp cycle end to end."""
    if not isinstance(job, dict):
        raise ValueError("job must be a mapping, got %r" % (job,))
    entry, gauge_entry = lookup_setup(table, job.get("contact"), job.get("gauge"))
    authorization = authorize_cycle(entry, gauge_entry, job)
    completion = evaluate_cycle_completion(
        job.get("cycle_completed", True),
        crimps_on_barrel=job.get("crimps_on_barrel", 1),
        ratchet_fitted=job.get("ratchet_fitted", True),
    )
    compression = evaluate_compression(job.get("crimp_height_mm"), gauge_entry)
    dispositions = [completion["disposition"], compression["disposition"]]
    findings = []
    if not authorization["authorized"]:
        dispositions.append(CRIMP_REMAKE)
        findings.extend(
            "authorization: %s" % text for text in authorization["blockers"]
        )
    findings.extend("cycle: %s" % text for text in completion["findings"])
    findings.extend("compression: %s" % text for text in compression["findings"])
    disposition = _worst(dispositions)
    if disposition == CRIMP_REMAKE:
        margin = _require_non_negative("wire_margin_mm", job.get("wire_margin_mm", 0.0))
        needed = _require_non_negative(
            "remake_margin_mm", job.get("remake_margin_mm", 0.0)
        )
        if not _at_least(margin, needed):
            disposition = CRIMP_REJECT
            findings.append(
                "remake: only %.2f mm of wire margin remains against the %.2f mm a "
                "re-termination needs" % (margin, needed)
            )
    return {
        "identifier": job.get("identifier", "unidentified"),
        "contact": entry["contact"],
        "gauge": gauge_entry["gauge"],
        "authorized": authorization["authorized"],
        "authorization": authorization,
        "cycle": completion,
        "compression": compression,
        "disposition": disposition,
        "findings": findings,
    }


def summarize_run(run):
    """Roll a crimping run up into one disposition with its yield."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (run,))
    table = validate_setup_table(run.get("setup_table"))
    jobs = run.get("crimps")
    if not isinstance(jobs, (list, tuple)) or not jobs:
        raise ValueError("run must carry a non-empty crimps sequence")
    declared = _require_count(
        "declared_crimp_count", run.get("declared_crimp_count", len(jobs))
    )
    if declared < len(jobs):
        raise ValueError(
            "%d crimps were recorded against a declared population of %d"
            % (len(jobs), declared)
        )
    results = [perform_crimp(job, table) for job in jobs]
    counts = {CRIMP_ACCEPT: 0, CRIMP_REMAKE: 0, CRIMP_REJECT: 0}
    for result in results:
        counts[result["disposition"]] += 1
    unrecorded = declared - len(results)
    return {
        "declared_crimp_count": declared,
        "recorded_crimp_count": len(results),
        "unrecorded_crimp_count": unrecorded,
        "record_complete": unrecorded == 0,
        "accepted": counts[CRIMP_ACCEPT],
        "remake": counts[CRIMP_REMAKE],
        "rejected": counts[CRIMP_REJECT],
        "first_pass_yield": counts[CRIMP_ACCEPT] / len(results),
        "unauthorized_cycles": sum(1 for r in results if not r["authorized"]),
        "worst_disposition": _worst(r["disposition"] for r in results),
        "not_accepted": [
            r["identifier"] for r in results if r["disposition"] != CRIMP_ACCEPT
        ],
        "crimps": results,
    }
