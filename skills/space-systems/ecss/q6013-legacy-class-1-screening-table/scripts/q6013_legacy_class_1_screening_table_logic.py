"""Legacy screening test-list assessment for highest-assurance active parts.

Anchor: ECSS-Q-ST-60-13C Table 8-10 (the screening test list applied to
active commercial parts procured under the highest assurance class, where
the part has legacy standing). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the delivered lot. Screening is applied to every part, not to a
   sample, so the lot size is the quantity entering the first screen and no
   screen may reject more parts than entered it.
2. Check the declared sequence covers every required screen once AND keeps
   the canonical order. Screening order carries meaning: a stress applied
   after the measurement that was supposed to catch its damage proves
   nothing, and an electrical reading taken before the stress that moves it
   is not a post-stress reading.
3. Enforce the bracket explicitly. Burn-in is only a screen when a pre-
   reading and a post-reading of the same parameters sit either side of it;
   the pair is what turns burn-in into a measurement rather than a soak.
4. Walk the sequence cumulatively. Each screen receives what the previous
   screen passed, removes its rejects, and hands the remainder on.
5. Reduce the burn-in bracket into a per-part drift: each parameter's change
   between the pre- and post-readings, as a percentage of the pre-reading,
   against a declared drift band. A part inside every count-based screen but
   outside a drift band is still removed. A removed part is a removal, not
   a finding against the lot: the lot is judged on how many were removed.
6. Compare the cumulative percent defective of the whole lot with the
   allowable. Over the allowable the lot is rejected as a whole, even though
   the parts that survived every screen are individually good: the lot has
   shown itself to be the wrong lot.
"""

import math

__all__ = [
    "REQUIRED_SCREENS",
    "BURN_IN_SCREEN",
    "PRE_BURN_IN_SCREEN",
    "POST_BURN_IN_SCREEN",
    "PDA_TOLERANCE",
    "DRIFT_TOLERANCE",
    "validate_lot_size",
    "parameter_drift_percent",
    "part_drift_verdict",
    "screen_coverage",
    "sequence_findings",
    "walk_sequence",
    "percent_defective",
    "assess_legacy_screening_table",
]

# The canonical screening order for an active part. Membership is required
# and the relative order is part of the requirement.
REQUIRED_SCREENS = (
    "internal-visual",
    "temperature-cycling",
    "constant-acceleration",
    "particle-impact-noise-detection",
    "seal-test",
    "pre-burn-in-electrical",
    "burn-in",
    "post-burn-in-electrical",
    "final-electrical-at-temperature-extremes",
    "radiographic-inspection",
    "external-visual",
)

BURN_IN_SCREEN = "burn-in"
PRE_BURN_IN_SCREEN = "pre-burn-in-electrical"
POST_BURN_IN_SCREEN = "post-burn-in-electrical"

# A percent defective sitting exactly on the allowable is a representation
# question, not an engineering one.
PDA_TOLERANCE = 1e-9

# The same for a drift sitting exactly on its band.
DRIFT_TOLERANCE = 1e-9


def _real(label, value):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _name(label, value):
    """Return value as a stripped non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty name, got %r" % (label, value))
    return value.strip()


def validate_lot_size(lot_size):
    """Return the validated quantity of parts entering the screening sequence."""
    size = _count("lot_size", lot_size)
    if size < 1:
        raise ValueError("lot_size must be at least one part, got %d" % size)
    return size


def parameter_drift_percent(pre_value, post_value):
    """Return the change of a parameter across burn-in, in percent of the pre-reading.

    The pre-reading is the reference, so a parameter that read zero before
    burn-in has no percentage to move by and is an input error rather than
    an infinite drift.
    """
    pre = _real("pre-burn-in reading", pre_value)
    post = _real("post-burn-in reading", post_value)
    if pre == 0.0:
        raise ValueError("a pre-burn-in reading of zero has no percentage drift")
    return 100.0 * (post - pre) / abs(pre)


def part_drift_verdict(part, bands):
    """Return the drift record of one part across the burn-in bracket.

    part keys: reference, pre (a parameter -> reading mapping) and post (the
    same parameters after burn-in). bands maps each parameter to the
    magnitude of drift, in percent, the part may show and stay in the lot.
    """
    if not isinstance(part, dict):
        raise ValueError("a part must be a mapping, got %r" % (part,))
    for key in ("reference", "pre", "post"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)
    if not isinstance(bands, dict) or not bands:
        raise ValueError("drift bands must be a non-empty mapping")
    reference = _name("part reference", part["reference"])
    pre = part["pre"]
    post = part["post"]
    if not isinstance(pre, dict) or not isinstance(post, dict):
        raise ValueError("part readings must be mappings of parameter to value")
    drifts = {}
    exceeded = []
    for parameter in sorted(bands):
        band = _real("drift band", bands[parameter])
        if band < 0.0:
            raise ValueError("a drift band must be non-negative, got %g" % band)
        if parameter not in pre:
            raise ValueError(
                "part '%s' has no pre-burn-in reading for '%s'" % (reference, parameter)
            )
        if parameter not in post:
            raise ValueError(
                "part '%s' has no post-burn-in reading for '%s'" % (reference, parameter)
            )
        drift = parameter_drift_percent(pre[parameter], post[parameter])
        drifts[parameter] = drift
        if abs(drift) > band + DRIFT_TOLERANCE:
            exceeded.append(parameter)
    return {
        "reference": reference,
        "drift_percent": drifts,
        "exceeded": exceeded,
        "retained": not exceeded,
    }


def screen_coverage(declared):
    """Return the coverage record of a declared screening sequence."""
    if not isinstance(declared, (list, tuple)) or not declared:
        raise ValueError("the sequence must be a non-empty list of screens")
    seen = []
    duplicates = []
    unknown = []
    for index, entry in enumerate(declared):
        if not isinstance(entry, dict):
            raise ValueError("sequence[%d] must be a mapping" % index)
        screen = entry.get("screen")
        if not isinstance(screen, str) or not screen.strip():
            raise ValueError("sequence[%d] needs a non-empty 'screen'" % index)
        screen = screen.strip()
        if screen in seen and screen not in duplicates:
            duplicates.append(screen)
        if screen not in seen:
            seen.append(screen)
        if screen not in REQUIRED_SCREENS and screen not in unknown:
            unknown.append(screen)
    missing = [s for s in REQUIRED_SCREENS if s not in seen]
    return {
        "declared": seen,
        "missing": missing,
        "duplicated": duplicates,
        "unrecognized": unknown,
        "complete": not missing and not duplicates,
    }


def sequence_findings(declared):
    """Return the ordering findings of a declared screening sequence.

    Order is checked on the required screens only: an extra screen may be
    inserted anywhere, but the required ones keep their relative order and
    burn-in stays bracketed by its two electrical readings.
    """
    coverage = screen_coverage(declared)
    order = [s for s in coverage["declared"] if s in REQUIRED_SCREENS]
    findings = []
    canonical = [s for s in REQUIRED_SCREENS if s in order]
    if order != canonical:
        for position, screen in enumerate(order):
            if screen != canonical[position]:
                findings.append(
                    "screen '%s' is declared where '%s' belongs in the sequence"
                    % (screen, canonical[position])
                )
                break
    positions = {screen: index for index, screen in enumerate(coverage["declared"])}
    if BURN_IN_SCREEN in positions:
        pre_at = positions.get(PRE_BURN_IN_SCREEN)
        post_at = positions.get(POST_BURN_IN_SCREEN)
        burn_at = positions[BURN_IN_SCREEN]
        if pre_at is None or pre_at > burn_at:
            findings.append("burn-in has no electrical reading in front of it")
        if post_at is None or post_at < burn_at:
            findings.append("burn-in has no electrical reading behind it")
    return {
        "coverage": coverage,
        "order": order,
        "ordered": not findings,
        "findings": findings,
    }


def walk_sequence(declared, lot_size):
    """Return the per-screen record of a lot walked through its sequence.

    Every screen is applied to the whole quantity that reached it; each one
    removes its rejects and hands the remainder to the next.
    """
    lot = validate_lot_size(lot_size)
    if not isinstance(declared, (list, tuple)) or not declared:
        raise ValueError("the sequence must be a non-empty list of screens")
    entering = lot
    steps = []
    for index, entry in enumerate(declared):
        if not isinstance(entry, dict):
            raise ValueError("sequence[%d] must be a mapping" % index)
        screen = _name("screen", entry.get("screen"))
        if "rejects" not in entry:
            raise ValueError("screen '%s' does not declare its reject count" % screen)
        rejects = _count("rejects", entry["rejects"])
        if rejects > entering:
            raise ValueError(
                "screen '%s' rejects %d parts from the %d that reached it"
                % (screen, rejects, entering)
            )
        remaining = entering - rejects
        steps.append(
            {
                "screen": screen,
                "entering": entering,
                "rejects": rejects,
                "remaining": remaining,
            }
        )
        entering = remaining
    return {
        "lot_size": lot,
        "steps": steps,
        "count_rejects": sum(step["rejects"] for step in steps),
        "surviving": entering,
    }


def percent_defective(rejects, lot_size):
    """Return the share of the lot removed by screening, in percent."""
    lot = validate_lot_size(lot_size)
    removed = _count("rejects", rejects)
    if removed > lot:
        raise ValueError(
            "screening removed %d parts from a lot of %d" % (removed, lot)
        )
    return 100.0 * removed / lot


def assess_legacy_screening_table(spec):
    """Run the full Table 8-10 legacy screening assessment.

    spec keys: lot_size, sequence (each screen with its reject count),
    percent_defective_allowable and optional drift_bands plus parts (the
    pre- and post-burn-in readings of the parts that reached the bracket).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "sequence", "percent_defective_allowable"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot_size = validate_lot_size(spec["lot_size"])
    allowable = _real("percent_defective_allowable", spec["percent_defective_allowable"])
    if allowable < 0.0 or allowable > 100.0:
        raise ValueError(
            "the allowable percent defective must lie in [0, 100], got %g" % allowable
        )
    ordering = sequence_findings(spec["sequence"])
    walk = walk_sequence(spec["sequence"], lot_size)
    bands = spec.get("drift_bands")
    parts = spec.get("parts") or []
    if not isinstance(parts, (list, tuple)):
        raise ValueError("parts must be a sequence of pre- and post-readings")
    drift_records = []
    drift_rejects = 0
    if parts:
        if not bands:
            raise ValueError("parts were offered with no drift bands to judge them by")
        for part in parts:
            record = part_drift_verdict(part, bands)
            drift_records.append(record)
            if not record["retained"]:
                drift_rejects += 1
    if drift_rejects > walk["surviving"]:
        raise ValueError(
            "%d parts drifted out of the %d that survived the counted screens"
            % (drift_rejects, walk["surviving"])
        )
    total_rejects = walk["count_rejects"] + drift_rejects
    defective = percent_defective(total_rejects, lot_size)
    within_pda = defective <= allowable + PDA_TOLERANCE
    findings = []
    for screen in ordering["coverage"]["missing"]:
        findings.append("required screen '%s' is absent from the sequence" % screen)
    for screen in ordering["coverage"]["duplicated"]:
        findings.append("screen '%s' is declared more than once" % screen)
    findings.extend(ordering["findings"])
    removed_parts = []
    for record in drift_records:
        for parameter in record["exceeded"]:
            removed_parts.append(
                "part '%s' drifted outside the band on '%s'"
                % (record["reference"], parameter)
            )
    if not within_pda:
        findings.append(
            "the lot is %.4f%% defective against a %.4f%% allowable"
            % (defective, allowable)
        )
    released = ordering["ordered"] and ordering["coverage"]["complete"] and within_pda
    advisories = []
    if within_pda and allowable > 0.0 and defective >= allowable - PDA_TOLERANCE:
        advisories.append("the lot used the whole allowable percent defective")
    for screen in ordering["coverage"]["unrecognized"]:
        advisories.append("screen '%s' is an addition to the required sequence" % screen)
    advisories.extend(removed_parts)
    return {
        "lot_size": lot_size,
        "coverage": ordering["coverage"],
        "ordering_findings": ordering["findings"],
        "steps": walk["steps"],
        "count_rejects": walk["count_rejects"],
        "drift_records": drift_records,
        "drift_rejects": drift_rejects,
        "removed_parts": removed_parts,
        "total_rejects": total_rejects,
        "delivered_quantity": lot_size - total_rejects,
        "percent_defective": defective,
        "percent_defective_allowable": allowable,
        "within_allowable": within_pda,
        "released": released,
        "disposition": "release-for-acceptance" if released else "reject-lot",
        "findings": findings,
        "advisories": advisories,
    }
