#!/usr/bin/env python3
"""Low-altitude windshear and microburst hazard logic (paraphrase, standard method).

Summary of the model (FAA windshear training guidance style, paraphrased
reference-only; far-25 and cs-25 set the certification context; no
regulatory text is reproduced): the windshear F-factor is the standard
dimensionless hazard metric used for the escape decision. This module
implements the simplified energy-based form used in windshear training:

  F_available = (t - d) / w        excess-thrust capability term
  F_demand    = -a_wind / g + w_d / v
                                    wind contributions, positive = hazard
  F_total     = F_available + F_demand

where a_wind is the along-track wind acceleration d(HW)/dt, positive when
the headwind component is increasing with time (a performance increase,
it lowers F), negative when the headwind decreases or the tailwind
increases (the hazard that erodes airspeed); w_d is the downdraft speed
(positive downward) and v the true airspeed. In calm air with zero excess
thrust the total F-factor is zero.

Form 1 (standard form from the training guidance):
  F = (t - d)/w - a_wind/g
Form 2 (headwind gradient plus downdraft): the altitude shear d(HW)/dh is
converted to the along-track time rate with the aircraft vertical speed
dh/dt; this module uses the steady-flight relation dh/dt = v*(t - d)/w
(sin(gamma) = (t - d)/w for unaccelerated flight, deterministic from the
stated inputs), so a_wind = (dHW/dh)*v*(t - d)/w and
  F = (t - d)/w - a_wind/g + w_d/v

Energy height loss: with E_s = h + v^2/(2g) the specific energy, the
encounter erodes energy height at the exact rate
  dH_e/dt = v*(F_demand - F_available)
which reduces to v*F_total when the excess-thrust term is zero (the
approach escape condition, where engines sit near the drag level).
Severity classes (typical training thresholds, not a regulation):
F < 0.05 low, 0.05 to 0.1 moderate, 0.1 to 0.15 high, > 0.15 severe.
Recovery: the thrust increase that raises F_available to the demand
level is dT = w*(F_demand - F_available).

Module constants fix the units: g0 = 9.80665 m/s^2 and one knot is
463/900 m/s, so the numbers are exactly reproducible. Units are SI
throughout: thrust, drag, weight in N; speed in m/s; wind accelerations
in m/s^2; downdraft in m/s; time in s.
"""

G0 = 9.80665  # standard gravity, m/s^2
KT_TO_MS = 463.0 / 900.0  # 1 knot = 1852/3600 m/s = 463/900 m/s
SEVERITY_LOW = 0.05  # below: low; at or above: moderate (training thresholds)
SEVERITY_MODERATE = 0.10  # at or above: high
SEVERITY_HIGH = 0.15  # at or above: severe
_ESC_VERDICT_SEVERE = 0.15  # demand at or above: escape verdict
_ESC_VERDICT_HIGH = 0.10  # demand at or above: high-alert verdict
_ESC_VERDICT_MODERATE = 0.05  # demand at or above: moderate-alert verdict


def _validate_states(t, d, w, v=None, g=G0):
    """Reject non-physical inputs with ValueError (shared checks)."""
    if w <= 0:
        raise ValueError("weight must be > 0 N, got %r" % (w,))
    if v is not None and v <= 0:
        raise ValueError("true airspeed must be > 0 m/s, got %r" % (v,))
    if t < 0:
        raise ValueError("thrust must be >= 0 N, got %r" % (t,))
    if d < 0:
        raise ValueError("drag must be >= 0 N, got %r" % (d,))
    if g <= 0:
        raise ValueError("gravity must be > 0 m/s^2, got %r" % (g,))


def weight_from_mass(mass, g=G0):
    """Weight in N from the mass in kg: W = m*g."""
    if mass <= 0:
        raise ValueError("mass must be > 0 kg, got %r" % (mass,))
    return mass * g


def f_factor_from_thrust(t, d, w, a_wind, g=G0):
    """Total F-factor from the excess thrust and the along-track wind acceleration.

    F = (t - d)/w - a_wind/g. a_wind is d(HW)/dt, positive when the
    headwind increases with time (performance increase, lowers F) and
    negative for a decreasing headwind (the hazard). Raises ValueError
    on negative thrust or drag, or non-positive weight or gravity.
    """
    _validate_states(t, d, w, g=g)
    return (t - d) / w - a_wind / g


def f_factor_from_wind_gradients(headwind_gradient, downdraft, v, w, t, d, g=G0):
    """Total F-factor from the headwind altitude gradient and the downdraft.

    The altitude shear d(HW)/dh (1/s) is converted with the steady-flight
    vertical speed dh/dt = v*(t - d)/w, so the along-track rate is
    a_wind = headwind_gradient*v*(t - d)/w, and
    F = (t - d)/w - a_wind/g + downdraft/v.
    Raises ValueError on non-positive weight or airspeed, or negative
    thrust or drag.
    """
    _validate_states(t, d, w, v=v, g=g)
    dh_dt = v * (t - d) / w  # steady-flight vertical speed, sin(gamma) = (t-d)/w
    a_wind = headwind_gradient * dh_dt
    return (t - d) / w - a_wind / g + downdraft / v


def severity_class(f_factor):
    """Severity class for an F-factor value (typical training thresholds).

    Returns low, moderate, high or severe; thresholds at 0.05, 0.1 and
    0.15 with each band inclusive at its lower edge. Negative values
    (energy gain from an increasing headwind or updraft) classify low.
    """
    if f_factor < SEVERITY_LOW:
        return "low"
    if f_factor < SEVERITY_MODERATE:
        return "moderate"
    if f_factor < SEVERITY_HIGH:
        return "high"
    return "severe"


def energy_height_loss_rate(f_factor, v):
    """Energy height loss rate in m/s implied by an F-factor at speed v.

    Rate = v*F. Exact for the escape condition where the excess-thrust
    term is zero (F then equals the demand); with nonzero excess thrust
    the exact relation is v*(F_demand - F_available), see windshear_verdict.
    Raises ValueError on a non-positive airspeed.
    """
    if v <= 0:
        raise ValueError("true airspeed must be > 0 m/s, got %r" % (v,))
    return f_factor * v


def altitude_loss(f_factor, v, time_s):
    """Altitude (energy height) lost over the encounter, in m.

    Loss = v*F*time_s, the energy height loss rate integrated over the
    encounter time. Raises ValueError on non-positive airspeed or a
    negative encounter time.
    """
    if v <= 0:
        raise ValueError("true airspeed must be > 0 m/s, got %r" % (v,))
    if time_s < 0:
        raise ValueError("encounter time must be >= 0 s, got %r" % (time_s,))
    return f_factor * v * time_s


def max_climb_rate_in_downdraft(excess_thrust, w, downdraft, v):
    """Check whether the aircraft can out-climb the downdraft.

    Still-air maximum climb rate from the excess thrust is
    RC = v*excess_thrust/w (m/s), compared against the downdraft speed.
    Returns a dict with max_climb_rate_mps, downdraft_mps, out_climbs
    (True only when the climb rate strictly exceeds the downdraft) and a
    verdict of out-climb, marginal (rates equal within 1e-9) or descend.
    Raises ValueError on non-positive weight or airspeed, or a negative
    excess thrust (negative excess thrust is a deficit, not a climb).
    """
    _validate_states(excess_thrust, 0.0, w, v=v)
    if excess_thrust < 0:
        raise ValueError("excess thrust must be >= 0 N, got %r" % (excess_thrust,))
    rc = v * excess_thrust / w
    if rc > downdraft + 1e-9:
        verdict = "out-climb"
        out_climbs = True
    elif rc < downdraft - 1e-9:
        verdict = "descend"
        out_climbs = False
    else:
        verdict = "marginal"
        out_climbs = False
    return {
        "max_climb_rate_mps": rc,
        "downdraft_mps": downdraft,
        "out_climbs": out_climbs,
        "verdict": verdict,
    }


def required_thrust_increment(f_target, current_f, w):
    """Thrust increase in N that raises F_available from current_f to f_target.

    dT = w*(f_target - current_f). For recovery from a shear encounter
    pass f_target = the environmental demand F_demand and current_f = the
    current excess-thrust ratio (t - d)/w; the increment then neutralizes
    the wind demand at the current drag and weight. Raises ValueError on
    a non-positive weight.
    """
    if w <= 0:
        raise ValueError("weight must be > 0 N, got %r" % (w,))
    return w * (f_target - current_f)


def _escape_verdict(f_demand):
    """Deterministic escape decision ladder from the demand F-factor."""
    if f_demand >= _ESC_VERDICT_SEVERE:
        return "escape"
    if f_demand >= _ESC_VERDICT_HIGH:
        return "high-alert"
    if f_demand >= _ESC_VERDICT_MODERATE:
        return "moderate-alert"
    return "monitor"


def windshear_verdict(t, d, w, v, a_wind, downdraft, time_s=20.0, g=G0, f_target=None):
    """Full encounter assessment as a dict.

    Inputs: thrust t, drag d, weight w (N), true airspeed v (m/s), the
    along-track wind acceleration a_wind = d(HW)/dt (m/s^2, positive for
    an increasing headwind), the downdraft w_d (m/s, positive downward),
    the encounter time (s) and gravity. Splits the total F-factor into
    F_available = (t - d)/w and F_demand = -a_wind/g + w_d/v, classifies
    the demand severity against the typical escape-guidance thresholds,
    computes the exact energy height loss rate v*(F_demand - F_available)
    and the altitude loss over the encounter, runs the downdraft
    out-climb check, and sizes the recovery thrust increment
    dT = w*(f_target - F_available) with f_target defaulting to F_demand.
    Raises ValueError on non-positive weight or airspeed, negative thrust
    or drag, or a negative encounter time.
    """
    _validate_states(t, d, w, v=v, g=g)
    if time_s < 0:
        raise ValueError("encounter time must be >= 0 s, got %r" % (time_s,))
    f_available = (t - d) / w
    f_demand = -a_wind / g + downdraft / v
    f_total = f_available + f_demand
    if f_target is None:
        f_target = f_demand
    loss_rate = v * (f_demand - f_available)
    climb = max_climb_rate_in_downdraft(t - d, w, downdraft, v)
    d_t = required_thrust_increment(f_target, f_available, w)
    return {
        "f_available": f_available,
        "f_demand": f_demand,
        "f_total": f_total,
        "severity": severity_class(f_demand),
        "energy_height_loss_rate_mps": loss_rate,
        "altitude_loss_m": loss_rate * time_s,
        "time_s": time_s,
        "max_climb_rate_mps": climb["max_climb_rate_mps"],
        "downdraft_mps": downdraft,
        "out_climbs": climb["out_climbs"],
        "climb_verdict": climb["verdict"],
        "required_thrust_increment_n": d_t,
        "thrust_to_weight_increment": d_t / w,
        "escape_verdict": _escape_verdict(f_demand),
    }
