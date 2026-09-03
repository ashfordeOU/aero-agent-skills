"""In-service safety assessment logic (pure stdlib, deterministic).

Implements the ARP5150A/ARP5151 style continued-airworthiness review of
field event data against the type-design safety assessment predictions
(ARP4761A process context). Consumes SSA predicted rates as inputs and
decides whether field experience requires corrective action. See the
companion SKILL.md for the engineering narrative.

All functions raise ValueError on non-physical inputs. No randomness, no
network, no third party imports.
"""

import math

# A single event at this severity is significant regardless of rate
# (single-event rule for hazardous or catastrophic events).
SINGLE_EVENT_SEVERITIES = frozenset({"hazardous", "catastrophic"})

# Exposure is adequate to judge a predicted rate when the expected event
# count (predicted_rate * exposure) is at least this value.
EXPOSURE_ADEQUACY_EXPECTED_EVENTS = 5.0

# One-sided Poisson exceedance significance threshold.
SIGNIFICANCE_ALPHA = 0.05

# Observed rate must be at least this multiple of the predicted rate to
# be significant on its own.
RATE_EXCEEDANCE_MIN = 2.0

# Poisson tail ceiling: stop when k exceeds expected * CEILING_MULT + 50
# or the added term falls below TERM_FLOOR.
CEILING_MULT = 20.0
TERM_FLOOR = 1e-12

# Recognized severity strings in increasing order.
SEVERITY_ORDER = ("none", "minor", "major", "hazardous", "catastrophic")
SEVERITY_RANK = {sev: i for i, sev in enumerate(SEVERITY_ORDER)}

VALID_EXPOSURE_UNITS = ("fh", "fc")


def _check_severity(severity):
    """Raise ValueError when severity is not a recognized string."""
    if severity not in SEVERITY_RANK:
        raise ValueError(
            "unknown severity %r; expected one of %s"
            % (severity, ", ".join(SEVERITY_ORDER))
        )
    return severity


def exposure_summary(exposure_hours, fleet_size):
    """Return the total exposure and the average per aircraft.

    exposure_hours is the total fleet exposure (flight hours or flight
    cycles, unit-agnostic here). fleet_size is the number of aircraft.
    """
    if exposure_hours < 0:
        raise ValueError("exposure_hours must be non-negative, got %r" % (exposure_hours,))
    if fleet_size <= 0:
        raise ValueError("fleet_size must be a positive integer, got %r" % (fleet_size,))
    return {
        "total": float(exposure_hours),
        "per_aircraft": float(exposure_hours) / float(fleet_size),
    }


def group_events(events):
    """Group field events by condition_id into a {condition_id: count} map.

    Each event dict must carry event_id, condition_id, severity and
    description. Severity strings are validated; the maximum observed
    event severity per condition is preserved for reporting (exposed by
    assessment_summary as observed_max_event_severity).
    """
    counts = {}
    for event in events:
        condition_id = event["condition_id"]
        _check_severity(event["severity"])
        counts[condition_id] = counts.get(condition_id, 0) + 1
    return counts


def severity_max_per_condition(events):
    """Return {condition_id: highest observed event severity} for events."""
    maxima = {}
    for event in events:
        condition_id = event["condition_id"]
        rank = SEVERITY_RANK[event["severity"]]
        if condition_id not in maxima or rank > SEVERITY_RANK[maxima[condition_id]]:
            maxima[condition_id] = event["severity"]
    return maxima


def observed_rate(events_count, exposure_hours):
    """Observed event rate per exposure unit: count / exposure."""
    if events_count < 0:
        raise ValueError("events_count must be non-negative, got %r" % (events_count,))
    if exposure_hours <= 0:
        raise ValueError("exposure_hours must be positive to form a rate, got %r" % (exposure_hours,))
    return float(events_count) / float(exposure_hours)


def poisson_exceedance_p(observed_count, expected_count):
    """One-sided Poisson tail P(X >= observed | mean = expected).

    Sums the Poisson mass from k = observed_count upward, stopping when
    k exceeds expected_count * CEILING_MULT + 50 or the added term drops
    below TERM_FLOOR. Uses exp and a log-factorial start for stability.
    """
    if observed_count < 0:
        raise ValueError("observed_count must be non-negative, got %r" % (observed_count,))
    if expected_count < 0:
        raise ValueError("expected_count must be non-negative, got %r" % (expected_count,))
    observed = int(observed_count)
    if observed == 0:
        return 1.0
    if expected_count == 0.0:
        # P(X >= k) with mean zero is zero for every k >= 1.
        return 0.0
    # Start term at k = observed via the log-factorial form for stability.
    ln_start = (
        -expected_count
        + observed * math.log(expected_count)
        - math.lgamma(observed + 1.0)
    )
    term = math.exp(ln_start)
    total = term
    k = observed
    limit = expected_count * CEILING_MULT + 50.0
    while k < limit:
        term = term * (expected_count / (k + 1.0))
        if term < TERM_FLOOR:
            break
        total += term
        k += 1
    if total > 1.0:
        return 1.0
    return total


def expected_events(predicted_rate, exposure_hours):
    """Expected number of events: predicted_rate * exposure."""
    if predicted_rate < 0:
        raise ValueError("predicted_rate must be non-negative, got %r" % (predicted_rate,))
    if exposure_hours < 0:
        raise ValueError("exposure_hours must be non-negative, got %r" % (exposure_hours,))
    return float(predicted_rate) * float(exposure_hours)


def adequacy_verdict(expected_event_count):
    """Return (adequate_bool, note) for the exposure adequacy screen."""
    if expected_event_count < 0:
        raise ValueError(
            "expected_event_count must be non-negative, got %r" % (expected_event_count,)
        )
    adequate = expected_event_count >= EXPOSURE_ADEQUACY_EXPECTED_EVENTS
    threshold = EXPOSURE_ADEQUACY_EXPECTED_EVENTS
    if adequate:
        note = (
            "exposure adequate to judge the predicted rate "
            "(expected events %.4g reaches the %.1f threshold)"
            % (expected_event_count, threshold)
        )
    else:
        note = (
            "exposure inadequate to judge the predicted rate "
            "(expected events %.4g below the %.1f threshold)"
            % (expected_event_count, threshold)
        )
    return adequate, note


def significance_verdict(condition_id, observed, expected, severity):
    """Decide whether the observed experience is safety-significant.

    Significant when: severity is hazardous or catastrophic with at least
    one observed event (single-event rule); or at least one observed
    event and the one-sided Poisson exceedance tail is at most alpha; or
    the observed rate is at least RATE_EXCEEDANCE_MIN times the
    predicted rate (rate ratio observed / expected). Returns a dict with
    the verdict, its reasons, and the supporting numbers.
    """
    if observed < 0:
        raise ValueError("observed must be non-negative, got %r" % (observed,))
    if expected < 0:
        raise ValueError("expected must be non-negative, got %r" % (expected,))
    _check_severity(severity)
    tail = poisson_exceedance_p(observed, expected)
    rate_ratio = None
    if expected > 0:
        rate_ratio = float(observed) / float(expected)
    significant = False
    reasons = []
    if severity in SINGLE_EVENT_SEVERITIES and observed >= 1:
        significant = True
        reasons.append(
            "single-event rule: one %s event is significant regardless of rate" % severity
        )
    if observed >= 1 and tail <= SIGNIFICANCE_ALPHA:
        significant = True
        reasons.append(
            "poisson exceedance tail %.4f is at or below alpha %.2f"
            % (tail, SIGNIFICANCE_ALPHA)
        )
    if rate_ratio is not None and rate_ratio >= RATE_EXCEEDANCE_MIN:
        significant = True
        reasons.append(
            "observed rate %.3f times predicted rate meets the %.1f exceedance factor"
            % (rate_ratio, RATE_EXCEEDANCE_MIN)
        )
    if not significant:
        reasons.append("rate within expectation")
    return {
        "condition_id": condition_id,
        "significant": significant,
        "severity": severity,
        "observed": observed,
        "expected": expected,
        "reasons": reasons,
        "poisson_exceedance_p": tail,
        "rate_ratio": rate_ratio,
    }


def corrective_route(verdict, exposure_adequate, trend_direction):
    """Route the corrective action and assign the urgency band.

    trend_direction is -1 (decreasing), 0 (flat) or 1 (increasing).
    Returns (route, urgency) with route one of
    airworthiness-directive-request, service-bulletin,
    continued-monitoring, no-action.
    """
    if trend_direction not in (-1, 0, 1):
        raise ValueError(
            "trend_direction must be -1, 0 or 1, got %r" % (trend_direction,)
        )
    severity = verdict["severity"]
    if verdict["significant"]:
        if severity == "catastrophic":
            return "airworthiness-directive-request", "immediate"
        if severity == "hazardous":
            return "service-bulletin", "short-term"
        if severity == "major" and trend_direction == 1:
            return "service-bulletin", "scheduled"
        if severity in ("major", "minor"):
            return "continued-monitoring", "scheduled"
        # Significant exceedance on a no-safety-effect condition.
        return "continued-monitoring", "routine"
    if exposure_adequate and trend_direction != 1:
        return "no-action", "routine"
    return "continued-monitoring", "routine"


def assessment_summary(
    fleet_size,
    exposure_hours,
    exposure_unit,
    events,
    predictions,
    trend_direction=0,
):
    """Assess the full fleet field-event dataset against predictions.

    Returns a dict with the exposure summary, the per-condition
    assessment rows (expected and observed events, adequacy, Poisson
    tail, significance verdict, route and urgency), and the list of
    safety-significant conditions.
    """
    if fleet_size <= 0:
        raise ValueError("fleet_size must be a positive integer, got %r" % (fleet_size,))
    if exposure_hours < 0:
        raise ValueError("exposure_hours must be non-negative, got %r" % (exposure_hours,))
    if exposure_unit not in VALID_EXPOSURE_UNITS:
        raise ValueError(
            "exposure_unit must be one of %s, got %r"
            % (", ".join(VALID_EXPOSURE_UNITS), exposure_unit)
        )
    if trend_direction not in (-1, 0, 1):
        raise ValueError(
            "trend_direction must be -1, 0 or 1, got %r" % (trend_direction,)
        )
    if not predictions:
        raise ValueError("predictions must not be empty")
    for condition_id, prediction in predictions.items():
        rate = prediction["predicted_rate"]
        if rate < 0:
            raise ValueError(
                "predicted_rate for %r must be non-negative, got %r" % (condition_id, rate)
            )
        _check_severity(prediction["severity"])
    counts = group_events(events)
    observed_max = severity_max_per_condition(events)
    for condition_id in counts:
        if condition_id not in predictions:
            raise ValueError(
                "event condition %r is missing from predictions" % (condition_id,)
            )
    exp = exposure_summary(exposure_hours, fleet_size)
    conditions = []
    for condition_id in sorted(predictions):
        prediction = predictions[condition_id]
        rate = prediction["predicted_rate"]
        severity = prediction["severity"]
        note = prediction.get("note", "")
        expected = expected_events(rate, exposure_hours)
        count = counts.get(condition_id, 0)
        adequate, adequacy_note = adequacy_verdict(expected)
        verdict = significance_verdict(condition_id, count, expected, severity)
        route, urgency = corrective_route(verdict, adequate, trend_direction)
        conditions.append(
            {
                "condition_id": condition_id,
                "predicted_rate": rate,
                "predicted_severity": severity,
                "prediction_note": note,
                "expected_events": expected,
                "observed_count": count,
                "observed_max_event_severity": observed_max.get(condition_id),
                "observed_rate": observed_rate(count, exposure_hours),
                "exposure_adequate": adequate,
                "adequacy_note": adequacy_note,
                "significance": verdict,
                "route": route,
                "urgency": urgency,
            }
        )
    significant_ids = [
        row["condition_id"] for row in conditions if row["significance"]["significant"]
    ]
    return {
        "fleet_size": fleet_size,
        "exposure_unit": exposure_unit,
        "exposure_summary": exp,
        "trend_direction": trend_direction,
        "conditions": conditions,
        "safety_significant_conditions": significant_ids,
    }
