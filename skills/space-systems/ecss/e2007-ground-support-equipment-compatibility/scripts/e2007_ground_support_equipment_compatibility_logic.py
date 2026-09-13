#!/usr/bin/env python3
"""Ground-support-equipment compatibility logic (ECSS-E-ST-20-07C clause 4.2.9).

Deterministic, offline, Python standard library only.

Clause 4.2.9 requires the electrical and mechanical ground equipment used
around a spacecraft during integration and testing not to degrade the
electromagnetic compatibility the flight design was qualified to. This module
turns that into a checkable procedure:

1. every item is categorized into the electrical or the mechanical
   ground-support-equipment family, which selects the checks that apply;
2. an electrical item's bond path is summed segment by segment and compared
   with the bond-resistance ceiling, and the return current through that
   bond gives the reference potential difference at the vehicle interface;
3. declared radiated emission levels are moved from their reference distance
   to the stand-off distance the item actually occupies, then compared with
   the vehicle susceptibility limit through the required compatibility
   margin, as are conducted levels on umbilical lines;
4. a mechanical item that contacts flight hardware has its surface
   resistivity placed inside the dissipative bleed-path window;
5. every item is checked for a compatibility verification record.

Units: resistance in ohms, current in amperes, potential in volts, distance
in metres, emission and susceptibility levels in decibels referred to their
own reference unit, surface resistivity in ohms per square. No standard text
is reproduced.
"""

import math

__all__ = [
    "DEFAULT_BOND_CEILING_OHM",
    "DEFAULT_REQUIRED_MARGIN_DB",
    "DEFAULT_SAFE_POTENTIAL_V",
    "BLEED_PATH_WINDOW_OHM_PER_SQUARE",
    "GSE_FAMILIES",
    "VERIFICATION_STATES",
    "TOLERANCE",
    "categorize_gse_item",
    "bond_path_resistance_ohm",
    "bond_resistance_finding",
    "reference_potential_difference_v",
    "scale_emission_to_distance_db",
    "emission_margin_db",
    "meets_required_margin",
    "bleed_path_state",
    "verification_findings",
    "evaluate_gse_item",
    "assess_ground_support_equipment_compatibility",
]

# Bond path from an electrical ground-support item to the common reference.
DEFAULT_BOND_CEILING_OHM = 0.010

# Compatibility margin the emission checks have to reach, in decibels.
DEFAULT_REQUIRED_MARGIN_DB = 6.0

# Potential a sensitive vehicle interface tolerates between references.
DEFAULT_SAFE_POTENTIAL_V = 0.050

# Dissipative window for a contacting mechanical surface, ohms per square.
BLEED_PATH_WINDOW_OHM_PER_SQUARE = (1.0e5, 1.0e9)

GSE_FAMILIES = {
    "stimulus-rack": "electrical",
    "power-feed": "electrical",
    "umbilical": "electrical",
    "check-out-console": "electrical",
    "handling-fixture": "mechanical",
    "container": "mechanical",
    "trolley": "mechanical",
    "lifting-device": "mechanical",
}

VERIFICATION_STATES = ("verified", "waived", "unverified")

# Sums of measured resistances and differences of decibel levels can land a
# few ULPs the wrong side of a comparison. This relative tolerance absorbs
# that representation error at the exact boundary; it does not move any
# engineering limit.
TOLERANCE = 1e-12


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _as_float(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, out))
    return out


def _within(value, ceiling):
    """True when value <= ceiling, absorbing float representation error."""
    return value < ceiling or math.isclose(
        value, ceiling, rel_tol=TOLERANCE, abs_tol=0.0
    )


def categorize_gse_item(item_type):
    """Return 'electrical' or 'mechanical' for a ground-support-equipment type.

    Raises ValueError for a type outside the two families; an uncategorized
    item is not evaluated by this procedure.
    """
    if not isinstance(item_type, str):
        raise ValueError("item_type must be a string, got %r" % (item_type,))
    key = item_type.strip().lower()
    if key not in GSE_FAMILIES:
        raise ValueError(
            "uncategorized ground-support-equipment type %r; expected one of %s"
            % (item_type, ", ".join(sorted(GSE_FAMILIES)))
        )
    return GSE_FAMILIES[key]


def bond_path_resistance_ohm(segments):
    """Total resistance of a bond path declared as a chain of segments.

    Raises ValueError on an empty chain or a non-positive segment.
    """
    if segments is None:
        raise ValueError("bond path segments are required")
    items = list(segments)
    if not items:
        raise ValueError("bond path must declare at least one segment")
    total = 0.0
    for index, value in enumerate(items):
        total += _positive(value, "bond path segment %d" % index)
    return total


def bond_resistance_finding(total_ohm, ceiling_ohm=DEFAULT_BOND_CEILING_OHM):
    """None when the bond path meets the ceiling, else a finding string."""
    total = _as_float(total_ohm, "total_ohm")
    ceiling = _positive(ceiling_ohm, "ceiling_ohm")
    if total < 0.0:
        raise ValueError("total_ohm must be non-negative, got %r" % (total,))
    if _within(total, ceiling):
        return None
    return (
        "bond path totals %.6g ohm against a %.6g ohm ceiling" % (total, ceiling)
    )


def reference_potential_difference_v(return_current_a, bond_resistance_ohm):
    """Potential the return current raises across the bond path.

    Raises ValueError on a negative current or resistance.
    """
    current = _as_float(return_current_a, "return_current_a")
    resistance = _as_float(bond_resistance_ohm, "bond_resistance_ohm")
    if current < 0.0:
        raise ValueError("return_current_a must be non-negative, got %r" % (current,))
    if resistance < 0.0:
        raise ValueError(
            "bond_resistance_ohm must be non-negative, got %r" % (resistance,)
        )
    return current * resistance


def scale_emission_to_distance_db(level_db, reference_distance_m, stand_off_m):
    """Move a declared emission level from its reference to the real distance.

    An item closer than its reference distance reads higher; the correction is
    twenty times the base-ten logarithm of the distance ratio. Raises
    ValueError on a non-positive distance.
    """
    level = _as_float(level_db, "level_db")
    reference = _positive(reference_distance_m, "reference_distance_m")
    stand_off = _positive(stand_off_m, "stand_off_m")
    return level - 20.0 * math.log10(stand_off / reference)


def emission_margin_db(susceptibility_limit_db, emission_db):
    """Margin between a vehicle susceptibility limit and an emission level."""
    limit = _as_float(susceptibility_limit_db, "susceptibility_limit_db")
    emission = _as_float(emission_db, "emission_db")
    return limit - emission


def meets_required_margin(margin_db, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB):
    """True when the margin reaches the requirement, absorbing float error."""
    margin = _as_float(margin_db, "margin_db")
    required = _as_float(required_margin_db, "required_margin_db")
    if required < 0.0:
        raise ValueError(
            "required_margin_db must be non-negative, got %r" % (required,)
        )
    return margin > required or math.isclose(
        margin, required, rel_tol=0.0, abs_tol=1e-9
    )


def bleed_path_state(surface_resistivity, window=BLEED_PATH_WINDOW_OHM_PER_SQUARE):
    """Place a contacting surface in the dissipative window.

    Returns "insulating", "dissipative" or "conductive". Raises ValueError on
    a non-positive resistivity or a malformed window.
    """
    value = _positive(surface_resistivity, "surface_resistivity")
    low = _positive(window[0], "window lower bound")
    high = _positive(window[1], "window upper bound")
    if high <= low:
        raise ValueError(
            "window upper bound (%r) must exceed the lower bound (%r)" % (high, low)
        )
    if value < low and not math.isclose(value, low, rel_tol=TOLERANCE):
        return "conductive"
    if value > high and not math.isclose(value, high, rel_tol=TOLERANCE):
        return "insulating"
    return "dissipative"


def verification_findings(item):
    """Findings against the compatibility verification record of one item.

    Raises ValueError on a verification state outside the recognised set.
    """
    findings = []
    state = item.get("verification_status", "unverified")
    if not isinstance(state, str):
        raise ValueError("verification_status must be a string, got %r" % (state,))
    key = state.strip().lower()
    if key not in VERIFICATION_STATES:
        raise ValueError(
            "verification_status %r must be one of %s"
            % (state, ", ".join(VERIFICATION_STATES))
        )
    powered = bool(item.get("powered_in_activity", True))
    if key == "unverified" and powered:
        findings.append(
            "item takes part in a powered activity with no compatibility "
            "verification on record"
        )
    if key == "waived":
        rationale = item.get("waiver_rationale")
        if not rationale or not str(rationale).strip():
            findings.append("compatibility waiver carries no recorded rationale")
    return findings


def evaluate_gse_item(
    item,
    vehicle,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Evaluate one ground-support-equipment item against the vehicle limits.

    item: item_id, item_type, plus family-specific fields --
      electrical: bond_segments_ohm, return_current_a, stand_off_m,
                  radiated_levels_db (list of {level_db, reference_distance_m}),
                  conducted_levels_db (list of numbers)
      mechanical: contacts_flight_hardware, surface_resistivity
    vehicle: radiated_susceptibility_db, conducted_susceptibility_db,
             optional bond_ceiling_ohm and safe_potential_v.

    Returns a result mapping with a findings list and a compatible flag.
    Raises ValueError on malformed input.
    """
    for key in ("item_id", "item_type"):
        if key not in item:
            raise ValueError("item entry missing '%s'" % key)
    family = categorize_gse_item(item["item_type"])
    result = {
        "item_id": item["item_id"],
        "family": family,
        "findings": list(verification_findings(item)),
        "bond_resistance_ohm": None,
        "reference_potential_v": None,
        "radiated_margins_db": [],
        "conducted_margins_db": [],
        "bleed_path_state": None,
    }

    if family == "electrical":
        ceiling = vehicle.get("bond_ceiling_ohm", DEFAULT_BOND_CEILING_OHM)
        safe_potential = vehicle.get("safe_potential_v", DEFAULT_SAFE_POTENTIAL_V)
        if "bond_segments_ohm" not in item:
            raise ValueError(
                "electrical item %r missing 'bond_segments_ohm'" % (item["item_id"],)
            )
        bond = bond_path_resistance_ohm(item["bond_segments_ohm"])
        result["bond_resistance_ohm"] = bond
        finding = bond_resistance_finding(bond, ceiling)
        if finding:
            result["findings"].append(finding)

        potential = reference_potential_difference_v(
            item.get("return_current_a", 0.0), bond
        )
        result["reference_potential_v"] = potential
        safe = _positive(safe_potential, "safe_potential_v")
        if not _within(potential, safe):
            result["findings"].append(
                "return current lifts the reference by %.6g V against a %.6g V "
                "interface allowance" % (potential, safe)
            )

        stand_off = item.get("stand_off_m")
        radiated = item.get("radiated_levels_db") or []
        if radiated and stand_off is None:
            raise ValueError(
                "electrical item %r declares radiated levels but no 'stand_off_m'"
                % (item["item_id"],)
            )
        limit_radiated = _as_float(
            vehicle.get("radiated_susceptibility_db"), "radiated_susceptibility_db"
        )
        for index, entry in enumerate(radiated):
            for key in ("level_db", "reference_distance_m"):
                if key not in entry:
                    raise ValueError(
                        "radiated level %d missing '%s'" % (index, key)
                    )
            scaled = scale_emission_to_distance_db(
                entry["level_db"], entry["reference_distance_m"], stand_off
            )
            margin = emission_margin_db(limit_radiated, scaled)
            result["radiated_margins_db"].append(margin)
            if not meets_required_margin(margin, required_margin_db):
                result["findings"].append(
                    "radiated level %d leaves %.4g dB against a %.4g dB "
                    "requirement at %.4g m" % (index, margin, required_margin_db, stand_off)
                )

        conducted = item.get("conducted_levels_db") or []
        if conducted:
            limit_conducted = _as_float(
                vehicle.get("conducted_susceptibility_db"),
                "conducted_susceptibility_db",
            )
            for index, level in enumerate(conducted):
                margin = emission_margin_db(limit_conducted, level)
                result["conducted_margins_db"].append(margin)
                if not meets_required_margin(margin, required_margin_db):
                    result["findings"].append(
                        "umbilical conducted level %d leaves %.4g dB against a "
                        "%.4g dB requirement" % (index, margin, required_margin_db)
                    )
    else:
        if item.get("contacts_flight_hardware", True):
            if "surface_resistivity" not in item:
                raise ValueError(
                    "contacting mechanical item %r missing 'surface_resistivity'"
                    % (item["item_id"],)
                )
            window = item.get("bleed_window", BLEED_PATH_WINDOW_OHM_PER_SQUARE)
            state = bleed_path_state(item["surface_resistivity"], window)
            result["bleed_path_state"] = state
            if state != "dissipative":
                result["findings"].append(
                    "contacting surface is %s, outside the electrostatic "
                    "bleed-path window" % state
                )

    result["compatible"] = not result["findings"]
    return result


def assess_ground_support_equipment_compatibility(
    items,
    vehicle,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Assess every ground-support-equipment item in one activity.

    Raises ValueError on an empty item set, a duplicate item identifier or a
    vehicle record missing the radiated susceptibility limit.
    """
    item_list = list(items or [])
    if not item_list:
        raise ValueError("at least one ground-support-equipment item is required")
    if not isinstance(vehicle, dict):
        raise ValueError("vehicle must be a mapping")
    if "radiated_susceptibility_db" not in vehicle:
        raise ValueError("vehicle record missing 'radiated_susceptibility_db'")

    seen = set()
    results = []
    for index, item in enumerate(item_list):
        if not isinstance(item, dict):
            raise ValueError("item %d must be a mapping" % index)
        ident = item.get("item_id")
        if ident in seen:
            raise ValueError("duplicate item identifier %r" % (ident,))
        seen.add(ident)
        results.append(evaluate_gse_item(item, vehicle, required_margin_db))

    non_compliant = [r for r in results if not r["compatible"]]
    return {
        "items": results,
        "non_compliant_items": non_compliant,
        "electrical_count": sum(1 for r in results if r["family"] == "electrical"),
        "mechanical_count": sum(1 for r in results if r["family"] == "mechanical"),
        "required_margin_db": _as_float(required_margin_db, "required_margin_db"),
        "activity_compatible": not non_compliant,
    }
