#!/usr/bin/env python3
"""Pull-off verification of a crimped lot: sample rate, force and break mode.

Anchor: ECSS-Q-ST-70-26 Quality clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Pull-off is destructive, so it is never applied to the hardware that
flies. It is applied to a sample, and the whole value of the result
rests on three things that are easy to report separately and easy to
lose together:

sample rate   the number of specimens the lot size demands. An
              undersized sample yields a measurement, not a
              verification, and it cannot accept the lot however good
              the forces were.
force         every specimen is compared with the minimum tabulated for
              its own gauge. The minimum moves with the conductor, so a
              single figure across a mixed-gauge lot passes the fine
              wire on the heavy wire's evidence.
break mode    where the specimen let go matters as much as when. A
              conductor that breaks outside the barrel proves the crimp
              is stronger than the wire. A conductor that pulls out of
              the barrel proves the opposite, even when the force was
              above the minimum.

A failing lot does not simply fail: the sample rate escalates, because
one failure in a small sample is evidence about the population and not
about the specimen.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BREAK_CONDUCTOR = "conductor-break"
BREAK_PULL_OUT = "pull-out"
BREAK_CONTACT = "contact-failure"
BREAK_MODES = (BREAK_CONDUCTOR, BREAK_PULL_OUT, BREAK_CONTACT)

LOT_ACCEPT = "accept"
LOT_REVIEW = "review"
LOT_REJECT = "reject"

_RANK = {LOT_ACCEPT: 0, LOT_REVIEW: 1, LOT_REJECT: 2}

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


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    value = _require_count(name, value)
    if value == 0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A force specified to land exactly on the minimum can evaluate a few
    units in the last place below it after a unit conversion from the
    load cell. The minimum is never relaxed; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = LOT_ACCEPT
    for disposition in dispositions:
        if _RANK[disposition] > _RANK[worst]:
            worst = disposition
    return worst


def validate_force_table(table):
    """Normalise the per-gauge minimum pull-off force table."""
    if not isinstance(table, dict) or not table:
        raise ValueError("force table must be a non-empty mapping of gauge to entry")
    normalised = {}
    for gauge, entry in table.items():
        if not isinstance(gauge, str) or not gauge.strip():
            raise ValueError("gauge key must be a non-empty string, got %r" % (gauge,))
        if isinstance(entry, dict):
            minimum = entry.get("min_pull_off_n")
        else:
            minimum = entry
        minimum = _require_positive("gauge %s min_pull_off_n" % gauge, minimum)
        normalised[gauge] = {"gauge": gauge, "min_pull_off_n": minimum}
    return normalised


def _looks_normalised(table):
    return (
        isinstance(table, dict)
        and bool(table)
        and all(
            isinstance(entry, dict) and "min_pull_off_n" in entry and "gauge" in entry
            for entry in table.values()
        )
    )


def lookup_force(table, gauge):
    """Return the minimum force for one gauge; nothing is interpolated."""
    normalised = table if _looks_normalised(table) else validate_force_table(table)
    if gauge not in normalised:
        raise ValueError(
            "gauge %r is not tabulated (have %s); a minimum pull-off force is "
            "not interpolated between gauges"
            % (gauge, ", ".join(sorted(normalised)))
        )
    return normalised[gauge]


def validate_sample_plan(plan):
    """Normalise the sampling plan: tiers by lot size plus a rule above them."""
    if not isinstance(plan, dict):
        raise ValueError("sample plan must be a mapping, got %r" % (plan,))
    tiers = plan.get("tiers")
    if not isinstance(tiers, (list, tuple)) or not tiers:
        raise ValueError("sample plan must carry a non-empty tiers sequence")
    normalised_tiers = []
    last_up_to = 0
    last_sample = 0
    for index, tier in enumerate(tiers):
        if not isinstance(tier, dict):
            raise ValueError("tier %d must be a mapping" % index)
        up_to = _require_positive_count("tier %d up_to" % index, tier.get("up_to"))
        sample = _require_positive_count("tier %d sample" % index, tier.get("sample"))
        if up_to <= last_up_to:
            raise ValueError(
                "tier %d up_to %d does not increase on the previous %d; the plan "
                "has to be ordered by lot size" % (index, up_to, last_up_to)
            )
        if sample < last_sample:
            raise ValueError(
                "tier %d takes %d specimens from a larger lot than the previous "
                "tier's %d; a bigger lot cannot need a smaller sample"
                % (index, sample, last_sample)
            )
        if sample > up_to:
            raise ValueError(
                "tier %d asks for %d specimens from a lot of at most %d"
                % (index, sample, up_to)
            )
        normalised_tiers.append({"up_to": up_to, "sample": sample})
        last_up_to = up_to
        last_sample = sample
    fraction = _require_number(
        "fraction_above", plan.get("fraction_above", 0.0)
    )
    if fraction < 0.0 or fraction > 1.0:
        raise ValueError("fraction_above must sit between 0 and 1")
    minimum_above = _require_count(
        "minimum_above", plan.get("minimum_above", last_sample)
    )
    if fraction == 0.0 and minimum_above == 0:
        raise ValueError(
            "the plan has no rule for lots above its largest tier; a lot of any "
            "size has to resolve to a sample size"
        )
    return {
        "tiers": normalised_tiers,
        "fraction_above": fraction,
        "minimum_above": minimum_above,
        "largest_tier": last_up_to,
    }


def required_sample_size(lot_size, plan):
    """Resolve the specimen count the lot size demands."""
    size = _require_positive_count("lot_size", lot_size)
    if not isinstance(plan, dict):
        raise ValueError("sample plan must be a mapping, got %r" % (plan,))
    normalised = plan if "largest_tier" in plan else validate_sample_plan(plan)
    for tier in normalised["tiers"]:
        if size <= tier["up_to"]:
            return min(tier["sample"], size)
    by_fraction = math.ceil(size * normalised["fraction_above"] - 1e-9)
    return min(max(by_fraction, normalised["minimum_above"]), size)


def evaluate_sample_size(lot_size, tested_count, plan):
    """Grade the sample actually pulled against the one the plan demands."""
    size = _require_positive_count("lot_size", lot_size)
    tested = _require_count("tested_count", tested_count)
    if tested > size:
        raise ValueError(
            "%d specimens were pulled from a lot of %d" % (tested, size)
        )
    required = required_sample_size(size, plan)
    sufficient = tested >= required
    findings = []
    if not sufficient:
        findings.append(
            "%d specimens were pulled where the plan demands %d for a lot of %d; "
            "an undersized sample is a measurement, not a verification"
            % (tested, required, size)
        )
    return {
        "lot_size": size,
        "tested_count": tested,
        "required_count": required,
        "shortfall": max(0, required - tested),
        "coverage_fraction": tested / size,
        "sufficient": sufficient,
        "disposition": LOT_ACCEPT if sufficient else LOT_REVIEW,
        "findings": findings,
    }


def evaluate_specimen(specimen, table):
    """Grade one pulled specimen on its force and on where it let go."""
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping, got %r" % (specimen,))
    entry = lookup_force(table, specimen.get("gauge"))
    force = _require_positive("force_n", specimen.get("force_n"))
    mode = _require_choice("break_mode", specimen.get("break_mode"), BREAK_MODES)
    minimum = entry["min_pull_off_n"]
    reached = _at_least(force, minimum)
    findings = []
    if not reached:
        disposition = LOT_REJECT
        findings.append(
            "%.1f N is below the %.1f N minimum for gauge %s"
            % (force, minimum, entry["gauge"])
        )
        if mode == BREAK_PULL_OUT:
            findings.append(
                "the conductor pulled out of the barrel, so the crimp released "
                "before the wire did"
            )
    elif mode == BREAK_PULL_OUT:
        disposition = LOT_REVIEW
        findings.append(
            "%.1f N cleared the %.1f N minimum but the conductor pulled out of "
            "the barrel; the crimp is still weaker than the wire"
            % (force, minimum)
        )
    elif mode == BREAK_CONTACT:
        disposition = LOT_REVIEW
        findings.append(
            "the contact itself failed at %.1f N, so this specimen says nothing "
            "about the crimp" % force
        )
    else:
        disposition = LOT_ACCEPT
    return {
        "identifier": specimen.get("identifier", "unidentified"),
        "gauge": entry["gauge"],
        "force_n": force,
        "minimum_n": minimum,
        "margin_n": force - minimum,
        "margin_fraction": (force - minimum) / minimum,
        "break_mode": mode,
        "reached_minimum": reached,
        "disposition": disposition,
        "findings": findings,
    }


def escalated_sample_size(lot_size, plan, failures):
    """Escalate the sample rate after a failure; two failures take the lot."""
    size = _require_positive_count("lot_size", lot_size)
    count = _require_count("failures", failures)
    base = required_sample_size(size, plan)
    if count == 0:
        return base
    if count >= 2:
        return size
    return min(base * 2, size)


def verify_lot(lot):
    """Full pull-off verification of one crimped lot."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    table = validate_force_table(lot.get("force_table"))
    plan = validate_sample_plan(lot.get("sample_plan"))
    specimens = lot.get("specimens")
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("lot must carry a non-empty specimens sequence")
    lot_size = _require_positive_count("lot_size", lot.get("lot_size"))
    results = [evaluate_specimen(specimen, table) for specimen in specimens]
    sampling = evaluate_sample_size(lot_size, len(results), plan)
    failures = [r for r in results if r["disposition"] == LOT_REJECT]
    inconclusive = [r for r in results if r["disposition"] == LOT_REVIEW]
    disposition = _worst(
        [sampling["disposition"]] + [r["disposition"] for r in results]
    )
    forces = [r["force_n"] for r in results]
    margins = [r["margin_fraction"] for r in results]
    findings = []
    findings.extend("sampling: %s" % text for text in sampling["findings"])
    for result in results:
        findings.extend(
            "%s: %s" % (result["identifier"], text) for text in result["findings"]
        )
    return {
        "lot_size": lot_size,
        "sampling": sampling,
        "specimen_count": len(results),
        "failure_count": len(failures),
        "inconclusive_count": len(inconclusive),
        "min_force_n": min(forces),
        "mean_force_n": sum(forces) / len(forces),
        "worst_margin_fraction": min(margins),
        "pull_out_count": sum(
            1 for r in results if r["break_mode"] == BREAK_PULL_OUT
        ),
        "disposition": disposition,
        "next_lot_sample_size": escalated_sample_size(lot_size, plan, len(failures)),
        "escalated": len(failures) > 0,
        "failed_specimens": [r["identifier"] for r in failures],
        "inconclusive_specimens": [r["identifier"] for r in inconclusive],
        "specimens": results,
        "findings": findings,
    }
