#!/usr/bin/env python3
"""Permanent coding of delivered solar cell assemblies and the depth it reaches.

Anchor: ECSS-E-ST-20-08C clause 6.1.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Every cell assembly that is delivered carries a permanent code, and the
code has to keep working after the assembly stops being a loose item --
after it is handled, bonded down, cured and cycled. The depth that code
has to reach is not a constant: the process identification document
sets it, and a scheme that is adequate at lot depth is inadequate the
moment the document asks for the constituent lots behind a single
serialised assembly.

Marking methods, most durable first
    laser-engraved   cut into the substrate or the busbar; survives all
    fired-on-ink     bonded to the surface; survives cure, fades on cycling
    printed-label    adhered; lost at the first bonding or cure step
    record-only      nothing on the hardware at all

Process exposure the delivered assembly sees
    handling-only      stored and shipped as a loose assembly
    bonding-and-cure   bonded to a panel and cured
    thermal-cycling    bonded, cured and cycled

Traceability depth, shallowest first
    none             nothing identifies the assembly
    lot              the delivery lot is known, the assembly is not
    assembly         this assembly is identified individually
    constituent-lot  the cell, coverglass and adhesive lots are reachable

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MARKING_METHODS = (
    "laser-engraved",
    "fired-on-ink",
    "printed-label",
    "record-only",
)

PROCESS_EXPOSURES = ("handling-only", "bonding-and-cure", "thermal-cycling")

CODE_FIELDS = ("lot-code", "serial", "constituent-lot-code")

DEPTH_NONE = "none"
DEPTH_LOT = "lot"
DEPTH_ASSEMBLY = "assembly"
DEPTH_CONSTITUENT = "constituent-lot"

DEPTH_RANK = {
    DEPTH_NONE: 0,
    DEPTH_LOT: 1,
    DEPTH_ASSEMBLY: 2,
    DEPTH_CONSTITUENT: 3,
}

CODING_COMPLIANT = "coding-meets-required-depth"
CODING_SHALLOW = "coding-below-required-depth"
CODING_NOT_ESTABLISHED = "coding-not-established"

CODING_RANK = {
    CODING_NOT_ESTABLISHED: 0,
    CODING_SHALLOW: 1,
    CODING_COMPLIANT: 2,
}

_SURVIVAL = {
    "laser-engraved": {
        "handling-only": True,
        "bonding-and-cure": True,
        "thermal-cycling": True,
    },
    "fired-on-ink": {
        "handling-only": True,
        "bonding-and-cure": True,
        "thermal-cycling": False,
    },
    "printed-label": {
        "handling-only": True,
        "bonding-and-cure": False,
        "thermal-cycling": False,
    },
    "record-only": {
        "handling-only": False,
        "bonding-and-cure": False,
        "thermal-cycling": False,
    },
}

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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A compliant share is a quotient of two assembly counts, so a
    delivery that exactly meets its required share can evaluate a unit
    in the last place below it. The comparison absorbs that; the counts
    themselves are untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def marking_permanence(marking_method, process_exposure):
    """Decide whether the declared mark is still readable after processing."""
    method = _require_choice("marking_method", marking_method, MARKING_METHODS)
    exposure = _require_choice(
        "process_exposure", process_exposure, PROCESS_EXPOSURES
    )
    survives = _SURVIVAL[method][exposure]
    findings = []

    if method == "record-only":
        findings.append(
            "nothing is coded onto the assembly; identity rests on paperwork "
            "alone and cannot be recovered from the hardware"
        )
    elif not survives:
        findings.append(
            "a %s mark does not stay legible through %s, so the assembly "
            "stops being identifiable at the step that matters most"
            % (method, exposure)
        )
    return {
        "marking_method": method,
        "process_exposure": exposure,
        "survives_processing": survives,
        "findings": findings,
    }


def achieved_depth(code_fields, register_resolves_constituents=False):
    """Read the depth the code fields and the delivery register actually reach."""
    if not isinstance(code_fields, (list, tuple)):
        raise ValueError("code_fields must be a sequence of coded field names")
    linked = _require_flag(
        "register_resolves_constituents", register_resolves_constituents
    )
    fields = []
    for item in code_fields:
        field = _require_choice("code field", item, CODE_FIELDS)
        if field in fields:
            raise ValueError("code field %r is declared twice" % field)
        fields.append(field)

    findings = []
    if "constituent-lot-code" in fields:
        depth = DEPTH_CONSTITUENT
    elif "serial" in fields and linked:
        depth = DEPTH_CONSTITUENT
    elif "serial" in fields:
        depth = DEPTH_ASSEMBLY
        findings.append(
            "the code identifies the assembly but nothing reaches the lots it "
            "was built from; the register has to close that gap"
        )
    elif "lot-code" in fields:
        depth = DEPTH_LOT
        findings.append(
            "the code reaches the delivery lot only; two assemblies from one "
            "lot are indistinguishable on the hardware"
        )
    else:
        depth = DEPTH_NONE
        findings.append("the code carries no field that identifies anything")

    if linked and "serial" not in fields:
        findings.append(
            "a register that resolves constituent lots needs a serial to key "
            "on; without one it cannot be entered from the hardware"
        )
    return {"depth": depth, "fields": fields, "findings": findings}


def depth_shortfall(required_depth, reached_depth):
    """Steps short of the depth the process identification document sets."""
    required = _require_choice("required_depth", required_depth, tuple(DEPTH_RANK))
    reached = _require_choice("reached_depth", reached_depth, tuple(DEPTH_RANK))
    if required == DEPTH_NONE:
        raise ValueError(
            "a process document that requires no traceability depth gives the "
            "coding scheme nothing to be graded against"
        )
    gap = DEPTH_RANK[required] - DEPTH_RANK[reached]
    return {
        "required_depth": required,
        "reached_depth": reached,
        "steps_short": max(gap, 0),
        "meets_requirement": gap <= 0,
    }


def code_uniqueness(codes):
    """Find codes repeated across the delivered set."""
    if not isinstance(codes, (list, tuple)) or not codes:
        raise ValueError("codes must be a non-empty sequence of delivered codes")
    seen = {}
    for item in codes:
        code = _require_label("delivered code", item)
        seen[code] = seen.get(code, 0) + 1
    repeated = sorted(code for code, count in seen.items() if count > 1)
    return {
        "delivered": len(codes),
        "distinct": len(seen),
        "repeated": repeated,
        "unique_share": len(seen) / len(codes),
    }


def assess_assembly_coding(assembly, required_depth):
    """Grade the permanent coding of one delivered cell assembly."""
    if not isinstance(assembly, dict):
        raise ValueError("assembly must be a mapping, got %r" % (assembly,))
    code = _require_label("code", assembly.get("code"))
    permanence = marking_permanence(
        assembly.get("marking_method"), assembly.get("process_exposure")
    )
    depth = achieved_depth(
        assembly.get("code_fields"),
        assembly.get("register_resolves_constituents", False),
    )
    shortfall = depth_shortfall(required_depth, depth["depth"])

    findings = ["%s: %s" % (code, f) for f in permanence["findings"]]
    findings.extend("%s: %s" % (code, f) for f in depth["findings"])
    if not shortfall["meets_requirement"]:
        findings.append(
            "%s: the process document asks for %s depth and the scheme reaches "
            "%s, %d step(s) short"
            % (
                code,
                shortfall["required_depth"],
                shortfall["reached_depth"],
                shortfall["steps_short"],
            )
        )

    if not permanence["survives_processing"] or depth["depth"] == DEPTH_NONE:
        verdict = CODING_NOT_ESTABLISHED
    elif not shortfall["meets_requirement"]:
        verdict = CODING_SHALLOW
    else:
        verdict = CODING_COMPLIANT

    return {
        "code": code,
        "marking_method": permanence["marking_method"],
        "process_exposure": permanence["process_exposure"],
        "survives_processing": permanence["survives_processing"],
        "reached_depth": depth["depth"],
        "shortfall": shortfall,
        "verdict": verdict,
        "findings": findings,
    }


def assess_delivery_coding(case):
    """Full clause 6.1.4 roll-up over a delivered set of cell assemblies."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    delivery_id = _require_label("delivery_id", case.get("delivery_id"))
    assemblies = case.get("assemblies")
    if not isinstance(assemblies, (list, tuple)) or not assemblies:
        raise ValueError("case must carry a non-empty assemblies sequence")
    required = case.get("required_depth")

    assessments = [assess_assembly_coding(a, required) for a in assemblies]
    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    uniqueness = code_uniqueness([a["code"] for a in assessments])
    for code in uniqueness["repeated"]:
        findings.append(
            "code %s is carried by more than one delivered assembly; a repeated "
            "code resolves to a set, not to an assembly" % code
        )

    compliant = [a for a in assessments if a["verdict"] == CODING_COMPLIANT]
    not_established = sorted(
        a["code"] for a in assessments if a["verdict"] == CODING_NOT_ESTABLISHED
    )
    compliant_share = len(compliant) / len(assessments)

    worst = min(CODING_RANK[a["verdict"]] for a in assessments)
    verdict = next(k for k, v in CODING_RANK.items() if v == worst)
    if uniqueness["repeated"] and verdict == CODING_COMPLIANT:
        verdict = CODING_NOT_ESTABLISHED

    weakest = min(
        assessments,
        key=lambda a: (
            CODING_RANK[a["verdict"]],
            -a["shortfall"]["steps_short"],
            a["code"],
        ),
    )
    return {
        "delivery_id": delivery_id,
        "required_depth": required,
        "assessments": assessments,
        "uniqueness": uniqueness,
        "verdict": verdict,
        "weakest_assembly": weakest["code"],
        "not_established": not_established,
        "compliant_share": compliant_share,
        "meets_expected_share": _at_least(compliant_share, 1.0),
        "findings": findings,
    }
