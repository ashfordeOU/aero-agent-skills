#!/usr/bin/env python3
"""SysML diagram modeling logic (paraphrase).

Common-knowledge summary (standards-map.yaml, arp4754a: gated, referenced
not reproduced): SysML is the systems modeling language used to execute
model-based systems engineering. Diagram kinds: block definition (bdd),
internal block (ibd), parametric (param), requirement (req), activity
(act), sequence (seq), state machine (stm), use case (uc), and package
(pkg) for model organization. A block definition diagram declares the
block hierarchy and value types; an internal block diagram shows the
internal structure and connections between parts; a parametric diagram
binds constraint equations to block value properties; a requirements
diagram links requirements to design elements for traceability.
Viewpoints (structure, behavior, requirements, parametric) must all be
covered for a model to be complete.
"""

DIAGRAM_KINDS = ("bdd", "ibd", "param", "req", "act", "seq", "stm", "uc", "pkg")

DIAGRAM_NAMES = {
    "bdd": "block definition diagram",
    "ibd": "internal block diagram",
    "param": "parametric diagram",
    "req": "requirements diagram",
    "act": "activity diagram",
    "seq": "sequence diagram",
    "stm": "state machine diagram",
    "uc": "use case diagram",
    "pkg": "package diagram",
}

PURPOSE_TO_DIAGRAM = {
    "system-composition": "bdd",
    "system-structure": "bdd",
    "system-hierarchy": "bdd",
    "block-definition": "bdd",
    "internal-structure": "ibd",
    "internal-connections": "ibd",
    "internal-interfaces": "ibd",
    "constraint-analysis": "param",
    "parametric-analysis": "param",
    "performance-equation": "param",
    "requirements-capture": "req",
    "requirements-traceability": "req",
    "functional-flow": "act",
    "activity-flow": "act",
    "message-ordering": "seq",
    "interaction-sequence": "seq",
    "state-transition": "stm",
    "system-modes": "stm",
    "use-case-scoping": "uc",
    "actor-system-boundary": "uc",
    "model-organization": "pkg",
}

REQUIRED_VIEWPOINTS = ("structure", "behavior", "requirements", "parametric")


def sysml_diagram_for(purpose):
    """Canonical SysML diagram kind for a modeling purpose.

    Hand-checked mapping: system-composition -> bdd,
    internal-connections -> ibd, constraint-analysis -> param,
    requirements-traceability -> req, functional-flow -> act,
    message-ordering -> seq, state-transition -> stm,
    use-case-scoping -> uc, model-organization -> pkg.
    """
    if not isinstance(purpose, str) or not purpose:
        raise ValueError("purpose must be a non-empty string")
    if purpose not in PURPOSE_TO_DIAGRAM:
        raise ValueError("unknown SysML modeling purpose: %r" % (purpose,))
    return PURPOSE_TO_DIAGRAM[purpose]


def diagram_kind_name(kind):
    """Full diagram name for a canonical SysML diagram kind.

    Hand-checked: bdd -> 'block definition diagram',
    ibd -> 'internal block diagram', param -> 'parametric diagram',
    req -> 'requirements diagram'.
    """
    if kind not in DIAGRAM_NAMES:
        raise ValueError("unknown SysML diagram kind: %r" % (kind,))
    return DIAGRAM_NAMES[kind]


def block_definition_verdict(parts, references):
    """A bdd is valid when it defines every referenced element.

    parts: block names declared in the diagram; references: element
    names the model references. Valid iff parts is non-empty and every
    reference has a definition among the parts.
    """
    if not isinstance(parts, (list, tuple)) or not isinstance(
        references, (list, tuple)
    ):
        raise ValueError("parts and references must be lists or tuples")
    if not parts:
        return "invalid"
    missing = [r for r in references if r not in set(parts)]
    return "invalid" if missing else "valid"


def requirement_trace_closure(requirements, satisfied_by):
    """Requirements without a satisfying design element (trace gap).

    satisfied_by maps each requirement to the list of design elements
    that satisfy it; a requirement with an empty or missing list is
    missing. Every satisfied_by key must be a known requirement.
    """
    if not isinstance(requirements, (list, tuple)):
        raise ValueError("requirements must be a list or tuple")
    if not isinstance(satisfied_by, dict):
        raise ValueError("satisfied_by must be a dict")
    known = set(requirements)
    unknown = [k for k in satisfied_by if k not in known]
    if unknown:
        raise ValueError(
            "satisfied_by keys are not requirements: %r" % (unknown,)
        )
    missing = [r for r in requirements if not satisfied_by.get(r)]
    return missing


def model_viewpoint_verdict(views):
    """Model viewpoint coverage: 'complete' or 'missing'.

    Required viewpoints: structure, behavior, requirements, parametric.
    Every required viewpoint must be present with value True. Unknown
    viewpoint keys raise ValueError (typo guard).
    """
    if not isinstance(views, dict):
        raise ValueError("views must be a dict")
    unknown = [v for v in views if v not in REQUIRED_VIEWPOINTS]
    if unknown:
        raise ValueError("unknown viewpoint: %r" % (unknown,))
    for v in views.values():
        if not isinstance(v, bool):
            raise ValueError("viewpoint coverage values must be bool")
    if all(views.get(v) for v in REQUIRED_VIEWPOINTS):
        return "complete"
    return "missing"
