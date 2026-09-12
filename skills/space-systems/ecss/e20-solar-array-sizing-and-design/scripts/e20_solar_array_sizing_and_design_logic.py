"""ECSS-E-ST-20C clause 5.5.2 -- solar array sizing and design logic.

Deterministic, offline, stdlib-only helpers that size a spacecraft solar
array so the power and the energy balance close in every operational
mission phase. The procedure is a paraphrase of the clause intent; no
standard text is reproduced here.

Model in one line: per phase, refer the sunlit load and the eclipse
recharge energy back to the array bus, degrade the reference cell power
density to the epoch and geometry of that phase, size an area, then take
the largest area across phases and re-check every phase against it.
"""

import math

REFERENCE_TEMPERATURE_C = 28.0
SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0

CONTINUOUS_SUNLIGHT = "continuous-sunlight"
ECLIPSE_CYCLING = "eclipse-cycling"
DARK_COAST = "dark-coast"

ILLUMINATION_REGIMES = (CONTINUOUS_SUNLIGHT, ECLIPSE_CYCLING, DARK_COAST)

DEFAULT_CELL_SPEC = {
    "bol_power_density_w_m2": 340.0,
    "inherent_degradation": 0.88,
    "annual_degradation": 0.025,
    "operating_temperature_c": 65.0,
    "power_temp_coeff_per_c": -0.0045,
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def validate_phase(phase):
    """Normalise one mission-phase record, raising ValueError on bad input."""
    if not isinstance(phase, dict):
        raise ValueError("phase must be a mapping, got %r" % (type(phase).__name__,))
    name = phase.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("phase name must be a non-empty string")
    period = _require_number(phase.get("orbit_period_s", 0.0), "orbit_period_s")
    if period <= 0.0:
        raise ValueError("phase %r: orbit_period_s must be > 0" % name)
    eclipse = _require_number(phase.get("eclipse_duration_s", 0.0), "eclipse_duration_s")
    if eclipse < 0.0:
        raise ValueError("phase %r: eclipse_duration_s must be >= 0" % name)
    if eclipse > period:
        raise ValueError("phase %r: eclipse_duration_s exceeds orbit_period_s" % name)
    sunlit_load = _require_number(phase.get("sunlit_load_w", 0.0), "sunlit_load_w")
    eclipse_load = _require_number(phase.get("eclipse_load_w", 0.0), "eclipse_load_w")
    if sunlit_load < 0.0 or eclipse_load < 0.0:
        raise ValueError("phase %r: loads must be >= 0" % name)
    if sunlit_load == 0.0 and eclipse_load == 0.0:
        raise ValueError("phase %r: both loads are zero; the phase draws no power" % name)
    duration_days = _require_number(phase.get("duration_days", 0.0), "duration_days")
    if duration_days <= 0.0:
        raise ValueError("phase %r: duration_days must be > 0" % name)
    incidence = _require_number(phase.get("sun_incidence_deg", 0.0), "sun_incidence_deg")
    if not 0.0 <= incidence < 90.0:
        raise ValueError("phase %r: sun_incidence_deg must be in [0, 90)" % name)
    return {
        "name": name,
        "orbit_period_s": period,
        "eclipse_duration_s": eclipse,
        "sunlit_duration_s": period - eclipse,
        "sunlit_load_w": sunlit_load,
        "eclipse_load_w": eclipse_load,
        "duration_days": duration_days,
        "sun_incidence_deg": incidence,
    }


def categorize_illumination(phase):
    """Return the illumination regime of a validated or raw phase record."""
    record = phase if "sunlit_duration_s" in phase else validate_phase(phase)
    if record["eclipse_duration_s"] == 0.0:
        return CONTINUOUS_SUNLIGHT
    if record["sunlit_duration_s"] == 0.0:
        return DARK_COAST
    return ECLIPSE_CYCLING


def _check_efficiency(value, label):
    eff = _require_number(value, label)
    if not 0.0 < eff <= 1.0:
        raise ValueError("%s must be in (0, 1], got %r" % (label, eff))
    return eff


def required_array_power(
    phase,
    sunlit_path_efficiency=0.90,
    eclipse_path_efficiency=0.88,
    charge_efficiency=0.90,
):
    """Array power a phase demands, in watts, referred to the array terminals.

    A dark-coast phase demands no array power (it is closed by stored
    energy) and returns 0.0; the caller flags it as unsized.
    """
    record = validate_phase(phase) if "sunlit_duration_s" not in phase else phase
    sunlit_eff = _check_efficiency(sunlit_path_efficiency, "sunlit_path_efficiency")
    eclipse_eff = _check_efficiency(eclipse_path_efficiency, "eclipse_path_efficiency")
    charge_eff = _check_efficiency(charge_efficiency, "charge_efficiency")
    if categorize_illumination(record) == DARK_COAST:
        return 0.0
    direct = record["sunlit_load_w"] / sunlit_eff
    eclipse_energy = record["eclipse_load_w"] * record["eclipse_duration_s"]
    referred_energy = eclipse_energy / (eclipse_eff * charge_eff)
    recharge = referred_energy / record["sunlit_duration_s"]
    return direct + recharge


def end_of_life_power_density(
    bol_power_density_w_m2,
    inherent_degradation,
    annual_degradation,
    elapsed_years,
    operating_temperature_c,
    power_temp_coeff_per_c,
    sun_incidence_deg,
    reference_temperature_c=REFERENCE_TEMPERATURE_C,
):
    """Usable array power density (W/m2) at a phase's epoch and geometry."""
    bol = _require_number(bol_power_density_w_m2, "bol_power_density_w_m2")
    if bol <= 0.0:
        raise ValueError("bol_power_density_w_m2 must be > 0")
    inherent = _check_efficiency(inherent_degradation, "inherent_degradation")
    annual = _require_number(annual_degradation, "annual_degradation")
    if not 0.0 <= annual < 1.0:
        raise ValueError("annual_degradation must be in [0, 1), got %r" % annual)
    years = _require_number(elapsed_years, "elapsed_years")
    if years < 0.0:
        raise ValueError("elapsed_years must be >= 0")
    t_op = _require_number(operating_temperature_c, "operating_temperature_c")
    if t_op <= -273.15:
        raise ValueError("operating_temperature_c is at or below absolute zero")
    coeff = _require_number(power_temp_coeff_per_c, "power_temp_coeff_per_c")
    if coeff > 0.0:
        raise ValueError("power_temp_coeff_per_c must be <= 0 for a photovoltaic cell")
    incidence = _require_number(sun_incidence_deg, "sun_incidence_deg")
    if not 0.0 <= incidence < 90.0:
        raise ValueError("sun_incidence_deg must be in [0, 90)")
    t_ref = _require_number(reference_temperature_c, "reference_temperature_c")
    life_factor = (1.0 - annual) ** years
    temp_factor = 1.0 + coeff * (t_op - t_ref)
    if temp_factor <= 0.0:
        raise ValueError("temperature factor collapsed to <= 0; operating point is outside the model")
    cosine_factor = math.cos(math.radians(incidence))
    return bol * inherent * life_factor * temp_factor * cosine_factor


def size_array_area(required_power_w, power_density_w_m2, design_margin=0.15):
    """Array area (m2) for a required power at a density, with design margin."""
    power = _require_number(required_power_w, "required_power_w")
    if power < 0.0:
        raise ValueError("required_power_w must be >= 0")
    density = _require_number(power_density_w_m2, "power_density_w_m2")
    if density <= 0.0:
        raise ValueError("power_density_w_m2 must be > 0")
    margin = _require_number(design_margin, "design_margin")
    if not 0.0 <= margin < 1.0:
        raise ValueError("design_margin must be in [0, 1), got %r" % margin)
    return power * (1.0 + margin) / density


def energy_balance(
    phase,
    array_area_m2,
    power_density_w_m2,
    sunlit_path_efficiency=0.90,
    eclipse_path_efficiency=0.88,
    charge_efficiency=0.90,
):
    """Per-orbit generated vs consumed energy for one phase, plus its margin."""
    record = validate_phase(phase) if "sunlit_duration_s" not in phase else phase
    area = _require_number(array_area_m2, "array_area_m2")
    if area <= 0.0:
        raise ValueError("array_area_m2 must be > 0")
    density = _require_number(power_density_w_m2, "power_density_w_m2")
    if density <= 0.0:
        raise ValueError("power_density_w_m2 must be > 0")
    sunlit_eff = _check_efficiency(sunlit_path_efficiency, "sunlit_path_efficiency")
    eclipse_eff = _check_efficiency(eclipse_path_efficiency, "eclipse_path_efficiency")
    charge_eff = _check_efficiency(charge_efficiency, "charge_efficiency")
    generated = area * density * record["sunlit_duration_s"]
    consumed = record["sunlit_load_w"] * record["sunlit_duration_s"] / sunlit_eff
    consumed += (
        record["eclipse_load_w"]
        * record["eclipse_duration_s"]
        / (eclipse_eff * charge_eff)
    )
    regime = categorize_illumination(record)
    margin = generated / consumed - 1.0
    return {
        "name": record["name"],
        "regime": regime,
        "generated_wh": generated / 3600.0,
        "consumed_wh": consumed / 3600.0,
        "margin": margin,
        "closes": regime != DARK_COAST and margin >= 0.0,
    }


def size_solar_array(phases, cell_spec=None, design_margin=0.15, **path_efficiencies):
    """Size the array on the driving phase and re-check every phase against it."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty list of phase records")
    spec = dict(DEFAULT_CELL_SPEC)
    if cell_spec is not None:
        if not isinstance(cell_spec, dict):
            raise ValueError("cell_spec must be a mapping")
        unknown = sorted(set(cell_spec) - set(DEFAULT_CELL_SPEC))
        if unknown:
            raise ValueError("cell_spec has unknown keys: %s" % ", ".join(unknown))
        spec.update(cell_spec)
    records = [validate_phase(p) for p in phases]
    elapsed_years = 0.0
    sized = []
    for record in records:
        elapsed_years += record["duration_days"] / 365.25
        regime = categorize_illumination(record)
        power = required_array_power(record, **path_efficiencies)
        density = end_of_life_power_density(
            spec["bol_power_density_w_m2"],
            spec["inherent_degradation"],
            spec["annual_degradation"],
            elapsed_years,
            spec["operating_temperature_c"],
            spec["power_temp_coeff_per_c"],
            record["sun_incidence_deg"],
        )
        area = size_array_area(power, density, design_margin)
        sized.append(
            {
                "name": record["name"],
                "regime": regime,
                "elapsed_years": elapsed_years,
                "required_power_w": power,
                "power_density_w_m2": density,
                "required_area_m2": area,
            }
        )
    sizable = [s for s in sized if s["regime"] != DARK_COAST]
    if not sizable:
        raise ValueError("every phase is dark-coast; the array cannot be sized")
    driver = max(sizable, key=lambda s: s["required_area_m2"])
    selected_area = driver["required_area_m2"]
    balances = []
    for record, entry in zip(records, sized):
        balances.append(
            energy_balance(
                record, selected_area, entry["power_density_w_m2"], **path_efficiencies
            )
        )
    findings = []
    for entry, balance in zip(sized, balances):
        if entry["regime"] == DARK_COAST:
            findings.append(
                "phase %r is dark-coast: not closable by the array, size the battery"
                % entry["name"]
            )
        elif not balance["closes"]:
            findings.append(
                "phase %r energy balance closes negative at the selected area"
                % entry["name"]
            )
    return {
        "driving_phase": driver["name"],
        "selected_area_m2": selected_area,
        "design_margin": design_margin,
        "phases": sized,
        "balances": balances,
        "findings": findings,
        "compliant": not findings,
    }
