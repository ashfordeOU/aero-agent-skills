"""Exception reporting on a space link.

Anchor: ECSS-E-ST-50C clause 5.6.14.9 -- space link exception reporting.
Paraphrased into an implementable procedure; no standard text is reproduced.

Two normative items sit here, and they fail independently:

  reported     -- an exception detected on the space link reaches a report. A
                  detectable condition with no route configured is a silent
                  failure: the system knows and nobody is told.
  identifiable -- the report carries enough to identify the exception. A report
                  that arrives saying only that something went wrong consumes
                  downlink and resolves nothing.

Grading them separately is the point. A design can route every exception type
and still fail the second item on every one of them, and a design can produce
beautifully complete reports for the three conditions it happens to route while
staying silent on the rest. A single pass-or-fail verdict hides both cases.

A third consideration cuts across both: the report channel is part of the link
it reports on. A condition that recurs at high rate, reported one occurrence at
a time, saturates the very channel the report has to travel over, so the burst
is aggregated into one report carrying a count instead.
"""

import math

__all__ = [
    "REQUIRED_REPORT_FIELDS",
    "COMPLIANT",
    "EXCEPTIONS_UNREPORTED",
    "REPORTS_NOT_IDENTIFIABLE",
    "REPORT_CHANNEL_SATURATED",
    "REL_TOL",
    "validate_types",
    "validate_routes",
    "validate_counts",
    "report_gaps",
    "unreported_exception_types",
    "orphan_routes",
    "report_load_bps",
    "aggregated_load_bps",
    "max_unaggregated_occurrences",
    "aggregation_required",
    "assess_exception_reporting",
]

REQUIRED_REPORT_FIELDS = (
    "exception_type",
    "occurrence_time_s",
    "link_identifier",
    "occurrence_count",
)

COMPLIANT = "compliant"
EXCEPTIONS_UNREPORTED = "exceptions-unreported"
REPORTS_NOT_IDENTIFIABLE = "reports-not-identifiable"
REPORT_CHANNEL_SATURATED = "report-channel-saturated"

# Relative tolerance for the channel-budget comparison, so a burst sized to
# exactly fill the report budget is accepted on every platform, not on some.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def _positive(value, name):
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_types(values, name="detectable_types"):
    """Return the exception types a subsystem can detect, as unique names."""
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a list or tuple of exception type names" % name)
    if not values:
        raise ValueError("%s must name at least one detectable exception" % name)
    checked = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s[%d] must be a non-empty exception type name" % (name, index))
        if value in checked:
            raise ValueError("%s names %r more than once" % (name, value))
        checked.append(value)
    return checked


def validate_routes(routes, name="routes"):
    """Return the reporting routes, each a sample report for one exception type."""
    if not isinstance(routes, dict):
        raise ValueError("%s must be a mapping of exception type to sample report" % name)
    for key, report in routes.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("%s has a key that is not an exception type name" % name)
        if not isinstance(report, dict):
            raise ValueError("%s[%r] must be a mapping of report fields" % (name, key))
    return dict(routes)


def validate_counts(counts, name="observed_counts"):
    """Return how many times each exception type fired in the window."""
    if not isinstance(counts, dict):
        raise ValueError("%s must be a mapping of exception type to occurrence count" % name)
    checked = {}
    for key, value in counts.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("%s has a key that is not an exception type name" % name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s[%r] must be an integer count" % (name, key))
        if value < 0:
            raise ValueError("%s[%r] must not be negative, got %r" % (name, key, value))
        checked[key] = value
    return checked


def report_gaps(report):
    """Return the identifying fields this report does not actually carry.

    A field present but empty is a gap, not a value. An empty field renders as
    a blank in whatever reads the report, which is indistinguishable from a
    condition that had nothing to say.
    """
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping of report fields")
    gaps = []
    for field in REQUIRED_REPORT_FIELDS:
        if field not in report:
            gaps.append("%s absent" % field)
            continue
        value = report[field]
        if value is None:
            gaps.append("%s empty" % field)
        elif isinstance(value, str) and not value.strip():
            gaps.append("%s empty" % field)
        elif field == "occurrence_count":
            if isinstance(value, bool) or not isinstance(value, int):
                gaps.append("occurrence_count is not a count")
            elif value < 1:
                gaps.append("occurrence_count reports no occurrence")
    return gaps


def unreported_exception_types(detectable_types, routes):
    """Return the detectable exceptions no route carries -- the silent failures."""
    detectable = validate_types(detectable_types)
    configured = validate_routes(routes)
    return [name for name in detectable if name not in configured]


def orphan_routes(detectable_types, routes):
    """Return routes for conditions nothing declares it can detect."""
    detectable = validate_types(detectable_types)
    configured = validate_routes(routes)
    return sorted(name for name in configured if name not in detectable)


def report_load_bps(occurrences, report_bits, window_s):
    """Return the report channel load of reporting each occurrence separately."""
    if isinstance(occurrences, bool) or not isinstance(occurrences, int):
        raise ValueError("occurrences must be an integer")
    if occurrences < 0:
        raise ValueError("occurrences must not be negative, got %r" % (occurrences,))
    size = _positive(report_bits, "report_bits")
    window = _positive(window_s, "window_s")
    return occurrences * size / window


def aggregated_load_bps(report_bits, window_s):
    """Return the load of one aggregated report per window carrying a count."""
    return _positive(report_bits, "report_bits") / _positive(window_s, "window_s")


def max_unaggregated_occurrences(channel_budget_bps, report_bits, window_s):
    """Return how many separate reports the budget carries in one window."""
    budget = _positive(channel_budget_bps, "channel_budget_bps")
    size = _positive(report_bits, "report_bits")
    window = _positive(window_s, "window_s")
    allowed = budget * window / size
    # Nudge before flooring so a burst sized to exactly fill the budget counts,
    # rather than being pushed under by the last bit of division rounding.
    return int(math.floor(allowed + REL_TOL * max(allowed, 1.0)))


def aggregation_required(occurrences, report_bits, window_s, channel_budget_bps):
    """Return whether this burst has to be aggregated to fit the report channel."""
    load = report_load_bps(occurrences, report_bits, window_s)
    budget = _positive(channel_budget_bps, "channel_budget_bps")
    return load > budget + REL_TOL * max(load, budget, 1.0)


def assess_exception_reporting(
    detectable_types,
    routes,
    report_bits,
    window_s,
    channel_budget_bps,
    observed_counts=None,
):
    """Grade a space link exception reporting design against both normative items."""
    detectable = validate_types(detectable_types)
    configured = validate_routes(routes)
    counts = validate_counts({} if observed_counts is None else observed_counts)
    size = _positive(report_bits, "report_bits")
    window = _positive(window_s, "window_s")
    budget = _positive(channel_budget_bps, "channel_budget_bps")

    unreported = unreported_exception_types(detectable, configured)
    orphans = orphan_routes(detectable, configured)

    gaps_by_type = {}
    for name in detectable:
        if name in configured:
            gaps = report_gaps(configured[name])
            if gaps:
                gaps_by_type[name] = gaps

    total_occurrences = sum(
        counts.get(name, 0) for name in detectable if name in configured
    )
    raw_load = report_load_bps(total_occurrences, size, window)
    saturating = [
        name
        for name in detectable
        if name in configured
        and aggregation_required(counts.get(name, 0), size, window, budget)
    ]
    channel_saturated = raw_load > budget + REL_TOL * max(raw_load, budget, 1.0)

    findings = []
    if unreported:
        findings.append(
            "%s can be detected but no report route carries %s; the system knows "
            "and nobody is told"
            % (", ".join(unreported), "them" if len(unreported) > 1 else "it")
        )
    if gaps_by_type:
        for name in sorted(gaps_by_type):
            findings.append(
                "report for %s does not identify the exception: %s"
                % (name, "; ".join(gaps_by_type[name]))
            )
    if channel_saturated:
        findings.append(
            "reporting %d occurrences separately costs %.9g bit/s against a %.9g "
            "bit/s report budget; the reporting saturates the link it reports on"
            % (total_occurrences, raw_load, budget)
        )
        findings.append(
            "at most %d separate reports fit one window; aggregate the rest into "
            "one report carrying a count, which costs %.9g bit/s"
            % (
                max_unaggregated_occurrences(budget, size, window),
                aggregated_load_bps(size, window),
            )
        )
    if orphans:
        findings.append(
            "route configured for %s, which nothing declares it can detect; the "
            "report can never be raised" % (", ".join(orphans),)
        )

    item_reported = not unreported and not channel_saturated
    item_identifiable = not gaps_by_type

    if unreported:
        verdict = EXCEPTIONS_UNREPORTED
    elif channel_saturated:
        verdict = REPORT_CHANNEL_SATURATED
    elif gaps_by_type:
        verdict = REPORTS_NOT_IDENTIFIABLE
    else:
        verdict = COMPLIANT

    return {
        "detectable_types": detectable,
        "routed_types": sorted(configured),
        "unreported_types": unreported,
        "orphan_routes": orphans,
        "report_gaps": gaps_by_type,
        "total_occurrences": total_occurrences,
        "report_load_bps": raw_load,
        "aggregated_load_bps": aggregated_load_bps(size, window),
        "max_unaggregated_occurrences": max_unaggregated_occurrences(budget, size, window),
        "saturating_types": saturating,
        "channel_budget_bps": budget,
        "item_reported": item_reported,
        "item_identifiable": item_identifiable,
        "verdict": verdict,
        "findings": findings,
    }
