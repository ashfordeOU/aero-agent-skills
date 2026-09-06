"""Exact constant-property solution for compressible Couette flow in a
high-Mach plate gap (aerodynamics/high-speed/compressible-couette-flow).

Pure stdlib math only. A stationary cold plate at y = 0 held at the
reference static temperature T_e and an insulated (adiabatic) moving
plate at y = h dragged at the edge velocity Ue = Me * a(T_e) shear the
gas between them. The velocity profile is exactly linear, the
temperature profile follows the Crocco energy integral over that linear
profile, and every joule of viscous dissipation leaves through the
stationary plate because the moving plate lets no heat through. The
model is laminar and Sutherland-free: mu and k are uniform constants and
the conductivity is derived as k = mu * cp / Pr, never an independent
input. The recovery factor of the insulated moving plate is the Prandtl
number itself, r = Pr, the constant-property Couette identity.
"""

import math

GAMMA = 1.4
R = 287.0
# Specific heat at constant pressure, DERIVED as GAMMA * R / (GAMMA - 1)
# so the temperature-dissipation identities close exactly in float math.
CP = GAMMA * R / (GAMMA - 1.0)
PR = 0.72
MU = 1.8e-5


def recovery_factor(pr):
    """Return the constant-property Couette recovery factor r = Pr.

    The recovery factor of the insulated moving plate equals the
    Prandtl number exactly for constant-property Couette flow (the
    external-plate values sqrt(Pr) or Pr^(1/3) do not apply here).
    """
    if pr <= 0:
        raise ValueError("recovery_factor: Prandtl number pr must be > 0")
    return pr


def edge_velocity(me, t_e, gamma=GAMMA, r=R):
    """Return the moving-plate edge velocity Ue = Me * sqrt(gamma R T_e).

    The edge sound speed of the stationary-plate gas is
    a_e = sqrt(gamma * r * t_e); the insulated moving plate drags the
    gas at Me times that speed.
    """
    if me <= 0:
        raise ValueError("edge_velocity: plate Mach number me must be > 0")
    if t_e <= 0:
        raise ValueError("edge_velocity: static temperature t_e must be > 0")
    if gamma <= 0:
        raise ValueError("edge_velocity: gamma must be > 0")
    if r <= 0:
        raise ValueError("edge_velocity: gas constant r must be > 0")
    return me * math.sqrt(gamma * r * t_e)


def adiabatic_wall_temperature(t_e, me, pr, gamma=GAMMA):
    """Return the insulated moving-plate temperature
    T_aw = t_e * (1 + pr * (gamma - 1) / 2 * me^2), K.

    The moving plate is not cooled, so its surface floats to the
    recovery temperature of the moving wall; the constant-property
    recovery factor r = pr makes this identical to
    t_e + pr * Ue^2 / (2 cp) with cp = gamma * R / (gamma - 1).
    """
    if t_e <= 0:
        raise ValueError("adiabatic_wall_temperature: t_e must be > 0")
    if me <= 0:
        raise ValueError("adiabatic_wall_temperature: me must be > 0")
    if pr <= 0:
        raise ValueError("adiabatic_wall_temperature: pr must be > 0")
    if gamma <= 0:
        raise ValueError("adiabatic_wall_temperature: gamma must be > 0")
    return t_e * (1.0 + pr * (gamma - 1.0) / 2.0 * me * me)


def velocity_profile(y, h, u_e):
    """Return the linear gap velocity u = u_e * y / h at height y, m/s.

    The shear-driven Couette profile between parallel plates is exactly
    linear: u(0) = 0 at the stationary plate and u(h) = u_e at the
    moving plate.
    """
    if h <= 0:
        raise ValueError("velocity_profile: gap height h must be > 0")
    if u_e <= 0:
        raise ValueError("velocity_profile: edge velocity u_e must be > 0")
    if y < 0.0 or y > h:
        raise ValueError("velocity_profile: y must lie inside [0, h]")
    return u_e * y / h


def temperature_profile(y, h, t_e, me, pr, gamma=GAMMA):
    """Return the Crocco energy-integral temperature T(y), K.

    T = t_e * (1 + pr * (gamma - 1) / 2 * me^2 * (2 eta - eta^2)) with
    eta = y / h, the energy-integral profile over the linear velocity
    profile: T(0) = T_e at the cold plate, T(h) = T_aw at the insulated
    moving plate, and dT/dy(h) = 0 because the moving plate is
    adiabatic.
    """
    if h <= 0:
        raise ValueError("temperature_profile: gap height h must be > 0")
    if t_e <= 0:
        raise ValueError("temperature_profile: t_e must be > 0")
    if me <= 0:
        raise ValueError("temperature_profile: me must be > 0")
    if pr <= 0:
        raise ValueError("temperature_profile: pr must be > 0")
    if gamma <= 0:
        raise ValueError("temperature_profile: gamma must be > 0")
    if y < 0.0 or y > h:
        raise ValueError("temperature_profile: y must lie inside [0, h]")
    eta = y / h
    return t_e * (1.0 + pr * (gamma - 1.0) / 2.0 * me * me
                  * (2.0 * eta - eta * eta))


def temperature_gradient(y, h, t_e, me, pr, gamma=GAMMA):
    """Return the analytic profile gradient dT/dy = t_e * pr *
    (gamma - 1) * me^2 * (1 - eta) / h at height y, K/m.

    The gradient is positive at the stationary plate (temperature rises
    away from the cold plate, so conduction carries heat into it) and
    zero at y = h, the insulated moving plate.
    """
    if h <= 0:
        raise ValueError("temperature_gradient: gap height h must be > 0")
    if t_e <= 0:
        raise ValueError("temperature_gradient: t_e must be > 0")
    if me <= 0:
        raise ValueError("temperature_gradient: me must be > 0")
    if pr <= 0:
        raise ValueError("temperature_gradient: pr must be > 0")
    if gamma <= 0:
        raise ValueError("temperature_gradient: gamma must be > 0")
    if y < 0.0 or y > h:
        raise ValueError("temperature_gradient: y must lie inside [0, h]")
    eta = y / h
    return t_e * pr * (gamma - 1.0) * me * me * (1.0 - eta) / h


def wall_shear(u_e, mu, h):
    """Return the wall shear tau_w = mu * u_e / h, Pa.

    The shear is constant across the gap because the velocity profile
    is linear.
    """
    if u_e <= 0:
        raise ValueError("wall_shear: edge velocity u_e must be > 0")
    if mu <= 0:
        raise ValueError("wall_shear: viscosity mu must be > 0")
    if h <= 0:
        raise ValueError("wall_shear: gap height h must be > 0")
    return mu * u_e / h


def wall_heat_flux(u_e, mu, h):
    """Return the heat flux q_w = mu * u_e^2 / h into the stationary
    plate, W/m2.

    Positive means the gas loses heat to the cold plate; the moving
    plate is insulated so its flux is zero. The closed form equals
    tau_w * u_e (viscous work per unit area) and the dissipation
    integral mu * (u_e / h)^2 * h across the gap.
    """
    if u_e <= 0:
        raise ValueError("wall_heat_flux: edge velocity u_e must be > 0")
    if mu <= 0:
        raise ValueError("wall_heat_flux: viscosity mu must be > 0")
    if h <= 0:
        raise ValueError("wall_heat_flux: gap height h must be > 0")
    return mu * u_e * u_e / h


def couette_solution(t_e, me, pr, mu, rho, h, gamma=GAMMA, r=R):
    """Return the full plate-gap solution as a dict with keys exactly
    Ue, T_aw, tau_w, q_w, r, Re_gap.

    Ue comes from edge_velocity, T_aw from adiabatic_wall_temperature,
    tau_w from wall_shear, q_w from wall_heat_flux, r from
    recovery_factor, and Re_gap = rho * Ue * h / mu is the laminar
    regime indicator. tau_w and q_w are independent of rho in
    constant-property Couette flow; rho enters only through Re_gap.
    """
    if t_e <= 0:
        raise ValueError("couette_solution: t_e must be > 0")
    if me <= 0:
        raise ValueError("couette_solution: me must be > 0")
    if pr <= 0:
        raise ValueError("couette_solution: pr must be > 0")
    if mu <= 0:
        raise ValueError("couette_solution: mu must be > 0")
    if rho <= 0:
        raise ValueError("couette_solution: rho must be > 0")
    if h <= 0:
        raise ValueError("couette_solution: gap height h must be > 0")
    if gamma <= 0:
        raise ValueError("couette_solution: gamma must be > 0")
    if r <= 0:
        raise ValueError("couette_solution: gas constant r must be > 0")
    u_e = edge_velocity(me, t_e, gamma, r)
    t_aw = adiabatic_wall_temperature(t_e, me, pr, gamma)
    tau_w = wall_shear(u_e, mu, h)
    q_w = wall_heat_flux(u_e, mu, h)
    return {
        "Ue": u_e,
        "T_aw": t_aw,
        "tau_w": tau_w,
        "q_w": q_w,
        "r": recovery_factor(pr),
        "Re_gap": rho * u_e * h / mu,
    }
