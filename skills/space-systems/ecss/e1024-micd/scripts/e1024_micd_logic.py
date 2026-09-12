#!/usr/bin/env python3
"""ECSS-E-ST-10-24C §5.11 MICD (mechanical interface control document)
production logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
interface management standard's §5.11 requires each mechanical interface
between system elements to be captured in a dedicated MICD that records
the interface identifier, the provider and receiver elements, the
interface type, the reference coordinate frame (which must be registered
in the project master frame list), a six-component load set (three
forces, three moments) at the interface plane, and basic mass properties
(mass and centre-of-gravity) of the provider-side hardware. The document
is not issued until every required data item is present, each load
component carries a numeric value, mass is non-negative, and the
coordinate frame appears in the registered list. This module implements
interface-type recognition, required-field completeness checking, load
and mass-property validation, coordinate-frame registration checking,
and open-item aggregation; it does not implement the broader ICD
hierarchy or the digital interface management database logic.
"""

INTERFACE_TYPES = frozenset({
    "structural",
    "kinematic",
    "thermal_mechanical",
    "electrical_mechanical",
    "fluid_mechanical",
    "optical_mechanical",
})

REQUIRED_MICD_FIELDS = (
    "interface_id",
    "provider_element",
    "receiver_element",
    "interface_type",
    "coordinate_frame_id",
    "interface_loads",
    "mass_properties",
)

REQUIRED_LOAD_COMPONENTS = ("Fx_N", "Fy_N", "Fz_N", "Mx_Nm", "My_Nm", "Mz_Nm")

REQUIRED_MASS_FIELDS = ("mass_kg", "cg_x_m", "cg_y_m", "cg_z_m")


def categorize_interface_type(interface_type):
    """Return interface_type if it is a known ECSS-E-ST-10-24C §5.11
    mechanical interface type. Raises ValueError for an unknown type."""
    if interface_type in INTERFACE_TYPES:
        return interface_type
    raise ValueError(
        "unrecognized mechanical interface type %r under "
        "E-ST-10-24C §5.11" % (interface_type,)
    )


def check_micd_completeness(micd):
    """Return a list of required field names absent from micd or set to
    None. An empty list means all required fields are present (completeness
    check only; does not validate field values). Does not mutate micd."""
    return [f for f in REQUIRED_MICD_FIELDS if f not in micd or micd[f] is None]


def validate_interface_loads(loads, interface_id):
    """Return a violation list for the six-component load set.
    loads: dict expected to contain Fx_N, Fy_N, Fz_N, Mx_Nm, My_Nm, Mz_Nm.
    Flags a missing component and a component whose value is not a real
    number. Does not mutate loads."""
    violations = []
    for component in REQUIRED_LOAD_COMPONENTS:
        if component not in loads:
            violations.append({
                "issue": "missing_load_component",
                "interface_id": interface_id,
                "component": component,
            })
        elif not isinstance(loads[component], (int, float)):
            violations.append({
                "issue": "non_numeric_load_component",
                "interface_id": interface_id,
                "component": component,
                "value": loads[component],
            })
    return violations


def validate_mass_properties(mass_props, interface_id):
    """Return a violation list for the mass-properties block.
    mass_props: dict expected to contain mass_kg, cg_x_m, cg_y_m, cg_z_m.
    Flags a missing field, a non-numeric value, and a negative mass_kg.
    Does not mutate mass_props."""
    violations = []
    for field in REQUIRED_MASS_FIELDS:
        if field not in mass_props:
            violations.append({
                "issue": "missing_mass_field",
                "interface_id": interface_id,
                "field": field,
            })
        elif not isinstance(mass_props[field], (int, float)):
            violations.append({
                "issue": "non_numeric_mass_field",
                "interface_id": interface_id,
                "field": field,
                "value": mass_props[field],
            })
        elif field == "mass_kg" and mass_props[field] < 0:
            violations.append({
                "issue": "negative_mass_kg",
                "interface_id": interface_id,
                "mass_kg": mass_props[field],
            })
    return violations


def validate_coordinate_frame(frame_id, registered_frames, interface_id):
    """Return a violation list (empty if compliant). A frame_id not found
    in registered_frames (an iterable of known frame identifiers) is flagged
    as an unregistered coordinate frame."""
    if frame_id not in registered_frames:
        return [{
            "issue": "unregistered_coordinate_frame",
            "interface_id": interface_id,
            "frame_id": frame_id,
        }]
    return []


def micd_open_items(micd, registered_frames):
    """Aggregate all open items for a single MICD.

    micd: dict with keys matching REQUIRED_MICD_FIELDS.
    registered_frames: iterable of known coordinate frame identifiers.

    Returns a list of finding dicts. An empty list means the MICD is
    ready for closure. Raises ValueError for an unrecognized
    interface_type when the field is present and non-null."""
    interface_id = micd.get("interface_id", "<unknown>")
    items = []

    missing = check_micd_completeness(micd)
    for field in missing:
        items.append({
            "issue": "missing_required_field",
            "interface_id": interface_id,
            "field": field,
        })

    if "interface_type" in micd and micd["interface_type"] is not None:
        categorize_interface_type(micd["interface_type"])

    if "interface_loads" in micd and micd["interface_loads"] is not None:
        items.extend(validate_interface_loads(micd["interface_loads"], interface_id))

    if "mass_properties" in micd and micd["mass_properties"] is not None:
        items.extend(validate_mass_properties(micd["mass_properties"], interface_id))

    if "coordinate_frame_id" in micd and micd["coordinate_frame_id"] is not None:
        items.extend(
            validate_coordinate_frame(micd["coordinate_frame_id"], registered_frames, interface_id)
        )

    return items


def is_micd_closed(open_items):
    """True when open_items is empty — the MICD has no outstanding findings
    and is ready for formal issue under E-ST-10-24C §5.11."""
    return len(open_items) == 0
