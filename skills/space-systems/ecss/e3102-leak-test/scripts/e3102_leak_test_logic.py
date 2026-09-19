"""Leak test definition for two-phase heat transport equipment.

Anchor: ECSS-E-ST-31-02C clause 5.6.8 (leak test: method, sensitivity,
acceptance leak rate). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. The acceptance leak rate is derived, not quoted. The fluid inventory a
   two-phase item is allowed to lose over its life, expressed as a mass, is
   converted to a throughput in Pa*m3/s through the specific gas constant of
   the working fluid, the reference temperature and the mission duration.
2. The method is selected from the recognised set, each of which carries a
   best achievable sensitivity. A method whose sensitivity is not finer than
   the acceptance rate by the resolution ratio cannot demonstrate the
   acceptance rate at all, and choosing it is a finding about the test
   definition rather than a result about the article.
3. A helium tracer measurement is not the service leak rate. In molecular
   flow the throughput scales with the inverse square root of molar mass, so
   a helium reading is converted to the working fluid before it is graded.
4. Acceptance is the converted service leak rate against the derived
   allowable, with the measurement itself required to sit above the
   instrument sensitivity to be a reading rather than a noise floor.
"""

import math

__all__ = [
    "LEAK_TOLERANCE",
    "UNIVERSAL_GAS_CONSTANT",
    "HELIUM_MOLAR_MASS_KG_PER_MOL",
    "METHOD_SENSITIVITY_PA_M3_PER_S",
    "DEFAULT_SENSITIVITY_RATIO",
    "require_real",
    "require_positive",
    "specific_gas_constant",
    "allowable_leak_rate_pa_m3_per_s",
    "validate_method",
    "method_sensitivity",
    "tracer_to_service_rate",
    "assess_sensitivity",
    "assess_measured_rate",
    "assess_leak_test",
]

# Rate and sensitivity grades are float comparisons a correct test lands
# exactly on. Absorb the representation error, never the requirement.
LEAK_TOLERANCE = 1e-12

UNIVERSAL_GAS_CONSTANT = 8.314462618

HELIUM_MOLAR_MASS_KG_PER_MOL = 4.002602e-3

# Best achievable sensitivity of each recognised method, in Pa*m3/s.
METHOD_SENSITIVITY_PA_M3_PER_S = {
    "helium-mass-spectrometer-vacuum-chamber": 1.0e-11,
    "helium-mass-spectrometer-sniffer": 1.0e-8,
    "helium-accumulation": 1.0e-9,
    "pressure-decay": 1.0e-5,
    "bubble-immersion": 1.0e-4,
}

# The instrument has to resolve the acceptance rate by this factor before a
# reading at the acceptance rate means anything.
DEFAULT_SENSITIVITY_RATIO = 10.0


def require_real(label, value):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def require_positive(label, value):
    """Return value as a strictly positive finite float or raise ValueError."""
    out = require_real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _at_most(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value < limit or math.isclose(value, limit, rel_tol=1e-12,
                                         abs_tol=LEAK_TOLERANCE)


def _at_least(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value > limit or math.isclose(value, limit, rel_tol=1e-12,
                                         abs_tol=LEAK_TOLERANCE)


def specific_gas_constant(molar_mass_kg_per_mol):
    """Return the specific gas constant of a fluid in J/(kg*K)."""
    molar_mass = require_positive("molar_mass_kg_per_mol", molar_mass_kg_per_mol)
    if molar_mass > 1.0:
        raise ValueError(
            "molar_mass_kg_per_mol %g looks like g/mol; this routine wants kg/mol"
            % molar_mass
        )
    return UNIVERSAL_GAS_CONSTANT / molar_mass


def allowable_leak_rate_pa_m3_per_s(allowed_mass_loss_kg, molar_mass_kg_per_mol,
                                    reference_temperature_k, lifetime_s):
    """Derive the acceptance leak rate from the allowed inventory loss.

    The mass the item may lose over its life becomes a throughput through
    p*V = m*R_specific*T divided by the mission duration.
    """
    mass = require_positive("allowed_mass_loss_kg", allowed_mass_loss_kg)
    temperature = require_positive("reference_temperature_k", reference_temperature_k)
    lifetime = require_positive("lifetime_s", lifetime_s)
    r_specific = specific_gas_constant(molar_mass_kg_per_mol)
    return mass * r_specific * temperature / lifetime


def validate_method(method):
    """Return the normalised leak-test method or raise ValueError."""
    if not isinstance(method, str) or not method.strip():
        raise ValueError("leak-test method must be a non-empty string")
    name = method.strip().lower()
    if name not in METHOD_SENSITIVITY_PA_M3_PER_S:
        raise ValueError("unrecognised leak-test method %r; expected one of %s"
                         % (method, ", ".join(sorted(METHOD_SENSITIVITY_PA_M3_PER_S))))
    return name


def method_sensitivity(method, declared_sensitivity=None):
    """Return the sensitivity to grade with, in Pa*m3/s.

    A declared facility sensitivity is honoured, but never one finer than the
    method can physically reach.
    """
    name = validate_method(method)
    best = METHOD_SENSITIVITY_PA_M3_PER_S[name]
    if declared_sensitivity is None:
        return name, best
    declared = require_positive("declared_sensitivity", declared_sensitivity)
    if declared < best and not math.isclose(declared, best, rel_tol=1e-12,
                                            abs_tol=0.0):
        raise ValueError(
            "declared sensitivity %g is finer than the best %g the '%s' method "
            "reaches" % (declared, best, name)
        )
    return name, declared


def tracer_to_service_rate(tracer_rate, service_molar_mass_kg_per_mol,
                           tracer_molar_mass_kg_per_mol=HELIUM_MOLAR_MASS_KG_PER_MOL):
    """Convert a tracer-gas throughput to the working-fluid throughput.

    Molecular-flow throughput scales with the inverse square root of molar
    mass, so a light tracer over-reads relative to a heavier working fluid.
    """
    rate = require_positive("tracer_rate", tracer_rate)
    service = require_positive("service_molar_mass_kg_per_mol",
                               service_molar_mass_kg_per_mol)
    tracer = require_positive("tracer_molar_mass_kg_per_mol",
                              tracer_molar_mass_kg_per_mol)
    if service > 1.0 or tracer > 1.0:
        raise ValueError("molar masses must be in kg/mol, not g/mol")
    return rate * math.sqrt(tracer / service)


def assess_sensitivity(method, acceptance_rate, declared_sensitivity=None,
                       ratio=DEFAULT_SENSITIVITY_RATIO):
    """Grade the instrument sensitivity against the acceptance rate."""
    acceptance = require_positive("acceptance_rate", acceptance_rate)
    resolution = require_positive("ratio", ratio)
    name, sensitivity = method_sensitivity(method, declared_sensitivity)
    required = acceptance / resolution
    adequate = _at_most(sensitivity, required)
    findings = []
    if not adequate:
        findings.append(
            "method '%s' resolves %.6g Pa*m3/s; %.6g Pa*m3/s is needed to "
            "demonstrate an acceptance rate of %.6g Pa*m3/s"
            % (name, sensitivity, required, acceptance)
        )
    return {
        "method": name,
        "sensitivity_pa_m3_per_s": sensitivity,
        "required_sensitivity_pa_m3_per_s": required,
        "acceptance_rate_pa_m3_per_s": acceptance,
        "resolution_ratio": resolution,
        "compliant": adequate,
        "findings": findings,
    }


def assess_measured_rate(measured_rate, acceptance_rate, sensitivity=None):
    """Grade a measured service leak rate against the acceptance rate."""
    measured = require_positive("measured_rate", measured_rate)
    acceptance = require_positive("acceptance_rate", acceptance_rate)
    within = _at_most(measured, acceptance)
    findings = []
    if not within:
        findings.append("measured leak rate %.6g Pa*m3/s exceeds the acceptance "
                        "rate %.6g Pa*m3/s" % (measured, acceptance))
    above_floor = True
    if sensitivity is not None:
        floor = require_positive("sensitivity", sensitivity)
        above_floor = _at_least(measured, floor)
        if not above_floor:
            findings.append(
                "measured %.6g Pa*m3/s sits below the instrument floor %.6g "
                "Pa*m3/s; the result is a non-detection, not a measured rate"
                % (measured, floor)
            )
    return {
        "measured_rate_pa_m3_per_s": measured,
        "acceptance_rate_pa_m3_per_s": acceptance,
        "margin": acceptance - measured,
        "within_acceptance": within,
        "above_instrument_floor": above_floor,
        "compliant": within,
        "findings": findings,
    }


def assess_leak_test(spec):
    """Run the whole clause 5.6.8 leak test assessment.

    spec keys: method, allowed_mass_loss_kg, molar_mass_kg_per_mol,
    reference_temperature_k, lifetime_s, measured_tracer_rate; optional
    declared_sensitivity, tracer_molar_mass_kg_per_mol, resolution_ratio,
    acceptance_rate_pa_m3_per_s (an explicit override of the derivation).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("method", "allowed_mass_loss_kg", "molar_mass_kg_per_mol",
                "reference_temperature_k", "lifetime_s", "measured_tracer_rate"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    derived = allowable_leak_rate_pa_m3_per_s(
        spec["allowed_mass_loss_kg"], spec["molar_mass_kg_per_mol"],
        spec["reference_temperature_k"], spec["lifetime_s"],
    )
    acceptance = derived
    if spec.get("acceptance_rate_pa_m3_per_s") is not None:
        acceptance = require_positive("acceptance_rate_pa_m3_per_s",
                                      spec["acceptance_rate_pa_m3_per_s"])
    sensitivity = assess_sensitivity(
        spec["method"], acceptance, spec.get("declared_sensitivity"),
        spec.get("resolution_ratio", DEFAULT_SENSITIVITY_RATIO),
    )
    service_rate = tracer_to_service_rate(
        spec["measured_tracer_rate"], spec["molar_mass_kg_per_mol"],
        spec.get("tracer_molar_mass_kg_per_mol", HELIUM_MOLAR_MASS_KG_PER_MOL),
    )
    measurement = assess_measured_rate(
        service_rate, acceptance, sensitivity["sensitivity_pa_m3_per_s"]
    )
    checks = {"sensitivity": sensitivity, "measurement": measurement}
    findings = []
    for name in ("sensitivity", "measurement"):
        for item in checks[name]["findings"]:
            findings.append("%s: %s" % (name, item))
    return {
        "derived_acceptance_rate_pa_m3_per_s": derived,
        "acceptance_rate_pa_m3_per_s": acceptance,
        "service_leak_rate_pa_m3_per_s": service_rate,
        "checks": checks,
        "failed_checks": sorted(n for n in checks if not checks[n]["compliant"]),
        "findings": findings,
        "compliant": all(checks[n]["compliant"] for n in checks),
    }
