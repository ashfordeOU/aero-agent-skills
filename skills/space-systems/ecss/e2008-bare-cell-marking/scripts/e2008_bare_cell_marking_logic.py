#!/usr/bin/env python3
"""Permanent traceability marking of delivered bare solar cells.

Anchor: ECSS-E-ST-20-08C clause 7.1.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A bare cell is delivered loose and spends the rest of its life being
built into something else. The code marked on it therefore has to do
three things that pull against each other: stay readable after the cell
has been welded, bonded, cured and cycled; sit somewhere that neither
costs photoactive area nor starts a crack in a brittle wafer; and reach
the traceability depth the process identification document sets rather
than the depth the marking shop finds convenient.

Marking methods, most durable first
    laser-engraved   cut into the metallisation or the wafer edge
    fired-on-ink     bonded to the surface; survives cure, fades on cycling
    printed-label    adhered; gone at the first bonding or cure step
    record-only      nothing on the cell at all

Where the mark is put
    rear-metallisation   hidden once the cell is bonded down, costs no area
    cell-border          the inactive edge strip around the junction
    front-active-area    inside the illuminated area, so it costs power

Process exposure the delivered cell will see
    handling-only          stored and shipped as a loose cell
    interconnector-welding welded into a string
    coverglass-bond-cure   welded, coverglassed and cured
    thermal-cycling        the full assembly campaign

Traceability depth, shallowest first
    none              nothing identifies the cell
    production-lot    the production lot is known, the cell is not
    cell              this cell is identified individually
    wafer-lot         the wafer and process lots behind it are reachable

Two pairings are refused outright rather than merely reported. A laser
cut into the front active area of a brittle cell is a crack initiator,
and an adhered label on the rear metallisation is a bond-line
contaminant; both are declaration defects the reviewer has to see named.

The area cap, the depth ladder and the survival table below are declared
project policy, not physical constants; a project may substitute its own.

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

MARK_LOCATIONS = ("rear-metallisation", "cell-border", "front-active-area")

PROCESS_EXPOSURES = (
    "handling-only",
    "interconnector-welding",
    "coverglass-bond-cure",
    "thermal-cycling",
)

CODE_FIELDS = ("production-lot-code", "cell-serial", "wafer-lot-code")

DEPTH_NONE = "none"
DEPTH_PRODUCTION_LOT = "production-lot"
DEPTH_CELL = "cell"
DEPTH_WAFER_LOT = "wafer-lot"

DEPTH_RANK = {
    DEPTH_NONE: 0,
    DEPTH_PRODUCTION_LOT: 1,
    DEPTH_CELL: 2,
    DEPTH_WAFER_LOT: 3,
}

MARKING_COMPLIANT = "marking-meets-required-depth"
MARKING_SHALLOW = "marking-below-required-depth"
MARKING_INADMISSIBLE = "marking-not-established"

MARKING_RANK = {
    MARKING_INADMISSIBLE: 0,
    MARKING_SHALLOW: 1,
    MARKING_COMPLIANT: 2,
}

DEFAULT_MARKING_POLICY = {
    "max_active_area_loss_fraction": 0.002,
    "required_depth": DEPTH_WAFER_LOT,
}

_SURVIVAL = {
    "laser-engraved": {
        "handling-only": True,
        "interconnector-welding": True,
        "coverglass-bond-cure": True,
        "thermal-cycling": True,
    },
    "fired-on-ink": {
        "handling-only": True,
        "interconnector-welding": True,
        "coverglass-bond-cure": True,
        "thermal-cycling": False,
    },
    "printed-label": {
        "handling-only": True,
        "interconnector-welding": False,
        "coverglass-bond-cure": False,
        "thermal-cycling": False,
    },
    "record-only": {
        "handling-only": False,
        "interconnector-welding": False,
        "coverglass-bond-cure": False,
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


def _require_positive(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    The area loss is a quotient of two measured areas and the cap is a
    round fraction, so a mark cut exactly to the cap can evaluate a unit
    in the last place above it. The comparison absorbs that; the cap
    itself stays as declared.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def mark_placement_admissibility(marking_method, mark_location):
    """Decide whether this method may be applied in this place on a bare cell.

    The pairing is what matters, never the method alone. A laser cut
    inside the illuminated area of a brittle cell is a crack initiator,
    and an adhered label on the rear metallisation sits in the bond line
    the cell is later attached through.
    """
    method = _require_choice("marking_method", marking_method, MARKING_METHODS)
    location = _require_choice("mark_location", mark_location, MARK_LOCATIONS)
    findings = []
    admissible = True

    if method == "record-only":
        admissible = False
        findings.append(
            "nothing is marked on the cell; identity rests on paperwork alone "
            "and cannot be recovered from the hardware"
        )
    elif method == "laser-engraved" and location == "front-active-area":
        admissible = False
        findings.append(
            "a laser cut into the front active area of a brittle cell starts a "
            "crack and removes illuminated area at the same time"
        )
    elif method == "printed-label" and location == "rear-metallisation":
        admissible = False
        findings.append(
            "an adhered label on the rear metallisation sits inside the bond "
            "line the cell is later attached through"
        )
    elif location == "front-active-area":
        findings.append(
            "the mark sits inside the illuminated area, so its footprint is "
            "power the cell will never produce"
        )
    return {
        "marking_method": method,
        "mark_location": location,
        "admissible": admissible,
        "findings": findings,
    }


def mark_survives_processing(marking_method, process_exposure):
    """Decide whether the mark is still readable after downstream processing."""
    method = _require_choice("marking_method", marking_method, MARKING_METHODS)
    exposure = _require_choice(
        "process_exposure", process_exposure, PROCESS_EXPOSURES
    )
    survives = _SURVIVAL[method][exposure]
    findings = []
    if method != "record-only" and not survives:
        findings.append(
            "a %s mark does not stay legible through %s, so the cell stops "
            "being identifiable at the step that matters most"
            % (method, exposure)
        )
    return {
        "marking_method": method,
        "process_exposure": exposure,
        "survives_processing": survives,
        "findings": findings,
    }


def active_area_loss_fraction(mark_area_mm2, cell_active_area_mm2, mark_location):
    """Share of the illuminated area the mark takes away.

    A mark outside the illuminated area costs nothing, however large it
    is; a mark inside it costs its own footprint.
    """
    footprint = _require_non_negative("mark_area_mm2", mark_area_mm2)
    active = _require_positive("cell_active_area_mm2", cell_active_area_mm2)
    location = _require_choice("mark_location", mark_location, MARK_LOCATIONS)
    if location != "front-active-area":
        return 0.0
    if footprint >= active:
        raise ValueError(
            "a mark footprint of %r mm2 is not smaller than the %r mm2 active "
            "area it is placed in" % (footprint, active)
        )
    return footprint / active


def achieved_traceability_depth(code_fields, register_resolves_wafer_lot=False):
    """Read the depth the coded fields and the delivery register actually reach."""
    if not isinstance(code_fields, (list, tuple)):
        raise ValueError("code_fields must be a sequence of coded field names")
    linked = _require_flag(
        "register_resolves_wafer_lot", register_resolves_wafer_lot
    )
    fields = []
    for item in code_fields:
        field = _require_choice("code field", item, CODE_FIELDS)
        if field in fields:
            raise ValueError("code field %r is declared twice" % field)
        fields.append(field)

    findings = []
    if "wafer-lot-code" in fields:
        depth = DEPTH_WAFER_LOT
    elif "cell-serial" in fields and linked:
        depth = DEPTH_WAFER_LOT
    elif "cell-serial" in fields:
        depth = DEPTH_CELL
        findings.append(
            "the code identifies the cell but nothing reaches the wafer lot it "
            "was cut from; the delivery register has to close that gap"
        )
    elif "production-lot-code" in fields:
        depth = DEPTH_PRODUCTION_LOT
        findings.append(
            "the code reaches the production lot only; two cells out of one lot "
            "are indistinguishable on the hardware"
        )
    else:
        depth = DEPTH_NONE
        findings.append("the code carries no field that identifies anything")

    if linked and "cell-serial" not in fields:
        findings.append(
            "a register that resolves wafer lots needs a cell serial to key on; "
            "without one it cannot be entered from the hardware"
        )
    return {"depth": depth, "fields": fields, "findings": findings}


def depth_shortfall(required_depth, reached_depth):
    """Steps short of the depth the process identification document sets."""
    required = _require_choice("required_depth", required_depth, tuple(DEPTH_RANK))
    reached = _require_choice("reached_depth", reached_depth, tuple(DEPTH_RANK))
    if required == DEPTH_NONE:
        raise ValueError(
            "a process document that requires no traceability depth gives the "
            "marking scheme nothing to be graded against"
        )
    gap = DEPTH_RANK[required] - DEPTH_RANK[reached]
    return {
        "required_depth": required,
        "reached_depth": reached,
        "steps_short": max(gap, 0),
        "meets_requirement": gap <= 0,
    }


def code_uniqueness(codes):
    """Find codes repeated across the delivered set of cells."""
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


def assess_cell_marking(cell, policy=None):
    """Grade the permanent marking of one delivered bare cell."""
    _require_mapping("cell", cell)
    settings = dict(DEFAULT_MARKING_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    cap = _require_non_negative(
        "max_active_area_loss_fraction",
        settings.get("max_active_area_loss_fraction"),
    )

    code = _require_label("code", cell.get("code"))
    placement = mark_placement_admissibility(
        cell.get("marking_method"), cell.get("mark_location")
    )
    permanence = mark_survives_processing(
        cell.get("marking_method"), cell.get("process_exposure")
    )
    loss = active_area_loss_fraction(
        cell.get("mark_area_mm2", 0.0),
        cell.get("cell_active_area_mm2"),
        cell.get("mark_location"),
    )
    depth = achieved_traceability_depth(
        cell.get("code_fields"),
        cell.get("register_resolves_wafer_lot", False),
    )
    shortfall = depth_shortfall(settings.get("required_depth"), depth["depth"])

    findings = ["%s: %s" % (code, f) for f in placement["findings"]]
    findings.extend("%s: %s" % (code, f) for f in permanence["findings"])
    findings.extend("%s: %s" % (code, f) for f in depth["findings"])

    within_cap = _at_most(loss, cap)
    if not within_cap:
        findings.append(
            "%s: the mark takes %.4g of the illuminated area against a %.4g cap"
            % (code, loss, cap)
        )
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

    if (
        not placement["admissible"]
        or not permanence["survives_processing"]
        or depth["depth"] == DEPTH_NONE
    ):
        verdict = MARKING_INADMISSIBLE
    elif not shortfall["meets_requirement"] or not within_cap:
        verdict = MARKING_SHALLOW
    else:
        verdict = MARKING_COMPLIANT

    return {
        "code": code,
        "marking_method": placement["marking_method"],
        "mark_location": placement["mark_location"],
        "admissible": placement["admissible"],
        "survives_processing": permanence["survives_processing"],
        "active_area_loss_fraction": loss,
        "within_area_cap": within_cap,
        "reached_depth": depth["depth"],
        "shortfall": shortfall,
        "verdict": verdict,
        "findings": findings,
    }


def assess_delivery_marking(case):
    """Full clause 7.1.3 roll-up over a delivered set of bare cells."""
    _require_mapping("case", case)
    delivery_id = _require_label("delivery_id", case.get("delivery_id"))
    cells = case.get("cells")
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError("case must carry a non-empty cells sequence")
    policy = case.get("policy")

    assessments = [assess_cell_marking(cell, policy) for cell in cells]
    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    uniqueness = code_uniqueness([a["code"] for a in assessments])
    for code in uniqueness["repeated"]:
        findings.append(
            "code %s is carried by more than one delivered cell; a repeated code "
            "resolves to a set, not to a cell" % code
        )

    compliant = [a for a in assessments if a["verdict"] == MARKING_COMPLIANT]
    not_established = sorted(
        a["code"] for a in assessments if a["verdict"] == MARKING_INADMISSIBLE
    )
    compliant_share = len(compliant) / len(assessments)

    worst = min(MARKING_RANK[a["verdict"]] for a in assessments)
    verdict = next(k for k, v in MARKING_RANK.items() if v == worst)
    if uniqueness["repeated"] and verdict == MARKING_COMPLIANT:
        verdict = MARKING_INADMISSIBLE

    weakest = min(
        assessments,
        key=lambda a: (
            MARKING_RANK[a["verdict"]],
            -a["shortfall"]["steps_short"],
            a["code"],
        ),
    )
    return {
        "delivery_id": delivery_id,
        "assessments": assessments,
        "uniqueness": uniqueness,
        "verdict": verdict,
        "weakest_cell": weakest["code"],
        "not_established": not_established,
        "compliant_share": compliant_share,
        "fully_compliant": _at_least(compliant_share, 1.0)
        and not uniqueness["repeated"],
        "findings": findings,
    }
