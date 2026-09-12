#!/usr/bin/env python3
"""ECSS-E-ST-32C Annex A — CAD model and drawing description delivery
validation (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structures standard's Annex A specifies the mandatory content elements for
a CAD Model and Drawing Description Document (CADMDD): model format
declaration (exchange or native), coordinate system definition (origin, axes,
handedness), assembly tree with unique component IDs, drawing title block
(document number, title, revision, release date, originator, approval
authority), mass properties (mass, centre of gravity, inertia tensor
diagonal), delivery maturity level, and interface definitions (ID, type,
mating component). This module implements format validation, coordinate
system checking, model tree completeness, title block field checking, mass
property validation, maturity level recognition, and interface definition
checking; it does not reproduce the normative content of ECSS-E-ST-32C.
"""

ACCEPTED_MODEL_FORMATS = frozenset({
    "step_ap214",
    "step_ap242",
    "iges",
    "catia_v5",
    "catia_v6",
    "siemens_nx",
    "creo",
    "solidworks",
})

TITLE_BLOCK_REQUIRED_FIELDS = frozenset({
    "document_number",
    "title",
    "revision",
    "release_date",
    "originator",
    "approval_authority",
})

VALID_MATURITY_LEVELS = frozenset({
    "preliminary",
    "development",
    "released",
    "superseded",
})

VALID_INTERFACE_TYPES = frozenset({
    "mechanical",
    "thermal",
    "electrical",
    "optical",
    "fluid",
})

VALID_HANDEDNESS = frozenset({"right", "left"})

COORDINATE_SYSTEM_REQUIRED_FIELDS = frozenset({
    "origin",
    "x_axis",
    "y_axis",
    "handedness",
})

MASS_PROPERTY_FIELDS = (
    "mass_kg",
    "cog_x_m",
    "cog_y_m",
    "cog_z_m",
    "ixx_kg_m2",
    "iyy_kg_m2",
    "izz_kg_m2",
)

NON_NEGATIVE_MASS_FIELDS = frozenset({
    "mass_kg",
    "ixx_kg_m2",
    "iyy_kg_m2",
    "izz_kg_m2",
})


def validate_model_format(fmt):
    """Confirm fmt is an accepted exchange or native CAD format.

    Returns "accepted" when recognised. Raises ValueError for any
    format string not in ACCEPTED_MODEL_FORMATS."""
    if fmt not in ACCEPTED_MODEL_FORMATS:
        raise ValueError(
            "unrecognised model format %r; accepted formats: %s"
            % (fmt, ", ".join(sorted(ACCEPTED_MODEL_FORMATS)))
        )
    return "accepted"


def validate_coordinate_system(cs):
    """Check a coordinate system dict for required fields and valid handedness.

    cs: dict expected to contain origin, x_axis, y_axis, handedness.
    Returns a list of finding dicts (empty when fully valid). Does not
    mutate cs."""
    findings = []
    for field in sorted(COORDINATE_SYSTEM_REQUIRED_FIELDS):
        if field not in cs:
            findings.append({"issue": "missing_coordinate_system_field", "field": field})
    if "handedness" in cs and cs["handedness"] not in VALID_HANDEDNESS:
        findings.append({
            "issue": "invalid_handedness_value",
            "value": cs["handedness"],
            "accepted": sorted(VALID_HANDEDNESS),
        })
    return findings


def validate_title_block(tb):
    """Check a drawing title block dict for all required fields.

    tb: dict expected to contain the fields in TITLE_BLOCK_REQUIRED_FIELDS.
    Returns a list of finding dicts (empty when complete). Does not mutate tb."""
    findings = []
    for field in sorted(TITLE_BLOCK_REQUIRED_FIELDS):
        if not tb.get(field):
            findings.append({"issue": "missing_title_block_field", "field": field})
    return findings


def validate_mass_properties(mp):
    """Check a mass properties dict for completeness and non-negative constraints.

    mp: dict expected to contain all fields in MASS_PROPERTY_FIELDS.
    Returns a list of finding dicts (empty when valid). Does not mutate mp."""
    findings = []
    for field in MASS_PROPERTY_FIELDS:
        if field not in mp:
            findings.append({"issue": "missing_mass_property_field", "field": field})
        elif field in NON_NEGATIVE_MASS_FIELDS and mp[field] < 0:
            findings.append({
                "issue": "negative_mass_property_value",
                "field": field,
                "value": mp[field],
            })
    return findings


def validate_maturity_level(level):
    """Confirm level is a recognised CADMDD maturity code.

    Returns the level string when recognised. Raises ValueError for any
    value not in VALID_MATURITY_LEVELS."""
    if level not in VALID_MATURITY_LEVELS:
        raise ValueError(
            "unrecognised maturity level %r; accepted levels: %s"
            % (level, ", ".join(sorted(VALID_MATURITY_LEVELS)))
        )
    return level


def validate_interface_definition(iface):
    """Check one interface definition dict for required fields and type validity.

    iface: dict expected to contain interface_id, interface_type, and
    mating_component. Returns a list of finding dicts (empty when valid).
    Does not mutate iface."""
    findings = []
    for field in ("interface_id", "interface_type", "mating_component"):
        if not iface.get(field):
            findings.append({"issue": "missing_interface_field", "field": field})
    if iface.get("interface_type") and iface["interface_type"] not in VALID_INTERFACE_TYPES:
        findings.append({
            "issue": "invalid_interface_type",
            "value": iface["interface_type"],
            "accepted": sorted(VALID_INTERFACE_TYPES),
        })
    return findings


def validate_model_tree(components):
    """Check the assembly tree component list for missing IDs and duplicate IDs.

    components: iterable of dicts; each must contain a non-empty "id" field.
    Returns a list of finding dicts (empty when complete). Does not mutate
    components."""
    findings = []
    seen_ids = {}
    for index, comp in enumerate(components):
        comp_id = comp.get("id")
        if not comp_id:
            findings.append({"issue": "component_missing_id", "index": index})
        else:
            if comp_id in seen_ids:
                findings.append({
                    "issue": "duplicate_component_id",
                    "id": comp_id,
                    "first_index": seen_ids[comp_id],
                    "duplicate_index": index,
                })
            else:
                seen_ids[comp_id] = index
    return findings


def cad_delivery_review(record):
    """Aggregate CADMDD delivery review for one delivery record.

    record: {
        "model_format": str,
        "coordinate_system": dict,
        "title_block": dict,
        "mass_properties": dict,
        "maturity_level": str,
        "interfaces": list of dicts,
        "model_tree_components": list of dicts,
    }

    Returns a findings dict keyed by category; each value is a list of
    finding dicts (empty list means that category is compliant). Raises
    ValueError for an unrecognised model_format or maturity_level."""
    validate_model_format(record["model_format"])
    validate_maturity_level(record["maturity_level"])

    interface_findings = []
    for iface in record.get("interfaces", []):
        interface_findings.extend(validate_interface_definition(iface))

    return {
        "coordinate_system": validate_coordinate_system(
            record.get("coordinate_system", {})
        ),
        "title_block": validate_title_block(record.get("title_block", {})),
        "mass_properties": validate_mass_properties(record.get("mass_properties", {})),
        "interfaces": interface_findings,
        "model_tree": validate_model_tree(record.get("model_tree_components", [])),
    }


def is_delivery_compliant(review):
    """True when every category in a cad_delivery_review result is empty —
    the CADMDD delivery satisfies all Annex A content requirements."""
    return all(len(findings) == 0 for findings in review.values())
