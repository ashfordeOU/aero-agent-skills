"""Thermal-control to power and attitude-control interface requirements.

Anchor: ECSS-E-ST-31C clauses 4.3.3 and 4.3.4 (interface requirements
towards the electrical power subsystem and towards the attitude and orbit
control subsystem). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate each heater circuit: resistance, the regulated bus voltage range
   it is fed from, its duty cycle in the cold case, and whether it is a prime
   or a redundant branch.
2. Size every circuit at the top of the bus range, where the power and the
   current are both worst case, and derive the switch current against the
   rating and the derating factor the power subsystem imposes.
3. Build the two demands the power subsystem actually allocates against: the
   peak switched-on demand, counting a redundant branch only when the design
   admits both branches live at once, and the orbit-average demand weighted
   by duty cycle.
4. Check the dissipation data the thermal subsystem owes the power subsystem
   for completeness: every declared mission mode must carry a dissipation
   figure, because a mode with no entry is unknown, not zero.
5. Turn the radiator and heater asymmetries into the disturbance inputs the
   attitude control subsystem needs: the recoil of thermally radiated power
   off an offset radiator, F = e * sigma * A * T^4 / c, times its moment arm,
   summed and compared with the disturbance-torque allocation.
"""

import math

__all__ = [
    "SPEED_OF_LIGHT_M_PER_S",
    "STEFAN_BOLTZMANN_W_PER_M2K4",
    "POWER_TOLERANCE_W",
    "TORQUE_TOLERANCE_NM",
    "validate_positive",
    "validate_bus_range",
    "heater_circuit_power_w",
    "heater_circuit_current_a",
    "switch_current_headroom",
    "evaluate_circuit",
    "peak_demand_w",
    "orbit_average_demand_w",
    "dissipation_by_mode",
    "radiator_recoil_force_n",
    "radiator_disturbance_torque_nm",
    "total_disturbance_torque_nm",
    "assess_electrical_aocs_interfaces",
]

SPEED_OF_LIGHT_M_PER_S = 299792458.0
STEFAN_BOLTZMANN_W_PER_M2K4 = 5.670374419e-8

# A demand sized exactly on its allocation is a design decision, not a
# failure; absorb the floating-point representation error at the boundary
# instead of relaxing the allocation.
POWER_TOLERANCE_W = 1e-9
TORQUE_TOLERANCE_NM = 1e-15


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


def validate_bus_range(v_min, v_max):
    """Return the validated (v_min, v_max) regulated bus voltage range."""
    low = validate_positive("bus_voltage_min_v", v_min)
    high = validate_positive("bus_voltage_max_v", v_max)
    if low > high:
        raise ValueError(
            "bus_voltage_min_v %g exceeds bus_voltage_max_v %g" % (low, high)
        )
    return (low, high)


def heater_circuit_power_w(resistance_ohm, bus_voltage_v):
    """Return the power a resistive heater draws at a bus voltage."""
    resistance = validate_positive("resistance_ohm", resistance_ohm)
    voltage = validate_positive("bus_voltage_v", bus_voltage_v)
    return voltage * voltage / resistance


def heater_circuit_current_a(resistance_ohm, bus_voltage_v):
    """Return the current a resistive heater draws at a bus voltage."""
    resistance = validate_positive("resistance_ohm", resistance_ohm)
    voltage = validate_positive("bus_voltage_v", bus_voltage_v)
    return voltage / resistance


def switch_current_headroom(current_a, switch_rating_a, derating_factor=0.8):
    """Return the fractional headroom against the derated switch rating."""
    current = validate_positive("current_a", current_a)
    rating = validate_positive("switch_rating_a", switch_rating_a)
    derating = validate_positive("derating_factor", derating_factor)
    if derating > 1.0:
        raise ValueError("derating_factor must not exceed one, got %g" % derating)
    allowed = rating * derating
    return (allowed - current) / allowed


def evaluate_circuit(circuit, bus_range):
    """Evaluate one heater circuit at the worst-case end of the bus range."""
    if not isinstance(circuit, dict):
        raise ValueError("circuit must be a mapping")
    for key in ("name", "resistance_ohm", "duty_cycle", "switch_rating_a"):
        if key not in circuit:
            raise ValueError("circuit record missing required key %r" % key)
    low, high = validate_bus_range(bus_range[0], bus_range[1])
    duty = validate_positive("duty_cycle", circuit["duty_cycle"], allow_zero=True)
    if duty > 1.0:
        raise ValueError("duty_cycle must lie in [0, 1], got %g" % duty)
    branch = circuit.get("branch", "prime")
    if branch not in ("prime", "redundant"):
        raise ValueError(
            "branch must be 'prime' or 'redundant', got %r" % (branch,)
        )
    power_high = heater_circuit_power_w(circuit["resistance_ohm"], high)
    power_low = heater_circuit_power_w(circuit["resistance_ohm"], low)
    current_high = heater_circuit_current_a(circuit["resistance_ohm"], high)
    headroom = switch_current_headroom(
        current_high, circuit["switch_rating_a"],
        circuit.get("derating_factor", 0.8),
    )
    return {
        "name": circuit["name"],
        "branch": branch,
        "duty_cycle": duty,
        "power_at_max_bus_w": power_high,
        "power_at_min_bus_w": power_low,
        "current_at_max_bus_a": current_high,
        "switch_headroom_fraction": headroom,
        "switch_compliant": headroom >= 0.0,
    }


def peak_demand_w(records, both_branches_credible=False):
    """Return the peak simultaneous heater demand, in watts."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of circuit records")
    total = 0.0
    for record in records:
        if not isinstance(record, dict) or "power_at_max_bus_w" not in record:
            raise ValueError("each record must carry 'power_at_max_bus_w'")
        if record.get("branch") == "redundant" and not both_branches_credible:
            continue
        total += float(record["power_at_max_bus_w"])
    return total


def orbit_average_demand_w(records):
    """Return the duty-weighted orbit-average heater demand, in watts."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of circuit records")
    total = 0.0
    for record in records:
        if not isinstance(record, dict) or "power_at_max_bus_w" not in record:
            raise ValueError("each record must carry 'power_at_max_bus_w'")
        if record.get("branch") == "redundant":
            continue
        total += float(record["power_at_max_bus_w"]) * float(record["duty_cycle"])
    return total


def dissipation_by_mode(modes, dissipation_map):
    """Return the dissipation figure per declared mode, refusing a gap."""
    if not isinstance(modes, (list, tuple)) or not modes:
        raise ValueError("modes must be a non-empty sequence of mode names")
    if not isinstance(dissipation_map, dict):
        raise ValueError("dissipation_map must be a mapping of mode to watts")
    table = {}
    for mode in modes:
        if not isinstance(mode, str) or not mode:
            raise ValueError("each mode name must be a non-empty string")
        if mode not in dissipation_map:
            raise ValueError(
                "mode %r carries no dissipation figure; an undeclared mode "
                "dissipation is unknown, not zero" % (mode,)
            )
        table[mode] = validate_positive(
            "dissipation_map[%r]" % mode, dissipation_map[mode], allow_zero=True
        )
    unused = sorted(set(dissipation_map) - set(modes))
    if unused:
        raise ValueError(
            "dissipation_map carries modes the mission does not declare: %s"
            % ", ".join(unused)
        )
    return table


def radiator_recoil_force_n(area_m2, emissivity, temperature_k):
    """Return the photon recoil force of a radiating surface, in newtons."""
    area = validate_positive("area_m2", area_m2)
    emissivity = validate_positive("emissivity", emissivity)
    if emissivity > 1.0:
        raise ValueError("emissivity must not exceed one, got %g" % emissivity)
    temperature = validate_positive("temperature_k", temperature_k)
    radiated = emissivity * STEFAN_BOLTZMANN_W_PER_M2K4 * area * temperature ** 4
    return radiated / SPEED_OF_LIGHT_M_PER_S


def radiator_disturbance_torque_nm(area_m2, emissivity, temperature_k, moment_arm_m):
    """Return the disturbance torque an offset radiating surface applies."""
    force = radiator_recoil_force_n(area_m2, emissivity, temperature_k)
    arm = validate_positive("moment_arm_m", moment_arm_m, allow_zero=True)
    return force * arm


def total_disturbance_torque_nm(surfaces):
    """Return the summed thermal disturbance torque of a surface set."""
    if not isinstance(surfaces, (list, tuple)) or not surfaces:
        raise ValueError("surfaces must be a non-empty sequence of surface records")
    total = 0.0
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, dict):
            raise ValueError("surfaces[%d] must be a mapping" % index)
        for key in ("area_m2", "emissivity", "temperature_k", "moment_arm_m"):
            if key not in surface:
                raise ValueError("surfaces[%d] missing key %r" % (index, key))
        total += radiator_disturbance_torque_nm(
            surface["area_m2"], surface["emissivity"],
            surface["temperature_k"], surface["moment_arm_m"],
        )
    return total


def assess_electrical_aocs_interfaces(spec):
    """Run the full clause 4.3.3 and 4.3.4 interface assessment.

    spec keys: circuits, bus_range, peak_allocation_w, average_allocation_w,
    modes, dissipation_w_by_mode, surfaces, torque_allocation_nm, optional
    both_branches_credible.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("circuits", "bus_range", "peak_allocation_w",
                "average_allocation_w", "modes", "dissipation_w_by_mode",
                "surfaces", "torque_allocation_nm"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    bus_range = spec["bus_range"]
    if not isinstance(bus_range, (list, tuple)) or len(bus_range) != 2:
        raise ValueError("spec['bus_range'] must be a (v_min, v_max) pair")
    circuits = spec["circuits"]
    if not isinstance(circuits, (list, tuple)) or not circuits:
        raise ValueError("spec['circuits'] must be a non-empty sequence")
    records = [evaluate_circuit(circuit, bus_range) for circuit in circuits]
    both = bool(spec.get("both_branches_credible", False))
    peak = peak_demand_w(records, both)
    average = orbit_average_demand_w(records)
    peak_allocation = validate_positive("peak_allocation_w", spec["peak_allocation_w"])
    average_allocation = validate_positive(
        "average_allocation_w", spec["average_allocation_w"]
    )
    peak_ok = peak < peak_allocation or math.isclose(
        peak, peak_allocation, rel_tol=0.0, abs_tol=POWER_TOLERANCE_W
    )
    average_ok = average < average_allocation or math.isclose(
        average, average_allocation, rel_tol=0.0, abs_tol=POWER_TOLERANCE_W
    )
    dissipation = dissipation_by_mode(spec["modes"], spec["dissipation_w_by_mode"])
    torque = total_disturbance_torque_nm(spec["surfaces"])
    torque_allocation = validate_positive(
        "torque_allocation_nm", spec["torque_allocation_nm"]
    )
    torque_ok = torque < torque_allocation or math.isclose(
        torque, torque_allocation, rel_tol=0.0, abs_tol=TORQUE_TOLERANCE_NM
    )
    findings = []
    if not peak_ok:
        findings.append(
            "peak heater demand %.3f W exceeds the %.3f W peak allocation"
            % (peak, peak_allocation)
        )
    if not average_ok:
        findings.append(
            "orbit-average heater demand %.3f W exceeds the %.3f W average "
            "allocation" % (average, average_allocation)
        )
    for record in records:
        if not record["switch_compliant"]:
            findings.append(
                "%s: worst-case current %.3f A leaves no headroom against the "
                "derated switch rating"
                % (record["name"], record["current_at_max_bus_a"])
            )
    if not torque_ok:
        findings.append(
            "thermal disturbance torque %.3e Nm exceeds the %.3e Nm allocated "
            "to attitude control" % (torque, torque_allocation)
        )
    return {
        "circuits": records,
        "peak_demand_w": peak,
        "orbit_average_demand_w": average,
        "peak_allocation_w": peak_allocation,
        "average_allocation_w": average_allocation,
        "dissipation_w_by_mode": dissipation,
        "disturbance_torque_nm": torque,
        "torque_allocation_nm": torque_allocation,
        "compliant": peak_ok and average_ok and torque_ok
        and all(record["switch_compliant"] for record in records),
        "findings": findings,
    }
