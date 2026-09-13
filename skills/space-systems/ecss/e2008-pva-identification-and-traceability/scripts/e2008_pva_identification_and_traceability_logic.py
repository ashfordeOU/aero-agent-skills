#!/usr/bin/env python3
"""Identification and traceability of the non-cell parts of a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.4.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Cells are serialised and tracked as a matter of course. Everything else
that goes into an assembly -- coverglass, interconnector stock,
adhesive, substrate laminate, wiring, bypass diodes -- has to be
identified by some other means and kept identified through every
production step, so that a suspect lot can be chased forward to the
assemblies that consumed it and an assembly can be chased back to the
lots it was built from.

Component form decides what identification is physically possible
    discrete-part      a countable item that can carry its own mark
    continuous-stock   reel or roll stock; a mark is lost on sectioning
    bulk-consumable    adhesive, encapsulant, flux; no part to mark

Identity carrier, strongest to weakest
    permanent-part-marking   the item itself carries its identity
    tagged-container         the identity lives on the container
    travelling-record-only   the identity lives only on the paperwork
    unmarked                 no carrier of any kind

The chain then matters more than the mark: identification that is not
transcribed at a production step ends there, and every step past the
break is untraceable regardless of how well the part was marked when it
arrived.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COMPONENT_FORMS = ("discrete-part", "continuous-stock", "bulk-consumable")
MARKING_METHODS = (
    "permanent-part-marking",
    "tagged-container",
    "travelling-record-only",
    "unmarked",
)
IDENTITY_RESOLUTIONS = ("part", "batch", "none")

TRACE_TO_PART = "traceable-to-part"
TRACE_TO_BATCH = "traceable-to-batch-only"
TRACE_BROKEN = "trace-broken"

TRACE_RANK = {TRACE_BROKEN: 0, TRACE_TO_BATCH: 1, TRACE_TO_PART: 2}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A retention is a quotient of two small counts, so a chain that is
    intact end to end can evaluate a unit in the last place below one.
    The comparison tolerates that; the counts themselves are untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def marking_adequacy(component_form, marking_method):
    """Decide what identification the declared carrier can actually deliver."""
    form = _require_choice("component_form", component_form, COMPONENT_FORMS)
    method = _require_choice("marking_method", marking_method, MARKING_METHODS)
    findings = []

    if method == "permanent-part-marking":
        if form == "bulk-consumable":
            raise ValueError(
                "a bulk consumable has no part to mark; declare a "
                "tagged-container or travelling-record-only carrier instead"
            )
        if form == "continuous-stock":
            findings.append(
                "a mark on continuous stock does not survive sectioning; each "
                "cut length falls back to the batch identity of the reel"
            )
            return {
                "identity_resolution": "batch",
                "survives_processing": False,
                "findings": findings,
            }
        return {
            "identity_resolution": "part",
            "survives_processing": True,
            "findings": findings,
        }

    if method == "tagged-container":
        if form == "bulk-consumable":
            findings.append(
                "the container tag stops at the dispensing step; past it the "
                "batch identity of the consumable lives only on the record"
            )
            return {
                "identity_resolution": "batch",
                "survives_processing": False,
                "findings": findings,
            }
        return {
            "identity_resolution": "batch",
            "survives_processing": True,
            "findings": findings,
        }

    if method == "travelling-record-only":
        findings.append(
            "identity rests entirely on the travelling record; a step that "
            "fails to transcribe it ends the chain with no physical fallback"
        )
        return {
            "identity_resolution": "batch",
            "survives_processing": False,
            "findings": findings,
        }

    findings.append(
        "the component carries no identification of any kind; nothing links "
        "it to a lot once it enters the build"
    )
    return {
        "identity_resolution": "none",
        "survives_processing": False,
        "findings": findings,
    }


def identity_chain(steps):
    """Walk the production steps and find where the identity link ends."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of production steps")
    names = []
    break_step = None
    retained = 0
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("step %d must be a mapping, got %r" % (index, step))
        name = _require_label("step name", step.get("name"))
        if name in names:
            raise ValueError("production step %r appears twice in the route" % name)
        names.append(name)
        carries = _require_flag("records_identity", step.get("records_identity"))
        if break_step is None:
            if carries:
                retained += 1
            else:
                break_step = name
    total = len(names)
    return {
        "total_steps": total,
        "retained_steps": retained,
        "break_step": break_step,
        "retention": retained / total,
        "route": names,
    }


def assess_component(component):
    """Judge one non-cell component: marked how, traceable how far."""
    if not isinstance(component, dict):
        raise ValueError("component must be a mapping, got %r" % (component,))
    name = _require_label("component name", component.get("name"))
    form = _require_choice(
        "component_form", component.get("component_form"), COMPONENT_FORMS
    )
    method = _require_choice(
        "marking_method", component.get("marking_method"), MARKING_METHODS
    )
    lot_id = component.get("lot_id")
    if lot_id is not None:
        lot_id = _require_label("lot_id", lot_id)
    adequacy = marking_adequacy(form, method)
    chain = identity_chain(component.get("steps"))
    findings = ["%s: %s" % (name, f) for f in adequacy["findings"]]

    chain_intact = chain["break_step"] is None and _at_least(chain["retention"], 1.0)
    if not chain_intact:
        findings.append(
            "%s: the identity chain ends at %s; %d of %d production steps "
            "carry it forward"
            % (name, chain["break_step"], chain["retained_steps"], chain["total_steps"])
        )
    if lot_id is None:
        findings.append(
            "%s: no lot identifier is recorded, so no chain has anything to "
            "point back to" % name
        )

    if lot_id is None or adequacy["identity_resolution"] == "none" or not chain_intact:
        verdict = TRACE_BROKEN
    elif adequacy["identity_resolution"] == "part" and adequacy["survives_processing"]:
        verdict = TRACE_TO_PART
    else:
        verdict = TRACE_TO_BATCH

    return {
        "name": name,
        "component_form": form,
        "marking_method": method,
        "lot_id": lot_id,
        "identity_resolution": adequacy["identity_resolution"],
        "survives_processing": adequacy["survives_processing"],
        "chain": chain,
        "chain_intact": chain_intact,
        "verdict": verdict,
        "findings": findings,
    }


def recall_scope(lot_id, usage_records):
    """Assemblies a suspect lot reached, from the forward usage records."""
    wanted = _require_label("lot_id", lot_id)
    if not isinstance(usage_records, (list, tuple)):
        raise ValueError("usage_records must be a sequence")
    reached = set()
    for index, record in enumerate(usage_records):
        if not isinstance(record, dict):
            raise ValueError("usage record %d must be a mapping" % index)
        serial = _require_label("assembly_serial", record.get("assembly_serial"))
        lots = record.get("lot_ids")
        if not isinstance(lots, (list, tuple)) or not lots:
            raise ValueError(
                "usage record for %s lists no lot identifiers; a build record "
                "without lots cannot be traced" % serial
            )
        for lot in lots:
            if _require_label("lot_ids entry", lot) == wanted:
                reached.add(serial)
    return sorted(reached)


def assess_assembly_traceability(case):
    """Full clause 5.4.4 roll-up over every non-cell component of an assembly."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    serial = _require_label("assembly_serial", case.get("assembly_serial"))
    components = case.get("components")
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("case must carry a non-empty components sequence")
    seen = set()
    assessments = []
    findings = []
    for component in components:
        assessment = assess_component(component)
        if assessment["name"] in seen:
            raise ValueError(
                "component %r appears twice; one identification record per "
                "component" % assessment["name"]
            )
        seen.add(assessment["name"])
        assessments.append(assessment)
        findings.extend(assessment["findings"])

    worst = min(TRACE_RANK[a["verdict"]] for a in assessments)
    verdict = next(k for k, v in TRACE_RANK.items() if v == worst)
    weakest = min(
        assessments, key=lambda a: (TRACE_RANK[a["verdict"]], a["chain"]["retention"], a["name"])
    )
    broken = [a["name"] for a in assessments if a["verdict"] == TRACE_BROKEN]
    lots = sorted(a["lot_id"] for a in assessments if a["lot_id"] is not None)
    return {
        "assembly_serial": serial,
        "assessments": assessments,
        "verdict": verdict,
        "weakest_component": weakest["name"],
        "broken_components": broken,
        "lots_reachable": lots,
        "traceable_share": (len(assessments) - len(broken)) / len(assessments),
        "findings": findings,
    }
