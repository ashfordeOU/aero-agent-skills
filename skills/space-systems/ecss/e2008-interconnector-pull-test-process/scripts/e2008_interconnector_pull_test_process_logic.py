"""Process of the interconnector pull test: a rising force at a defined speed.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.10.2 (pull-test process -- a force that
rises steadily on each interconnector tab, applied at a defined speed until the
joint gives way). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Check the crosshead speed each tab was pulled at against the declared speed
   window, since the speed is the one process variable the clause fixes.
2. Turn that speed into the force ramp rate the machine and the article
   compliance produce together, and from the ramp rate the time the pull takes
   to reach the expected parting force.
3. Check the instrumentation resolves that pull: the recorder places enough
   samples between zero and the peak for a rising ramp to be reconstructable,
   and the load cell range spans the peak without being so oversized that the
   force lands in its own noise floor.
4. Check each recorded force trace really rises: no pre-load on the first
   sample, and no dip on the way up, because a trace that unloads and reloads
   measures a second, weaker pull rather than the first one.
5. Reconcile the tabs pulled against the tabs planned, so a tab pulled twice or
   left unpulled is visible instead of absorbed into a count.
6. Report the derived rate, pull duration, sample count, load-cell use, every
   finding and the run verdict; the process is conformant only with no finding.
"""

import math

__all__ = [
    "RATE_TOLERANCE",
    "MIN_SAMPLES_TO_PEAK",
    "MIN_LOAD_CELL_UTILISATION",
    "MAX_PRELOAD_FRACTION",
    "SECONDS_PER_MINUTE",
    "validate_speed_window",
    "speed_findings",
    "ramp_rate_n_per_s",
    "time_to_peak_s",
    "samples_to_peak",
    "load_cell_utilisation",
    "instrumentation_findings",
    "trace_findings",
    "tab_reconciliation",
    "assess_pull_test_process",
]

SECONDS_PER_MINUTE = 60.0

# A speed or a rate sitting exactly on a declared bound is conformant; the
# comparison absorbs representation error and the bound itself never moves.
RATE_TOLERANCE = 1e-9

# Fewer points than this between zero and the parting force and the record
# shows that a force was reached, not that it rose steadily.
MIN_SAMPLES_TO_PEAK = 20

# A load cell whose range dwarfs the force reads the pull inside its own noise;
# the peak has to use at least this fraction of the range.
MIN_LOAD_CELL_UTILISATION = 0.05

# The first sample of a pull trace is the unloaded state; anything above this
# fraction of the peak means the tab was already carrying load.
MAX_PRELOAD_FRACTION = 0.02


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def _name(value, label):
    """Return a trimmed, non-empty identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("%s must not be empty" % label)
    return cleaned


def validate_speed_window(min_speed_mm_per_min, max_speed_mm_per_min):
    """Return the validated (slowest, fastest) crosshead speed pair."""
    slowest = _positive(min_speed_mm_per_min, "min_speed_mm_per_min")
    fastest = _positive(max_speed_mm_per_min, "max_speed_mm_per_min")
    if fastest < slowest:
        raise ValueError(
            "max speed %g must not be below the min speed %g" % (fastest, slowest)
        )
    return (slowest, fastest)


def speed_findings(records, window):
    """Return findings for every tab pulled outside the declared speed window."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of pull records")
    slowest, fastest = validate_speed_window(window[0], window[1])
    findings = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each pull record must be a mapping")
        for key in ("tab", "speed_mm_per_min"):
            if key not in record:
                raise ValueError("pull record missing key '%s'" % key)
        tab = _name(record["tab"], "tab")
        speed = _positive(record["speed_mm_per_min"], "speed_mm_per_min")
        if speed < slowest - RATE_TOLERANCE:
            findings.append(
                "tab '%s' was pulled at %g mm/min, under the %g mm/min floor"
                % (tab, speed, slowest)
            )
        elif speed > fastest + RATE_TOLERANCE:
            findings.append(
                "tab '%s' was pulled at %g mm/min, over the %g mm/min ceiling"
                % (tab, speed, fastest)
            )
    return findings


def ramp_rate_n_per_s(speed_mm_per_min, stiffness_n_per_mm):
    """Return the force ramp rate the crosshead speed produces, in newtons/s."""
    speed = _positive(speed_mm_per_min, "speed_mm_per_min")
    stiffness = _positive(stiffness_n_per_mm, "stiffness_n_per_mm")
    return speed / SECONDS_PER_MINUTE * stiffness


def time_to_peak_s(peak_force_n, rate_n_per_s):
    """Return the time a steady ramp takes to reach the parting force."""
    peak = _positive(peak_force_n, "peak_force_n")
    rate = _positive(rate_n_per_s, "rate_n_per_s")
    return peak / rate


def samples_to_peak(duration_s, sample_rate_hz):
    """Return how many samples the recorder places on the rising ramp."""
    duration = _positive(duration_s, "duration_s")
    rate = _positive(sample_rate_hz, "sample_rate_hz")
    return duration * rate


def load_cell_utilisation(peak_force_n, load_cell_range_n):
    """Return the fraction of the load cell range the parting force uses."""
    peak = _positive(peak_force_n, "peak_force_n")
    span = _positive(load_cell_range_n, "load_cell_range_n")
    return peak / span


def instrumentation_findings(peak_force_n, rate_n_per_s, sample_rate_hz,
                             load_cell_range_n,
                             min_samples=MIN_SAMPLES_TO_PEAK,
                             min_utilisation=MIN_LOAD_CELL_UTILISATION):
    """Return findings where the recorder or the load cell cannot see the pull."""
    if not isinstance(min_samples, int) or isinstance(min_samples, bool):
        raise ValueError("min_samples must be an integer, got %r" % (min_samples,))
    if min_samples < 2:
        raise ValueError("min_samples must be at least 2, got %d" % min_samples)
    floor = _positive(min_utilisation, "min_utilisation")
    if floor >= 1.0:
        raise ValueError("min_utilisation must be below 1.0, got %g" % floor)
    duration = time_to_peak_s(peak_force_n, rate_n_per_s)
    count = samples_to_peak(duration, sample_rate_hz)
    usage = load_cell_utilisation(peak_force_n, load_cell_range_n)
    findings = []
    if count < min_samples - RATE_TOLERANCE:
        findings.append(
            "the recorder places %.1f samples on the rising ramp, under the %d "
            "a steady rise needs" % (count, min_samples)
        )
    if usage > 1.0 + RATE_TOLERANCE:
        findings.append(
            "the parting force is %.1f%% of the load cell range, so the cell "
            "saturates before the joint parts" % (usage * 100.0)
        )
    elif usage < floor - RATE_TOLERANCE:
        findings.append(
            "the parting force uses only %.2f%% of the load cell range, under "
            "the %.2f%% the cell resolves" % (usage * 100.0, floor * 100.0)
        )
    return findings


def trace_findings(trace, tab="tab",
                   max_preload_fraction=MAX_PRELOAD_FRACTION):
    """Return findings where a recorded force trace does not rise steadily."""
    label = _name(tab, "tab")
    if not isinstance(trace, (list, tuple)) or len(trace) < 2:
        raise ValueError("trace must hold at least two (time_s, force_n) points")
    fraction = _positive(max_preload_fraction, "max_preload_fraction")
    if fraction >= 1.0:
        raise ValueError(
            "max_preload_fraction must be below 1.0, got %g" % fraction
        )
    times = []
    forces = []
    for point in trace:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("each trace point must be a (time_s, force_n) pair")
        times.append(_non_negative(point[0], "trace time_s"))
        forces.append(_non_negative(point[1], "trace force_n"))
    for earlier, later in zip(times, times[1:]):
        if later <= earlier:
            raise ValueError("trace times must strictly increase")
    peak = max(forces)
    if peak <= 0.0:
        raise ValueError("a trace must reach a force above zero")
    peak_index = forces.index(peak)
    findings = []
    if forces[0] > peak * fraction + RATE_TOLERANCE:
        findings.append(
            "tab '%s' carried %g N before the pull began, so the trace starts "
            "pre-loaded" % (label, forces[0])
        )
    for index in range(1, peak_index + 1):
        if forces[index] < forces[index - 1] - RATE_TOLERANCE:
            findings.append(
                "tab '%s' unloaded from %g N to %g N on the way up, so the "
                "force did not rise steadily"
                % (label, forces[index - 1], forces[index])
            )
            break
    return findings


def tab_reconciliation(planned_tabs, pulled_tabs):
    """Return the missing, unplanned and repeated tabs of a pull run."""
    for label, value in (("planned_tabs", planned_tabs),
                         ("pulled_tabs", pulled_tabs)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a sequence of tab names" % label)
    planned = [_name(item, "planned tab") for item in planned_tabs]
    pulled = [_name(item, "pulled tab") for item in pulled_tabs]
    if not planned:
        raise ValueError("planned_tabs must name at least one tab")
    repeated = sorted({tab for tab in pulled if pulled.count(tab) > 1})
    missing = [tab for tab in planned if tab not in pulled]
    unplanned = sorted({tab for tab in pulled if tab not in planned})
    return {
        "missing": missing,
        "unplanned": unplanned,
        "repeated": repeated,
    }


def assess_pull_test_process(spec):
    """Run the full clause 6.4.3.10.2 pull-test process check.

    spec keys: planned_tabs, pull_records (tab, speed_mm_per_min,
    peak_force_n, trace), speed_window_mm_per_min (pair), stiffness_n_per_mm,
    sample_rate_hz, load_cell_range_n; optional min_samples, min_utilisation,
    max_preload_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "planned_tabs",
        "pull_records",
        "speed_window_mm_per_min",
        "stiffness_n_per_mm",
        "sample_rate_hz",
        "load_cell_range_n",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    window = spec["speed_window_mm_per_min"]
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError(
            "speed_window_mm_per_min must be a (slowest, fastest) pair"
        )
    records = spec["pull_records"]
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("pull_records must be a non-empty sequence")

    findings = list(speed_findings(records, window))
    tab_report = tab_reconciliation(
        spec["planned_tabs"], [record["tab"] for record in records]
    )
    for tab in tab_report["missing"]:
        findings.append("planned tab '%s' was never pulled" % tab)
    for tab in tab_report["repeated"]:
        findings.append(
            "tab '%s' carries two pull records, so its result is ambiguous" % tab
        )
    for tab in tab_report["unplanned"]:
        findings.append("tab '%s' was pulled but is not on the plan" % tab)

    per_tab = []
    for record in records:
        for key in ("peak_force_n", "trace"):
            if key not in record:
                raise ValueError("pull record missing key '%s'" % key)
        tab = _name(record["tab"], "tab")
        rate = ramp_rate_n_per_s(
            record["speed_mm_per_min"], spec["stiffness_n_per_mm"]
        )
        duration = time_to_peak_s(record["peak_force_n"], rate)
        count = samples_to_peak(duration, spec["sample_rate_hz"])
        tab_findings = instrumentation_findings(
            record["peak_force_n"],
            rate,
            spec["sample_rate_hz"],
            spec["load_cell_range_n"],
            spec.get("min_samples", MIN_SAMPLES_TO_PEAK),
            spec.get("min_utilisation", MIN_LOAD_CELL_UTILISATION),
        )
        tab_findings.extend(
            trace_findings(
                record["trace"],
                tab,
                spec.get("max_preload_fraction", MAX_PRELOAD_FRACTION),
            )
        )
        for item in tab_findings:
            findings.append(item if item.startswith("tab '") else
                            "tab '%s': %s" % (tab, item))
        per_tab.append({
            "tab": tab,
            "ramp_rate_n_per_s": rate,
            "duration_s": duration,
            "samples_to_peak": count,
            "load_cell_utilisation": load_cell_utilisation(
                record["peak_force_n"], spec["load_cell_range_n"]
            ),
            "findings": tab_findings,
        })
    return {
        "tabs": per_tab,
        "reconciliation": tab_report,
        "pulled_count": len(records),
        "planned_count": len(spec["planned_tabs"]),
        "findings": findings,
        "process_conformant": not findings,
    }
