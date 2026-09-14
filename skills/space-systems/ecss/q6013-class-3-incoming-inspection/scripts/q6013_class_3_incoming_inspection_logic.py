"""Receiving inspection of a lowest-assurance commercial EEE delivery.

Anchor: ECSS-Q-ST-60-13C clause 6.3.7 (receiving inspection of deliveries of
commercial parts of the lowest assurance category, which at this category may
be carried out at the supplier's own premises rather than at the receiving
organisation's dock). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Test the delegation claim that lets a source inspection at the supplier
   premises stand in for the receiving organisation's own inspection: the
   surveillance audit behind the supplier has to still be current, a signed
   source inspection report has to exist, that report has to cover every
   criterion the delivery is judged on, and the part family has to be one the
   category allows to be inspected away from the dock.
2. Size the source inspection sample from the delivered quantity with an exact
   integer percentage plan bounded by a declared floor and cap, so the sample
   is reproducible and never larger than the lot.
3. Judge the defects the source report records against the sample's accept
   number.
4. Run the residual dock duties that no delegation removes: package integrity,
   identity and quantity reconciliation, and the documents that travel with
   the parts.
5. Dispose the delivery: released to stores only when the delegation stands
   and nothing was found, sent back for a full dock inspection when the
   delegation does not stand, and quarantined whenever a residual duty or the
   source sample failed.
"""

import math

__all__ = [
    "REQUIRED_SOURCE_CRITERIA",
    "NON_DELEGABLE_FAMILIES",
    "RESIDUAL_DOCK_DUTIES",
    "DEFAULT_SURVEILLANCE_VALIDITY_MONTHS",
    "DEFAULT_SOURCE_SAMPLE_PERCENT",
    "DEFAULT_SOURCE_SAMPLE_FLOOR",
    "DEFAULT_SOURCE_SAMPLE_CAP",
    "RECEIPT_TOLERANCE",
    "surveillance_currency",
    "source_criteria_gaps",
    "family_is_delegable",
    "delegation_decision",
    "source_sample_size",
    "source_sample_verdict",
    "residual_dock_findings",
    "assess_class3_incoming_inspection",
]

# The criteria a source inspection report has to speak to before it can stand
# in for an inspection the receiving organisation would otherwise do itself.
REQUIRED_SOURCE_CRITERIA = (
    "external-visual",
    "marking-legibility",
    "lead-and-terminal-condition",
    "packaging-and-esd-protection",
)

# Part families kept at the dock whatever the supplier offers, because their
# failure modes are not visible in a supplier's own routine inspection.
NON_DELEGABLE_FAMILIES = (
    "hybrid",
    "high-voltage",
    "custom-asic",
)

# Duties the receiving organisation always performs on arrival. Delegation
# thins what is inspected at the supplier; it removes none of these.
RESIDUAL_DOCK_DUTIES = (
    "package-integrity",
    "identity-reconciliation",
    "quantity-reconciliation",
    "delivery-documentation",
)

DEFAULT_SURVEILLANCE_VALIDITY_MONTHS = 24.0
DEFAULT_SOURCE_SAMPLE_PERCENT = 2
DEFAULT_SOURCE_SAMPLE_FLOOR = 3
DEFAULT_SOURCE_SAMPLE_CAP = 50

# Audit-age comparisons land on the validity limit exactly in the normal case;
# absorb representation error here rather than by moving the limit.
RECEIPT_TOLERANCE = 1e-9


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _real(label, value):
    """Return value as a finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _text(label, value):
    """Return a stripped, lower-cased, non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower()


def _flag(label, value):
    """Return value as a strict boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (label, value))
    return value


def surveillance_currency(audit_age_months, validity_months=DEFAULT_SURVEILLANCE_VALIDITY_MONTHS):
    """Return the currency of the supplier surveillance audit.

    An audit whose age sits exactly on the validity limit is still current;
    the tolerance absorbs representation error only and does not move the
    limit.
    """
    age = _real("audit_age_months", audit_age_months)
    validity = _real("validity_months", validity_months)
    if age < 0.0:
        raise ValueError("audit_age_months must be non-negative, got %g" % age)
    if validity <= 0.0:
        raise ValueError("validity_months must be positive, got %g" % validity)
    current = age < validity or math.isclose(
        age, validity, rel_tol=0.0, abs_tol=RECEIPT_TOLERANCE
    )
    return {
        "audit_age_months": age,
        "validity_months": validity,
        "months_remaining": validity - age,
        "current": current,
    }


def source_criteria_gaps(covered, required=REQUIRED_SOURCE_CRITERIA):
    """Return the required source-inspection criteria the report does not cover."""
    if isinstance(covered, (list, tuple, set, frozenset)):
        covered = {str(item): True for item in covered}
    if not isinstance(covered, dict):
        raise ValueError("covered must be a mapping or a sequence of criterion names")
    seen = {}
    for key, value in covered.items():
        name = _text("criterion name", key)
        seen[name] = _flag("covered['%s']" % name, value)
    gaps = []
    for item in required:
        if not seen.get(_text("required criterion", item), False):
            gaps.append(_text("required criterion", item))
    return gaps


def family_is_delegable(part_family, blocked=NON_DELEGABLE_FAMILIES):
    """Return whether this part family may be inspected at the supplier premises."""
    name = _text("part_family", part_family)
    blocked_names = {_text("blocked family", item) for item in blocked}
    return name not in blocked_names


def delegation_decision(claim):
    """Return whether a source inspection at the supplier premises may stand.

    claim keys: part_family, audit_age_months, source_report_present,
    source_report_signed, covered_criteria, and optional
    surveillance_validity_months.
    """
    if not isinstance(claim, dict):
        raise ValueError("claim must be a mapping")
    for key in (
        "part_family",
        "audit_age_months",
        "source_report_present",
        "source_report_signed",
        "covered_criteria",
    ):
        if key not in claim:
            raise ValueError("claim missing required key '%s'" % key)
    family = _text("part_family", claim["part_family"])
    delegable = family_is_delegable(family)
    audit = surveillance_currency(
        claim["audit_age_months"],
        claim.get("surveillance_validity_months", DEFAULT_SURVEILLANCE_VALIDITY_MONTHS),
    )
    present = _flag("source_report_present", claim["source_report_present"])
    signed = _flag("source_report_signed", claim["source_report_signed"])
    gaps = source_criteria_gaps(claim["covered_criteria"])
    reasons = []
    if not delegable:
        reasons.append("part family '%s' is inspected at the dock at this category" % family)
    if not audit["current"]:
        reasons.append(
            "supplier surveillance audit is %.2f month(s) old against a validity of %.2f"
            % (audit["audit_age_months"], audit["validity_months"])
        )
    if not present:
        reasons.append("no source inspection report accompanied the delivery")
    elif not signed:
        reasons.append("the source inspection report is unsigned")
    if gaps:
        reasons.append("source report does not cover: %s" % ", ".join(gaps))
    return {
        "part_family": family,
        "family_delegable": delegable,
        "audit": audit,
        "report_present": present,
        "report_signed": signed,
        "uncovered_criteria": gaps,
        "granted": not reasons,
        "reasons": reasons,
    }


def source_sample_size(
    lot_size,
    percent=DEFAULT_SOURCE_SAMPLE_PERCENT,
    floor=DEFAULT_SOURCE_SAMPLE_FLOOR,
    cap=DEFAULT_SOURCE_SAMPLE_CAP,
):
    """Return the source inspection sample size for a delivered lot.

    Exact ceiling of percent/100 of the lot, computed in integer arithmetic,
    raised to the declared floor, limited by the declared cap and never larger
    than the lot itself. The same lot gives the same sample on every platform.
    """
    lot = _count("lot_size", lot_size)
    pct = _count("percent", percent)
    low = _count("floor", floor)
    high = _count("cap", cap)
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    if pct < 1 or pct > 100:
        raise ValueError("percent must lie in 1..100, got %d" % pct)
    if low < 1:
        raise ValueError("floor must be at least 1, got %d" % low)
    if high < low:
        raise ValueError("cap %d is below floor %d" % (high, low))
    proportional = -((-lot * pct) // 100)
    size = max(proportional, low)
    size = min(size, high)
    return min(size, lot)


def source_sample_verdict(sample_size, defects, accept_number=0):
    """Return the verdict on the defects the source report records."""
    sample = _count("sample_size", sample_size)
    found = _count("defects", defects)
    accept = _count("accept_number", accept_number)
    if sample < 1:
        raise ValueError("sample_size must be at least 1, got %d" % sample)
    if found > sample:
        raise ValueError("defects %d exceed the sample size %d" % (found, sample))
    return {
        "sample_size": sample,
        "defects": found,
        "accept_number": accept,
        "defect_fraction": found / sample,
        "accepted": found <= accept,
    }


def residual_dock_findings(observations, duties=RESIDUAL_DOCK_DUTIES):
    """Return the residual dock duties that were not satisfied on arrival."""
    if not isinstance(observations, dict):
        raise ValueError("observations must be a mapping of duty name to True or False")
    seen = {}
    for key, value in observations.items():
        name = _text("duty name", key)
        seen[name] = _flag("observations['%s']" % name, value)
    duty_names = [_text("duty", item) for item in duties]
    unknown = sorted(set(seen) - set(duty_names))
    if unknown:
        raise ValueError("unknown residual dock duty: %s" % ", ".join(unknown))
    return [name for name in duty_names if not seen.get(name, False)]


def assess_class3_incoming_inspection(spec):
    """Run the full clause 6.3.7 receiving inspection of one delivery.

    spec keys: part_family, audit_age_months, source_report_present,
    source_report_signed, covered_criteria, received_quantity, source_defects,
    dock_observations, and optional surveillance_validity_months,
    accept_number, sample_percent, sample_floor and sample_cap.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "part_family",
        "audit_age_months",
        "source_report_present",
        "source_report_signed",
        "covered_criteria",
        "received_quantity",
        "source_defects",
        "dock_observations",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    quantity = _count("received_quantity", spec["received_quantity"])
    if quantity < 1:
        raise ValueError("received_quantity must be at least 1 to inspect a delivery")
    delegation = delegation_decision(
        {
            "part_family": spec["part_family"],
            "audit_age_months": spec["audit_age_months"],
            "source_report_present": spec["source_report_present"],
            "source_report_signed": spec["source_report_signed"],
            "covered_criteria": spec["covered_criteria"],
            "surveillance_validity_months": spec.get(
                "surveillance_validity_months", DEFAULT_SURVEILLANCE_VALIDITY_MONTHS
            ),
        }
    )
    sample = source_sample_size(
        quantity,
        spec.get("sample_percent", DEFAULT_SOURCE_SAMPLE_PERCENT),
        spec.get("sample_floor", DEFAULT_SOURCE_SAMPLE_FLOOR),
        spec.get("sample_cap", DEFAULT_SOURCE_SAMPLE_CAP),
    )
    source = source_sample_verdict(
        sample, spec["source_defects"], spec.get("accept_number", 0)
    )
    residual = residual_dock_findings(spec["dock_observations"])
    findings = []
    for reason in delegation["reasons"]:
        findings.append("delegation refused: %s" % reason)
    if delegation["granted"] and not source["accepted"]:
        findings.append(
            "%d defect(s) in a source sample of %d exceed the accept number %d"
            % (source["defects"], source["sample_size"], source["accept_number"])
        )
    for duty in residual:
        findings.append("residual dock duty not satisfied: %s" % duty)
    held = bool(residual) or (delegation["granted"] and not source["accepted"])
    if held:
        disposition = "quarantine"
    elif not delegation["granted"]:
        disposition = "dock-inspection-required"
    else:
        disposition = "release-to-stores"
    return {
        "received_quantity": quantity,
        "delegation": delegation,
        "source_sample": source,
        "residual_findings": residual,
        "accepted": disposition == "release-to-stores",
        "disposition": disposition,
        "findings": findings,
    }
