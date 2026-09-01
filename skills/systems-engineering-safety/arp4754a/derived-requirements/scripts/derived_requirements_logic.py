#!/usr/bin/env python3
"""Derived requirements logic per ARP4754A (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4754a: gated):
ARP4754A treats a derived requirement as one whose content is not
directly traceable to a parent requirement or to a source document;
it arises during the development process. Derived requirements need a
derivation source (design decision, implementation constraint,
interface resolution, architectural choice, environmental assumption),
a derivation rationale, and an impact analysis, and they participate in
validation, verification planning, and the traceability matrix like
allocated requirements.
"""

DERIVATION_SOURCES = (
    "design_decision",
    "implementation_constraint",
    "interface_resolution",
    "architectural_choice",
    "environmental_assumption",
)

RATIONALE_FIELDS = ("derivation_rationale", "impact_analysis")


def _validate_req(req):
    """Structural validation of a requirement record. Raises ValueError
    on non-dict input, missing traceability keys, non-boolean
    traceability values, or an unknown derivation source."""
    if not isinstance(req, dict):
        raise ValueError("requirement must be a dict")
    for key in ("has_parent_trace", "has_source_doc"):
        if key not in req:
            raise ValueError("requirement missing key %r" % (key,))
        if not isinstance(req[key], bool):
            raise ValueError("requirement key %r must be a bool" % (key,))
    source = req.get("derivation_source")
    if source is not None and source not in DERIVATION_SOURCES:
        raise ValueError(
            "unknown derivation source %r; expected one of %s"
            % (source, ", ".join(DERIVATION_SOURCES))
        )


def classify_requirement(req):
    """Classify a requirement as ('derived', rationale_fields) or
    ('allocated', []).

    A requirement with a parent trace or a source document trace is
    allocated: its content is directly traceable upward. A requirement
    with neither is derived: its content arose during design, so the
    full rationale (the derivation source categories plus the rationale
    and impact analysis fields) is required.
    """
    _validate_req(req)
    if req["has_parent_trace"] or req["has_source_doc"]:
        return ("allocated", [])
    return ("derived", list(DERIVATION_SOURCES) + list(RATIONALE_FIELDS))


def required_rationale(req):
    """Rationale fields a requirement must carry: empty for allocated,
    the full derivation-source and rationale set for derived."""
    return classify_requirement(req)[1]


def validation_checklist(req):
    """Per-field validation checks for one requirement.

    Returns a list of (field, ok, message) tuples. For an allocated
    requirement the traceability fields themselves are the check. For a
    derived requirement the derivation source must be one of the five
    categories, and the derivation rationale and impact analysis must
    be non-empty text.
    """
    _validate_req(req)
    classification, _ = classify_requirement(req)
    checks = []
    if classification == "allocated":
        checks.append(("traceability", True, "allocated: traces to parent or source"))
        return checks
    source = req.get("derivation_source")
    checks.append(
        (
            "derivation_source",
            source in DERIVATION_SOURCES,
            "derivation source is one of %s" % ", ".join(DERIVATION_SOURCES),
        )
    )
    for field in RATIONALE_FIELDS:
        value = req.get(field)
        ok = isinstance(value, str) and bool(value.strip())
        checks.append((field, ok, "%s present" % field if ok else "%s missing" % field))
    return checks


def validate_requirement(req):
    """True when every validation checklist entry passes."""
    _validate_req(req)
    return all(ok for _, ok, _ in validation_checklist(req))
