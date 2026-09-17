"""Accountability for electronic part control on a class 3 programme.

Anchor: ECSS-Q-ST-60C clause 6.1.2.1 (naming the unit accountable for the
electronic part control activities of a class 3 programme). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read each candidate unit's declared part control functions, keeping the
   names the programme does not recognise visible rather than dropping them.
2. Test every candidate for admissibility: declared in the project
   organization, an accountable role named, part selection approval held, an
   escalation depth inside the ceiling, independence from the design authority
   and a mandate share at or above the floor.
3. Name the functions no unit holds and the functions more than one unit
   claims.
4. Nominate the accountable unit: the admissible candidate holding the largest
   mandate, ties broken by the shorter escalation path and then by unit id.
5. Return one disposition: accountability-assigned, accountability-split or
   accountability-unassigned.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "ESCALATION_DEPTH_CEILING",
    "MANDATE_FLOOR",
    "PART_CONTROL_FUNCTIONS",
    "unit_id",
    "ordered_functions",
    "declared_functions",
    "unrecognised_functions",
    "mandate_share",
    "unit_defects",
    "unit_findings",
    "admissible_units",
    "unassigned_functions",
    "contested_functions",
    "accountable_unit",
    "organization_disposition",
    "compile_class_3_parts_control_organization",
]

# Mandate share is a quotient of small counts; a candidate sitting exactly on
# the floor can land a few ULP on the wrong side. Absorb the representation
# error here, never by moving the floor itself.
BOUND_TOLERANCE = 1e-9

# The electronic part control functions a class 3 programme has to place with
# a named unit, in the order they are reported.
PART_CONTROL_FUNCTIONS = (
    "part-selection-approval",
    "procurement-source-control",
    "qualification-status-review",
    "alert-and-obsolescence-handling",
    "nonconformance-referral",
    "declared-parts-list-maintenance",
)

_FUNCTION_ORDER = {name: index for index, name in enumerate(PART_CONTROL_FUNCTIONS)}

# Approving the parts is the function that cannot be delegated away: a unit
# holding everything else and not this one is not the accountable unit.
_MANDATORY_FUNCTION = "part-selection-approval"

# Share of the part control functions one unit must hold to carry the mandate.
MANDATE_FLOOR = 0.75

# Reporting levels between the accountable unit and the project manager. A
# longer path is a unit that cannot escalate a part decision in time.
ESCALATION_DEPTH_CEILING = 3


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _is_text(value):
    return isinstance(value, str) and bool(value.strip())


def _require_unit(unit):
    if not isinstance(unit, dict):
        raise ValueError("unit must be a mapping, got %r" % (unit,))
    return unit


def unit_id(unit):
    """Return the unit identifier, or a stable placeholder when none is given."""
    _require_unit(unit)
    if _is_text(unit.get("unit_id")):
        return unit["unit_id"].strip()
    return "unnamed-unit"


def ordered_functions(names):
    """Return recognised function names in report order, without repetition."""
    if not isinstance(names, (list, tuple, set, frozenset)):
        raise ValueError("functions must be a sequence or set")
    seen = []
    for item in names:
        name = _require_text(item, "function").casefold()
        if name in _FUNCTION_ORDER and name not in seen:
            seen.append(name)
    return sorted(seen, key=lambda name: _FUNCTION_ORDER[name])


def declared_functions(unit):
    """Return the recognised part control functions one unit declares."""
    _require_unit(unit)
    return ordered_functions(unit.get("functions", []))


def unrecognised_functions(unit):
    """Return the function names a unit declares that the programme does not know."""
    _require_unit(unit)
    names = unit.get("functions", [])
    if not isinstance(names, (list, tuple, set, frozenset)):
        raise ValueError("functions must be a sequence or set")
    unknown = []
    for item in names:
        name = _require_text(item, "function").casefold()
        if name not in _FUNCTION_ORDER and name not in unknown:
            unknown.append(name)
    return sorted(unknown)


def mandate_share(unit):
    """Return the share of the part control functions one unit holds."""
    return len(declared_functions(unit)) / float(len(PART_CONTROL_FUNCTIONS))


def unit_defects(unit):
    """Return the admissibility defects one candidate unit carries.

    An empty list means the unit could be named accountable. unit keys read
    here: unit_id, declared_in_project_organization, accountable_role,
    functions, escalation_depth and independent_of_design_authority.
    """
    _require_unit(unit)
    defects = []
    if unit.get("declared_in_project_organization") is not True:
        defects.append("unit-not-declared-in-organization")
    if not _is_text(unit.get("accountable_role")):
        defects.append("accountable-role-not-named")
    held = declared_functions(unit)
    if not held:
        defects.append("no-part-control-function-held")
    if _MANDATORY_FUNCTION not in held:
        defects.append("part-selection-approval-not-held")
    if unrecognised_functions(unit):
        defects.append("function-not-recognised")
    depth = unit.get("escalation_depth")
    if not isinstance(depth, (int, float)) or isinstance(depth, bool):
        defects.append("escalation-depth-not-stated")
    else:
        value = _require_number(depth, "escalation depth")
        if value > ESCALATION_DEPTH_CEILING + BOUND_TOLERANCE:
            defects.append("escalation-depth-beyond-ceiling")
    if unit.get("independent_of_design_authority") is not True:
        defects.append("not-independent-of-design-authority")
    if mandate_share(unit) < MANDATE_FLOOR - BOUND_TOLERANCE:
        defects.append("mandate-below-floor")
    return defects


def _require_units(units):
    if not isinstance(units, (list, tuple)):
        raise ValueError("units must be a sequence")
    if not units:
        raise ValueError("units must name at least one candidate unit")
    for unit in units:
        _require_unit(unit)
    return list(units)


def unit_findings(units):
    """Return one entry per candidate unit carrying defects, in declared order."""
    candidates = _require_units(units)
    findings = []
    for unit in candidates:
        defects = unit_defects(unit)
        if defects:
            findings.append({"unit": unit_id(unit), "defects": defects})
    return findings


def admissible_units(units):
    """Return the candidate units that could be named accountable."""
    return [unit for unit in _require_units(units) if not unit_defects(unit)]


def unassigned_functions(units):
    """Return the part control functions no declared unit holds, in report order."""
    candidates = _require_units(units)
    held = set()
    for unit in candidates:
        if unit.get("declared_in_project_organization") is True:
            held.update(declared_functions(unit))
    return [name for name in PART_CONTROL_FUNCTIONS if name not in held]


def contested_functions(units):
    """Return the functions more than one declared unit claims, in report order."""
    candidates = _require_units(units)
    counts = {}
    for unit in candidates:
        if unit.get("declared_in_project_organization") is not True:
            continue
        for name in declared_functions(unit):
            counts[name] = counts.get(name, 0) + 1
    return [name for name in PART_CONTROL_FUNCTIONS if counts.get(name, 0) > 1]


def accountable_unit(units):
    """Return the identifier of the unit to name accountable, or None.

    The largest mandate wins; a tie goes to the shorter escalation path and
    then to the lower unit identifier, so the nomination is deterministic.
    """
    candidates = admissible_units(units)
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda unit: (
            -mandate_share(unit),
            float(unit.get("escalation_depth", ESCALATION_DEPTH_CEILING)),
            unit_id(unit),
        ),
    )
    return unit_id(ranked[0])


def organization_disposition(accountable, unassigned, contested):
    """Return the disposition implied by the declared organization.

    A function nobody holds, or no admissible unit at all, leaves the part
    control mandate unplaced and outranks an overlap between two units that
    both hold it.
    """
    for label, value in (("unassigned", unassigned), ("contested", contested)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a sequence, got %r" % (label, value))
    if accountable is not None and not _is_text(accountable):
        raise ValueError("accountable must be a unit identifier or None")
    if accountable is None or unassigned:
        return "accountability-unassigned"
    if contested:
        return "accountability-split"
    return "accountability-assigned"


def compile_class_3_parts_control_organization(project):
    """Name the clause 6.1.2.1 accountable unit of one class 3 programme.

    project keys: units and an optional project_id.
    """
    if not isinstance(project, dict):
        raise ValueError("project must be a mapping")
    units = _require_units(project.get("units", []))
    findings = unit_findings(units)
    admissible = [unit_id(unit) for unit in admissible_units(units)]
    unassigned = unassigned_functions(units)
    contested = contested_functions(units)
    accountable = accountable_unit(units)
    disposition = organization_disposition(accountable, unassigned, contested)
    mandate = None
    for unit in units:
        if unit_id(unit) == accountable:
            mandate = mandate_share(unit)
            break
    return {
        "unit_findings": findings,
        "admissible_units": admissible,
        "unassigned_functions": unassigned,
        "contested_functions": contested,
        "accountable_unit": accountable,
        "accountable_mandate_share": mandate,
        "disposition": disposition,
        "organization_ready": disposition == "accountability-assigned",
    }
