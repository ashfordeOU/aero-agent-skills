#!/usr/bin/env python3
"""Baseline selection rules for a Class 3 commercial EEE part.

Anchor: ECSS-Q-ST-60-13C clause 6.2.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Class 3 is the lowest assurance category a commercial EEE part can be
procured under, and it is the one most often reached for because it
costs the least. The baseline rules exist so that "lowest assurance"
never degrades into "no rule at all": a part still has to earn its
place on the board.

Five baseline rules are applied to every candidate:

    temperature        the maker's rated range has to cover the
                       mission environment at both ends, with the
                       margin the project declares
    production status  a part still in serial production is admissible;
                       one whose end has been announced is admissible
                       only against a secured lifetime buy; a part
                       already withdrawn, or never past sample build,
                       is not
    quality system     the maker runs a certified or project-audited
                       quality system, so the line that built the part
                       is at least described
    traceability       delivery carries a lot identity and a date code,
                       because a Class 3 part is bought on its
                       population statistics and a population with no
                       identity has none
    alternative        where a higher-assurance qualified part already
                       fits the same slot, the commercial route is not
                       the one the baseline steers to

Each rule returns met, conditional or breached. The part verdict is the
worst of the five, and the rule that produced it is named as the
binding rule -- that is the single thing a project has to change to
move the answer.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PRODUCTION_STATUSES = (
    "serial-production",
    "announced-obsolete",
    "end-of-life",
    "prototype-sample",
)

QUALITY_SYSTEMS = (
    "certified-quality-system",
    "project-audited",
    "declared-not-verified",
    "none",
)

TRACEABILITY_LEVELS = (
    "lot-and-date-code",
    "date-code-only",
    "none",
)

RULE_MET = "selection-rule-met"
RULE_CONDITIONAL = "selection-rule-conditional"
RULE_BREACHED = "selection-rule-breached"

RULE_SEVERITY = {RULE_MET: 0, RULE_CONDITIONAL: 1, RULE_BREACHED: 2}

PART_ADMISSIBLE = "class-3-selection-admissible"
PART_ADMISSIBLE_WITH_ACTIONS = "class-3-selection-admissible-with-actions"
PART_NOT_ADMISSIBLE = "class-3-selection-not-admissible"

RULE_ORDER = (
    "temperature-range-coverage",
    "production-status",
    "manufacturer-quality-system",
    "lot-traceability",
    "qualified-alternative",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_temperature(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < -273.15:
        raise ValueError("%s is below absolute zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A margin is a difference of two declared temperatures, so a margin
    built to sit exactly on the required value can land a few units in
    the last place below it. The requirement is never lowered; only the
    comparison tolerates the representation error.
    """
    return value >= limit or _equal(value, limit)


def temperature_margins(rated_min_c, rated_max_c, envelope_min_c, envelope_max_c):
    """Cold-end and hot-end room between the rating and the mission."""
    rated_min = _require_temperature("rated_min_c", rated_min_c)
    rated_max = _require_temperature("rated_max_c", rated_max_c)
    env_min = _require_temperature("envelope_min_c", envelope_min_c)
    env_max = _require_temperature("envelope_max_c", envelope_max_c)
    if rated_max < rated_min:
        raise ValueError("rated_max_c must not sit below rated_min_c")
    if env_max < env_min:
        raise ValueError("envelope_max_c must not sit below envelope_min_c")
    return {
        "cold_margin_c": env_min - rated_min,
        "hot_margin_c": rated_max - env_max,
    }


def assess_temperature_rule(
    rated_min_c,
    rated_max_c,
    envelope_min_c,
    envelope_max_c,
    required_margin_c=0.0,
):
    """Grade the rated range against the mission environment."""
    required = _require_non_negative("required_margin_c", required_margin_c)
    margins = temperature_margins(
        rated_min_c, rated_max_c, envelope_min_c, envelope_max_c
    )
    cold = margins["cold_margin_c"]
    hot = margins["hot_margin_c"]
    tightest_end = "cold" if cold <= hot else "hot"
    tightest = min(cold, hot)
    if _at_least(tightest, required):
        verdict = RULE_MET
        detail = "rated range covers the mission with the declared margin"
    elif _at_least(tightest, 0.0):
        verdict = RULE_CONDITIONAL
        detail = (
            "rated range covers the mission but the %s end holds %.2f C "
            "against a required %.2f C" % (tightest_end, tightest, required)
        )
    else:
        verdict = RULE_BREACHED
        detail = (
            "the %s end of the mission sits %.2f C outside the rating"
            % (tightest_end, -tightest)
        )
    return {
        "rule": "temperature-range-coverage",
        "verdict": verdict,
        "cold_margin_c": cold,
        "hot_margin_c": hot,
        "tightest_end": tightest_end,
        "tightest_margin_c": tightest,
        "required_margin_c": required,
        "detail": detail,
    }


def assess_production_status(production_status, lifetime_buy_secured=False):
    """Grade where the part sits in the maker's own product life."""
    status = _require_choice(
        "production_status", production_status, PRODUCTION_STATUSES
    )
    secured = _require_bool("lifetime_buy_secured", lifetime_buy_secured)
    if status == "serial-production":
        verdict, detail = RULE_MET, "part is in serial production"
    elif status == "announced-obsolete" and secured:
        verdict, detail = (
            RULE_CONDITIONAL,
            "end of production announced; a secured lifetime buy carries it",
        )
    elif status == "announced-obsolete":
        verdict, detail = (
            RULE_BREACHED,
            "end of production announced with no lifetime buy secured",
        )
    elif status == "end-of-life":
        verdict, detail = RULE_BREACHED, "part is already withdrawn from supply"
    else:
        verdict, detail = (
            RULE_BREACHED,
            "part has never passed sample build into series supply",
        )
    return {
        "rule": "production-status",
        "verdict": verdict,
        "production_status": status,
        "lifetime_buy_secured": secured,
        "detail": detail,
    }


def assess_quality_system(quality_system):
    """Grade how well the line that built the part is described."""
    system = _require_choice("quality_system", quality_system, QUALITY_SYSTEMS)
    if system == "certified-quality-system":
        verdict, detail = RULE_MET, "maker runs a certified quality system"
    elif system == "project-audited":
        verdict, detail = RULE_MET, "maker's line has been audited by the project"
    elif system == "declared-not-verified":
        verdict, detail = (
            RULE_CONDITIONAL,
            "quality system is declared by the maker but never verified",
        )
    else:
        verdict, detail = RULE_BREACHED, "no quality system behind the line"
    return {
        "rule": "manufacturer-quality-system",
        "verdict": verdict,
        "quality_system": system,
        "detail": detail,
    }


def assess_traceability(traceability, single_lot_delivery=True):
    """Grade whether the delivered population can be identified later."""
    level = _require_choice("traceability", traceability, TRACEABILITY_LEVELS)
    single_lot = _require_bool("single_lot_delivery", single_lot_delivery)
    if level == "none":
        verdict, detail = (
            RULE_BREACHED,
            "delivery carries neither a lot identity nor a date code",
        )
    elif level == "date-code-only":
        verdict, detail = (
            RULE_CONDITIONAL,
            "date code without a lot identity; the population cannot be closed",
        )
    elif not single_lot:
        verdict, detail = (
            RULE_CONDITIONAL,
            "lot and date code held, but the delivery mixes more than one lot",
        )
    else:
        verdict, detail = (
            RULE_MET,
            "single lot delivered with a lot identity and a date code",
        )
    return {
        "rule": "lot-traceability",
        "verdict": verdict,
        "traceability": level,
        "single_lot_delivery": single_lot,
        "detail": detail,
    }


def assess_qualified_alternative(alternative_available, alternative_fits_slot=False):
    """Grade whether a higher-assurance part already fits the same slot."""
    available = _require_bool("alternative_available", alternative_available)
    fits = _require_bool("alternative_fits_slot", alternative_fits_slot)
    if available and fits:
        verdict, detail = (
            RULE_BREACHED,
            "a qualified higher-assurance part already fits this slot",
        )
    elif available:
        verdict, detail = (
            RULE_CONDITIONAL,
            "a qualified part exists but does not fit the slot as offered",
        )
    else:
        verdict, detail = (
            RULE_MET,
            "no qualified higher-assurance part covers this slot",
        )
    return {
        "rule": "qualified-alternative",
        "verdict": verdict,
        "alternative_available": available,
        "alternative_fits_slot": fits,
        "detail": detail,
    }


def _action_for(entry):
    rule = entry["rule"]
    if rule == "temperature-range-coverage":
        return (
            "raise the declared margin or narrow the mission environment "
            "until the %s end holds %.2f C" % (
                entry["tightest_end"], entry["required_margin_c"]
            )
        )
    if rule == "production-status":
        return "secure a lifetime buy or move to a part still in serial supply"
    if rule == "manufacturer-quality-system":
        return "audit the line or obtain the maker's quality-system certificate"
    if rule == "lot-traceability":
        return "procure a single lot delivered with a lot identity and date code"
    return "adopt the qualified part, or record why the slot rules it out"


def apply_selection_rules(candidate, envelope):
    """Full clause 6.2.2.1 baseline screen for one commercial candidate."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping, got %r" % (candidate,))
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a mapping, got %r" % (envelope,))
    for key in ("rated_min_c", "rated_max_c"):
        if key not in candidate:
            raise ValueError("candidate is missing %s" % key)
    for key in ("min_temperature_c", "max_temperature_c"):
        if key not in envelope:
            raise ValueError("envelope is missing %s" % key)

    entries = [
        assess_temperature_rule(
            candidate["rated_min_c"],
            candidate["rated_max_c"],
            envelope["min_temperature_c"],
            envelope["max_temperature_c"],
            envelope.get("required_margin_c", 0.0),
        ),
        assess_production_status(
            candidate.get("production_status"),
            candidate.get("lifetime_buy_secured", False),
        ),
        assess_quality_system(candidate.get("quality_system")),
        assess_traceability(
            candidate.get("traceability"),
            candidate.get("single_lot_delivery", True),
        ),
        assess_qualified_alternative(
            candidate.get("alternative_available", False),
            candidate.get("alternative_fits_slot", False),
        ),
    ]
    by_rule = {entry["rule"]: entry for entry in entries}
    worst = max(RULE_SEVERITY[entry["verdict"]] for entry in entries)
    binding = next(
        by_rule[rule]
        for rule in RULE_ORDER
        if RULE_SEVERITY[by_rule[rule]["verdict"]] == worst
    )
    if worst == 0:
        verdict = PART_ADMISSIBLE
    elif worst == 1:
        verdict = PART_ADMISSIBLE_WITH_ACTIONS
    else:
        verdict = PART_NOT_ADMISSIBLE
    actions = [
        {"rule": entry["rule"], "action": _action_for(entry)}
        for entry in entries
        if entry["verdict"] != RULE_MET
    ]
    findings = [
        "%s: %s" % (entry["rule"], entry["detail"])
        for entry in entries
        if entry["verdict"] != RULE_MET
    ]
    return {
        "verdict": verdict,
        "admissible": verdict != PART_NOT_ADMISSIBLE,
        "rules": entries,
        "by_rule": by_rule,
        "binding_rule": binding["rule"],
        "binding_detail": binding["detail"],
        "open_actions": actions,
        "findings": findings,
    }
