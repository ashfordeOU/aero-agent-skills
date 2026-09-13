#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 6.3.3.5 -- conductive-coating thickness budget.

Deterministic, offline, stdlib-only support for the rule that a conductive
coating applied to an externally exposed surface is laid down thick enough to
keep conducting after the erosion expected across the whole mission, not just
on the day it leaves the coating shop.

The module carries four pieces:

1. a small coating register giving, per coating family, the bulk resistivity
   of the deposited layer and the continuity floor below which the layer stops
   behaving as a continuous conductive film;
2. depth-loss models for the erosion mechanisms that thin an external coating
   -- atomic-oxygen recession, ion-sputtering, and any mechanism supplied as a
   linear rate per year (particulate-abrasion, handling-wear);
3. the end-of-life state: as-deposited thickness minus the accumulated loss
   scaled by an erosion-uncertainty factor, and the sheet resistance that
   surviving thickness delivers;
4. the verdict: the coating passes only when the surviving layer clears both
   the continuity floor and the sheet-resistance ceiling, and the module also
   reports the as-deposited thickness that would have been needed.

Thicknesses are in nanometres, resistivities in ohm-metres, sheet resistances
in ohm per square. Thresholds are module constants so a project can
re-baseline them without editing the procedure.
"""

import math

# Bulk resistivity of the deposited layer (ohm-metre) and the continuity floor
# (nanometre) below which the film loses its continuous conductive path.
COATING_REGISTER = {
    "indium-tin-oxide": {"bulk_resistivity_ohm_m": 5.0e-6, "continuity_floor_nm": 20.0},
    "vapour-deposited-aluminium": {
        "bulk_resistivity_ohm_m": 3.0e-8,
        "continuity_floor_nm": 30.0,
    },
    "gold-flash": {"bulk_resistivity_ohm_m": 2.4e-8, "continuity_floor_nm": 25.0},
    "germanium-on-polyimide": {
        "bulk_resistivity_ohm_m": 5.0e-2,
        "continuity_floor_nm": 50.0,
    },
    "conductive-black-paint": {
        "bulk_resistivity_ohm_m": 1.0e-1,
        "continuity_floor_nm": 20000.0,
    },
}

# Ceiling on the end-of-life sheet resistance of an external bleed surface.
ALLOWABLE_SHEET_RESISTANCE_OHM_SQ = 1.0e9

# Multiplier applied to the summed depth loss to cover model and environment
# spread; a project may raise it but never take it below unity.
DEFAULT_EROSION_UNCERTAINTY_FACTOR = 1.5
MIN_EROSION_UNCERTAINTY_FACTOR = 1.0

# Absolute tolerance in nanometres absorbing the representation error of a
# subtraction, so a layer that lands exactly on the floor is not read as under.
THICKNESS_TOLERANCE_NM = 1.0e-9

# Relative tolerance on the sheet-resistance comparison, same reasoning.
SHEET_RESISTANCE_REL_TOLERANCE = 1.0e-12

CM_TO_NM = 1.0e7
M_TO_NM = 1.0e9

LINEAR_MECHANISMS = ("particulate-abrasion", "handling-wear")
MECHANISM_TYPES = ("atomic-oxygen", "ion-sputtering") + LINEAR_MECHANISMS


def _number(record, key, label, minimum=None, strict=False):
    """Return a finite float field, enforcing an optional lower bound."""
    if key not in record:
        raise ValueError("%s missing required '%s'" % (label, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s '%s' must be numeric, got %r" % (label, key, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s '%s' must be finite, got %r" % (label, key, value))
    if minimum is not None:
        if strict and value <= minimum:
            raise ValueError("%s '%s' must be > %g, got %r" % (label, key, minimum, value))
        if not strict and value < minimum:
            raise ValueError("%s '%s' must be >= %g, got %r" % (label, key, minimum, value))
    return value


def coating_properties(material):
    """Return the register entry for a coating family."""
    if not isinstance(material, str) or not material.strip():
        raise ValueError("coating material must be a non-empty name")
    key = material.strip().lower()
    if key not in COATING_REGISTER:
        raise ValueError(
            "coating '%s' is not in the register %s"
            % (material, sorted(COATING_REGISTER))
        )
    entry = COATING_REGISTER[key]
    return {
        "material": key,
        "bulk_resistivity_ohm_m": entry["bulk_resistivity_ohm_m"],
        "continuity_floor_nm": entry["continuity_floor_nm"],
    }


def atomic_oxygen_recession_nm(fluence_atoms_per_cm2, erosion_yield_cm3_per_atom):
    """Depth removed by atomic-oxygen recession, in nanometres."""
    values = {"fluence": fluence_atoms_per_cm2, "yield": erosion_yield_cm3_per_atom}
    fluence = _number(values, "fluence", "atomic-oxygen", minimum=0.0)
    yield_ = _number(values, "yield", "atomic-oxygen", minimum=0.0, strict=True)
    return fluence * yield_ * CM_TO_NM


def sputter_recession_nm(
    ion_flux_per_cm2_s, sputter_yield_atoms_per_ion, duration_s, atomic_volume_cm3
):
    """Depth removed by ion-sputtering over an exposure duration, in nanometres."""
    values = {
        "flux": ion_flux_per_cm2_s,
        "yield": sputter_yield_atoms_per_ion,
        "duration": duration_s,
        "atomic_volume": atomic_volume_cm3,
    }
    flux = _number(values, "flux", "ion-sputtering", minimum=0.0)
    yield_ = _number(values, "yield", "ion-sputtering", minimum=0.0)
    duration = _number(values, "duration", "ion-sputtering", minimum=0.0)
    volume = _number(values, "atomic_volume", "ion-sputtering", minimum=0.0, strict=True)
    return flux * yield_ * duration * volume * CM_TO_NM


def linear_recession_nm(rate_nm_per_year, mission_years):
    """Depth removed by a mechanism quoted as a linear rate per year."""
    values = {"rate": rate_nm_per_year, "years": mission_years}
    rate = _number(values, "rate", "linear mechanism", minimum=0.0)
    years = _number(values, "years", "linear mechanism", minimum=0.0)
    return rate * years


def mechanism_recession_nm(mechanism, mission_years):
    """Dispatch one mechanism record to its depth-loss model."""
    if not isinstance(mechanism, dict):
        raise ValueError("mechanism must be a mapping")
    kind = mechanism.get("type")
    if kind not in MECHANISM_TYPES:
        raise ValueError(
            "mechanism type %r is not one of %s" % (kind, list(MECHANISM_TYPES))
        )
    if kind == "atomic-oxygen":
        return atomic_oxygen_recession_nm(
            mechanism.get("fluence_atoms_per_cm2"),
            mechanism.get("erosion_yield_cm3_per_atom"),
        )
    if kind == "ion-sputtering":
        return sputter_recession_nm(
            mechanism.get("ion_flux_per_cm2_s"),
            mechanism.get("sputter_yield_atoms_per_ion"),
            mechanism.get("duration_s"),
            mechanism.get("atomic_volume_cm3"),
        )
    return linear_recession_nm(mechanism.get("rate_nm_per_year"), mission_years)


def total_recession_nm(mechanisms, mission_years, uncertainty_factor=None):
    """Sum every mechanism depth loss and scale it by the uncertainty factor."""
    if not isinstance(mechanisms, (list, tuple)):
        raise ValueError("mechanisms must be a list")
    factor = (
        DEFAULT_EROSION_UNCERTAINTY_FACTOR
        if uncertainty_factor is None
        else _number({"f": uncertainty_factor}, "f", "uncertainty factor",
                     minimum=MIN_EROSION_UNCERTAINTY_FACTOR)
    )
    per_mechanism = []
    for mechanism in mechanisms:
        depth = mechanism_recession_nm(mechanism, mission_years)
        per_mechanism.append({"type": mechanism["type"], "recession_nm": depth})
    nominal = math.fsum(item["recession_nm"] for item in per_mechanism)
    return {
        "per_mechanism": per_mechanism,
        "nominal_nm": nominal,
        "uncertainty_factor": factor,
        "budgeted_nm": nominal * factor,
    }


def end_of_life_thickness_nm(as_deposited_nm, recession_nm):
    """Surviving thickness after recession; never negative."""
    deposited = _number({"t": as_deposited_nm}, "t", "as-deposited thickness",
                        minimum=0.0, strict=True)
    lost = _number({"r": recession_nm}, "r", "recession", minimum=0.0)
    return max(0.0, deposited - lost)


def sheet_resistance_ohm_sq(bulk_resistivity_ohm_m, thickness_nm):
    """Sheet resistance of a layer of the given thickness."""
    rho = _number({"r": bulk_resistivity_ohm_m}, "r", "bulk resistivity",
                  minimum=0.0, strict=True)
    thickness = _number({"t": thickness_nm}, "t", "thickness", minimum=0.0, strict=True)
    return rho / (thickness / M_TO_NM)


def thickness_for_sheet_resistance_nm(bulk_resistivity_ohm_m, allowable_ohm_sq):
    """Thinnest layer that still meets a sheet-resistance ceiling."""
    rho = _number({"r": bulk_resistivity_ohm_m}, "r", "bulk resistivity",
                  minimum=0.0, strict=True)
    allowable = _number({"a": allowable_ohm_sq}, "a", "allowable sheet resistance",
                        minimum=0.0, strict=True)
    return (rho / allowable) * M_TO_NM


def required_end_of_life_thickness_nm(properties, allowable_ohm_sq):
    """The stricter of the continuity floor and the sheet-resistance floor."""
    electrical = thickness_for_sheet_resistance_nm(
        properties["bulk_resistivity_ohm_m"], allowable_ohm_sq
    )
    return max(properties["continuity_floor_nm"], electrical)


def _within(value, limit, tolerance):
    """True when value >= limit, absorbing subtraction representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=tolerance)


def evaluate_conductive_coating(spec):
    """Run the full clause 6.3.3.5 thickness evaluation for one coated surface."""
    if not isinstance(spec, dict):
        raise ValueError("coating spec must be a mapping")
    surface = spec.get("surface")
    if not isinstance(surface, str) or not surface.strip():
        raise ValueError("coating spec needs a non-empty 'surface'")
    properties = coating_properties(spec.get("material"))
    as_deposited = _number(spec, "as_deposited_nm", "coating spec",
                           minimum=0.0, strict=True)
    mission_years = _number(spec, "mission_years", "coating spec", minimum=0.0)
    allowable = (
        ALLOWABLE_SHEET_RESISTANCE_OHM_SQ
        if spec.get("allowable_sheet_resistance_ohm_sq") is None
        else _number(spec, "allowable_sheet_resistance_ohm_sq", "coating spec",
                     minimum=0.0, strict=True)
    )
    recession = total_recession_nm(
        spec.get("mechanisms", []), mission_years, spec.get("uncertainty_factor")
    )
    eol = end_of_life_thickness_nm(as_deposited, recession["budgeted_nm"])

    findings = []
    continuity_ok = _within(
        eol, properties["continuity_floor_nm"], THICKNESS_TOLERANCE_NM
    )
    if not continuity_ok:
        findings.append(
            "end-of-life thickness %.3f nm is below the %.3f nm continuity floor "
            "for %s" % (eol, properties["continuity_floor_nm"], properties["material"])
        )
    if eol > 0.0:
        eol_sheet = sheet_resistance_ohm_sq(
            properties["bulk_resistivity_ohm_m"], eol
        )
        sheet_ok = eol_sheet <= allowable or math.isclose(
            eol_sheet, allowable, rel_tol=SHEET_RESISTANCE_REL_TOLERANCE, abs_tol=0.0
        )
    else:
        eol_sheet = math.inf
        sheet_ok = False
    if not sheet_ok:
        findings.append(
            "end-of-life sheet resistance %.4g ohm per square exceeds the %.4g "
            "ohm per square ceiling" % (eol_sheet, allowable)
        )
    required_eol = required_end_of_life_thickness_nm(properties, allowable)
    required_as_deposited = required_eol + recession["budgeted_nm"]
    if as_deposited < required_as_deposited and not math.isclose(
        as_deposited, required_as_deposited, rel_tol=0.0, abs_tol=THICKNESS_TOLERANCE_NM
    ):
        findings.append(
            "as-deposited thickness %.3f nm is short of the %.3f nm the erosion "
            "budget requires" % (as_deposited, required_as_deposited)
        )
    return {
        "surface": surface.strip(),
        "material": properties["material"],
        "as_deposited_nm": as_deposited,
        "recession": recession,
        "end_of_life_thickness_nm": eol,
        "end_of_life_sheet_resistance_ohm_sq": eol_sheet,
        "required_end_of_life_thickness_nm": required_eol,
        "required_as_deposited_nm": required_as_deposited,
        "thickness_margin_nm": as_deposited - required_as_deposited,
        "continuity_ok": continuity_ok,
        "sheet_resistance_ok": sheet_ok,
        "findings": findings,
        "compliant": not findings,
    }
