#!/usr/bin/env python3
"""Gain scheduling logic (paraphrase, standard flight control practice).

Gain scheduling adapts controller gains to the current operating point
of a nonlinear plant by interpolating a schedule table: a list of
breakpoints of a scheduling variable (dynamic pressure in Pa, Mach
number, angle of attack in deg, or altitude in m) paired with the
controller gains tuned at those operating points. Between breakpoints
the gain is interpolated (nearest or linear); spline fitting is covered
as an overview option and is not implemented here. Out-of-range
scheduling values clamp to the end gains by default, or raise ValueError
when out_of_range="error". The scheduling variable is rate limited so
that gain changes cannot excite the plant faster than the actuators can
follow.

Units: scheduling variable in its native unit (Pa for dynamic pressure,
dimensionless for Mach number, deg for angle of attack, m for altitude);
gains in whatever units the controller uses (dimensionless, per rad, per
m/s, and so on). ARP4754A supplies the development-assurance context;
the interpolation math is common knowledge, paraphrase only.
"""


def _normalize_table(table):
    """Validate a schedule table and return [(breakpoint, gain), ...].

    Accepts an iterable of (breakpoint, gain) pairs or a dict mapping
    breakpoint to gain (dicts are sorted by breakpoint). Raises
    ValueError on malformed tables: fewer than two rows, non-numeric
    entries, or breakpoints that are not strictly increasing.
    """
    if isinstance(table, dict):
        pairs = list(table.items())
    else:
        try:
            pairs = list(table)
        except TypeError:
            raise ValueError(
                "table must be an iterable of (breakpoint, gain) pairs or a dict"
            )
    if len(pairs) < 2:
        raise ValueError(
            "schedule table needs at least two breakpoints, got %d" % len(pairs)
        )
    rows = []
    for i, row in enumerate(pairs):
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            raise ValueError(
                "table row %d must be a (breakpoint, gain) pair" % i
            )
        bp, gain = row
        if isinstance(bp, bool) or isinstance(gain, bool):
            raise ValueError(
                "table row %d: breakpoint and gain must be numeric" % i
            )
        try:
            rows.append((float(bp), float(gain)))
        except (TypeError, ValueError):
            raise ValueError(
                "table row %d: breakpoint and gain must be numeric" % i
            )
    if isinstance(table, dict):
        rows.sort(key=lambda r: r[0])
    for i in range(1, len(rows)):
        if rows[i][0] <= rows[i - 1][0]:
            raise ValueError(
                "breakpoints must be strictly increasing; "
                "duplicate or out-of-order at index %d" % i
            )
    return rows


def schedule_gain(table, sched_var_value, method="linear", out_of_range="clamp"):
    """Interpolated gain at sched_var_value from a breakpoint/gain table.

    table: iterable of (breakpoint, gain) pairs or a dict; breakpoints
    must be strictly increasing (dicts are sorted by breakpoint).
    sched_var_value: current value of the scheduling variable in its
    native unit.
    method: "linear" (default) or "nearest". "spline" is recognized as
    an overview option and raises NotImplementedError: use linear or
    nearest for a concrete gain.
    out_of_range: "clamp" (default) holds the end gain outside the
    breakpoint range; "error" raises ValueError on out-of-range input.

    Returns the interpolated gain in the units of the table gains.
    """
    rows = _normalize_table(table)
    if method not in ("nearest", "linear", "spline"):
        raise ValueError(
            "method must be 'nearest', 'linear', or 'spline', got %r"
            % (method,)
        )
    if method == "spline":
        raise NotImplementedError(
            "spline gain scheduling is an overview topic in this skill; "
            "use method='linear' or method='nearest' for a concrete gain"
        )
    if isinstance(sched_var_value, bool):
        raise ValueError("sched_var_value must be numeric")
    try:
        x = float(sched_var_value)
    except (TypeError, ValueError):
        raise ValueError(
            "sched_var_value must be numeric, got %r" % (sched_var_value,)
        )
    if out_of_range not in ("clamp", "error"):
        raise ValueError(
            "out_of_range must be 'clamp' or 'error', got %r" % (out_of_range,)
        )
    bps = [r[0] for r in rows]
    gains = [r[1] for r in rows]
    if x < bps[0] or x > bps[-1]:
        if out_of_range == "error":
            raise ValueError(
                "sched_var_value %.6g outside breakpoint range [%.6g, %.6g]"
                % (x, bps[0], bps[-1])
            )
        x = min(max(x, bps[0]), bps[-1])
    for i, bp in enumerate(bps):
        if x == bp:
            return gains[i]
    lo = max(i for i, bp in enumerate(bps) if bp < x)
    hi = lo + 1
    if method == "nearest":
        if x - bps[lo] <= bps[hi] - x:
            return gains[lo]
        return gains[hi]
    x0, x1 = bps[lo], bps[hi]
    g0, g1 = gains[lo], gains[hi]
    return g0 + (g1 - g0) * (x - x0) / (x1 - x0)


def rate_limited_scheduling_variable(prev_value, new_value, max_rate, dt):
    """Scheduling variable value after a per-step rate limit.

    The commanded value new_value is approached from prev_value at no
    more than max_rate units per second over the step dt (seconds).
    Returns the applied value. max_rate must be >= 0 and dt > 0; a zero
    max_rate freezes the variable at prev_value.
    """
    if isinstance(prev_value, bool) or isinstance(new_value, bool):
        raise ValueError("prev_value and new_value must be numeric")
    try:
        pv = float(prev_value)
        nv = float(new_value)
        mr = float(max_rate)
        dt_f = float(dt)
    except (TypeError, ValueError):
        raise ValueError("prev_value, new_value, max_rate, and dt must be numeric")
    if mr < 0.0:
        raise ValueError("max_rate must be >= 0, got %r" % (max_rate,))
    if dt_f <= 0.0:
        raise ValueError("dt must be > 0, got %r" % (dt,))
    delta = nv - pv
    cap = mr * dt_f
    if delta > cap:
        return pv + cap
    if delta < -cap:
        return pv - cap
    return nv
