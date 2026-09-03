#!/usr/bin/env python3
"""Point-mass trajectory simulation logic (stdlib only, deterministic, offline).

Vertical-plane point-mass model of an aircraft climbing out (flat
Earth, no wind, symmetric flight in the vertical plane, angle of
attack small so thrust acts along the velocity vector). The state is
(V, gamma, h, x): true airspeed V in m/s, flight-path angle gamma in
radians, altitude h in m, horizontal distance x in m.

State derivatives:
- dV/dt = (T - D) / m - g0 * sin(gamma)
- dgamma/dt = (L - W * cos(gamma)) / (m * V)
- dh/dt = V * sin(gamma)
- dx/dt = V * cos(gamma)

with W = m * g0, L = q * S * CL, D = q * S * CD,
q = 0.5 * rho(h) * V^2, CD = CD0 + K * CL^2, K = 1 / (pi * e * AR).

Documented assumption: the simulation holds a CONSTANT lift
coefficient CL (a fixed-angle-of-attack climb), so the load factor
n = L / W evolves with speed and flight-path angle: as V grows at
fixed CL the lift exceeds W * cos(gamma), gamma grows, and the
airplane climbs. The aircraft flies over a flat ground reference at
h = 0: altitude states and RK4 stage evaluations are clamped at the
ground so a diving phase cannot drive the ISA lookup negative. A
stall/limit event is flagged per step when the commanded CL would
exceed the input cl_max, or when the level-flight trim CL demanded
by the current dynamic pressure would exceed cl_max.

Thrust model: simple altitude lapse
T = T_sl * (rho(h) / rho_sl) ^ thrust_lapse_exponent.

Atmosphere (inside this file, no cross-skill imports): ISA
troposphere below 11000 m with T_K = 288.15 - 0.0065 h,
p = 101325 (T_K / 288.15)^5.2561, rho = p / (287.05 T_K); above
11000 m the isothermal stratosphere p = 22632 exp(-(h - 11000) /
6341.62), rho = p / (287.05 * 216.65).

Standards far-25 and cs-25 are referenced for the climb/performance
context only; all relations here are standard engineering methodology
paraphrased, no regulatory text reproduced.
"""

import math

# ISA sea-level constants and module defaults.
RHO_SL = 1.225  # kg/m^3
P_SL = 101325.0  # Pa
T_SL_K = 288.15  # K
G0 = 9.80665  # m/s^2
R_AIR = 287.05  # J/(kg K)
TROPOPAUSE_H = 11000.0  # m
TROPOPAUSE_T_K = 216.65  # K
TROPOPAUSE_P = 22632.0  # Pa
STRATOSPHERE_SCALE = 6341.62  # m
LAPSE_RATE = 0.0065  # K/m
PRESSURE_EXPONENT = 5.2561
DEFAULT_THRUST_LAPSE_EXPONENT = 0.7
DEFAULT_DT = 0.5  # s
DEFAULT_CL_MAX = 1.5
DEFAULT_N_STEPS = 600
PI = math.pi

STATE_NAMES = ("V", "gamma", "h", "x")


def isa_atmosphere(h):
    """ISA temperature, pressure, density at geopotential altitude h (m).

    Returns dict with keys T_K (K), p (Pa), rho (kg/m^3). Troposphere
    below 11000 m, isothermal stratosphere above. Negative altitude
    (below the ground reference) raises ValueError; the trajectory
    integration clamps the state altitude at the ground reference so
    this is only reachable through a direct bad input.
    """
    if h < 0:
        raise ValueError("altitude must be non-negative")
    if h <= TROPOPAUSE_H:
        t_k = T_SL_K - LAPSE_RATE * h
        p = P_SL * (t_k / T_SL_K) ** PRESSURE_EXPONENT
    else:
        t_k = TROPOPAUSE_T_K
        p = TROPOPAUSE_P * math.exp(-(h - TROPOPAUSE_H) / STRATOSPHERE_SCALE)
    rho = p / (R_AIR * t_k)
    return {"T_K": t_k, "p": p, "rho": rho}


def drag_polar_cd(cd0, k, cl):
    """Drag coefficient from the parabolic polar CD = CD0 + K * CL^2."""
    if cd0 < 0:
        raise ValueError("cd0 must be non-negative")
    if k < 0:
        raise ValueError("induced drag factor k must be non-negative")
    return cd0 + k * cl * cl


def thrust_at_altitude(thrust_sl, rho, rho_sl, exponent=DEFAULT_THRUST_LAPSE_EXPONENT):
    """Installed thrust with the density altitude lapse."""
    if thrust_sl <= 0:
        raise ValueError("sea-level thrust must be positive")
    if rho_sl <= 0:
        raise ValueError("sea-level density must be positive")
    return thrust_sl * (rho / rho_sl) ** exponent


def level_trim_cl(mass, velocity, wing_area, rho, g0=G0):
    """Level-flight trim CL = 2 W / (rho V^2 S) = W / (q S)."""
    if mass <= 0:
        raise ValueError("mass must be positive")
    if velocity <= 0:
        raise ValueError("velocity must be positive")
    if wing_area <= 0:
        raise ValueError("wing area must be positive")
    if rho <= 0:
        raise ValueError("density must be positive")
    return 2.0 * mass * g0 / (rho * velocity * velocity * wing_area)


def point_mass_derivs(state, params):
    """Vertical-plane point-mass state derivatives.

    params dict keys: m, S, cd0, k, thrust_sl, rho_sl, cl (constant
    commanded lift coefficient), cl_max, thrust_lapse_exponent, g0.
    The sim holds the constant commanded CL (fixed-alpha climb), so
    the load factor n = L / W evolves with speed and flight-path
    angle. cl_max is not applied inside the derivative: the caller
    flags stall/limit events against it and decides the effective CL
    for the step.
    """
    v, gamma, h, _x = state
    m = params["m"]
    s_area = params["S"]
    cd0 = params["cd0"]
    k = params["k"]
    thrust_sl = params["thrust_sl"]
    rho_sl = params["rho_sl"]
    cl = params["cl"]
    exponent = params["thrust_lapse_exponent"]
    g0 = params["g0"]
    rho = isa_atmosphere(h)["rho"]
    if v <= 0:
        raise ValueError("airspeed must be positive")
    q = 0.5 * rho * v * v
    thrust = thrust_at_altitude(thrust_sl, rho, rho_sl, exponent)
    weight = m * g0
    cd = drag_polar_cd(cd0, k, cl)
    lift = q * s_area * cl
    drag = q * s_area * cd
    d_v_dt = (thrust - drag) / m - g0 * math.sin(gamma)
    d_gamma_dt = (lift - weight * math.cos(gamma)) / (m * v)
    d_h_dt = v * math.sin(gamma)
    d_x_dt = v * math.cos(gamma)
    return [d_v_dt, d_gamma_dt, d_h_dt, d_x_dt]


def _ground_clamped(h):
    """Ground-reference clamp used by the propagator stages.

    The trajectory model flies over a flat ground at h = 0: RK4 stage
    evaluations below the ground reference are evaluated at the
    ground density so a diving state cannot drive the atmosphere
    lookup negative. The flown altitude state itself is clamped at
    the ground reference after each completed step.
    """
    return h if h >= 0.0 else 0.0


def rk4_step(state, params, dt):
    """One fixed-step fourth order Runge Kutta propagation of the state.

    Stage evaluations below the ground reference use the ground
    density (altitude clamped to 0 for the atmosphere lookup) so a
    diving pull-up never drives the ISA lookup negative.
    """
    k1 = point_mass_derivs([state[0], state[1], _ground_clamped(state[2]), state[3]], params)
    s2 = [state[i] + 0.5 * dt * k1[i] for i in range(4)]
    k2 = point_mass_derivs([s2[0], s2[1], _ground_clamped(s2[2]), s2[3]], params)
    s3 = [state[i] + 0.5 * dt * k2[i] for i in range(4)]
    k3 = point_mass_derivs([s3[0], s3[1], _ground_clamped(s3[2]), s3[3]], params)
    s4 = [state[i] + dt * k3[i] for i in range(4)]
    k4 = point_mass_derivs([s4[0], s4[1], _ground_clamped(s4[2]), s4[3]], params)
    new_state = []
    for i in range(4):
        new_state.append(state[i] + dt * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]) / 6.0)
    return new_state


def _check_sim_params(params):
    """ValueError on any non-physical simulation parameter."""
    if params.get("m", 1.0) <= 0:
        raise ValueError("mass must be positive")
    if params.get("S", 1.0) <= 0:
        raise ValueError("wing area must be positive")
    if params.get("thrust_sl", 1.0) <= 0:
        raise ValueError("sea-level thrust must be positive")
    if params.get("cd0", 0.0) < 0:
        raise ValueError("cd0 must be non-negative")
    e = params.get("e", 1.0)
    if e <= 0 or e > 1:
        raise ValueError("Oswald efficiency e must be in (0, 1]")
    ar = params.get("AR", 1.0)
    if ar <= 0:
        raise ValueError("aspect ratio must be positive")
    if params.get("cl_max", DEFAULT_CL_MAX) <= 0:
        raise ValueError("cl_max must be positive")
    if params.get("cl", 1.0) <= 0:
        raise ValueError("commanded lift coefficient must be positive")
    if params.get("rho_sl", RHO_SL) <= 0:
        raise ValueError("sea-level density must be positive")
    if params.get("thrust_lapse_exponent", DEFAULT_THRUST_LAPSE_EXPONENT) < 0:
        raise ValueError("thrust lapse exponent must be non-negative")


def simulate_trajectory(initial_state, params, dt=DEFAULT_DT, n_steps=DEFAULT_N_STEPS):
    """RK4 trajectory simulation returning states and derived values.

    initial_state is (V0, gamma0, h0, x0) in m/s, rad, m, m. The
    constant lift coefficient CL is taken from params["cl"]. Returns a
    dict with keys "states" (list of [V, gamma, h, x]) and "derived"
    (list of per-step dicts with q, CL, CD, L, D, T, load_factor,
    stall_event). Entry 0 of each list is the initial point before the
    first step.
    """
    if len(initial_state) != 4:
        raise ValueError("initial_state must be (V0, gamma0, h0, x0)")
    v0, gamma0, h0, _x0 = initial_state
    if v0 <= 0:
        raise ValueError("initial airspeed must be positive")
    if h0 < 0:
        raise ValueError("initial altitude must be non-negative")
    if dt <= 0:
        raise ValueError("time step dt must be positive")
    if n_steps <= 0:
        raise ValueError("n_steps must be positive")
    m = params.get("m")
    s_area = params.get("S")
    cd0 = params.get("cd0")
    k = params.get("k")
    thrust_sl = params.get("thrust_sl")
    rho_sl = params.get("rho_sl", RHO_SL)
    cl_cmd = params.get("cl")
    cl_max = params.get("cl_max", DEFAULT_CL_MAX)
    exponent = params.get("thrust_lapse_exponent", DEFAULT_THRUST_LAPSE_EXPONENT)
    g0 = params.get("g0", G0)
    if m is None or s_area is None or cd0 is None or k is None or thrust_sl is None or cl_cmd is None:
        raise ValueError("params must include m, S, cd0, k, thrust_sl, cl")
    _check_sim_params(params)
    e = params.get("e", 1.0)
    ar = params.get("AR", 1.0)
    k_implied = 1.0 / (PI * e * ar)
    if abs(k_implied - k) / k > 1e-6:
        raise ValueError("k must equal 1/(pi e AR) from the e and AR inputs")
    state = [v0, gamma0, h0, _x0]
    states = [list(state)]
    derived = []
    weight = m * g0
    for _step in range(n_steps):
        rho = isa_atmosphere(state[2])["rho"]
        v = state[0]
        gamma = state[1]
        q = 0.5 * rho * v * v
        thrust = thrust_at_altitude(thrust_sl, rho, rho_sl, exponent)
        # Constant-CL (fixed-alpha) climb: the commanded CL is held
        # through the whole integration. The stall/limit event is a
        # diagnostic per step: it fires when the commanded CL exceeds
        # cl_max, or when the level-flight trim CL demanded by the
        # current dynamic pressure, CL = W / (q S), would exceed
        # cl_max (the wing cannot hold the commanded lift at this
        # speed and altitude).
        trim_cl = weight / (q * s_area)
        stall = cl_cmd > cl_max or trim_cl > cl_max
        cl = cl_cmd
        cd = drag_polar_cd(cd0, k, cl)
        lift = q * s_area * cl
        drag = q * s_area * cd
        load_factor = lift / weight
        derived.append(
            {
                "q": q,
                "CL": cl,
                "CD": cd,
                "L": lift,
                "D": drag,
                "T": thrust,
                "load_factor": load_factor,
                "stall_event": stall,
            }
        )
        state = rk4_step(state, params, dt)
        if state[2] < 0.0:
            # Ground contact: the aircraft cannot fly below the ground
            # reference (flat Earth at h = 0), so the altitude state
            # clamps there and the climb-out continues from the ground.
            state[2] = 0.0
        states.append(list(state))
    return {"states": states, "derived": derived}


def steady_climb_angle(velocity, thrust, mass, cd0, k, wing_area, rho, g0=G0):
    """Closed-form steady-climb excess-thrust flight-path angle.

    Solves L = W (cos gamma ~ 1 for the consistency check) so
    CL = 2 W / (rho V^2 S) = W / (q S), CD from the polar, and
    sin(gamma) = (T - D) / W. Returns (gamma_deg, cl, cd).
    """
    if velocity <= 0:
        raise ValueError("velocity must be positive")
    if mass <= 0:
        raise ValueError("mass must be positive")
    if thrust < 0:
        raise ValueError("thrust must be non-negative")
    if wing_area <= 0:
        raise ValueError("wing area must be positive")
    if rho <= 0:
        raise ValueError("density must be positive")
    weight = mass * g0
    cl = 2.0 * weight / (rho * velocity * velocity * wing_area)
    cd = drag_polar_cd(cd0, k, cl)
    drag = 0.5 * rho * velocity * velocity * wing_area * cd
    sin_gamma = (thrust - drag) / weight
    sin_gamma = max(-1.0, min(1.0, sin_gamma))
    gamma_deg = math.degrees(math.asin(sin_gamma))
    return gamma_deg, cl, cd


def end_of_sim_summary(states):
    """End-of-simulation summary dict from the trajectory state list.

    Reports the final state, the net climb, net horizontal distance,
    and the mean flight-path angle over the last 10% of the run
    (the late-run gamma trend used for the steady-climb consistency
    check).
    """
    if not states:
        raise ValueError("states list must not be empty")
    v0, gamma0, h0, x0 = states[0]
    vf, gamma_f, hf, xf = states[-1]
    n = len(states)
    tail_start = max(1, n - max(1, n // 10))
    tail_gammas = [states[i][1] for i in range(tail_start, n)]
    mean_tail_gamma = sum(tail_gammas) / len(tail_gammas)
    return {
        "final_state": [vf, gamma_f, hf, xf],
        "initial_state": [v0, gamma0, h0, x0],
        "climb": hf - h0,
        "range": xf - x0,
        "speed_change": vf - v0,
        "mean_tail_gamma_deg": math.degrees(mean_tail_gamma),
        "final_gamma_deg": math.degrees(gamma_f),
    }


def default_params(cl_value=1.07):
    """Worked-example transport parameter set with derived k and CL.

    CL = 1.07 is the tuned constant lift coefficient (fixed-alpha
    climb) for the worked example: it keeps the t = 300 s altitude
    inside the 1500-5000 m band with margin at the transport thrust
    setting below.
    """
    e = 0.81
    ar = 9.3
    return {
        "m": 70000.0,
        "S": 122.6,
        "cd0": 0.021,
        "e": e,
        "AR": ar,
        "k": 1.0 / (PI * e * ar),
        "thrust_sl": 2.0 * 110000.0,
        "rho_sl": RHO_SL,
        "cl": cl_value,
        "cl_max": DEFAULT_CL_MAX,
        "thrust_lapse_exponent": DEFAULT_THRUST_LAPSE_EXPONENT,
        "g0": G0,
    }


if __name__ == "__main__":
    # Quick sanity run of the worked example.
    traj = simulate_trajectory(
        (90.0, 0.0, 0.0, 0.0), default_params(), dt=DEFAULT_DT, n_steps=DEFAULT_N_STEPS
    )
    summary = end_of_sim_summary(traj["states"])
    print(summary)
