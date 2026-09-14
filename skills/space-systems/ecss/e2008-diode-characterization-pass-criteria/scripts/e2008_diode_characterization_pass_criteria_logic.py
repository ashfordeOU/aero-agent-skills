#!/usr/bin/env python3
"""Sentencing characterised protection diodes against drawing limits.

Anchor: ECSS-E-ST-20-08C clause 9.4.5.2.3. The steps below are a
paraphrase into implementable form; no standard text is reproduced.

The characterisation produced two branches of numbers. This clause
turns them into a verdict, and it names where the limits come from: the
source control drawing that governs the part, not a datasheet, not a
handbook and not the bench operator's recollection. A limit set with no
drawing reference and no issue is refused here rather than used,
because a number nobody can trace back to a controlled document cannot
carry an acceptance decision.

Two independent limits are applied to every diode:

    forward drop     measured at the drawing's stated forward test
                     current, and referred to the drawing's reference
                     junction temperature before it is compared, since
                     a diode drop moves by millivolts per kelvin and a
                     warm bench flatters every part on it

    reverse leakage  measured at the drawing's stated reverse test
                     voltage, compared as read

They fail independently and they fail for different reasons, so a part
is grouped by which limit it breached, not merely as accept or reject.
A part that meets both but sits almost on one is accepted and flagged:
it has passed today and has nothing left for the degradation the
mission will add.

The lot carries its own question. Individual rejects are expected; a
rejected share above the declared allowance says the lot, not the part,
is what failed.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIODE_ACCEPT = "diode-accept"
DIODE_ACCEPT_MARGINAL = "diode-accept-marginal"
DIODE_REJECT_FORWARD = "diode-reject-forward-voltage"
DIODE_REJECT_REVERSE = "diode-reject-reverse-leakage"
DIODE_REJECT_BOTH = "diode-reject-forward-and-reverse"

REJECT_DISPOSITIONS = (
    DIODE_REJECT_FORWARD,
    DIODE_REJECT_REVERSE,
    DIODE_REJECT_BOTH,
)

DIODE_LOT_ACCEPTED = "diode-lot-accepted"
DIODE_LOT_ACCEPTED_WITH_ADVISORY = "diode-lot-accepted-with-advisory"
DIODE_LOT_CONTAINS_REJECTS = "diode-lot-contains-rejects"
DIODE_LOT_REJECT_ALLOWANCE_EXCEEDED = "diode-lot-reject-allowance-exceeded"

DEFAULT_SENTENCING_POLICY = {
    "advisory_margin_fraction": 0.05,
    "max_lot_reject_fraction": 0.05,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return number


def _require_reference(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "%s must name a controlled document, got %r" % (name, value)
        )
    return value.strip()


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


def validate_sentencing_policy(policy):
    """Check the advisory band and lot allowance are complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "advisory_margin_fraction", policy.get("advisory_margin_fraction")
    )
    allowance = _require_fraction(
        "max_lot_reject_fraction", policy.get("max_lot_reject_fraction")
    )
    if allowance >= 1.0:
        raise ValueError(
            "max_lot_reject_fraction %g would accept a lot in which every part "
            "failed" % (allowance,)
        )
    return policy


def validate_source_control_limits(limits):
    """Refuse a limit set that cannot be traced to a drawing and an issue."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    drawing = _require_reference("drawing_reference", limits.get("drawing_reference"))
    issue = _require_reference("drawing_issue", limits.get("drawing_issue"))
    _require_positive(
        "max_forward_voltage_v", limits.get("max_forward_voltage_v")
    )
    _require_positive(
        "forward_test_current_a", limits.get("forward_test_current_a")
    )
    _require_positive(
        "max_reverse_leakage_a", limits.get("max_reverse_leakage_a")
    )
    _require_positive(
        "reverse_test_voltage_v", limits.get("reverse_test_voltage_v")
    )
    _require_number(
        "reference_junction_temperature_c",
        limits.get("reference_junction_temperature_c"),
    )
    _require_number(
        "forward_voltage_tempco_v_per_k",
        limits.get("forward_voltage_tempco_v_per_k"),
    )
    return {"drawing_reference": drawing, "drawing_issue": issue}


def refer_forward_voltage(
    measured_voltage_v, junction_temperature_c, tempco_v_per_k, reference_temperature_c
):
    """Move a measured forward drop back to the drawing's reference temperature."""
    measured = _require_positive("measured_voltage_v", measured_voltage_v)
    junction = _require_number("junction_temperature_c", junction_temperature_c)
    tempco = _require_number("tempco_v_per_k", tempco_v_per_k)
    reference = _require_number("reference_temperature_c", reference_temperature_c)
    return measured - tempco * (junction - reference)


def margin_fraction(measured, limit):
    """How far a measured value stands below the maximum it is allowed."""
    ceiling = _require_positive("limit", limit)
    value = _require_non_negative("measured", measured)
    return (ceiling - value) / ceiling


def within_limit(measured, limit):
    """True when the measured value is at or under its maximum; a tie passes."""
    ceiling = _require_positive("limit", limit)
    value = _require_non_negative("measured", measured)
    return _at_most(value, ceiling)


def margin_is_marginal(margin, policy=DEFAULT_SENTENCING_POLICY):
    """True when a passing margin leaves almost nothing for degradation."""
    validate_sentencing_policy(policy)
    value = _require_number("margin", margin)
    if value < 0.0:
        return False
    return not _at_least(value, float(policy["advisory_margin_fraction"]))


def sentence_diode(record, limits, policy=DEFAULT_SENTENCING_POLICY):
    """Group one characterised diode by which drawing limit it breached."""
    validate_sentencing_policy(policy)
    validate_source_control_limits(limits)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    part_id = _require_reference("record part_id", record.get("part_id"))
    measured_forward = _require_positive(
        "record measured_forward_voltage_v",
        record.get("measured_forward_voltage_v"),
    )
    junction = _require_number(
        "record junction_temperature_c", record.get("junction_temperature_c")
    )
    measured_leakage = _require_non_negative(
        "record measured_reverse_leakage_a",
        record.get("measured_reverse_leakage_a"),
    )

    referred = refer_forward_voltage(
        measured_forward,
        junction,
        float(limits["forward_voltage_tempco_v_per_k"]),
        float(limits["reference_junction_temperature_c"]),
    )
    forward_limit = float(limits["max_forward_voltage_v"])
    leakage_limit = float(limits["max_reverse_leakage_a"])

    forward_ok = within_limit(referred, forward_limit)
    leakage_ok = within_limit(measured_leakage, leakage_limit)
    forward_margin = margin_fraction(referred, forward_limit)
    leakage_margin = margin_fraction(measured_leakage, leakage_limit)

    breaches = []
    if not forward_ok:
        breaches.append(
            "%s: referred forward drop %.5f V is above the %.5f V drawing limit"
            % (part_id, referred, forward_limit)
        )
    if not leakage_ok:
        breaches.append(
            "%s: reverse leakage %.4g A is above the %.4g A drawing limit"
            % (part_id, measured_leakage, leakage_limit)
        )

    if not forward_ok and not leakage_ok:
        disposition = DIODE_REJECT_BOTH
    elif not forward_ok:
        disposition = DIODE_REJECT_FORWARD
    elif not leakage_ok:
        disposition = DIODE_REJECT_REVERSE
    else:
        marginal = margin_is_marginal(
            forward_margin, policy
        ) or margin_is_marginal(leakage_margin, policy)
        disposition = DIODE_ACCEPT_MARGINAL if marginal else DIODE_ACCEPT
        if marginal:
            breaches.append(
                "%s: accepted with the tighter margin at %.4f, under the %.4f "
                "advisory band, leaving little for in-orbit degradation"
                % (part_id, min(forward_margin, leakage_margin),
                   float(policy["advisory_margin_fraction"]))
            )

    return {
        "part_id": part_id,
        "referred_forward_voltage_v": referred,
        "measured_reverse_leakage_a": measured_leakage,
        "forward_margin_fraction": forward_margin,
        "reverse_margin_fraction": leakage_margin,
        "forward_within_limit": forward_ok,
        "reverse_within_limit": leakage_ok,
        "disposition": disposition,
        "notes": breaches,
    }


def lot_reject_fraction(reject_count, total_count):
    """Rejected share of the characterised lot."""
    total = total_count
    if isinstance(total, bool) or not isinstance(total, int) or total < 1:
        raise ValueError("total_count must be a whole number of at least 1")
    rejects = reject_count
    if isinstance(rejects, bool) or not isinstance(rejects, int) or rejects < 0:
        raise ValueError("reject_count must be a whole number of at least 0")
    if rejects > total:
        raise ValueError(
            "reject_count %d exceeds the lot total of %d" % (rejects, total)
        )
    return rejects / total


def sentence_diode_lot(records, limits, policy=DEFAULT_SENTENCING_POLICY):
    """Full clause 9.4.5.2.3 verdict for a characterised diode lot."""
    validate_sentencing_policy(policy)
    provenance = validate_source_control_limits(limits)
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be an ordered sequence of diode records")
    if not records:
        raise ValueError(
            "a lot with no characterised diode cannot be sentenced; an absent "
            "record set is not an accepted one"
        )

    sentenced = [sentence_diode(record, limits, policy) for record in records]
    seen = set()
    for entry in sentenced:
        if entry["part_id"] in seen:
            raise ValueError(
                "part_id %r appears twice; a lot cannot sentence one part under "
                "two records" % (entry["part_id"],)
            )
        seen.add(entry["part_id"])

    rejects = [e for e in sentenced if e["disposition"] in REJECT_DISPOSITIONS]
    marginal = [e for e in sentenced if e["disposition"] == DIODE_ACCEPT_MARGINAL]
    reject_share = lot_reject_fraction(len(rejects), len(sentenced))
    allowance = float(policy["max_lot_reject_fraction"])
    within_allowance = _at_most(reject_share, allowance)

    findings = []
    for entry in sentenced:
        findings.extend(entry["notes"])

    if not within_allowance:
        verdict = DIODE_LOT_REJECT_ALLOWANCE_EXCEEDED
        findings.append(
            "%d of %d characterised diodes were rejected, a share of %.4f above "
            "the %.4f allowance; the lot is what failed, not only the parts"
            % (len(rejects), len(sentenced), reject_share, allowance)
        )
    elif rejects:
        verdict = DIODE_LOT_CONTAINS_REJECTS
    elif marginal:
        verdict = DIODE_LOT_ACCEPTED_WITH_ADVISORY
    else:
        verdict = DIODE_LOT_ACCEPTED

    return {
        "drawing_reference": provenance["drawing_reference"],
        "drawing_issue": provenance["drawing_issue"],
        "sentenced": tuple(sentenced),
        "characterised_count": len(sentenced),
        "reject_count": len(rejects),
        "marginal_count": len(marginal),
        "lot_reject_fraction": reject_share,
        "reject_allowance_fraction": allowance,
        "within_reject_allowance": within_allowance,
        "verdict": verdict,
        "findings": findings,
    }
