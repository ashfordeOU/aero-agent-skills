#!/usr/bin/env python3
"""Engine-out takeoff flight test reduction logic (paraphrase, common
flight-test methodology).

Balanced-field engine-out takeoff model in the FAR 25.107/25.113
certification-test context (standards-map.yaml, far-25 and cs-25:
reference-only): reduce the critical-engine takeoff run to the engine
failure speed VEF, add the V1 recognition-time segment, continue the
takeoff to the 35-ft obstacle at the measured engine-out rate, and set
the decision speed V1 where the stop-distance curve ASD(V1) equals the
continued engine-out takeoff distance curve TOD(V1).

This leaf owns the engine-out takeoff reduction and balanced-field V1
determination; the all-engine accelerate-stop sibling defers that
balanced-field model to this module. Pure stdlib, deterministic.
"""

H_TARGET_M = 10.668  # 35-ft obstacle height, m


def engine_failure_distance(v_samples, t_samples, v_ef_mps):
    """Ground distance from brake release to the engine failure speed, m.

    Trapezoid integration of the measured ground speed samples v(t)
    from the first sample to the interpolated crossing of v_ef. Both
    sample arrays must be non-empty, equal length (>= 2), strictly
    increasing, and non-negative; v_ef must be positive and reachable
    within the sampled speed range. ValueError otherwise.
    """
    if not v_samples or not t_samples:
        raise ValueError("empty speed or time samples")
    if len(v_samples) != len(t_samples):
        raise ValueError("speed and time samples must have equal length")
    if len(v_samples) < 2:
        raise ValueError("at least two samples are required")
    if any(v < 0 for v in v_samples):
        raise ValueError("speed samples must be non-negative")
    if any(t < 0 for t in t_samples):
        raise ValueError("time samples must be non-negative")
    for a, b in zip(v_samples, v_samples[1:]):
        if b <= a:
            raise ValueError("speed samples must be strictly increasing")
    for a, b in zip(t_samples, t_samples[1:]):
        if b <= a:
            raise ValueError("time samples must be strictly increasing")
    if v_ef_mps <= 0:
        raise ValueError("engine failure speed must be > 0, got %r" % (v_ef_mps,))
    if v_ef_mps < v_samples[0]:
        raise ValueError("v_ef lies below the first speed sample")
    if v_ef_mps > v_samples[-1]:
        raise ValueError("v_ef not reached within the sampled speeds")

    dist = 0.0
    for j in range(len(v_samples) - 1):
        if v_samples[j + 1] <= v_ef_mps:
            # Full trapezoid segment before the failure crossing.
            dist += 0.5 * (v_samples[j] + v_samples[j + 1]) * (
                t_samples[j + 1] - t_samples[j]
            )
        else:
            # Crossing inside segment j..j+1: partial trapezoid to v_ef.
            frac = (v_ef_mps - v_samples[j]) / (v_samples[j + 1] - v_samples[j])
            t_cross = t_samples[j] + frac * (t_samples[j + 1] - t_samples[j])
            dist += 0.5 * (v_samples[j] + v_ef_mps) * (t_cross - t_samples[j])
            break
    return dist


def recognition_distance(v1_mps, t_rec_s):
    """Recognition segment distance at the decision speed, m: v1 * t_rec.

    Constant-speed segment at V1 during the recognition interval.
    ValueError on a non-positive decision speed or recognition time.
    """
    if v1_mps <= 0:
        raise ValueError("decision speed must be > 0, got %r" % (v1_mps,))
    if t_rec_s <= 0:
        raise ValueError("recognition time must be > 0, got %r" % (t_rec_s,))
    return v1_mps * t_rec_s


def continued_climb_distance(v2_mps, roc_oei_mps, h_target_m=H_TARGET_M):
    """Continued climb distance to the obstacle, m: v2 * h_target / roc.

    Constant-speed climb at the takeoff safety speed V2 over the
    obstacle height h_target (default 10.668 m, 35 ft) at the measured
    one-engine-inoperative rate of climb. ValueError on a non-positive
    v2, roc or h_target.
    """
    if v2_mps <= 0:
        raise ValueError("takeoff safety speed must be > 0, got %r" % (v2_mps,))
    if roc_oei_mps <= 0:
        raise ValueError("engine-out rate of climb must be > 0, got %r" % (roc_oei_mps,))
    if h_target_m <= 0:
        raise ValueError("obstacle height must be > 0, got %r" % (h_target_m,))
    return v2_mps * h_target_m / roc_oei_mps


def engine_out_takeoff_distance(
    failure_dist_m,
    v1_mps,
    v2_mps,
    t_rec_s,
    a_cont_mps2,
    roc_oei_mps,
    h_target_m=H_TARGET_M,
):
    """Chained continued engine-out takeoff distance from the legs, m.

    Exact chaining used here: failure leg (measured ground run to VEF,
    engine_failure_distance) + recognition segment v1 * t_rec +
    continued ground segment accelerating from V1 to V2 at a_cont,
    (v2^2 - v1^2) / (2 * a_cont) + continued climb at V2 to the
    obstacle, v2 * h_target / roc. V1 must not exceed V2.

    Returns {'failure_m', 'recognition_m', 'ground_continue_m',
    'climb_m', 'total_m'} with total_m the chained sum. ValueError on
    any non-positive or non-physical input.
    """
    if failure_dist_m < 0:
        raise ValueError("failure distance must be >= 0, got %r" % (failure_dist_m,))
    if v2_mps <= 0:
        raise ValueError("takeoff safety speed must be > 0, got %r" % (v2_mps,))
    if v2_mps < v1_mps:
        raise ValueError("v2 must be at or above the decision speed v1")
    if a_cont_mps2 <= 0:
        raise ValueError(
            "continued acceleration must be > 0, got %r" % (a_cont_mps2,)
        )
    s_rec = recognition_distance(v1_mps, t_rec_s)
    s_ground = (v2_mps ** 2 - v1_mps ** 2) / (2.0 * a_cont_mps2)
    s_climb = continued_climb_distance(v2_mps, roc_oei_mps, h_target_m)
    total = failure_dist_m + s_rec + s_ground + s_climb
    return {
        "failure_m": failure_dist_m,
        "recognition_m": s_rec,
        "ground_continue_m": s_ground,
        "climb_m": s_climb,
        "total_m": total,
    }


def _interp_polyline(xs, ys, v):
    """Piecewise-linear interpolation of (xs, ys) at speed v."""
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= v:
            lo = mid
        else:
            hi = mid
    frac = (v - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + frac * (ys[hi] - ys[lo])


def _validate_curve(speeds, dists, name):
    if not speeds or not dists:
        raise ValueError("%s curve arrays are empty" % name)
    if len(speeds) != len(dists):
        raise ValueError("%s speed and distance arrays differ in length" % name)
    if len(speeds) < 2:
        raise ValueError("%s curve needs at least two points" % name)
    for a, b in zip(speeds, speeds[1:]):
        if b <= a:
            raise ValueError("%s speeds must be strictly increasing" % name)
    if any(d < 0 for d in dists):
        raise ValueError("%s distances must be non-negative" % name)


def balanced_field_v1(asd_speeds, asd_dists, tod_speeds, tod_dists):
    """Balanced-field decision speed from the ASD and engine-out TOD
    curves, (v1_mps, dist_m), or (None, regime) when no crossing.

    Segment-linear intersection of the stop-distance curve ASD(V1) and
    the continued engine-out takeoff distance curve TOD(V1) over their
    common speed range; the lowest-speed crossing is the balanced
    point. When the curves do not cross inside the shared range the
    regime flag is returned with v1 None: 'asd-limited' when the
    engine-out TOD curve lies everywhere at or above the ASD curve
    (the balance lies above the tested speeds), 'tod-limited' in the
    reverse case. ValueError on empty, mismatched, non-monotone speed
    or descending-ASD inputs.
    """
    _validate_curve(asd_speeds, asd_dists, "asd")
    _validate_curve(tod_speeds, tod_dists, "tod")
    for a, b in zip(asd_dists, asd_dists[1:]):
        if b < a:
            raise ValueError("asd distances must be non-decreasing in speed")

    lo = max(asd_speeds[0], tod_speeds[0])
    hi = min(asd_speeds[-1], tod_speeds[-1])
    if lo > hi:
        raise ValueError("asd and tod curves share no common speed range")
    if lo == hi:
        raise ValueError("asd and tod curves overlap only at a single speed")

    nodes = sorted({s for s in asd_speeds + tod_speeds if lo <= s <= hi})

    def diff(v):
        return _interp_polyline(asd_speeds, asd_dists, v) - _interp_polyline(
            tod_speeds, tod_dists, v
        )

    for a, b in zip(nodes, nodes[1:]):
        d_a, d_b = diff(a), diff(b)
        if d_a == 0.0:
            return a, _interp_polyline(asd_speeds, asd_dists, a)
        if d_b == 0.0:
            return b, _interp_polyline(asd_speeds, asd_dists, b)
        if (d_a < 0.0) != (d_b < 0.0):
            frac = d_a / (d_a - d_b)
            v1 = a + frac * (b - a)
            return v1, _interp_polyline(asd_speeds, asd_dists, v1)

    vals = [diff(n) for n in nodes]
    if max(vals) <= 0.0:
        return None, "asd-limited"
    if min(vals) >= 0.0:
        return None, "tod-limited"
    raise ValueError("unable to resolve asd/tod crossing regime")


def v1_ordering_verdict(v1_mps, v_ef_mps, t_rec_s, a_cont_mps2, v_r_mps):
    """Ordering checks on the decision speed V1, as a dict.

    Verifies V1 >= VEF + a_cont * t_rec (the failure-plus-recognition
    speed, v1_min) and V1 <= V_R (rotation speed). Returns
    {'v1_min_mps', 'v1_ge_v1_min', 'v1_min_margin_mps', 'v1_le_vr',
    'v_r_margin_mps', 'ordering_pass'}. ValueError on non-positive or
    negative inputs.
    """
    if v1_mps <= 0:
        raise ValueError("decision speed must be > 0, got %r" % (v1_mps,))
    if v_ef_mps <= 0:
        raise ValueError("engine failure speed must be > 0, got %r" % (v_ef_mps,))
    if t_rec_s <= 0:
        raise ValueError("recognition time must be > 0, got %r" % (t_rec_s,))
    if a_cont_mps2 < 0:
        raise ValueError(
            "continued acceleration must be >= 0, got %r" % (a_cont_mps2,)
        )
    if v_r_mps <= 0:
        raise ValueError("rotation speed must be > 0, got %r" % (v_r_mps,))
    v1_min = v_ef_mps + a_cont_mps2 * t_rec_s
    return {
        "v1_min_mps": v1_min,
        "v1_ge_v1_min": v1_mps >= v1_min,
        "v1_min_margin_mps": v1_mps - v1_min,
        "v1_le_vr": v1_mps <= v_r_mps,
        "v_r_margin_mps": v_r_mps - v1_mps,
        "ordering_pass": v1_mps >= v1_min and v1_mps <= v_r_mps,
    }


def field_length_verdict(runway_m, dist_m):
    """Runway fit verdict for the balanced distance, as a dict.

    Returns {'margin_m': runway_m - dist_m, 'fits': margin >= 0}. A
    negative margin is a real, reportable outcome (too short), not an
    error. ValueError on a non-positive runway or negative distance.
    """
    if runway_m <= 0:
        raise ValueError("runway length must be > 0, got %r" % (runway_m,))
    if dist_m < 0:
        raise ValueError("distance must be >= 0, got %r" % (dist_m,))
    margin = runway_m - dist_m
    return {"margin_m": margin, "fits": margin >= 0.0}


def engine_failure_takeoff_summary(
    asd_speeds,
    asd_dists,
    tod_speeds,
    tod_dists,
    v_ef_mps,
    t_rec_s,
    a_cont_mps2,
    v_r_mps,
    runway_m,
):
    """Full engine-out takeoff reduction summary, as a dict.

    Reduces the balanced-field problem from the ASD and engine-out TOD
    curve data: regime ('balanced', 'asd-limited', 'tod-limited'),
    balanced_field_v1_mps, balanced_field_distance_m (the continued
    engine-out takeoff distance at the balanced speed; the TOD curve
    values already embed the failure, recognition and continued legs),
    v1_min_mps = VEF + a_cont * t_rec, recognition_distance_m at the
    balanced V1, the ordering_verdict dict and the field_verdict dict.

    When no crossing exists regime carries the flag and the balanced
    speed, distance, recognition distance, ordering and field entries
    are None. Top-level keys are exactly: regime,
    balanced_field_v1_mps, balanced_field_distance_m, v1_min_mps,
    recognition_distance_m, ordering_verdict, field_verdict. ValueError
    on non-physical inputs.
    """
    if v_ef_mps <= 0:
        raise ValueError("engine failure speed must be > 0, got %r" % (v_ef_mps,))
    if t_rec_s <= 0:
        raise ValueError("recognition time must be > 0, got %r" % (t_rec_s,))
    if a_cont_mps2 < 0:
        raise ValueError(
            "continued acceleration must be >= 0, got %r" % (a_cont_mps2,)
        )
    if v_r_mps <= 0:
        raise ValueError("rotation speed must be > 0, got %r" % (v_r_mps,))
    if runway_m <= 0:
        raise ValueError("runway length must be > 0, got %r" % (runway_m,))

    v1, bal = balanced_field_v1(asd_speeds, asd_dists, tod_speeds, tod_dists)
    result = {
        "regime": "balanced" if v1 is not None else bal,
        "balanced_field_v1_mps": v1,
        "balanced_field_distance_m": bal if v1 is not None else None,
        "v1_min_mps": v_ef_mps + a_cont_mps2 * t_rec_s,
        "recognition_distance_m": None,
        "ordering_verdict": None,
        "field_verdict": None,
    }
    if v1 is not None:
        result["recognition_distance_m"] = recognition_distance(v1, t_rec_s)
        result["ordering_verdict"] = v1_ordering_verdict(
            v1, v_ef_mps, t_rec_s, a_cont_mps2, v_r_mps
        )
        result["field_verdict"] = field_length_verdict(runway_m, bal)
    return result
