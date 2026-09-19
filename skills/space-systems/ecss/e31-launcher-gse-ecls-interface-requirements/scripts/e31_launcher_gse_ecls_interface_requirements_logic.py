"""Thermal-control interfaces to the launcher, ground support and life support.

Anchor: ECSS-E-ST-31C clauses 4.3.7 to 4.3.9 (interface requirements
towards the launch vehicle, towards ground support equipment and towards
the environmental control and life support subsystem for crew-tended
items). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Launcher: size the fairing conditioned-air interface. The air picks up
   the pre-launch dissipation as it passes the spacecraft, dT = Q /
   (m_dot * cp), so the item sees the inlet temperature plus that rise and
   has to stay inside its non-operating band. Separately, the supply dew
   point must sit clear of the coldest exposed surface or the vehicle
   collects condensation inside the fairing.
2. Launcher: hold the thermal envelope. The clearance to the fairing
   dynamic envelope is the static gap less the thermal growth of the item
   over the ground-to-flight swing and less the declared deflection, and it
   has to stay above the minimum clearance.
3. Ground support: size the test cooling or heating interface. The coolant
   flow the load demands is Q / (cp * dT_coolant), and the demanded heat
   load is graded against the declared capacity of the equipment with a
   margin.
4. Life support: grade touch temperature of any surface the crew can reach.
   The allowable band depends on the material group of the surface and on
   the contact duration band, because a metal surface removes heat from
   skin far faster than an insulator at the same temperature.
"""

import math

__all__ = [
    "AIR_CP_J_PER_KGK",
    "CONDENSATION_MARGIN_K",
    "TOUCH_TEMPERATURE_LIMITS_C",
    "validate_positive",
    "air_temperature_rise_k",
    "item_temperature_c",
    "condensation_clearance_k",
    "thermal_growth_m",
    "envelope_clearance_m",
    "gse_coolant_flow_kg_s",
    "gse_capacity_margin_fraction",
    "touch_duration_band",
    "touch_temperature_verdict",
    "assess_launcher_interface",
    "assess_gse_interface",
    "assess_crew_touch_surfaces",
    "assess_external_interfaces",
]

AIR_CP_J_PER_KGK = 1005.0

# The conditioned-air dew point has to sit this far below the coldest
# exposed surface before the interface is considered condensation-free.
CONDENSATION_MARGIN_K = 5.0

# Allowable crew touch temperature band in degrees Celsius, by material
# group and contact duration band. A metal surface pulls heat out of skin
# far faster than an insulator, so its band is the narrowest.
TOUCH_TEMPERATURE_LIMITS_C = {
    ("metal", "momentary"): (-5.0, 55.0),
    ("metal", "short"): (0.0, 48.0),
    ("metal", "prolonged"): (4.0, 43.0),
    ("composite", "momentary"): (-10.0, 62.0),
    ("composite", "short"): (-4.0, 55.0),
    ("composite", "prolonged"): (2.0, 46.0),
    ("insulator", "momentary"): (-18.0, 75.0),
    ("insulator", "short"): (-10.0, 65.0),
    ("insulator", "prolonged"): (0.0, 50.0),
}

MOMENTARY_LIMIT_S = 1.0
SHORT_LIMIT_S = 60.0


def validate_positive(label, value, allow_zero=False):
    """Return value as a positive finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, out))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def _validate_real(label, value):
    """Return value as a finite float of any sign."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def air_temperature_rise_k(dissipation_w, mass_flow_kg_s, cp_j_per_kgk=AIR_CP_J_PER_KGK):
    """Return the temperature rise of the conditioned air across the item."""
    heat = validate_positive("dissipation_w", dissipation_w, allow_zero=True)
    flow = validate_positive("mass_flow_kg_s", mass_flow_kg_s)
    cp = validate_positive("cp_j_per_kgk", cp_j_per_kgk)
    return heat / (flow * cp)


def item_temperature_c(inlet_temperature_c, rise_k):
    """Return the temperature the item sees downstream of the inlet."""
    inlet = _validate_real("inlet_temperature_c", inlet_temperature_c)
    rise = validate_positive("rise_k", rise_k, allow_zero=True)
    return inlet + rise


def condensation_clearance_k(dew_point_c, coldest_surface_c):
    """Return how far the coldest exposed surface sits above the dew point."""
    dew = _validate_real("dew_point_c", dew_point_c)
    surface = _validate_real("coldest_surface_c", coldest_surface_c)
    return surface - dew


def thermal_growth_m(expansion_coefficient_per_k, delta_temperature_k, length_m):
    """Return the thermal growth of a dimension over a temperature swing."""
    alpha = _validate_real("expansion_coefficient_per_k", expansion_coefficient_per_k)
    swing = _validate_real("delta_temperature_k", delta_temperature_k)
    length = validate_positive("length_m", length_m)
    return abs(alpha * swing * length)


def envelope_clearance_m(static_gap_m, growth_m, deflection_m):
    """Return the clearance left to the launcher dynamic envelope."""
    gap = validate_positive("static_gap_m", static_gap_m)
    growth = validate_positive("growth_m", growth_m, allow_zero=True)
    deflection = validate_positive("deflection_m", deflection_m, allow_zero=True)
    return gap - growth - deflection


def gse_coolant_flow_kg_s(load_w, cp_j_per_kgk, allowed_rise_k):
    """Return the coolant mass flow a ground test load demands."""
    load = validate_positive("load_w", load_w)
    cp = validate_positive("cp_j_per_kgk", cp_j_per_kgk)
    rise = validate_positive("allowed_rise_k", allowed_rise_k)
    return load / (cp * rise)


def gse_capacity_margin_fraction(demand_w, capacity_w):
    """Return the fractional margin of ground equipment against the demand."""
    demand = validate_positive("demand_w", demand_w)
    capacity = validate_positive("capacity_w", capacity_w)
    return (capacity - demand) / capacity


def touch_duration_band(contact_duration_s):
    """Return the contact duration band a touch duration falls into."""
    duration = validate_positive("contact_duration_s", contact_duration_s)
    if duration <= MOMENTARY_LIMIT_S:
        return "momentary"
    if duration <= SHORT_LIMIT_S:
        return "short"
    return "prolonged"


def touch_temperature_verdict(surface_temperature_c, material_group, contact_duration_s):
    """Return the crew touch verdict for one reachable surface."""
    temperature = _validate_real("surface_temperature_c", surface_temperature_c)
    if not isinstance(material_group, str):
        raise ValueError("material_group must be a string, got %r" % (material_group,))
    band = touch_duration_band(contact_duration_s)
    key = (material_group, band)
    if key not in TOUCH_TEMPERATURE_LIMITS_C:
        raise ValueError(
            "no touch limit for material group %r; the groups categorized here "
            "are metal, composite and insulator" % (material_group,)
        )
    low, high = TOUCH_TEMPERATURE_LIMITS_C[key]
    if temperature < low:
        return "cold-hazard"
    if temperature > high:
        return "hot-hazard"
    return "within-limits"


def assess_launcher_interface(launcher):
    """Assess the fairing conditioned-air and envelope interface."""
    if not isinstance(launcher, dict):
        raise ValueError("launcher must be a mapping")
    for key in ("inlet_temperature_c", "mass_flow_kg_s", "prelaunch_dissipation_w",
                "non_operating_max_c", "dew_point_c", "coldest_surface_c",
                "static_gap_m", "expansion_coefficient_per_k",
                "ground_to_flight_swing_k", "item_length_m", "deflection_m",
                "minimum_clearance_m"):
        if key not in launcher:
            raise ValueError("launcher record missing required key %r" % key)
    rise = air_temperature_rise_k(
        launcher["prelaunch_dissipation_w"], launcher["mass_flow_kg_s"],
        launcher.get("cp_j_per_kgk", AIR_CP_J_PER_KGK),
    )
    reached = item_temperature_c(launcher["inlet_temperature_c"], rise)
    limit = _validate_real("non_operating_max_c", launcher["non_operating_max_c"])
    air_ok = reached < limit or math.isclose(reached, limit, rel_tol=1e-12, abs_tol=0.0)
    clearance_to_dew = condensation_clearance_k(
        launcher["dew_point_c"], launcher["coldest_surface_c"]
    )
    dew_ok = clearance_to_dew > CONDENSATION_MARGIN_K or math.isclose(
        clearance_to_dew, CONDENSATION_MARGIN_K, rel_tol=1e-12, abs_tol=0.0
    )
    growth = thermal_growth_m(
        launcher["expansion_coefficient_per_k"],
        launcher["ground_to_flight_swing_k"], launcher["item_length_m"],
    )
    clearance = envelope_clearance_m(
        launcher["static_gap_m"], growth, launcher["deflection_m"]
    )
    minimum = validate_positive("minimum_clearance_m", launcher["minimum_clearance_m"])
    envelope_ok = clearance > minimum or math.isclose(
        clearance, minimum, rel_tol=1e-12, abs_tol=0.0
    )
    findings = []
    if not air_ok:
        findings.append(
            "fairing air brings the item to %.2f C, above its %.2f C "
            "non-operating limit" % (reached, limit)
        )
    if not dew_ok:
        findings.append(
            "coldest exposed surface sits only %.2f K above the supply dew "
            "point; %.1f K is required" % (clearance_to_dew, CONDENSATION_MARGIN_K)
        )
    if not envelope_ok:
        findings.append(
            "envelope clearance %.4f m falls below the %.4f m minimum once "
            "thermal growth and deflection are taken" % (clearance, minimum)
        )
    return {
        "air_temperature_rise_k": rise,
        "item_temperature_c": reached,
        "dew_point_clearance_k": clearance_to_dew,
        "thermal_growth_m": growth,
        "envelope_clearance_m": clearance,
        "compliant": air_ok and dew_ok and envelope_ok,
        "findings": findings,
    }


def assess_gse_interface(gse):
    """Assess the ground support cooling or heating interface."""
    if not isinstance(gse, dict):
        raise ValueError("gse must be a mapping")
    for key in ("test_load_w", "coolant_cp_j_per_kgk", "allowed_rise_k",
                "capacity_w", "required_margin_fraction"):
        if key not in gse:
            raise ValueError("gse record missing required key %r" % key)
    flow = gse_coolant_flow_kg_s(
        gse["test_load_w"], gse["coolant_cp_j_per_kgk"], gse["allowed_rise_k"]
    )
    margin = gse_capacity_margin_fraction(gse["test_load_w"], gse["capacity_w"])
    required = validate_positive(
        "required_margin_fraction", gse["required_margin_fraction"], allow_zero=True
    )
    if required >= 1.0:
        raise ValueError("required_margin_fraction must be below one, got %g" % required)
    margin_ok = margin > required or math.isclose(
        margin, required, rel_tol=1e-12, abs_tol=0.0
    )
    findings = []
    if not margin_ok:
        findings.append(
            "ground equipment margin %.3f is below the required %.3f against a "
            "%.1f W test load" % (margin, required, float(gse["test_load_w"]))
        )
    return {
        "coolant_flow_kg_s": flow,
        "capacity_margin_fraction": margin,
        "required_margin_fraction": required,
        "compliant": margin_ok,
        "findings": findings,
    }


def assess_crew_touch_surfaces(surfaces):
    """Assess every crew-reachable surface against its touch limits."""
    if not isinstance(surfaces, (list, tuple)):
        raise ValueError("surfaces must be a sequence of surface records")
    records = []
    findings = []
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, dict):
            raise ValueError("surfaces[%d] must be a mapping" % index)
        for key in ("name", "surface_temperature_c", "material_group",
                    "contact_duration_s"):
            if key not in surface:
                raise ValueError("surfaces[%d] missing key %r" % (index, key))
        verdict = touch_temperature_verdict(
            surface["surface_temperature_c"], surface["material_group"],
            surface["contact_duration_s"],
        )
        record = {
            "name": surface["name"],
            "duration_band": touch_duration_band(surface["contact_duration_s"]),
            "verdict": verdict,
            "compliant": verdict == "within-limits",
        }
        if not record["compliant"]:
            findings.append(
                "%s: %s at %.1f C for a %s contact on a %s surface"
                % (surface["name"], verdict,
                   float(surface["surface_temperature_c"]),
                   record["duration_band"], surface["material_group"])
            )
        records.append(record)
    return {
        "surfaces": records,
        "compliant": all(record["compliant"] for record in records),
        "findings": findings,
    }


def assess_external_interfaces(spec):
    """Run the full clause 4.3.7 to 4.3.9 external interface assessment.

    spec keys: launcher, gse, crew_surfaces.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("launcher", "gse", "crew_surfaces"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    launcher = assess_launcher_interface(spec["launcher"])
    gse = assess_gse_interface(spec["gse"])
    crew = assess_crew_touch_surfaces(spec["crew_surfaces"])
    findings = launcher["findings"] + gse["findings"] + crew["findings"]
    return {
        "launcher": launcher,
        "gse": gse,
        "crew": crew,
        "compliant": launcher["compliant"] and gse["compliant"] and crew["compliant"],
        "findings": findings,
    }
