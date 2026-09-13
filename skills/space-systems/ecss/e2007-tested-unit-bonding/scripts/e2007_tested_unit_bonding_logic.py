#!/usr/bin/env python3
"""Bonding of a tested unit to the test reference plane under
ECSS-E-ST-20-07C clause 5.2.6.2.

Paraphrased, implementable procedure (no verbatim standard text):

* A unit under electromagnetic measurement is bonded to the reference
  plane only through the bonding means that belong to its own design --
  its qualified mounting interface and the bonding strap defined in its
  interface documentation. Anything the laboratory adds for convenience
  changes the very impedance the measurement is trying to characterize.
* Each bond path is therefore categorized by provenance before any
  number is computed: design-provided, or test-added. Every test-added
  path is a setup non-conformance in its own right, whatever its
  resistance turns out to be.
* The direct-current resistance of a design-provided path is the strap
  or foot resistance (material resistivity times length over section)
  in series with the contact resistance of each joint along it.
* Paths in place at the same time carry current in parallel, so the
  effective bonding resistance of the unit is the parallel combination
  of the design-provided paths only; a test-added path is excluded from
  the number rather than quietly improving it.
* A bond path also has to work at radio frequency, where inductance
  dominates. That is controlled geometrically, by keeping the strap
  length-to-width ratio at or below a stated maximum.
* The computed effective resistance is finally reconciled with the
  bench measurement; a disagreement beyond a stated fraction means the
  model or the joint is wrong and is reported, not averaged away.

Stdlib only, offline, deterministic.
"""

import math

# Named tolerance absorbing binary representation error in resistance sums
# and geometric ratios. It is NOT an engineering allowance: the bonding
# limits themselves are never widened.
BOND_EPS = 1e-12
RATIO_EPS = 1e-9

DESIGN_PROVIDED = "design-provided"
TEST_ADDED = "test-added"

PROVENANCE_CATEGORY = {
    "unit-design": DESIGN_PROVIDED,
    "interface-control-document": DESIGN_PROVIDED,
    "qualified-mounting-interface": DESIGN_PROVIDED,
    "test-setup-jumper": TEST_ADDED,
    "laboratory-auxiliary-strap": TEST_ADDED,
}

# Direct-current resistivity in ohm metre at laboratory temperature.
RESISTIVITY_OHM_M = {
    "silver": 1.59e-8,
    "copper": 1.72e-8,
    "tinned-copper-braid": 2.10e-8,
    "aluminium": 2.82e-8,
    "stainless-steel": 6.90e-7,
}

MAX_STRAP_ASPECT_RATIO = 5.0


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _not_above(value, limit, tolerance):
    """True when value does not exceed limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=tolerance)


def categorize_bond_path(path):
    """Categorize one bond path as design-provided or test-added."""
    if not isinstance(path, dict):
        raise ValueError("bond path must be a mapping, got %r" % (path,))
    name = path.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("bond path needs a non-empty 'name', got %r" % (name,))
    provenance = path.get("provenance")
    if provenance not in PROVENANCE_CATEGORY:
        raise ValueError(
            "bond path %r has unrecognized provenance %r (expected one of %s)"
            % (name, provenance, ", ".join(sorted(PROVENANCE_CATEGORY)))
        )
    return PROVENANCE_CATEGORY[provenance]


def strap_resistance_ohm(material, length_mm, width_mm, thickness_mm):
    """Direct-current resistance of a rectangular bonding strap or foot."""
    if material not in RESISTIVITY_OHM_M:
        raise ValueError(
            "unrecognized bonding material %r (expected one of %s)"
            % (material, ", ".join(sorted(RESISTIVITY_OHM_M)))
        )
    length_mm = _require_number(length_mm, "length_mm")
    width_mm = _require_number(width_mm, "width_mm")
    thickness_mm = _require_number(thickness_mm, "thickness_mm")
    if length_mm <= 0.0:
        raise ValueError("length_mm must be positive, got %r" % (length_mm,))
    if width_mm <= 0.0:
        raise ValueError("width_mm must be positive, got %r" % (width_mm,))
    if thickness_mm <= 0.0:
        raise ValueError("thickness_mm must be positive, got %r" % (thickness_mm,))
    length_m = length_mm / 1000.0
    section_m2 = (width_mm / 1000.0) * (thickness_mm / 1000.0)
    return RESISTIVITY_OHM_M[material] * length_m / section_m2


def contact_resistance_ohm(contacts):
    """Series sum of the joint resistances along one bond path."""
    if contacts is None:
        return 0.0
    if not isinstance(contacts, (list, tuple)):
        raise ValueError("contact_resistances_ohm must be a sequence, got %r" % (contacts,))
    total = 0.0
    for i, value in enumerate(contacts):
        value = _require_number(value, "contact_resistances_ohm[%d]" % i)
        if value < 0.0:
            raise ValueError(
                "contact_resistances_ohm[%d] must not be negative, got %r" % (i, value)
            )
        total += value
    return total


def path_resistance_ohm(path):
    """Total series resistance of one bond path, strap plus every joint."""
    categorize_bond_path(path)
    strap = strap_resistance_ohm(
        path.get("material"),
        path.get("length_mm"),
        path.get("width_mm"),
        path.get("thickness_mm"),
    )
    return strap + contact_resistance_ohm(path.get("contact_resistances_ohm"))


def parallel_resistance_ohm(values):
    """Parallel combination of a set of positive resistances."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("parallel_resistance_ohm needs a non-empty sequence")
    conductance = 0.0
    for i, value in enumerate(values):
        value = _require_number(value, "values[%d]" % i)
        if value <= 0.0:
            raise ValueError("values[%d] must be positive, got %r" % (i, value))
        conductance += 1.0 / value
    return 1.0 / conductance


def effective_bond_resistance_ohm(paths):
    """Effective resistance of the design-provided bonding set only."""
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("paths must be a non-empty sequence of bond paths")
    design = [p for p in paths if categorize_bond_path(p) == DESIGN_PROVIDED]
    if not design:
        raise ValueError(
            "no design-provided bond path on record; the unit has no bonding means of its own"
        )
    return parallel_resistance_ohm([path_resistance_ohm(p) for p in design])


def strap_aspect_ratio(length_mm, width_mm):
    """Length-to-width ratio of a bonding strap."""
    length_mm = _require_number(length_mm, "length_mm")
    width_mm = _require_number(width_mm, "width_mm")
    if length_mm <= 0.0:
        raise ValueError("length_mm must be positive, got %r" % (length_mm,))
    if width_mm <= 0.0:
        raise ValueError("width_mm must be positive, got %r" % (width_mm,))
    return length_mm / width_mm


def check_strap_geometry(length_mm, width_mm, max_ratio=MAX_STRAP_ASPECT_RATIO):
    """Confirm a strap is short and wide enough to stay low-inductance."""
    max_ratio = _require_number(max_ratio, "max_ratio")
    if max_ratio <= 0.0:
        raise ValueError("max_ratio must be positive, got %r" % (max_ratio,))
    ratio = strap_aspect_ratio(length_mm, width_mm)
    return {
        "aspect_ratio": ratio,
        "max_ratio": max_ratio,
        "compliant": _not_above(ratio, max_ratio, RATIO_EPS),
    }


def check_bond_resistance(measured_ohm, limit_ohm):
    """Compare a bonding resistance with its declared requirement."""
    measured_ohm = _require_number(measured_ohm, "measured_ohm")
    limit_ohm = _require_number(limit_ohm, "limit_ohm")
    if measured_ohm < 0.0:
        raise ValueError("measured_ohm must not be negative, got %r" % (measured_ohm,))
    if limit_ohm <= 0.0:
        raise ValueError("limit_ohm must be positive, got %r" % (limit_ohm,))
    return {
        "measured_ohm": measured_ohm,
        "limit_ohm": limit_ohm,
        "margin_ohm": limit_ohm - measured_ohm,
        "compliant": _not_above(measured_ohm, limit_ohm, BOND_EPS),
    }


def compare_declared_and_measured(computed_ohm, measured_ohm, tolerance_fraction):
    """Reconcile the computed bonding resistance with the bench reading."""
    computed_ohm = _require_number(computed_ohm, "computed_ohm")
    measured_ohm = _require_number(measured_ohm, "measured_ohm")
    tolerance_fraction = _require_number(tolerance_fraction, "tolerance_fraction")
    if computed_ohm <= 0.0:
        raise ValueError("computed_ohm must be positive, got %r" % (computed_ohm,))
    if measured_ohm < 0.0:
        raise ValueError("measured_ohm must not be negative, got %r" % (measured_ohm,))
    if tolerance_fraction < 0.0:
        raise ValueError(
            "tolerance_fraction must not be negative, got %r" % (tolerance_fraction,)
        )
    relative = abs(measured_ohm - computed_ohm) / computed_ohm
    return {
        "computed_ohm": computed_ohm,
        "measured_ohm": measured_ohm,
        "relative_deviation": relative,
        "tolerance_fraction": tolerance_fraction,
        "agrees": _not_above(relative, tolerance_fraction, RATIO_EPS),
    }


def audit_bonding_configuration(config):
    """End-to-end clause 5.2.6.2 bonding audit for one tested unit."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    paths = config.get("paths")
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("config['paths'] must be a non-empty sequence of bond paths")
    limit = _require_number(
        config.get("bond_resistance_limit_ohm", 2.5e-3), "bond_resistance_limit_ohm"
    )
    max_ratio = _require_number(
        config.get("max_strap_aspect_ratio", MAX_STRAP_ASPECT_RATIO),
        "max_strap_aspect_ratio",
    )

    names = []
    records = []
    for path in paths:
        category = categorize_bond_path(path)
        names.append(path["name"])
        record = {
            "name": path["name"],
            "provenance": path["provenance"],
            "category": category,
            "resistance_ohm": path_resistance_ohm(path),
            "geometry": check_strap_geometry(
                path.get("length_mm"), path.get("width_mm"), max_ratio
            ),
        }
        records.append(record)
    if len(set(names)) != len(names):
        raise ValueError("bond path names must be unique, got %r" % (names,))

    findings = []
    for record in records:
        if record["category"] == TEST_ADDED:
            findings.append(
                "bond path %s was added for the test and is not part of the unit design"
                % record["name"]
            )
        elif not record["geometry"]["compliant"]:
            findings.append(
                "bond path %s exceeds the permitted strap length-to-width ratio"
                % record["name"]
            )

    design = [r for r in records if r["category"] == DESIGN_PROVIDED]
    if not design:
        findings.append("no design-provided bonding path on record")
        effective = None
        resistance = None
    else:
        effective = parallel_resistance_ohm([r["resistance_ohm"] for r in design])
        resistance = check_bond_resistance(effective, limit)
        if not resistance["compliant"]:
            findings.append("effective bonding resistance above the declared requirement")

    reconciliation = None
    measured = config.get("measured_effective_resistance_ohm")
    if effective is None:
        pass
    elif measured is None:
        findings.append("no bench bonding-resistance measurement on record")
    else:
        reconciliation = compare_declared_and_measured(
            effective, measured, config.get("reconciliation_tolerance_fraction", 0.25)
        )
        if not reconciliation["agrees"]:
            findings.append("bench bonding measurement disagrees with the computed value")

    return {
        "paths": records,
        "design_path_count": len(design),
        "test_added_path_count": len(records) - len(design),
        "effective_resistance_ohm": effective,
        "resistance_check": resistance,
        "reconciliation": reconciliation,
        "findings": findings,
        "status": "bonding-as-designed" if not findings else "bonding-non-conformance",
        "compliant": not findings,
    }
