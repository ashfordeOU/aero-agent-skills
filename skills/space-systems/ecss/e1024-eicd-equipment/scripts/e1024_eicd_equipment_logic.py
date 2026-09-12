"""
ECSS-E-ST-10-24C §5.8.1 — Equipment-level EICD completeness logic.
Deterministic, offline, stdlib only.
"""

VALID_INTERFACE_TYPES = {"electrical", "mechanical", "thermal"}
VALID_SIGNAL_DIRECTIONS = {"in", "out", "bidir", "power", "return", "nc"}
REQUIRED_PIN_FIELDS = {"pin_id", "signal_name", "direction", "voltage_v", "current_ma"}
REQUIRED_MECHANICAL_FIELDS = {"attachment_pattern", "envelope_mm", "mass_kg"}
REQUIRED_THERMAL_FIELDS = {"dissipation_w", "temp_range_c", "theta_interface_k_w"}


def categorize_interface(interface):
    """Return the interface type string or raise ValueError for unknown types."""
    itype = interface.get("type", "").lower()
    if itype not in VALID_INTERFACE_TYPES:
        raise ValueError(
            f"Unknown interface type '{itype}'; "
            f"expected one of {sorted(VALID_INTERFACE_TYPES)}"
        )
    return itype


def validate_pin(pin):
    """Return a list of error strings for a single pin record."""
    errors = []
    pid = pin.get("pin_id", "?")
    for field in REQUIRED_PIN_FIELDS:
        if field not in pin or pin[field] is None:
            errors.append(f"pin '{pid}' missing field '{field}'")
    direction = str(pin.get("direction", "")).lower()
    if direction and direction not in VALID_SIGNAL_DIRECTIONS:
        errors.append(
            f"pin '{pid}' has unrecognized direction '{direction}'; "
            f"expected one of {sorted(VALID_SIGNAL_DIRECTIONS)}"
        )
    return errors


def check_pin_duplicate(pins):
    """Detect duplicate pin_id values within one connector's pin list."""
    seen = set()
    errors = []
    for pin in pins:
        pid = pin.get("pin_id")
        if pid in seen:
            errors.append(f"duplicate pin_id '{pid}' in connector")
        else:
            seen.add(pid)
    return errors


def validate_electrical_connector(connector):
    """Validate one electrical connector definition; return error list."""
    errors = []
    cid = connector.get("connector_id") or "?"
    if not connector.get("connector_id"):
        errors.append("electrical connector missing 'connector_id'")
    if not connector.get("connector_type"):
        errors.append(f"connector '{cid}' missing 'connector_type'")
    pins = connector.get("pins", [])
    if not pins:
        errors.append(f"connector '{cid}' has no pins defined")
    for pin in pins:
        errors.extend(validate_pin(pin))
    errors.extend(check_pin_duplicate(pins))
    return errors


def validate_mechanical_interface(mech):
    """Validate one mechanical interface definition; return error list."""
    errors = []
    iid = mech.get("iface_id", "?")
    for field in REQUIRED_MECHANICAL_FIELDS:
        if field not in mech or mech[field] is None:
            errors.append(f"mechanical interface '{iid}' missing field '{field}'")
    mass = mech.get("mass_kg")
    if mass is not None and mass < 0:
        errors.append(f"mechanical interface '{iid}' has negative mass_kg {mass}")
    return errors


def validate_thermal_interface(therm):
    """Validate one thermal interface definition; return error list."""
    errors = []
    iid = therm.get("iface_id", "?")
    for field in REQUIRED_THERMAL_FIELDS:
        if field not in therm or therm[field] is None:
            errors.append(f"thermal interface '{iid}' missing field '{field}'")
    dissipation = therm.get("dissipation_w")
    if dissipation is not None and dissipation < 0:
        errors.append(
            f"thermal interface '{iid}' has negative dissipation_w {dissipation}"
        )
    theta = therm.get("theta_interface_k_w")
    if theta is not None and theta < 0:
        errors.append(
            f"thermal interface '{iid}' has negative theta_interface_k_w {theta}"
        )
    return errors


def assess_equipment_eicd(equipment):
    """
    Top-level EICD completeness assessment for one equipment item.

    Expected input structure:
        {
            "equipment_id": str,
            "name": str,
            "interfaces": [
                {"type": "electrical", "connector_id": ..., "connector_type": ...,
                 "pins": [{"pin_id": ..., "signal_name": ..., "direction": ...,
                            "voltage_v": ..., "current_ma": ...}, ...]},
                {"type": "mechanical", "iface_id": ..., "attachment_pattern": ...,
                 "envelope_mm": ..., "mass_kg": ...},
                {"type": "thermal", "iface_id": ..., "dissipation_w": ...,
                 "temp_range_c": ..., "theta_interface_k_w": ...},
            ]
        }

    Returns:
        {"equipment_id": str, "findings": [str, ...], "compliant": bool}
    """
    if not equipment.get("equipment_id"):
        raise ValueError("equipment record missing 'equipment_id'")

    findings = []
    interfaces = equipment.get("interfaces", [])

    if not interfaces:
        findings.append("no interfaces defined for equipment")

    has_electrical = False
    has_mechanical = False
    has_thermal = False

    for iface in interfaces:
        itype = categorize_interface(iface)
        if itype == "electrical":
            has_electrical = True
            findings.extend(validate_electrical_connector(iface))
        elif itype == "mechanical":
            has_mechanical = True
            findings.extend(validate_mechanical_interface(iface))
        elif itype == "thermal":
            has_thermal = True
            findings.extend(validate_thermal_interface(iface))

    if not has_electrical:
        findings.append("EICD has no electrical interface defined")
    if not has_mechanical:
        findings.append("EICD has no mechanical interface defined")
    if not has_thermal:
        findings.append("EICD has no thermal interface defined")

    return {
        "equipment_id": equipment["equipment_id"],
        "findings": findings,
        "compliant": len(findings) == 0,
    }
