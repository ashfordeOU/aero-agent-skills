#!/usr/bin/env python3
"""Engineering margins logic: margin of safety for engineering reports.

Quantity convention: allowable and applied values are loads in newtons
(N). The margin is unitless, so stresses in pascals (Pa) work
identically when both inputs are stresses, but a single call must
never mix units: pick one unit (all newtons, or all pascals) and state
it in the report. The Pa/MPa mix is the known bug class: converting
one input and not the other silently corrupts the margin.

Margin of safety MS = (allowable / applied) - 1, the standard
structural margin. MS >= 0 passes (allowable at least equals applied),
MS < 0 fails. This is the documentation-pack discipline for reporting
margins, not a strength or allowable computation leaf.
"""


def margin_of_safety(allowable, applied):
    """Margin of safety MS = (allowable / applied) - 1, unitless decimal.

    Both inputs are loads in newtons (N), or stresses in pascals (Pa)
    when both are stresses; never mix units within one call. Raises
    ValueError when allowable <= 0 or applied <= 0.
    """
    if allowable <= 0:
        raise ValueError("allowable must be > 0, got %r" % (allowable,))
    if applied <= 0:
        raise ValueError("applied must be > 0, got %r" % (applied,))
    return (allowable / applied) - 1.0


def margin_percent(allowable, applied):
    """Margin of safety as a percent: MS * 100.

    Inputs are loads in newtons (N), output in percent. Raises
    ValueError when allowable <= 0 or applied <= 0.
    """
    return margin_of_safety(allowable, applied) * 100.0


def limit_margin(limit_allowable, limit_applied):
    """Limit margin ML = (limit_allowable / limit_applied) - 1.

    The limit-basis check: the limit allowable versus the limit
    applied load, both in newtons (N). Raises ValueError when either
    input is <= 0.
    """
    return margin_of_safety(limit_allowable, limit_applied)


def margin_verdict(allowable, applied):
    """Verdict dict {"ms": ms, "verdict": "pass" or "fail"}.

    Verdict is "pass" when ms >= 0, else "fail". Inputs are loads in
    newtons (N). Raises ValueError when allowable <= 0 or applied <= 0.
    """
    ms = margin_of_safety(allowable, applied)
    return {"ms": ms, "verdict": "pass" if ms >= 0 else "fail"}


def report_margin(allowable, applied, basis):
    """One-line engineering-report sentence for the margin.

    Sentence shape: "Margin of safety <ms> (<basis> basis): <verdict>",
    for example "Margin of safety 0.25 (ultimate basis): pass". The
    margin is rounded to 4 decimals for the report. basis must be
    "limit" or "ultimate" (ValueError otherwise). Inputs are loads in
    newtons (N); raises ValueError when allowable <= 0 or applied <= 0.
    """
    if basis not in ("limit", "ultimate"):
        raise ValueError("basis must be 'limit' or 'ultimate', got %r" % (basis,))
    ms = margin_of_safety(allowable, applied)
    verdict = "pass" if ms >= 0 else "fail"
    return "Margin of safety %s (%s basis): %s" % (round(ms, 4), basis, verdict)
