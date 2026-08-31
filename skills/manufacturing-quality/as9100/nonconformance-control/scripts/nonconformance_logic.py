#!/usr/bin/env python3
"""AS9100 nonconformance control logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, as9100: gated):
AS9100 clause 10.2 requires the organization to control nonconforming
output: identify it, segregate (quarantine) it so it cannot be used or
delivered, and disposition it through a defined authority such as a
material review board (MRB). Disposition options are rework (bring back
to the original specification), repair (restore function but not full
original conformance), scrap, use-as-is (derogation/waiver, typically
customer-approved), and return to supplier. Reworked output is re-verified
against the original acceptance criteria before release. Safety-critical
parts get the strictest treatment: any disposition that leaves the part
outside the original specification is not acceptable.

Disposition decision logic (documented, in order):
1. safety-critical and not reworkable          -> scrap
2. reworkable and rework meets the spec        -> rework
3. repairable and not safety-critical          -> repair
4. reworkable, rework misses the spec, and not
   repairable                                  -> scrap
5. otherwise, use-as-is is allowed only when
   not safety-critical; safety-critical
   leftovers are scrapped                      -> use-as-is | scrap
"""

NONCONFORMANCE_TYPES = frozenset({"dimensional", "material", "process", "finish"})

DISPOSITIONS = frozenset({"rework", "repair", "scrap", "use-as-is", "return-to-supplier"})

MRB_DISPOSITIONS = frozenset({"repair", "use-as-is"})

# Checks a complete disposition record must cover, per 10.2 practice:
# identification, segregation, disposition, disposition authority, and
# customer notification.
RECORD_CHECKS = (
    "identified",
    "segregated",
    "disposition",
    "authority",
    "customer_notified",
)


def disposition_decision(
    nonconformance_type,
    reworkable,
    repairable,
    within_spec_after_rework,
    safety_critical,
):
    """Pick the disposition for a nonconforming part.

    Args:
        nonconformance_type: one of dimensional, material, process, finish.
        reworkable: whether rework can bring the part back to spec.
        repairable: whether repair can restore the part's function.
        within_spec_after_rework: whether rework actually meets the spec.
        safety_critical: whether the part is safety-critical.

    Returns one of: rework, repair, scrap, use-as-is.
    """
    if nonconformance_type not in NONCONFORMANCE_TYPES:
        raise ValueError(
            "unknown nonconformance type: %r (expected one of %s)"
            % (nonconformance_type, ", ".join(sorted(NONCONFORMANCE_TYPES)))
        )
    if safety_critical and not reworkable:
        return "scrap"
    if reworkable and within_spec_after_rework:
        return "rework"
    if repairable and not safety_critical:
        return "repair"
    if reworkable and not within_spec_after_rework and not repairable:
        return "scrap"
    if not safety_critical:
        return "use-as-is"
    return "scrap"


def rework_requires_reverification(disposition, characteristic_critical):
    """Reworked critical characteristics are re-verified before release."""
    if disposition not in DISPOSITIONS:
        raise ValueError("unknown disposition: %r" % (disposition,))
    return disposition == "rework" and bool(characteristic_critical)


def mrb_approval_required(disposition):
    """Repair and use-as-is need material review board (MRB) approval."""
    if disposition not in DISPOSITIONS:
        raise ValueError("unknown disposition: %r" % (disposition,))
    return disposition in MRB_DISPOSITIONS


def disposition_record_complete(
    identified, segregated, disposition, authority, customer_notified
):
    """A disposition record is complete only when all five 10.2 checks hold:
    identification, segregation, disposition, disposition authority, and
    customer notification."""
    checks = {
        "identified": bool(identified),
        "segregated": bool(segregated),
        "disposition": bool(disposition),
        "authority": bool(authority),
        "customer_notified": bool(customer_notified),
    }
    missing = [name for name in RECORD_CHECKS if not checks[name]]
    return {
        "checks": sum(checks.values()),
        "total": len(checks),
        "complete": not missing,
        "missing": missing,
    }


def nonconformance_summary(
    nonconformance_type,
    reworkable,
    repairable,
    within_spec_after_rework,
    safety_critical,
    characteristic_critical=False,
    identified=True,
    segregated=True,
    disposition=True,
    authority=True,
    customer_notified=True,
):
    """Convenience: run the full disposition pipeline and summarize it."""
    disposition = disposition_decision(
        nonconformance_type,
        reworkable,
        repairable,
        within_spec_after_rework,
        safety_critical,
    )
    return {
        "disposition": disposition,
        "rework_reverification": rework_requires_reverification(
            disposition, characteristic_critical
        ),
        "mrb_required": mrb_approval_required(disposition),
        "record_complete": disposition_record_complete(
            identified, segregated, disposition, authority, customer_notified
        ),
    }
