#!/usr/bin/env python3
"""MIL-STD-1797A flying qualities assessment logic (summary paraphrase).

MIL-STD-1797A (Flying Qualities of Piloted Aircraft, the successor to
MIL-F-8785C) grades the dynamic stability and response of an aircraft
against level criteria that depend on the flight phase category, the
aircraft class, and the required level of flying qualities. This module
implements the classic category/class/level framework and the mode
criteria tables as a summary paraphrase (reference only, not a
reproduction of the standard; see standards-map.yaml).

Flight phase categories:
  A: nonterminal phases requiring rapid maneuvering, precision
     tracking, or precise flight-path control (air-to-air combat,
     ground attack, in-flight refueling as receiver, terrain
     following, close formation)
  B: nonterminal phases accomplished with gradual maneuvers and
     without precision tracking (climb, cruise, loiter, descent,
     in-flight refueling as tanker)
  C: terminal phases (takeoff, approach, landing, wave-off/go-around)

Aircraft classes:
  I: small, light (utility, primary trainer)
  II: medium weight, low-to-medium maneuverability (small transport,
      tactical bomber)
  III: large, heavy, low-to-medium maneuverability (heavy transport,
       tanker, bomber)
  IV: high maneuverability (fighter, attack)

Flying qualities levels:
  1: clearly adequate for the mission flight phase, desired
     performance with minimal pilot compensation
  2: adequate to accomplish the mission phase with some increase in
     pilot workload or degradation of mission effectiveness
  3: controllable safely, but with excessive workload or inadequate
     mission effectiveness

Mode criteria (summary of the standard's tables; all frequencies in
rad/s, times in seconds):
  Short period: Level 1 damping ratio 0.35-1.30; minimum natural
    frequency from the category/class table, interpolated in n/alpha
    (g/rad) between the n/alpha = 1.0 and n/alpha = 3.0 values:
    category A classes I/II/III/IV: 3.6/3.6/3.0/2.5 rising to 6.0 at
    n/alpha = 3.0; categories B and C: 1.0 rising to 2.0. Level 2
    damping 0.25-2.00; Level 3 minimum 0.15. The frequency
    requirement applies at Level 1; a Level 1 damping with a frequency
    below the table minimum is graded Level 2 (degraded tracking).
  Phugoid: Level 1 damping ratio >= 0.04; Level 2 >= 0 (stable);
    Level 3 time to double >= 55 s (slow divergence allowed).
  Dutch roll: Level 1 category A class IV: zeta >= 0.19, omega >= 1.0,
    zeta*omega >= 0.35; category A classes I-III: zeta >= 0.19,
    omega >= 0.4, zeta*omega >= 0.35; categories B and C: zeta >= 0.08,
    omega >= 0.4, zeta*omega >= 0.15. Level 2: zeta >= 0.02,
    omega >= 0.4, zeta*omega >= 0.05. Level 3: zeta > 0 (stable).
  Spiral: minimum time to double: Level 1: 20 s (categories A and C),
    12 s (category B); Level 2: 8 s; Level 3: 4 s.
  Roll mode: maximum time constant: Level 1: 1.0 s (A), 1.4 s (B),
    1.0 s (C); Level 2: 1.4 s (A), 3.0 s (B), 1.4 s (C); Level 3:
    10 s (all).
  Roll performance (category A only): time to a 60 deg bank angle
    change: Level 1: 1.3 s (classes I, II, IV), 1.7 s (class III);
    Level 2: 1.8 s (I, II, IV), 2.5 s (III); Level 3: 3.6 s (I, II,
    IV), 5.0 s (III). The first-order roll response
    phi(t) = p_ss * (t - tau * (1 - exp(-t / tau))) gives the bank
    angle in 1 s and the time to 60 deg and 90 deg from the steady
    roll rate p_ss (deg/s) and the roll mode time constant tau (s).

Every assess function takes a state dict with the mode's measured
values plus the flight phase category and aircraft class, and returns
a verdict dict: {"level": 1|2|3, "verdict": "PASS"|"FAIL", "reason":
str, "metrics": {...}}. Invalid categories, classes, and physically
invalid values raise ValueError. The overall level is the worst
(limiting) level across the assessed modes.
"""

import math

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

CATEGORIES = ("A", "B", "C")
CLASSES = ("I", "II", "III", "IV")
LEVELS = (1, 2, 3)

CATEGORY_DESCRIPTIONS = {
    "A": "nonterminal phases requiring rapid maneuvering, precision "
         "tracking, or precise flight-path control",
    "B": "nonterminal phases accomplished with gradual maneuvers "
         "without precision tracking",
    "C": "terminal phases (takeoff and landing) requiring accurate "
         "flight-path control",
}

CLASS_DESCRIPTIONS = {
    "I": "small, light aircraft (utility, primary trainer)",
    "II": "medium weight, medium maneuverability (small transport, "
          "tactical bomber)",
    "III": "large, heavy, low maneuverability (heavy transport, "
           "tanker, bomber)",
    "IV": "high-maneuverability (fighter, attack)",
}

LEVEL_DESCRIPTIONS = {
    1: "clearly adequate: desired performance with minimal pilot compensation",
    2: "adequate: increased pilot workload or degraded mission effectiveness",
    3: "safe but marginal: controllable with excessive workload or "
       "inadequate mission effectiveness",
}

# Cooper-Harper rating bands tied to each level (see cooper-harper-rating
# skill for the full decision tree): 1-3 satisfactory without improvement,
# 4-6 deficiencies warrant improvement, 7-9 deficiencies require
# improvement, 10 uncontrollable (outside the level framework).
COOPER_HARPER_BANDS = {
    1: (1, 3),
    2: (4, 6),
    3: (7, 9),
}

# ---------------------------------------------------------------------------
# Criteria tables (summary paraphrase, reference only)
# ---------------------------------------------------------------------------

# Short-period damping ratio bands per level (category independent):
# (min, max); Level 3 is a minimum with no upper bound.
SHORT_PERIOD_DAMPING = {
    1: (0.35, 1.30),
    2: (0.25, 2.00),
    3: (0.15, None),
}

# Short-period minimum frequency (rad/s) at n/alpha = 1.0 and 3.0 g/rad
# per (category, class). Linear interpolation between, clamped outside.
SHORT_PERIOD_FREQ_N1 = {
    "A": {"I": 3.6, "II": 3.6, "III": 3.0, "IV": 2.5},
    "B": {"I": 1.0, "II": 1.0, "III": 1.0, "IV": 1.0},
    "C": {"I": 1.0, "II": 1.0, "III": 1.0, "IV": 1.0},
}
SHORT_PERIOD_FREQ_N3 = {
    "A": {"I": 6.0, "II": 6.0, "III": 6.0, "IV": 6.0},
    "B": {"I": 2.0, "II": 2.0, "III": 2.0, "IV": 2.0},
    "C": {"I": 2.0, "II": 2.0, "III": 2.0, "IV": 2.0},
}
N_ALPHA_MIN = 1.0
N_ALPHA_MAX = 3.0

# Phugoid: minimum damping ratio per level (Level 3 expressed as minimum
# time to double).
PHUGOID_DAMPING = {1: 0.04, 2: 0.0}
PHUGOID_T2_LEVEL3 = 55.0

# Dutch roll (zeta_min, omega_min rad/s, zeta*omega_min) per
# (level, category, class). Category A class IV is the strictest row.
DUTCH_ROLL_CRITERIA = {
    1: {
        "A": {"IV": (0.19, 1.0, 0.35),
              "I": (0.19, 0.4, 0.35),
              "II": (0.19, 0.4, 0.35),
              "III": (0.19, 0.4, 0.35)},
        "B": {"I": (0.08, 0.4, 0.15), "II": (0.08, 0.4, 0.15),
              "III": (0.08, 0.4, 0.15), "IV": (0.08, 0.4, 0.15)},
        "C": {"I": (0.08, 0.4, 0.15), "II": (0.08, 0.4, 0.15),
              "III": (0.08, 0.4, 0.15), "IV": (0.08, 0.4, 0.15)},
    },
    2: {
        "A": {c: (0.02, 0.4, 0.05) for c in CLASSES},
        "B": {c: (0.02, 0.4, 0.05) for c in CLASSES},
        "C": {c: (0.02, 0.4, 0.05) for c in CLASSES},
    },
}
DUTCH_ROLL_LEVEL3_MIN_ZETA = 0.0  # must be stable (zeta > 0)

# Spiral: minimum time to double amplitude (s) per level and category.
SPIRAL_T2 = {
    1: {"A": 20.0, "B": 12.0, "C": 20.0},
    2: {"A": 8.0, "B": 8.0, "C": 8.0},
    3: {"A": 4.0, "B": 4.0, "C": 4.0},
}

# Roll mode: maximum time constant (s) per level and category.
ROLL_MODE_TAU_MAX = {
    1: {"A": 1.0, "B": 1.4, "C": 1.0},
    2: {"A": 1.4, "B": 3.0, "C": 1.4},
    3: {"A": 10.0, "B": 10.0, "C": 10.0},
}

# Roll performance (category A only): maximum time (s) to a 60 deg bank
# angle change per level and class.
ROLL_PERFORMANCE_T60 = {
    1: {"I": 1.3, "II": 1.3, "III": 1.7, "IV": 1.3},
    2: {"I": 1.8, "II": 1.8, "III": 2.5, "IV": 1.8},
    3: {"I": 3.6, "II": 3.6, "III": 5.0, "IV": 3.6},
}

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate(category, aircraft_class):
    if category not in CATEGORIES:
        raise ValueError(
            "flight phase category must be one of %s, got %r"
            % ("/".join(CATEGORIES), category)
        )
    if aircraft_class not in CLASSES:
        raise ValueError(
            "aircraft class must be one of %s, got %r"
            % ("/".join(CLASSES), aircraft_class)
        )


def _require(name, value, minimum=0.0, inclusive=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if inclusive and value < minimum:
        raise ValueError("%s must be >= %s, got %r" % (name, minimum, value))
    if not inclusive and value <= minimum:
        raise ValueError("%s must be > %s, got %r" % (name, minimum, value))


# ---------------------------------------------------------------------------
# Short period
# ---------------------------------------------------------------------------


def short_period_min_frequency(category, aircraft_class, n_over_alpha=1.0):
    """Minimum short-period natural frequency (rad/s) from the
    category/class table, linearly interpolated in n/alpha (g/rad)
    between n/alpha = 1.0 and 3.0 and clamped outside that range."""
    _validate(category, aircraft_class)
    _require("n_over_alpha", n_over_alpha, 0.0, inclusive=False)
    n = min(max(n_over_alpha, N_ALPHA_MIN), N_ALPHA_MAX)
    f1 = SHORT_PERIOD_FREQ_N1[category][aircraft_class]
    f3 = SHORT_PERIOD_FREQ_N3[category][aircraft_class]
    t = (n - N_ALPHA_MIN) / (N_ALPHA_MAX - N_ALPHA_MIN)
    return f1 + t * (f3 - f1)


def assess_short_period(state, category, aircraft_class):
    """Grade the short-period mode (state keys: zeta_sp, omega_sp,
    optional n_over_alpha, default 1.0 g/rad)."""
    _validate(category, aircraft_class)
    zeta = state.get("zeta_sp")
    omega = state.get("omega_sp")
    n_over_alpha = state.get("n_over_alpha", 1.0)
    if zeta is None or omega is None:
        raise ValueError("state must provide zeta_sp and omega_sp")
    if not isinstance(zeta, (int, float)) or isinstance(zeta, bool):
        raise ValueError("zeta_sp must be a number, got %r" % (zeta,))
    _require("omega_sp", omega, 0.0, inclusive=False)
    _require("n_over_alpha", n_over_alpha, 0.0, inclusive=False)

    min_omega = short_period_min_frequency(category, aircraft_class,
                                           n_over_alpha)

    if SHORT_PERIOD_DAMPING[1][0] <= zeta <= SHORT_PERIOD_DAMPING[1][1]:
        level = 1
    elif SHORT_PERIOD_DAMPING[2][0] <= zeta <= SHORT_PERIOD_DAMPING[2][1]:
        level = 2
    else:
        level = 3  # includes negative zeta (divergent oscillation)

    if level == 1 and omega < min_omega:
        level = 2  # frequency deficiency degrades tracking -> Level 2

    if zeta < SHORT_PERIOD_DAMPING[3][0]:
        reason = "damping %s below Level 3 minimum %s" % (
            zeta, SHORT_PERIOD_DAMPING[3][0])
    else:
        reason = "damping %s in [%s, %s]" % (
            zeta, SHORT_PERIOD_DAMPING[level][0],
            SHORT_PERIOD_DAMPING[level][1] if SHORT_PERIOD_DAMPING[level][1]
            else "inf")
    freq_ok = omega >= min_omega
    if not freq_ok:
        reason += "; frequency %s below minimum %s" % (omega, min_omega)

    return {
        "mode": "short_period",
        "level": level,
        "verdict": "PASS" if level == 1 else "FAIL",
        "reason": reason,
        "metrics": {
            "zeta_sp": zeta,
            "omega_sp": omega,
            "n_over_alpha": n_over_alpha,
            "min_omega": min_omega,
            "frequency_ok": freq_ok,
        },
    }


# ---------------------------------------------------------------------------
# Phugoid
# ---------------------------------------------------------------------------


def _phugoid_time_to_double(zeta, omega, t2):
    """Time to double amplitude (s) for a divergent phugoid:
    T2 = ln(2) / |zeta * omega_n|. Prefers the measured t2 when given."""
    if t2 is not None:
        return t2
    if omega is None or omega <= 0:
        raise ValueError(
            "state must provide t2_ph or omega_ph when zeta_ph < 0")
    return math.log(2.0) / (abs(zeta) * omega)


def assess_phugoid(state, category, aircraft_class):
    """Grade the phugoid mode (state keys: zeta_ph; optional t2_ph or
    omega_ph used only when zeta_ph < 0)."""
    _validate(category, aircraft_class)
    zeta = state.get("zeta_ph")
    if zeta is None:
        raise ValueError("state must provide zeta_ph")
    if not isinstance(zeta, (int, float)) or isinstance(zeta, bool):
        raise ValueError("zeta_ph must be a number, got %r" % (zeta,))

    if zeta >= PHUGOID_DAMPING[1]:
        level = 1
    elif zeta >= PHUGOID_DAMPING[2]:
        level = 2
    else:
        # Level 3 requires T2 >= 55 s; a faster divergence is still
        # graded Level 3 (the worst level) but is flagged in the reason.
        level = 3

    reason = "damping %s" % (zeta,)
    if level == 3:
        t2 = _phugoid_time_to_double(zeta, state.get("omega_ph"),
                                     state.get("t2_ph"))
        if t2 < PHUGOID_T2_LEVEL3:
            reason += "; time to double %s s below Level 3 minimum %s s" % (
                t2, PHUGOID_T2_LEVEL3)
        else:
            reason += "; time to double %s s (Level 3 boundary)" % (t2,)

    return {
        "mode": "phugoid",
        "level": level,
        "verdict": "PASS" if level == 1 else "FAIL",
        "reason": reason,
        "metrics": {"zeta_ph": zeta,
                    "t2_ph": _phugoid_time_to_double(
                        zeta, state.get("omega_ph"), state.get("t2_ph"))
                    if zeta < PHUGOID_DAMPING[2] else None},
    }


# ---------------------------------------------------------------------------
# Dutch roll
# ---------------------------------------------------------------------------


def dutch_roll_criteria(level, category, aircraft_class):
    """(zeta_min, omega_min, zeta_omega_min) tuple for a level."""
    _validate(category, aircraft_class)
    if level not in LEVELS:
        raise ValueError("level must be 1, 2, or 3, got %r" % (level,))
    if level == 3:
        return (DUTCH_ROLL_LEVEL3_MIN_ZETA, 0.0, 0.0)
    return DUTCH_ROLL_CRITERIA[level][category][aircraft_class]


def assess_dutch_roll(state, category, aircraft_class):
    """Grade the dutch roll mode (state keys: zeta_dr, omega_dr)."""
    _validate(category, aircraft_class)
    zeta = state.get("zeta_dr")
    omega = state.get("omega_dr")
    if zeta is None or omega is None:
        raise ValueError("state must provide zeta_dr and omega_dr")
    if not isinstance(zeta, (int, float)) or isinstance(zeta, bool):
        raise ValueError("zeta_dr must be a number, got %r" % (zeta,))
    _require("omega_dr", omega, 0.0, inclusive=False)

    if zeta <= 0.0:
        # Divergent or undamped: fails the Level 3 stability row.
        level = 3
    else:
        zeta_omega = zeta * omega
        l1 = dutch_roll_criteria(1, category, aircraft_class)
        if (zeta >= l1[0] and omega >= l1[1] and zeta_omega >= l1[2]):
            level = 1
        else:
            l2 = dutch_roll_criteria(2, category, aircraft_class)
            if (zeta >= l2[0] and omega >= l2[1] and zeta_omega >= l2[2]):
                level = 2
            else:
                level = 3

    return {
        "mode": "dutch_roll",
        "level": level,
        "verdict": "PASS" if level == 1 else "FAIL",
        "reason": "damping %s, frequency %s, product %s" % (
            zeta, omega, zeta * omega),
        "metrics": {"zeta_dr": zeta, "omega_dr": omega,
                    "zeta_omega": zeta * omega},
    }


# ---------------------------------------------------------------------------
# Spiral
# ---------------------------------------------------------------------------


def assess_spiral(state, category, aircraft_class):
    """Grade the spiral mode (state key: t2_spiral, seconds to double
    amplitude; use a large value, e.g. None, for a stable spiral)."""
    _validate(category, aircraft_class)
    t2 = state.get("t2_spiral")
    if t2 is None:
        t2 = float("inf")  # stable spiral never doubles
    _require("t2_spiral", t2, 0.0, inclusive=True)

    if t2 >= SPIRAL_T2[1][category]:
        level = 1
    elif t2 >= SPIRAL_T2[2][category]:
        level = 2
    else:
        level = 3

    return {
        "mode": "spiral",
        "level": level,
        "verdict": "PASS" if level == 1 else "FAIL",
        "reason": "time to double %s s (Level 1 minimum %s s)" % (
            t2 if math.isfinite(t2) else "inf", SPIRAL_T2[1][category]),
        "metrics": {"t2_spiral": t2,
                    "min_t2_level1": SPIRAL_T2[1][category]},
    }


# ---------------------------------------------------------------------------
# Roll mode
# ---------------------------------------------------------------------------


def assess_roll_mode(state, category, aircraft_class):
    """Grade the roll subsidence mode (state key: tau_roll, seconds)."""
    _validate(category, aircraft_class)
    tau = state.get("tau_roll")
    if tau is None:
        raise ValueError("state must provide tau_roll")
    _require("tau_roll", tau, 0.0, inclusive=True)

    if tau <= ROLL_MODE_TAU_MAX[1][category]:
        level = 1
    elif tau <= ROLL_MODE_TAU_MAX[2][category]:
        level = 2
    else:
        level = 3

    return {
        "mode": "roll_mode",
        "level": level,
        "verdict": "PASS" if level == 1 else "FAIL",
        "reason": "time constant %s s (Level 1 maximum %s s)" % (
            tau, ROLL_MODE_TAU_MAX[1][category]),
        "metrics": {"tau_roll": tau,
                    "max_tau_level1": ROLL_MODE_TAU_MAX[1][category]},
    }


# ---------------------------------------------------------------------------
# Roll performance
# ---------------------------------------------------------------------------


def roll_response_bank_angle(p_ss, tau, t):
    """Bank angle (deg) at time t (s) for a first-order roll response to
    a step aileron input: phi(t) = p_ss * (t - tau * (1 - exp(-t/tau)))."""
    if t <= 0:
        return 0.0
    return p_ss * (t - tau * (1.0 - math.exp(-t / tau)))


def _roll_time_to_bank(p_ss, tau, target_deg, tol=1e-9):
    """Time (s) to reach target_deg bank angle by bisection on the
    monotone first-order roll response."""
    lo, hi = 0.0, max(60.0, 4.0 * tau + target_deg / max(p_ss, 1e-12))
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if roll_response_bank_angle(p_ss, tau, mid) < target_deg:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def assess_roll_performance(state, category, aircraft_class):
    """Grade roll performance from the steady roll rate p_ss (deg/s) and
    the roll mode time constant tau_roll (s): computes the bank angle
    reached in 1 s, the time to a 60 deg bank change (the standard's
    category A criterion), and the time to 90 deg. An optional measured
    t_60 (state key t_60_measured) overrides the computed value. The
    standard applies the 60 deg roll performance criterion to category A
    only; for B and C the roll mode time constant is the criterion and
    the verdict level is reported as None (not applicable)."""
    _validate(category, aircraft_class)
    p_ss = state.get("roll_rate_ss")
    tau = state.get("roll_mode_tau")
    if p_ss is None or tau is None:
        raise ValueError("state must provide roll_rate_ss and roll_mode_tau")
    _require("roll_rate_ss", p_ss, 0.0, inclusive=False)
    _require("roll_mode_tau", tau, 0.0, inclusive=True)

    phi_1s = roll_response_bank_angle(p_ss, tau, 1.0)
    t_60 = state.get("t_60_measured")
    if t_60 is None:
        t_60 = _roll_time_to_bank(p_ss, tau, 60.0)
    else:
        _require("t_60_measured", t_60, 0.0, inclusive=True)
    t_90 = _roll_time_to_bank(p_ss, tau, 90.0)

    if category != "A":
        return {
            "mode": "roll_performance",
            "level": None,
            "verdict": "N/A",
            "reason": "roll performance criterion applies to category A "
                      "only; roll mode time constant is the criterion "
                      "for category %s" % (category,),
            "metrics": {"phi_1s": phi_1s, "t_60": t_60, "t_90": t_90},
        }

    if t_60 <= ROLL_PERFORMANCE_T60[1][aircraft_class]:
        level = 1
    elif t_60 <= ROLL_PERFORMANCE_T60[2][aircraft_class]:
        level = 2
    else:
        level = 3

    return {
        "mode": "roll_performance",
        "level": level,
        "verdict": "PASS" if level == 1 else "FAIL",
        "reason": "time to 60 deg bank %s s (Level 1 maximum %s s)" % (
            t_60, ROLL_PERFORMANCE_T60[1][aircraft_class]),
        "metrics": {"phi_1s": phi_1s, "t_60": t_60, "t_90": t_90,
                    "max_t60_level1": ROLL_PERFORMANCE_T60[1][aircraft_class]},
    }


# ---------------------------------------------------------------------------
# Overall
# ---------------------------------------------------------------------------


def combine_levels(assessments):
    """Worst (limiting) level across the mode assessments. Modes with
    level None (not applicable) are skipped."""
    graded = {name: v["level"] for name, v in assessments.items()
              if v["level"] is not None}
    if not graded:
        return 1, []
    worst = max(graded.values())
    limiting = [name for name, level in graded.items() if level == worst]
    return worst, limiting


def overall_flying_qualities_level(state, category, aircraft_class):
    """Run every mode assessment and return the overall (limiting) level
    with the per-mode verdicts and the Cooper-Harper band tie-in."""
    _validate(category, aircraft_class)
    assessments = {
        "short_period": assess_short_period(state, category, aircraft_class),
        "phugoid": assess_phugoid(state, category, aircraft_class),
        "dutch_roll": assess_dutch_roll(state, category, aircraft_class),
        "spiral": assess_spiral(state, category, aircraft_class),
        "roll_mode": assess_roll_mode(state, category, aircraft_class),
        "roll_performance": assess_roll_performance(state, category,
                                                    aircraft_class),
    }
    level, limiting = combine_levels(assessments)
    return {
        "level": level,
        "limiting_modes": limiting,
        "category": category,
        "aircraft_class": aircraft_class,
        "cooper_harper_band": COOPER_HARPER_BANDS[level],
        "assessments": assessments,
    }
