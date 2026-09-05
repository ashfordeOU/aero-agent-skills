"""Pure stdlib logic for the synodic-launch-window leaf.

Determines the interplanetary launch window timing between two planets
on near-circular coplanar orbits: the synodic period of the launch
opportunity recurrence, the required heliocentric departure phase angle
for a Hohmann window, the recurrence epochs and the phase progression
between windows. Stdlib only, deterministic, offline.
"""

import math

EARTH_YEAR_DAYS = 365.25
MARS_YEAR_DAYS = 686.98
EARTH_SMA_AU = 1.0
MARS_SMA_AU = 1.523679
TWO_PI = 2.0 * math.pi


def synodic_period(inner_period_days, outer_period_days):
    """Return the synodic period T_syn of the launch opportunity
    recurrence for an inner and an outer planet.

    T_syn = (T_in * T_out) / (T_out - T_in), the beat period of the two
    orbital frequencies. Raises ValueError if either period is not
    positive or the outer period does not exceed the inner period.
    """
    if inner_period_days <= 0 or outer_period_days <= 0:
        raise ValueError("both orbital periods must be positive")
    if outer_period_days <= inner_period_days:
        raise ValueError("the outer orbital period must exceed the inner one")
    return (inner_period_days * outer_period_days) / (
        outer_period_days - inner_period_days
    )


def hohmann_departure_phase_angle(inner_sma_au, outer_sma_au):
    """Return the required heliocentric departure phase angle in radians
    for a Hohmann window between two near-circular coplanar orbits.

    alpha_dep = pi * (1 - ((a_in + a_out) / 2 / a_out)**1.5). Raises
    ValueError if either semi-major axis is not positive or the outer
    semi-major axis does not exceed the inner one.
    """
    if inner_sma_au <= 0 or outer_sma_au <= 0:
        raise ValueError("both semi-major axes must be positive")
    if outer_sma_au <= inner_sma_au:
        raise ValueError("the outer semi-major axis must exceed the inner one")
    mean_radius_ratio = ((inner_sma_au + outer_sma_au) / 2.0) / outer_sma_au
    return math.pi * (1.0 - mean_radius_ratio ** 1.5)


def window_epochs(t0_days, synodic_days, count):
    """Return the recurrence epochs t_k = t_0 + k * T_syn for k in
    0..count-1 as a list of day values.

    Raises ValueError if count is below 1 or the synodic period is not
    positive.
    """
    if count < 1:
        raise ValueError("count must be at least one window")
    if synodic_days <= 0:
        raise ValueError("the synodic period must be positive")
    return [t0_days + k * synodic_days for k in range(count)]


def phase_progression(t_days, t0_days, synodic_days):
    """Return the heliocentric synodic phase advance in radians in
    [0, 2*pi) of the outer planet relative to the inner since t0.

    phase = 2 * pi * (((t - t0) / T_syn) mod 1), so the phase returns to
    zero modulo 2*pi at every recurrence epoch. Raises ValueError if the
    synodic period is not positive.
    """
    if synodic_days <= 0:
        raise ValueError("the synodic period must be positive")
    cycle_fraction = ((t_days - t0_days) / synodic_days) % 1.0
    return TWO_PI * cycle_fraction


def synodic_report(
    inner_period_days,
    outer_period_days,
    inner_sma_au,
    outer_sma_au,
    t0_days=0.0,
    count=3,
):
    """Return the interplanetary window summary dict for the two planets.

    Keys: synodic_period_days, departure_phase_angle_deg, window_epochs
    and phase_at_first_window (the synodic phase at the first recurrence
    epoch, zero modulo 2*pi by construction). All inputs are validated by
    the underlying functions.
    """
    t_syn = synodic_period(inner_period_days, outer_period_days)
    alpha_rad = hohmann_departure_phase_angle(inner_sma_au, outer_sma_au)
    epochs = window_epochs(t0_days, t_syn, count)
    phase_first = phase_progression(epochs[0], t0_days, t_syn)
    return {
        "synodic_period_days": t_syn,
        "departure_phase_angle_deg": math.degrees(alpha_rad),
        "window_epochs": epochs,
        "phase_at_first_window": phase_first,
    }
