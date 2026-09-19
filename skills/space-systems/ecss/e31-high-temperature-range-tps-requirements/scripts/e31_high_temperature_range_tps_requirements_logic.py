"""High-temperature range and thermal-protection engineering requirements.

Anchor: ECSS-E-ST-31 clause 4.2.2 and its thermal-protection annex -- the
design constraints that apply once an item runs above the high-temperature
range boundary, and the engineering requirements on the protection it carries:
maximum use temperature, recession allowance, bondline temperature and reuse
degradation. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Admit only a peak that reaches into the high-temperature range.
2. Inflate the predicted peak by its uncertainty before the material check.
3. Spend the recession allowance and take the residual thickness.
4. Refuse a residual that has gone through the item.
5. Compute the bondline temperature from the RESIDUAL thickness.
6. Walk the surface emissivity out over the required reuse cycles.
7. Report a per-constraint verdict with its margin.
"""

import math

__all__ = [
    "HIGH_TEMPERATURE_LOWER_K",
    "TEMPERATURE_TOLERANCE_K",
    "LENGTH_TOLERANCE_M",
    "RELATIVE_TOLERANCE",
    "validate_item",
    "inflated_peak_temperature",
    "material_temperature_margin",
    "residual_thickness",
    "bondline_temperature",
    "emissivity_after_cycles",
    "assess_reuse",
    "assess_tps_item",
    "assess_tps_set",
]

HIGH_TEMPERATURE_LOWER_K = 470.0

# Margins are differences of products and sums; absorb representation error at
# a boundary here rather than by moving a limit.
TEMPERATURE_TOLERANCE_K = 1e-9
LENGTH_TOLERANCE_M = 1e-12
RELATIVE_TOLERANCE = 1e-12


def _real(label, value):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(label, value):
    v = _real(label, value)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _non_negative(label, value):
    v = _real(label, value)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def _unit_closed(label, value):
    v = _real(label, value)
    if v < 0.0 or v > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return v


def validate_item(item):
    """Return one validated thermal-protection item in the high range."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("item needs a non-empty name")
    peak = _positive("predicted_peak_k of %s" % name, item.get("predicted_peak_k"))
    uncertainty = _non_negative(
        "uncertainty_hot_k of %s" % name, item.get("uncertainty_hot_k", 0.0)
    )
    if peak + uncertainty <= HIGH_TEMPERATURE_LOWER_K + TEMPERATURE_TOLERANCE_K:
        raise ValueError(
            "inflated peak of %s does not reach the high-temperature boundary "
            "%g K; the conventional rules apply instead"
            % (name, HIGH_TEMPERATURE_LOWER_K)
        )
    checked = {
        "name": name.strip(),
        "predicted_peak_k": peak,
        "uncertainty_hot_k": uncertainty,
        "max_use_temperature_k": _positive(
            "max_use_temperature_k of %s" % name, item.get("max_use_temperature_k")
        ),
        "installed_thickness_m": _positive(
            "installed_thickness_m of %s" % name, item.get("installed_thickness_m")
        ),
        "required_residual_m": _non_negative(
            "required_residual_m of %s" % name, item.get("required_residual_m", 0.0)
        ),
        "recession_rate_m_per_s": _non_negative(
            "recession_rate_m_per_s of %s" % name,
            item.get("recession_rate_m_per_s", 0.0),
        ),
        "exposure_s": _positive("exposure_s of %s" % name, item.get("exposure_s")),
        "heat_flux_w_m2": _non_negative(
            "heat_flux_w_m2 of %s" % name, item.get("heat_flux_w_m2", 0.0)
        ),
        "conductivity_w_mk": _positive(
            "conductivity_w_mk of %s" % name, item.get("conductivity_w_mk")
        ),
        "bondline_limit_k": _positive(
            "bondline_limit_k of %s" % name, item.get("bondline_limit_k")
        ),
        "emissivity_bol": _unit_closed(
            "emissivity_bol of %s" % name, item.get("emissivity_bol")
        ),
        "emissivity_floor": _unit_closed(
            "emissivity_floor of %s" % name, item.get("emissivity_floor")
        ),
        "emissivity_loss_per_cycle": _non_negative(
            "emissivity_loss_per_cycle of %s" % name,
            item.get("emissivity_loss_per_cycle", 0.0),
        ),
        "required_cycles": item.get("required_cycles", 1),
        "qualified_cycles": item.get("qualified_cycles", 1),
    }
    for key in ("required_cycles", "qualified_cycles"):
        value = checked[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError("%s of %s must be an integer of at least 1" % (key, name))
    if checked["required_residual_m"] > checked["installed_thickness_m"]:
        raise ValueError(
            "required_residual_m of %s exceeds the installed thickness" % name
        )
    return checked


def inflated_peak_temperature(item):
    """Return the predicted peak widened by its hot uncertainty."""
    return item["predicted_peak_k"] + item["uncertainty_hot_k"]


def material_temperature_margin(item):
    """Compare the inflated peak with the material maximum use temperature."""
    peak = inflated_peak_temperature(item)
    margin = item["max_use_temperature_k"] - peak
    return {
        "inflated_peak_k": peak,
        "margin_k": margin,
        "acceptable": margin >= -TEMPERATURE_TOLERANCE_K,
    }


def residual_thickness(item):
    """Spend the recession allowance and return what thickness is left."""
    recessed = item["recession_rate_m_per_s"] * item["exposure_s"]
    residual = item["installed_thickness_m"] - recessed
    burn_through = residual <= LENGTH_TOLERANCE_M
    return {
        "recessed_m": recessed,
        "residual_m": residual,
        "burn_through": burn_through,
        "margin_m": residual - item["required_residual_m"],
        "acceptable": (not burn_through)
        and residual >= item["required_residual_m"] - LENGTH_TOLERANCE_M,
    }


def bondline_temperature(surface_temperature_k, thickness_m, heat_flux_w_m2,
                         conductivity_w_mk):
    """Return the through-thickness bondline temperature of a protection layer."""
    surface = _positive("surface_temperature_k", surface_temperature_k)
    thickness = _positive("thickness_m", thickness_m)
    flux = _non_negative("heat_flux_w_m2", heat_flux_w_m2)
    conductivity = _positive("conductivity_w_mk", conductivity_w_mk)
    drop = flux * thickness / conductivity
    temperature = surface - drop
    if temperature <= 0.0:
        raise ValueError(
            "the through-thickness drop %g K exceeds the surface temperature %g K; "
            "the steady conduction estimate does not apply" % (drop, surface)
        )
    return {"drop_k": drop, "bondline_k": temperature}


def emissivity_after_cycles(emissivity_bol, loss_per_cycle, cycles):
    """Walk a surface emissivity out over a number of reuse cycles."""
    start = _unit_closed("emissivity_bol", emissivity_bol)
    loss = _non_negative("loss_per_cycle", loss_per_cycle)
    if not isinstance(cycles, int) or isinstance(cycles, bool) or cycles < 1:
        raise ValueError("cycles must be an integer of at least 1, got %r" % (cycles,))
    value = start - loss * (cycles - 1)
    if value < 0.0:
        return 0.0
    return value


def assess_reuse(item):
    """Grade the reuse case: qualified cycles and end-of-life emissivity."""
    end_of_life = emissivity_after_cycles(
        item["emissivity_bol"],
        item["emissivity_loss_per_cycle"],
        item["required_cycles"],
    )
    cycles_ok = item["required_cycles"] <= item["qualified_cycles"]
    emissivity_ok = end_of_life >= item["emissivity_floor"] * (1.0 - RELATIVE_TOLERANCE)
    findings = []
    if not cycles_ok:
        findings.append(
            "%d cycles required but only %d qualified"
            % (item["required_cycles"], item["qualified_cycles"])
        )
    if not emissivity_ok:
        findings.append(
            "end-of-life emissivity %g falls below the floor %g; the degraded "
            "surface radiates less and runs hotter"
            % (end_of_life, item["emissivity_floor"])
        )
    return {
        "end_of_life_emissivity": end_of_life,
        "cycles_qualified": cycles_ok,
        "emissivity_acceptable": emissivity_ok,
        "acceptable": cycles_ok and emissivity_ok,
        "findings": findings,
    }


def assess_tps_item(item):
    """Apply every high-temperature constraint to one thermal-protection item."""
    checked = validate_item(item)
    material = material_temperature_margin(checked)
    recession = residual_thickness(checked)
    reuse = assess_reuse(checked)
    findings = []
    if not material["acceptable"]:
        findings.append(
            "inflated peak %g K exceeds the maximum use temperature %g K"
            % (material["inflated_peak_k"], checked["max_use_temperature_k"])
        )
    if recession["burn_through"]:
        findings.append(
            "recession of %g m consumes the installed thickness %g m; this is a "
            "burn-through, not a thin item"
            % (recession["recessed_m"], checked["installed_thickness_m"])
        )
    elif not recession["acceptable"]:
        findings.append(
            "residual thickness %g m is below the required %g m"
            % (recession["residual_m"], checked["required_residual_m"])
        )
    findings.extend(reuse["findings"])
    bond = None
    bond_ok = False
    if not recession["burn_through"]:
        bond = bondline_temperature(
            material["inflated_peak_k"],
            recession["residual_m"],
            checked["heat_flux_w_m2"],
            checked["conductivity_w_mk"],
        )
        bond["limit_k"] = checked["bondline_limit_k"]
        bond["margin_k"] = checked["bondline_limit_k"] - bond["bondline_k"]
        bond_ok = bond["margin_k"] >= -TEMPERATURE_TOLERANCE_K
        bond["acceptable"] = bond_ok
        if not bond_ok:
            findings.append(
                "bondline reaches %g K against a substrate limit of %g K"
                % (bond["bondline_k"], checked["bondline_limit_k"])
            )
    constraints = {
        "material": material["acceptable"],
        "recession": recession["acceptable"],
        "bondline": bond_ok,
        "reuse": reuse["acceptable"],
    }
    return {
        "name": checked["name"],
        "material": material,
        "recession": recession,
        "bondline": bond,
        "reuse": reuse,
        "constraints": constraints,
        "failed_constraints": sorted(k for k, ok in constraints.items() if not ok),
        "acceptable": all(constraints.values()),
        "findings": findings,
    }


def assess_tps_set(items):
    """Grade a set of thermal-protection items and name the driving one."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence")
    records = []
    seen = set()
    for item in items:
        record = assess_tps_item(item)
        if record["name"] in seen:
            raise ValueError("duplicate item name %r" % record["name"])
        seen.add(record["name"])
        records.append(record)
    failing = [r["name"] for r in records if not r["acceptable"]]
    driver = min(
        records, key=lambda r: (r["material"]["margin_k"], r["name"])
    )
    return {
        "records": records,
        "failing": sorted(failing),
        "material_driver": driver["name"],
        "material_driver_margin_k": driver["material"]["margin_k"],
        "acceptable": not failing,
    }
