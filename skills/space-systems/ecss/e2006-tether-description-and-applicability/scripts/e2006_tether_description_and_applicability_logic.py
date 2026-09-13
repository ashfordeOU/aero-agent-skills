#!/usr/bin/env python3
"""Deployed-tether description and applicability (ECSS-E-ST-20-06C cl. 10.1).

Deterministic, offline, stdlib-only implementation of the applicability
procedure for thin deployed or connecting elements on a spacecraft system.
The standard text is not reproduced; the clause is cited as an anchor only
and the engineering intent is re-expressed as a checkable procedure:

  * measure the slenderness of each deployed or connecting element,
  * categorize it (electrodynamic tether, conducting tether, non-conducting
    tether, inter-body connecting cable, or out of scope),
  * decide whether the tether provisions apply to it,
  * enumerate the electrical hazard families the applicability drags into
    the design, and
  * report any hazard family left without a control owner.
"""

import math

# An element counts as "thin" once its deployed length exceeds its diameter
# by this factor; below it the item behaves as a boom or a strut, not a
# tether, and the tether provisions do not attach to it.
SLENDERNESS_THRESHOLD = 100.0

# Below this deployed length the element is a jumper/harness detail rather
# than a deployed tether, whatever its slenderness.
MIN_DEPLOYED_LENGTH_M = 1.0

# Floating-point slack used only to absorb representation error on an exact
# boundary (a ratio landing a few ULPs below a threshold it equals). It never
# widens the engineering threshold itself.
BOUNDARY_REL_TOL = 1e-9
BOUNDARY_ABS_TOL = 1e-12

CONDUCTOR_KINDS = ("bare-conductor", "insulated-conductor", "dielectric")

ELEMENT_FUNCTIONS = (
    "electrodynamic",
    "momentum-exchange",
    "formation-keeping",
    "data-power-umbilical",
)

ORBIT_REGIMES = ("leo", "meo", "geo", "interplanetary")

CATEGORY_NOT_A_TETHER = "not-a-tether"
CATEGORY_ELECTRODYNAMIC = "electrodynamic-tether"
CATEGORY_CONDUCTING = "conducting-tether"
CATEGORY_NON_CONDUCTING = "non-conducting-tether"
CATEGORY_CONNECTING_CABLE = "connecting-cable"

CATEGORIES = (
    CATEGORY_ELECTRODYNAMIC,
    CATEGORY_CONDUCTING,
    CATEGORY_NON_CONDUCTING,
    CATEGORY_CONNECTING_CABLE,
    CATEGORY_NOT_A_TETHER,
)

# Hazard families every in-scope element carries, whatever its conductor.
STRUCTURAL_HAZARDS = (
    "tether-breakage-debris",
    "deployed-dynamics-oscillation",
)

# Regimes in which a conducting element sweeps enough magnetic flux for the
# motional end-potential family to be credible.
MAGNETIC_SWEEP_REGIMES = ("leo", "meo")

# Regimes with a plasma dense enough for the current-collection family.
DENSE_PLASMA_REGIMES = ("leo",)


def _require_number(value, name):
    """Return value as float, rejecting non-numeric and non-finite input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _require_positive(value, name):
    out = _require_number(value, name)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _at_or_above(value, threshold):
    """True when value >= threshold, absorbing float representation error."""
    if value >= threshold:
        return True
    return math.isclose(
        value, threshold, rel_tol=BOUNDARY_REL_TOL, abs_tol=BOUNDARY_ABS_TOL
    )


def slenderness_ratio(deployed_length_m, diameter_mm):
    """Deployed length divided by diameter, both reduced to metres."""
    length = _require_positive(deployed_length_m, "deployed_length_m")
    diameter = _require_positive(diameter_mm, "diameter_mm")
    return length / (diameter * 1e-3)


def is_thin_element(deployed_length_m, diameter_mm, threshold=SLENDERNESS_THRESHOLD):
    """True when the element is slender enough to behave as a tether."""
    limit = _require_positive(threshold, "threshold")
    return _at_or_above(slenderness_ratio(deployed_length_m, diameter_mm), limit)


def _element_field(element, key):
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping, got %r" % (type(element),))
    if key not in element:
        raise ValueError("element is missing required field %r" % (key,))
    return element[key]


def _require_flag(value, name):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def categorize_element(element):
    """Return the tether category of one deployed or connecting element.

    Required element fields: id, deployed_length_m, diameter_mm, conductor,
    function, connects_two_bodies.
    """
    conductor = _element_field(element, "conductor")
    if conductor not in CONDUCTOR_KINDS:
        raise ValueError(
            "unknown conductor %r; expected one of %s" % (conductor, CONDUCTOR_KINDS)
        )
    function = _element_field(element, "function")
    if function not in ELEMENT_FUNCTIONS:
        raise ValueError(
            "unknown function %r; expected one of %s" % (function, ELEMENT_FUNCTIONS)
        )
    length = _require_positive(
        _element_field(element, "deployed_length_m"), "deployed_length_m"
    )
    diameter = _require_positive(_element_field(element, "diameter_mm"), "diameter_mm")
    _require_flag(_element_field(element, "connects_two_bodies"), "connects_two_bodies")

    if length < MIN_DEPLOYED_LENGTH_M:
        return CATEGORY_NOT_A_TETHER
    if not is_thin_element(length, diameter):
        return CATEGORY_NOT_A_TETHER
    if conductor == "dielectric":
        return CATEGORY_NON_CONDUCTING
    if function == "electrodynamic":
        return CATEGORY_ELECTRODYNAMIC
    if function == "data-power-umbilical":
        return CATEGORY_CONNECTING_CABLE
    return CATEGORY_CONDUCTING


def applies_to_element(element):
    """True when the clause 10.1 tether provisions attach to this element."""
    category = categorize_element(element)
    if category == CATEGORY_NOT_A_TETHER:
        return False
    return bool(_element_field(element, "connects_two_bodies"))


def hazard_families(category, orbit_regime, conductor="dielectric"):
    """Electrical and mechanical hazard families an in-scope element carries."""
    if category not in CATEGORIES:
        raise ValueError(
            "unknown category %r; expected one of %s" % (category, CATEGORIES)
        )
    if orbit_regime not in ORBIT_REGIMES:
        raise ValueError(
            "unknown orbit_regime %r; expected one of %s"
            % (orbit_regime, ORBIT_REGIMES)
        )
    if conductor not in CONDUCTOR_KINDS:
        raise ValueError(
            "unknown conductor %r; expected one of %s" % (conductor, CONDUCTOR_KINDS)
        )
    if category == CATEGORY_NOT_A_TETHER:
        return []
    families = list(STRUCTURAL_HAZARDS)
    conducting = conductor in ("bare-conductor", "insulated-conductor")
    if conducting and orbit_regime in MAGNETIC_SWEEP_REGIMES:
        families.append("motional-emf-end-potential")
    if conducting and orbit_regime in DENSE_PLASMA_REGIMES:
        families.append("plasma-current-collection")
    if conductor == "bare-conductor":
        families.append("exposed-conductor-arcing")
    if conductor == "insulated-conductor":
        families.append("insulation-continuity-loss")
    return sorted(set(families))


def assess_element(element, orbit_regime):
    """Categorize one element and report its hazard and control status."""
    element_id = _element_field(element, "id")
    if not isinstance(element_id, str) or not element_id.strip():
        raise ValueError("element id must be a non-empty string, got %r" % (element_id,))
    category = categorize_element(element)
    conductor = element["conductor"]
    in_scope = category != CATEGORY_NOT_A_TETHER and element["connects_two_bodies"]
    families = hazard_families(category, orbit_regime, conductor) if in_scope else []
    controls = element.get("hazard_controls", [])
    if not isinstance(controls, (list, tuple)):
        raise ValueError("hazard_controls must be a list, got %r" % (type(controls),))
    for control in controls:
        if not isinstance(control, str):
            raise ValueError("hazard_controls entries must be strings, got %r" % (control,))
    uncontrolled = sorted(set(families) - set(controls))
    findings = []
    if (
        category != CATEGORY_NOT_A_TETHER
        and not element["connects_two_bodies"]
    ):
        findings.append(
            "%s: slender deployed item does not span two bodies; "
            "out of scope for the tether provisions" % element_id
        )
    for family in uncontrolled:
        findings.append("%s: hazard family %s has no control on record" % (element_id, family))
    return {
        "id": element_id,
        "category": category,
        "slenderness": slenderness_ratio(
            element["deployed_length_m"], element["diameter_mm"]
        ),
        "in_scope": in_scope,
        "hazard_families": families,
        "uncontrolled_hazards": uncontrolled,
        "findings": findings,
        "compliant": in_scope is False or not uncontrolled,
    }


def assess_inventory(elements, orbit_regime):
    """Run the applicability decision across a deployed-element inventory."""
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a list, got %r" % (type(elements),))
    if not elements:
        raise ValueError("elements must not be empty")
    seen = set()
    records = []
    for element in elements:
        record = assess_element(element, orbit_regime)
        if record["id"] in seen:
            raise ValueError("duplicate element id %r in inventory" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
    in_scope = [r for r in records if r["in_scope"]]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    union = sorted({f for r in in_scope for f in r["hazard_families"]})
    return {
        "orbit_regime": orbit_regime,
        "element_count": len(records),
        "in_scope_ids": [r["id"] for r in in_scope],
        "out_of_scope_ids": [r["id"] for r in records if not r["in_scope"]],
        "hazard_families": union,
        "records": records,
        "findings": findings,
        "clause_applicable": bool(in_scope),
        "compliant": not findings,
    }


def applicability_statement(summary):
    """One-line applicability verdict for an inventory summary."""
    if not isinstance(summary, dict) or "clause_applicable" not in summary:
        raise ValueError("summary must be an assess_inventory result")
    if not summary["clause_applicable"]:
        return "tether provisions do not apply: no in-scope deployed element"
    return "tether provisions apply to %d element(s): %s" % (
        len(summary["in_scope_ids"]),
        ", ".join(summary["in_scope_ids"]),
    )
