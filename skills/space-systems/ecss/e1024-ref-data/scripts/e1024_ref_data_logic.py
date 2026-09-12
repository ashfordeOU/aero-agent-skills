"""
ECSS-E-ST-10-24C Annex E — Interface reference data logic.
Reference: ECSS-E-ST-10-24C, Annex E (informative).

Determines whether an interface parameter record is complete and consistent:
validates interface type, checks unit membership for the type, checks format
token vocabulary, and flags missing or blank required fields.
"""

INTERFACE_TYPES = frozenset({
    "electrical",
    "mechanical",
    "thermal",
    "data",
    "rf",
    "optical",
    "fluid",
    "pyrotechnic",
})

# Accepted measurement units per interface type.
UNITS_BY_TYPE = {
    "electrical": frozenset({"V", "mV", "A", "mA", "W", "mW", "Ohm", "Hz", "kHz", "MHz", "-"}),
    "mechanical": frozenset({"kg", "g", "mm", "m", "N", "Nm", "MPa", "Hz", "deg", "-"}),
    "thermal":    frozenset({"K", "degC", "W", "W/m2", "W/mK", "-"}),
    "data":       frozenset({"bps", "kbps", "Mbps", "B", "kB", "MB", "ms", "us", "-"}),
    "rf":         frozenset({"dBm", "dBW", "MHz", "GHz", "dB", "deg", "-"}),
    "optical":    frozenset({"nm", "um", "m", "deg", "sr", "W/m2", "-"}),
    "fluid":      frozenset({"Pa", "kPa", "MPa", "kg/s", "l/s", "degC", "K", "-"}),
    "pyrotechnic": frozenset({"A", "mA", "ms", "V", "W", "-"}),
}

# Accepted format-token prefixes.
VALID_FORMAT_PREFIXES = frozenset({"float", "int", "enum", "string", "bool", "hex", "binary"})

# All fields that must be present and non-blank in a raw parameter dict.
REQUIRED_FIELDS = frozenset({"interface_type", "parameter_name", "unit", "format", "value_range"})


class InterfaceParamRecord:
    """One row in the interface reference data list."""

    def __init__(self, interface_type, parameter_name, unit, fmt, value_range):
        self.interface_type = interface_type.lower().strip()
        self.parameter_name = parameter_name.strip()
        self.unit = unit.strip()
        self.fmt = fmt.strip().lower()
        self.value_range = value_range.strip()

    def __repr__(self):
        return (
            f"InterfaceParamRecord(type={self.interface_type!r}, "
            f"name={self.parameter_name!r}, unit={self.unit!r})"
        )


def validate_record(record):
    """
    Validate one InterfaceParamRecord.

    Returns a list of finding strings describing every problem found.
    An empty list means the record is compliant.  All findings are
    collected before returning — callers get a complete view per record.
    """
    findings = []

    if record.interface_type not in INTERFACE_TYPES:
        findings.append(
            f"Unknown interface type '{record.interface_type}'. "
            f"Accepted: {sorted(INTERFACE_TYPES)}"
        )
        # Cannot check unit or format without a valid type; stop here.
        return findings

    if not record.parameter_name:
        findings.append("parameter_name is blank.")

    accepted_units = UNITS_BY_TYPE[record.interface_type]
    if record.unit not in accepted_units:
        findings.append(
            f"Unit '{record.unit}' not in accepted set for "
            f"'{record.interface_type}': {sorted(accepted_units)}"
        )

    if not any(record.fmt.startswith(prefix) for prefix in VALID_FORMAT_PREFIXES):
        findings.append(
            f"Format token '{record.fmt}' not recognised. "
            f"Must start with one of: {sorted(VALID_FORMAT_PREFIXES)}"
        )

    if not record.value_range:
        findings.append("value_range is blank.")

    return findings


def missing_required_fields(raw_dict):
    """
    Return a list of field names that are absent or blank in raw_dict.

    Checks against REQUIRED_FIELDS; a field present with only whitespace
    counts as missing.
    """
    return [
        field for field in REQUIRED_FIELDS
        if field not in raw_dict or not str(raw_dict[field]).strip()
    ]


def build_reference_table(records):
    """
    Group InterfaceParamRecord objects by interface_type.

    Records whose type is not in INTERFACE_TYPES are stored under the
    key "INVALID" so callers can inspect and resolve them separately.

    Returns a dict mapping type keys to lists of records.
    """
    table = {}
    for rec in records:
        key = rec.interface_type if rec.interface_type in INTERFACE_TYPES else "INVALID"
        table.setdefault(key, []).append(rec)
    return table


def summarize_table(table):
    """
    Return a dict mapping each key in table to the count of its records.
    """
    return {key: len(recs) for key, recs in table.items()}
