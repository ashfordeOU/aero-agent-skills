#!/usr/bin/env python3
"""Crimped wire terminations against the accepted crimping workmanship standard.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.15. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A crimp is a permanent cold weld made by deforming a barrel onto a
stranded conductor. Nothing about it can be judged in the abstract: the
compression that makes a sound joint on one gauge crushes the next one,
so the numbers that matter -- the crimp height band for the gauge, the
strand count the gauge carries, the pull-out force the joint has to
hold -- live in a crimping workmanship standard, and that standard is
only an authority for this clause once the customer has accepted it.

Four things are derived per termination:

    compression   the measured crimp height against the band the
                  standard tabulates for that gauge
    conductor     the strands that reached the barrel, the strands cut
                  or nicked getting there, and any brushed outside it
    features      bell mouth, insulation support, insulation trapped in
                  the barrel, conductor visible at the inspection window
    strength      the pull-out force, where the termination was in the
                  pull-test sample

A gauge the standard does not tabulate is refused rather than
interpolated: the band for a gauge between two tabulated ones is not the
average of their bands, and inventing one grades the joint against a
number nobody accepted.

Dispositions are accept, rework -- meaning cut back and re-terminate,
since a crimp cannot be adjusted -- and reject. The allowance set below
is a declared project allowance set, not a physical constant; a project
may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
CRIMP_DISPOSITIONS = (ACCEPT, REWORK, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

SUPPORT_CORRECT = "correct"
SUPPORT_LOOSE = "loose"
SUPPORT_MISSING = "missing"
INSULATION_SUPPORT_STATES = (SUPPORT_CORRECT, SUPPORT_LOOSE, SUPPORT_MISSING)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

DEFAULT_CRIMPING_ALLOWANCES = {
    "max_strand_loss_fraction": 0.0,
    "max_nicked_strand_fraction": 0.05,
    "max_brush_strands": 0,
    "max_affected_crimp_fraction": 0.05,
    "min_pull_test_fraction": 0.10,
    "rework_margin_factor": 2.0,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    count = _require_count(name, value)
    if count == 0:
        raise ValueError("%s must be greater than zero" % name)
    return count


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An allowance is a product of a declared fraction and a counted
    number of strands or terminations, and a crimp height sits against a
    tabulated band edge, so a value landing exactly on its limit can
    evaluate a few units in the last place above it. The limit is never
    raised; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit under the same representation tolerance."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_crimping_allowances(allowances):
    """Check a crimping allowance set is complete and self-consistent."""
    if not isinstance(allowances, dict):
        raise ValueError("allowances must be a mapping, got %r" % (allowances,))
    for key in (
        "max_strand_loss_fraction",
        "max_nicked_strand_fraction",
        "max_affected_crimp_fraction",
        "min_pull_test_fraction",
    ):
        _require_fraction("allowances %s" % key, allowances.get(key))
    _require_count("allowances max_brush_strands", allowances.get("max_brush_strands"))
    factor = allowances.get("rework_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "allowances rework_margin_factor must be at least one, got %r" % (factor,)
        )
    if (
        allowances["max_strand_loss_fraction"]
        > allowances["max_nicked_strand_fraction"]
    ):
        raise ValueError(
            "allowances permit a larger fraction of strands missing from the "
            "barrel than of strands nicked inside it; a strand that never "
            "reached the barrel is the worse of the pair, so the two "
            "allowances contradict each other"
        )
    return allowances


def validate_crimping_standard(standard):
    """Check the crimping workmanship standard the inspection answers to.

    The clause grades a termination against a standard the customer has
    accepted. A standard with no recorded acceptance is refused here
    rather than applied and footnoted, because a disposition taken
    against it is not evidence of anything the customer agreed to.
    """
    if not isinstance(standard, dict):
        raise ValueError("standard must be a mapping, got %r" % (standard,))
    _require_text("standard_id", standard.get("standard_id"))
    _require_text("standard revision", standard.get("revision"))
    accepted = standard.get("customer_accepted")
    if not isinstance(accepted, bool):
        raise ValueError(
            "customer_accepted must be true or false, got %r" % (accepted,)
        )
    if not accepted:
        raise ValueError(
            "workmanship standard %s revision %s carries no customer acceptance; "
            "the clause grades a crimp against an accepted standard, so this one "
            "cannot be the authority for a disposition"
            % (standard["standard_id"], standard["revision"])
        )
    _require_text("accepted_by", standard.get("accepted_by"))
    bands = standard.get("gauge_bands")
    if not isinstance(bands, dict) or not bands:
        raise ValueError(
            "the standard must tabulate at least one gauge, got %r" % (bands,)
        )
    for gauge, entry in bands.items():
        _require_text("gauge key", gauge)
        if not isinstance(entry, dict):
            raise ValueError("gauge %s entry must be a mapping, got %r" % (gauge, entry))
        low = _require_positive(
            "crimp_height_min_mm for gauge %s" % gauge, entry.get("crimp_height_min_mm")
        )
        high = _require_positive(
            "crimp_height_max_mm for gauge %s" % gauge, entry.get("crimp_height_max_mm")
        )
        if low >= high:
            raise ValueError(
                "crimp height band for gauge %s runs from %r up to %r and leaves "
                "no width" % (gauge, low, high)
            )
        _require_positive(
            "min_pull_out_n for gauge %s" % gauge, entry.get("min_pull_out_n")
        )
        _require_positive_count(
            "nominal_strand_count for gauge %s" % gauge,
            entry.get("nominal_strand_count"),
        )
    return bands


def gauge_band(standard, gauge):
    """The tabulated entry for one gauge, refusing an untabulated one."""
    bands = validate_crimping_standard(standard)
    _require_text("gauge", gauge)
    if gauge not in bands:
        raise ValueError(
            "workmanship standard %s does not tabulate gauge %r; the band for an "
            "untabulated gauge is not between the neighbouring ones and is not "
            "invented here" % (standard["standard_id"], gauge)
        )
    return bands[gauge]


def crimp_measurements(crimp, standard):
    """Compression and conductor figures for one termination."""
    if not isinstance(crimp, dict):
        raise ValueError("crimp must be a mapping, got %r" % (crimp,))
    crimp_id = _require_text("crimp_id", crimp.get("crimp_id"))
    gauge = _require_text("gauge on %s" % crimp_id, crimp.get("gauge"))
    entry = gauge_band(standard, gauge)

    nominal = entry["nominal_strand_count"]
    strand_count = _require_positive_count(
        "strand_count on %s" % crimp_id, crimp.get("strand_count")
    )
    if strand_count != nominal:
        raise ValueError(
            "%s carries %d strands while the standard tabulates %d for gauge %s; "
            "the wire in the barrel is not the wire the band was written for"
            % (crimp_id, strand_count, nominal, gauge)
        )
    in_barrel = _require_count(
        "strands_in_barrel on %s" % crimp_id, crimp.get("strands_in_barrel")
    )
    if in_barrel > strand_count:
        raise ValueError(
            "%s has %d strands in the barrel of a %d strand conductor"
            % (crimp_id, in_barrel, strand_count)
        )
    nicked = _require_count("nicked_strands on %s" % crimp_id, crimp.get("nicked_strands", 0))
    if nicked > in_barrel:
        raise ValueError(
            "%s records %d nicked strands against %d that reached the barrel"
            % (crimp_id, nicked, in_barrel)
        )
    brushed = _require_count("brush_strands on %s" % crimp_id, crimp.get("brush_strands", 0))
    if in_barrel + brushed > strand_count:
        raise ValueError(
            "%s accounts for more strands than the conductor has: %d in the "
            "barrel and %d brushed outside it of %d"
            % (crimp_id, in_barrel, brushed, strand_count)
        )

    height = _require_positive(
        "crimp_height_mm on %s" % crimp_id, crimp.get("crimp_height_mm")
    )
    low = entry["crimp_height_min_mm"]
    high = entry["crimp_height_max_mm"]
    width = high - low
    lost = strand_count - in_barrel

    pull_out = crimp.get("pull_out_n")
    if pull_out is not None:
        pull_out = _require_positive("pull_out_n on %s" % crimp_id, pull_out)

    return {
        "crimp_id": crimp_id,
        "gauge": gauge,
        "strand_count": strand_count,
        "strands_in_barrel": in_barrel,
        "strands_lost": lost,
        "strand_loss_fraction": lost / float(strand_count),
        "nicked_strands": nicked,
        "nicked_strand_fraction": nicked / float(strand_count),
        "brush_strands": brushed,
        "crimp_height_mm": height,
        "crimp_height_band_mm": (low, high),
        "crimp_height_band_position": (height - low) / width,
        "under_compressed": not _at_most(height, high),
        "over_compressed": not _at_least(height, low),
        "pull_out_n": pull_out,
        "min_pull_out_n": entry["min_pull_out_n"],
        "pull_tested": pull_out is not None,
    }


def assess_crimp(crimp, standard, allowances=DEFAULT_CRIMPING_ALLOWANCES):
    """Apply the accepted workmanship standard to one crimped termination."""
    validate_crimping_allowances(allowances)
    measured = crimp_measurements(crimp, standard)
    crimp_id = measured["crimp_id"]
    findings = []
    dispositions = [ACCEPT]
    factor = allowances["rework_margin_factor"]

    low, high = measured["crimp_height_band_mm"]
    window = (high - low) * (factor - 1.0)
    if measured["over_compressed"]:
        if _at_least(measured["crimp_height_mm"], low - window):
            dispositions.append(REWORK)
            findings.append(
                "crimp height %.3f mm is under the %.3f mm band floor for gauge "
                "%s; the barrel is over-compressed onto the conductor"
                % (measured["crimp_height_mm"], low, measured["gauge"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "crimp height %.3f mm is past the rework window below the %.3f mm "
                "band floor for gauge %s"
                % (measured["crimp_height_mm"], low, measured["gauge"])
            )
    elif measured["under_compressed"]:
        if _at_most(measured["crimp_height_mm"], high + window):
            dispositions.append(REWORK)
            findings.append(
                "crimp height %.3f mm is over the %.3f mm band top for gauge %s; "
                "the barrel has not closed onto the conductor"
                % (measured["crimp_height_mm"], high, measured["gauge"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "crimp height %.3f mm is past the rework window above the %.3f mm "
                "band top for gauge %s"
                % (measured["crimp_height_mm"], high, measured["gauge"])
            )

    if measured["strands_in_barrel"] == 0:
        dispositions.append(REJECT)
        findings.append(
            "no strand reached the barrel; the termination carries no conductor"
        )
    elif not _at_most(
        measured["strand_loss_fraction"], allowances["max_strand_loss_fraction"]
    ):
        dispositions.append(REJECT)
        findings.append(
            "%d of %d strands never reached the barrel, past the %.3f fraction "
            "the allowance permits"
            % (
                measured["strands_lost"],
                measured["strand_count"],
                allowances["max_strand_loss_fraction"],
            )
        )

    if not _at_most(
        measured["nicked_strand_fraction"], allowances["max_nicked_strand_fraction"]
    ):
        dispositions.append(REJECT)
        findings.append(
            "%d of %d strands are cut or nicked, past the %.3f fraction the "
            "allowance permits"
            % (
                measured["nicked_strands"],
                measured["strand_count"],
                allowances["max_nicked_strand_fraction"],
            )
        )

    if measured["brush_strands"] > allowances["max_brush_strands"]:
        if measured["brush_strands"] <= allowances["max_brush_strands"] + 1:
            dispositions.append(REWORK)
        else:
            dispositions.append(REJECT)
        findings.append(
            "%d strands are brushed outside the barrel, past the %d the allowance "
            "permits; a loose strand is an isolation question as well as a lost "
            "current path"
            % (measured["brush_strands"], allowances["max_brush_strands"])
        )

    support = crimp.get("insulation_support", SUPPORT_CORRECT)
    if support not in INSULATION_SUPPORT_STATES:
        raise ValueError(
            "insulation_support on %s must be one of %s, got %r"
            % (crimp_id, ", ".join(INSULATION_SUPPORT_STATES), support)
        )
    if support == SUPPORT_MISSING:
        dispositions.append(REJECT)
        findings.append(
            "the insulation support is not formed; the conductor takes the whole "
            "bending load at the barrel mouth"
        )
    elif support == SUPPORT_LOOSE:
        dispositions.append(REWORK)
        findings.append("the insulation support is loose on the jacket")

    if _require_flag(
        "insulation_in_barrel on %s" % crimp_id, crimp.get("insulation_in_barrel", False)
    ):
        dispositions.append(REJECT)
        findings.append(
            "insulation is trapped inside the barrel; it sits between the strands "
            "and the contact"
        )

    if not _require_flag(
        "bell_mouth_present on %s" % crimp_id, crimp.get("bell_mouth_present", True)
    ):
        dispositions.append(REWORK)
        findings.append(
            "no bell mouth at the barrel entry; the strands turn on a sheared edge"
        )

    if not _require_flag(
        "conductor_visible_at_window on %s" % crimp_id,
        crimp.get("conductor_visible_at_window", True),
    ):
        dispositions.append(REWORK)
        findings.append(
            "the conductor is not visible at the inspection window, so the strands "
            "cannot be confirmed bottomed in the barrel"
        )

    if measured["pull_tested"] and not _at_least(
        measured["pull_out_n"], measured["min_pull_out_n"]
    ):
        dispositions.append(REJECT)
        findings.append(
            "pulled out at %.1f N against the %.1f N the standard holds gauge %s to"
            % (measured["pull_out_n"], measured["min_pull_out_n"], measured["gauge"])
        )

    return {
        "crimp_id": crimp_id,
        "gauge": measured["gauge"],
        "verdict": _worst(dispositions),
        "measurements": measured,
        "pull_tested": measured["pull_tested"],
        "findings": findings,
    }


def inspect_crimping(harness, standard, allowances=DEFAULT_CRIMPING_ALLOWANCES):
    """Clause 5.5.3.2.15 crimp inspection over one harness or assembly."""
    validate_crimping_allowances(allowances)
    validate_crimping_standard(standard)
    if not isinstance(harness, dict):
        raise ValueError("harness must be a mapping, got %r" % (harness,))
    harness_id = _require_text("harness_id", harness.get("harness_id"))
    cited = _require_text("standard_revision", harness.get("standard_revision"))
    if cited != standard["revision"]:
        raise ValueError(
            "harness %s was inspected against workmanship standard revision %r "
            "while the accepted standard in hand is revision %r"
            % (harness_id, cited, standard["revision"])
        )
    declared = harness.get("declared_crimp_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_crimp_count must be a positive integer, got %r" % (declared,)
        )
    records = harness.get("crimps")
    if not isinstance(records, (list, tuple)):
        raise ValueError("crimps must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d crimp records against a declared count of %d on %s"
            % (len(records), declared, harness_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_crimp(record, standard, allowances)
        if result["crimp_id"] in seen:
            raise ValueError(
                "duplicate crimp id %r on harness %s" % (result["crimp_id"], harness_id)
            )
        seen.add(result["crimp_id"])
        screened.append(result)

    inspected = len(screened)
    counts = dict((state, 0) for state in CRIMP_DISPOSITIONS)
    findings = []
    dispositions = [ACCEPT]
    affected = 0
    pull_tested = 0
    for result in screened:
        counts[result["verdict"]] += 1
        dispositions.append(result["verdict"])
        if result["findings"]:
            affected += 1
        if result["pull_tested"]:
            pull_tested += 1
        for finding in result["findings"]:
            findings.append("%s %s" % (result["crimp_id"], finding))

    affected_allowed = allowances["max_affected_crimp_fraction"] * inspected
    factor = allowances["rework_margin_factor"]
    if inspected and not _at_most(affected, affected_allowed):
        if _at_most(affected, affected_allowed * factor):
            dispositions.append(REWORK)
            findings.append(
                "%d of %d terminations carry a finding, past the %.2f the harness "
                "allowance permits" % (affected, inspected, affected_allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d of %d terminations carry a finding, past the rework margin "
                "of %.2f" % (affected, inspected, affected_allowed * factor)
            )

    pull_required = allowances["min_pull_test_fraction"] * declared
    pull_sample_met = _at_least(pull_tested, pull_required)
    if not pull_sample_met:
        dispositions.append(REWORK)
        findings.append(
            "%d terminations were pull tested against the %.2f the sample "
            "fraction asks of a %d crimp harness"
            % (pull_tested, pull_required, declared)
        )

    verdict = _worst(dispositions)
    missing = declared - inspected
    complete = missing == 0
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of %d terminations carry no inspection record; an allowance "
            "applied to a short set is applied to the wrong population"
            % (missing, declared)
        )
    return {
        "harness_id": harness_id,
        "standard_id": standard["standard_id"],
        "standard_revision": standard["revision"],
        "accepted_by": standard["accepted_by"],
        "verdict": verdict,
        "inspection_complete": complete,
        "declared_crimp_count": declared,
        "inspected_count": inspected,
        "missing_record_count": missing,
        "disposition_counts": counts,
        "affected_count": affected,
        "affected_fraction": affected / float(inspected) if inspected else 0.0,
        "affected_allowance": affected_allowed,
        "remaining_affected_allowance": affected_allowed - affected,
        "pull_tested_count": pull_tested,
        "pull_test_sample_required": pull_required,
        "pull_test_sample_met": pull_sample_met,
        "not_accepted_ids": [
            result["crimp_id"] for result in screened if result["verdict"] != ACCEPT
        ],
        "crimps": screened,
        "findings": findings,
    }
