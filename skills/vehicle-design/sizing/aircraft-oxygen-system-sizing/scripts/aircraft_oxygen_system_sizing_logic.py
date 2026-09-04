"""Aircraft supplemental oxygen system sizing for transport aircraft.

Pure stdlib module implementing the leaf contract for
vehicle-design/sizing/aircraft-oxygen-system-sizing: passenger
continuous-flow chemical generator demand (one unit per passenger),
crew diluter-demand gaseous oxygen requirement, conversion of
standard-litre demand volumes to oxygen mass at standard conditions,
and crew high-pressure gaseous oxygen bottle volume from the ideal gas
law at the service pressure and storage temperature.

All demand volumes are standard litres (SL) at 0 C and 101.325 kPa.
The governing cabin pressure altitude is an input here, produced by
vehicle-design/sizing/environmental-control-sizing; this module only
consumes that altitude result and computes no altitude schedule. All
public functions raise ValueError on non-physical inputs.
"""

# --- Module constants -------------------------------------------------------
R_O2 = 259.8            # oxygen specific gas constant, J/(kg K)
RHO_O2_STP = 1.429      # oxygen density at 0 C, 101.325 kPa, kg/m3
STORAGE_TEMP_K = 288.15  # 15 C storage temperature, K
PSI_TO_PA = 6894.757    # Pa per psi

FLOW_PAX_SLPM = 5.0     # continuous-flow litres per minute per passenger
FLOW_CREW_SLPM = 2.5    # average diluter-demand litres per minute per crew
PAX_PROTECTION_MIN = 22.0   # minutes of protection per passenger generator
CREW_PROTECTION_MIN = 120.0  # 2 h crew protection duration, minutes


def passenger_demand(n_passengers, flow_slpm=FLOW_PAX_SLPM,
                     duration_min=PAX_PROTECTION_MIN):
    """Passenger supplemental oxygen demand at standard conditions.

    Returns {volume_sl, mass_kg}: volume_sl = n_passengers * flow_slpm
    * duration_min and mass_kg = volume_sl * 1e-3 * RHO_O2_STP. Raises
    ValueError for any non-positive input.
    """
    if n_passengers <= 0:
        raise ValueError("n_passengers must be positive")
    if flow_slpm <= 0:
        raise ValueError("flow_slpm must be positive")
    if duration_min <= 0:
        raise ValueError("duration_min must be positive")
    volume_sl = n_passengers * flow_slpm * duration_min
    mass_kg = volume_sl * 1e-3 * RHO_O2_STP
    return {"volume_sl": volume_sl, "mass_kg": mass_kg}


def generator_units(n_passengers):
    """Chemical oxygen generator unit count, one unit per passenger.

    Continuous-flow per-person generators, so the count equals the
    passenger count. Raises ValueError for n_passengers < 1.
    """
    if n_passengers < 1:
        raise ValueError("n_passengers must be at least 1")
    return int(n_passengers)


def crew_demand(n_crew, flow_slpm=FLOW_CREW_SLPM,
                duration_min=CREW_PROTECTION_MIN):
    """Crew diluter-demand oxygen requirement at standard conditions.

    Same math as passenger_demand: {volume_sl, mass_kg} with
    volume_sl = n_crew * flow_slpm * duration_min and mass_kg =
    volume_sl * 1e-3 * RHO_O2_STP. Raises ValueError for any
    non-positive input.
    """
    if n_crew <= 0:
        raise ValueError("n_crew must be positive")
    if flow_slpm <= 0:
        raise ValueError("flow_slpm must be positive")
    if duration_min <= 0:
        raise ValueError("duration_min must be positive")
    volume_sl = n_crew * flow_slpm * duration_min
    mass_kg = volume_sl * 1e-3 * RHO_O2_STP
    return {"volume_sl": volume_sl, "mass_kg": mass_kg}


def bottle_volume(mass_kg, service_pressure_psi, temperature_k=STORAGE_TEMP_K):
    """Crew gaseous oxygen bottle volume from the ideal gas law.

    Returns {volume_m3, volume_l} = m R T / p with p =
    service_pressure_psi * PSI_TO_PA. Raises ValueError for mass <= 0,
    pressure <= 0 or temperature <= 0.
    """
    if mass_kg <= 0:
        raise ValueError("mass_kg must be positive")
    if service_pressure_psi <= 0:
        raise ValueError("service_pressure_psi must be positive")
    if temperature_k <= 0:
        raise ValueError("temperature_k must be positive")
    p_pa = service_pressure_psi * PSI_TO_PA
    volume_m3 = mass_kg * R_O2 * temperature_k / p_pa
    return {"volume_m3": volume_m3, "volume_l": volume_m3 * 1000.0}


def oxygen_summary(n_passengers, n_crew, service_pressure_psi):
    """Full supplemental oxygen sizing summary for one aircraft.

    Returns passenger and crew demands, the passenger generator unit
    count, the crew bottle volume at the service pressure and the
    total stored oxygen mass. Keys are documented and fixed:
    passenger_demand_sl, passenger_mass_kg, generator_units,
    crew_demand_sl, crew_mass_kg, bottle_volume_m3, bottle_volume_l,
    total_mass_kg.
    """
    pax = passenger_demand(n_passengers)
    crew = crew_demand(n_crew)
    bottle = bottle_volume(crew["mass_kg"], service_pressure_psi)
    return {
        "passenger_demand_sl": pax["volume_sl"],
        "passenger_mass_kg": pax["mass_kg"],
        "generator_units": generator_units(n_passengers),
        "crew_demand_sl": crew["volume_sl"],
        "crew_mass_kg": crew["mass_kg"],
        "bottle_volume_m3": bottle["volume_m3"],
        "bottle_volume_l": bottle["volume_l"],
        "total_mass_kg": pax["mass_kg"] + crew["mass_kg"],
    }
