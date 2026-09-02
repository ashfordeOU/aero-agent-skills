#!/usr/bin/env python3
"""CFD turbulence modeling logic: y plus and friction velocity.

Common-knowledge summary (standards-map.yaml, naca-tr-824: public
domain reference data): near-wall turbulence modeling sizes the
first cell height with the dimensionless wall distance y+ =
y * u_tau / nu. The friction velocity u_tau = sqrt(tau_w / rho)
follows from the wall shear stress, or from the skin friction
coefficient via u_tau = v_inf * sqrt(cf / 2). The target y+ selects
the turbulence model: resolve the viscous sublayer at y+ about 1,
use wall-resolved blending up to y+ about 30, or rely on wall
functions up to y+ about 300; beyond that the wall treatment must
be re-checked. All inputs are SI: y in meters, u_tau in m/s, nu in
m^2/s, tau_w in Pa, rho in kg/m^3, v_inf in m/s.
"""

import math


def y_plus(y_m, u_tau_ms, nu_m2_s):
    """Dimensionless wall distance y+ = y * u_tau / nu.

    Raises ValueError when y, u_tau, or nu is not positive."""
    if y_m <= 0:
        raise ValueError("y must be > 0, got %r" % (y_m,))
    if u_tau_ms <= 0:
        raise ValueError("u_tau must be > 0, got %r" % (u_tau_ms,))
    if nu_m2_s <= 0:
        raise ValueError("nu must be > 0, got %r" % (nu_m2_s,))
    return y_m * u_tau_ms / nu_m2_s


def friction_velocity(tau_w_pa, rho):
    """Friction velocity u_tau = sqrt(tau_w / rho).

    Raises ValueError when tau_w or rho is not positive."""
    if tau_w_pa <= 0:
        raise ValueError("tau_w must be > 0, got %r" % (tau_w_pa,))
    if rho <= 0:
        raise ValueError("rho must be > 0, got %r" % (rho,))
    return math.sqrt(tau_w_pa / rho)


def friction_velocity_from_cf(cf, v_inf_ms):
    """Friction velocity from skin friction coefficient u_tau = v_inf * sqrt(cf / 2).

    Raises ValueError when cf or v_inf is not positive."""
    if cf <= 0:
        raise ValueError("cf must be > 0, got %r" % (cf,))
    if v_inf_ms <= 0:
        raise ValueError("v_inf must be > 0, got %r" % (v_inf_ms,))
    return v_inf_ms * math.sqrt(cf / 2.0)


def turbulence_model_recommendation(y_plus_target, separated_flow):
    """Recommend a turbulence model for the target y+.

    Mapping: y+ <= 1 -> k-omega-sst; 1 < y+ <= 30 ->
    k-epsilon-realizable; 30 < y+ <= 300 -> sa-wall-function; else
    wall-model-check. separated_flow (bool) does not change the
    mapping but flags cases where a wall-resolved model is preferred
    because wall functions degrade in separated regions; record it
    as a consideration in the recommendation report.

    Raises ValueError when y_plus_target is not positive or
    separated_flow is not a bool."""
    if y_plus_target <= 0:
        raise ValueError("y_plus_target must be > 0, got %r" % (y_plus_target,))
    if not isinstance(separated_flow, bool):
        raise ValueError(
            "separated_flow must be a bool, got %r" % (separated_flow,)
        )
    if y_plus_target <= 1:
        return "k-omega-sst"
    if y_plus_target <= 30:
        return "k-epsilon-realizable"
    if y_plus_target <= 300:
        return "sa-wall-function"
    return "wall-model-check"
