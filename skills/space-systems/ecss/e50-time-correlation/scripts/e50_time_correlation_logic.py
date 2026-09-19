"""Onboard-to-reference time correlation for a space communication system.

Anchor: ECSS-E-ST-50C clause 5.6.14.6 -- time correlation.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that the system correlates onboard time with the
reference time scale to a stated accuracy. Stating an accuracy is the part that
turns the obligation into arithmetic: a correlation is not a single number but
a fit with a validity horizon, and the horizon is what tells an operator when
the correlation has to be taken again.

The model is an ordinary least-squares fit of the offset between the two scales
against onboard time, which yields three things a mission can act on:

  offset      -- where the onboard scale sits against the reference at epoch;
  drift       -- the rate at which that offset is opening, in seconds per
                 second, which is the onboard oscillator's frequency error;
  horizon     -- how long the fit stays inside the stated accuracy once the
                 uncertainty in the drift is allowed to accumulate.

Propagation delay is handled first and separately. A correlation pair whose
reference timestamp was taken when the packet reached the ground is biased by
exactly the one-way light time, and no amount of fitting removes a bias that
every pair shares.
"""

import math

__all__ = [
    "CORRELATED",
    "ACCURACY_EXCEEDED",
    "UNDERDETERMINED",
    "validate_pairs",
    "validate_accuracy",
    "correct_for_light_time",
    "fit_correlation",
    "residuals",
    "residual_rms",
    "drift_uncertainty",
    "predict_reference",
    "prediction_error_s",
    "validity_horizon_s",
    "assess_time_correlation",
]

CORRELATED = "correlated"
ACCURACY_EXCEEDED = "accuracy-exceeded"
UNDERDETERMINED = "underdetermined"


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_pairs(pairs, name="pairs"):
    """Return at least two correlation pairs with strictly increasing onboard time."""
    if isinstance(pairs, (str, bytes)) or not isinstance(pairs, (list, tuple)):
        raise ValueError("%s must be a list or tuple of (onboard, reference) pairs" % name)
    if len(pairs) < 2:
        raise ValueError("%s needs at least two pairs to define a correlation" % name)
    checked = []
    for index, pair in enumerate(pairs):
        if isinstance(pair, (str, bytes)) or not isinstance(pair, (list, tuple)):
            raise ValueError("%s[%d] must be an (onboard, reference) pair" % (name, index))
        if len(pair) != 2:
            raise ValueError("%s[%d] must hold exactly two times" % (name, index))
        onboard = _validate_number(pair[0], "%s[%d].onboard" % (name, index))
        reference = _validate_number(pair[1], "%s[%d].reference" % (name, index))
        checked.append((onboard, reference))
    for index in range(1, len(checked)):
        if checked[index][0] <= checked[index - 1][0]:
            raise ValueError(
                "%s must strictly increase in onboard time; pair %d does not "
                "follow pair %d" % (name, index, index - 1)
            )
    return checked


def validate_accuracy(value, name="accuracy_bound_s"):
    """Return a strictly positive accuracy bound in seconds."""
    bound = _validate_number(value, name)
    if bound <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return bound


def correct_for_light_time(pairs, one_way_light_time_s):
    """Return pairs with the propagation delay removed from the reference time.

    A reference timestamp taken when the packet arrived on the ground is later
    than the instant the onboard clock actually read, by exactly the one-way
    light time. The correction is a bias every pair carries, so a fit over
    uncorrected pairs is wrong by the same amount at every point.
    """
    checked = validate_pairs(pairs)
    delay = _validate_number(one_way_light_time_s, "one_way_light_time_s")
    if delay < 0.0:
        raise ValueError("one_way_light_time_s must not be negative, got %r" % (one_way_light_time_s,))
    return [(onboard, reference - delay) for onboard, reference in checked]


def fit_correlation(pairs):
    """Return the least-squares offset and drift of reference against onboard time."""
    checked = validate_pairs(pairs)
    epoch = checked[0][0]
    xs = [onboard - epoch for onboard, _ in checked]
    ys = [reference - onboard for onboard, reference in checked]
    count = float(len(checked))
    xbar = sum(xs) / count
    ybar = sum(ys) / count
    sxx = sum((x - xbar) * (x - xbar) for x in xs)
    if sxx <= 0.0:
        raise ValueError("pairs must span more than one onboard instant")
    sxy = sum((xs[i] - xbar) * (ys[i] - ybar) for i in range(len(xs)))
    drift = sxy / sxx
    offset = ybar - drift * xbar
    return {
        "epoch_s": epoch,
        "offset_s": offset,
        "drift_s_per_s": drift,
        "span_s": xs[-1],
        "pair_count": len(checked),
        "sxx": sxx,
    }


def residuals(pairs, fit):
    """Return how far each pair sits from the fitted correlation, in seconds."""
    checked = validate_pairs(pairs)
    epoch = fit["epoch_s"]
    offset = fit["offset_s"]
    drift = fit["drift_s_per_s"]
    out = []
    for onboard, reference in checked:
        modelled = onboard + offset + drift * (onboard - epoch)
        out.append(reference - modelled)
    return out


def residual_rms(values):
    """Return the root-mean-square of a set of residuals."""
    if not values:
        raise ValueError("values must not be empty")
    total = sum(value * value for value in values)
    return math.sqrt(total / float(len(values)))


def drift_uncertainty(pairs, fit):
    """Return the standard error of the fitted drift, in seconds per second.

    None means the fit has no redundancy: two pairs determine a straight line
    exactly, so their residuals are zero by construction and say nothing about
    how well the drift is known.
    """
    checked = validate_pairs(pairs)
    count = len(checked)
    if count < 3:
        return None
    errors = residuals(checked, fit)
    total = sum(value * value for value in errors)
    variance = total / float(count - 2)
    return math.sqrt(variance) / math.sqrt(fit["sxx"])


def predict_reference(fit, onboard_time_s):
    """Return the reference time the fit places this onboard reading at."""
    onboard = _validate_number(onboard_time_s, "onboard_time_s")
    return onboard + fit["offset_s"] + fit["drift_s_per_s"] * (onboard - fit["epoch_s"])


def prediction_error_s(rms, drift_error, elapsed_s):
    """Return the correlation error expected this long after the last pair.

    None means it cannot be stated, because the drift uncertainty could not be
    estimated from the pairs given.
    """
    noise = _validate_number(rms, "rms")
    if noise < 0.0:
        raise ValueError("rms must not be negative, got %r" % (rms,))
    elapsed = _validate_number(elapsed_s, "elapsed_s")
    if elapsed < 0.0:
        raise ValueError("elapsed_s must not be negative, got %r" % (elapsed_s,))
    if drift_error is None:
        return None
    slope_error = _validate_number(drift_error, "drift_error")
    return noise + abs(slope_error) * elapsed


def validity_horizon_s(accuracy_bound_s, rms, drift_error):
    """Return how long the correlation stays inside the stated accuracy.

    None means undetermined -- the drift uncertainty could not be estimated.
    Infinity means the fit does not decay: the drift is known exactly as far as
    these pairs can tell, so only the residual noise stands against the bound.
    Zero means the fit is already outside the bound before any time passes.
    """
    bound = validate_accuracy(accuracy_bound_s)
    noise = _validate_number(rms, "rms")
    if noise < 0.0:
        raise ValueError("rms must not be negative, got %r" % (rms,))
    if drift_error is None:
        return None
    slope_error = abs(_validate_number(drift_error, "drift_error"))
    if noise >= bound:
        return 0.0
    if slope_error == 0.0:
        return float("inf")
    return (bound - noise) / slope_error


def assess_time_correlation(
    pairs, accuracy_bound_s, one_way_light_time_s=0.0, elapsed_since_last_s=0.0
):
    """Grade one correlation pair set against a stated accuracy."""
    bound = validate_accuracy(accuracy_bound_s)
    corrected = correct_for_light_time(pairs, one_way_light_time_s)
    delay = _validate_number(one_way_light_time_s, "one_way_light_time_s")
    fit = fit_correlation(corrected)
    errors = residuals(corrected, fit)
    rms = residual_rms(errors)
    slope_error = drift_uncertainty(corrected, fit)
    horizon = validity_horizon_s(bound, rms, slope_error)
    elapsed = _validate_number(elapsed_since_last_s, "elapsed_since_last_s")
    if elapsed < 0.0:
        raise ValueError("elapsed_since_last_s must not be negative, got %r" % (elapsed_since_last_s,))
    expected = prediction_error_s(rms, slope_error, elapsed)
    findings = []
    if slope_error is None:
        verdict = UNDERDETERMINED
        findings.append(
            "two pairs fit a straight line exactly, so the residuals are zero by "
            "construction and the drift uncertainty cannot be estimated"
        )
        findings.append(
            "a third pair separated in onboard time is the smallest set that can "
            "state a validity horizon"
        )
    elif rms >= bound:
        verdict = ACCURACY_EXCEEDED
        findings.append(
            "residual spread %.9g s already meets or exceeds the %.9g s accuracy "
            "bound, so the correlation is outside it before any time passes"
            % (rms, bound)
        )
        findings.append(
            "either the bound is wrong or the pairs are: widen the bound to more "
            "than %.9g s, or take pairs with less dispersion" % (rms,)
        )
    else:
        verdict = CORRELATED
    if delay > bound:
        findings.append(
            "a one-way light time of %.9g s was removed; left uncorrected it "
            "would have biased every pair by more than the %.9g s bound"
            % (delay, bound)
        )
    return {
        "pair_count": fit["pair_count"],
        "epoch_s": fit["epoch_s"],
        "offset_s": fit["offset_s"],
        "drift_s_per_s": fit["drift_s_per_s"],
        "span_s": fit["span_s"],
        "residuals_s": errors,
        "residual_rms_s": rms,
        "drift_uncertainty_s_per_s": slope_error,
        "accuracy_bound_s": bound,
        "light_time_applied_s": delay,
        "validity_horizon_s": horizon,
        "recorrelation_interval_s": horizon,
        "expected_error_s": expected,
        "within_accuracy": verdict == CORRELATED,
        "verdict": verdict,
        "findings": findings,
    }
