#!/usr/bin/env python3
"""ECSS-E-ST-10-12C §5.1.3 radiation design margin — single-event effects (SEE).
Paraphrase, not verbatim copy.

Common-knowledge summary (standards-map.yaml, ecss: gated false): the radiation
hardness assurance standard's margin approach for single-event effects (§5.1.3)
splits parts into two assessment tracks. Destructive effects (SEL, SEB, SEGR)
require a LET-threshold margin: the ratio of the measured LET threshold to the
worst-case environment LET must meet or exceed the required RDM factor (minimum
2.0). Non-destructive effects (SEU, SEFI, SET) require a rate margin: the
predicted upset rate multiplied by the RDM factor must not exceed the allowable
rate set by the system upset budget. This module implements effect-type
categorization, LET-margin computation, rate-margin computation, per-part
compliance checking, and multi-part assessment aggregation; it does not implement
the radiation environment model or the shielding analysis.
"""

DEFAULT_RDM_MIN = 2.0

DESTRUCTIVE_EFFECTS = frozenset({"SEL", "SEB", "SEGR"})
NON_DESTRUCTIVE_EFFECTS = frozenset({"SEU", "SEFI", "SET"})
_ALL_EFFECTS = DESTRUCTIVE_EFFECTS | NON_DESTRUCTIVE_EFFECTS


class SEEError(ValueError):
    """Invalid input to an SEE margin function."""


def categorize_effect(effect_type):
    """Return 'destructive' or 'non_destructive' for a known SEE effect type.

    Raises SEEError for any unrecognized effect type string.
    """
    key = effect_type.strip().upper()
    if key in DESTRUCTIVE_EFFECTS:
        return "destructive"
    if key in NON_DESTRUCTIVE_EFFECTS:
        return "non_destructive"
    raise SEEError(
        "Unknown SEE effect type %r. Recognized: %s"
        % (effect_type, ", ".join(sorted(_ALL_EFFECTS)))
    )


def compute_let_margin(let_threshold, let_environment):
    """LET margin = let_threshold / let_environment for a destructive-track part.

    Both values must be strictly positive (MeV·cm²/mg). A threshold at or below
    the environment LET means the device can trigger at the prevailing fluence
    before any margin is applied.

    Raises SEEError for a non-positive argument.
    """
    if let_threshold <= 0:
        raise SEEError(
            "let_threshold must be > 0 MeV·cm²/mg, got %r" % (let_threshold,)
        )
    if let_environment <= 0:
        raise SEEError(
            "let_environment must be > 0 MeV·cm²/mg, got %r" % (let_environment,)
        )
    return let_threshold / let_environment


def compute_rate_margin(predicted_rate, allowable_rate, rdm_min):
    """Rate margin = allowable_rate / (predicted_rate × rdm_min) for a non-destructive part.

    A margin >= 1.0 means the derated budget (allowable / rdm_min) covers the
    predicted rate. A predicted_rate of exactly 0 returns infinity (always passes).

    Raises SEEError for a negative predicted_rate, a non-positive allowable_rate,
    or a non-positive rdm_min.
    """
    if predicted_rate < 0:
        raise SEEError(
            "predicted_rate must be >= 0 events/device/day, got %r" % (predicted_rate,)
        )
    if allowable_rate <= 0:
        raise SEEError(
            "allowable_rate must be > 0 events/device/day, got %r" % (allowable_rate,)
        )
    if rdm_min <= 0:
        raise SEEError("rdm_min must be > 0, got %r" % (rdm_min,))
    if predicted_rate == 0:
        return float("inf")
    return allowable_rate / (predicted_rate * rdm_min)


def check_see_compliance(part_id, category, margin, rdm_min):
    """Compliance result for one part given its computed margin.

    For the destructive track: passes when margin >= rdm_min.
    For the non-destructive track: passes when margin >= 1.0
    (i.e. allowable_rate / (predicted_rate * rdm_min) >= 1.0).

    Returns a dict:
      part_id    — the supplied identifier
      category   — 'destructive' or 'non_destructive'
      margin     — the computed margin value
      rdm_min    — the required minimum RDM factor
      compliant  — True when the part passes its track threshold
      finding    — None if compliant; violation dict otherwise

    Raises SEEError for an unknown category.
    """
    if category == "destructive":
        threshold = rdm_min
    elif category == "non_destructive":
        threshold = 1.0
    else:
        raise SEEError(
            "Unknown category %r; expected 'destructive' or 'non_destructive'"
            % (category,)
        )
    compliant = margin >= threshold
    finding = (
        None
        if compliant
        else {
            "issue": "see_margin_below_threshold",
            "part_id": part_id,
            "category": category,
            "margin": margin,
            "threshold": threshold,
            "rdm_min": rdm_min,
        }
    )
    return {
        "part_id": part_id,
        "category": category,
        "margin": margin,
        "rdm_min": rdm_min,
        "compliant": compliant,
        "finding": finding,
    }


def assess_part(part_spec, rdm_min=DEFAULT_RDM_MIN):
    """Full SEE-RDM assessment for one part specification dict.

    Required keys:
      part_id      — string identifier
      effect_type  — one of: SEL, SEB, SEGR (destructive) or SEU, SEFI, SET (non-destructive)

    For the destructive track (SEL, SEB, SEGR):
      let_threshold   — measured LET threshold in MeV·cm²/mg (from heavy-ion test data)
      let_environment — worst-case environment LET at the device location in MeV·cm²/mg

    For the non-destructive track (SEU, SEFI, SET):
      predicted_rate  — predicted upset rate in events/device/day
      allowable_rate  — allowable upset rate from the system budget in events/device/day

    Optional:
      rdm_min — per-part override of the minimum required RDM factor

    Returns a dict with all intermediate values, the computed margin, and the
    compliance result. Does not mutate the input dict.

    Raises SEEError for any missing or invalid field.
    """
    part_id = part_spec.get("part_id", "<unknown>")
    effect_type = part_spec.get("effect_type")
    if effect_type is None:
        raise SEEError("Part %r: missing required field 'effect_type'" % (part_id,))

    effective_rdm = part_spec.get("rdm_min", rdm_min)
    category = categorize_effect(effect_type)

    if category == "destructive":
        let_threshold = part_spec.get("let_threshold")
        let_environment = part_spec.get("let_environment")
        if let_threshold is None:
            raise SEEError(
                "Part %r: destructive effect requires 'let_threshold'" % (part_id,)
            )
        if let_environment is None:
            raise SEEError(
                "Part %r: destructive effect requires 'let_environment'" % (part_id,)
            )
        margin = compute_let_margin(let_threshold, let_environment)
        compliance = check_see_compliance(part_id, category, margin, effective_rdm)
        return {
            "part_id": part_id,
            "effect_type": effect_type.strip().upper(),
            "category": category,
            "let_threshold": let_threshold,
            "let_environment": let_environment,
            "margin": margin,
            "rdm_min": effective_rdm,
            "compliant": compliance["compliant"],
            "finding": compliance["finding"],
        }

    # non-destructive track
    predicted_rate = part_spec.get("predicted_rate")
    allowable_rate = part_spec.get("allowable_rate")
    if predicted_rate is None:
        raise SEEError(
            "Part %r: non-destructive effect requires 'predicted_rate'" % (part_id,)
        )
    if allowable_rate is None:
        raise SEEError(
            "Part %r: non-destructive effect requires 'allowable_rate'" % (part_id,)
        )
    margin = compute_rate_margin(predicted_rate, allowable_rate, effective_rdm)
    compliance = check_see_compliance(part_id, category, margin, effective_rdm)
    return {
        "part_id": part_id,
        "effect_type": effect_type.strip().upper(),
        "category": category,
        "predicted_rate": predicted_rate,
        "allowable_rate": allowable_rate,
        "margin": margin,
        "rdm_min": effective_rdm,
        "compliant": compliance["compliant"],
        "finding": compliance["finding"],
    }


def assess_all(parts, rdm_min=DEFAULT_RDM_MIN):
    """Assess a list of part specification dicts.

    Returns a list of assessment result dicts in the same order as the input.
    Does not mutate the input list or any of its dicts.
    Raises SEEError on the first invalid part encountered.
    """
    return [assess_part(p, rdm_min) for p in parts]


def see_findings(assessment_results):
    """Non-compliant findings from an assess_all result list.

    Returns a list of finding dicts for every part that did not meet its
    required margin. An empty list means all parts pass.
    """
    return [r["finding"] for r in assessment_results if not r["compliant"]]
