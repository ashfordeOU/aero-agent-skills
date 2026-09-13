"""Common charging engineering concerns (ECSS-E-ST-20-06C clause 4.1.2).

Deterministic, offline, stdlib-only. Takes the numbers recorded against one
hardware item and returns the charging concerns it carries:

* surface-charge-buildup -- absolute frame potential, differential potential
  to the structure reference and to an adjacent surface;
* internal-charge-deposition -- the bulk electric field a deposited current
  density sustains in a dielectric, the deposition rate itself, and the
  aluminium-equivalent shield thickness behind which the dielectric sits;
* bonding -- an unbonded conductor, or one bonded through too high a
  resistance to bleed accumulated charge.

No ECSS text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "ITEM_KINDS",
    "SEVERITY_ORDER",
    "CONCERN_SEVERITY",
    "default_thresholds",
    "normalize_thresholds",
    "normalize_item",
    "differential_potential",
    "bulk_field",
    "allowable_bulk_field",
    "exceeds_limit",
    "assess_external_surface",
    "assess_buried_dielectric",
    "assess_floating_conductor",
    "severity_of",
    "worst_severity",
    "evaluate_item",
    "assess_items",
]

ITEM_KINDS = ("external-surface", "buried-dielectric", "floating-conductor")

SEVERITY_ORDER = ("none", "watch", "major", "critical")

CONCERN_SEVERITY = {
    "absolute-frame-potential-excursion": "major",
    "structure-referenced-differential-esd": "critical",
    "adjacent-surface-differential-esd": "critical",
    "buried-charge-breakdown": "critical",
    "marginal-bulk-field": "watch",
    "deposition-rate-above-screening-limit": "major",
    "shielding-below-guideline": "watch",
    "unbonded-floating-conductor": "critical",
    "high-impedance-bond": "major",
}

_DEFAULT_THRESHOLDS = {
    # Absolute structure potential relative to the ambient plasma, in volts.
    "absolute_potential_limit_v": 1000.0,
    # Differential potential across a dielectric boundary, in volts.
    "differential_potential_limit_v": 400.0,
    # Deposited current density screening limit, in amperes per square metre.
    "deposition_current_density_limit_a_m2": 1.0e-9,
    # Dielectric strength is divided by this factor to get the allowable field.
    "bulk_field_safety_factor": 2.0,
    # Fraction of the allowable field above which a passing item is marginal.
    "marginal_field_fraction": 0.9,
    # Aluminium-equivalent shield thickness guideline, in millimetres.
    "shield_thickness_guideline_mm": 2.0,
    # Bond resistance above which a bonded conductor is high impedance, ohms.
    "bond_resistance_limit_ohm": 1.0e6,
}

_LIMIT_TOLERANCE = 1e-12


def _real(value, name, allow_negative=False, allow_zero=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    if not allow_zero and number == 0.0:
        raise ValueError("%s must be non-zero" % name)
    return number


def _bool(value, name):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def default_thresholds():
    """A fresh copy of the default threshold set."""
    return dict(_DEFAULT_THRESHOLDS)


def normalize_thresholds(overrides=None):
    """Defaults merged with validated overrides. ValueError on an unknown key."""
    thresholds = default_thresholds()
    if overrides is None:
        return thresholds
    if not isinstance(overrides, dict):
        raise ValueError("threshold overrides must be a mapping")
    for key, value in overrides.items():
        if key not in thresholds:
            raise ValueError("unknown threshold %r" % (key,))
        thresholds[key] = _real(value, key, allow_zero=False)
    if not 0.0 < thresholds["marginal_field_fraction"] <= 1.0:
        raise ValueError("marginal_field_fraction must lie in (0, 1]")
    if thresholds["bulk_field_safety_factor"] < 1.0:
        raise ValueError("bulk_field_safety_factor must be at least 1.0")
    return thresholds


def _require(item, key):
    if key not in item:
        raise ValueError(
            "item %r of kind %r missing required field %r"
            % (item.get("name", "unnamed"), item.get("kind"), key)
        )
    return item[key]


def normalize_item(item):
    """Validate one hardware item record and fill its optional fields."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    name = item.get("name", "")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("item name must be a non-empty string")
    kind = item.get("kind")
    if not isinstance(kind, str) or kind.strip().lower() not in ITEM_KINDS:
        raise ValueError(
            "unknown item kind %r; expected one of %s" % (kind, ", ".join(ITEM_KINDS))
        )
    kind = kind.strip().lower()
    record = {"name": name.strip(), "kind": kind}

    if kind == "external-surface":
        record["potential_v"] = _real(
            _require(item, "potential_v"), "potential_v", allow_negative=True
        )
        record["reference_potential_v"] = _real(
            item.get("reference_potential_v", 0.0),
            "reference_potential_v",
            allow_negative=True,
        )
        neighbour = item.get("adjacent_potential_v")
        record["adjacent_potential_v"] = (
            None
            if neighbour is None
            else _real(neighbour, "adjacent_potential_v", allow_negative=True)
        )
    elif kind == "buried-dielectric":
        record["deposited_current_density_a_m2"] = _real(
            _require(item, "deposited_current_density_a_m2"),
            "deposited_current_density_a_m2",
            allow_zero=False,
        )
        record["resistivity_ohm_m"] = _real(
            _require(item, "resistivity_ohm_m"), "resistivity_ohm_m", allow_zero=False
        )
        record["dielectric_strength_v_m"] = _real(
            _require(item, "dielectric_strength_v_m"),
            "dielectric_strength_v_m",
            allow_zero=False,
        )
        shield = item.get("shield_thickness_mm")
        record["shield_thickness_mm"] = (
            None if shield is None else _real(shield, "shield_thickness_mm")
        )
    else:
        record["bonded"] = _bool(_require(item, "bonded"), "bonded")
        resistance = item.get("bond_resistance_ohm")
        record["bond_resistance_ohm"] = (
            None
            if resistance is None
            else _real(resistance, "bond_resistance_ohm", allow_zero=False)
        )
    return record


def differential_potential(potential_a_v, potential_b_v):
    """Magnitude of the potential difference between two surfaces, in volts."""
    a = _real(potential_a_v, "potential_a_v", allow_negative=True)
    b = _real(potential_b_v, "potential_b_v", allow_negative=True)
    return abs(a - b)


def bulk_field(current_density_a_m2, resistivity_ohm_m):
    """Steady-state field a deposited current density sustains, in V/m."""
    current = _real(
        current_density_a_m2, "current_density_a_m2", allow_zero=False
    )
    resistivity = _real(resistivity_ohm_m, "resistivity_ohm_m", allow_zero=False)
    return current * resistivity


def allowable_bulk_field(dielectric_strength_v_m, safety_factor):
    """Dielectric strength reduced by the safety factor, in V/m."""
    strength = _real(
        dielectric_strength_v_m, "dielectric_strength_v_m", allow_zero=False
    )
    factor = _real(safety_factor, "safety_factor", allow_zero=False)
    if factor < 1.0:
        raise ValueError("safety_factor must be at least 1.0, got %r" % (safety_factor,))
    return strength / factor


def exceeds_limit(value, limit):
    """True only when value is genuinely above limit.

    A value that lands a few units in the last place above a limit it
    physically meets -- a difference of two potentials, or a product of a
    current density and a resistivity -- is treated as compliant. The limit
    itself is never widened.
    """
    value = _real(value, "value", allow_negative=True)
    limit = _real(limit, "limit", allow_negative=True)
    if value <= limit:
        return False
    return not math.isclose(value, limit, rel_tol=_LIMIT_TOLERANCE, abs_tol=0.0)


def assess_external_surface(item, thresholds):
    """Concerns carried by an external surface."""
    concerns = []
    if exceeds_limit(abs(item["potential_v"]), thresholds["absolute_potential_limit_v"]):
        concerns.append("absolute-frame-potential-excursion")
    structure = differential_potential(
        item["potential_v"], item["reference_potential_v"]
    )
    if exceeds_limit(structure, thresholds["differential_potential_limit_v"]):
        concerns.append("structure-referenced-differential-esd")
    if item["adjacent_potential_v"] is not None:
        adjacent = differential_potential(
            item["potential_v"], item["adjacent_potential_v"]
        )
        if exceeds_limit(adjacent, thresholds["differential_potential_limit_v"]):
            concerns.append("adjacent-surface-differential-esd")
    return tuple(concerns)


def assess_buried_dielectric(item, thresholds):
    """Concerns carried by a dielectric that stores deposited charge."""
    concerns = []
    field = bulk_field(
        item["deposited_current_density_a_m2"], item["resistivity_ohm_m"]
    )
    allowable = allowable_bulk_field(
        item["dielectric_strength_v_m"], thresholds["bulk_field_safety_factor"]
    )
    if exceeds_limit(field, allowable):
        concerns.append("buried-charge-breakdown")
    elif not exceeds_limit(
        allowable * thresholds["marginal_field_fraction"], field
    ):
        concerns.append("marginal-bulk-field")
    if exceeds_limit(
        item["deposited_current_density_a_m2"],
        thresholds["deposition_current_density_limit_a_m2"],
    ):
        concerns.append("deposition-rate-above-screening-limit")
    shield = item["shield_thickness_mm"]
    if shield is not None and exceeds_limit(
        thresholds["shield_thickness_guideline_mm"], shield
    ):
        concerns.append("shielding-below-guideline")
    return tuple(concerns)


def assess_floating_conductor(item, thresholds):
    """Concerns carried by a conductor that may float free of the structure."""
    if not item["bonded"]:
        return ("unbonded-floating-conductor",)
    resistance = item["bond_resistance_ohm"]
    if resistance is not None and exceeds_limit(
        resistance, thresholds["bond_resistance_limit_ohm"]
    ):
        return ("high-impedance-bond",)
    return ()


def severity_of(concern):
    """Severity band of one concern token. ValueError on an unknown token."""
    if concern not in CONCERN_SEVERITY:
        raise ValueError("unknown concern %r" % (concern,))
    return CONCERN_SEVERITY[concern]


def worst_severity(concerns):
    """Highest severity across a set of concerns; 'none' when empty."""
    worst = "none"
    for concern in concerns:
        band = severity_of(concern)
        if SEVERITY_ORDER.index(band) > SEVERITY_ORDER.index(worst):
            worst = band
    return worst


def evaluate_item(item, thresholds=None):
    """Evaluate one item and return its concerns, severity and compliance."""
    limits = normalize_thresholds(thresholds)
    record = normalize_item(item)
    if record["kind"] == "external-surface":
        concerns = assess_external_surface(record, limits)
    elif record["kind"] == "buried-dielectric":
        concerns = assess_buried_dielectric(record, limits)
    else:
        concerns = assess_floating_conductor(record, limits)
    concerns = tuple(sorted(set(concerns)))
    severity = worst_severity(concerns)
    return {
        "name": record["name"],
        "kind": record["kind"],
        "concerns": concerns,
        "severity": severity,
        "concern_free": not concerns,
    }


def assess_items(items, thresholds=None):
    """Evaluate an item list and roll the findings up by severity."""
    try:
        rows = list(items)
    except TypeError:
        raise ValueError("items must be an iterable of item mappings")
    if not rows:
        raise ValueError("at least one item is required")
    limits = normalize_thresholds(thresholds)
    evaluated = [evaluate_item(row, limits) for row in rows]
    counts = {band: 0 for band in SEVERITY_ORDER}
    for result in evaluated:
        counts[result["severity"]] += 1
    flagged = tuple(r["name"] for r in evaluated if not r["concern_free"])
    return {
        "count": len(evaluated),
        "items": tuple(evaluated),
        "severity_counts": counts,
        "flagged_items": flagged,
        "worst_severity": worst_severity(
            [c for r in evaluated for c in r["concerns"]]
        ),
        "concern_free": not flagged,
    }
