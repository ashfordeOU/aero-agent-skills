#!/usr/bin/env python3
"""Single axial compressor stage velocity-triangle logic.

Convention (Dixon): flow angles are measured from the axial direction,
all angles in RADIANS. A compressor stage adds work to the flow, so the
absolute flow angle grows across the rotor (alpha2 > alpha1 gives
positive specific work). tan(beta) = u/ca - tan(alpha) relates the
relative flow angles beta to the absolute angles alpha at the same
axial station.

Quantities (SI units throughout):
- blade speed u in m/s
- axial velocity ca in m/s
- absolute flow angles alpha1 (rotor inlet), alpha2 (rotor outlet) in rad
- relative flow angles beta1 (rotor inlet), beta2 (rotor outlet) in rad
- stagnation inlet temperature t01 in K
- specific work w in J/kg
- flow coefficient phi = ca/u, dimensionless
- work coefficient psi = w/u^2, dimensionless
- degree of reaction r, dimensionless
- stage pressure ratio pi, dimensionless
- cp in J/(kg K), gamma dimensionless, eta (polytropic stage
  efficiency) dimensionless

FAR-33 is referenced, not reproduced; the velocity-triangle relations
are common turbomachinery methodology summarized per standards-map.yaml.

Functions raise ValueError on non-physical inputs (u <= 0, ca <= 0,
t01 <= 0) instead of returning nonsense or dividing by zero.
"""

import math


def specific_work(u, ca, alpha1, alpha2):
    """Specific work of the stage, w = u*ca*(tan(alpha2) - tan(alpha1)) in J/kg.

    Positive when the rotor turns the flow through a larger absolute
    angle (alpha2 > alpha1), which is the compressor (work-adding) case.
    """
    if u <= 0:
        raise ValueError("u must be > 0, got %r" % (u,))
    if ca <= 0:
        raise ValueError("ca must be > 0, got %r" % (ca,))
    return u * ca * (math.tan(alpha2) - math.tan(alpha1))


def flow_coefficient(ca, u):
    """Flow coefficient phi = ca/u, dimensionless."""
    if u <= 0:
        raise ValueError("u must be > 0, got %r" % (u,))
    return ca / u


def work_coefficient(u, ca, alpha1, alpha2):
    """Work coefficient psi = w/u^2, dimensionless."""
    return specific_work(u, ca, alpha1, alpha2) / (u * u)


def degree_of_reaction(ca, u, beta1, beta2):
    """Degree of reaction r = ca/(2*u) * (tan(beta1) - tan(beta2)).

    Dimensionless; 0.5 for a symmetric 50% reaction stage. beta1 and
    beta2 are the relative flow angles at rotor inlet and outlet in
    radians.
    """
    if u <= 0:
        raise ValueError("u must be > 0, got %r" % (u,))
    if ca <= 0:
        raise ValueError("ca must be > 0, got %r" % (ca,))
    return ca / (2.0 * u) * (math.tan(beta1) - math.tan(beta2))


def stage_pressure_ratio(u, ca, alpha1, alpha2, t01, eta=0.9, cp=1005.0,
                         gamma=1.4):
    """Stage pressure ratio from the specific work and the stage efficiency.

    pi = (1 + eta*w/(cp*t01))**(gamma/(gamma-1)), with w from
    specific_work(u, ca, alpha1, alpha2). t01 is the stagnation inlet
    temperature in K; eta defaults to 0.9, cp to 1005 J/(kg K),
    gamma to 1.4 (air-standard values).
    """
    if t01 <= 0:
        raise ValueError("t01 must be > 0, got %r" % (t01,))
    w = specific_work(u, ca, alpha1, alpha2)
    return (1.0 + eta * w / (cp * t01)) ** (gamma / (gamma - 1.0))


def stage_properties(u, ca, alpha1, alpha2, beta1, beta2, t01, eta=0.9):
    """Full velocity-triangle stage assessment as a dict.

    Returns specific_work (J/kg), phi, psi, reaction (dimensionless),
    and pressure_ratio (dimensionless, air-standard cp and gamma).
    """
    w = specific_work(u, ca, alpha1, alpha2)
    return {
        "specific_work": w,
        "phi": flow_coefficient(ca, u),
        "psi": work_coefficient(u, ca, alpha1, alpha2),
        "reaction": degree_of_reaction(ca, u, beta1, beta2),
        "pressure_ratio": stage_pressure_ratio(u, ca, alpha1, alpha2, t01,
                                               eta=eta),
    }
