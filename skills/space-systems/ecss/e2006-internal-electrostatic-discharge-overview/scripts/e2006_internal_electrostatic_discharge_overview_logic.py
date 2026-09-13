#!/usr/bin/env python3
"""Internal-electrostatic-discharge provisions, ECSS-E-ST-20-06C clause 9.1.

Deterministic, offline, stdlib-only implementation of the clause 9.1 entry
point: energetic electrons penetrate the outer shell, stop inside insulators
and inside ungrounded metal, and build a buried charge that later relaxes as
an internal discharge right next to the electronics. The clause sets the
general provisions for those internal parts and materials and the validation
provisions that close them out.

The procedure implemented here is a paraphrase of the engineering intent, not
of the standard text. The clause is cited as an anchor only.
"""

import math

__all__ = [
    "LIMIT_REL_TOL",
    "SCREENING_FLUX_PA_CM2",
    "INTERNAL_FIELD_LIMIT_V_PER_M",
    "STORED_ENERGY_LIMIT_J",
    "BLEED_TAU_FRACTION",
    "ITEM_CATEGORIES",
    "VALIDATION_METHODS",
    "validate_deep_charging_environment",
    "attenuated_flux_pa_cm2",
    "is_below_screening_threshold",
    "effective_resistivity_ohm_m",
    "steady_state_internal_field_v_per_m",
    "floating_conductor_potential_v",
    "stored_discharge_energy_j",
    "bleed_time_constant_s",
    "categorize_internal_item",
    "verify_validation_provision",
    "evaluate_internal_item",
    "assess_internal_esd_provisions",
]

#: Relative tolerance that absorbs floating-point representation error at an
#: exactly-compliant limit. It does NOT widen any engineering limit: a value
#: mathematically equal to the limit that lands a few ULPs above it after a
#: unit conversion and a product still reads as compliant.
LIMIT_REL_TOL = 1e-9

# Flux is carried in picoamperes per square centimetre, the unit internal
# charging screening is usually argued in.
PA_CM2_TO_A_M2 = 1.0e-8

# Below this penetrating flux an item cannot accumulate enough buried charge
# to matter over a mission, whatever its resistivity.
SCREENING_FLUX_PA_CM2 = 0.1

# Attenuation length of the penetrating electron population in aluminium.
SHIELD_ATTENUATION_LENGTH_MM = 0.75

# Buried-charge field a dielectric may hold before an internal discharge is
# credible. Sits below intrinsic breakdown, which is the point of the margin.
INTERNAL_FIELD_LIMIT_V_PER_M = 1.0e7

# Energy an internal discharge may release before it is treated as able to
# upset or damage the electronics next to it.
STORED_ENERGY_LIMIT_J = 1.0e-6

# A grounded part is only grounded for this purpose if its bleed path drains
# charge fast compared with the exposure it accumulates over.
BLEED_TAU_FRACTION = 0.01

# Radiation-induced conductivity: a dielectric under flux conducts better
# than the same dielectric in the dark, which is what keeps real hardware
# below the field limit.
RIC_SENSITIVITY_PER_PA_CM2 = 2.0

ITEM_CATEGORIES = ("bulk-dielectric", "ungrounded-conductor", "grounded-conductor")

VALIDATION_METHODS = (
    "electron-beam-exposure-test",
    "deep-charging-analysis",
    "grounding-continuity-inspection",
    "similarity-to-qualified-design",
)

# Which validation provision actually closes which category.
_ACCEPTED_METHODS = {
    "bulk-dielectric": {"electron-beam-exposure-test", "deep-charging-analysis"},
    "ungrounded-conductor": {
        "electron-beam-exposure-test",
        "similarity-to-qualified-design",
    },
    "grounded-conductor": {
        "grounding-continuity-inspection",
        "deep-charging-analysis",
    },
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(value, label):
    out = _require_number(value, label)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _require_non_negative(value, label):
    out = _require_number(value, label)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return out


def _not_above(value, limit):
    """True when value is at or below limit, tolerating representation error."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=LIMIT_REL_TOL, abs_tol=0.0)


def validate_deep_charging_environment(env):
    """Validate the penetrating-electron environment the item lives in."""
    if not isinstance(env, dict):
        raise ValueError("environment must be a mapping, got %r" % (env,))
    flux = _require_positive(
        env.get("incident_flux_pa_cm2"), "incident_flux_pa_cm2"
    )
    duration = _require_positive(
        env.get("exposure_duration_s"), "exposure_duration_s"
    )
    return {"incident_flux_pa_cm2": flux, "exposure_duration_s": duration}


def attenuated_flux_pa_cm2(incident_flux_pa_cm2, shield_thickness_mm):
    """Penetrating flux left after the shell and local shielding."""
    flux = _require_positive(incident_flux_pa_cm2, "incident_flux_pa_cm2")
    thickness = _require_non_negative(shield_thickness_mm, "shield_thickness_mm")
    return flux * math.exp(-thickness / SHIELD_ATTENUATION_LENGTH_MM)


def is_below_screening_threshold(flux_pa_cm2):
    """True when the item screens out of the deep-charging assessment."""
    flux = _require_non_negative(flux_pa_cm2, "flux_pa_cm2")
    return _not_above(flux, SCREENING_FLUX_PA_CM2)


def effective_resistivity_ohm_m(dark_resistivity_ohm_m, flux_pa_cm2):
    """Dark resistivity reduced by the radiation-induced conductivity."""
    rho = _require_positive(dark_resistivity_ohm_m, "dark_resistivity_ohm_m")
    flux = _require_non_negative(flux_pa_cm2, "flux_pa_cm2")
    return rho / (1.0 + RIC_SENSITIVITY_PER_PA_CM2 * flux)


def steady_state_internal_field_v_per_m(flux_pa_cm2, resistivity_ohm_m):
    """Buried-charge field where deposition balances conduction away."""
    flux = _require_non_negative(flux_pa_cm2, "flux_pa_cm2")
    rho = _require_positive(resistivity_ohm_m, "resistivity_ohm_m")
    return flux * PA_CM2_TO_A_M2 * rho


def floating_conductor_potential_v(flux_pa_cm2, area_m2, capacitance_f, duration_s):
    """Potential an ungrounded conductor reaches with no path to bleed off."""
    flux = _require_non_negative(flux_pa_cm2, "flux_pa_cm2")
    area = _require_positive(area_m2, "area_m2")
    capacitance = _require_positive(capacitance_f, "capacitance_f")
    duration = _require_non_negative(duration_s, "duration_s")
    charge = flux * PA_CM2_TO_A_M2 * area * duration
    return charge / capacitance


def stored_discharge_energy_j(capacitance_f, potential_v):
    """Energy an internal discharge would dump when that potential relaxes."""
    capacitance = _require_positive(capacitance_f, "capacitance_f")
    potential = _require_number(potential_v, "potential_v")
    return 0.5 * capacitance * potential * potential


def bleed_time_constant_s(resistance_ohm, capacitance_f):
    """Time constant of the bleed path that is supposed to keep a part safe."""
    resistance = _require_positive(resistance_ohm, "resistance_ohm")
    capacitance = _require_positive(capacitance_f, "capacitance_f")
    return resistance * capacitance


def categorize_internal_item(item):
    """Validate one internal part or material and normalize its record."""
    if not isinstance(item, dict):
        raise ValueError("internal item must be a mapping, got %r" % (item,))
    item_id = item.get("item_id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("internal item needs a non-empty item_id")
    category = item.get("category")
    if category not in ITEM_CATEGORIES:
        raise ValueError(
            "item %s has uncategorized category %r; known: %s"
            % (item_id, category, ", ".join(ITEM_CATEGORIES))
        )
    record = {
        "item_id": item_id,
        "category": category,
        "shield_thickness_mm": _require_non_negative(
            item.get("shield_thickness_mm", 0.0),
            "shield_thickness_mm of item %s" % item_id,
        ),
    }
    if category == "bulk-dielectric":
        record["dark_resistivity_ohm_m"] = _require_positive(
            item.get("dark_resistivity_ohm_m"),
            "dark_resistivity_ohm_m of item %s" % item_id,
        )
    else:
        record["area_m2"] = _require_positive(
            item.get("area_m2"), "area_m2 of item %s" % item_id
        )
        record["capacitance_f"] = _require_positive(
            item.get("capacitance_f"), "capacitance_f of item %s" % item_id
        )
        if category == "grounded-conductor":
            record["bond_resistance_ohm"] = _require_positive(
                item.get("bond_resistance_ohm"),
                "bond_resistance_ohm of item %s" % item_id,
            )
    return record


def verify_validation_provision(item, category):
    """Check the recorded validation provision suits the item category."""
    if category not in _ACCEPTED_METHODS:
        raise ValueError("uncategorized category %r" % (category,))
    provision = item.get("validation") if isinstance(item, dict) else None
    if provision is None:
        return ["no validation provision on record for clause 9.1"]
    if not isinstance(provision, dict):
        raise ValueError("validation must be a mapping or None, got %r" % (provision,))
    method = provision.get("method")
    if method not in VALIDATION_METHODS:
        raise ValueError(
            "uncategorized validation method %r; known: %s"
            % (method, ", ".join(VALIDATION_METHODS))
        )
    findings = []
    reference = provision.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        findings.append("validation method %s carries no report reference" % method)
    if method not in _ACCEPTED_METHODS[category]:
        findings.append(
            "validation method %s does not close a %s" % (method, category)
        )
    return findings


def evaluate_internal_item(item, env):
    """Run the clause 9.1 evaluation for one internal part or material."""
    record = categorize_internal_item(item)
    plasma = validate_deep_charging_environment(env)
    flux = attenuated_flux_pa_cm2(
        plasma["incident_flux_pa_cm2"], record["shield_thickness_mm"]
    )
    record["penetrating_flux_pa_cm2"] = flux
    record["exposure_duration_s"] = plasma["exposure_duration_s"]
    findings = []
    if is_below_screening_threshold(flux):
        record["screened_out"] = True
        record["findings"] = findings
        record["compliant"] = True
        return record
    record["screened_out"] = False
    if record["category"] == "bulk-dielectric":
        rho = effective_resistivity_ohm_m(record["dark_resistivity_ohm_m"], flux)
        field = steady_state_internal_field_v_per_m(flux, rho)
        record["effective_resistivity_ohm_m"] = rho
        record["internal_field_v_per_m"] = field
        record["field_margin_v_per_m"] = INTERNAL_FIELD_LIMIT_V_PER_M - field
        if not _not_above(field, INTERNAL_FIELD_LIMIT_V_PER_M):
            findings.append(
                "item %s holds %.3e V/m, above the %.3e V/m internal-field limit"
                % (record["item_id"], field, INTERNAL_FIELD_LIMIT_V_PER_M)
            )
    else:
        if record["category"] == "grounded-conductor":
            tau = bleed_time_constant_s(
                record["bond_resistance_ohm"], record["capacitance_f"]
            )
            tau_limit = BLEED_TAU_FRACTION * plasma["exposure_duration_s"]
            record["bleed_time_constant_s"] = tau
            record["bleed_tau_limit_s"] = tau_limit
            bleeds = _not_above(tau, tau_limit)
            record["bleed_path_adequate"] = bleeds
            if not bleeds:
                findings.append(
                    "item %s bleeds with tau %.3e s, slower than the %.3e s limit"
                    % (record["item_id"], tau, tau_limit)
                )
            duration = plasma["exposure_duration_s"] if not bleeds else tau
        else:
            record["bleed_path_adequate"] = False
            duration = plasma["exposure_duration_s"]
        potential = floating_conductor_potential_v(
            flux, record["area_m2"], record["capacitance_f"], duration
        )
        energy = stored_discharge_energy_j(record["capacitance_f"], potential)
        record["floating_potential_v"] = potential
        record["stored_energy_j"] = energy
        record["energy_margin_j"] = STORED_ENERGY_LIMIT_J - energy
        if not _not_above(energy, STORED_ENERGY_LIMIT_J):
            findings.append(
                "item %s stores %.3e J, above the %.3e J discharge-energy limit"
                % (record["item_id"], energy, STORED_ENERGY_LIMIT_J)
            )
    findings.extend(verify_validation_provision(item, record["category"]))
    record["findings"] = findings
    record["compliant"] = not findings
    return record


def assess_internal_esd_provisions(items, env):
    """Roll every internal part up into one clause 9.1 verdict."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("assess_internal_esd_provisions needs a non-empty item list")
    plasma = validate_deep_charging_environment(env)
    results = [evaluate_internal_item(item, plasma) for item in items]
    non_compliant = [r["item_id"] for r in results if not r["compliant"]]
    screened = [r["item_id"] for r in results if r["screened_out"]]
    return {
        "assessed": len(results),
        "item_results": results,
        "screened_out": screened,
        "non_compliant": non_compliant,
        "clause_9_1_met": not non_compliant,
    }
