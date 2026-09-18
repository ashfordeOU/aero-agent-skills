#!/usr/bin/env python3
"""Radiated electric susceptibility reporting, clause 5.4.11.5.

Paraphrased procedure, no verbatim standard text. The clause is about what the
report has to put in front of a reader once the exposure is finished: the
generator setting that drove each frequency, the forward power that reached
the antenna, and the field level that was actually achieved at the unit --
presented as a table, as a graph, or as both. This module models that:

  per-frequency record        -> complete, or the point cannot be reported
  forward and reflected power -> net power delivered into the antenna
  net power + chamber factor  -> the field that level of drive predicts
  predicted vs achieved       -> decibel discrepancy vs its tolerance
  table and graph inventory   -> every point reaches the reader somehow
  aggregate                   -> presentation verdict

A point whose achieved field cannot be reconciled with the power that produced
it is not a presentation problem: it says the level written into the report is
not the level the unit saw.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Relative tolerance for frequency matching between the data and the exhibits.
REL_TOL = 1e-9

# Absolute tolerance in decibels and watts for boundary comparisons.
ABS_TOL = 1e-9

# Fields every reported frequency point has to carry.
REQUIRED_POINT_FIELDS = (
    "frequency_hz",
    "generator_setting_dbm",
    "forward_power_w",
    "reflected_power_w",
    "achieved_field_v_per_m",
)

# How far the achieved field may sit from the field the delivered power
# predicts before the pair stops being reconcilable, in decibels.
DEFAULT_FIELD_TOLERANCE_DB = 2.0

# A frequency axis spanning this ratio or more has to be logarithmic, or the
# bottom of the range is compressed into the left-hand edge of the plot.
DECADE_RATIO = 10.0

AXIS_SCALES = ("linear", "logarithmic")

CATEGORY_REPORTABLE = "reportable"
CATEGORY_UNPRESENTED = "unpresented"
CATEGORY_IRRECONCILABLE = "irreconcilable"
CATEGORIES = (CATEGORY_REPORTABLE, CATEGORY_UNPRESENTED, CATEGORY_IRRECONCILABLE)

VERDICT_REPORTABLE = "presentation-complete"
VERDICT_REJECTED = "presentation-rejected"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def normalize_point(raw, where="point"):
    """Validate one reported frequency point and return it normalized."""
    if not isinstance(raw, dict):
        raise ValueError("%s: must be a mapping of field -> value" % where)
    point = {}
    for field in REQUIRED_POINT_FIELDS:
        point[field] = _number(raw, field, where)
    for field in raw:
        if field not in REQUIRED_POINT_FIELDS:
            raise ValueError("%s: unrecognized field %r" % (where, field))
    if point["frequency_hz"] <= 0.0:
        raise ValueError(
            "%s: frequency_hz must be > 0, got %g" % (where, point["frequency_hz"])
        )
    if point["forward_power_w"] <= 0.0:
        raise ValueError(
            "%s: forward_power_w must be > 0, got %g" % (where, point["forward_power_w"])
        )
    if point["reflected_power_w"] < 0.0:
        raise ValueError(
            "%s: reflected_power_w must be >= 0, got %g"
            % (where, point["reflected_power_w"])
        )
    if point["achieved_field_v_per_m"] <= 0.0:
        raise ValueError(
            "%s: achieved_field_v_per_m must be > 0, got %g"
            % (where, point["achieved_field_v_per_m"])
        )
    return point


def normalize_points(raws):
    """Validate the reported points and return them sorted by frequency."""
    where = "points"
    if not isinstance(raws, (list, tuple)):
        raise ValueError("%s: must be a sequence of point records" % where)
    if not raws:
        raise ValueError("%s: the report carries no frequency point" % where)
    points = []
    for index, raw in enumerate(raws):
        point = normalize_point(raw, "%s[%d]" % (where, index))
        for previous in points:
            if math.isclose(
                previous["frequency_hz"],
                point["frequency_hz"],
                rel_tol=REL_TOL,
                abs_tol=0.0,
            ):
                raise ValueError(
                    "%s[%d]: frequency %g Hz reported more than once"
                    % (where, index, point["frequency_hz"])
                )
        points.append(point)
    points.sort(key=lambda p: p["frequency_hz"])
    return tuple(points)


def net_forward_power(forward_power_w, reflected_power_w):
    """Power actually delivered into the antenna: forward less what came back."""
    forward = _number({"v": forward_power_w}, "v", "forward_power_w")
    reflected = _number({"v": reflected_power_w}, "v", "reflected_power_w")
    if forward <= 0.0:
        raise ValueError("forward_power_w must be > 0, got %g" % forward)
    if reflected < 0.0:
        raise ValueError("reflected_power_w must be >= 0, got %g" % reflected)
    if reflected > forward and not math.isclose(
        reflected, forward, rel_tol=0.0, abs_tol=ABS_TOL
    ):
        raise ValueError(
            "reflected_power_w %g exceeds forward_power_w %g" % (reflected, forward)
        )
    net = forward - reflected
    return net if net > 0.0 else 0.0


def predicted_field(net_power_w, chamber_factor_v_per_m_per_sqrt_w):
    """Field the delivered power predicts at the unit, volt per metre.

    The chamber factor bundles the antenna, the separation and the room into
    one calibrated constant, and field goes as the square root of power: four
    times the drive buys twice the field, which is why the last few decibels
    of a level are the expensive ones.
    """
    power = _number({"v": net_power_w}, "v", "net_power_w")
    factor = _number(
        {"v": chamber_factor_v_per_m_per_sqrt_w},
        "v",
        "chamber_factor_v_per_m_per_sqrt_w",
    )
    if power < 0.0:
        raise ValueError("net_power_w must be >= 0, got %g" % power)
    if factor <= 0.0:
        raise ValueError(
            "chamber_factor_v_per_m_per_sqrt_w must be > 0, got %g" % factor
        )
    return factor * math.sqrt(power)


def field_discrepancy_db(achieved_v_per_m, predicted_v_per_m):
    """Signed decibel distance of the achieved field from the predicted one."""
    achieved = _number({"v": achieved_v_per_m}, "v", "achieved_v_per_m")
    predicted = _number({"v": predicted_v_per_m}, "v", "predicted_v_per_m")
    if achieved <= 0.0:
        raise ValueError("achieved_v_per_m must be > 0, got %g" % achieved)
    if predicted <= 0.0:
        raise ValueError("predicted_v_per_m must be > 0, got %g" % predicted)
    return 20.0 * math.log10(achieved / predicted)


def validate_graph(graph):
    """Validate a graph exhibit and return it normalized, or None when absent."""
    where = "graph"
    if graph is None:
        return None
    if not isinstance(graph, dict):
        raise ValueError("%s: must be a mapping or None" % where)
    for field in ("frequency_axis_label", "level_axis_label", "frequency_axis_scale"):
        if field not in graph:
            raise ValueError("%s: missing required field %r" % (where, field))
    for field in graph:
        if field not in (
            "frequency_axis_label",
            "level_axis_label",
            "frequency_axis_scale",
            "plotted_frequencies_hz",
        ):
            raise ValueError("%s: unrecognized field %r" % (where, field))
    labels = {}
    for field in ("frequency_axis_label", "level_axis_label"):
        label = graph[field]
        if not isinstance(label, str) or not label.strip():
            raise ValueError("%s: %s must be a non-empty string" % (where, field))
        labels[field] = label.strip()
    scale = graph["frequency_axis_scale"]
    if not isinstance(scale, str) or scale.strip().lower() not in AXIS_SCALES:
        raise ValueError(
            "%s: frequency_axis_scale must be one of %s, got %r"
            % (where, ", ".join(AXIS_SCALES), scale)
        )
    plotted = graph.get("plotted_frequencies_hz", ())
    if not isinstance(plotted, (list, tuple)):
        raise ValueError("%s: plotted_frequencies_hz must be a sequence" % where)
    frequencies = []
    for index, value in enumerate(plotted):
        frequency = _number(
            {"v": value}, "v", "%s.plotted_frequencies_hz[%d]" % (where, index)
        )
        if frequency <= 0.0:
            raise ValueError(
                "%s.plotted_frequencies_hz[%d]: must be > 0, got %g"
                % (where, index, frequency)
            )
        frequencies.append(frequency)
    normalized = dict(labels)
    normalized["frequency_axis_scale"] = scale.strip().lower()
    normalized["plotted_frequencies_hz"] = tuple(sorted(frequencies))
    return normalized


def axis_scale_adequate(graph, start_hz, stop_hz):
    """A frequency axis covering a decade or more has to be logarithmic."""
    if graph is None:
        return True
    start = _number({"v": start_hz}, "v", "start_hz")
    stop = _number({"v": stop_hz}, "v", "stop_hz")
    if start <= 0.0:
        raise ValueError("start_hz must be > 0, got %g" % start)
    if stop < start:
        raise ValueError("stop_hz must be at or above start_hz")
    span = stop / start
    wide = span > DECADE_RATIO or math.isclose(
        span, DECADE_RATIO, rel_tol=REL_TOL, abs_tol=0.0
    )
    if not wide:
        return True
    return graph["frequency_axis_scale"] == "logarithmic"


def normalize_tabulated(frequencies):
    """Validate the frequencies a table carries and return them sorted."""
    where = "tabulated_frequencies_hz"
    if not isinstance(frequencies, (list, tuple)):
        raise ValueError("%s: must be a sequence" % where)
    values = []
    for index, value in enumerate(frequencies):
        frequency = _number({"v": value}, "v", "%s[%d]" % (where, index))
        if frequency <= 0.0:
            raise ValueError("%s[%d]: must be > 0, got %g" % (where, index, frequency))
        values.append(frequency)
    return tuple(sorted(values))


def _presented(frequency, exhibited):
    for candidate in exhibited:
        if math.isclose(frequency, candidate, rel_tol=REL_TOL, abs_tol=0.0):
            return True
    return False


def categorize_point(point, chamber_factor, exhibited, tolerance_db):
    """Categorize one point as reportable, unpresented or irreconcilable."""
    checked = normalize_point(point)
    net = net_forward_power(
        checked["forward_power_w"], checked["reflected_power_w"]
    )
    if net <= 0.0:
        return CATEGORY_IRRECONCILABLE
    predicted = predicted_field(net, chamber_factor)
    discrepancy = field_discrepancy_db(
        checked["achieved_field_v_per_m"], predicted
    )
    over = abs(discrepancy) > tolerance_db and not math.isclose(
        abs(discrepancy), tolerance_db, rel_tol=0.0, abs_tol=ABS_TOL
    )
    if over:
        return CATEGORY_IRRECONCILABLE
    if not _presented(checked["frequency_hz"], exhibited):
        return CATEGORY_UNPRESENTED
    return CATEGORY_REPORTABLE


def assess_report(
    points,
    chamber_factor_v_per_m_per_sqrt_w,
    tabulated_frequencies_hz=(),
    graph=None,
    tolerance_db=DEFAULT_FIELD_TOLERANCE_DB,
):
    """Full clause 5.4.11.5 assessment of a susceptibility test presentation."""
    recorded = normalize_points(points)
    factor = _number(
        {"v": chamber_factor_v_per_m_per_sqrt_w},
        "v",
        "chamber_factor_v_per_m_per_sqrt_w",
    )
    if factor <= 0.0:
        raise ValueError("chamber_factor_v_per_m_per_sqrt_w must be > 0, got %g" % factor)
    tolerance = _number({"v": tolerance_db}, "v", "tolerance_db")
    if tolerance <= 0.0:
        raise ValueError("tolerance_db must be > 0, got %g" % tolerance)
    tabulated = normalize_tabulated(tabulated_frequencies_hz)
    exhibit = validate_graph(graph)
    plotted = exhibit["plotted_frequencies_hz"] if exhibit else ()
    exhibited = tuple(tabulated) + tuple(plotted)

    start = recorded[0]["frequency_hz"]
    stop = recorded[-1]["frequency_hz"]

    graded = []
    counts = dict((category, 0) for category in CATEGORIES)
    findings = []
    limitations = []
    for point in recorded:
        net = net_forward_power(point["forward_power_w"], point["reflected_power_w"])
        predicted = predicted_field(net, factor) if net > 0.0 else 0.0
        discrepancy = (
            field_discrepancy_db(point["achieved_field_v_per_m"], predicted)
            if predicted > 0.0
            else float("nan")
        )
        category = categorize_point(point, factor, exhibited, tolerance)
        counts[category] += 1
        graded.append(
            {
                "frequency_hz": point["frequency_hz"],
                "generator_setting_dbm": point["generator_setting_dbm"],
                "net_forward_power_w": net,
                "predicted_field_v_per_m": predicted,
                "achieved_field_v_per_m": point["achieved_field_v_per_m"],
                "discrepancy_db": discrepancy,
                "category": category,
            }
        )
        if category == CATEGORY_IRRECONCILABLE:
            findings.append(
                "the field reported at %g Hz cannot be reconciled with the power "
                "delivered there" % point["frequency_hz"]
            )
        elif category == CATEGORY_UNPRESENTED:
            findings.append(
                "the point at %g Hz appears in no table and on no graph"
                % point["frequency_hz"]
            )
        reflected_share = point["reflected_power_w"] / point["forward_power_w"]
        if reflected_share > 0.25:
            limitations.append(
                "%g Hz returned %.0f%% of the forward power, so the drive margin "
                "there is thin" % (point["frequency_hz"], 100.0 * reflected_share)
            )

    if not tabulated and exhibit is None:
        findings.append("the report carries neither a table nor a graph")

    if not axis_scale_adequate(exhibit, start, stop):
        findings.append(
            "the frequency axis spans a decade or more on a linear scale"
        )

    return {
        "points": tuple(graded),
        "counts": counts,
        "reported_span_hz": (start, stop),
        "tabulated_frequencies_hz": tabulated,
        "graph": exhibit,
        "tolerance_db": tolerance,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_REPORTABLE if not findings else VERDICT_REJECTED,
    }
