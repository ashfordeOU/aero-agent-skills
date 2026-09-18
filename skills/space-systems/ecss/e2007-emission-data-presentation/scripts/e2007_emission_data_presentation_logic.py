#!/usr/bin/env python3
"""Emission data presentation, ECSS-E-ST-20-07C clause 5.2.9.4.

Paraphrased procedure, no verbatim standard text. The clause requires an
emission test to produce amplitude-against-frequency plots and to put them
in front of the operator automatically while the measurement is running.
This module turns that into a deterministic assessment:

  generation + timing   -> display mode (live, deferred, operator-initiated)
  axis quantities/units -> is the plot really amplitude against frequency
  displayed span        -> does it cover the declared test band
  refresh + latency     -> does the operator see the sweep progressing

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Refresh intervals and axis edges are floats, so a
# requirement that is exactly met can land a few units in the last place
# short. The tolerances absorb that representation error only.
TIME_REL_TOL = 1e-12
TIME_ABS_TOL = 1e-9
FREQ_REL_TOL = 1e-12
FREQ_ABS_TOL = 1e-6

# Updates the plot must deliver across one receiver sweep before the
# display counts as showing the measurement rather than summarising it.
DEFAULT_MIN_UPDATES_PER_SWEEP = 4.0

RECOGNIZED_QUANTITIES = ("amplitude", "frequency", "time", "phase")
RECOGNIZED_FREQUENCY_UNITS = ("hz", "khz", "mhz", "ghz")
RECOGNIZED_AMPLITUDE_UNITS = ("dbuv", "dbuv_m", "dbua", "dbm", "dbpt")

MODE_LIVE = "automatic-during-run"
MODE_DEFERRED = "automatic-after-run"
MODE_OPERATOR = "operator-initiated"
DISPLAY_MODES = (MODE_LIVE, MODE_DEFERRED, MODE_OPERATOR)


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


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


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


def at_most_time(value, bound):
    """True when a duration stays at or under a bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=TIME_REL_TOL, abs_tol=TIME_ABS_TOL)


def at_most_freq(value, bound):
    """True when a frequency stays at or under a bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=FREQ_REL_TOL, abs_tol=FREQ_ABS_TOL)


def at_least_freq(value, bound):
    """True when a frequency reaches a bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=FREQ_REL_TOL, abs_tol=FREQ_ABS_TOL)


def validate_presentation(config):
    """Validate a plotting-chain configuration and return it normalized.

    Required: automatic_generation, displayed_during_run, limit_line_shown
    (booleans), x_quantity, y_quantity, x_unit, y_unit (recognized tokens),
    refresh_interval_s (> 0), display_latency_s (>= 0), plot_start_hz and
    plot_stop_hz (positive, stop above start).
    """
    where = "presentation"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)

    automatic = _flag(config, "automatic_generation", where)
    during_run = _flag(config, "displayed_during_run", where)
    limit_line = _flag(config, "limit_line_shown", where)

    x_quantity = _word(config, "x_quantity", where, RECOGNIZED_QUANTITIES)
    y_quantity = _word(config, "y_quantity", where, RECOGNIZED_QUANTITIES)
    x_unit = _word(
        config,
        "x_unit",
        where,
        RECOGNIZED_FREQUENCY_UNITS + RECOGNIZED_AMPLITUDE_UNITS,
    )
    y_unit = _word(
        config,
        "y_unit",
        where,
        RECOGNIZED_FREQUENCY_UNITS + RECOGNIZED_AMPLITUDE_UNITS,
    )

    refresh = _number(config, "refresh_interval_s", where)
    if refresh <= 0.0:
        raise ValueError(
            "%s: refresh_interval_s must be > 0, got %g" % (where, refresh)
        )
    latency = _number(config, "display_latency_s", where)
    if latency < 0.0:
        raise ValueError(
            "%s: display_latency_s must be >= 0, got %g" % (where, latency)
        )

    plot_start = _number(config, "plot_start_hz", where)
    plot_stop = _number(config, "plot_stop_hz", where)
    if plot_start <= 0.0:
        raise ValueError("%s: plot_start_hz must be > 0, got %g" % (where, plot_start))
    if plot_stop <= plot_start:
        raise ValueError(
            "%s: plot_stop_hz (%g) must exceed plot_start_hz (%g)"
            % (where, plot_stop, plot_start)
        )

    return {
        "automatic_generation": automatic,
        "displayed_during_run": during_run,
        "limit_line_shown": limit_line,
        "x_quantity": x_quantity,
        "y_quantity": y_quantity,
        "x_unit": x_unit,
        "y_unit": y_unit,
        "refresh_interval_s": refresh,
        "display_latency_s": latency,
        "plot_start_hz": plot_start,
        "plot_stop_hz": plot_stop,
    }


def resolve_display_mode(automatic_generation, displayed_during_run):
    """Group a plotting chain by how and when the plot reaches the operator."""
    if not isinstance(automatic_generation, bool) or not isinstance(
        displayed_during_run, bool
    ):
        raise ValueError("display mode inputs must be booleans")
    if not automatic_generation:
        return MODE_OPERATOR
    if displayed_during_run:
        return MODE_LIVE
    return MODE_DEFERRED


def axis_findings(presentation):
    """Report axes that are not amplitude plotted against frequency."""
    config = presentation if isinstance(presentation, dict) else {}
    if not config:
        raise ValueError("presentation: record must be a mapping")
    for key in ("x_quantity", "y_quantity", "x_unit", "y_unit"):
        if key not in config:
            raise ValueError("presentation: missing required field %r" % key)
    out = []
    if config["x_quantity"] != "frequency":
        out.append(
            "horizontal axis carries %s, the clause needs frequency"
            % config["x_quantity"]
        )
    elif config["x_unit"] not in RECOGNIZED_FREQUENCY_UNITS:
        out.append(
            "horizontal axis is frequency but its unit %s is not a frequency unit"
            % config["x_unit"]
        )
    if config["y_quantity"] != "amplitude":
        out.append(
            "vertical axis carries %s, the clause needs amplitude"
            % config["y_quantity"]
        )
    elif config["y_unit"] not in RECOGNIZED_AMPLITUDE_UNITS:
        out.append(
            "vertical axis is amplitude but its unit %s is not an amplitude unit"
            % config["y_unit"]
        )
    return out


def max_refresh_interval_s(sweep_time_s, min_updates_per_sweep=DEFAULT_MIN_UPDATES_PER_SWEEP):
    """Slowest refresh that still shows the sweep progressing on screen."""
    sweep = _scalar(sweep_time_s, "sweep_time_s")
    updates = _scalar(min_updates_per_sweep, "min_updates_per_sweep")
    if sweep <= 0.0:
        raise ValueError("sweep_time_s must be > 0, got %g" % sweep)
    if updates < 1.0:
        raise ValueError("min_updates_per_sweep must be >= 1, got %g" % updates)
    return sweep / updates


def updates_per_sweep(sweep_time_s, refresh_interval_s):
    """Whole plot updates the operator receives across one receiver sweep."""
    sweep = _scalar(sweep_time_s, "sweep_time_s")
    refresh = _scalar(refresh_interval_s, "refresh_interval_s")
    if sweep <= 0.0:
        raise ValueError("sweep_time_s must be > 0, got %g" % sweep)
    if refresh <= 0.0:
        raise ValueError("refresh_interval_s must be > 0, got %g" % refresh)
    return int(math.floor(sweep / refresh))


def refresh_is_live(refresh_interval_s, sweep_time_s, min_updates_per_sweep=DEFAULT_MIN_UPDATES_PER_SWEEP):
    """True when the refresh interval keeps the plot ahead of the sweep."""
    refresh = _scalar(refresh_interval_s, "refresh_interval_s")
    if refresh <= 0.0:
        raise ValueError("refresh_interval_s must be > 0, got %g" % refresh)
    bound = max_refresh_interval_s(sweep_time_s, min_updates_per_sweep)
    return at_most_time(refresh, bound)


def latency_is_current(display_latency_s, refresh_interval_s):
    """True when a plot arrives before the update that supersedes it."""
    latency = _scalar(display_latency_s, "display_latency_s")
    refresh = _scalar(refresh_interval_s, "refresh_interval_s")
    if latency < 0.0:
        raise ValueError("display_latency_s must be >= 0, got %g" % latency)
    if refresh <= 0.0:
        raise ValueError("refresh_interval_s must be > 0, got %g" % refresh)
    return at_most_time(latency, refresh)


def axis_span_shortfalls(presentation, band_start_hz, band_stop_hz):
    """Parts of the declared test band the displayed axis does not show."""
    start = _scalar(band_start_hz, "band_start_hz")
    stop = _scalar(band_stop_hz, "band_stop_hz")
    if start <= 0.0:
        raise ValueError("band_start_hz must be > 0, got %g" % start)
    if stop <= start:
        raise ValueError(
            "band_stop_hz (%g) must exceed band_start_hz (%g)" % (stop, start)
        )
    plot_start = _number(presentation, "plot_start_hz", "presentation")
    plot_stop = _number(presentation, "plot_stop_hz", "presentation")
    out = []
    if not at_most_freq(plot_start, start):
        out.append(
            "displayed axis starts at %g Hz, above the declared band start %g Hz"
            % (plot_start, start)
        )
    if not at_least_freq(plot_stop, stop):
        out.append(
            "displayed axis stops at %g Hz, below the declared band stop %g Hz"
            % (plot_stop, stop)
        )
    return out


def assess_emission_data_presentation(
    config,
    band_start_hz,
    band_stop_hz,
    sweep_time_s,
    min_updates_per_sweep=DEFAULT_MIN_UPDATES_PER_SWEEP,
):
    """Full clause 5.2.9.4 assessment of an emission plotting chain."""
    presentation = validate_presentation(config)
    mode = resolve_display_mode(
        presentation["automatic_generation"], presentation["displayed_during_run"]
    )
    axes = axis_findings(presentation)
    shortfalls = axis_span_shortfalls(presentation, band_start_hz, band_stop_hz)
    allowed_refresh = max_refresh_interval_s(sweep_time_s, min_updates_per_sweep)
    live_refresh = refresh_is_live(
        presentation["refresh_interval_s"], sweep_time_s, min_updates_per_sweep
    )
    current = latency_is_current(
        presentation["display_latency_s"], presentation["refresh_interval_s"]
    )
    seen = updates_per_sweep(sweep_time_s, presentation["refresh_interval_s"])

    findings = []
    if mode == MODE_OPERATOR:
        findings.append(
            "plots are produced only when an operator asks; the clause needs them "
            "produced automatically"
        )
    elif mode == MODE_DEFERRED:
        findings.append(
            "plots are produced automatically but only after the run; the clause "
            "needs them shown while the measurement proceeds"
        )
    findings.extend(axes)
    findings.extend(shortfalls)
    if not live_refresh:
        findings.append(
            "refresh interval %g s exceeds the %g s that keeps the display abreast "
            "of a %g s sweep"
            % (presentation["refresh_interval_s"], allowed_refresh, float(sweep_time_s))
        )

    limitations = []
    if not presentation["limit_line_shown"]:
        limitations.append(
            "no applicable limit line is overlaid, so an exceedance is not visible "
            "on the plot as it is drawn"
        )
    if not current:
        limitations.append(
            "display latency %g s exceeds the %g s refresh interval, so the plot on "
            "screen lags the data behind it"
            % (presentation["display_latency_s"], presentation["refresh_interval_s"])
        )

    return {
        "presentation": presentation,
        "display_mode": mode,
        "max_refresh_interval_s": allowed_refresh,
        "updates_per_sweep": seen,
        "refresh_is_live": live_refresh,
        "latency_is_current": current,
        "axis_findings": axes,
        "axis_span_shortfalls": shortfalls,
        "findings": findings,
        "limitations": limitations,
        "verdict": "presentation-compliant" if not findings else "presentation-deficient",
    }
