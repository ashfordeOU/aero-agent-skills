#!/usr/bin/env python3
"""Drawing characteristic ballooning for AS9102 first article inspection.

Paraphrase of AS9102 (IAQG/SAE) practice, not a copy of the standard
text (standards-map.yaml: as9102 gated, reference-only). Ballooning
marks every design characteristic on the drawing with a unique balloon
number; the D-list accountability matrix ties each balloon number to
its characteristic, verification method code, and classification, and
the result feeds form 3 characteristic accountability.

Verification method codes (summarized, per common AS9102 practice):
1 = measuring/variable, 2 = attribute/go-no-go, 3 = functional,
4 = visual, 5 = analytical.

This module handles no physical quantities, so it defines no units.
"""

# Verification method label to AS9102 code (paraphrase, not standard text).
METHOD_CODE_BY_LABEL = {
    "measuring": 1,
    "variable": 1,
    "attribute": 2,
    "go-no-go": 2,
    "functional": 3,
    "visual": 4,
    "analytical": 5,
}

# Characteristic kind to classification label (paraphrase of common
# design-definition practice, not AS9102 wording).
CLASSIFICATION_BY_KIND = {
    "key": "key characteristic",
    "critical": "critical characteristic",
    "standard": "standard",
}


def assign_balloon_numbers(characteristics):
    """Assign unique sequential balloon numbers starting at 1.

    characteristics is a list or tuple of characteristic entries, each
    either a dict with an 'id' key or a plain identifier (string or
    number). Returns a dict mapping each characteristic identifier to
    its balloon number, in input order. Raises ValueError when the
    input is not a list/tuple or when an identifier repeats.
    """
    if not isinstance(characteristics, (list, tuple)):
        raise ValueError(
            "characteristics must be a list or tuple, got %r" % (characteristics,)
        )
    numbers = {}
    for i, item in enumerate(characteristics, start=1):
        cid = item.get("id") if isinstance(item, dict) else item
        if cid in numbers:
            raise ValueError("duplicate characteristic %r in ballooning input" % (cid,))
        numbers[cid] = i
    return numbers


def verification_method_code(method_label):
    """Map a verification method label to the AS9102 code 1 to 5.

    Accepts the labels measuring/variable (1), attribute/go-no-go (2),
    functional (3), visual (4), and analytical (5), case-insensitively
    and with spaces normalized to hyphens ('go no go' equals
    'go-no-go'). Raises ValueError for a non-string or unknown label.
    """
    if not isinstance(method_label, str):
        raise ValueError(
            "method label must be a string, got %r" % (method_label,)
        )
    label = method_label.strip().lower().replace(" ", "-")
    code = METHOD_CODE_BY_LABEL.get(label)
    if code is None:
        raise ValueError(
            "unknown verification method label %r; expected one of %s"
            % (method_label, ", ".join(sorted(METHOD_CODE_BY_LABEL)))
        )
    return code


def classify_characteristic(kind):
    """Classify a characteristic kind as key, critical, or standard.

    kind is 'key', 'critical', or 'standard' (case-insensitive);
    returns the classification label ('key characteristic',
    'critical characteristic', or 'standard'). Raises ValueError for a
    non-string or unknown kind.
    """
    if not isinstance(kind, str):
        raise ValueError("characteristic kind must be a string, got %r" % (kind,))
    label = CLASSIFICATION_BY_KIND.get(kind.strip().lower())
    if label is None:
        raise ValueError(
            "unknown characteristic kind %r; expected key, critical, or standard"
            % (kind,)
        )
    return label


def balloon_count_reconciliation(balloon_count, form_line_items):
    """Verdict for balloon count vs form 3 line items.

    Returns a dict with status 'match' when the ballooned
    characteristic count equals the form 3 line item count, else
    'mismatch', plus the counts, the difference (balloon count minus
    line items), and a note. Raises ValueError for non-integer or
    negative inputs.
    """
    if isinstance(balloon_count, bool) or not isinstance(balloon_count, int):
        raise ValueError(
            "balloon_count must be an integer, got %r" % (balloon_count,)
        )
    if isinstance(form_line_items, bool) or not isinstance(form_line_items, int):
        raise ValueError(
            "form_line_items must be an integer, got %r" % (form_line_items,)
        )
    if balloon_count < 0 or form_line_items < 0:
        raise ValueError("balloon count and form line items must be non-negative")
    difference = balloon_count - form_line_items
    status = "match" if difference == 0 else "mismatch"
    note = (
        "balloon count equals the form 3 line items"
        if status == "match"
        else "balloon count differs from the form 3 line items by %d"
        % (abs(difference),)
    )
    return {
        "status": status,
        "balloon_count": balloon_count,
        "form_line_items": form_line_items,
        "difference": difference,
        "note": note,
    }


def accountability_matrix_verdict(balloons):
    """Verdict on the D-list accountability matrix completeness.

    balloons is a list or tuple of dicts, each with an 'id' (the
    balloon number), a 'method' (verification method label or code
    acceptable to verification_method_code), and a 'classification'
    (kind acceptable to classify_characteristic). Returns a dict with
    complete (True when every balloon has a valid method and
    classification), issues (one message per deficient balloon), and
    balloon_count. Raises ValueError when the input is not a list or
    tuple.
    """
    if not isinstance(balloons, (list, tuple)):
        raise ValueError("balloons must be a list or tuple, got %r" % (balloons,))
    issues = []
    for balloon in balloons:
        if not isinstance(balloon, dict):
            issues.append("balloon entry is not a dict: %r" % (balloon,))
            continue
        bid = balloon.get("id")
        if bid is None:
            issues.append("balloon entry missing 'id'")
            continue
        problems = []
        method = balloon.get("method")
        classification = balloon.get("classification")
        if method is None:
            problems.append("missing method")
        else:
            try:
                verification_method_code(method)
            except ValueError:
                problems.append("invalid method %r" % (method,))
        if classification is None:
            problems.append("missing classification")
        else:
            try:
                classify_characteristic(classification)
            except ValueError:
                problems.append("invalid classification %r" % (classification,))
        if problems:
            issues.append("balloon %s: %s" % (bid, "; ".join(problems)))
    return {
        "complete": not issues,
        "issues": issues,
        "balloon_count": len(balloons),
    }
