#!/usr/bin/env python3
"""Choosing the Class 3 source that costs the least added qualification.

Anchor: ECSS-Q-ST-60C clause 6.2.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

On a Class 3 design the preference between two parts that do the same
electrical job is not a matter of taste and not only a matter of price.
It is the work still owed before either can be flown: the construction
analysis, the lot traceability, the electrical upscreening, the thermal
cycling, the burn-in, the destructive physical analysis, the radiation
characterisation and the qualification testing that the source has not
already done. The preferred source is the one that leaves the shortest
list of those.

Two things decide that list. The first is where the part sits: a part
already qualified to a recognised standard owes almost nothing, a part
from a manufacturer's space catalogue owes a little, an automotive or
industrial part owes a good deal, and an uncharacterised commercial
part owes nearly all of it. The second is what the supplier can already
show. Evidence on file removes an activity from the list; it does not
reduce it, because an activity is either done and documented or it is
owed in full.

Effort and schedule are different currencies and a source can fail on
either. Upscreening runs in sequence on one lot, so the weeks add up,
and a cheap programme that lands after the integration date is not
cheap. A source is therefore graded twice: on the effort it adds and on
whether that effort fits the time left.

One condition is not tradeable. Upscreening acts on a lot, so a part
that cannot be tied to a single production lot cannot be upscreened at
all -- every result would describe a different population from the one
that flies. Such a source is inadmissible rather than expensive, and no
amount of schedule buys it back.

The useful output is a ranking with the numbers behind it: the effort
index and the weeks for each candidate, the recommended source, the
runner-up, the margin between them, and the single activity that
dominates what is still owed.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

QUALIFICATION_ACTIVITIES = (
    "construction-analysis",
    "lot-traceability-reconstruction",
    "electrical-upscreening",
    "temperature-cycling-upscreening",
    "burn-in",
    "destructive-physical-analysis",
    "radiation-characterisation",
    "qualification-testing",
)

ACTIVITY_EFFORT = {
    "construction-analysis": 2.0,
    "lot-traceability-reconstruction": 1.0,
    "electrical-upscreening": 3.0,
    "temperature-cycling-upscreening": 2.0,
    "burn-in": 2.0,
    "destructive-physical-analysis": 3.0,
    "radiation-characterisation": 5.0,
    "qualification-testing": 6.0,
}

ACTIVITY_LEAD_WEEKS = {
    "construction-analysis": 3.0,
    "lot-traceability-reconstruction": 2.0,
    "electrical-upscreening": 4.0,
    "temperature-cycling-upscreening": 3.0,
    "burn-in": 2.0,
    "destructive-physical-analysis": 4.0,
    "radiation-characterisation": 8.0,
    "qualification-testing": 12.0,
}

TOTAL_EFFORT = sum(ACTIVITY_EFFORT.values())

SOURCE_TIERS = (
    "qualified-to-a-recognised-standard",
    "manufacturer-space-catalogue",
    "automotive-or-industrial-qualified",
    "commercial-uncharacterised",
)

TIER_REQUIRED_ACTIVITIES = {
    "qualified-to-a-recognised-standard": (
        "lot-traceability-reconstruction",
    ),
    "manufacturer-space-catalogue": (
        "construction-analysis",
        "lot-traceability-reconstruction",
        "radiation-characterisation",
    ),
    "automotive-or-industrial-qualified": (
        "construction-analysis",
        "lot-traceability-reconstruction",
        "electrical-upscreening",
        "temperature-cycling-upscreening",
        "destructive-physical-analysis",
        "radiation-characterisation",
    ),
    "commercial-uncharacterised": QUALIFICATION_ACTIVITIES,
}

SOURCE_PREFERRED = "class-3-source-preferred"
SOURCE_ACCEPTABLE_WITH_EFFORT = "class-3-source-acceptable-with-added-qualification"
SOURCE_NOT_SCHEDULABLE = "class-3-source-not-schedulable"
SOURCE_INADMISSIBLE = "class-3-source-inadmissible"

PREFERRED_EFFORT_CEILING = 0.2

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An effort index is a quotient while the ceiling it is graded against
    is a decimal literal, so a candidate built to sit exactly on the
    ceiling can land a few units in the last place over it. The ceiling
    is never moved; only the comparison tolerates the representation
    error.
    """
    return value <= limit or _equal(value, limit)


def required_activities(source_tier):
    """The qualification work a source of this kind owes before flight."""
    if source_tier not in SOURCE_TIERS:
        raise ValueError("unknown source_tier %r" % (source_tier,))
    return tuple(
        activity
        for activity in QUALIFICATION_ACTIVITIES
        if activity in TIER_REQUIRED_ACTIVITIES[source_tier]
    )


def _read_candidate(candidate):
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping, got %r" % (candidate,))
    reference = _require_text("candidate reference", candidate.get("reference"))
    tier = candidate.get("source_tier")
    if tier not in SOURCE_TIERS:
        raise ValueError(
            "source_tier of %s must be one of %s, got %r"
            % (reference, ", ".join(SOURCE_TIERS), tier)
        )
    evidence = candidate.get("evidence_on_file", ())
    if isinstance(evidence, str) or not isinstance(evidence, (list, tuple, set, frozenset)):
        raise ValueError(
            "evidence_on_file of %s must be a sequence of activity names, got %r"
            % (reference, evidence)
        )
    unknown = set(evidence) - set(QUALIFICATION_ACTIVITIES)
    if unknown:
        raise ValueError(
            "evidence_on_file of %s names unknown activities: %s"
            % (reference, ", ".join(sorted(unknown)))
        )
    traceable = _require_flag(
        "traceable_to_single_lot of %s" % reference,
        candidate.get("traceable_to_single_lot"),
    )
    return reference, tier, frozenset(evidence), traceable


def outstanding_activities(candidate):
    """The activities the source owes that nobody has evidence for yet."""
    reference, tier, evidence, _ = _read_candidate(candidate)
    return tuple(
        activity
        for activity in required_activities(tier)
        if activity not in evidence
    )


def qualification_effort(candidate):
    """Weighted effort still owed by this source, in effort units."""
    return sum(ACTIVITY_EFFORT[activity] for activity in outstanding_activities(candidate))


def qualification_lead_weeks(candidate):
    """Weeks the outstanding programme needs, run in sequence on one lot."""
    return sum(
        ACTIVITY_LEAD_WEEKS[activity] for activity in outstanding_activities(candidate)
    )


def effort_index(candidate):
    """Outstanding effort as a share of a wholly uncharacterised source."""
    return qualification_effort(candidate) / TOTAL_EFFORT


def dominant_activity(candidate):
    """The single outstanding activity that costs the most effort."""
    outstanding = outstanding_activities(candidate)
    if not outstanding:
        return None
    return max(
        outstanding,
        key=lambda activity: (ACTIVITY_EFFORT[activity], ACTIVITY_LEAD_WEEKS[activity]),
    )


def assess_candidate(candidate, weeks_available):
    """Grade one candidate source on added effort and on schedule."""
    reference, tier, evidence, traceable = _read_candidate(candidate)
    available = _require_positive("weeks_available", weeks_available)
    outstanding = outstanding_activities(candidate)
    effort = qualification_effort(candidate)
    index = effort / TOTAL_EFFORT
    weeks = qualification_lead_weeks(candidate)
    schedulable = _at_most(weeks, available)
    reasons = []
    if not traceable:
        reasons.append(
            "%s cannot be tied to a single production lot, so no upscreening "
            "result would describe the population that flies" % reference
        )
        verdict = SOURCE_INADMISSIBLE
    elif not schedulable:
        reasons.append(
            "%s needs %.1f weeks of added qualification against %.1f available"
            % (reference, weeks, available)
        )
        verdict = SOURCE_NOT_SCHEDULABLE
    elif not outstanding:
        verdict = SOURCE_PREFERRED
    elif _at_most(index, PREFERRED_EFFORT_CEILING):
        verdict = SOURCE_PREFERRED
    else:
        verdict = SOURCE_ACCEPTABLE_WITH_EFFORT
    return {
        "reference": reference,
        "source_tier": tier,
        "evidence_on_file": tuple(sorted(evidence)),
        "traceable_to_single_lot": traceable,
        "outstanding_activities": outstanding,
        "qualification_effort": effort,
        "effort_index": index,
        "lead_time_weeks": weeks,
        "weeks_available": available,
        "schedulable": schedulable,
        "dominant_activity": dominant_activity(candidate),
        "verdict": verdict,
        "selectable": verdict in (SOURCE_PREFERRED, SOURCE_ACCEPTABLE_WITH_EFFORT),
        "reasons": reasons,
    }


def rank_candidates(candidates, weeks_available):
    """Order the selectable candidates by the work they still owe."""
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("candidates must be a non-empty sequence of mappings")
    graded = [assess_candidate(candidate, weeks_available) for candidate in candidates]
    seen = set()
    for entry in graded:
        if entry["reference"] in seen:
            raise ValueError("candidate %s declared twice" % entry["reference"])
        seen.add(entry["reference"])
    selectable = [entry for entry in graded if entry["selectable"]]
    selectable.sort(
        key=lambda entry: (
            entry["qualification_effort"],
            entry["lead_time_weeks"],
            entry["reference"],
        )
    )
    return {"graded": graded, "ranked": selectable}


def select_preferred_source(case):
    """Full clause 6.2.2.3 read on one Class 3 make-or-buy shortlist."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    function = _require_text("function", case.get("function"))
    weeks_available = case.get("weeks_available")
    outcome = rank_candidates(case.get("candidates"), weeks_available)
    graded = outcome["graded"]
    ranked = outcome["ranked"]

    findings = []
    for entry in graded:
        findings.extend(entry["reasons"])
    if not ranked:
        return {
            "function": function,
            "selected": None,
            "runner_up": None,
            "effort_margin": None,
            "verdict": SOURCE_INADMISSIBLE
            if all(entry["verdict"] == SOURCE_INADMISSIBLE for entry in graded)
            else SOURCE_NOT_SCHEDULABLE,
            "acceptable": False,
            "graded": graded,
            "ranked": ranked,
            "findings": findings
            + ["no candidate on the shortlist can be brought to Class 3 in time"],
            "actions": ["widen the shortlist or move the integration date"],
        }

    selected = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    margin = (
        runner_up["qualification_effort"] - selected["qualification_effort"]
        if runner_up is not None
        else None
    )
    actions = []
    for activity in selected["outstanding_activities"]:
        actions.append(
            "raise %s on %s before the part is released to the build"
            % (activity, selected["reference"])
        )
    if runner_up is not None and margin is not None and _equal(margin, 0.0):
        findings.append(
            "%s and %s owe the same effort, so the choice between them was made "
            "on lead time and then on name, not on qualification work"
            % (selected["reference"], runner_up["reference"])
        )
    return {
        "function": function,
        "selected": selected["reference"],
        "selected_effort_index": selected["effort_index"],
        "selected_lead_weeks": selected["lead_time_weeks"],
        "dominant_activity": selected["dominant_activity"],
        "runner_up": runner_up["reference"] if runner_up is not None else None,
        "effort_margin": margin,
        "verdict": selected["verdict"],
        "acceptable": True,
        "graded": graded,
        "ranked": ranked,
        "findings": findings,
        "actions": actions,
    }
