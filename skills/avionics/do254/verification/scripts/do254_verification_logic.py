#!/usr/bin/env python3
"""DO-254 verification logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, do-254: gated): DO-254
covers design assurance of airborne electronic hardware (AEH).
Verification shows the hardware item satisfies its requirements via
test, analysis, and review; complex AEH (programmable logic,
processors, significant internal state) is verified with the full
method set while simple AEH uses reduced verification. Independent
verification is expected at the higher hardware design assurance
levels, and requirements-based testing is measured against coverage
ratios (0.98 at levels A/B, 0.95 at C/D). Hardware/software
integration evidence ties the item to the software it hosts.
"""

VALID_HDAL = ("A", "B", "C", "D")

FULL_METHODS = {"test", "analysis", "review"}
REDUCED_METHODS = {"review"}


def verification_methods_for(aeh_class, hdal):
    """Verification methods for a DO-254 hardware item: complex AEH uses
    test, analysis, and review; simple AEH uses reduced verification
    (review). Unknown classes or levels raise ValueError."""
    if aeh_class not in ("simple", "complex"):
        raise ValueError("unknown AEH class: %r" % (aeh_class,))
    if hdal not in VALID_HDAL:
        raise ValueError("invalid hardware design assurance level: %r" % (hdal,))
    if aeh_class == "complex":
        return set(FULL_METHODS)
    return set(REDUCED_METHODS)


def independence_required(hdal):
    """Independent verification is expected at the higher hardware design
    assurance levels (A/B); returns False otherwise."""
    return hdal in ("A", "B")


def requirements_based_coverage_ok(tested, total, hdal, min_ratio=0.95):
    """Requirements-based test coverage check: passes when tested/total
    meets min_ratio. Use min_ratio 0.98 at levels A/B and 0.95 at C/D
    (the default). Invalid inputs (tested > total, total <= 0, or a
    level outside A-D) raise ValueError."""
    if hdal not in VALID_HDAL:
        raise ValueError("invalid hardware design assurance level: %r" % (hdal,))
    if total <= 0:
        raise ValueError("total must be positive, got %r" % (total,))
    if tested > total:
        raise ValueError("tested (%r) exceeds total (%r)" % (tested, total))
    return tested / total >= min_ratio


def hwsw_integration_evidence(present):
    """Whether hardware/software integration evidence is available for
    the item (plain boolean pass-through)."""
    return bool(present)


def verification_complete(methods_used, required_methods):
    """True when every required verification method is present in the
    methods used (extra methods do not fail the check)."""
    return set(required_methods).issubset(set(methods_used))
