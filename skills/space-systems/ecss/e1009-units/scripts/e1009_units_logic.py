"""
ECSS-E-ST-10-09C §5.4.3 — Unit assignment checker.

Each coordinate or derived quantity must carry its SI standard unit or
an explicitly listed stated exception. This module implements the lookup
table and verdict logic; no external dependencies required.
"""

# Unit table: quantity_type -> {si, stated_exceptions, description}
# SI units are the base or coherent derived SI unit for each quantity.
# Stated exceptions are units explicitly permitted by §5.4.3 or the
# standard's accompanying exception table.
UNIT_TABLE = {
    "distance": {
        "si": "m",
        "stated_exceptions": {"km"},
        "description": "Linear position or distance",
    },
    "angle": {
        "si": "rad",
        "stated_exceptions": {"deg", "arcmin", "arcsec"},
        "description": "Plane angle",
    },
    "time": {
        "si": "s",
        "stated_exceptions": {"min", "h", "day", "yr", "JD", "MJD"},
        "description": "Time interval or epoch",
    },
    "angular_rate": {
        "si": "rad/s",
        "stated_exceptions": {"deg/s", "rpm", "deg/h"},
        "description": "Angular velocity",
    },
    "velocity": {
        "si": "m/s",
        "stated_exceptions": {"km/s"},
        "description": "Linear velocity",
    },
    "mass": {
        "si": "kg",
        "stated_exceptions": {"g"},
        "description": "Mass",
    },
    "force": {
        "si": "N",
        "stated_exceptions": set(),
        "description": "Force",
    },
    "pressure": {
        "si": "Pa",
        "stated_exceptions": {"kPa", "MPa"},
        "description": "Pressure",
    },
    "temperature": {
        "si": "K",
        "stated_exceptions": {"degC"},
        "description": "Temperature",
    },
    "frequency": {
        "si": "Hz",
        "stated_exceptions": {"kHz", "MHz", "GHz"},
        "description": "Frequency",
    },
    "acceleration": {
        "si": "m/s2",
        "stated_exceptions": {"km/s2"},
        "description": "Linear acceleration",
    },
}


class UnitStatus:
    SI = "si"
    STATED_EXCEPTION = "stated_exception"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN_QUANTITY = "unknown_quantity"


def check_unit(quantity_type, unit):
    """
    Return a verdict dict for one (quantity_type, unit) pair.

    Keys: status, quantity_type, unit, expected_si, stated_exceptions, message.
    Raises ValueError for empty inputs.
    """
    if not quantity_type or not isinstance(quantity_type, str):
        raise ValueError("quantity_type must be a non-empty string")
    if not unit or not isinstance(unit, str):
        raise ValueError("unit must be a non-empty string")

    entry = UNIT_TABLE.get(quantity_type)
    if entry is None:
        return {
            "status": UnitStatus.UNKNOWN_QUANTITY,
            "quantity_type": quantity_type,
            "unit": unit,
            "expected_si": None,
            "stated_exceptions": [],
            "message": (
                f"Quantity type '{quantity_type}' is not in the unit table; "
                "resolve the type before accepting the parameter."
            ),
        }

    si_unit = entry["si"]
    exceptions = entry["stated_exceptions"]

    if unit == si_unit:
        return {
            "status": UnitStatus.SI,
            "quantity_type": quantity_type,
            "unit": unit,
            "expected_si": si_unit,
            "stated_exceptions": sorted(exceptions),
            "message": f"'{unit}' is the SI unit for {quantity_type}.",
        }

    if unit in exceptions:
        return {
            "status": UnitStatus.STATED_EXCEPTION,
            "quantity_type": quantity_type,
            "unit": unit,
            "expected_si": si_unit,
            "stated_exceptions": sorted(exceptions),
            "message": (
                f"'{unit}' is a stated exception for {quantity_type} "
                f"(SI: {si_unit})."
            ),
        }

    return {
        "status": UnitStatus.NON_COMPLIANT,
        "quantity_type": quantity_type,
        "unit": unit,
        "expected_si": si_unit,
        "stated_exceptions": sorted(exceptions),
        "message": (
            f"'{unit}' is non-compliant for {quantity_type}. "
            f"Use SI unit '{si_unit}' or a stated exception: "
            f"{sorted(exceptions)}."
        ),
    }


def is_compliant(quantity_type, unit):
    """Return True when unit is SI or a stated exception for quantity_type."""
    result = check_unit(quantity_type, unit)
    return result["status"] in (UnitStatus.SI, UnitStatus.STATED_EXCEPTION)


def get_si_unit(quantity_type):
    """Return the SI unit string for quantity_type. Raises KeyError if unknown."""
    entry = UNIT_TABLE.get(quantity_type)
    if entry is None:
        raise KeyError(f"Unknown quantity type: '{quantity_type}'")
    return entry["si"]


def get_stated_exceptions(quantity_type):
    """Return the set of stated exceptions for quantity_type. Raises KeyError if unknown."""
    entry = UNIT_TABLE.get(quantity_type)
    if entry is None:
        raise KeyError(f"Unknown quantity type: '{quantity_type}'")
    return set(entry["stated_exceptions"])


def validate_parameter_list(params):
    """
    Validate a list of parameter dicts, each with 'quantity_type' and 'unit' keys.

    Returns a summary dict:
      total, counts (by status), findings (list of check_unit results),
      all_compliant (True when non_compliant and unknown_quantity counts are 0).
    """
    if not isinstance(params, list):
        raise ValueError("params must be a list")

    counts = {
        UnitStatus.SI: 0,
        UnitStatus.STATED_EXCEPTION: 0,
        UnitStatus.NON_COMPLIANT: 0,
        UnitStatus.UNKNOWN_QUANTITY: 0,
    }
    findings = []

    for i, p in enumerate(params):
        if not isinstance(p, dict) or "quantity_type" not in p or "unit" not in p:
            raise ValueError(
                f"Entry {i} must be a dict with 'quantity_type' and 'unit' keys"
            )
        result = check_unit(p["quantity_type"], p["unit"])
        findings.append(result)
        counts[result["status"]] += 1

    return {
        "total": len(params),
        "counts": counts,
        "findings": findings,
        "all_compliant": (
            counts[UnitStatus.NON_COMPLIANT] == 0
            and counts[UnitStatus.UNKNOWN_QUANTITY] == 0
        ),
    }


def list_supported_quantities():
    """Return a sorted list of all quantity types in the unit table."""
    return sorted(UNIT_TABLE.keys())
