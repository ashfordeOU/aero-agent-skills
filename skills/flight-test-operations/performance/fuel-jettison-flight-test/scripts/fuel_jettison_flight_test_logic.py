"""Fuel jettison flight test logic (pure stdlib, deterministic).

Reduction helpers for a FAR 25.1001 fuel jettison demonstration flight
test (name and requirement frame only, no verbatim rule text): fit the
telemetered fuel-weight-vs-time samples taken while the dump runs with a
closed-form least-squares straight line, read the measured average dump
rate from the fitted slope, extrapolate the time the aircraft needs to
come down from the takeoff weight to the landing weight at that measured
rate, judge the PASS or FAIL verdict against the 900 s limit, and check
the measured rate against the required rate q_req that the design side
sets from MTOW and MLW over the same limit. Scatter in the samples is
handled by the fit's R^2, not by a stochastic model.
"""

# 15-minute limit of FAR 25.1001 for a fuel jettison demonstration,
# paraphrased frame only (no rule text reproduced).
JETTISON_LIMIT_S = 900.0

# Fewest telemetered samples that admit a least-squares line fit.
MIN_SAMPLES = 2


def lsq_fit(weights, times):
    """Least-squares straight-line fit of fuel weight W(t) over the dump
    window. Returns {"slope", "intercept", "r_squared"} with slope in
    kg/s (negative while fuel is dumped) and intercept in kg.

    Closed forms: slope = (n * sum(t*w) - sum(t) * sum(w)) /
    (n * sum(t^2) - (sum(t))^2), intercept = mean(w) - slope * mean(t),
    r_squared = 1 - ss_res / ss_tot with ss_res the residual sum of
    squares and ss_tot = sum((w - mean(w))^2); r_squared is 1.0 when
    ss_tot is 0 (all weights equal).
    """
    if len(weights) != len(times):
        raise ValueError("weights and times must have equal length")
    if len(weights) < MIN_SAMPLES:
        raise ValueError("at least %d samples are required" % MIN_SAMPLES)
    for i in range(1, len(times)):
        if times[i] <= times[i - 1]:
            raise ValueError("times must be strictly increasing")
    n = float(len(weights))
    sum_t = float(sum(times))
    sum_w = float(sum(weights))
    sum_tt = float(sum(t * t for t in times))
    sum_tw = float(sum(t * w for t, w in zip(times, weights)))
    denom = n * sum_tt - sum_t * sum_t
    if denom == 0.0:
        raise ValueError("zero fit denominator (duplicate time values)")
    slope = (n * sum_tw - sum_t * sum_w) / denom
    intercept = sum_w / n - slope * (sum_t / n)
    ss_tot = sum((w - sum_w / n) ** 2 for w in weights)
    if ss_tot == 0.0:
        r_squared = 1.0
    else:
        ss_res = sum(
            (w - (intercept + slope * t)) ** 2
            for t, w in zip(times, weights)
        )
        r_squared = 1.0 - ss_res / ss_tot
    return {"slope": slope, "intercept": intercept, "r_squared": r_squared}


def measured_rate(weights, times):
    """Measured average dump rate in kg/s, taken as -lsq_fit slope so the
    rate is positive for a dump. A non-negative fitted slope means no
    dump is observable in the window and raises ValueError.
    """
    fit = lsq_fit(weights, times)
    if fit["slope"] >= 0.0:
        raise ValueError(
            "no dump observable: fitted slope is non-negative"
        )
    return -fit["slope"]


def time_to_landing_weight(w_start, w_landing, rate):
    """Extrapolated time in seconds to come down from the takeoff weight
    w_start (the weight at dump start) to the landing weight target
    w_landing at the measured rate: (w_start - w_landing) / rate.
    """
    if w_start <= 0.0:
        raise ValueError("w_start must be positive")
    if w_landing <= 0.0:
        raise ValueError("w_landing must be positive")
    if w_start <= w_landing:
        raise ValueError("w_start must exceed w_landing (nothing to jettison)")
    if rate <= 0.0:
        raise ValueError("rate must be positive")
    return (w_start - w_landing) / rate


def verdict(time_s, limit=JETTISON_LIMIT_S):
    """PASS or FAIL verdict against the jettison time limit. PASS when
    time_s <= limit (inclusive at the boundary), else FAIL. Returns
    {"verdict", "limit_s", "margin_s"} with margin_s = limit - time_s,
    positive for PASS and negative for FAIL.
    """
    if time_s <= 0.0:
        raise ValueError("time_s must be positive")
    if limit <= 0.0:
        raise ValueError("limit must be positive")
    margin_s = limit - time_s
    return {
        "verdict": "PASS" if margin_s >= 0.0 else "FAIL",
        "limit_s": float(limit),
        "margin_s": margin_s,
    }


def rate_meets_requirement(measured, required):
    """Check of the measured dump rate against the required rate q_req
    set by the design side. Returns {"meets", "margin_kg_s"} with meets
    True when measured >= required (inclusive) and margin_kg_s =
    measured - required.
    """
    if measured <= 0.0:
        raise ValueError("measured rate must be positive")
    if required <= 0.0:
        raise ValueError("required rate must be positive")
    margin_kg_s = measured - required
    return {"meets": margin_kg_s >= 0.0, "margin_kg_s": margin_kg_s}


def reduce_dump_demonstration(
    weights, times, w_start, w_landing, required_rate, limit=JETTISON_LIMIT_S
):
    """One-call summary of the fuel jettison demonstration reduction,
    chaining measured_rate, time_to_landing_weight, verdict and
    rate_meets_requirement in that order. Returns exactly the keys
    measured_rate_kg_s, r_squared, time_to_landing_weight_s, verdict,
    limit_s, margin_s, meets_required_rate, required_rate_kg_s and
    rate_margin_kg_s.
    """
    rate = measured_rate(weights, times)
    r_squared = lsq_fit(weights, times)["r_squared"]
    time_to_landing = time_to_landing_weight(w_start, w_landing, rate)
    v = verdict(time_to_landing, limit)
    rq = rate_meets_requirement(rate, required_rate)
    return {
        "measured_rate_kg_s": rate,
        "r_squared": r_squared,
        "time_to_landing_weight_s": time_to_landing,
        "verdict": v["verdict"],
        "limit_s": v["limit_s"],
        "margin_s": v["margin_s"],
        "meets_required_rate": rq["meets"],
        "required_rate_kg_s": float(required_rate),
        "rate_margin_kg_s": rq["margin_kg_s"],
    }


# Module-level sanity import guard: importing this module never runs
# math, it only binds the functions above.
__all__ = [
    "lsq_fit",
    "measured_rate",
    "time_to_landing_weight",
    "verdict",
    "rate_meets_requirement",
    "reduce_dump_demonstration",
    "JETTISON_LIMIT_S",
    "MIN_SAMPLES",
]
