"""turbofan_design_point_logic.py - two-stream turbofan design point (separate-exhaust-cycle).

Pure-stdlib (math only) implementation of the wave-43 turbofan-design-point
leaf: traverse the station chain 0-2-13-2.5-3-4-4.5-5-9/19 of a two-spool
separate-exhaust turbofan at flight Mach number and altitude, close the HP
and LP spool work balances, expand both streams through their convergent
nozzles and report the net thrust and TSFC.

SI units throughout. Component efficiencies are constant-gamma isentropic
forms on KAPPA_C and KAPPA_G only.
"""

import math

# --- Module constants (pinned by the engineering spec) ---
GAMMA_C = 1.4                      # cold air: fan/core compression, fan nozzle
KAPPA_C = (GAMMA_C - 1) / GAMMA_C  # 2/7
GAMMA_G = 4.0 / 3.0                # hot gas: turbines and core nozzle
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
ISA_EXP = G0 / (ISA_R * ISA_LAPSE)  # troposphere exponent
ALT_TROP = 11000.0                 # m, tropopause
LBF_PER_HR_FACTOR = 3600.0 * G0    # 35303.9, kg/(N s) -> lbm/(lbf hr)


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
    a0 = math.sqrt(GAMMA_C * R_C * t0)
    v0 = mach * a0
    tt0 = t0 * (1.0 + 0.5 * (GAMMA_C - 1.0) * mach * mach)
    pt0 = p0 * (tt0 / t0) ** (1.0 / KAPPA_C)
    return v0, tt0, pt0


def diffuser_state(tt0, t0, p0, eta_d):
    """Inlet traverse to the fan face: (tt2, pt2) from the ram recovery.

    tt2 = tt0; pt2 = p0*(1 + eta_d*(tt0/t0 - 1))**(1/KAPPA_C), based on the
    ambient STATIC pressure p0 (equals pt0 at eta_d = 1). ValueError if
    tt0/t0/p0 non-positive or eta_d outside (0, 1].
    """
    if tt0 <= 0.0 or t0 <= 0.0 or p0 <= 0.0:
        raise ValueError("total and static temperature and pressure must be positive")
    if eta_d <= 0.0 or eta_d > 1.0:
        raise ValueError("diffuser efficiency must lie in (0, 1]")
    tt2 = tt0
    pt2 = p0 * (1.0 + eta_d * (tt0 / t0 - 1.0)) ** (1.0 / KAPPA_C)
    return tt2, pt2


def compressor_exit_temperature(tt_in, pr, eta):
    """Cold isentropic-efficiency compression: tt_out from tt_in, pr, eta.

    tt_s = tt_in*pr**KAPPA_C; tt_out = tt_in + (tt_s - tt_in)/eta.
    ValueError if tt_in <= 0, pr <= 1 or eta outside (0, 1].
    """
    if tt_in <= 0.0:
        raise ValueError("inlet temperature must be positive")
    if pr <= 1.0:
        raise ValueError("compressor pressure ratio must exceed 1")
    if eta <= 0.0 or eta > 1.0:
        raise ValueError("compressor efficiency must lie in (0, 1]")
    tt_s = tt_in * pr ** KAPPA_C
    return tt_in + (tt_s - tt_in) / eta


def hp_spool_balance(tt25, tt3, tt4, cp_c=CP_C, cp_g=CP_G):
    """HP spool balance: HPT exit temperature tt45 that drives the HPC.

    cp_g*(tt4 - tt45) = cp_c*(tt3 - tt25), so
    tt45 = tt4 - (cp_c/cp_g)*(tt3 - tt25). ValueError unless
    0 < tt25 < tt3 < tt4 and unless the HP demand reaches tt4.
    """
    if not (0.0 < tt25 < tt3 < tt4):
        raise ValueError("require 0 < tt25 < tt3 < tt4 for the HP spool balance")
    demand = (cp_c / cp_g) * (tt3 - tt25)
    if demand >= tt4:
        raise ValueError("HP compressor demand reaches the turbine-inlet temperature")
    return tt4 - demand


def lp_spool_balance(tt2, tt13, tt25, tt45, bpr, cp_c=CP_C, cp_g=CP_G):
    """LP spool balance: LPT exit temperature tt5 drives fan (both streams)
    plus booster, per unit core air.

    cp_g*(tt45 - tt5) = cp_c*((1 + bpr)*(tt13 - tt2) + (tt25 - tt13)); the
    fan term carries (1 + bpr) because the fan moves the bypass stream AND
    the core stream. ValueError unless 0 < tt2 < tt13 < tt25, bpr >= 0,
    and unless the LP demand reaches tt45 (the fan-growth limit at fixed
    Tt4).
    """
    if not (0.0 < tt2 < tt13 < tt25):
        raise ValueError("require 0 < tt2 < tt13 < tt25 for the LP spool balance")
    if bpr < 0.0:
        raise ValueError("bypass ratio must be non-negative")
    demand = (cp_c / cp_g) * ((1.0 + bpr) * (tt13 - tt2) + (tt25 - tt13))
    if demand >= tt45:
        raise ValueError("LP spool demand reaches the LP turbine inlet temperature")
    return tt45 - demand


def fuel_air_ratio(tt3, tt4, eta_b, cp=CP_C, lhv=LHV):
    """Combustor energy balance: f = cp*(tt4 - tt3)/(eta_b*lhv).

    ValueError if tt3 <= 0, tt4 <= tt3 or eta_b outside (0, 1].
    """
    if tt3 <= 0.0:
        raise ValueError("combustor inlet temperature must be positive")
    if tt4 <= tt3:
        raise ValueError("turbine-inlet temperature must exceed the combustor inlet")
    if eta_b <= 0.0 or eta_b > 1.0:
        raise ValueError("combustor efficiency must lie in (0, 1]")
    return cp * (tt4 - tt3) / (eta_b * lhv)


def turbine_pressure_ratio(tt_in, tt_out, eta):
    """Turbine isentropic-efficiency expansion pressure ratio.

    tt_s = tt_in - (tt_in - tt_out)/eta; returns (tt_s/tt_in)**(1/KAPPA_G).
    ValueError if tt_in <= 0, tt_out >= tt_in (turbines must cool) or eta
    outside (0, 1].
    """
    if tt_in <= 0.0:
        raise ValueError("turbine inlet temperature must be positive")
    if tt_out >= tt_in:
        raise ValueError("turbine outlet temperature must fall below the inlet")
    if eta <= 0.0 or eta > 1.0:
        raise ValueError("turbine efficiency must lie in (0, 1]")
    tt_s = tt_in - (tt_in - tt_out) / eta
    return (tt_s / tt_in) ** (1.0 / KAPPA_G)


def nozzle_exit(tt_in, pt_in, p_amb, gamma, cp, cv):
    """Convergent nozzle exit from the entry total state (choked or not).

    Returns dict with keys choked, me, npr, critical, te, pe, v_ideal, ve.
    npr = pt_in/p_amb; choked when npr >= critical =
    ((gamma+1)/2)**(gamma/(gamma-1)). Choked: me = 1, te = 2*tt_in/(gamma+1),
    pe = pt_in*((gamma+1)/2)**(-gamma/(gamma-1)); unchoked: pe = p_amb,
    te = tt_in*(p_amb/pt_in)**((gamma-1)/gamma). Ideal velocity
    sqrt(2*cp*(tt_in - te)); actual ve = cv*v_ideal (velocity coefficient).
    ValueError if tt_in <= 0, cp <= 0, pt_in <= p_amb (nothing to expand)
    or cv outside (0, 1].
    """
    if tt_in <= 0.0:
        raise ValueError("nozzle inlet total temperature must be positive")
    if cp <= 0.0:
        raise ValueError("specific heat must be positive")
    if pt_in <= p_amb:
        raise ValueError("nozzle total pressure must exceed the ambient pressure")
    if cv <= 0.0 or cv > 1.0:
        raise ValueError("nozzle velocity coefficient must lie in (0, 1]")
    gamma_m1 = gamma - 1.0
    critical = ((gamma + 1.0) / 2.0) ** (gamma / gamma_m1)
    npr = pt_in / p_amb
    if npr >= critical:
        choked = True
        me = 1.0
        te = 2.0 * tt_in / (gamma + 1.0)
        pe = pt_in * ((gamma + 1.0) / 2.0) ** (-gamma / gamma_m1)
    else:
        choked = False
        me = math.sqrt((2.0 / gamma_m1) * (npr ** (gamma_m1 / gamma) - 1.0))
        pe = p_amb
        te = tt_in * (p_amb / pt_in) ** (gamma_m1 / gamma)
    v_ideal = math.sqrt(2.0 * cp * (tt_in - te))
    ve = cv * v_ideal
    return {
        "choked": choked,
        "me": me,
        "npr": npr,
        "critical": critical,
        "te": te,
        "pe": pe,
        "v_ideal": v_ideal,
        "ve": ve,
    }


def turbofan_design_point(mach, altitude, opr, fpr, lpc_pr, bpr, tt4,
                          mdot_core, eta_d, eta_fan, eta_lpc, eta_hpc,
                          eta_b, eta_hpt, eta_lpt, cv_core, cv_fan):
    """Full two-spool separate-exhaust turbofan design point report.

    Traverses 0-2-13-2.5-3-4-4.5-5-9/19, closes the OPR (pt3/pt2 = opr =
    fpr*lpc_pr*hpc_pr), closes both spool balances and exhausts the core
    and fan nozzles. Returns a dict with the station total states, ram
    recovery, hpc_pr and opr_actual, the burner fuel/air ratio, the two
    nozzle dicts and exit areas, the mass flows, the four thrust terms,
    net thrust, specific thrust, fuel flow and TSFC (kg/(N s) and
    lb/(lbf hr)). ValueError if mdot_core <= 0 or opr <= fpr*lpc_pr (the
    HPC would have no ratio), plus every guard above.
    """
    if mdot_core <= 0.0:
        raise ValueError("core mass flow must be positive")
    if opr <= fpr * lpc_pr:
        raise ValueError("overall pressure ratio must exceed fpr*lpc_pr so the HPC has a ratio")
    hpc_pr = opr / (fpr * lpc_pr)

    # Step 1 flight point: ambient + freestream ram traverse.
    t0, p0 = isa_atmosphere(altitude)
    v0, tt0, pt0 = freestream_state(t0, p0, mach)

    # Inlet to the fan face, station 2.
    tt2, pt2 = diffuser_state(tt0, t0, p0, eta_d)
    ram_recovery = pt2 / pt0

    # Fan to station 13 (fan discharge, common to both streams).
    tt13 = compressor_exit_temperature(tt2, fpr, eta_fan)
    pt13 = pt2 * fpr

    # Core stream: booster (LP compressor) to station 2.5.
    tt25 = compressor_exit_temperature(tt13, lpc_pr, eta_lpc)
    pt25 = pt13 * lpc_pr

    # HPC to station 3; OPR closes from the fan face.
    tt3 = compressor_exit_temperature(tt25, hpc_pr, eta_hpc)
    pt3 = pt25 * hpc_pr
    opr_actual = pt3 / pt2

    # Combustor: station 4 at Tt4, no pressure loss (pt4 = pt3).
    f = fuel_air_ratio(tt3, tt4, eta_b)
    pt4 = pt3

    # HP spool balance: HPT exit state 4.5.
    tt45 = hp_spool_balance(tt25, tt3, tt4)
    pt45 = pt4 * turbine_pressure_ratio(tt4, tt45, eta_hpt)

    # LP spool balance: LPT exit state 5.
    tt5 = lp_spool_balance(tt2, tt13, tt25, tt45, bpr)
    pt5 = pt45 * turbine_pressure_ratio(tt45, tt5, eta_lpt)

    # Nozzles: core stream (9) from station 5, fan stream (19) from 13.
    core_nz = nozzle_exit(tt5, pt5, p0, GAMMA_G, CP_G, cv_core)
    fan_nz = nozzle_exit(tt13, pt13, p0, GAMMA_C, CP_C, cv_fan)

    # Exit-plane areas for the pressure terms (continuity at the exit).
    a9 = mdot_core * R_G * core_nz["te"] / (core_nz["pe"] * core_nz["ve"])
    a19 = (bpr * mdot_core) * R_C * fan_nz["te"] / (fan_nz["pe"] * fan_nz["ve"])

    # Mass split and thrust bookkeeping.
    mdot_fan = bpr * mdot_core
    mdot_total = (1.0 + bpr) * mdot_core
    f_core_mom = mdot_core * (core_nz["ve"] - v0)
    f_fan_mom = mdot_fan * (fan_nz["ve"] - v0)
    f_core_pres = (core_nz["pe"] - p0) * a9
    f_fan_pres = (fan_nz["pe"] - p0) * a19
    net_thrust = f_core_mom + f_fan_mom + f_core_pres + f_fan_pres
    specific_thrust = net_thrust / mdot_total
    mdot_fuel = f * mdot_core
    tsfc = mdot_fuel / net_thrust
    tsfc_imp = tsfc * LBF_PER_HR_FACTOR

    return {
        # station total states (turbofan-design-point fan-stream-station-states)
        "tt0": tt0, "pt0": pt0,
        "tt2": tt2, "pt2": pt2,
        "tt13": tt13, "pt13": pt13,
        "tt25": tt25, "pt25": pt25,
        "tt3": tt3, "pt3": pt3,
        "tt4": tt4, "pt4": pt4,
        "tt45": tt45, "pt45": pt45,
        "tt5": tt5, "pt5": pt5,
        "ram_recovery": ram_recovery,
        "hpc_pr": hpc_pr,
        "opr_actual": opr_actual,
        "f": f,
        "core_nz": core_nz,
        "fan_nz": fan_nz,
        "a9": a9,
        "a19": a19,
        "mdot_core": mdot_core,
        "mdot_fan": mdot_fan,
        "mdot_total": mdot_total,
        "f_core_mom": f_core_mom,
        "f_fan_mom": f_fan_mom,
        "f_core_pres": f_core_pres,
        "f_fan_pres": f_fan_pres,
        "net_thrust": net_thrust,
        "specific_thrust": specific_thrust,
        "mdot_fuel": mdot_fuel,
        "tsfc": tsfc,
        "tsfc_imp": tsfc_imp,
    }
