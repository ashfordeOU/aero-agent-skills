"""Support structure design and removal for additively manufactured parts.

Anchor: ECSS-Q-ST-70-80 part clauses covering support structures: designing
them so they can be removed, and removing them without damaging the part.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each support region: the contact area it fuses to the part with,
   the interface style that area is broken through, how a tool reaches it, the
   class of surface it lands on, and the witness height it leaves behind.
2. Reduce the contact area to the effective bonded area of the interface, since
   a toothed or perforated interface fuses over a fraction of its footprint.
3. Form the force needed to break that bond, and the load the local part
   section can carry before it is the part that yields instead.
4. Decide the removal method from access, surface class and those two forces,
   escalating a break-off that would overload the section to a cutting method
   rather than accepting the damage.
5. Grade the witness left behind against the machining allowance of the
   surface, and refuse a region that no tool can reach or that lands on a
   functional surface that removal cannot restore.
"""

import math

__all__ = [
    "FORCE_TOLERANCE",
    "INTERFACE_BOND_FRACTION",
    "ACCESS_CLASSES",
    "SURFACE_CLASSES",
    "validate_region",
    "effective_bond_area_mm2",
    "removal_force_n",
    "allowable_load_n",
    "damage_ratio",
    "select_removal_method",
    "witness_finding",
    "evaluate_region",
    "assess_support_removal",
]

# Forces are products and quotients of measured quantities, so a break-off load
# exactly equal to the section allowable can land a few units in the last place
# above it. The comparison absorbs that; the allowable is never raised.
FORCE_TOLERANCE = 1e-9

# Fraction of the contact footprint that actually fuses, per interface style.
INTERFACE_BOND_FRACTION = {
    "solid": 1.0,
    "perforated": 0.5,
    "toothed": 0.25,
}

ACCESS_CLASSES = ("open", "recessed", "internal-closed")
SURFACE_CLASSES = ("non-critical", "machined-later", "critical-functional")


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s cannot be negative, got %r" % (label, value))
    return number


def validate_region(region):
    """Return a validated support-region record."""
    if not isinstance(region, dict):
        raise ValueError("region must be a mapping")
    identifier = region.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("region id must be a non-empty string")
    interface = region.get("interface")
    if interface not in INTERFACE_BOND_FRACTION:
        raise ValueError(
            "region %s interface must be one of %s"
            % (identifier, ", ".join(sorted(INTERFACE_BOND_FRACTION)))
        )
    access = region.get("access")
    if access not in ACCESS_CLASSES:
        raise ValueError(
            "region %s access must be one of %s" % (identifier, ", ".join(ACCESS_CLASSES))
        )
    surface_class = region.get("surface_class")
    if surface_class not in SURFACE_CLASSES:
        raise ValueError(
            "region %s surface_class must be one of %s"
            % (identifier, ", ".join(SURFACE_CLASSES))
        )
    return {
        "id": identifier,
        "interface": interface,
        "access": access,
        "surface_class": surface_class,
        "contact_area_mm2": _positive("region %s contact_area_mm2" % identifier,
                                      region.get("contact_area_mm2")),
        "section_area_mm2": _positive("region %s section_area_mm2" % identifier,
                                      region.get("section_area_mm2")),
        "witness_height_mm": _non_negative("region %s witness_height_mm" % identifier,
                                           region.get("witness_height_mm", 0.0)),
        "machining_allowance_mm": _non_negative(
            "region %s machining_allowance_mm" % identifier,
            region.get("machining_allowance_mm", 0.0)),
    }


def effective_bond_area_mm2(contact_area_mm2, interface):
    """Return the area that actually fuses for a given interface style."""
    if interface not in INTERFACE_BOND_FRACTION:
        raise ValueError("unknown interface style %r" % (interface,))
    return _positive("contact_area_mm2", contact_area_mm2) * INTERFACE_BOND_FRACTION[interface]


def removal_force_n(effective_area_mm2, interface_strength_mpa):
    """Return the force needed to break the support interface, in newtons."""
    area = _positive("effective_area_mm2", effective_area_mm2)
    strength = _positive("interface_strength_mpa", interface_strength_mpa)
    return area * strength


def allowable_load_n(section_area_mm2, allowable_stress_mpa, safety_factor=1.0):
    """Return the load the local part section may carry, in newtons."""
    area = _positive("section_area_mm2", section_area_mm2)
    stress = _positive("allowable_stress_mpa", allowable_stress_mpa)
    factor = _positive("safety_factor", safety_factor)
    if factor < 1.0:
        raise ValueError("safety_factor cannot be below 1, got %r" % (safety_factor,))
    return area * stress / factor


def damage_ratio(required_force_n, allowable_force_n):
    """Return the ratio of break-off force to the section allowable."""
    required = _positive("required_force_n", required_force_n)
    allowable = _positive("allowable_force_n", allowable_force_n)
    return required / allowable


def select_removal_method(record, force_n, manual_force_limit_n):
    """Return the removal method implied by access, surface class and force."""
    limit = _positive("manual_force_limit_n", manual_force_limit_n)
    force = _positive("force_n", force_n)
    if record["access"] == "internal-closed":
        return "not-removable-redesign"
    if record["surface_class"] == "critical-functional":
        return "not-removable-redesign"
    within_manual = force < limit or math.isclose(
        force, limit, rel_tol=FORCE_TOLERANCE, abs_tol=0.0
    )
    if record["access"] == "open":
        return "manual-break-off" if within_manual else "machining"
    return "machining" if within_manual else "wire-edm"


def witness_finding(record):
    """Return a finding when the witness left behind outlives its allowance."""
    if record["surface_class"] == "non-critical":
        return None
    witness = record["witness_height_mm"]
    allowance = record["machining_allowance_mm"]
    if witness > allowance and not math.isclose(
        witness, allowance, rel_tol=FORCE_TOLERANCE, abs_tol=0.0
    ):
        return ("region %s leaves %.3f mm of witness on a %s surface with %.3f mm of allowance"
                % (record["id"], witness, record["surface_class"], allowance))
    return None


def evaluate_region(region, spec):
    """Evaluate one support region and return its removal record."""
    record = validate_region(region)
    effective = effective_bond_area_mm2(record["contact_area_mm2"], record["interface"])
    force = removal_force_n(effective, spec["interface_strength_mpa"])
    allowable = allowable_load_n(
        record["section_area_mm2"],
        spec["allowable_stress_mpa"],
        spec.get("safety_factor", 1.0),
    )
    ratio = damage_ratio(force, allowable)
    method = select_removal_method(record, force, spec["manual_force_limit_n"])
    escalated = False
    if method == "manual-break-off" and ratio > 1.0 and not math.isclose(
        ratio, 1.0, rel_tol=FORCE_TOLERANCE, abs_tol=0.0
    ):
        method = "machining"
        escalated = True
    return {
        "id": record["id"],
        "effective_bond_area_mm2": effective,
        "removal_force_n": force,
        "allowable_load_n": allowable,
        "damage_ratio": ratio,
        "method": method,
        "escalated_from_break_off": escalated,
        "witness_finding": witness_finding(record),
        "access": record["access"],
        "surface_class": record["surface_class"],
    }


def assess_support_removal(spec):
    """Run the full support design and removal assessment.

    spec keys: regions, interface_strength_mpa, allowable_stress_mpa,
    manual_force_limit_n, optional safety_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("regions", "interface_strength_mpa", "allowable_stress_mpa",
                "manual_force_limit_n"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    regions = spec["regions"]
    if not isinstance(regions, (list, tuple)) or not regions:
        raise ValueError("spec['regions'] must be a non-empty sequence")
    records = []
    seen = set()
    blocking = []
    findings = []
    for region in regions:
        record = evaluate_region(region, spec)
        if record["id"] in seen:
            raise ValueError("duplicate support region id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
        if record["method"] == "not-removable-redesign":
            if record["access"] == "internal-closed":
                blocking.append(
                    "region %s is inside a closed volume; no tool reaches it" % record["id"]
                )
            else:
                blocking.append(
                    "region %s contacts a functional surface that removal cannot restore"
                    % record["id"]
                )
        if record["witness_finding"] is not None:
            blocking.append(record["witness_finding"])
        if record["escalated_from_break_off"]:
            findings.append(
                "region %s cannot be broken off: the interface needs %.0f N against a "
                "%.0f N section allowable, so it is cut instead"
                % (record["id"], record["removal_force_n"], record["allowable_load_n"])
            )
    if blocking:
        verdict = "redesign-required"
    elif findings:
        verdict = "removable-with-findings"
    else:
        verdict = "removable"
    return {
        "verdict": verdict,
        "records": records,
        "blocking": blocking,
        "findings": findings,
        "methods": {record["id"]: record["method"] for record in records},
    }
