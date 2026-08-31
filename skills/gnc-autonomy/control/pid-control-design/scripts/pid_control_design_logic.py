#!/usr/bin/env python3
"""PID controller design logic for aerospace flight/GNC loops (paraphrase,
common textbook control theory; ARP4754A supplies the development-assurance
context only, per standards-map.yaml).

Deterministic, stdlib-only, offline. All functions validate inputs and
raise ValueError on impossible values.

Conventions (documented in SKILL.md):
- PID output  u = kp*e + ki*int(e) + kd*de/dt  with error terms in the
  plant's engineering units and gains in compatible units.
- Ziegler-Nichols continuous-cycling (closed-loop) tuning from the
  ultimate gain ku and ultimate period tu, classic rules:
  P:   kp = 0.5*ku
  PI:  kp = 0.45*ku,  Ti = tu/1.2
  PID: kp = 0.6*ku,   Ti = tu/2,  Td = tu/8
- Pole placement for the plant b/(s + a) with a PI controller and the
  plant b/(s^2 + a1*s + a0) with a PID controller, matching the closed
  loop to s^2 + 2*zeta*wn*s + wn^2 (and an extra real pole at -p3 for
  the second-order plant).
- Anti-windup by conditional integration (integrator clamping).
- Margins for the type-1 open loop K/(s(s + a)): finite phase margin,
  infinite gain margin (phase reaches -180 deg only at infinite
  frequency).
"""

import math


def _require_finite(value, name):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))


def _require_ge(value, bound, name):
    if value < bound:
        raise ValueError("%s must be >= %s, got %r" % (name, bound, value))


def _require_gt(value, bound, name):
    if value <= bound:
        raise ValueError("%s must be > %s, got %r" % (name, bound, value))


def pid_output(kp, ki, kd, error, integral, derivative):
    """PID controller output u = kp*error + ki*integral + kd*derivative.

    error, integral, derivative are the error, its accumulated integral,
    and its derivative in plant units; kp > 0 and ki, kd >= 0 (structural
    sanity rule shared with the control-design siblings).
    """
    for g, val in (("kp", kp), ("ki", ki), ("kd", kd)):
        _require_finite(val, g)
    _require_gt(kp, 0.0, "kp")
    _require_ge(ki, 0.0, "ki")
    _require_ge(kd, 0.0, "kd")
    for v, n in ((error, "error"), (integral, "integral"),
                 (derivative, "derivative")):
        _require_finite(v, n)
    return kp * error + ki * integral + kd * derivative


def ziegler_nichols(ku, tu, kind="pid"):
    """Ziegler-Nichols gains (classic rules) from ultimate gain ku and
    ultimate period tu (continuous cycling). kind in {'p', 'pi', 'pid'}.

    Returns {"kp", "ki", "kd", "ti", "td"}; ti/td are None for kinds that
    do not use that term. ku and tu must be > 0.
    """
    _require_gt(ku, 0.0, "ku")
    _require_gt(tu, 0.0, "tu")
    if kind == "p":
        return {"kp": 0.5 * ku, "ki": 0.0, "kd": 0.0,
                "ti": None, "td": None}
    if kind == "pi":
        kp = 0.45 * ku
        ti = tu / 1.2
        return {"kp": kp, "ki": kp / ti, "kd": 0.0,
                "ti": ti, "td": None}
    if kind == "pid":
        kp = 0.6 * ku
        ti = tu / 2.0
        td = tu / 8.0
        return {"kp": kp, "ki": kp / ti, "kd": kp * td,
                "ti": ti, "td": td}
    raise ValueError("kind must be one of 'p', 'pi', 'pid', got %r" % (kind,))


def pole_placement_first_order(a, b, wn, zeta):
    """PI gains (kp, ki) for the first-order plant G(s) = b/(s + a) with
    controller C(s) = kp + ki/s, matching the closed loop to
    s^2 + 2*zeta*wn*s + wn^2.

    kp = (2*zeta*wn - a)/b, ki = wn^2/b. Requires b != 0, wn > 0,
    0 < zeta <= 1.
    """
    if b == 0:
        raise ValueError("b must be nonzero, got %r" % (b,))
    _require_gt(wn, 0.0, "wn")
    _require_gt(zeta, 0.0, "zeta")
    if zeta > 1.0:
        raise ValueError("zeta must be in (0, 1], got %r" % (zeta,))
    kp = (2.0 * zeta * wn - a) / b
    ki = wn * wn / b
    return kp, ki


def pole_placement_second_order(a1, a0, b, wn, zeta, p3):
    """PID gains (kp, ki, kd) for the second-order plant
    G(s) = b/(s^2 + a1*s + a0) with controller C(s) = kp + ki/s + kd*s,
    matching the closed loop to (s^2 + 2*zeta*wn*s + wn^2)(s + p3).

    kd = (2*zeta*wn + p3 - a1)/b
    kp = (wn^2 + 2*zeta*wn*p3 - a0)/b
    ki = wn^2*p3/b
    Requires b != 0, wn > 0, 0 < zeta <= 1, p3 > 0.
    """
    if b == 0:
        raise ValueError("b must be nonzero, got %r" % (b,))
    _require_gt(wn, 0.0, "wn")
    if not (0.0 < zeta <= 1.0):
        raise ValueError("zeta must be in (0, 1], got %r" % (zeta,))
    _require_gt(p3, 0.0, "p3")
    kd = (2.0 * zeta * wn + p3 - a1) / b
    kp = (wn * wn + 2.0 * zeta * wn * p3 - a0) / b
    ki = wn * wn * p3 / b
    return kp, ki, kd


def integrator_clamp(integral, error, ki, dt, limit):
    """Anti-windup integrator clamp (conditional integration).

    Integrates ki*error*dt onto the running integral and clamps the
    result to [-limit, limit] so a saturated actuator cannot wind the
    integrator up. Requires ki >= 0, dt > 0, limit > 0.
    """
    _require_ge(ki, 0.0, "ki")
    _require_gt(dt, 0.0, "dt")
    _require_gt(limit, 0.0, "limit")
    _require_finite(integral, "integral")
    _require_finite(error, "error")
    trial = integral + ki * error * dt
    if trial > limit:
        return limit
    if trial < -limit:
        return -limit
    return trial


def stability_margins_type1(a, K):
    """Gain and phase margin of the type-1 open loop L(s) = K/(s(s + a)).

    Crossover frequency wc where |L(j*wc)| = 1 solves
    K^2 = wc^2 * (wc^2 + a^2); phase margin is
    90 - atan(wc/a) in degrees. The phase of L approaches -180 deg only
    as w -> inf, so the gain margin is infinite (reported as float inf).
    Requires a > 0, K > 0.
    """
    _require_gt(a, 0.0, "a")
    _require_gt(K, 0.0, "K")
    wc2 = (-a * a + math.sqrt(a ** 4 + 4.0 * K * K)) / 2.0
    wc = math.sqrt(wc2)
    pm = 90.0 - math.degrees(math.atan(wc / a))
    return {"crossover_rad_s": wc, "phase_margin_deg": pm,
            "gain_margin": float("inf")}


def discrete_derivative(e_now, e_prev, dt):
    """Backward-difference derivative term (e_now - e_prev)/dt, the
    first-order discrete approximation used in sampled PID loops.
    Requires dt > 0.
    """
    _require_gt(dt, 0.0, "dt")
    _require_finite(e_now, "e_now")
    _require_finite(e_prev, "e_prev")
    return (e_now - e_prev) / dt
