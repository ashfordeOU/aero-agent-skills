#!/usr/bin/env python3
"""Integral protection diodes among the deliverable items of a PVA.

Anchor: ECSS-E-ST-20-08C clause 9.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A photovoltaic assembly is handed over as a list of items, and the
protection diodes built into it are items on that list. Whether a given
diode belongs on the assembly's own line or on a separate line is
decided by how it is mounted, not by who made it, so the first question
is always where the diode physically lives.

Mounting categories
    integral-on-cell    bonded onto or monolithic with the cell assembly
    integral-on-panel   mounted on the assembly substrate or its harness
    external-on-bus     mounted off the assembly, in the spacecraft wiring

Delivery item lines
    assembly-item-list  the deliverable items of the photovoltaic assembly
    separate-item-list  a delivery line of its own, outside the assembly
    not-listed          the part ships but no delivery line carries it

An integral diode is delivered with the assembly and belongs on the
assembly item list. An external diode is a separate deliverable and does
not; carrying it on the assembly line double-counts it at incoming and
leaves the wiring set short at integration.

Three counts have to agree per string and they are gathered from three
different places: the protection the string architecture requires, the
diodes actually fitted, and the diodes the delivery paperwork declares.
Requirement against fitted is a protection question. Fitted against
declared is a traceability question. They fail separately and they are
repaired separately.

The per-section bypass count, the per-string blocking count and the
release floor below are declared project policy, not physical
constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MOUNTINGS = ("integral-on-cell", "integral-on-panel", "external-on-bus")

INTEGRAL_MOUNTINGS = ("integral-on-cell", "integral-on-panel")

ITEM_LINES = ("assembly-item-list", "separate-item-list", "not-listed")

STRING_DELIVERABLE = "string-items-deliverable"
STRING_CONCESSION = "string-items-deliverable-under-concession"
STRING_WITHHELD = "string-items-withheld"

STRING_RANK = {
    STRING_WITHHELD: 0,
    STRING_CONCESSION: 1,
    STRING_DELIVERABLE: 2,
}

DEFAULT_DELIVERY_POLICY = {
    "bypass_diodes_per_section": 1,
    "blocking_diodes_per_string": 1,
    "min_release_share": 1.0,
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


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    count = _require_count(name, value)
    if count == 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return count


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Release shares are quotients of counts, so a delivery sitting exactly
    on its floor can evaluate a unit in the last place under it. The
    comparison absorbs that; the floor itself stays as declared.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def categorize_diode_mounting(mounting):
    """Say whether a diode mounted this way ships with the assembly."""
    where = _require_choice("mounting", mounting, MOUNTINGS)
    integral = where in INTEGRAL_MOUNTINGS
    return {
        "mounting": where,
        "integral": integral,
        "expected_item_line": (
            "assembly-item-list" if integral else "separate-item-list"
        ),
    }


def item_line_placement(mounting, listed_on):
    """Check the delivery line a diode is carried on against its mounting."""
    category = categorize_diode_mounting(mounting)
    line = _require_choice("listed_on", listed_on, ITEM_LINES)
    expected = category["expected_item_line"]
    findings = []
    misfiled = False

    if line == "not-listed":
        misfiled = True
        findings.append(
            "a %s diode ships with no delivery line carrying it, so it arrives "
            "as hardware nobody booked in" % category["mounting"]
        )
    elif line != expected:
        misfiled = True
        if category["integral"]:
            findings.append(
                "an integral diode is carried on a separate delivery line; it "
                "cannot be received on its own because it arrives bonded to the "
                "assembly"
            )
        else:
            findings.append(
                "an external diode is carried on the assembly item list, which "
                "double-counts it at incoming and leaves the wiring set short "
                "at integration"
            )
    return {
        "mounting": category["mounting"],
        "integral": category["integral"],
        "listed_on": line,
        "expected_item_line": expected,
        "correctly_placed": not misfiled,
        "findings": findings,
    }


def required_protection_diodes(sections, policy=None):
    """Diodes the string architecture calls for, split by function."""
    count = _require_positive_count("sections", sections)
    settings = dict(DEFAULT_DELIVERY_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    per_section = _require_count(
        "bypass_diodes_per_section", settings.get("bypass_diodes_per_section")
    )
    per_string = _require_count(
        "blocking_diodes_per_string", settings.get("blocking_diodes_per_string")
    )
    bypass = count * per_section
    if bypass + per_string == 0:
        raise ValueError(
            "a policy asking for no bypass and no blocking diodes leaves the "
            "string with no protection to grade"
        )
    return {
        "sections": count,
        "required_bypass": bypass,
        "required_blocking": per_string,
        "required_total": bypass + per_string,
    }


def reconcile_diode_inventory(fitted, declared):
    """Compare the diodes on the hardware with the diodes on the item list."""
    on_hardware = _require_count("fitted", fitted)
    on_paper = _require_count("declared", declared)
    accounted = min(on_hardware, on_paper)
    return {
        "fitted": on_hardware,
        "declared": on_paper,
        "accounted": accounted,
        "unlisted": max(on_hardware - on_paper, 0),
        "phantom": max(on_paper - on_hardware, 0),
        "reconciled": on_hardware == on_paper,
    }


def deliverable_diode_bracket(required, fitted, declared):
    """Bracket how many protection diodes this string actually delivers.

    At most the diodes both fitted and declared; at least that figure
    less the protection the architecture asked for and never got, since
    a string short of protection cannot deliver against its own count.
    """
    needed = _require_positive_count("required", required)
    inventory = reconcile_diode_inventory(fitted, declared)
    upper = inventory["accounted"]
    shortfall = max(needed - inventory["fitted"], 0)
    lower = max(upper - shortfall, 0)
    return {
        "required": needed,
        "at_most": upper,
        "at_least": lower,
        "protection_shortfall": shortfall,
        "bracket_width": upper - lower,
    }


def assess_string_deliverables(string, policy=None):
    """Grade the protection diode items of one string of the assembly."""
    _require_mapping("string", string)
    string_id = _require_label("string_id", string.get("string_id"))
    requirement = required_protection_diodes(string.get("sections"), policy)

    fitted_bypass = _require_count(
        "fitted_bypass", string.get("fitted_bypass")
    )
    fitted_blocking = _require_count(
        "fitted_blocking", string.get("fitted_blocking")
    )
    fitted = fitted_bypass + fitted_blocking
    placement = item_line_placement(
        string.get("mounting"), string.get("listed_on")
    )
    inventory = reconcile_diode_inventory(fitted, string.get("declared_diodes"))
    bracket = deliverable_diode_bracket(
        requirement["required_total"], fitted, string.get("declared_diodes")
    )

    findings = ["%s: %s" % (string_id, f) for f in placement["findings"]]
    if fitted_bypass < requirement["required_bypass"]:
        findings.append(
            "%s: %d section(s) call for %d bypass diode(s) and %d are fitted, so "
            "a shadowed section drives the string in reverse"
            % (
                string_id,
                requirement["sections"],
                requirement["required_bypass"],
                fitted_bypass,
            )
        )
    if fitted_blocking < requirement["required_blocking"]:
        findings.append(
            "%s: the architecture asks for %d blocking diode(s) and %d are "
            "fitted, so the string can be back-fed from the bus"
            % (string_id, requirement["required_blocking"], fitted_blocking)
        )
    if inventory["unlisted"]:
        findings.append(
            "%s: %d diode(s) are fitted that no delivery line declares; they "
            "ship as untracked hardware"
            % (string_id, inventory["unlisted"])
        )
    if inventory["phantom"]:
        findings.append(
            "%s: the item list declares %d diode(s) the assembly does not "
            "carry" % (string_id, inventory["phantom"])
        )

    under_protected = bracket["protection_shortfall"] > 0
    if under_protected or inventory["phantom"] or not placement["correctly_placed"]:
        disposition = STRING_WITHHELD
    elif inventory["unlisted"]:
        disposition = STRING_CONCESSION
    else:
        disposition = STRING_DELIVERABLE

    return {
        "string_id": string_id,
        "requirement": requirement,
        "fitted_bypass": fitted_bypass,
        "fitted_blocking": fitted_blocking,
        "fitted_total": fitted,
        "placement": placement,
        "inventory": inventory,
        "bracket": bracket,
        "fully_protected": not under_protected,
        "disposition": disposition,
        "findings": findings,
    }


def assess_assembly_deliverables(case):
    """Full clause 9.2.2 roll-up over the strings of one assembly."""
    _require_mapping("case", case)
    assembly_id = _require_label("assembly_id", case.get("assembly_id"))
    strings = case.get("strings")
    if not isinstance(strings, (list, tuple)) or not strings:
        raise ValueError("case must carry a non-empty strings sequence")
    settings = dict(DEFAULT_DELIVERY_POLICY)
    if case.get("policy") is not None:
        settings.update(_require_mapping("policy", case.get("policy")))
    floor = settings.get("min_release_share")
    if not isinstance(floor, (int, float)) or isinstance(floor, bool):
        raise ValueError("min_release_share must be a number, got %r" % (floor,))
    floor = float(floor)

    assessments = [
        assess_string_deliverables(item, case.get("policy")) for item in strings
    ]
    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    seen = []
    for assessment in assessments:
        if assessment["string_id"] in seen:
            raise ValueError(
                "string identifier %r appears twice in one assembly"
                % assessment["string_id"]
            )
        seen.append(assessment["string_id"])

    required_total = sum(a["requirement"]["required_total"] for a in assessments)
    fitted_total = sum(a["fitted_total"] for a in assessments)
    released_total = sum(
        a["bracket"]["at_least"]
        for a in assessments
        if a["disposition"] != STRING_WITHHELD
    )
    release_share = released_total / required_total

    withheld = sorted(
        a["string_id"] for a in assessments if a["disposition"] == STRING_WITHHELD
    )
    concession = sorted(
        a["string_id"] for a in assessments if a["disposition"] == STRING_CONCESSION
    )
    worst = min(STRING_RANK[a["disposition"]] for a in assessments)
    disposition = next(k for k, v in STRING_RANK.items() if v == worst)
    weakest = min(
        assessments,
        key=lambda a: (
            STRING_RANK[a["disposition"]],
            -a["bracket"]["protection_shortfall"],
            a["string_id"],
        ),
    )
    return {
        "assembly_id": assembly_id,
        "assessments": assessments,
        "required_diodes": required_total,
        "fitted_diodes": fitted_total,
        "released_diodes": released_total,
        "release_share": release_share,
        "meets_release_floor": _at_least(release_share, floor),
        "disposition": disposition,
        "withheld_strings": withheld,
        "concession_strings": concession,
        "weakest_string": weakest["string_id"],
        "findings": findings,
    }
