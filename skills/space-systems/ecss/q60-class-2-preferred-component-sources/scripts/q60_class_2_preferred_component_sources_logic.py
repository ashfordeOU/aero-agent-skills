#!/usr/bin/env python3
"""Preferring the Class 2 source that costs the least added work.

Anchor: ECSS-Q-ST-60C clause 5.2.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

On a Class 2 design the direction is not "buy the best part". It is
"buy the part that arrives closest to the assurance the class already
asks for", because every step the source has not already evidenced has
to be paid for afterwards in an upscreening or qualification campaign
the project runs itself.

That turns source preference into an arithmetic question rather than a
tier lookup:

    burden     which of the applicable qualification and screening
               steps does this source NOT already evidence, and what do
               those cost in effort, in campaign weeks and in sample
               devices consumed
    ranking    which candidate carries the smallest residual burden
    departure  if the design did not take that candidate, is the step
               away recorded against a reason the project accepts

Applicability comes before cost. A seal test on a plastic package is
not a gap the source failed to close, it is a step that does not exist
for that package, and counting it as missing penalises exactly the
sources the clause is steering a Class 2 design toward.

The campaign length is the longest missing step rather than their sum,
because separate steps run in parallel on separate samples; the sample
count and the effort, which do not share, are summed.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PACKAGE_STYLES = ("hermetic", "non-hermetic")

# Each step carries the effort it costs to run, the campaign weeks it
# occupies and the sample devices it consumes. A step is scoped to the
# package styles it can physically be run on.
DEFAULT_STEP_CATALOGUE = {
    "lot-traceability-record": {
        "effort": 2.0,
        "lead_weeks": 2.0,
        "samples": 0,
        "package_styles": PACKAGE_STYLES,
    },
    "temperature-cycling-screen": {
        "effort": 6.0,
        "lead_weeks": 3.0,
        "samples": 0,
        "package_styles": PACKAGE_STYLES,
    },
    "burn-in-screen": {
        "effort": 10.0,
        "lead_weeks": 6.0,
        "samples": 0,
        "package_styles": PACKAGE_STYLES,
    },
    "electrical-drift-measurement": {
        "effort": 5.0,
        "lead_weeks": 3.0,
        "samples": 0,
        "package_styles": PACKAGE_STYLES,
    },
    "destructive-physical-analysis": {
        "effort": 12.0,
        "lead_weeks": 5.0,
        "samples": 6,
        "package_styles": PACKAGE_STYLES,
    },
    "radiation-lot-acceptance": {
        "effort": 18.0,
        "lead_weeks": 12.0,
        "samples": 11,
        "package_styles": PACKAGE_STYLES,
    },
    "seal-and-leak-screen": {
        "effort": 4.0,
        "lead_weeks": 2.0,
        "samples": 0,
        "package_styles": ("hermetic",),
    },
    "particle-impact-noise-screen": {
        "effort": 4.0,
        "lead_weeks": 2.0,
        "samples": 0,
        "package_styles": ("hermetic",),
    },
    "moisture-sensitivity-characterisation": {
        "effort": 8.0,
        "lead_weeks": 5.0,
        "samples": 9,
        "package_styles": ("non-hermetic",),
    },
}

# Reasons the project accepts for taking a source that is not the
# cheapest to bring up to the class.
ACCEPTED_DEPARTURE_REASONS = (
    "no-form-fit-function-equivalent",
    "cheaper-source-obsolete",
    "cheaper-source-lead-time-misses-need-date",
    "cheaper-source-fails-a-material-restriction",
)

DEFAULT_CAMPAIGN_INDEX_CEILING = 0.60

CANDIDATE_READY = "candidate-arrives-qualified"
CANDIDATE_UPSCREENING = "candidate-needs-upscreening"
CANDIDATE_CAMPAIGN = "candidate-needs-full-campaign"

SELECTION_LEAST_EFFORT = "selection-takes-the-least-effort-source"
SELECTION_JUSTIFIED = "selection-departs-on-recorded-reason"
SELECTION_UNJUSTIFIED = "selection-departs-with-no-accepted-reason"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    value = _require_non_negative(name, value)
    if value > 1.0:
        raise ValueError("%s must not exceed 1.0, got %r" % (name, value))
    return value


def _require_sample_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_reference(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A residual index is a ratio of two sums, so an index built to sit
    exactly on a ceiling can land a few units in the last place above
    it. The ceiling is never raised; only the comparison tolerates the
    representation error.
    """
    return value <= limit or _equal(value, limit)


def validate_step_catalogue(catalogue):
    """Check a step catalogue is usable before any burden is measured."""
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("catalogue must be a non-empty mapping")
    for step, entry in catalogue.items():
        _require_reference("step name", step)
        if not isinstance(entry, dict):
            raise ValueError("catalogue entry for %s must be a mapping" % step)
        for field in ("effort", "lead_weeks"):
            if field not in entry:
                raise ValueError("catalogue entry for %s is missing %s" % (step, field))
        _require_positive("effort for %s" % step, entry["effort"])
        _require_non_negative("lead_weeks for %s" % step, entry["lead_weeks"])
        _require_sample_count("samples for %s" % step, entry.get("samples", 0))
        styles = entry.get("package_styles", PACKAGE_STYLES)
        if not isinstance(styles, (list, tuple)) or not styles:
            raise ValueError("package_styles for %s must be a non-empty sequence" % step)
        for style in styles:
            _require_choice("package_style for %s" % step, style, PACKAGE_STYLES)
    return catalogue


def applicable_steps(package_style, catalogue=DEFAULT_STEP_CATALOGUE):
    """Steps that can physically be run on this package style."""
    validate_step_catalogue(catalogue)
    _require_choice("package_style", package_style, PACKAGE_STYLES)
    return tuple(
        sorted(
            step
            for step, entry in catalogue.items()
            if package_style in tuple(entry.get("package_styles", PACKAGE_STYLES))
        )
    )


def residual_qualification_burden(candidate, catalogue=DEFAULT_STEP_CATALOGUE):
    """Work left over after the source's own evidence is taken into account."""
    validate_step_catalogue(catalogue)
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping, got %r" % (candidate,))
    reference = _require_reference("part_reference", candidate.get("part_reference"))
    style = _require_choice(
        "package_style", candidate.get("package_style"), PACKAGE_STYLES
    )
    held = candidate.get("evidence_held", [])
    if not isinstance(held, (list, tuple)):
        raise ValueError("evidence_held must be a sequence for %s" % reference)
    held_set = set()
    for step in held:
        step = _require_reference("evidence_held entry", step)
        if step not in catalogue:
            raise ValueError(
                "%s claims evidence for an unknown step: %s" % (reference, step)
            )
        held_set.add(step)

    scoped = applicable_steps(style, catalogue)
    not_applicable = sorted(held_set - set(scoped))
    missing = tuple(step for step in scoped if step not in held_set)
    total_effort = sum(float(catalogue[step]["effort"]) for step in scoped)
    residual_effort = sum(float(catalogue[step]["effort"]) for step in missing)
    lead_weeks = max(
        [float(catalogue[step]["lead_weeks"]) for step in missing] + [0.0]
    )
    samples = sum(int(catalogue[step].get("samples", 0)) for step in missing)
    return {
        "part_reference": reference,
        "package_style": style,
        "applicable_steps": scoped,
        "evidenced_steps": tuple(step for step in scoped if step in held_set),
        "missing_steps": missing,
        "evidence_outside_scope": tuple(not_applicable),
        "total_effort": total_effort,
        "residual_effort": residual_effort,
        "residual_index": residual_effort / total_effort,
        "campaign_lead_weeks": lead_weeks,
        "sample_devices_consumed": samples,
    }


def grade_candidate(
    candidate,
    catalogue=DEFAULT_STEP_CATALOGUE,
    campaign_index_ceiling=DEFAULT_CAMPAIGN_INDEX_CEILING,
):
    """Burden of one candidate plus the disposition it implies."""
    ceiling = _require_fraction("campaign_index_ceiling", campaign_index_ceiling)
    burden = residual_qualification_burden(candidate, catalogue)
    index = burden["residual_index"]
    if not burden["missing_steps"]:
        disposition = CANDIDATE_READY
    elif _at_most(index, ceiling):
        disposition = CANDIDATE_UPSCREENING
    else:
        disposition = CANDIDATE_CAMPAIGN
    findings = []
    if burden["evidence_outside_scope"]:
        findings.append(
            "%s claims evidence for %s, which its package style cannot be run "
            "through; the claim is ignored rather than credited"
            % (
                burden["part_reference"],
                ", ".join(burden["evidence_outside_scope"]),
            )
        )
    if disposition == CANDIDATE_CAMPAIGN:
        findings.append(
            "%s leaves %.4g of the applicable effort open, past the %.4g ceiling; "
            "this is a qualification campaign rather than an upscreening run"
            % (burden["part_reference"], index, ceiling)
        )
    burden["disposition"] = disposition
    burden["findings"] = findings
    return burden


def rank_candidates(
    candidates,
    catalogue=DEFAULT_STEP_CATALOGUE,
    campaign_index_ceiling=DEFAULT_CAMPAIGN_INDEX_CEILING,
):
    """Order candidates by the work each one leaves for the project."""
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("candidates must be a non-empty sequence")
    graded = [
        grade_candidate(item, catalogue, campaign_index_ceiling) for item in candidates
    ]
    seen = set()
    for item in graded:
        if item["part_reference"] in seen:
            raise ValueError(
                "part_reference %s appears twice among the candidates"
                % item["part_reference"]
            )
        seen.add(item["part_reference"])
    return sorted(
        graded,
        key=lambda item: (
            item["residual_effort"],
            item["campaign_lead_weeks"],
            item["sample_devices_consumed"],
            item["part_reference"],
        ),
    )


def assess_selection(
    selection,
    catalogue=DEFAULT_STEP_CATALOGUE,
    campaign_index_ceiling=DEFAULT_CAMPAIGN_INDEX_CEILING,
):
    """Full clause 5.2.2.3 source preference check for one Class 2 part slot."""
    if not isinstance(selection, dict):
        raise ValueError("selection must be a mapping, got %r" % (selection,))
    slot = _require_reference("slot", selection.get("slot"))
    chosen_reference = _require_reference(
        "chosen_reference", selection.get("chosen_reference")
    )
    ranked = rank_candidates(
        selection.get("candidates"), catalogue, campaign_index_ceiling
    )
    by_reference = {item["part_reference"]: item for item in ranked}
    if chosen_reference not in by_reference:
        raise ValueError(
            "the chosen part %s is not among the candidates for %s"
            % (chosen_reference, slot)
        )
    chosen = by_reference[chosen_reference]
    least = ranked[0]
    reason = selection.get("departure_reason")
    if reason is not None:
        reason = _require_reference("departure_reason", reason)

    findings = list(chosen["findings"])
    takes_least = _equal(chosen["residual_effort"], least["residual_effort"])
    if takes_least:
        verdict = SELECTION_LEAST_EFFORT
    elif reason in ACCEPTED_DEPARTURE_REASONS:
        verdict = SELECTION_JUSTIFIED
        findings.append(
            "%s carries %.4g more effort units than %s, recorded against %s"
            % (
                chosen_reference,
                chosen["residual_effort"] - least["residual_effort"],
                least["part_reference"],
                reason,
            )
        )
    else:
        verdict = SELECTION_UNJUSTIFIED
        findings.append(
            "%s was available at %.4g effort units against %.4g for %s, and the "
            "step away is not recorded against a reason the project accepts"
            % (
                least["part_reference"],
                least["residual_effort"],
                chosen["residual_effort"],
                chosen_reference,
            )
        )
    return {
        "slot": slot,
        "verdict": verdict,
        "preferred": verdict in (SELECTION_LEAST_EFFORT, SELECTION_JUSTIFIED),
        "chosen": chosen,
        "least_effort_candidate": least,
        "ranking": [item["part_reference"] for item in ranked],
        "effort_penalty": chosen["residual_effort"] - least["residual_effort"],
        "lead_penalty_weeks": (
            chosen["campaign_lead_weeks"] - least["campaign_lead_weeks"]
        ),
        "departure_reason": reason,
        "findings": findings,
    }
