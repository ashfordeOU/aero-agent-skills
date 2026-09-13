#!/usr/bin/env python3
"""Electromagnetic radiation hazard logic (ECSS-E-ST-20-07C clause 4.2.7).

Deterministic, offline, Python standard library only.

Clause 4.2.7 requires the evaluation of the hazards a radiated
radio-frequency field presents, and requires that evaluation to feed the
hazard-analysis process run by product assurance rather than stand alone.
This module implements that as a checkable procedure:

1. the receptor is categorized into one of three families (ordnance,
   ground crew, propellant vapour), each with its own governing quantity and
   safety margin;
2. the near-field boundary of the emitting aperture is computed, and a
   receptor standing inside it is returned as near-field-invalid rather than
   evaluated with a far-field relation that does not hold there;
3. beyond the boundary the incident field strength and power flux density
   are computed from radiated power, antenna gain and stand-off distance;
4. the family threshold is derated by the family safety margin and compared
   with the computed quantity, and the safe separation distance is derived;
5. the hazard-analysis linkage is checked: identifier, severity category and
   independent-inhibit count.

Units: power in watts, gain in decibels relative to an isotropic radiator,
distance and aperture in metres, frequency in hertz, field strength in volts
per metre, power flux density in watts per square metre. No standard text is
reproduced.
"""

import math

__all__ = [
    "SPEED_OF_LIGHT_M_S",
    "RECEPTOR_FAMILIES",
    "SEVERITY_INHIBITS",
    "COMPARISON_TOLERANCE",
    "linear_gain",
    "wavelength_m",
    "near_field_boundary_m",
    "field_strength_v_per_m",
    "power_flux_density_w_per_m2",
    "categorize_receptor",
    "derated_allowable",
    "safe_separation_distance_m",
    "check_hazard_analysis_linkage",
    "evaluate_radiation_hazard_case",
    "assess_electromagnetic_radiation_hazards",
]

SPEED_OF_LIGHT_M_S = 299792458.0

# Governing quantity and default safety margin per receptor family.
# "field" families are bounded by incident field strength (an amplitude
# quantity, derated over twenty decades-of-amplitude); "flux" families are
# bounded by power flux density (a power quantity, derated over ten).
RECEPTOR_FAMILIES = {
    "electro-explosive-device": {"quantity": "field", "margin_db": 20.0},
    "propellant-vapour": {"quantity": "field", "margin_db": 6.0},
    "ground-crew": {"quantity": "flux", "margin_db": 10.0},
}

# Independent inhibits the product-assurance hazard-analysis expects for each
# severity category.
SEVERITY_INHIBITS = {
    "catastrophic": 2,
    "critical": 2,
    "major": 1,
    "minor": 0,
}

# Relative tolerance used when a computed quantity lands exactly on a derated
# allowable. Sums, square roots and decade conversions can put a physically
# compliant case a few ULPs the wrong side of the comparison; this absorbs
# the representation error without moving the engineering threshold.
COMPARISON_TOLERANCE = 1e-12


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


def _within(value, allowable):
    """True when value <= allowable, absorbing float representation error."""
    return value < allowable or math.isclose(
        value, allowable, rel_tol=COMPARISON_TOLERANCE, abs_tol=0.0
    )


def linear_gain(gain_dbi):
    """Convert antenna gain in decibels-isotropic to a linear power ratio."""
    gain = _as_float(gain_dbi, "gain_dbi")
    return 10.0 ** (gain / 10.0)


def wavelength_m(frequency_hz):
    """Free-space wavelength at the emitter frequency."""
    freq = _positive(frequency_hz, "frequency_hz")
    return SPEED_OF_LIGHT_M_S / freq


def near_field_boundary_m(aperture_m, frequency_hz):
    """Distance beyond which the far-field relations may be used.

    Taken as the largest of the radiating near-field boundary (twice the
    squared aperture dimension over the wavelength), the reactive near-field
    boundary, and one wavelength over two pi. Raises ValueError on a
    non-positive aperture or frequency.
    """
    aperture = _positive(aperture_m, "aperture_m")
    lam = wavelength_m(frequency_hz)
    radiating = 2.0 * aperture * aperture / lam
    reactive = 0.62 * math.sqrt(aperture ** 3 / lam)
    return max(radiating, reactive, lam / (2.0 * math.pi))


def field_strength_v_per_m(power_w, gain_dbi, distance_m):
    """Incident field strength of a far-field radiated beam."""
    power = _positive(power_w, "power_w")
    distance = _positive(distance_m, "distance_m")
    gain = linear_gain(gain_dbi)
    return math.sqrt(30.0 * power * gain) / distance


def power_flux_density_w_per_m2(power_w, gain_dbi, distance_m):
    """Power flux density of a far-field radiated beam."""
    power = _positive(power_w, "power_w")
    distance = _positive(distance_m, "distance_m")
    gain = linear_gain(gain_dbi)
    return power * gain / (4.0 * math.pi * distance * distance)


def categorize_receptor(receptor_type):
    """Return the family record for a receptor type.

    Raises ValueError for a receptor type outside the three families this
    procedure covers; an uncategorized receptor is not evaluated.
    """
    if not isinstance(receptor_type, str):
        raise ValueError("receptor_type must be a string, got %r" % (receptor_type,))
    key = receptor_type.strip().lower()
    if key not in RECEPTOR_FAMILIES:
        raise ValueError(
            "uncategorized receptor type %r; expected one of %s"
            % (receptor_type, ", ".join(sorted(RECEPTOR_FAMILIES)))
        )
    record = dict(RECEPTOR_FAMILIES[key])
    record["receptor_type"] = key
    return record


def derated_allowable(threshold, margin_db, quantity):
    """Threshold pulled down by the safety margin.

    quantity "field" derates over twenty (amplitude), "flux" over ten
    (power). Raises ValueError on a non-positive threshold, a negative
    margin or an unknown quantity.
    """
    value = _positive(threshold, "threshold")
    margin = _as_float(margin_db, "margin_db")
    if margin < 0.0:
        raise ValueError("margin_db must be non-negative, got %r" % (margin,))
    if quantity == "field":
        decades = 20.0
    elif quantity == "flux":
        decades = 10.0
    else:
        raise ValueError("quantity must be 'field' or 'flux', got %r" % (quantity,))
    return value * 10.0 ** (-margin / decades)


def safe_separation_distance_m(power_w, gain_dbi, allowable, quantity):
    """Stand-off distance at which the computed quantity meets the allowable.

    Raises ValueError on a non-positive allowable or an unknown quantity.
    """
    power = _positive(power_w, "power_w")
    limit = _positive(allowable, "allowable")
    gain = linear_gain(gain_dbi)
    if quantity == "field":
        return math.sqrt(30.0 * power * gain) / limit
    if quantity == "flux":
        return math.sqrt(power * gain / (4.0 * math.pi * limit))
    raise ValueError("quantity must be 'field' or 'flux', got %r" % (quantity,))


def check_hazard_analysis_linkage(receptor):
    """Findings against the product-assurance hazard-analysis linkage.

    Returns a list of finding strings, empty when the linkage is complete.
    Raises ValueError when the inhibit count is not a non-negative integer.
    """
    findings = []
    report_id = receptor.get("hazard_report_id")
    if not report_id or not str(report_id).strip():
        findings.append(
            "no hazard-report identifier on record; clause 4.2.7 requires the "
            "case to appear in the product-assurance hazard-analysis"
        )
    severity = receptor.get("severity")
    severity_key = severity.strip().lower() if isinstance(severity, str) else None
    if severity_key not in SEVERITY_INHIBITS:
        findings.append(
            "severity category %r is not one of %s"
            % (severity, ", ".join(sorted(SEVERITY_INHIBITS)))
        )
        return findings
    inhibits = receptor.get("independent_inhibits", 0)
    if isinstance(inhibits, bool) or not isinstance(inhibits, int):
        raise ValueError(
            "independent_inhibits must be an integer, got %r" % (inhibits,)
        )
    if inhibits < 0:
        raise ValueError(
            "independent_inhibits must be non-negative, got %r" % (inhibits,)
        )
    required = SEVERITY_INHIBITS[severity_key]
    if inhibits < required:
        findings.append(
            "severity %s requires %d independent inhibit(s), %d on record"
            % (severity_key, required, inhibits)
        )
    return findings


def evaluate_radiation_hazard_case(emitter, receptor):
    """Evaluate one emitter against one receptor.

    emitter:  power_w, gain_dbi, frequency_hz, aperture_m, optional id.
    receptor: receptor_type, threshold, distance_m, optional margin_db,
              hazard_report_id, severity, independent_inhibits.

    Status is one of "near-field-invalid", "compliant", "exceeded".
    Raises ValueError on malformed input.
    """
    for key in ("power_w", "gain_dbi", "frequency_hz", "aperture_m"):
        if key not in emitter:
            raise ValueError("emitter entry missing '%s'" % key)
    for key in ("receptor_type", "threshold", "distance_m"):
        if key not in receptor:
            raise ValueError("receptor entry missing '%s'" % key)

    family = categorize_receptor(receptor["receptor_type"])
    quantity = family["quantity"]
    margin_db = receptor.get("margin_db", family["margin_db"])
    distance = _positive(receptor["distance_m"], "distance_m")
    power = _positive(emitter["power_w"], "power_w")
    gain_dbi = _as_float(emitter["gain_dbi"], "gain_dbi")
    boundary = near_field_boundary_m(emitter["aperture_m"], emitter["frequency_hz"])

    result = {
        "emitter_id": emitter.get("emitter_id", "emitter"),
        "receptor_id": receptor.get("receptor_id", family["receptor_type"]),
        "receptor_type": family["receptor_type"],
        "quantity": quantity,
        "margin_db": margin_db,
        "distance_m": distance,
        "near_field_boundary_m": boundary,
        "linkage_findings": check_hazard_analysis_linkage(receptor),
    }

    if distance < boundary:
        result.update(
            {
                "status": "near-field-invalid",
                "computed": None,
                "allowable": None,
                "safe_separation_m": None,
                "finding": (
                    "receptor stands %.3f m from the aperture, inside the "
                    "%.3f m near-field boundary; a far-field relation does "
                    "not apply and measurement is required"
                    % (distance, boundary)
                ),
            }
        )
        return result

    allowable = derated_allowable(receptor["threshold"], margin_db, quantity)
    if quantity == "field":
        computed = field_strength_v_per_m(power, gain_dbi, distance)
    else:
        computed = power_flux_density_w_per_m2(power, gain_dbi, distance)
    safe_distance = safe_separation_distance_m(power, gain_dbi, allowable, quantity)

    result.update(
        {
            "computed": computed,
            "allowable": allowable,
            "safe_separation_m": safe_distance,
            "separation_shortfall_m": max(0.0, safe_distance - distance),
        }
    )
    if _within(computed, allowable):
        result["status"] = "compliant"
        result["finding"] = None
    else:
        result["status"] = "exceeded"
        result["finding"] = (
            "incident %s of %.6g exceeds the derated allowable %.6g; the "
            "layout needs %.3f m of separation, %.3f m available"
            % (quantity, computed, allowable, safe_distance, distance)
        )
    return result


def assess_electromagnetic_radiation_hazards(emitter, receptors):
    """Assess one emitter against every declared receptor.

    Returns a mapping with per-case results, the findings split by kind and an
    overall verdict. Raises ValueError on an empty receptor set or duplicate
    receptor identifiers.
    """
    case_list = list(receptors or [])
    if not case_list:
        raise ValueError("at least one receptor is required")
    seen = set()
    results = []
    for index, receptor in enumerate(case_list):
        if not isinstance(receptor, dict):
            raise ValueError("receptor %d must be a mapping" % index)
        ident = receptor.get("receptor_id", receptor.get("receptor_type"))
        if ident in seen:
            raise ValueError("duplicate receptor identifier %r" % (ident,))
        seen.add(ident)
        results.append(evaluate_radiation_hazard_case(emitter, receptor))

    near_field = [r for r in results if r["status"] == "near-field-invalid"]
    exceeded = [r for r in results if r["status"] == "exceeded"]
    linkage = [r for r in results if r["linkage_findings"]]
    return {
        "cases": results,
        "near_field_invalid": near_field,
        "exceeded_cases": exceeded,
        "linkage_gaps": linkage,
        "hazard_compliant": not near_field and not exceeded and not linkage,
    }
