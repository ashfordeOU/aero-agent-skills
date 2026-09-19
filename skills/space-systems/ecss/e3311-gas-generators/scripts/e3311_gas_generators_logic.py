"""Performance and output screen for a pyrotechnic gas generator.

Anchor: ECSS-E-ST-33-11C clause 4.11.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A gas generator is a charge chosen for what it produces rather than
for what it breaks: a quantity of gas, at a temperature, delivered
into a closed volume inside a required time. That makes its screen a
two-sided one. The cold, light, large-volume corner has to still
develop enough pressure to move the actuator; the hot, heavy,
small-volume corner has to stay inside what the receiver can hold.

The delivered pressure is computed rather than quoted:

    moles     = grain mass x specific gas yield
    pressure  = moles x R x delivered gas temperature / free volume

and both extreme corners are evaluated from the same expression, with
mass, volume and conditioning temperature pushed to opposite bounds.

The screen then runs five gates:

    actuation    the cold-corner pressure against the pressure the
                 actuator needs, with margin
    structural   the hot-corner pressure against the receiver's
                 working pressure, and the burst pressure against the
                 hot corner, with margin
    rise-time    measured pressure rise against the actuator's limit
    thermal      hot-corner gas temperature against the seal limit
    particulate  solid products against what the receiver tolerates

Limits are declared policy, not physical constants: the defaults below
are a starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

UNIVERSAL_GAS_CONSTANT_J_PER_MOL_K = 8.314462618

PASCAL_PER_MEGAPASCAL = 1.0e6

GATES = ("actuation", "structural", "rise-time", "thermal", "particulate")

VERDICT_MET = "gas-generator-output-met"
VERDICT_NOT_MET = "gas-generator-output-not-met"

DEFAULT_GAS_GENERATOR_POLICY = {
    "min_actuation_margin": 1.25,
    "min_burst_margin": 2.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    value = _require_number(name, value)
    if value < 0.0 or value >= 1.0:
        raise ValueError(
            "%s must be a fraction in [0, 1), got %r" % (name, value)
        )
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A corner pressure is a product of four measured quantities, so a
    design sitting exactly on a limit can land a few units in the last
    place above it. The limit is never relaxed; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_gas_generator_policy(policy):
    """Check a policy carries both margins the output gates need."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in ("min_actuation_margin", "min_burst_margin"):
        _require_positive("policy %s" % key, policy.get(key))
    if not _at_least(policy["min_actuation_margin"], 1.0):
        raise ValueError(
            "policy min_actuation_margin must be at least 1.0, got %r"
            % (policy["min_actuation_margin"],)
        )
    if not _at_least(policy["min_burst_margin"], 1.0):
        raise ValueError(
            "policy min_burst_margin must be at least 1.0, got %r"
            % (policy["min_burst_margin"],)
        )
    return policy


def validate_generator(record):
    """Normalize one gas generator into a checked record."""
    if not isinstance(record, dict):
        raise ValueError("generator must be a mapping, got %r" % (record,))
    generator_id = _require_text("generator id", record.get("id"))
    return {
        "id": generator_id,
        "grain_mass_g": _require_positive(
            "generator %s grain_mass_g" % generator_id, record.get("grain_mass_g")
        ),
        "mass_tolerance_fraction": _require_fraction(
            "generator %s mass_tolerance_fraction" % generator_id,
            record.get("mass_tolerance_fraction", 0.0),
        ),
        "gas_yield_mol_per_g": _require_positive(
            "generator %s gas_yield_mol_per_g" % generator_id,
            record.get("gas_yield_mol_per_g"),
        ),
        "flame_temperature_k": _require_positive(
            "generator %s flame_temperature_k" % generator_id,
            record.get("flame_temperature_k"),
        ),
        "temperature_sensitivity_k_per_k": _require_non_negative(
            "generator %s temperature_sensitivity_k_per_k" % generator_id,
            record.get("temperature_sensitivity_k_per_k", 0.0),
        ),
        "reference_conditioning_k": _require_positive(
            "generator %s reference_conditioning_k" % generator_id,
            record.get("reference_conditioning_k"),
        ),
        "measured_rise_time_s": _require_positive(
            "generator %s measured_rise_time_s" % generator_id,
            record.get("measured_rise_time_s"),
        ),
        "particulate_mg": _require_non_negative(
            "generator %s particulate_mg" % generator_id,
            record.get("particulate_mg", 0.0),
        ),
    }


def validate_receiver(record):
    """Normalize the volume the generator discharges into."""
    if not isinstance(record, dict):
        raise ValueError("receiver must be a mapping, got %r" % (record,))
    receiver_id = _require_text("receiver id", record.get("id"))
    working = _require_positive(
        "receiver %s max_allowable_working_pressure_mpa" % receiver_id,
        record.get("max_allowable_working_pressure_mpa"),
    )
    burst = _require_positive(
        "receiver %s burst_pressure_mpa" % receiver_id,
        record.get("burst_pressure_mpa"),
    )
    if burst < working:
        raise ValueError(
            "receiver %s declares a burst pressure below its working pressure"
            % receiver_id
        )
    return {
        "id": receiver_id,
        "free_volume_m3": _require_positive(
            "receiver %s free_volume_m3" % receiver_id, record.get("free_volume_m3")
        ),
        "volume_tolerance_fraction": _require_fraction(
            "receiver %s volume_tolerance_fraction" % receiver_id,
            record.get("volume_tolerance_fraction", 0.0),
        ),
        "required_actuation_pressure_mpa": _require_positive(
            "receiver %s required_actuation_pressure_mpa" % receiver_id,
            record.get("required_actuation_pressure_mpa"),
        ),
        "max_allowable_working_pressure_mpa": working,
        "burst_pressure_mpa": burst,
        "max_rise_time_s": _require_positive(
            "receiver %s max_rise_time_s" % receiver_id,
            record.get("max_rise_time_s"),
        ),
        "max_gas_temperature_k": _require_positive(
            "receiver %s max_gas_temperature_k" % receiver_id,
            record.get("max_gas_temperature_k"),
        ),
        "max_particulate_mg": _require_positive(
            "receiver %s max_particulate_mg" % receiver_id,
            record.get("max_particulate_mg"),
        ),
    }


def validate_conditioning_case(case):
    """Normalize the cold and hot conditioning temperatures."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    cold = _require_positive("case cold_conditioning_k", case.get("cold_conditioning_k"))
    hot = _require_positive("case hot_conditioning_k", case.get("hot_conditioning_k"))
    if hot < cold:
        raise ValueError("case hot conditioning is below the cold conditioning")
    return {"cold_conditioning_k": cold, "hot_conditioning_k": hot}


def generated_moles(record, mass_g=None):
    """Moles of gas a given grain mass yields."""
    generator = validate_generator(record)
    mass = generator["grain_mass_g"] if mass_g is None else _require_positive(
        "mass_g", mass_g
    )
    return mass * generator["gas_yield_mol_per_g"]


def delivered_gas_temperature_k(record, conditioning_k):
    """Gas temperature the grain delivers at a conditioning temperature."""
    generator = validate_generator(record)
    conditioning = _require_positive("conditioning_k", conditioning_k)
    temperature = generator["flame_temperature_k"] + generator[
        "temperature_sensitivity_k_per_k"
    ] * (conditioning - generator["reference_conditioning_k"])
    if temperature <= 0.0:
        raise ValueError(
            "generator %s delivers a non-physical gas temperature at %.2f K"
            % (generator["id"], conditioning)
        )
    return temperature


def delivered_pressure_mpa(moles, temperature_k, volume_m3):
    """Closed-volume pressure from an ideal-gas charge, in megapascal."""
    quantity = _require_positive("moles", moles)
    temperature = _require_positive("temperature_k", temperature_k)
    volume = _require_positive("volume_m3", volume_m3)
    pascal = (
        quantity * UNIVERSAL_GAS_CONSTANT_J_PER_MOL_K * temperature / volume
    )
    return pascal / PASCAL_PER_MEGAPASCAL


def worst_case_output(generator, receiver, case):
    """Cold-light-large and hot-heavy-small corners of the output."""
    unit = validate_generator(generator)
    volume = validate_receiver(receiver)
    conditioning = validate_conditioning_case(case)
    cold_mass = unit["grain_mass_g"] * (1.0 - unit["mass_tolerance_fraction"])
    hot_mass = unit["grain_mass_g"] * (1.0 + unit["mass_tolerance_fraction"])
    large_volume = volume["free_volume_m3"] * (
        1.0 + volume["volume_tolerance_fraction"]
    )
    small_volume = volume["free_volume_m3"] * (
        1.0 - volume["volume_tolerance_fraction"]
    )
    cold_temperature = delivered_gas_temperature_k(
        generator, conditioning["cold_conditioning_k"]
    )
    hot_temperature = delivered_gas_temperature_k(
        generator, conditioning["hot_conditioning_k"]
    )
    return {
        "cold_pressure_mpa": delivered_pressure_mpa(
            generated_moles(generator, cold_mass), cold_temperature, large_volume
        ),
        "hot_pressure_mpa": delivered_pressure_mpa(
            generated_moles(generator, hot_mass), hot_temperature, small_volume
        ),
        "cold_gas_temperature_k": cold_temperature,
        "hot_gas_temperature_k": hot_temperature,
        "cold_mass_g": cold_mass,
        "hot_mass_g": hot_mass,
        "large_volume_m3": large_volume,
        "small_volume_m3": small_volume,
    }


def actuation_verdict(
    generator, receiver, case, policy=DEFAULT_GAS_GENERATOR_POLICY
):
    """Grade the cold corner against the pressure the actuator needs."""
    validate_gas_generator_policy(policy)
    unit = validate_generator(generator)
    volume = validate_receiver(receiver)
    corners = worst_case_output(generator, receiver, case)
    margin = (
        corners["cold_pressure_mpa"] / volume["required_actuation_pressure_mpa"]
    )
    ok = _at_least(margin, policy["min_actuation_margin"])
    findings = []
    if not ok:
        findings.append(
            "%s develops %.4f MPa in the cold corner against a %.4f MPa "
            "actuation requirement, a margin of %.3f below the required %.3f"
            % (
                unit["id"],
                corners["cold_pressure_mpa"],
                volume["required_actuation_pressure_mpa"],
                margin,
                policy["min_actuation_margin"],
            )
        )
    return {
        "gate": "actuation",
        "cold_pressure_mpa": corners["cold_pressure_mpa"],
        "actuation_margin": margin,
        "compliant": ok,
        "findings": findings,
    }


def structural_verdict(
    generator, receiver, case, policy=DEFAULT_GAS_GENERATOR_POLICY
):
    """Grade the hot corner against working and burst pressure."""
    validate_gas_generator_policy(policy)
    unit = validate_generator(generator)
    volume = validate_receiver(receiver)
    corners = worst_case_output(generator, receiver, case)
    peak = corners["hot_pressure_mpa"]
    burst_margin = volume["burst_pressure_mpa"] / peak
    findings = []
    if not _at_most(peak, volume["max_allowable_working_pressure_mpa"]):
        findings.append(
            "%s peaks at %.4f MPa in the hot corner, above the %.4f MPa the "
            "receiver is allowed to work at"
            % (unit["id"], peak, volume["max_allowable_working_pressure_mpa"])
        )
    if not _at_least(burst_margin, policy["min_burst_margin"]):
        findings.append(
            "%s peaks at %.4f MPa against a %.4f MPa burst pressure, a margin "
            "of %.3f below the required %.3f"
            % (
                unit["id"],
                peak,
                volume["burst_pressure_mpa"],
                burst_margin,
                policy["min_burst_margin"],
            )
        )
    return {
        "gate": "structural",
        "hot_pressure_mpa": peak,
        "burst_margin": burst_margin,
        "compliant": not findings,
        "findings": findings,
    }


def rise_time_verdict(generator, receiver):
    """Grade the measured pressure rise against the actuator's limit."""
    unit = validate_generator(generator)
    volume = validate_receiver(receiver)
    ok = _at_most(unit["measured_rise_time_s"], volume["max_rise_time_s"])
    findings = []
    if not ok:
        findings.append(
            "%s reaches pressure in %.5f s, above the %.5f s the actuator "
            "allows" % (unit["id"], unit["measured_rise_time_s"], volume["max_rise_time_s"])
        )
    return {"gate": "rise-time", "compliant": ok, "findings": findings}


def thermal_verdict(generator, receiver, case):
    """Grade the hot-corner gas temperature against the seal limit."""
    unit = validate_generator(generator)
    volume = validate_receiver(receiver)
    corners = worst_case_output(generator, receiver, case)
    hot = corners["hot_gas_temperature_k"]
    ok = _at_most(hot, volume["max_gas_temperature_k"])
    findings = []
    if not ok:
        findings.append(
            "%s delivers gas at %.2f K in the hot corner, above the %.2f K "
            "the receiver seals tolerate"
            % (unit["id"], hot, volume["max_gas_temperature_k"])
        )
    return {
        "gate": "thermal",
        "hot_gas_temperature_k": hot,
        "compliant": ok,
        "findings": findings,
    }


def particulate_verdict(generator, receiver):
    """Grade solid combustion products against the receiver's allowance."""
    unit = validate_generator(generator)
    volume = validate_receiver(receiver)
    ok = _at_most(unit["particulate_mg"], volume["max_particulate_mg"])
    findings = []
    if not ok:
        findings.append(
            "%s leaves %.2f mg of solid products, above the %.2f mg the "
            "receiver tolerates"
            % (unit["id"], unit["particulate_mg"], volume["max_particulate_mg"])
        )
    return {"gate": "particulate", "compliant": ok, "findings": findings}


def assess_gas_generator(
    generator, receiver, case, policy=DEFAULT_GAS_GENERATOR_POLICY
):
    """Full clause 4.11.6 output screen over one generator and receiver."""
    validate_gas_generator_policy(policy)
    unit = validate_generator(generator)
    corners = worst_case_output(generator, receiver, case)
    gates = {
        "actuation": actuation_verdict(generator, receiver, case, policy),
        "structural": structural_verdict(generator, receiver, case, policy),
        "rise-time": rise_time_verdict(generator, receiver),
        "thermal": thermal_verdict(generator, receiver, case),
        "particulate": particulate_verdict(generator, receiver),
    }
    findings = []
    failed = []
    for name in GATES:
        gate = gates[name]
        findings.extend(gate["findings"])
        if not gate["compliant"]:
            failed.append(name)
    compliant = not failed
    return {
        "id": unit["id"],
        "corners": corners,
        "gates": gates,
        "failed_gates": failed,
        "compliant": compliant,
        "verdict": VERDICT_MET if compliant else VERDICT_NOT_MET,
        "findings": findings,
    }
