#!/usr/bin/env python3
"""Photovoltaic assembly scope logic (ECSS-E-ST-20-08C, 5.1.1).

Offline, deterministic, standard-library only. The module fixes what the
photovoltaic assembly covers and which array configurations the clause
speaks to:

* placement of each declared element inside, on, or outside the boundary,
* the boundary of supply a declaration has to name for itself,
* derivation of the array configuration family from its attributes,
* whether that family is one the clause addresses,
* the provisions a family pulls in beyond the common ones,
* per-declaration and multi-wing acceptance of the scope statement.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "ELEMENT_PLACEMENT",
    "PLACEMENTS",
    "MOUNTINGS",
    "SUBSTRATE_TYPES",
    "DEPLOYMENT_KINEMATICS",
    "CONFIGURATION_FAMILIES",
    "ADDRESSED_FAMILIES",
    "FAMILY_EXCLUDED_ELEMENTS",
    "COMMON_PROVISIONS",
    "FAMILY_PROVISIONS",
    "FLAT_PLATE_CONCENTRATION_RATIO",
    "element_placement",
    "boundary_of_supply",
    "configuration_family",
    "addressed_provisions",
    "evaluate_assembly_declaration",
    "assess_array_scope",
]

# Absorbs binary-representation error when a declared ratio lands a few ULPs
# off an exactly-flat one. It never shifts the threshold itself.
REL_TOL = 1e-9

PLACEMENTS = ("inside", "boundary", "outside")

# Where each array element sits relative to the photovoltaic assembly. An
# element "inside" is supplied and verified as part of the assembly; one on
# the "boundary" is the interface at which the assembly stops; one "outside"
# belongs to the mechanism, the power chain or the spacecraft.
ELEMENT_PLACEMENT = {
    "solar-cell": ("inside", "the converting element the assembly exists for"),
    "coverglass": ("inside", "protects the cell and is bonded to it"),
    "coverglass-adhesive": ("inside", "forms the cell-to-coverglass joint"),
    "cell-interconnect": ("inside", "carries current between adjacent cells"),
    "cell-to-substrate-adhesive": ("inside", "bonds the cell stack to the substrate"),
    "bus-bar": ("inside", "collects the string current on the panel"),
    "string-wiring": ("inside", "routes string current to the array connector"),
    "bypass-diode": ("inside", "protects a shadowed cell within the string"),
    "substrate-facesheet": ("inside", "carries the cell field"),
    "substrate-core": ("inside", "gives the substrate its bending stiffness"),
    "insulation-layer": ("inside", "separates the cell circuit from the substrate"),
    "array-connector": ("boundary", "the electrical end of the assembly"),
    "panel-mounting-interface": ("boundary", "the mechanical end of the assembly"),
    "temperature-sensor-interface": ("boundary", "the instrumentation end of the assembly"),
    "deployment-hinge": ("outside", "belongs to the deployment mechanism"),
    "hold-down-release": ("outside", "belongs to the deployment mechanism"),
    "yoke": ("outside", "belongs to the array structure, not the assembly"),
    "solar-array-drive-mechanism": ("outside", "belongs to the pointing chain"),
    "power-conditioning-unit": ("outside", "belongs to the power subsystem"),
    "spacecraft-harness": ("outside", "starts where the array connector ends"),
    "sun-sensor": ("outside", "belongs to the attitude chain"),
}

MOUNTINGS = ("body-mounted", "panel", "drum")

SUBSTRATE_TYPES = ("rigid", "flexible")

DEPLOYMENT_KINEMATICS = ("fold-out", "roll-out", "tension-deployed")

CONFIGURATION_FAMILIES = (
    "body-mounted",
    "spinner-drum",
    "rigid-deployable-panel",
    "flexible-deployable-blanket",
    "concentrator",
)

# The clause speaks to the flat-plate families, whose cells see the solar
# constant directly. A concentrating array is derived here so that it can be
# recognised and handed over with its optics provisions named, but it is not
# a family this clause itself addresses.
ADDRESSED_FAMILIES = (
    "body-mounted",
    "spinner-drum",
    "rigid-deployable-panel",
    "flexible-deployable-blanket",
)

# Elements a family cannot contain: a tensioned blanket has no stiff core to
# bend, so a core declared on one is a contradiction between the attribute
# set and the element list.
FAMILY_EXCLUDED_ELEMENTS = {
    "body-mounted": (),
    "spinner-drum": (),
    "rigid-deployable-panel": (),
    "flexible-deployable-blanket": ("substrate-core",),
    "concentrator": (),
}

# A ratio at or below this value is a flat-plate array; above it the array
# concentrates and the optics come with their own provisions.
FLAT_PLATE_CONCENTRATION_RATIO = 1.0

COMMON_PROVISIONS = (
    "cell-and-coverglass-assembly",
    "interconnect-and-string-layout",
    "substrate-insulation",
    "array-electrical-performance",
)

FAMILY_PROVISIONS = {
    "body-mounted": ("spacecraft-structure-thermal-coupling",),
    "spinner-drum": ("spin-modulated-illumination",),
    "rigid-deployable-panel": ("deployment-induced-loading",),
    "flexible-deployable-blanket": (
        "deployment-induced-loading",
        "blanket-tensioning-and-stowage",
    ),
    "concentrator": (
        "concentrator-optics-alignment",
        "off-pointing-thermal-margin",
    ),
}

_ATTRIBUTE_KEYS = (
    "mounting",
    "substrate",
    "deployable",
    "deployment_kinematics",
    "concentration_ratio",
)

_DECLARATION_KEYS = ("id", "elements", "attributes", "declared_provisions")


def _finding(code, subject, detail):
    """Build one scope finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _above(value, threshold):
    """Strictly-above comparison that does not fire on representation error."""
    return value > threshold and not math.isclose(
        value, threshold, rel_tol=REL_TOL, abs_tol=0.0
    )


def _require_known(value, allowed, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-blank string" % label)
    token = value.strip()
    if token not in allowed:
        raise ValueError(
            "%s is %r, expected one of %s" % (label, token, ", ".join(sorted(allowed)))
        )
    return token


def element_placement(element):
    """Place one named array element relative to the assembly boundary."""
    name = _require_known(element, tuple(ELEMENT_PLACEMENT), "element")
    placement, rationale = ELEMENT_PLACEMENT[name]
    return {"element": name, "placement": placement, "rationale": rationale}


def boundary_of_supply(elements):
    """Group a declared element list into inside, boundary and outside sets."""
    if isinstance(elements, (str, bytes)) or not hasattr(elements, "__iter__"):
        raise ValueError("elements must be an iterable of element names")
    placed = [element_placement(element) for element in elements]
    if not placed:
        raise ValueError("an assembly declaration must name at least one element")
    seen = set()
    for record in placed:
        if record["element"] in seen:
            raise ValueError("element %r is declared twice" % record["element"])
        seen.add(record["element"])
    grouped = {placement: [] for placement in PLACEMENTS}
    for record in placed:
        grouped[record["placement"]].append(record["element"])
    return {
        "elements": placed,
        "inside": tuple(grouped["inside"]),
        "boundary": tuple(grouped["boundary"]),
        "outside": tuple(grouped["outside"]),
        "bounded": bool(grouped["boundary"]),
        "converting_element_present": "solar-cell" in seen,
    }


def configuration_family(attributes):
    """Derive the array configuration family from its declared attributes."""
    if not isinstance(attributes, dict):
        raise ValueError(
            "attributes must be a mapping, got %s" % type(attributes).__name__
        )
    unknown = [key for key in attributes if key not in _ATTRIBUTE_KEYS]
    if unknown:
        raise ValueError(
            "attributes carry unknown key(s): %s" % ", ".join(sorted(unknown))
        )
    for key in ("mounting", "substrate", "deployable"):
        if key not in attributes:
            raise ValueError("attributes are missing required key %r" % key)
    mounting = _require_known(attributes["mounting"], MOUNTINGS, "mounting")
    substrate = _require_known(attributes["substrate"], SUBSTRATE_TYPES, "substrate")
    deployable = attributes["deployable"]
    if not isinstance(deployable, bool):
        raise ValueError(
            "deployable must be true or false, got %s" % type(deployable).__name__
        )
    kinematics = attributes.get("deployment_kinematics")
    if deployable:
        if kinematics is None:
            raise ValueError("a deployable array must state its deployment kinematics")
        kinematics = _require_known(
            kinematics, DEPLOYMENT_KINEMATICS, "deployment_kinematics"
        )
    elif kinematics is not None:
        raise ValueError(
            "a non-deployable array cannot state deployment kinematics (%r)"
            % (kinematics,)
        )
    ratio = _as_float(
        attributes.get("concentration_ratio", FLAT_PLATE_CONCENTRATION_RATIO),
        "concentration_ratio",
    )
    if ratio < FLAT_PLATE_CONCENTRATION_RATIO and not math.isclose(
        ratio, FLAT_PLATE_CONCENTRATION_RATIO, rel_tol=REL_TOL, abs_tol=0.0
    ):
        raise ValueError(
            "concentration_ratio must be at least %r, got %r"
            % (FLAT_PLATE_CONCENTRATION_RATIO, attributes.get("concentration_ratio"))
        )
    concentrating = _above(ratio, FLAT_PLATE_CONCENTRATION_RATIO)
    if substrate == "flexible" and not deployable:
        raise ValueError(
            "a flexible substrate has to be deployed and tensioned to carry cells"
        )
    if substrate == "flexible" and mounting != "panel":
        raise ValueError(
            "a flexible blanket is carried on a panel wing, not %r" % (mounting,)
        )
    if deployable and mounting == "body-mounted":
        raise ValueError("a body-mounted array does not deploy")

    if concentrating:
        family = "concentrator"
        rationale = "concentrates sunlight by a ratio of %.4g" % ratio
    elif substrate == "flexible":
        family = "flexible-deployable-blanket"
        rationale = "flexible blanket deployed by %s kinematics" % kinematics
    elif deployable:
        family = "rigid-deployable-panel"
        rationale = "rigid panel deployed by %s kinematics" % kinematics
    elif mounting == "drum":
        family = "spinner-drum"
        rationale = "cells wrapped on a spinning drum"
    else:
        family = "body-mounted"
        rationale = "cells mounted directly on the spacecraft body"
    return {
        "family": family,
        "rationale": rationale,
        "mounting": mounting,
        "substrate": substrate,
        "deployable": deployable,
        "deployment_kinematics": kinematics,
        "concentration_ratio": ratio,
        "concentrating": concentrating,
        "addressed": family in ADDRESSED_FAMILIES,
    }


def addressed_provisions(family):
    """List the provisions the clause hands to this configuration family."""
    name = _require_known(family, CONFIGURATION_FAMILIES, "family")
    return tuple(COMMON_PROVISIONS) + tuple(FAMILY_PROVISIONS[name])


def evaluate_assembly_declaration(declaration):
    """Evaluate one array wing's scope declaration against the clause."""
    if not isinstance(declaration, dict):
        raise ValueError(
            "declaration must be a mapping, got %s" % type(declaration).__name__
        )
    unknown = [key for key in declaration if key not in _DECLARATION_KEYS]
    if unknown:
        raise ValueError(
            "declaration carries unknown key(s): %s" % ", ".join(sorted(unknown))
        )
    for key in ("id", "elements", "attributes"):
        if key not in declaration:
            raise ValueError("declaration is missing required key %r" % key)
    if not isinstance(declaration["id"], str) or not declaration["id"].strip():
        raise ValueError("declaration id must be a non-blank string")
    identifier = declaration["id"].strip()

    boundary = boundary_of_supply(declaration["elements"])
    configuration = configuration_family(declaration["attributes"])
    provisions = addressed_provisions(configuration["family"])
    findings = []

    if not boundary["bounded"]:
        findings.append(
            _finding(
                "assembly-boundary-undeclared",
                identifier,
                "names no element at which the assembly stops, so its extent "
                "cannot be read from the declaration",
            )
        )
    if not boundary["converting_element_present"]:
        findings.append(
            _finding(
                "converting-element-absent",
                identifier,
                "names no solar cell, so the declaration is not a photovoltaic "
                "assembly",
            )
        )
    if boundary["outside"]:
        findings.append(
            _finding(
                "element-outside-the-assembly",
                identifier,
                "claims %s, which belong to the mechanism, the power chain or "
                "the spacecraft" % ", ".join(boundary["outside"]),
            )
        )
    if not configuration["addressed"]:
        findings.append(
            _finding(
                "configuration-not-addressed",
                identifier,
                "is a %s array, which this clause recognises but hands over "
                "with the provisions %s"
                % (
                    configuration["family"],
                    ", ".join(FAMILY_PROVISIONS[configuration["family"]]),
                ),
            )
        )
    excluded = tuple(
        element
        for element in FAMILY_EXCLUDED_ELEMENTS[configuration["family"]]
        if element in boundary["inside"]
    )
    if excluded:
        findings.append(
            _finding(
                "element-inconsistent-with-configuration",
                identifier,
                "declares %s, which a %s array does not carry"
                % (", ".join(excluded), configuration["family"]),
            )
        )

    declared = declaration.get("declared_provisions")
    uncovered = ()
    if declared is not None:
        if isinstance(declared, (str, bytes)) or not hasattr(declared, "__iter__"):
            raise ValueError("declared_provisions must be an iterable of names")
        stated = tuple(declared)
        for item in stated:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("each declared provision must be a non-blank string")
        stated_set = {item.strip() for item in stated}
        uncovered = tuple(item for item in provisions if item not in stated_set)
        if uncovered:
            findings.append(
                _finding(
                    "provision-not-covered",
                    identifier,
                    "does not carry %s, which its configuration pulls in"
                    % ", ".join(uncovered),
                )
            )

    return {
        "id": identifier,
        "boundary": boundary,
        "configuration": configuration,
        "applicable_provisions": provisions,
        "uncovered_provisions": uncovered,
        "findings": findings,
        "in_scope": configuration["addressed"] and not findings,
    }


def assess_array_scope(declarations):
    """Assess every wing declaration of an array against the clause scope."""
    if isinstance(declarations, (str, bytes)) or not hasattr(
        declarations, "__iter__"
    ):
        raise ValueError("declarations must be an iterable of wing declarations")
    evaluated = [evaluate_assembly_declaration(item) for item in declarations]
    if not evaluated:
        raise ValueError("an array must carry at least one wing declaration")
    seen = set()
    for record in evaluated:
        if record["id"] in seen:
            raise ValueError("wing declaration %r appears twice" % record["id"])
        seen.add(record["id"])
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])
    families = sorted({record["configuration"]["family"] for record in evaluated})
    accepted = not findings
    return {
        "verdict": "scope-consistent" if accepted else "scope-inconsistent",
        "accepted": accepted,
        "findings": findings,
        "declarations": evaluated,
        "declaration_count": len(evaluated),
        "families": tuple(families),
        "mixed_configuration": len(families) > 1,
        "in_scope_fraction": sum(1 for record in evaluated if record["in_scope"])
        / float(len(evaluated)),
    }
