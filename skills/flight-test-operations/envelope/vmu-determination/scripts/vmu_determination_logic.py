"""Minimum unstick speed (Vmu) reduction of takeoff rotation runs.

Pure stdlib, closed-form math only. Implements the FAR/CS 25.107(b)
summary method: per rotation run, classify the run against the
certified tail-strike/rotation limit angle, correct the measured
liftoff speed to the reference takeoff weight, flap and standard
conditions, and reduce the corrected limit-unstick runs to the Vmu
verdict with the no-unstick and premature-unstick bracket checks.
Then gates the V1/VR schedule against the 1.08*Vmu liftoff constraint
and the 1.10*Vs1 rotation stall floor (all engines operative).

Single-layer ISA to 11 km only; every speed verdict is a CAS m/s value
at reference conditions. KT2MS appears only to quote the verdict in
knots.
"""

import math

# Module constants (single-layer ISA and unit conversions).
RHO_SL = 1.225          # kg/m3, sea-level standard density
T0 = 288.15             # K, sea-level standard temperature
LAPSE = 0.0065          # K/m, tropospheric lapse rate
G0 = 9.80665            # m/s2, standard gravity
R_AIR = 287.05          # J/(kg K), specific gas constant of air
EXP = G0 / (R_AIR * LAPSE)      # ISA pressure exponent, about 5.2559
KT2MS = 0.514444444444  # m/s per knot (1852/3600)


def isa_sigma(h_p, dt_isa=0.0):
    """ISA density ratio delta/theta at pressure altitude h_p with
    temperature deviation dt_isa, single-layer closed form.

    sigma = delta/theta with delta = (1 - LAPSE*h_p/T0)**EXP and
    theta = (T0 - LAPSE*h_p + dt_isa)/T0.
    """
    if h_p < 0.0 or h_p > 11000.0:
        raise ValueError("pressure altitude must be within [0, 11000] m")
    ambient = T0 - LAPSE * h_p + dt_isa
    if ambient <= 0.0:
        raise ValueError("ambient temperature must be positive")
    delta = (1.0 - LAPSE * h_p / T0) ** EXP
    theta = ambient / T0
    return delta / theta


def tas_to_cas(v_tas, h_p, dt_isa=0.0):
    """True to calibrated airspeed: v_cas = v_tas*sqrt(sigma)."""
    if v_tas <= 0.0:
        raise ValueError("true airspeed must be positive")
    return v_tas * math.sqrt(isa_sigma(h_p, dt_isa))


def weight_corrected_speed(v_cas, w_test, w_ref):
    """Weight correction at fixed lift coefficient (CAS scaling):
    v_corr = v_cas*sqrt(w_ref/w_test)."""
    if v_cas <= 0.0:
        raise ValueError("airspeed must be positive")
    if w_test <= 0.0 or w_ref <= 0.0:
        raise ValueError("weights must be positive")
    return v_cas * math.sqrt(w_ref / w_test)


def flap_normalized_speed(v_cas, flap_test, flap_ref, cl_0, cl_per_deg):
    """Configuration normalization through the rotation-limit lift
    coefficient CL(f) = cl_0 + cl_per_deg*f:
    v_norm = v_cas*sqrt(CL(flap_test)/CL(flap_ref))."""
    if v_cas <= 0.0:
        raise ValueError("airspeed must be positive")
    if flap_test < 0.0 or flap_ref < 0.0:
        raise ValueError("flap settings must not be negative")
    if cl_0 <= 0.0:
        raise ValueError("cl_0 must be positive")
    if cl_per_deg < 0.0:
        raise ValueError("cl_per_deg must not be negative")
    cl_test = cl_0 + cl_per_deg * flap_test
    cl_ref = cl_0 + cl_per_deg * flap_ref
    if cl_test <= 0.0 or cl_ref <= 0.0:
        raise ValueError("lift coefficient must be positive at both flap settings")
    return v_cas * math.sqrt(cl_test / cl_ref)


def rotation_run_class(theta_unstick, unstuck, theta_lim):
    """Classify one rotation run against the certified rotation limit.

    "no-unstick": the limit was reached without liftoff, Vmu lies
    above this run's speed. "limit-unstick": unstuck at or beyond the
    limit (theta_unstick >= theta_lim), the Vmu-qualifying class.
    "premature-unstick": unstuck before reaching the limit, Vmu lies
    at or below this run's speed.
    """
    if theta_lim <= 0.0:
        raise ValueError("rotation limit angle must be positive")
    if theta_unstick < 0.0:
        raise ValueError("unstick pitch angle must not be negative")
    if not unstuck:
        return "no-unstick"
    if theta_unstick >= theta_lim:
        return "limit-unstick"
    return "premature-unstick"


def corrected_run_speed(v_meas, w_test, w_ref, flap_test, flap_ref,
                        cl_0, cl_per_deg, h_p=0.0, dt_isa=0.0,
                        tas_input=False):
    """Full standard-condition reduction of one measured liftoff speed:
    TAS to CAS first when tas_input (CAS input used directly), then the
    weight correction, then the flap normalization."""
    if v_meas <= 0.0:
        raise ValueError("measured speed must be positive")
    if tas_input:
        v = tas_to_cas(v_meas, h_p, dt_isa)
    else:
        v = v_meas
    v = weight_corrected_speed(v, w_test, w_ref)
    return flap_normalized_speed(v, flap_test, flap_ref, cl_0, cl_per_deg)


def vmu_verdict(runs, theta_lim, w_ref, flap_ref, cl_0, cl_per_deg):
    """Reduce the takeoff rotation run list to the Vmu verdict.

    Each run dict: id, speed (m/s), weight (kg), flap (deg),
    theta (deg, pitch at unstick; the limit angle for no-unstick
    runs), unstuck (bool), h_p (m, default 0), dt_isa (K, default 0),
    tas_input (bool, default False). Returns the corrected run table,
    vmu_cas (min corrected limit-unstick speed), vmu_knots, the
    no-unstick max and premature-unstick min bracket speeds (None when
    empty), bracket_ok, and n_qualifying.
    """
    if not runs:
        raise ValueError("run list must not be empty")
    corrected = []
    for run in runs:
        v = corrected_run_speed(
            run["speed"], run["weight"], w_ref, run["flap"], flap_ref,
            cl_0, cl_per_deg, run.get("h_p", 0.0), run.get("dt_isa", 0.0),
            run.get("tas_input", False))
        cls = rotation_run_class(run["theta"], run["unstuck"], theta_lim)
        corrected.append({"id": run["id"], "class": cls, "corrected": v})
    qualifying = [c["corrected"] for c in corrected
                  if c["class"] == "limit-unstick"]
    if not qualifying:
        raise ValueError("Vmu not defined: no limit-unstick run in the data")
    no_unstick = [c["corrected"] for c in corrected
                  if c["class"] == "no-unstick"]
    premature = [c["corrected"] for c in corrected
                 if c["class"] == "premature-unstick"]
    vmu_cas = min(qualifying)
    v_no_unstick_max = max(no_unstick) if no_unstick else None
    v_premature_min = min(premature) if premature else None
    bracket_ok = True
    if v_no_unstick_max is not None and not (vmu_cas > v_no_unstick_max):
        bracket_ok = False
    if v_premature_min is not None and not (vmu_cas <= v_premature_min):
        bracket_ok = False
    return {
        "runs": corrected,
        "vmu_cas": vmu_cas,
        "vmu_knots": vmu_cas / KT2MS,
        "v_no_unstick_max": v_no_unstick_max,
        "v_premature_min": v_premature_min,
        "bracket_ok": bracket_ok,
        "n_qualifying": len(qualifying),
    }


def liftoff_margin_108(vmu_cas, v_lof_cas):
    """Geometrically limited liftoff margin (AEO):
    required_108 = 1.08*Vmu; met when v_lof >= required_108."""
    if vmu_cas <= 0.0 or v_lof_cas <= 0.0:
        raise ValueError("speeds must be positive")
    required_108 = 1.08 * vmu_cas
    return {
        "required_108": required_108,
        "margin_mps": v_lof_cas - required_108,
        "ratio_vlof_over_vmu": v_lof_cas / vmu_cas,
        "met": v_lof_cas >= required_108,
    }


def scheduling_gate(vmu_cas, vr_cas, vs1_cas=None):
    """V1/VR scheduling gate against the Vmu verdict.

    The Vmu gate is met when vr >= 1.08*Vmu; when vs1 is supplied the
    stall floor is met when vr >= 1.10*Vs1. vr_required is the max of
    the applicable floors; verdict is "ok", "vmu-gated", "stall-gated"
    or "dual-gated". This leaf only checks a supplied schedule.
    """
    if vmu_cas <= 0.0 or vr_cas <= 0.0:
        raise ValueError("speeds must be positive")
    if vs1_cas is not None and vs1_cas <= 0.0:
        raise ValueError("stall speed must be positive")
    req_vmu = 1.08 * vmu_cas
    vmu_met = vr_cas >= req_vmu
    if vs1_cas is None:
        req_stall = None
        stall_met = None
        floors = [req_vmu]
    else:
        req_stall = 1.10 * vs1_cas
        stall_met = vr_cas >= req_stall
        floors = [req_vmu, req_stall]
    if vs1_cas is None:
        verdict = "ok" if vmu_met else "vmu-gated"
    elif vmu_met and stall_met:
        verdict = "ok"
    elif vmu_met:
        verdict = "stall-gated"
    elif stall_met:
        verdict = "vmu-gated"
    else:
        verdict = "dual-gated"
    return {
        "vmu_gate_met": vmu_met,
        "stall_floor_met": stall_met,
        "req_vr_vmu_108": req_vmu,
        "req_vr_stall_110": req_stall,
        "vr_required": max(floors),
        "verdict": verdict,
    }
