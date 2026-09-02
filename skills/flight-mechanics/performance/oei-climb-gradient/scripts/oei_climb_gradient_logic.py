#!/usr/bin/env python3
"""One-engine-inoperative climb gradient logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context, cs-25 mirrors it): FAR-25.121 sets minimum
steady climb gradients with one engine inoperative. The available
gradient follows from the excess thrust over the drag at the
aircraft weight: gamma = (T_oei - D) / W. The remaining-engine
thrust is the total installed thrust derated by the engine count:
T_oei = T_total * (n - f) / n. Minimum gradients in percent:
second segment (25.121(b)) 2.4 / 2.7 / 3.0 for 2 / 3 / 4 engines,
approach climb (25.121(d)) 2.1 / 2.4 / 2.7, landing climb
(25.121(e)) 3.2 for every engine count. Units: forces in N, speed
in m/s, gradient as a dimensionless fraction (percent = * 100).
"""


def oei_thrust(total_thrust_n, n_engines, failed_engines=1):
    """Net thrust available with engines failed: total * (n - f) / n.

    Raises ValueError on non-positive total thrust, on an engine
    count below 2 or non-integer, and on a failed count outside
    the 1..n-1 range.
    """
    if total_thrust_n <= 0:
        raise ValueError("total thrust must be > 0 N, got %r" % (total_thrust_n,))
    if not isinstance(n_engines, int) or n_engines < 2:
        raise ValueError("engine count must be an integer >= 2, got %r" % (n_engines,))
    if not isinstance(failed_engines, int) or failed_engines < 1 or failed_engines >= n_engines:
        raise ValueError(
            "failed engine count must be an integer in 1..n-1, got %r" % (failed_engines,)
        )
    return total_thrust_n * (n_engines - failed_engines) / n_engines


def climb_gradient(t_oei_n, drag_n, weight_n):
    """Steady climb gradient fraction (T_oei - D) / W.

    A negative result is a legitimate no-climb verdict. Raises
    ValueError on non-positive weight or negative drag or thrust.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0 N, got %r" % (weight_n,))
    if drag_n < 0:
        raise ValueError("drag must be >= 0 N, got %r" % (drag_n,))
    if t_oei_n < 0:
        raise ValueError("thrust must be >= 0 N, got %r" % (t_oei_n,))
    return (t_oei_n - drag_n) / weight_n


def gradient_percent(gradient_fraction):
    """Gradient as a dimensionless fraction converted to percent."""
    return gradient_fraction * 100.0


def rate_of_climb(gradient_fraction, v_ms):
    """Rate of climb in m/s from the gradient fraction and airspeed."""
    if v_ms <= 0:
        raise ValueError("speed must be > 0 m/s, got %r" % (v_ms,))
    return gradient_fraction * v_ms


def second_segment_minimum(n_engines):
    """FAR-25.121(b) second segment minimum gradient in percent.

    One engine inoperative, takeoff configuration, gear up, at V2:
    2.4 for 2 engines, 2.7 for 3 engines, 3.0 for 4 engines.
    Raises ValueError for engine counts outside 2..4.
    """
    table = {2: 2.4, 3: 2.7, 4: 3.0}
    if n_engines not in table:
        raise ValueError("engine count must be 2, 3, or 4, got %r" % (n_engines,))
    return table[n_engines]


def approach_climb_minimum(n_engines):
    """FAR-25.121(d) approach climb minimum gradient in percent.

    Critical engine inoperative, gear down, go-around power:
    2.1 for 2 engines, 2.4 for 3 engines, 2.7 for 4 engines.
    Raises ValueError for engine counts outside 2..4.
    """
    table = {2: 2.1, 3: 2.4, 4: 2.7}
    if n_engines not in table:
        raise ValueError("engine count must be 2, 3, or 4, got %r" % (n_engines,))
    return table[n_engines]


def landing_climb_minimum():
    """FAR-25.121(e) landing climb minimum gradient: 3.2 percent.

    All engines operating, landing configuration, at the go-around
    speed; applies to every transport-category engine count.
    """
    return 3.2


def meets_minimum(gradient_pct, minimum_pct):
    """True when the available gradient percent clears the minimum."""
    return gradient_pct >= minimum_pct
