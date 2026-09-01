#!/usr/bin/env python3
"""Acoustic emission inspection logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml: as9100 and nas-410
reference-only): acoustic emission testing listens passively for
elastic waves released by sudden localized deformation. Aerospace
sources include crack growth, fiber breakage, delamination, matrix
cracking, and fretting. Resonant piezoelectric sensors (100-500 kHz
typical bands) record hits when a channel crosses an amplitude
threshold; hits are grouped into events with the hit definition time
(HDT) window. Source location is linear (two sensors on a line) or
planar (three or more sensors, hyperbolic time-difference system
solved by iterative least squares). On reload, the Kaiser effect
predicts silence until the previous maximum load is exceeded; the
Felicity ratio (resume load / previous maximum load) below 1 signals
the Felicity effect and progressing damage. No proprietary procedure
text is reproduced here.
"""

import math


def hit_threshold_check(amplitudes_db, threshold_db):
    """Filter recorded signal amplitudes against a dB threshold.

    amplitudes_db: list of signal amplitudes in dB; threshold_db: the
    fixed amplitude threshold. Returns a dict with the threshold, the
    list of hits (amplitudes at or above the threshold), the hit
    count, and the total number of signals. A zero threshold keeps
    every non-negative amplitude; a negative threshold raises
    ValueError.
    """
    if threshold_db < 0.0:
        raise ValueError("threshold_db must be non-negative: %r" % (threshold_db,))
    hits = [a for a in amplitudes_db if a >= threshold_db]
    return {
        "threshold_db": threshold_db,
        "hits": hits,
        "hit_count": len(hits),
        "total_signals": len(amplitudes_db),
    }


def signal_energy(amplitudes, dt):
    """Energy proxy for a signal: dt * sum of squared amplitudes.

    Deterministic MARSE-style stand-in for the measured area under the
    rectified signal envelope. dt must be positive.
    """
    if dt <= 0.0:
        raise ValueError("dt must be positive: %r" % (dt,))
    return dt * sum(a * a for a in amplitudes)


def group_hits_to_events(arrival_times, hdt):
    """Group hit arrival times into events with the HDT window.

    Consecutive hits separated by more than hdt start a new event;
    hits within hdt of the previous hit join the current event.
    Returns a list of event lists (chronological). Empty input returns
    an empty list; a non-positive hdt raises ValueError.
    """
    if hdt <= 0.0:
        raise ValueError("hdt must be positive: %r" % (hdt,))
    if not arrival_times:
        return []
    ordered = sorted(arrival_times)
    events = [[ordered[0]]]
    for t in ordered[1:]:
        if t - events[-1][-1] > hdt:
            events.append([t])
        else:
            events[-1].append(t)
    return events


def source_location_linear(sensor_distance, arrival_times, wave_speed):
    """Position of an AE source on a line between two sensors.

    Sensors sit at x = 0 and x = sensor_distance; arrival_times is
    [t1, t2] for the near and far sensor. From v*t1 = x and
    v*t2 = D - x the position is x = (D + v*(t1 - t2)) / 2. Raises
    ValueError when the arrival-time difference is impossible for a
    source between the sensors (v*|t1 - t2| exceeds the gauge
    distance), when the gauge distance or wave speed is not positive,
    or when the times are not a two-element list of non-negative
    values.
    """
    if sensor_distance <= 0.0:
        raise ValueError("sensor_distance must be positive: %r" % (sensor_distance,))
    if wave_speed <= 0.0:
        raise ValueError("wave_speed must be positive: %r" % (wave_speed,))
    if len(arrival_times) != 2:
        raise ValueError("linear location needs exactly 2 arrival times")
    t1, t2 = arrival_times
    if t1 < 0.0 or t2 < 0.0:
        raise ValueError("arrival times must be non-negative")
    delta = t2 - t1
    if wave_speed * abs(delta) > sensor_distance:
        raise ValueError("impossible arrival times: source outside the sensor span")
    return (sensor_distance + wave_speed * (t1 - t2)) / 2.0


def source_location_planar(sensors, arrival_times, wave_speed,
                           max_iter=60, tol=1e-12, residual_tol=1e-6,
                           margin_ratio=0.5):
    """Planar AE source location by iterative least-squares triangulation.

    sensors: list of (x, y) positions with the reference sensor first;
    arrival_times: matching list. Each pair (i, 0) gives the
    hyperbolic constraint d_i - d_0 = v*(t_i - t_0). The system is
    linearized around the current guess and solved as a 2x2 normal
    system (Cramer), iterating from the sensor centroid to convergence
    (deterministic, stdlib only).

    Raises ValueError for fewer than 3 sensors, mismatched lengths,
    non-positive wave speed, negative times, a triangle-inequality
    violation (|v*(t_i - t_0)| exceeds the sensor spacing, i.e.
    impossible arrival times), non-convergence, a degenerate
    (collinear) array, an inconsistent time set (residual above
    residual_tol), or a solution outside the array bounds (margin is
    margin_ratio times the array's largest dimension, i.e. an
    out-of-grid location that planar location cannot estimate
    reliably).
    """
    if wave_speed <= 0.0:
        raise ValueError("wave_speed must be positive: %r" % (wave_speed,))
    n = len(sensors)
    if n < 3:
        raise ValueError("planar location needs at least 3 sensors, got %d" % n)
    if len(arrival_times) != n:
        raise ValueError("arrival_times must match sensors one-to-one")
    for s in sensors:
        if len(s) != 2:
            raise ValueError("each sensor must be an (x, y) pair")
    if any(t < 0.0 for t in arrival_times):
        raise ValueError("arrival times must be non-negative")

    xs = [s[0] for s in sensors]
    ys = [s[1] for s in sensors]
    x0, y0 = xs[0], ys[0]

    # Triangle inequality: |d_i - d_0| <= dist(s_i, s_0) always.
    for i in range(1, n):
        delta_i = wave_speed * (arrival_times[i] - arrival_times[0])
        spacing = math.hypot(xs[i] - x0, ys[i] - y0)
        if abs(delta_i) > spacing * (1.0 + 1e-12):
            raise ValueError("impossible arrival times: TDOA exceeds sensor spacing")

    x = sum(xs) / n
    y = sum(ys) / n
    iterations = 0
    for iterations in range(1, max_iter + 1):
        d0 = math.hypot(x - x0, y - y0)
        s_aa = s_ab = s_bb = s_ac = s_bc = 0.0
        for i in range(1, n):
            delta_i = wave_speed * (arrival_times[i] - arrival_times[0])
            a_i = -2.0 * (xs[i] - x0)
            b_i = -2.0 * (ys[i] - y0)
            c_i = 2.0 * d0 * delta_i + delta_i * delta_i - (
                xs[i] * xs[i] + ys[i] * ys[i] - x0 * x0 - y0 * y0
            )
            s_aa += a_i * a_i
            s_ab += a_i * b_i
            s_bb += b_i * b_i
            s_ac += a_i * c_i
            s_bc += b_i * c_i
        det = s_aa * s_bb - s_ab * s_ab
        if det == 0.0:
            raise ValueError("degenerate sensor geometry (collinear array)")
        x_new = (s_ac * s_bb - s_bc * s_ab) / det
        y_new = (s_aa * s_bc - s_ab * s_ac) / det
        if max(abs(x_new - x), abs(y_new - y)) < tol:
            x, y = x_new, y_new
            break
        x, y = x_new, y_new
    else:
        raise ValueError("planar location did not converge")

    # Residual check: a consistent time set leaves near-zero residuals.
    residual = 0.0
    for i in range(1, n):
        d_i = math.hypot(x - xs[i], y - ys[i])
        d_0 = math.hypot(x - x0, y - y0)
        expected = wave_speed * (arrival_times[i] - arrival_times[0])
        residual = max(residual, abs((d_i - d_0) - expected))
    if residual > residual_tol:
        raise ValueError("inconsistent arrival times (residual %.3g m)" % residual)

    # Array-bounds guard: sources far outside the array are unreliable.
    max_dim = max(max(xs) - min(xs), max(ys) - min(ys))
    margin = margin_ratio * max_dim
    if (x < min(xs) - margin or x > max(xs) + margin
            or y < min(ys) - margin or y > max(ys) + margin):
        raise ValueError("source location outside sensor array bounds")

    return {"x": x, "y": y, "iterations": iterations, "residual": residual}


def felicity_ratio(resume_load, previous_max_load):
    """Felicity ratio: load at which emission resumes / previous max.

    A ratio at or above 1 means the Kaiser effect holds; below 1 the
    Felicity effect is present. previous_max_load must be positive and
    resume_load non-negative; otherwise ValueError.
    """
    if previous_max_load <= 0.0:
        raise ValueError("previous_max_load must be positive: %r" % (previous_max_load,))
    if resume_load < 0.0:
        raise ValueError("resume_load must be non-negative: %r" % (resume_load,))
    return resume_load / previous_max_load


def kaiser_effect_check(resume_load, previous_max_load, felicity_threshold=0.95):
    """Kaiser effect and Felicity ratio verdict for a reload cycle.

    Returns a dict with the felicity ratio, whether the Kaiser effect
    holds (ratio >= 1), whether the Felicity effect is present
    (ratio < 1), whether damage is indicated (ratio below the
    felicity_threshold, 0.95 by default for composites), and the
    threshold used. felicity_threshold must be in (0, 1].
    """
    if not (0.0 < felicity_threshold <= 1.0):
        raise ValueError(
            "felicity_threshold must be in (0, 1]: %r" % (felicity_threshold,)
        )
    ratio = felicity_ratio(resume_load, previous_max_load)
    return {
        "felicity_ratio": ratio,
        "kaiser_effect_holds": ratio >= 1.0,
        "felicity_effect": ratio < 1.0,
        "damage_indicated": ratio < felicity_threshold,
        "felicity_threshold": felicity_threshold,
    }
