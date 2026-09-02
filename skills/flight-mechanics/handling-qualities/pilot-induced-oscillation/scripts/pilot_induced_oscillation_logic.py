#!/usr/bin/env python3
"""Pilot-induced oscillation (PIO) categorization and phase-lag risk logic
(paraphrase).

A pilot-induced oscillation is an unintentional, sustained oscillation
of the aircraft that develops from the close coupling between the
pilot's control inputs and the aircraft response: the pilot's
corrective inputs add energy to the oscillation instead of damping it.
The standard categorization (flying qualities methodology, summary
only) groups PIO into three categories:

- Category I: linear aircraft response. The aircraft responds
  essentially linearly; the oscillation develops because the
  pilot-vehicle loop (pilot gain and lag plus aircraft and actuation
  lags) is unstable.
- Category II: quasi-linear response with rate-limited actuators or
  control surfaces. Rate saturation during the oscillation reduces the
  effective gain and adds phase lag, so describing-function methods are
  needed; the oscillation often appears at a frequency different from
  the linear prediction.
- Category III: nonlinear response, typically involving transitions:
  control law mode switching, surface saturation, or reversion to
  alternate modes during the task.

The phase-lag risk check interprets the phase lag of the pilot-vehicle
open loop at the crossover frequency (the frequency where the loop gain
passes through unity) as an equivalent time delay,
tau_e = |phase_lag_deg| / (360 * crossover_freq_hz), and returns a risk
band: low below 0.10 s, medium from 0.10 s to 0.20 s, high above
0.20 s. The phase margin is 180 + phase_lag_deg for the negative lag.
FAR-25 and CS-25 flight characteristics requirements frame the
assessment for transport aeroplanes (summary reference only,
standards-map.yaml).

Functions:
- categorize_pio(rate_limiting, nonlinear): Category I, II, or III.
- equivalent_time_delay(phase_lag_deg, crossover_freq_hz): seconds.
- phase_margin(phase_lag_deg): degrees.
- phase_lag_risk(phase_lag_deg, crossover_freq_hz): (band, margin, tau).
- suppression_measures(...): mitigation measures for the causes present.
"""

LOW_DELAY = 0.10
HIGH_DELAY = 0.20


def _validate_phase_lag(phase_lag_deg):
    if isinstance(phase_lag_deg, bool) or not isinstance(
            phase_lag_deg, (int, float)):
        raise ValueError(
            "phase_lag_deg must be a number in (-180, 0), got %r"
            % (phase_lag_deg,))
    if not (-180.0 < phase_lag_deg < 0.0):
        raise ValueError(
            "phase_lag_deg must be in (-180, 0) degrees, got %r"
            % (phase_lag_deg,))
    return float(phase_lag_deg)


def _validate_freq(crossover_freq_hz):
    if isinstance(crossover_freq_hz, bool) or not isinstance(
            crossover_freq_hz, (int, float)):
        raise ValueError(
            "crossover_freq_hz must be a positive number, got %r"
            % (crossover_freq_hz,))
    if crossover_freq_hz <= 0.0:
        raise ValueError(
            "crossover_freq_hz must be positive, got %r"
            % (crossover_freq_hz,))
    return float(crossover_freq_hz)


def categorize_pio(rate_limiting, nonlinear):
    """PIO category from the dominant response character.

    (False, False) gives 'Category I' (linear response); (True, False)
    gives 'Category II' (quasi-linear with rate-limited actuators); a
    nonlinear response gives 'Category III' regardless of rate
    limiting. Raises ValueError on non-bool arguments.
    """
    for flag, name in ((rate_limiting, "rate_limiting"),
                       (nonlinear, "nonlinear")):
        if not isinstance(flag, bool):
            raise ValueError("%s must be a bool, got %r" % (name, flag))
    if nonlinear:
        return "Category III"
    if rate_limiting:
        return "Category II"
    return "Category I"


def equivalent_time_delay(phase_lag_deg, crossover_freq_hz):
    """Equivalent time delay in seconds from the phase lag at crossover.

    tau_e = |phase_lag| / (360 * f). Worked: (-45.0, 1.0) = 0.125 s;
    (-90.0, 2.0) = 0.125 s; (-30.0, 2.0) = 0.0416667 s. Raises
    ValueError when the lag is not in (-180, 0) degrees or the frequency
    is not positive.
    """
    lag = _validate_phase_lag(phase_lag_deg)
    freq = _validate_freq(crossover_freq_hz)
    return abs(lag) / (360.0 * freq)


def phase_margin(phase_lag_deg):
    """Phase margin in degrees for a negative phase lag at crossover.

    margin = 180 + lag. Worked: (-45.0) = 135.0; (-120.0) = 60.0;
    (-160.0) = 20.0. Raises ValueError when the lag is not in
    (-180, 0) degrees.
    """
    lag = _validate_phase_lag(phase_lag_deg)
    return 180.0 + lag


def phase_lag_risk(phase_lag_deg, crossover_freq_hz):
    """Risk band (low/medium/high) from the phase lag at crossover.

    Returns (band, phase_margin_deg, equivalent_time_delay_s). The band
    follows the bandwidth-style equivalent time delay: below 0.10 s is
    low, 0.10-0.20 s is medium, above 0.20 s is high. Worked:
    (-30.0, 2.0) gives ('low', 150.0, 0.0416667);
    (-60.0, 1.0) gives ('medium', 120.0, 0.1666667);
    (-100.0, 1.0) gives ('high', 80.0, 0.2777778). Raises ValueError on
    invalid lag or frequency.
    """
    lag = _validate_phase_lag(phase_lag_deg)
    freq = _validate_freq(crossover_freq_hz)
    tau = abs(lag) / (360.0 * freq)
    if tau < LOW_DELAY:
        band = "low"
    elif tau <= HIGH_DELAY:
        band = "medium"
    else:
        band = "high"
    return (band, 180.0 + lag, tau)


def suppression_measures(phase_lag_deg, crossover_freq_hz,
                         rate_limiting=False, high_sensitivity=False,
                         structural_filter=False, nonlinear=False):
    """Suppression measures for the PIO causes present.

    Validates the loop data and the boolean flags. A medium or high
    risk band adds the gain reduction and phase lead compensation
    measure; each flagged cause adds its specific measure (actuator
    rate limiting, high control sensitivity, structural notch filter,
    nonlinear response). Returns the list of measures; an empty list
    means no measure is indicated by the inputs.
    """
    lag = _validate_phase_lag(phase_lag_deg)
    freq = _validate_freq(crossover_freq_hz)
    flags = {
        "rate_limiting": rate_limiting,
        "high_sensitivity": high_sensitivity,
        "structural_filter": structural_filter,
        "nonlinear": nonlinear,
    }
    for name, flag in flags.items():
        if not isinstance(flag, bool):
            raise ValueError("%s must be a bool, got %r" % (name, flag))
    band, _margin, _tau = phase_lag_risk(lag, freq)
    measures = []
    if band != "low":
        measures.append(
            "reduce the pilot-vehicle loop gain and add phase lead "
            "compensation to recover phase margin")
    if rate_limiting:
        measures.append(
            "increase the actuator rate limit or add command-rate "
            "shaping so the surface keeps up with pilot commands")
    if high_sensitivity:
        measures.append(
            "reduce the control sensitivity (gearing) so small pilot "
            "inputs produce proportionally smaller responses")
    if structural_filter:
        measures.append(
            "retune or relocate the structural notch filter to move "
            "its phase lag out of the piloted frequency band")
    if nonlinear:
        measures.append(
            "add control logic that prevents mode switching or "
            "reversion during the critical task")
    return measures


def demonstrate():
    """Print a demonstration of categorization and risk assessment."""
    for case in ((False, False), (True, False), (True, True),
                 (False, True)):
        print("categorize_pio%s -> %s" % (case, categorize_pio(*case)))
    for lag, freq in ((-30.0, 2.0), (-60.0, 1.0), (-100.0, 1.0)):
        band, margin, tau = phase_lag_risk(lag, freq)
        print("phase_lag_risk(%.1f, %.1f) -> %s, margin %.1f deg, "
              "delay %.4f s" % (lag, freq, band, margin, tau))
    measures = suppression_measures(-100.0, 1.0, rate_limiting=True,
                                    high_sensitivity=True,
                                    structural_filter=True,
                                    nonlinear=True)
    print("suppression_measures(...) ->")
    for measure in measures:
        print("  - " + measure)


if __name__ == "__main__":
    demonstrate()
