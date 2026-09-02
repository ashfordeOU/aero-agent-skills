#!/usr/bin/env python3
"""Six degree of freedom rigid body aircraft simulation logic (stdlib only, deterministic, offline).

Body-axis equations of motion for a rigid aircraft over a flat,
non-rotating Earth (constant mass, principal inertia axes, products
of inertia zero):
- translational: u_dot = X/m - q w + r v - g sin(theta), with the
  cyclic companions v_dot = Y/m - r u + p w + g sin(phi) cos(theta)
  and w_dot = Z/m - p v + q u + g cos(phi) cos(theta)
- rotational (Euler rigid body equations about principal axes):
  p_dot = (L + (Iyy - Izz) q r) / Ixx,
  q_dot = (M + (Izz - Ixx) r p) / Iyy,
  r_dot = (N + (Ixx - Iyy) p q) / Izz
- Euler angle kinematics:
  phi_dot = p + tan(theta) (q sin(phi) + r cos(phi)),
  theta_dot = q cos(phi) - r sin(phi),
  psi_dot = (q sin(phi) + r cos(phi)) / cos(theta)
- one fourth order Runge Kutta propagation step of the nine state
  components

Conventions: the state vector is (u, v, w, p, q, r, phi, theta, psi):
translational velocities u, v, w in m/s along the body axes (x
forward, y out the right wing, z down), angular rates p, q, r in
rad/s, and the Euler angles phi (roll), theta (pitch), psi (yaw) in
radians. Forces (X, Y, Z) in N and moments (L, M, N) in N m are the
non-gravity body-axis loads (aerodynamic plus thrust); weight enters
through the g terms. Inertia is the tuple (Ixx, Iyy, Izz) in kg m^2.
g defaults to 9.80665 m/s^2 and may be set to zero to isolate the
translational or rotational dynamics.

This is generic rigid-body dynamics (textbook material) paraphrased;
ARP4754A is the pack reference standard (standards-map.yaml) and no
RTCA/SAE/IAQG content is reproduced here.
"""

import math

STATE_NAMES = ("u", "v", "w", "p", "q", "r", "phi", "theta", "psi")

DEFAULT_G = 9.80665


def euler_angle_rates(p, q, r, phi, theta):
    """Euler angle rates from body angular rates and current attitude.

    phi_dot = p + tan(theta) (q sin(phi) + r cos(phi))
    theta_dot = q cos(phi) - r sin(phi)
    psi_dot = (q sin(phi) + r cos(phi)) / cos(theta)

    Angles in radians. Raises ValueError at gimbal lock (theta within
    1e-12 of plus or minus 90 degrees), where psi_dot is singular.
    """
    ct = math.cos(theta)
    if abs(ct) < 1e-12:
        raise ValueError("gimbal lock: theta at plus or minus 90 degrees")
    qsp = q * math.sin(phi)
    rcp = r * math.cos(phi)
    return (
        p + math.tan(theta) * (qsp + rcp),
        q * math.cos(phi) - r * math.sin(phi),
        (qsp + rcp) / ct,
    )


def body_axis_derivative(state, forces, moments, mass, inertia, g=DEFAULT_G):
    """Nine-component state derivative of the body-axis equations.

    state is (u, v, w, p, q, r, phi, theta, psi); forces (X, Y, Z)
    and moments (L, M, N) are the non-gravity body-axis loads; mass in
    kg; inertia (Ixx, Iyy, Izz) in kg m^2. Returns
    (u_dot, v_dot, w_dot, p_dot, q_dot, r_dot, phi_dot, theta_dot,
    psi_dot).
    """
    if len(state) != 9:
        raise ValueError("state must have 9 components")
    if len(forces) != 3 or len(moments) != 3:
        raise ValueError("forces and moments must have 3 components each")
    if mass <= 0.0:
        raise ValueError("mass must be positive")
    ixx, iyy, izz = inertia
    if ixx <= 0.0 or iyy <= 0.0 or izz <= 0.0:
        raise ValueError("principal inertias must be positive")

    u, v, w, p, q, r, phi, theta, psi = state
    fx, fy, fz = forces
    l, m, n = moments

    u_dot = fx / mass - q * w + r * v - g * math.sin(theta)
    v_dot = fy / mass - r * u + p * w + g * math.sin(phi) * math.cos(theta)
    w_dot = fz / mass - p * v + q * u + g * math.cos(phi) * math.cos(theta)

    p_dot = (l + (iyy - izz) * q * r) / ixx
    q_dot = (m + (izz - ixx) * r * p) / iyy
    r_dot = (n + (ixx - iyy) * p * q) / izz

    phi_dot, theta_dot, psi_dot = euler_angle_rates(p, q, r, phi, theta)
    return (u_dot, v_dot, w_dot, p_dot, q_dot, r_dot, phi_dot, theta_dot, psi_dot)


def rk4_core(deriv, y, dt):
    """One fourth order Runge Kutta step for the vector field deriv.

    deriv(y) returns the derivative tuple at y. The update is
    y + dt (k1 + 2 k2 + 2 k3 + k4) / 6 with the classic coefficients;
    the local error is fifth order in dt, so halving the step shrinks
    the error by about a factor of 32. Exact for constant derivatives
    and for derivatives that are polynomials of degree at most four.
    """
    k1 = deriv(y)
    k2 = deriv(tuple(a + 0.5 * dt * b for a, b in zip(y, k1)))
    k3 = deriv(tuple(a + 0.5 * dt * b for a, b in zip(y, k2)))
    k4 = deriv(tuple(a + dt * b for a, b in zip(y, k3)))
    return tuple(a + dt / 6.0 * (b1 + 2.0 * b2 + 2.0 * b3 + b4)
                 for a, b1, b2, b3, b4 in zip(y, k1, k2, k3, k4))


def rk4_step(state, forces, moments, mass, inertia, dt, g=DEFAULT_G):
    """Propagate the nine-component state one step with RK4.

    Equivalent to rk4_core over the body-axis equations of motion; a
    zero state derivative leaves the state unchanged exactly.
    """
    def deriv(y):
        return body_axis_derivative(y, forces, moments, mass, inertia, g)

    return rk4_core(deriv, tuple(state), dt)


def kinetic_energy(state, mass, inertia):
    """Total kinetic energy in J of the rigid body state.

    0.5 m (u^2 + v^2 + w^2) plus the rotational part
    0.5 (Ixx p^2 + Iyy q^2 + Izz r^2). Used for the energy consistency
    check of a propagation step: for a pure translation with constant
    force the kinetic energy increase equals the force times the
    distance traveled.
    """
    if len(state) != 9:
        raise ValueError("state must have 9 components")
    u, v, w, p, q, r = state[:6]
    ixx, iyy, izz = inertia
    return 0.5 * mass * (u * u + v * v + w * w) + 0.5 * (
        ixx * p * p + iyy * q * q + izz * r * r
    )
