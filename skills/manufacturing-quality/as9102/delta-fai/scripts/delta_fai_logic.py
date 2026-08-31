#!/usr/bin/env python3
"""Delta first article inspection (FAI) decision logic.

Paraphrase of AS9102 (IAQG/SAE) change evaluation practice, not a copy
of the standard text (standards-map.yaml: as9102 gated, reference-only).
After a production change the organization classifies the change as
full new FAI, delta FAI, or no FAI, then scopes a delta FAI to the
affected forms (form 1 part accountability, form 2 material and special
processes, form 3 characteristic accountability) and to the affected
characteristics.

This module handles no physical quantities, so it defines no units; it
is a deterministic decision table over change types.
"""

CHANGE_RULES = {
    "part-number": "full-new-fai",
    "material": "full-new-fai",
    "process": "delta-fai",
    "tooling": "delta-fai",
    "drawing-revision": "delta-fai",
    "location": "delta-fai",
    "supplier": "delta-fai",
    "none": "no-fai",
}

# Delta FAI form scope per change type (practical paraphrase of AS9102
# change practice): material or process affects forms 1 and 2, tooling
# or drawing revision affects forms 1 and 3, location or supplier
# affects form 1 only. Material normally classifies as full new FAI but
# is kept in the table because a delta scope can still be requested.
FORM_SCOPE = {
    "material": (1, 2),
    "process": (1, 2),
    "tooling": (1, 3),
    "drawing-revision": (1, 3),
    "location": (1,),
    "supplier": (1,),
}

DELTA_TYPES = frozenset(t for t, rule in CHANGE_RULES.items() if rule == "delta-fai")


def classify_change(change):
    """Classify a change as 'full-new-fai', 'delta-fai', or 'no-fai'.

    change is a dict with change_type, one of the CHANGE_RULES keys,
    and an optional description. A part number or material change
    classifies as full-new-fai; process, tooling, drawing-revision,
    location, and supplier changes classify as delta-fai; none
    classifies as no-fai. Raises ValueError for a non-dict, a missing
    change_type, or an unknown change_type.
    """
    if not isinstance(change, dict):
        raise ValueError("change must be a dict, got %r" % (change,))
    ctype = change.get("change_type")
    if ctype not in CHANGE_RULES:
        raise ValueError(
            "unknown change_type %r; expected one of %s"
            % (ctype, ", ".join(sorted(CHANGE_RULES)))
        )
    return CHANGE_RULES[ctype]


def scope_delta_fai(change, affected_characteristics):
    """Delta FAI scope: dict with forms, characteristics, and note.

    forms is the list of affected form numbers for the change type
    (material or process: forms 1 and 2; tooling or drawing-revision:
    forms 1 and 3; location or supplier: form 1). characteristics is
    the passed list of affected characteristics, copied in order.
    note is a one-sentence explanation of the scope. Raises ValueError
    when the change type has no delta scope (part-number, none, or an
    unknown type) or when affected_characteristics is not a list or
    tuple.
    """
    if not isinstance(change, dict):
        raise ValueError("change must be a dict, got %r" % (change,))
    ctype = change.get("change_type")
    if ctype not in FORM_SCOPE:
        raise ValueError(
            "change_type %r has no delta FAI scope "
            "(part-number or none classify as full new FAI / no FAI)"
            % (ctype,)
        )
    if not isinstance(affected_characteristics, (list, tuple)):
        raise ValueError(
            "affected_characteristics must be a list or tuple, got %r"
            % (affected_characteristics,)
        )
    forms = list(FORM_SCOPE[ctype])
    chars = list(affected_characteristics)
    desc = change.get("description") or ""
    detail = " (%s)" % desc if desc else ""
    if ctype == "material":
        note = (
            "material change classifies as full new FAI; if a delta scope is "
            "applied, forms %s are affected%s"
            % (", ".join(str(f) for f in forms), detail)
        )
    else:
        note = "delta FAI for a %s change%s; forms %s are affected" % (
            ctype,
            detail,
            ", ".join(str(f) for f in forms),
        )
    return {"forms": forms, "characteristics": chars, "note": note}


def verify_full_fai_needed(change):
    """True when the change classifies as a full new FAI."""
    return classify_change(change) == "full-new-fai"
