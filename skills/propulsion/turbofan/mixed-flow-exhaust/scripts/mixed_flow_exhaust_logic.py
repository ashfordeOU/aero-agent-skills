"""mixed_flow_exhaust_logic.py - two-stream turbofan design point with a mixing exhaust.

Pure-stdlib (math only) implementation of the wave-44 mixed-flow-exhaust
leaf: traverse the two-spool turbofan station chain 0-2-13-2.5-3-4-4.5-5
at flight Mach and altitude exactly as the separate-exhaust sibling does,
carry the bypass stream through the fan duct to the mixer entry (station
16) and the core stream from the LPT exit to the same entry plane, close
the constant-area mixer by the energy and momentum balances over the two
streams' total states, expand the mixed stream through one common
convergent nozzle, and report the net thrust and TSFC of the mixed-flow
configuration against the separate-exhaust baseline.

SI units throughout. Component efficiencies are constant-gamma isentropic
forms on the module gas constants only (KAPPA_C cold, KAPPA_G hot).
Deterministic: no imports beyond math, no RNG, fixed-iteration bisection.
"""

import math

# --- Module constants (pinned by the engineering spec) ---
GAMMA_C = 1.4                      # cold air: fan/core compression, fan stream
KAPPA_C = (GAMMA_C - 1) / GAMMA_C  # 2/7
GAMMA_G = 4.0 / 3.0                # hot gas: turbines, core stream at mixer entry
KAPPA_G = (GAMMA_G - 1) / GAMMA_G  # 1/4
CP_C = 1005.0                      # J/(kg K), cold stream
CP_G = 1150.0                      # J/(kg K), hot stream
R_C = CP_C * KAPPA_C               # 287.142857 J/(kg K)
R_G = CP_G * KAPPA_G               # 287.5 J/(kg K)
LHV = 43.0e6                       # J/kg, kerosene lower heating value
ISA_SEA_T = 288.15                 # K
ISA_SEA_P = 101325.0               # Pa
ISA_LAPSE = 0.0065                 # K/m
ISA_R = 287.0                      # J/(kg K), ISA gas constant
G0 = 9.80665                       # m/s^2
ISA_EXP = G0 / (ISA_R * ISA_LAPSE)  # troposphere exponent, about 5.25588
ALT_TROP = 11000.0                 # m, tropopause
LBF_PER_HR = 3600.0 * G0           # 35303.9, kg/(N s) -> lbm/(lbf hr)
BISECT_TOL = 1e-12                 # bisection width tolerance, m/s
BISECT_MAX = 200                   # bisection iteration cap


def _check_eta(eta, name):
    """Raise ValueError unless eta lies in (0, 1]."""
    if not (0.0 < eta <= 1.0):
        raise ValueError("%s must lie in (0, 1]" % name)


def isa_atmosphere(altitude):
    """Return the ISA troposphere static state (t0, p0) at altitude (m).

    t0 = 288.15 - 0.0065*altitude, p0 = 101325.0*(t0/288.15)**ISA_EXP.
    ValueError if altitude outside [0, 11000].
    """
    if altitude < 0.0 or altitude > ALT_TROP:
        raise ValueError("altitude must be within [0, 11000] m (ISA troposphere)")
    t0 = ISA_SEA_T - ISA_LAPSE * altitude
    p0 = ISA_SEA_P * (t0 / ISA_SEA_T) ** ISA_EXP
    return t0, p0


def freestream_state(t0, p0, mach):
    """Freestream flight state (v0, tt0, pt0) from static state and Mach.

    v0 = mach*sqrt(GAMMA_C*R_C*t0); tt0 = t0*(1 + 0.5*(GAMMA_C-1)*mach^2);
    pt0 = p0*(tt0/t0)**(1/KAPPA_C). ValueError on non-positive t0/p0 or
    negative mach.
    """
    if t0 <= 0.0:
        raise ValueError("static temperature must be positive")
    if p0 <= 0.0:
        raise ValueError("static pressure must be positive")
    if mach < 0.0:
        raise ValueError("mach number must be non-negative")
    v0 = mach * math.sqrt(GAMMA_C * R_C * t0)
    tt0 = t0 * (1.0 + 0.5 * (GAMMA_C - 1.0) * mach * mach)
    pt0 = p0 * (tt0 / t0) ** (1.0 / KAPPA_C)
    return v0, tt0, pt0


def diffuser_state(tt0, t0, p0, eta_d):
    """Diffuser exit total state (tt2, pt2) from the ram total state.

    tt2 = tt0; pt2 = p0*(1 + eta_d*(tt0/t0 - 1))**(1/KAPPA_C). ValueError
    if eta_d not in (0, 1] or t0/p0 non-positive.
    """
    _check_eta(eta_d, "diffuser efficiency eta_d")
    if t0 <= 0.0:
        raise ValueError("static temperature must be positive")
    if p0 <= 0.0:
        raise ValueError("static pressure must be positive")
    tt2 = tt0
    pt2 = p0 * (1.0 + eta_d * (tt0 / t0 - 1.0)) ** (1.0 / KAPPA_C)
    return tt2, pt2


def cold_compressor(tt_in, pt_in, pr, eta):
    """Cold (fan/booster/HPC) compression at isentropic efficiency eta.

    tt_s = tt_in*pr**KAPPA_C; tt_out = tt_in + (tt_s - tt_in)/eta;
    pt_out = pt_in*pr. ValueError if pr < 1 or eta outside (0, 1].
    """
    _check_eta(eta, "compressor efficiency")
    if pr < 1.0:
        raise ValueError("pressure ratio must be >= 1")
    if tt_in <= 0.0 or pt_in <= 0.0:
        raise ValueError("compressor entry state must be positive")
    tt_s = tt_in * pr ** KAPPA_C
    tt_out = tt_in + (tt_s - tt_in) / eta
    pt_out = pt_in * pr
    return tt_out, pt_out


def burner_far(tt3, tt4, eta_b):
    """Burner fuel-to-air ratio f = CP_C*(tt4-tt3)/(eta_b*LHV).

    ValueError if tt4 <= tt3 (no heat release) or eta_b outside (0, 1].
    """
    _check_eta(eta_b, "burner efficiency eta_b")
    if tt4 <= tt3:
        raise ValueError("turbine entry temperature must exceed burner entry")
    return CP_C * (tt4 - tt3) / (eta_b * LHV)


def hp_spool(tt3, tt25, tt4, eta_hpt):
    """HPT exit total temperature tt45 from the HP spool work balance.

    CP_G*(tt4 - tt45) = CP_C*(tt3 - tt25) per unit core air. eta_hpt is
    validated (the pressure side is closed by turbine_expansion). ValueError
    if eta_hpt outside (0, 1] or tt45 <= 0.
    """
    _check_eta(eta_hpt, "HPT efficiency eta_hpt")
    tt45 = tt4 - CP_C * (tt3 - tt25) / CP_G
    if tt45 <= 0.0:
        raise ValueError("HPT exit temperature must be positive")
    return tt45


def lp_spool(tt45, tt2, tt13, tt25, bpr, eta_lpt):
    """LPT exit total temperature tt5 from the LP spool work balance.

    CP_G*(tt45 - tt5) = CP_C*((1 + bpr)*(tt13 - tt2) + (tt25 - tt13)) per
    unit core air (fan work on both streams plus booster work on the core).
    ValueError if tt5 <= 0, bpr < 0 or eta_lpt outside (0, 1].
    """
    _check_eta(eta_lpt, "LPT efficiency eta_lpt")
    if bpr < 0.0:
        raise ValueError("bypass ratio must be non-negative")
    work = (1.0 + bpr) * (tt13 - tt2) + (tt25 - tt13)
    tt5 = tt45 - CP_C * work / CP_G
    if tt5 <= 0.0:
        raise ValueError("LPT exit temperature must be positive")
    return tt5


def turbine_expansion(tt_in, tt_out, pt_in, eta):
    """Turbine exit total pressure pt_out at isentropic efficiency eta.

    tt_s = tt_in - (tt_in - tt_out)/eta; pt_out = pt_in*(tt_s/tt_in)**
    (1/KAPPA_G). ValueError if tt_out >= tt_in, tt_s <= 0 or eta outside
    (0, 1].
    """
    _check_eta(eta, "turbine efficiency")
    if tt_out >= tt_in:
        raise ValueError("turbine exit temperature must be below entry")
    if tt_in <= 0.0 or pt_in <= 0.0:
        raise ValueError("turbine entry state must be positive")
    tt_s = tt_in - (tt_in - tt_out) / eta
    if tt_s <= 0.0:
        raise ValueError("isentropic turbine exit temperature must be positive")
    pt_out = pt_in * (tt_s / tt_in) ** (1.0 / KAPPA_G)
    return pt_out


def design_point_traverse(mach, altitude, opr, fpr, bpr, lpc_pr, tt4,
                          eta_d, eta_fan, eta_bst, eta_hpc, eta_b,
                          eta_hpt, eta_lpt):
    """Run the station traverse 0-2-13-2.5-3-4-4.5-5 at the design point.

    Returns a dict of the station total states (tt2/pt2, tt13/pt13,
    tt25/pt25, tt3/pt3, tt45/pt45, tt5/pt5), the burner f, the mass flows
    per unit core air (m_fan = bpr, m_core = 1 + f, m_total = bpr + m_core),
    hpc_pr = opr/(fpr*lpc_pr) and the freestream state. ValueError if
    opr < fpr, hpc_pr < 1 or any efficiency outside (0, 1].
    """
    _check_eta(eta_d, "diffuser efficiency eta_d")
    _check_eta(eta_fan, "fan efficiency eta_fan")
    _check_eta(eta_bst, "booster efficiency eta_bst")
    _check_eta(eta_hpc, "HPC efficiency eta_hpc")
    _check_eta(eta_b, "burner efficiency eta_b")
    _check_eta(eta_hpt, "HPT efficiency eta_hpt")
    _check_eta(eta_lpt, "LPT efficiency eta_lpt")
    if opr < fpr:
        raise ValueError("OPR must be >= fan pressure ratio")
    hpc_pr = opr / (fpr * lpc_pr)
    if hpc_pr < 1.0:
        raise ValueError("HPC pressure ratio must be >= 1")
    if tt4 <= 0.0:
        raise ValueError("turbine entry temperature must be positive")

    t0, p0 = isa_atmosphere(altitude)
    v0, tt0, pt0 = freestream_state(t0, p0, mach)
    tt2, pt2 = diffuser_state(tt0, t0, p0, eta_d)
    tt13, pt13 = cold_compressor(tt2, pt2, fpr, eta_fan)
    tt25, pt25 = cold_compressor(tt13, pt13, lpc_pr, eta_bst)
    tt3, pt3 = cold_compressor(tt25, pt25, hpc_pr, eta_hpc)
    f = burner_far(tt3, tt4, eta_b)
    pt4 = pt3
    tt45 = hp_spool(tt3, tt25, tt4, eta_hpt)
    pt45 = turbine_expansion(tt4, tt45, pt4, eta_hpt)
    tt5 = lp_spool(tt45, tt2, tt13, tt25, bpr, eta_lpt)
    pt5 = turbine_expansion(tt45, tt5, pt45, eta_lpt)

    m_fan = bpr
    m_core = 1.0 + f
    m_total = bpr + m_core
    return {
        "t0": t0, "p0": p0, "v0": v0, "tt0": tt0, "pt0": pt0,
        "tt2": tt2, "pt2": pt2,
        "tt13": tt13, "pt13": pt13,
        "tt25": tt25, "pt25": pt25,
        "tt3": tt3, "pt3": pt3,
        "tt45": tt45, "pt45": pt45,
        "tt5": tt5, "pt5": pt5,
        "f": f, "m_fan": m_fan, "m_core": m_core, "m_total": m_total,
        "hpc_pr": hpc_pr,
    }


def _subsonic_mach_from_total_ratio(pt_over_ps, gamma):
    """Entry Mach from the total-to-static pressure ratio, subsonic root.

    Closed form: M = sqrt(2*((pt/p_s)**((gamma-1)/gamma) - 1)/(gamma-1)).
    Returns None when the ratio is at or beyond the sonic limit.
    """
    critical = ((gamma + 1.0) / 2.0) ** (gamma / (gamma - 1.0))
    if pt_over_ps >= critical:
        return None
    return math.sqrt(2.0 * ((pt_over_ps) ** ((gamma - 1.0) / gamma) - 1.0)
                     / (gamma - 1.0))


def mixing_state(tt_f, pt_f, gamma_f, cp_f, r_f, m_f,
                 tt_g, pt_g, gamma_g, cp_g, r_g, m_g,
                 m_fan_entry=0.3):
    """Close the constant-area mixer over the two entry total states.

    The mixer entry is the equal-static-pressure plane: the fan-stream
    entry Mach is the design input m_fan_entry, the common entry static
    pressure p_s follows from the fan stream total state, the core-stream
    entry Mach is the subsonic isentropic root at that p_s, entry areas
    follow from continuity, and the constant-area duct momentum balance
    m_total*v_exit + p_exit*A = m_f*v_f + m_g*v_g + p_s*A with the exit
    static pressure from continuity closes the uniform mixed exit state
    on the first (subsonic) root by bisection.

    Returns a dict with p_s, mach_f, mach_g, T_s_f, T_s_g, v_f, v_g,
    A_f, A_g, A, tt_mix, cp_mix, r_mix, gamma_mix, v_exit, p_exit,
    M_exit, T_s_exit, pt_mix, pt_tw, mixing_loss_ratio. ValueError on a
    negative mass flow, m_fan_entry outside (0, 1), a core entry Mach
    reaching 1 (reduce m_fan_entry) or a momentum balance with no
    subsonic root.
    """
    if m_f < 0.0 or m_g < 0.0:
        raise ValueError("mass flows must be non-negative")
    if not (0.0 < m_fan_entry < 1.0):
        raise ValueError("fan-stream mixer entry Mach must lie in (0, 1)")
    if tt_f <= 0.0 or pt_f <= 0.0 or tt_g <= 0.0 or pt_g <= 0.0:
        raise ValueError("mixer entry total states must be positive")

    # Equal static pressure plane at the fan-stream entry Mach.
    p_s = pt_f / (1.0 + 0.5 * (gamma_f - 1.0) * m_fan_entry * m_fan_entry) \
        ** (gamma_f / (gamma_f - 1.0))
    mach_f = m_fan_entry
    mach_g = _subsonic_mach_from_total_ratio(pt_g / p_s, gamma_g)
    if mach_g is None:
        raise ValueError("core entry Mach reaches 1; reduce the fan-stream "
                         "mixer entry Mach")

    T_s_f = tt_f / (1.0 + 0.5 * (gamma_f - 1.0) * mach_f * mach_f)
    T_s_g = tt_g / (1.0 + 0.5 * (gamma_g - 1.0) * mach_g * mach_g)
    v_f = mach_f * math.sqrt(gamma_f * r_f * T_s_f)
    v_g = mach_g * math.sqrt(gamma_g * r_g * T_s_g)
    A_f = m_f * r_f * T_s_f / (p_s * v_f)
    A_g = m_g * r_g * T_s_g / (p_s * v_g)
    A = A_f + A_g

    # Mixed gas properties (mass weighted) and mixed total temperature.
    m_total = m_f + m_g
    cp_mix = (m_f * cp_f + m_g * cp_g) / m_total
    r_mix = (m_f * r_f + m_g * r_g) / m_total
    gamma_mix = cp_mix / (cp_mix - r_mix)
    tt_mix = (m_f * cp_f * tt_f + m_g * cp_g * tt_g) / (m_total * cp_mix)

    # Momentum balance over the constant-area duct: residual in v_exit
    # with the exit static pressure from continuity. Residual is positive
    # at v -> 0 (continuity pressure diverges) and falls through the
    # first (subsonic) root; march by doubling to the first sign change,
    # then bisect.
    rhs = m_f * v_f + m_g * v_g + p_s * A
    v_hi = math.sqrt(2.0 * cp_mix * tt_mix)

    def residual(v):
        t_s_exit = tt_mix - v * v / (2.0 * cp_mix)
        p_exit = m_total * r_mix * t_s_exit / (A * v)
        return m_total * v + p_exit * A - rhs

    lo = v_hi * 1e-9
    hi = lo
    found = False
    for _ in range(BISECT_MAX):
        hi = 2.0 * hi
        if hi > v_hi:
            hi = v_hi
        if residual(hi) <= 0.0:
            found = True
            break
        if hi >= v_hi:
            break
        lo = hi
    if not found:
        raise ValueError("momentum balance has no subsonic root; check the "
                         "mixer entry states")

    for _ in range(BISECT_MAX):
        mid = 0.5 * (lo + hi)
        if hi - lo <= BISECT_TOL:
            break
        if residual(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    v_exit = 0.5 * (lo + hi)

    T_s_exit = tt_mix - v_exit * v_exit / (2.0 * cp_mix)
    p_exit = m_total * r_mix * T_s_exit / (A * v_exit)
    a_exit = math.sqrt(gamma_mix * r_mix * T_s_exit)
    M_exit = v_exit / a_exit
    pt_mix = p_exit * (1.0 + 0.5 * (gamma_mix - 1.0) * M_exit * M_exit) \
        ** (gamma_mix / (gamma_mix - 1.0))
    pt_tw = (m_f * pt_f + m_g * pt_g) / m_total
    mixing_loss_ratio = pt_mix / pt_tw

    return {
        "p_s": p_s, "mach_f": mach_f, "mach_g": mach_g,
        "T_s_f": T_s_f, "T_s_g": T_s_g, "v_f": v_f, "v_g": v_g,
        "A_f": A_f, "A_g": A_g, "A": A,
        "tt_mix": tt_mix, "cp_mix": cp_mix, "r_mix": r_mix,
        "gamma_mix": gamma_mix,
        "v_exit": v_exit, "p_exit": p_exit, "M_exit": M_exit,
        "T_s_exit": T_s_exit, "pt_mix": pt_mix, "pt_tw": pt_tw,
        "mixing_loss_ratio": mixing_loss_ratio,
    }


def common_nozzle(tt, pt, p_amb, gamma, cp, r, cv):
    """Convergent nozzle on a single stream: choked/unchoked exit state.

    Choked when npr >= ((gamma + 1)/2)**(gamma/(gamma - 1)); the exit
    velocity is v_exit = cv*sqrt(2*cp*(tt - Te)) and the exit-plane area
    per unit mass flow is a_by_mdot = r*Te/(pe*v_exit). Returns a dict
    with choked, Me, Te, pe, v_ideal, v_exit, a_by_mdot. ValueError if
    cv outside (0, 1] or a state is non-positive.
    """
    _check_eta(cv, "nozzle velocity coefficient cv")
    if tt <= 0.0 or pt <= 0.0 or p_amb <= 0.0:
        raise ValueError("nozzle states must be positive")
    npr = pt / p_amb
    npr_crit = ((gamma + 1.0) / 2.0) ** (gamma / (gamma - 1.0))
    choked = npr >= npr_crit
    if choked:
        Me = 1.0
        Te = tt * 2.0 / (gamma + 1.0)
        pe = pt * (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    else:
        Me = math.sqrt(2.0 * (npr ** ((gamma - 1.0) / gamma) - 1.0)
                       / (gamma - 1.0))
        pe = p_amb
        Te = tt / (1.0 + 0.5 * (gamma - 1.0) * Me * Me)
    v_ideal = math.sqrt(2.0 * cp * (tt - Te))
    v_exit = cv * v_ideal
    a_by_mdot = r * Te / (pe * v_exit)
    return {
        "choked": choked, "Me": Me, "Te": Te, "pe": pe,
        "v_ideal": v_ideal, "v_exit": v_exit, "a_by_mdot": a_by_mdot,
    }


def net_thrust(mdot, v_exit, v0, pe, p0, a_by_mdot):
    """Net thrust F = mdot*(v_exit - v0) + (pe - p0)*a_by_mdot*mdot.

    ValueError if mdot <= 0.
    """
    if mdot <= 0.0:
        raise ValueError("mass flow must be positive")
    a9 = a_by_mdot * mdot
    return mdot * (v_exit - v0) + (pe - p0) * a9
