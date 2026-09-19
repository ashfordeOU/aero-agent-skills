#!/usr/bin/env python3
"""The test-centre organization behind quality and safety management.

Anchor: ECSS-Q-ST-20-07 clause 5.3.1, the requirement that a test centre
defines its organization: the units it is built from, the reporting
structure that joins them, the quality and safety functions that have to
exist somewhere in it, and the interfaces across which those functions
work. The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

Four things follow from what the organization chart is for.

A chart is a tree, and a tree has to be provable. A unit reporting to a
parent the chart does not hold is an orphan, a unit reachable from
itself is a cycle, and a chart with two roots is two organizations. Each
of those is a structural defect that has to be caught before any
question about functions can be asked, because none of the later walks
terminate on a broken chart.

A function exists where somebody holds it, not where the chart draws a
box. A required quality or safety function nobody holds is missing even
when a unit is named after it, and a function held by two units is
reported as shared rather than silently counted once.

Assurance only assures when it is not reporting to the thing it grades.
The quality and safety functions therefore have their reporting chain
walked to the root, and a chain passing through the test-operations line
is an independence defect however senior the eventual reporting point
is.

An interface is a declared pair, and both ends have to exist. A declared
interface naming a unit the chart does not hold is a dangling interface;
a required pair with no declaration behind it is an interface gap. They
are reported apart because one is a wrong entry and the other is a
missing one.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

FUNCTION_QUALITY_ASSURANCE = "quality-assurance-function"
FUNCTION_SAFETY_ASSURANCE = "safety-assurance-function"
FUNCTION_TEST_OPERATIONS = "test-operations-function"
FUNCTION_CONFIGURATION = "configuration-management-function"
FUNCTION_METROLOGY = "metrology-and-calibration-function"

RECOGNISED_FUNCTIONS = (
    FUNCTION_QUALITY_ASSURANCE,
    FUNCTION_SAFETY_ASSURANCE,
    FUNCTION_TEST_OPERATIONS,
    FUNCTION_CONFIGURATION,
    FUNCTION_METROLOGY,
)

REQUIRED_FUNCTIONS = (
    FUNCTION_QUALITY_ASSURANCE,
    FUNCTION_SAFETY_ASSURANCE,
    FUNCTION_TEST_OPERATIONS,
    FUNCTION_CONFIGURATION,
    FUNCTION_METROLOGY,
)

INDEPENDENT_FUNCTIONS = (FUNCTION_QUALITY_ASSURANCE, FUNCTION_SAFETY_ASSURANCE)

REQUIRED_INTERFACES = (
    (FUNCTION_QUALITY_ASSURANCE, FUNCTION_TEST_OPERATIONS),
    (FUNCTION_SAFETY_ASSURANCE, FUNCTION_TEST_OPERATIONS),
    (FUNCTION_METROLOGY, FUNCTION_TEST_OPERATIONS),
)

REQUIRED_UNIT_FIELDS = ("unit_id", "reports_to", "functions")

ORGANIZATION_UNDEFINED = "test-centre-organization-undefined"
STRUCTURE_INVALID = "test-centre-structure-invalid"
FUNCTION_MISSING = "test-centre-function-unassigned"
INDEPENDENCE_COMPROMISED = "test-centre-assurance-independence-compromised"
INTERFACE_GAPS = "test-centre-interface-undeclared"
ORGANIZATION_DEFINED = "test-centre-organization-defined"


def _require_token(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty identifier, got %r" % (name, value))
    return value.strip()


def _require_function_list(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence of function names, got %r" % (name, value))
    out = []
    for index, item in enumerate(value):
        token = _require_token("%s[%d]" % (name, index), item)
        if token not in RECOGNISED_FUNCTIONS:
            raise ValueError("unrecognised quality and safety function '%s'" % token)
        out.append(token)
    if len(set(out)) != len(out):
        raise ValueError("%s names the same function twice" % name)
    return out


def validate_unit(unit):
    """Return one validated organizational unit."""
    if not isinstance(unit, dict):
        raise ValueError("an organizational unit must be a mapping, got %r" % (unit,))
    for field in REQUIRED_UNIT_FIELDS:
        if field not in unit:
            raise ValueError("organizational unit missing field '%s'" % field)
    reports_to = unit["reports_to"]
    if reports_to is not None:
        reports_to = _require_token("reports_to", reports_to)
    unit_id = _require_token("unit_id", unit["unit_id"])
    if reports_to == unit_id:
        raise ValueError("unit '%s' reports to itself" % unit_id)
    return {
        "unit_id": unit_id,
        "reports_to": reports_to,
        "functions": _require_function_list("functions", unit["functions"]),
    }


def validate_interface(interface):
    """Return one validated declared interface as an ordered unit pair."""
    if not isinstance(interface, (list, tuple)) or len(interface) != 2:
        raise ValueError("a declared interface must be a pair of unit ids, got %r" % (interface,))
    left = _require_token("interface left unit", interface[0])
    right = _require_token("interface right unit", interface[1])
    if left == right:
        raise ValueError("unit '%s' cannot declare an interface with itself" % left)
    return (left, right)


def validate_organization(organization):
    """Return the validated organization record."""
    if not isinstance(organization, dict):
        raise ValueError("organization must be a mapping")
    for field in ("defined", "units", "interfaces"):
        if field not in organization:
            raise ValueError("organization missing field '%s'" % field)
    defined = organization["defined"]
    if not isinstance(defined, bool):
        raise ValueError("defined must be a boolean")
    if not isinstance(organization["units"], (list, tuple)):
        raise ValueError("units must be a sequence")
    units = [validate_unit(item) for item in organization["units"]]
    seen = set()
    for unit in units:
        if unit["unit_id"] in seen:
            raise ValueError("unit '%s' is registered twice" % unit["unit_id"])
        seen.add(unit["unit_id"])
    if not isinstance(organization["interfaces"], (list, tuple)):
        raise ValueError("interfaces must be a sequence")
    interfaces = [validate_interface(item) for item in organization["interfaces"]]
    normalised = set()
    for left, right in interfaces:
        key = tuple(sorted((left, right)))
        if key in normalised:
            raise ValueError("the interface %s-%s is declared twice" % key)
        normalised.add(key)
    return {
        "defined": defined,
        "units": units,
        "interfaces": interfaces,
        "unit_index": {unit["unit_id"]: unit for unit in units},
    }


def _as_organization(organization):
    """Return the record already validated, validating a raw one first."""
    if isinstance(organization, dict) and organization.get("unit_index") is not None:
        return organization
    return validate_organization(organization)


def root_units(organization):
    """Return the unit ids that report to nobody."""
    record = _as_organization(organization)
    return [u["unit_id"] for u in record["units"] if u["reports_to"] is None]


def orphan_units(organization):
    """Return the unit ids reporting to a unit the chart does not hold."""
    record = _as_organization(organization)
    index = record["unit_index"]
    return [
        u["unit_id"]
        for u in record["units"]
        if u["reports_to"] is not None and u["reports_to"] not in index
    ]


def reporting_chain(organization, unit_id):
    """Return the chain from a unit up to its root, raising on a cycle."""
    record = _as_organization(organization)
    index = record["unit_index"]
    start = _require_token("unit_id", unit_id)
    if start not in index:
        raise ValueError("the chart holds no unit '%s'" % start)
    chain = [start]
    seen = {start}
    current = index[start]["reports_to"]
    while current is not None:
        if current not in index:
            raise ValueError(
                "unit '%s' reports to '%s', which the chart does not hold" % (chain[-1], current)
            )
        if current in seen:
            raise ValueError("the reporting chain from '%s' is a cycle" % start)
        chain.append(current)
        seen.add(current)
        current = index[current]["reports_to"]
    return chain


def cyclic_units(organization):
    """Return the unit ids whose reporting chain never reaches a root."""
    record = _as_organization(organization)
    index = record["unit_index"]
    out = []
    for unit in record["units"]:
        seen = {unit["unit_id"]}
        current = unit["reports_to"]
        while current is not None and current in index:
            if current in seen:
                out.append(unit["unit_id"])
                break
            seen.add(current)
            current = index[current]["reports_to"]
    return out


def structure_defects(organization):
    """Return the structural defects that stop the chart being a single tree."""
    record = _as_organization(organization)
    defects = []
    roots = root_units(record)
    orphans = orphan_units(record)
    cycles = cyclic_units(record)
    if cycles:
        defects.append("reporting cycle through: %s" % ", ".join(sorted(cycles)))
    if orphans:
        defects.append("unit(s) reporting to an unheld parent: %s" % ", ".join(sorted(orphans)))
    if not cycles and not orphans:
        if len(roots) == 0:
            defects.append("the chart has no root unit")
        elif len(roots) > 1:
            defects.append("the chart has %d roots: %s" % (len(roots), ", ".join(sorted(roots))))
    return defects


def units_holding(organization, function):
    """Return the unit ids holding one quality or safety function."""
    record = _as_organization(organization)
    name = _require_token("function", function)
    if name not in RECOGNISED_FUNCTIONS:
        raise ValueError("unrecognised quality and safety function '%s'" % name)
    return [u["unit_id"] for u in record["units"] if name in u["functions"]]


def unassigned_functions(organization, required=REQUIRED_FUNCTIONS):
    """Return the required functions no unit holds."""
    record = _as_organization(organization)
    return [name for name in required if not units_holding(record, name)]


def shared_functions(organization, required=REQUIRED_FUNCTIONS):
    """Return (function, unit ids) for every required function held twice over."""
    record = _as_organization(organization)
    out = []
    for name in required:
        holders = units_holding(record, name)
        if len(holders) > 1:
            out.append((name, holders))
    return out


def independence_defects(organization):
    """Return the assurance units whose reporting chain runs through operations."""
    record = _as_organization(organization)
    operations = set(units_holding(record, FUNCTION_TEST_OPERATIONS))
    out = []
    for function in INDEPENDENT_FUNCTIONS:
        for holder in units_holding(record, function):
            chain = reporting_chain(record, holder)
            for ancestor in chain[1:]:
                if ancestor in operations:
                    out.append((function, holder, ancestor))
                    break
    return out


def dangling_interfaces(organization):
    """Return the declared interfaces naming a unit the chart does not hold."""
    record = _as_organization(organization)
    index = record["unit_index"]
    return [
        (left, right)
        for left, right in record["interfaces"]
        if left not in index or right not in index
    ]


def interface_gaps(organization, required=REQUIRED_INTERFACES):
    """Return the required function pairs with no declared interface behind them."""
    record = _as_organization(organization)
    declared = {tuple(sorted(pair)) for pair in record["interfaces"]}
    out = []
    for left_function, right_function in required:
        left_units = units_holding(record, left_function)
        right_units = units_holding(record, right_function)
        if not left_units or not right_units:
            continue
        joined = False
        for left in left_units:
            for right in right_units:
                if left == right:
                    joined = True
                elif tuple(sorted((left, right))) in declared:
                    joined = True
        if not joined:
            out.append((left_function, right_function))
    return out


def assess_organization(case):
    """Run the full clause 5.3.1 test-centre organization assessment.

    case keys: organization (the chart record) and optional required_functions
    and required_interfaces overrides.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "organization" not in case:
        raise ValueError("case missing required key 'organization'")
    required_functions = tuple(case.get("required_functions") or REQUIRED_FUNCTIONS)
    for name in required_functions:
        if name not in RECOGNISED_FUNCTIONS:
            raise ValueError("unrecognised required function '%s'" % name)
    required_interfaces = tuple(
        tuple(pair) for pair in (case.get("required_interfaces") or REQUIRED_INTERFACES)
    )
    record = validate_organization(case["organization"])

    findings = []
    advisories = []
    defects = structure_defects(record)

    if not record["defined"] or not record["units"]:
        verdict = ORGANIZATION_UNDEFINED
        findings.append("no test-centre organization has been defined")
        return {
            "verdict": verdict,
            "structure_defects": defects,
            "unassigned_functions": [],
            "shared_functions": [],
            "independence_defects": [],
            "dangling_interfaces": [],
            "interface_gaps": [],
            "findings": findings,
            "advisories": advisories,
        }

    if defects:
        return {
            "verdict": STRUCTURE_INVALID,
            "structure_defects": defects,
            "unassigned_functions": [],
            "shared_functions": [],
            "independence_defects": [],
            "dangling_interfaces": dangling_interfaces(record),
            "interface_gaps": [],
            "findings": ["the reporting structure is not a single tree: %s" % "; ".join(defects)],
            "advisories": advisories,
        }

    unassigned = unassigned_functions(record, required_functions)
    shared = shared_functions(record, required_functions)
    independence = independence_defects(record)
    dangling = dangling_interfaces(record)
    gaps = interface_gaps(record, required_interfaces)

    if unassigned:
        verdict = FUNCTION_MISSING
        findings.append(
            "%d required function(s) are held by no unit: %s"
            % (len(unassigned), ", ".join(unassigned))
        )
    elif independence:
        verdict = INDEPENDENCE_COMPROMISED
        findings.append(
            "%d assurance holder(s) report through the test-operations line: %s"
            % (
                len(independence),
                ", ".join("%s at %s via %s" % triple for triple in independence),
            )
        )
    elif gaps or dangling:
        verdict = INTERFACE_GAPS
        if gaps:
            findings.append(
                "%d required interface(s) are undeclared: %s"
                % (len(gaps), ", ".join("%s-%s" % pair for pair in gaps))
            )
        if dangling:
            findings.append(
                "%d declared interface(s) name a unit the chart does not hold: %s"
                % (len(dangling), ", ".join("%s-%s" % pair for pair in dangling))
            )
    else:
        verdict = ORGANIZATION_DEFINED

    if shared:
        advisories.append(
            "%d required function(s) are held by more than one unit: %s"
            % (len(shared), ", ".join("%s(%s)" % (name, "+".join(u)) for name, u in shared))
        )

    return {
        "verdict": verdict,
        "structure_defects": defects,
        "unassigned_functions": unassigned,
        "shared_functions": shared,
        "independence_defects": independence,
        "dangling_interfaces": dangling,
        "interface_gaps": gaps,
        "findings": findings,
        "advisories": advisories,
    }
