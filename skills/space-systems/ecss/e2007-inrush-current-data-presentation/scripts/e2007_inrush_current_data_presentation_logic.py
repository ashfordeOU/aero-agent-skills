#!/usr/bin/env python3
"""Inrush-current data presentation, ECSS-E-ST-20-07C clause 5.4.4.5.

Paraphrased procedure, no verbatim standard text. The clause asks a
switch-on surge result to be presented as current drawn against time,
spanning the transient and stating the conditions the trace is valid
under. This module turns that into a deterministic assessment:

  axis quantities and units -> is the graph really current against time
  plotted span              -> does it hold the surge and its settling
  vertical scale vs peak    -> is the peak clipped, or too small to read
  sample interval vs edge   -> is the rising edge resolved at all
  stated conditions         -> can the trace be reproduced from the page

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Plot edges, scales and intervals are floats, so
# a graph that exactly meets a bound can land a few units in the last
# place off it. The tolerances absorb that representation error only.
REL_TOL = 1e-12
ABS_TOL = 1e-15

# A peak using less than this share of the vertical scale is legible but
# coarse: the reader loses resolution on the quantity being reported.
MIN_PEAK_SCALE_FRACTION = 0.25

# Samples that must land on the rising edge before the drawn edge is the
# unit's own rather than the digitizer's.
MIN_SAMPLES_ON_RISING_EDGE = 5

# Below this peak-to-steady ratio the surge is hard to separate from the
# steady draw on a single linear axis.
MIN_DISTINGUISHABLE_RATIO = 1.05

RECOGNIZED_QUANTITIES = ("current", "time", "voltage", "temperature")
RECOGNIZED_CURRENT_UNITS = ("a", "ma", "ka")
RECOGNIZED_TIME_UNITS = ("s", "ms", "us", "ns")

REQUIRED_CONDITIONS = (
    "ambient-temperature",
    "bus-voltage",
    "load-configuration",
    "source-impedance",
    "switching-event",
)

VERDICT_COMPLIANT = "presentation-compliant"
VERDICT_DEFICIENT = "presentation-deficient"


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


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _word(record, key, where, recognized):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str):
        raise ValueError("%s: field %r must be a string, got %r" % (where, key, value))
    token = value.strip().lower()
    if token not in recognized:
        raise ValueError(
            "%s: unrecognized %s %r; recognized: %s"
            % (where, key, value, ", ".join(recognized))
        )
    return token


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def normalize_condition(name):
    """Normalize a stated-condition label to its comparison token."""
    if not isinstance(name, str):
        raise ValueError("stated condition must be a string, got %r" % (name,))
    token = name.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in token:
        token = token.replace("--", "-")
    if not token:
        raise ValueError("stated condition must not be empty")
    return token


def validate_graph(config):
    """Validate a presented current-against-time graph and normalize it."""
    where = "graph"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)

    out = {}
    out["x_quantity"] = _word(config, "x_quantity", where, RECOGNIZED_QUANTITIES)
    out["y_quantity"] = _word(config, "y_quantity", where, RECOGNIZED_QUANTITIES)
    units = RECOGNIZED_CURRENT_UNITS + RECOGNIZED_TIME_UNITS
    out["x_unit"] = _word(config, "x_unit", where, units)
    out["y_unit"] = _word(config, "y_unit", where, units)

    plot_start = _number(config, "plot_start_s", where)
    plot_stop = _number(config, "plot_stop_s", where)
    if plot_stop <= plot_start:
        raise ValueError(
            "%s: plot_stop_s (%g) must exceed plot_start_s (%g)"
            % (where, plot_stop, plot_start)
        )
    out["plot_start_s"] = plot_start
    out["plot_stop_s"] = plot_stop

    for key in ("full_scale_a", "peak_current_a", "sample_interval_s"):
        value = _number(config, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        out[key] = value

    steady = _number(config, "steady_current_a", where)
    if steady <= 0.0:
        raise ValueError("%s: steady_current_a must be > 0, got %g" % (where, steady))
    if steady > out["peak_current_a"]:
        raise ValueError(
            "%s: steady_current_a (%g) cannot exceed peak_current_a (%g)"
            % (where, steady, out["peak_current_a"])
        )
    out["steady_current_a"] = steady

    stated = config.get("stated_conditions", ())
    if isinstance(stated, str) or not isinstance(stated, (tuple, list, set)):
        raise ValueError(
            "%s: stated_conditions must be a sequence of condition labels" % where
        )
    out["stated_conditions"] = frozenset(normalize_condition(n) for n in stated)
    return out


def axis_findings(graph):
    """Report axes that are not current plotted against time."""
    if not isinstance(graph, dict):
        raise ValueError("graph: record must be a mapping")
    for key in ("x_quantity", "y_quantity", "x_unit", "y_unit"):
        if key not in graph:
            raise ValueError("graph: missing required field %r" % key)
    out = []
    if graph["x_quantity"] != "time":
        out.append(
            "horizontal axis carries %s, the clause needs time" % graph["x_quantity"]
        )
    elif graph["x_unit"] not in RECOGNIZED_TIME_UNITS:
        out.append(
            "horizontal axis is time but its unit %s is not a time unit"
            % graph["x_unit"]
        )
    if graph["y_quantity"] != "current":
        out.append(
            "vertical axis carries %s, the clause needs current"
            % graph["y_quantity"]
        )
    elif graph["y_unit"] not in RECOGNIZED_CURRENT_UNITS:
        out.append(
            "vertical axis is current but its unit %s is not a current unit"
            % graph["y_unit"]
        )
    return out


def time_span_shortfalls(graph, switching_instant_s, settle_time_s):
    """Parts of the transient the plotted time span does not show."""
    instant = _scalar(switching_instant_s, "switching_instant_s")
    settle = _scalar(settle_time_s, "settle_time_s")
    if settle <= instant:
        raise ValueError(
            "settle_time_s (%g) must come after switching_instant_s (%g)"
            % (settle, instant)
        )
    start = _number(graph, "plot_start_s", "graph")
    stop = _number(graph, "plot_stop_s", "graph")
    out = []
    if not at_most(start, instant):
        out.append(
            "the plot opens at %g s, after the switching instant %g s, so the draw "
            "the surge started from is not shown" % (start, instant)
        )
    if not at_least(stop, settle):
        out.append(
            "the plot closes at %g s, before the draw has settled at %g s, so the "
            "return to steady current is not shown" % (stop, settle)
        )
    return out


def peak_is_clipped(peak_current_a, full_scale_a):
    """True when the peak runs off the top of the vertical scale."""
    peak = _scalar(peak_current_a, "peak_current_a")
    full_scale = _scalar(full_scale_a, "full_scale_a")
    if peak <= 0.0:
        raise ValueError("peak_current_a must be > 0, got %g" % peak)
    if full_scale <= 0.0:
        raise ValueError("full_scale_a must be > 0, got %g" % full_scale)
    return not at_most(peak, full_scale)


def scale_utilisation(peak_current_a, full_scale_a):
    """Share of the vertical scale the peak actually occupies."""
    peak = _scalar(peak_current_a, "peak_current_a")
    full_scale = _scalar(full_scale_a, "full_scale_a")
    if peak <= 0.0:
        raise ValueError("peak_current_a must be > 0, got %g" % peak)
    if full_scale <= 0.0:
        raise ValueError("full_scale_a must be > 0, got %g" % full_scale)
    return peak / full_scale


def samples_on_rising_edge(rise_time_s, sample_interval_s):
    """Whole samples that land on the rising edge of the surge."""
    rise = _scalar(rise_time_s, "rise_time_s")
    interval = _scalar(sample_interval_s, "sample_interval_s")
    if rise <= 0.0:
        raise ValueError("rise_time_s must be > 0, got %g" % rise)
    if interval <= 0.0:
        raise ValueError("sample_interval_s must be > 0, got %g" % interval)
    return int(math.floor(rise / interval))


def peak_to_steady_ratio(peak_current_a, steady_current_a):
    """How far the surge rises above the draw it settles back to."""
    peak = _scalar(peak_current_a, "peak_current_a")
    steady = _scalar(steady_current_a, "steady_current_a")
    if peak <= 0.0:
        raise ValueError("peak_current_a must be > 0, got %g" % peak)
    if steady <= 0.0:
        raise ValueError("steady_current_a must be > 0, got %g" % steady)
    return peak / steady


def missing_conditions(stated_conditions, required=REQUIRED_CONDITIONS):
    """Conditions the clause expects on the graph that are not stated."""
    if isinstance(stated_conditions, str) or not isinstance(
        stated_conditions, (tuple, list, set, frozenset)
    ):
        raise ValueError("stated_conditions must be a sequence of condition labels")
    present = set(normalize_condition(name) for name in stated_conditions)
    return [name for name in required if name not in present]


def assess_inrush_data_presentation(
    config,
    switching_instant_s,
    settle_time_s,
    rise_time_s,
    min_samples_on_edge=MIN_SAMPLES_ON_RISING_EDGE,
):
    """Full clause 5.4.4.5 assessment of a presented surge graph."""
    graph = validate_graph(config)
    axes = axis_findings(graph)
    shortfalls = time_span_shortfalls(graph, switching_instant_s, settle_time_s)
    clipped = peak_is_clipped(graph["peak_current_a"], graph["full_scale_a"])
    utilisation = scale_utilisation(graph["peak_current_a"], graph["full_scale_a"])
    edge_samples = samples_on_rising_edge(rise_time_s, graph["sample_interval_s"])
    ratio = peak_to_steady_ratio(
        graph["peak_current_a"], graph["steady_current_a"]
    )
    absent = missing_conditions(graph["stated_conditions"])

    wanted_samples = int(min_samples_on_edge)
    if wanted_samples < 1:
        raise ValueError(
            "min_samples_on_edge must be >= 1, got %d" % wanted_samples
        )

    findings = []
    findings.extend(axes)
    findings.extend(shortfalls)
    if clipped:
        findings.append(
            "the peak %g A runs past the %g A full scale, so the value the graph "
            "reports is the scale, not the surge"
            % (graph["peak_current_a"], graph["full_scale_a"])
        )
    if edge_samples < wanted_samples:
        findings.append(
            "%d sample(s) land on the %g s rising edge at a %g s interval, under "
            "the %d needed to draw the edge the unit produced"
            % (
                edge_samples,
                float(rise_time_s),
                graph["sample_interval_s"],
                wanted_samples,
            )
        )
    if absent:
        findings.append(
            "the graph does not state: %s, so the trace cannot be reproduced from "
            "the page" % ", ".join(absent)
        )

    limitations = []
    if not clipped and not at_least(utilisation, MIN_PEAK_SCALE_FRACTION):
        limitations.append(
            "the peak occupies %.3g of the vertical scale, so the surge is read at "
            "a coarser resolution than the graph could give" % utilisation
        )
    if not at_least(ratio, MIN_DISTINGUISHABLE_RATIO):
        limitations.append(
            "the peak is only %.3g times the settled draw, so the transient is hard "
            "to separate from the steady current on this axis" % ratio
        )

    return {
        "graph": graph,
        "axis_findings": axes,
        "time_span_shortfalls": shortfalls,
        "peak_is_clipped": clipped,
        "scale_utilisation": utilisation,
        "samples_on_rising_edge": edge_samples,
        "peak_to_steady_ratio": ratio,
        "missing_conditions": absent,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_COMPLIANT if not findings else VERDICT_DEFICIENT,
    }
