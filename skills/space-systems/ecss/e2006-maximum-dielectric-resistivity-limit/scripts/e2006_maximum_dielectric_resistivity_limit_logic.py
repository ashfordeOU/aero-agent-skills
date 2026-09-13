#!/usr/bin/env python3
"""Maximum dielectric resistivity limit (ECSS-E-ST-20-06C clause 6.2.2).

Paraphrased, implementable procedure -- no standard text is reproduced.

The clause does not hand out a resistivity number; it requires the
resistivity of an external dielectric to stay below a ceiling derived from
a bounding charging current density and the differential potential the
surface is allowed to sustain.

Bulk path (through the thickness):

    V = rho * J * t          ->      rho_max = V_allow / (J * t)

Sheet path (along a conductive coating draining to a grounded edge, with
the environment current collected uniformly over the bleed path):

    V = rho_s * J * L**2 / 2 ->      rho_s_max = 2 * V_allow / (J * L**2)

Everything here is stdlib-only, offline and deterministic.
"""

import math

__all__ = [
    "REL_TOL",
    "CONDUCTIVE_REGIME_MAX_OHM_M",
    "DISSIPATIVE_REGIME_MAX_OHM_M",
    "net_charging_current_density",
    "bounding_charging_current_density",
    "maximum_bulk_resistivity",
    "maximum_sheet_resistivity",
    "bulk_potential_drop",
    "sheet_potential_drop",
    "maximum_dielectric_thickness",
    "resistivity_margin",
    "categorize_resistivity_regime",
    "within_ceiling",
    "evaluate_dielectric",
    "assess_dielectric_inventory",
]

# Relative tolerance applied when a computed quantity meets an engineering
# ceiling exactly. A ceiling such as V / (J * t) is a quotient of powers of
# ten and can land a few ULPs either side of the algebraic value; the
# tolerance absorbs that representation error. The engineering ceiling
# itself is never widened.
REL_TOL = 1e-9

# Descriptive resistivity regimes (ohm*m) used to steer the review. They are
# review aids only: the derived ceiling is the requirement.
CONDUCTIVE_REGIME_MAX_OHM_M = 1.0e4
DISSIPATIVE_REGIME_MAX_OHM_M = 1.0e11

_REQUIRED_ITEM_KEYS = ("id", "resistivity_ohm_m", "thickness_m")
_KNOWN_ITEM_KEYS = set(_REQUIRED_ITEM_KEYS) | {
    "allowable_potential_v",
    "coating_sheet_resistivity_ohm_sq",
    "bleed_path_length_m",
}


def _as_float(name, value):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _require_positive(name, value):
    out = _as_float(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _require_non_negative(name, value):
    out = _as_float(name, value)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def net_charging_current_density(
    electron_flux_density_a_m2,
    secondary_yield=0.0,
    backscatter_yield=0.0,
    ion_flux_density_a_m2=0.0,
    photoemission_density_a_m2=0.0,
):
    """Signed net current density (A/m^2) driving the dielectric.

    Positive means net electron collection (the surface drives negative).
    Negative means emission and ion collection dominate.
    """
    j_e = _require_positive("electron_flux_density_a_m2", electron_flux_density_a_m2)
    delta = _require_non_negative("secondary_yield", secondary_yield)
    eta = _require_non_negative("backscatter_yield", backscatter_yield)
    j_i = _require_non_negative("ion_flux_density_a_m2", ion_flux_density_a_m2)
    j_ph = _require_non_negative("photoemission_density_a_m2", photoemission_density_a_m2)
    if delta > 10.0:
        raise ValueError("secondary_yield %r is outside any physical range" % (secondary_yield,))
    if eta > 1.0:
        raise ValueError("backscatter_yield %r cannot exceed 1.0" % (backscatter_yield,))
    return j_e * (1.0 - delta - eta) - j_i - j_ph


def bounding_charging_current_density(
    electron_flux_density_a_m2,
    secondary_yield=0.0,
    backscatter_yield=0.0,
    ion_flux_density_a_m2=0.0,
    photoemission_density_a_m2=0.0,
):
    """Magnitude of the net current density used to derive the ceiling.

    Raises ValueError when the environment terms cancel: an environment with
    no net driver cannot produce a resistivity ceiling, which is an input
    defect rather than a pass.
    """
    net = net_charging_current_density(
        electron_flux_density_a_m2,
        secondary_yield=secondary_yield,
        backscatter_yield=backscatter_yield,
        ion_flux_density_a_m2=ion_flux_density_a_m2,
        photoemission_density_a_m2=photoemission_density_a_m2,
    )
    magnitude = abs(net)
    if magnitude <= abs(electron_flux_density_a_m2) * REL_TOL:
        raise ValueError(
            "net charging current density is zero; no resistivity ceiling can be derived"
        )
    return magnitude


def maximum_bulk_resistivity(allowable_potential_v, current_density_a_m2, thickness_m):
    """Bulk-resistivity ceiling in ohm*m: V_allow / (J * t)."""
    v = _require_positive("allowable_potential_v", allowable_potential_v)
    j = _require_positive("current_density_a_m2", current_density_a_m2)
    t = _require_positive("thickness_m", thickness_m)
    return v / (j * t)


def maximum_sheet_resistivity(allowable_potential_v, current_density_a_m2, bleed_path_length_m):
    """Sheet-resistivity ceiling in ohm/square: 2 * V_allow / (J * L^2)."""
    v = _require_positive("allowable_potential_v", allowable_potential_v)
    j = _require_positive("current_density_a_m2", current_density_a_m2)
    length = _require_positive("bleed_path_length_m", bleed_path_length_m)
    return 2.0 * v / (j * length * length)


def bulk_potential_drop(resistivity_ohm_m, current_density_a_m2, thickness_m):
    """Differential potential (V) sustained through the dielectric thickness."""
    rho = _require_positive("resistivity_ohm_m", resistivity_ohm_m)
    j = _require_positive("current_density_a_m2", current_density_a_m2)
    t = _require_positive("thickness_m", thickness_m)
    return rho * j * t


def sheet_potential_drop(sheet_resistivity_ohm_sq, current_density_a_m2, bleed_path_length_m):
    """Differential potential (V) accumulated along a coating bleed path."""
    rho_s = _require_positive("sheet_resistivity_ohm_sq", sheet_resistivity_ohm_sq)
    j = _require_positive("current_density_a_m2", current_density_a_m2)
    length = _require_positive("bleed_path_length_m", bleed_path_length_m)
    return rho_s * j * length * length / 2.0


def maximum_dielectric_thickness(resistivity_ohm_m, current_density_a_m2, allowable_potential_v):
    """Largest thickness (m) a given material may have and still comply."""
    rho = _require_positive("resistivity_ohm_m", resistivity_ohm_m)
    j = _require_positive("current_density_a_m2", current_density_a_m2)
    v = _require_positive("allowable_potential_v", allowable_potential_v)
    return v / (rho * j)


def resistivity_margin(resistivity, ceiling):
    """Fractional margin to the ceiling: ceiling / resistivity - 1.

    Zero means exactly at the ceiling, positive means below it (compliant),
    negative means above it.
    """
    rho = _require_positive("resistivity", resistivity)
    ceil_value = _require_positive("ceiling", ceiling)
    return ceil_value / rho - 1.0


def categorize_resistivity_regime(resistivity_ohm_m):
    """Descriptive regime for a bulk resistivity (review aid, not a verdict)."""
    rho = _require_positive("resistivity_ohm_m", resistivity_ohm_m)
    if rho < CONDUCTIVE_REGIME_MAX_OHM_M:
        return "conductive"
    if rho < DISSIPATIVE_REGIME_MAX_OHM_M:
        return "static-dissipative"
    return "insulating"


def within_ceiling(value, ceiling):
    """True when value <= ceiling, absorbing float representation error.

    The comparison uses a relative tolerance so a case that is physically at
    the ceiling is not failed by a few ULPs of drift in a quotient of powers
    of ten. The ceiling itself is unchanged.
    """
    v = _require_non_negative("value", value)
    ceil_value = _require_positive("ceiling", ceiling)
    if v <= ceil_value:
        return True
    return math.isclose(v, ceil_value, rel_tol=REL_TOL, abs_tol=0.0)


def evaluate_dielectric(item, current_density_a_m2, default_allowable_potential_v=None):
    """Evaluate one dielectric item against its derived clause 6.2.2 ceiling.

    item keys: id, resistivity_ohm_m, thickness_m, and optionally
    allowable_potential_v, coating_sheet_resistivity_ohm_sq,
    bleed_path_length_m.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (type(item).__name__,))
    unknown = sorted(set(item) - _KNOWN_ITEM_KEYS)
    if unknown:
        raise ValueError("item has unknown keys: %s" % ", ".join(unknown))
    for key in _REQUIRED_ITEM_KEYS:
        if key not in item:
            raise ValueError("item is missing required key '%s'" % key)
    item_id = item["id"]
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("item id must be a non-empty string, got %r" % (item_id,))

    j = _require_positive("current_density_a_m2", current_density_a_m2)
    allowable = item.get("allowable_potential_v", default_allowable_potential_v)
    if allowable is None:
        raise ValueError(
            "item '%s' has no allowable_potential_v and no default was supplied" % item_id
        )
    v_allow = _require_positive("allowable_potential_v", allowable)

    rho = _require_positive("resistivity_ohm_m", item["resistivity_ohm_m"])
    thickness = _require_positive("thickness_m", item["thickness_m"])

    bulk_ceiling = maximum_bulk_resistivity(v_allow, j, thickness)
    bulk_ok = within_ceiling(rho, bulk_ceiling)

    result = {
        "id": item_id,
        "regime": categorize_resistivity_regime(rho),
        "bulk_ceiling_ohm_m": bulk_ceiling,
        "bulk_potential_v": bulk_potential_drop(rho, j, thickness),
        "bulk_margin": resistivity_margin(rho, bulk_ceiling),
        "bulk_within_ceiling": bulk_ok,
        "sheet_ceiling_ohm_sq": None,
        "sheet_potential_v": None,
        "sheet_within_ceiling": None,
        "findings": [],
    }

    coating = item.get("coating_sheet_resistivity_ohm_sq")
    length = item.get("bleed_path_length_m")
    if (coating is None) != (length is None):
        raise ValueError(
            "item '%s' must declare coating_sheet_resistivity_ohm_sq and "
            "bleed_path_length_m together" % item_id
        )
    coating_ok = None
    if coating is not None:
        rho_s = _require_positive("coating_sheet_resistivity_ohm_sq", coating)
        path = _require_positive("bleed_path_length_m", length)
        sheet_ceiling = maximum_sheet_resistivity(v_allow, j, path)
        coating_ok = within_ceiling(rho_s, sheet_ceiling)
        result["sheet_ceiling_ohm_sq"] = sheet_ceiling
        result["sheet_potential_v"] = sheet_potential_drop(rho_s, j, path)
        result["sheet_within_ceiling"] = coating_ok

    if bulk_ok:
        result["disposition"] = "compliant"
    elif coating_ok is True:
        result["disposition"] = "mitigated-by-bleed-path"
        result["findings"].append(
            "bulk resistivity above ceiling; drained by a compliant conductive coating"
        )
    elif coating_ok is False:
        result["disposition"] = "ceiling-exceeded"
        result["findings"].append("bulk resistivity above ceiling")
        result["findings"].append("declared conductive coating is itself above its sheet ceiling")
    else:
        result["disposition"] = "ceiling-exceeded"
        result["findings"].append("bulk resistivity above ceiling; no bleed path declared")
    return result


def assess_dielectric_inventory(items, current_density_a_m2, default_allowable_potential_v=None):
    """Aggregate clause 6.2.2 verdicts over an inventory of dielectrics."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list or tuple")
    if not items:
        raise ValueError("items must not be empty")
    evaluations = []
    seen = set()
    for item in items:
        evaluation = evaluate_dielectric(
            item, current_density_a_m2, default_allowable_potential_v=default_allowable_potential_v
        )
        if evaluation["id"] in seen:
            raise ValueError("duplicate item id '%s'" % evaluation["id"])
        seen.add(evaluation["id"])
        evaluations.append(evaluation)

    counts = {"compliant": 0, "mitigated-by-bleed-path": 0, "ceiling-exceeded": 0}
    for evaluation in evaluations:
        counts[evaluation["disposition"]] += 1
    worst = min(evaluations, key=lambda e: e["bulk_margin"])
    return {
        "evaluations": evaluations,
        "counts": counts,
        "worst_margin_id": worst["id"],
        "worst_margin": worst["bulk_margin"],
        "compliant": counts["ceiling-exceeded"] == 0,
    }
