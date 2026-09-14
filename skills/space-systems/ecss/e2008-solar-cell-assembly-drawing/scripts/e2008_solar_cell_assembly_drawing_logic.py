#!/usr/bin/env python3
"""Source control drawing content for a solar cell assembly.

Anchor: ECSS-E-ST-20-08C Annex B. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

A solar cell assembly is a bonded stack, and what the drawing has to control
is not only the items in that stack but the joints between them. A coverglass,
an adhesive and a cell can each be fully specified on their own drawings while
the assembly remains uncontrolled, because nothing says how thick the bond
between two of them is or how much of the area it has to cover.

So the drawing is graded on four things.

The stack itself.
    Which layers are in it, in which order, outer face inward. A stack listing
    the cell outside the coverglass is not a mis-typed drawing, it is a
    different assembly.

The joints the stack implies.
    Every pair of adjacent layers is a bonded interface, and each interface
    needs exactly one control record naming the bonding agent, its thickness
    and the share of the area it covers. No record leaves the joint
    uncontrolled; two records leave the supplier to choose.

The terminals.
    A solar cell assembly has a polarity. Each polarity is identified once,
    and identified on the drawing rather than in a list beside it.

The drawings it cites.
    An assembly drawing controls its constituents through the issues it cites,
    and a citation at a draft or cancelled issue controls nothing.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "STACK_ORDER",
    "REQUIRED_LAYER_ROLES",
    "TERMINAL_POLARITIES",
    "CITATION_ISSUE_STATES",
    "MIN_BOND_COVERAGE",
    "INTERFACE_CONTROLLED",
    "INTERFACE_UNDER_COVERED",
    "INTERFACE_UNCONTROLLED",
    "INTERFACE_AMBIGUOUS",
    "CITATION_GOVERNING",
    "CITATION_OFF_ISSUE",
    "CITATION_VOID",
    "SCA_DRAWING_RELEASABLE",
    "SCA_DRAWING_OPEN_ITEMS",
    "SCA_DRAWING_NOT_RELEASABLE",
    "layer_stack",
    "grade_interface",
    "terminal_identification",
    "cited_drawing_standing",
    "controlled_interface_share",
    "assess_solar_cell_assembly_drawing",
]

# The canonical order of a solar cell assembly stack, outer face inward.
STACK_ORDER = (
    "coverglass",
    "coverglass-adhesive",
    "solar-cell",
    "rear-adhesive",
    "rear-insulation",
)

# Without these three there is no solar cell assembly to draw.
REQUIRED_LAYER_ROLES = ("coverglass", "coverglass-adhesive", "solar-cell")

TERMINAL_POLARITIES = ("positive", "negative")

CITATION_ISSUE_STATES = ("released", "draft", "superseded", "cancelled")

# Smallest share of the joint area a bond has to cover to be a bond.
MIN_BOND_COVERAGE = 0.90

INTERFACE_CONTROLLED = "interface-controlled"
INTERFACE_UNDER_COVERED = "interface-under-covered"
INTERFACE_UNCONTROLLED = "interface-uncontrolled"
INTERFACE_AMBIGUOUS = "interface-doubly-controlled"

CITATION_GOVERNING = "citation-governing"
CITATION_OFF_ISSUE = "citation-off-issue"
CITATION_VOID = "citation-void"

SCA_DRAWING_RELEASABLE = "assembly-drawing-releasable"
SCA_DRAWING_OPEN_ITEMS = "assembly-drawing-releasable-with-open-items"
SCA_DRAWING_NOT_RELEASABLE = "assembly-drawing-not-releasable"

# Coverage shares and control shares are quotients compared with written
# floors, so a value physically on a floor can evaluate a few units in the
# last place under it. The comparisons absorb that; the floors stay as written.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _label(name, value):
    """Return a non-empty stripped string, or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _flag(name, value):
    """Return a boolean, or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _positive(name, value):
    """Return a finite positive float, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _share(name, value):
    """Return a finite share in (0, 1], or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value <= 0.0 or value > 1.0:
        raise ValueError("%s must lie in (0, 1], got %r" % (name, value))
    return value


def _at_least(value, bound):
    """True when value is at or above bound, absorbing representation error."""
    return value > bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _interface_id(upper, lower):
    """Name the joint between two adjacent layers."""
    return "%s-to-%s" % (upper, lower)


def layer_stack(layers):
    """Resolve the assembly stack and the bonded interfaces it implies.

    layers: an ordered sequence, outer face inward, of mappings carrying
    role, item and thickness_um.
    """
    if not isinstance(layers, (list, tuple)):
        raise ValueError("layers must be an ordered sequence of stack layers")
    if not layers:
        raise ValueError("a solar cell assembly with no layer is an input error")

    resolved = []
    seen = set()
    for record in layers:
        if not isinstance(record, dict):
            raise ValueError("stack layer must be a mapping")
        for key in ("role", "item", "thickness_um"):
            if key not in record:
                raise ValueError("stack layer missing required key '%s'" % key)
        role = record["role"]
        if role not in STACK_ORDER:
            raise ValueError(
                "layer role must be one of %s, got %r" % (STACK_ORDER, role)
            )
        if role in seen:
            raise ValueError("layer role '%s' appears twice in one stack" % role)
        seen.add(role)
        resolved.append(
            {
                "role": role,
                "item": _label("item", record["item"]),
                "thickness_um": _positive("thickness_um", record["thickness_um"]),
            }
        )

    findings = []
    missing = [role for role in REQUIRED_LAYER_ROLES if role not in seen]
    for role in missing:
        findings.append(
            "the stack carries no '%s' layer; without it there is no solar cell "
            "assembly to control" % role
        )

    positions = [STACK_ORDER.index(item["role"]) for item in resolved]
    ordered = positions == sorted(positions)
    if not ordered:
        findings.append(
            "the stack is not drawn outer face inward; a stack in this order is "
            "a different assembly, not a mis-typed drawing"
        )

    interfaces = [
        _interface_id(resolved[i]["role"], resolved[i + 1]["role"])
        for i in range(len(resolved) - 1)
    ]
    if not interfaces:
        findings.append(
            "a single-layer stack implies no bonded interface; there is nothing "
            "for the assembly drawing to control"
        )

    return {
        "layers": resolved,
        "roles": [item["role"] for item in resolved],
        "interfaces": interfaces,
        "missing_roles": missing,
        "ordered": ordered,
        "total_thickness_um": sum(item["thickness_um"] for item in resolved),
        "findings": findings,
    }


def grade_interface(interface_id, records):
    """Grade one bonded interface against the control records naming it.

    Each record carries interface, agent, thickness_um and coverage.
    """
    interface = _label("interface_id", interface_id)
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of bond control records")

    matched = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("bond control record must be a mapping")
        for key in ("interface", "agent", "thickness_um", "coverage"):
            if key not in record:
                raise ValueError(
                    "bond control record missing required key '%s'" % key
                )
        if _label("interface", record["interface"]) != interface:
            continue
        matched.append(
            {
                "agent": _label("agent", record["agent"]),
                "thickness_um": _positive("thickness_um", record["thickness_um"]),
                "coverage": _share("coverage", record["coverage"]),
            }
        )

    findings = []
    if not matched:
        findings.append(
            "interface %s carries no bond control; the joint is drawn and not "
            "controlled" % interface
        )
        return {
            "interface": interface,
            "state": INTERFACE_UNCONTROLLED,
            "controls": [],
            "coverage": None,
            "controlled": False,
            "findings": findings,
        }
    if len(matched) > 1:
        findings.append(
            "interface %s carries %d bond controls naming %s; the supplier is "
            "left to choose between them"
            % (interface, len(matched), ", ".join(m["agent"] for m in matched))
        )
        return {
            "interface": interface,
            "state": INTERFACE_AMBIGUOUS,
            "controls": matched,
            "coverage": None,
            "controlled": False,
            "findings": findings,
        }

    control = matched[0]
    if not _at_least(control["coverage"], MIN_BOND_COVERAGE):
        findings.append(
            "interface %s is bonded with %s over %.4f of the joint, under the "
            "%.0f%% a bond is worth"
            % (interface, control["agent"], control["coverage"],
               MIN_BOND_COVERAGE * 100.0)
        )
        return {
            "interface": interface,
            "state": INTERFACE_UNDER_COVERED,
            "controls": matched,
            "coverage": control["coverage"],
            "controlled": False,
            "findings": findings,
        }

    return {
        "interface": interface,
        "state": INTERFACE_CONTROLLED,
        "controls": matched,
        "coverage": control["coverage"],
        "controlled": True,
        "findings": findings,
    }


def terminal_identification(terminals):
    """Check each polarity is identified exactly once, and marked on the drawing.

    Each terminal carries terminal, polarity and marked.
    """
    if not isinstance(terminals, (list, tuple)):
        raise ValueError("terminals must be a sequence of terminal records")

    resolved = []
    for record in terminals:
        if not isinstance(record, dict):
            raise ValueError("terminal record must be a mapping")
        for key in ("terminal", "polarity", "marked"):
            if key not in record:
                raise ValueError("terminal record missing required key '%s'" % key)
        polarity = record["polarity"]
        if polarity not in TERMINAL_POLARITIES:
            raise ValueError(
                "terminal polarity must be one of %s, got %r"
                % (TERMINAL_POLARITIES, polarity)
            )
        resolved.append(
            {
                "terminal": _label("terminal", record["terminal"]),
                "polarity": polarity,
                "marked": _flag("marked", record["marked"]),
            }
        )

    findings = []
    missing = []
    duplicated = []
    for polarity in TERMINAL_POLARITIES:
        count = sum(1 for item in resolved if item["polarity"] == polarity)
        if count == 0:
            missing.append(polarity)
            findings.append(
                "no %s terminal is identified; an assembly without a stated "
                "polarity cannot be connected" % polarity
            )
        elif count > 1:
            duplicated.append(polarity)
            findings.append(
                "%d terminals are identified as %s; which one the harness meets "
                "is left open" % (count, polarity)
            )

    unmarked = [item["terminal"] for item in resolved if not item["marked"]]
    for terminal in unmarked:
        findings.append(
            "terminal '%s' is listed but not marked on the drawing; the mark is "
            "what the operator reads" % terminal
        )

    return {
        "terminals": resolved,
        "missing_polarities": missing,
        "duplicated_polarities": duplicated,
        "unmarked": unmarked,
        "identified": not missing and not duplicated,
        "findings": findings,
    }


def cited_drawing_standing(citation):
    """Resolve how far a drawing cited by the assembly drawing governs.

    citation keys: constituent, drawing, issue_state, cited_issue,
    released_issue.
    """
    if not isinstance(citation, dict):
        raise ValueError("citation must be a mapping")
    for key in ("constituent", "drawing", "issue_state", "cited_issue", "released_issue"):
        if key not in citation:
            raise ValueError("citation missing required key '%s'" % key)
    constituent = _label("constituent", citation["constituent"])
    drawing = _label("drawing", citation["drawing"])
    state = citation["issue_state"]
    if state not in CITATION_ISSUE_STATES:
        raise ValueError(
            "issue_state must be one of %s, got %r" % (CITATION_ISSUE_STATES, state)
        )
    cited = _label("cited_issue", citation["cited_issue"])
    released = _label("released_issue", citation["released_issue"])
    findings = []

    if state in ("draft", "cancelled"):
        findings.append(
            "the %s is cited on drawing %s at a %s issue, which controls nothing"
            % (constituent, drawing, state)
        )
        standing = CITATION_VOID
    elif state == "superseded":
        findings.append(
            "the %s is cited on drawing %s at superseded issue %s; the step to "
            "issue %s needs dispositioning"
            % (constituent, drawing, cited, released)
        )
        standing = CITATION_OFF_ISSUE
    elif cited != released:
        findings.append(
            "the %s is cited on drawing %s at issue %s while issue %s is the "
            "released one" % (constituent, drawing, cited, released)
        )
        standing = CITATION_OFF_ISSUE
    else:
        standing = CITATION_GOVERNING

    return {
        "constituent": constituent,
        "drawing": drawing,
        "standing": standing,
        "findings": findings,
    }


def controlled_interface_share(graded):
    """Share of the bonded interfaces the drawing actually controls."""
    if not isinstance(graded, (list, tuple)):
        raise ValueError("graded must be a sequence of graded interfaces")
    if not graded:
        return 0.0
    controlled = sum(1 for item in graded if item.get("controlled"))
    return float(controlled) / float(len(graded))


def assess_solar_cell_assembly_drawing(spec):
    """Assess a solar cell assembly source control drawing package.

    spec keys: drawing, layers, bond_controls, terminals, citations,
    optional required_interface_control_share.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("drawing", "layers", "bond_controls", "terminals", "citations"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    drawing = _label("drawing", spec["drawing"])
    for key in ("bond_controls", "terminals", "citations"):
        if not isinstance(spec[key], (list, tuple)):
            raise ValueError("spec['%s'] must be a sequence" % key)

    required_share = spec.get("required_interface_control_share", 1.0)
    if isinstance(required_share, bool) or not isinstance(
        required_share, (int, float)
    ):
        raise ValueError("required_interface_control_share must be a real number")
    required_share = float(required_share)
    if not math.isfinite(required_share) or not 0.0 <= required_share <= 1.0:
        raise ValueError(
            "required_interface_control_share must lie in [0, 1], got %r"
            % (spec.get("required_interface_control_share"),)
        )

    stack = layer_stack(spec["layers"])
    graded = [
        grade_interface(interface, spec["bond_controls"])
        for interface in stack["interfaces"]
    ]
    terminals = terminal_identification(spec["terminals"])
    citations = [cited_drawing_standing(item) for item in spec["citations"]]
    if not citations:
        raise ValueError(
            "an assembly drawing citing no constituent drawing is an input error"
        )
    seen = set()
    for item in citations:
        if item["constituent"] in seen:
            raise ValueError(
                "constituent '%s' is cited twice on drawing %s"
                % (item["constituent"], drawing)
            )
        seen.add(item["constituent"])

    stray = []
    known = set(stack["interfaces"])
    for record in spec["bond_controls"]:
        if not isinstance(record, dict) or "interface" not in record:
            raise ValueError(
                "bond control record must be a mapping carrying 'interface'"
            )
        name = _label("interface", record["interface"])
        if name not in known:
            stray.append(name)

    findings = list(stack["findings"])
    for item in graded:
        findings.extend(item["findings"])
    findings.extend(terminals["findings"])
    for item in citations:
        findings.extend(item["findings"])
    for name in sorted(set(stray)):
        findings.append(
            "bond control names interface %s, which this stack does not have"
            % name
        )

    uncontrolled = [
        item["interface"] for item in graded if item["state"] == INTERFACE_UNCONTROLLED
    ]
    ambiguous = [
        item["interface"] for item in graded if item["state"] == INTERFACE_AMBIGUOUS
    ]
    under_covered = [
        item["interface"] for item in graded if item["state"] == INTERFACE_UNDER_COVERED
    ]
    void_citations = [i["constituent"] for i in citations if i["standing"] == CITATION_VOID]
    off_issue = [i["constituent"] for i in citations if i["standing"] == CITATION_OFF_ISSUE]

    share = controlled_interface_share(graded)
    share_met = _at_least(share, required_share)
    if not share_met:
        findings.append(
            "controlled interface share is %.4f against a required %.4f"
            % (share, required_share)
        )

    blocking = bool(
        stack["missing_roles"]
        or not stack["ordered"]
        or uncontrolled
        or ambiguous
        or under_covered
        or void_citations
        or stray
        or not terminals["identified"]
    ) or not share_met
    conditional = bool(off_issue or terminals["unmarked"])

    if blocking:
        verdict = SCA_DRAWING_NOT_RELEASABLE
    elif conditional:
        verdict = SCA_DRAWING_OPEN_ITEMS
    else:
        verdict = SCA_DRAWING_RELEASABLE

    return {
        "drawing": drawing,
        "stack": stack,
        "interfaces": graded,
        "terminals": terminals,
        "citations": citations,
        "uncontrolled_interfaces": uncontrolled,
        "ambiguous_interfaces": ambiguous,
        "under_covered_interfaces": under_covered,
        "stray_bond_controls": sorted(set(stray)),
        "void_citations": void_citations,
        "off_issue_citations": off_issue,
        "interface_control_share": share,
        "required_interface_control_share": required_share,
        "verdict": verdict,
        "findings": findings,
    }
