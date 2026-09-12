#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.6.1 -- battery provision applicability.

Deterministic, offline, standard-library-only helpers that decide whether
the battery provisions of the electrical engineering standard reach a given
on-board energy store, resolve the declared cell assembly into terminal
voltage / capacity / stored energy, and reconcile the derived reach against
the reach the electrical architecture declared.

The procedure is a paraphrase of the clause intent; no standard text is
reproduced. The clause is cited as the anchor only.
"""

# Per-cell nominal voltage (V) of recognized rechargeable chemistries.
SECONDARY_CELL_NOMINAL_V = {
    "lithium-ion": 3.60,
    "lithium-ion-polymer": 3.70,
    "lithium-iron-phosphate": 3.20,
    "nickel-cadmium": 1.20,
    "nickel-hydrogen": 1.25,
    "nickel-metal-hydride": 1.20,
    "silver-zinc-rechargeable": 1.50,
}

# Per-cell nominal voltage (V) of recognized single-discharge chemistries.
PRIMARY_CELL_NOMINAL_V = {
    "lithium-thionyl-chloride": 3.60,
    "lithium-sulphur-dioxide": 2.90,
    "lithium-manganese-dioxide": 3.00,
    "silver-zinc-primary": 1.55,
    "thermal-reserve": 2.00,
}

# Electrochemical, but reactants are supplied from outside the cell.
CONVERTER_SOURCES = frozenset(
    {"fuel-cell-pem", "fuel-cell-alkaline", "regenerative-fuel-cell"}
)

# Electrical energy stores that are not electrochemical at all.
NON_ELECTROCHEMICAL_SOURCES = frozenset(
    {
        "supercapacitor",
        "capacitor-bank",
        "flywheel",
        "solar-array",
        "radioisotope-thermoelectric-generator",
    }
)

CATEGORY_SECONDARY = "secondary-battery"
CATEGORY_PRIMARY = "primary-battery"
CATEGORY_CONVERTER = "electrochemical-converter"
CATEGORY_NON_ELECTROCHEMICAL = "non-electrochemical-store"

IN_SCOPE_CATEGORIES = frozenset({CATEGORY_SECONDARY, CATEGORY_PRIMARY})

# Provision groups reached by each category (clause 5.6 family).
PROVISION_GROUPS = {
    CATEGORY_SECONDARY: (
        "charge-management",
        "cell-rating-limits",
        "energy-balance-sizing",
        "safety-management",
        "storage-and-handling",
        "telemetry-monitoring",
    ),
    CATEGORY_PRIMARY: (
        "cell-rating-limits",
        "safety-management",
        "storage-and-handling",
        "telemetry-monitoring",
    ),
    CATEGORY_CONVERTER: (),
    CATEGORY_NON_ELECTROCHEMICAL: (),
}

_TOPOLOGY_KEYS = ("series_cells", "parallel_strings", "cell_capacity_ah")


def normalize_chemistry(chemistry):
    """Return the canonical lowercase chemistry token.

    Raises ValueError if the value is not a non-empty string.
    """
    if not isinstance(chemistry, str):
        raise ValueError("chemistry must be a string, got %r" % (chemistry,))
    token = chemistry.strip().lower()
    if not token:
        raise ValueError("chemistry must be a non-empty string")
    return token


def categorize_energy_source(chemistry):
    """Map a chemistry token onto exactly one applicability category.

    Raises ValueError for a chemistry that is not on the recognized list --
    an unknown store is an input defect, never a silent out-of-scope pass.
    """
    token = normalize_chemistry(chemistry)
    if token in SECONDARY_CELL_NOMINAL_V:
        return CATEGORY_SECONDARY
    if token in PRIMARY_CELL_NOMINAL_V:
        return CATEGORY_PRIMARY
    if token in CONVERTER_SOURCES:
        return CATEGORY_CONVERTER
    if token in NON_ELECTROCHEMICAL_SOURCES:
        return CATEGORY_NON_ELECTROCHEMICAL
    raise ValueError("unrecognized energy-source chemistry %r" % (token,))


def nominal_cell_voltage(chemistry):
    """Per-cell nominal voltage of an in-scope battery chemistry (V).

    Raises ValueError when the chemistry carries no cell voltage because it
    is not a battery in the sense of the clause.
    """
    token = normalize_chemistry(chemistry)
    category = categorize_energy_source(token)
    if category == CATEGORY_SECONDARY:
        return SECONDARY_CELL_NOMINAL_V[token]
    if category == CATEGORY_PRIMARY:
        return PRIMARY_CELL_NOMINAL_V[token]
    raise ValueError(
        "%r is categorized %s and has no per-cell nominal voltage"
        % (token, category)
    )


def battery_topology(chemistry, series_cells, parallel_strings, cell_capacity_ah):
    """Resolve a declared cell assembly into terminal voltage, capacity, energy.

    series_cells and parallel_strings are positive integers; cell_capacity_ah
    is a positive number of ampere-hours. Raises ValueError otherwise.
    """
    cell_v = nominal_cell_voltage(chemistry)
    for label, value in (
        ("series_cells", series_cells),
        ("parallel_strings", parallel_strings),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be an integer, got %r" % (label, value))
        if value < 1:
            raise ValueError("%s must be >= 1, got %d" % (label, value))
    if isinstance(cell_capacity_ah, bool) or not isinstance(
        cell_capacity_ah, (int, float)
    ):
        raise ValueError(
            "cell_capacity_ah must be a number, got %r" % (cell_capacity_ah,)
        )
    if cell_capacity_ah <= 0.0:
        raise ValueError(
            "cell_capacity_ah must be > 0, got %r" % (cell_capacity_ah,)
        )
    nominal_voltage_v = cell_v * series_cells
    capacity_ah = float(cell_capacity_ah) * parallel_strings
    return {
        "cell_nominal_voltage_v": cell_v,
        "series_cells": series_cells,
        "parallel_strings": parallel_strings,
        "nominal_voltage_v": nominal_voltage_v,
        "capacity_ah": capacity_ah,
        "stored_energy_wh": nominal_voltage_v * capacity_ah,
        "cell_count": series_cells * parallel_strings,
    }


def provisions_in_reach(category):
    """Provision groups reached by a category. Raises ValueError if unknown."""
    if category not in PROVISION_GROUPS:
        raise ValueError("unknown applicability category %r" % (category,))
    return PROVISION_GROUPS[category]


def evaluate_energy_store(item):
    """Decide reach for one inventory entry and collect its findings.

    Required keys: id, chemistry. Optional: series_cells, parallel_strings,
    cell_capacity_ah (all three together or none), declared_in_battery_scope
    (bool) and charge_control_present (bool).
    """
    if not isinstance(item, dict):
        raise ValueError("energy-store entry must be a mapping, got %r" % (item,))
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("energy-store entry needs a non-empty string 'id'")
    item_id = item_id.strip()
    category = categorize_energy_source(item.get("chemistry"))
    in_scope = category in IN_SCOPE_CATEGORIES
    findings = []

    present = [key for key in _TOPOLOGY_KEYS if item.get(key) is not None]
    topology = None
    if present and len(present) != len(_TOPOLOGY_KEYS):
        missing = [key for key in _TOPOLOGY_KEYS if item.get(key) is None]
        raise ValueError(
            "%s declares a partial cell assembly; missing %s"
            % (item_id, ", ".join(missing))
        )
    if present:
        if not in_scope:
            raise ValueError(
                "%s is categorized %s and cannot declare a cell assembly"
                % (item_id, category)
            )
        topology = battery_topology(
            item["chemistry"],
            item["series_cells"],
            item["parallel_strings"],
            item["cell_capacity_ah"],
        )
    elif in_scope:
        findings.append("%s: cell assembly not declared" % item_id)

    declared = item.get("declared_in_battery_scope")
    if declared is not None:
        if not isinstance(declared, bool):
            raise ValueError(
                "%s: declared_in_battery_scope must be a boolean" % item_id
            )
        if declared != in_scope:
            findings.append(
                "%s: declared reach %s contradicts derived reach %s (%s)"
                % (item_id, declared, in_scope, category)
            )

    charge_control = item.get("charge_control_present")
    if charge_control is not None and not isinstance(charge_control, bool):
        raise ValueError("%s: charge_control_present must be a boolean" % item_id)
    if category == CATEGORY_SECONDARY and charge_control is False:
        findings.append("%s: rechargeable store with no charge control" % item_id)

    return {
        "id": item_id,
        "category": category,
        "in_battery_scope": in_scope,
        "provisions": provisions_in_reach(category),
        "topology": topology,
        "findings": tuple(findings),
    }


def assess_energy_store_inventory(items):
    """Run the reach decision over a whole energy-storage inventory."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("inventory must be a list of entries")
    if not items:
        raise ValueError("inventory must contain at least one entry")
    records = []
    seen = set()
    findings = []
    for entry in items:
        record = evaluate_energy_store(entry)
        if record["id"] in seen:
            raise ValueError("duplicate energy-store id %r" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
        findings.extend(record["findings"])
    in_scope_ids = tuple(r["id"] for r in records if r["in_battery_scope"])
    out_of_scope_ids = tuple(r["id"] for r in records if not r["in_battery_scope"])
    return {
        "records": tuple(records),
        "in_scope_ids": in_scope_ids,
        "out_of_scope_ids": out_of_scope_ids,
        "total_stored_energy_wh": sum(
            r["topology"]["stored_energy_wh"] for r in records if r["topology"]
        ),
        "findings": tuple(findings),
        "settled": not findings,
    }
