"""Time-domain simulation setup sizing for die-form MMIC switching analysis.

Anchor: ECSS-Q-ST-60-12C clause 7.2.4 (transient simulation -- covering the
switch-on, switch-off and other time-varying behaviour of the circuit).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared transient events (switch-on, switch-off, bias step,
   pulse edges) and the settling time constants of the circuit.
2. Derive the spectral content of the fastest edge from its rise time, and from
   that the maximum integration timestep that still resolves the edge to the
   required number of points.
3. Derive the simulation stop time from the slowest settling time constant and
   the residual error the analysis has to demonstrate, and from the schedule of
   the declared events, whichever reaches further.
4. Convert timestep and stop time into a step count and grade it against the
   run budget, so an unaffordable setup is reported before it is launched
   rather than after it has run overnight.
5. Assess the switching stress the run has to capture: the peak inrush drawn
   into the load capacitance through the source resistance, the energy that
   capacitance stores, and the supply slew rate the edge imposes.
6. Report findings for an edge that is under-resolved, a window that truncates
   settling, an event schedule that leaves the window, a missing switch-off
   event, and a step count over budget.
"""

import math

__all__ = [
    "KNEE_CONSTANT",
    "MIN_POINTS_PER_EDGE",
    "MIN_OVERSAMPLE_FACTOR",
    "TIME_TOLERANCE_NS",
    "validate_positive",
    "validate_fraction",
    "knee_frequency_ghz",
    "max_timestep_ps",
    "settling_time_ns",
    "sample_rate_ghz",
    "required_steps",
    "inrush_peak_a",
    "stored_energy_nj",
    "supply_slew_rate_v_per_ns",
    "validate_event_schedule",
    "assess_transient_simulation",
]

# Rise-time to spectral-knee constant for a monotonic edge: f_knee = 0.35 / t_r.
KNEE_CONSTANT = 0.35

# An edge resolved by fewer points than this is a straight line in the run, and
# the overshoot and ringing the analysis exists to find are simply absent.
MIN_POINTS_PER_EDGE = 10

# The sample rate implied by the timestep must clear the knee by this factor,
# not merely satisfy Nyquist, because the edge carries energy above the knee.
MIN_OVERSAMPLE_FACTOR = 5.0

# Window and settling comparisons are differences of computed floats; a case
# that is physically exactly on the limit can land a few ULPs on the wrong
# side. Absorb the representation error here, not by shortening the window.
TIME_TOLERANCE_NS = 1e-9

_EVENT_KINDS = ("switch_on", "switch_off", "bias_step", "pulse_edge")


def validate_positive(label, value):
    """Return value as a strictly positive finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return number


def validate_fraction(label, value):
    """Return value as a float strictly inside (0, 1), or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0 or number >= 1.0:
        raise ValueError("%s must lie strictly inside (0, 1), got %r" % (label, value))
    return number


def knee_frequency_ghz(rise_time_ps):
    """Return the spectral knee in GHz of an edge with the given rise time."""
    rise = validate_positive("rise_time_ps", rise_time_ps)
    return KNEE_CONSTANT * 1000.0 / rise


def max_timestep_ps(rise_time_ps, points_per_edge=MIN_POINTS_PER_EDGE):
    """Return the largest timestep in ps that still resolves the edge."""
    rise = validate_positive("rise_time_ps", rise_time_ps)
    if not isinstance(points_per_edge, int) or isinstance(points_per_edge, bool):
        raise ValueError("points_per_edge must be an integer, got %r" % (points_per_edge,))
    if points_per_edge < MIN_POINTS_PER_EDGE:
        raise ValueError(
            "points_per_edge must be at least %d to resolve an edge, got %d"
            % (MIN_POINTS_PER_EDGE, points_per_edge)
        )
    return rise / float(points_per_edge)


def settling_time_ns(time_constant_ns, residual_error_fraction):
    """Return the time in ns for a first-order decay to reach the residual error."""
    tau = validate_positive("time_constant_ns", time_constant_ns)
    error = validate_fraction("residual_error_fraction", residual_error_fraction)
    return tau * math.log(1.0 / error)


def sample_rate_ghz(timestep_ps):
    """Return the sample rate in GHz implied by an integration timestep."""
    step = validate_positive("timestep_ps", timestep_ps)
    return 1000.0 / step


def required_steps(stop_time_ns, timestep_ps):
    """Return the number of integration steps a run of this length needs."""
    stop = validate_positive("stop_time_ns", stop_time_ns)
    step = validate_positive("timestep_ps", timestep_ps)
    return int(math.ceil(stop * 1000.0 / step))


def inrush_peak_a(supply_v, source_resistance_ohm):
    """Return the peak inrush current in A drawn through the source resistance."""
    volts = validate_positive("supply_v", supply_v)
    ohms = validate_positive("source_resistance_ohm", source_resistance_ohm)
    return volts / ohms


def stored_energy_nj(capacitance_pf, supply_v):
    """Return the energy in nJ stored in the load capacitance at full supply."""
    farads = validate_positive("capacitance_pf", capacitance_pf) * 1.0e-12
    volts = validate_positive("supply_v", supply_v)
    return 0.5 * farads * volts * volts * 1.0e9


def supply_slew_rate_v_per_ns(supply_v, rise_time_ps):
    """Return the supply slew rate in V/ns imposed by the switching edge."""
    volts = validate_positive("supply_v", supply_v)
    rise = validate_positive("rise_time_ps", rise_time_ps)
    return volts / (rise / 1000.0)


def validate_event_schedule(events, window_ns):
    """Return the declared events sorted in time, all inside the window.

    Each event is a mapping with 'kind' (one of the recognised transient kinds)
    and 'time_ns'. Raises on an unknown kind, a duplicate time, or an event
    that falls outside the simulation window.
    """
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("events must be a non-empty sequence")
    window = validate_positive("window_ns", window_ns)
    ordered = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError("events[%d] must be a mapping" % index)
        kind = event.get("kind")
        if kind not in _EVENT_KINDS:
            raise ValueError(
                "events[%d] has unknown kind %r; use one of %s"
                % (index, kind, ", ".join(_EVENT_KINDS))
            )
        time_ns = event.get("time_ns")
        if not isinstance(time_ns, (int, float)) or isinstance(time_ns, bool):
            raise ValueError("events[%d] needs a real 'time_ns'" % index)
        moment = float(time_ns)
        if not math.isfinite(moment) or moment < 0.0:
            raise ValueError("events[%d] time_ns must be finite and non-negative" % index)
        if moment > window + TIME_TOLERANCE_NS:
            raise ValueError(
                "events[%d] at %g ns falls outside the %g ns simulation window"
                % (index, moment, window)
            )
        ordered.append({"kind": kind, "time_ns": moment})
    ordered.sort(key=lambda item: item["time_ns"])
    for i in range(1, len(ordered)):
        if math.isclose(
            ordered[i]["time_ns"], ordered[i - 1]["time_ns"], rel_tol=0.0, abs_tol=TIME_TOLERANCE_NS
        ):
            raise ValueError(
                "two events share the time %g ns; give each edge a distinct moment"
                % ordered[i]["time_ns"]
            )
    return ordered


def assess_transient_simulation(spec):
    """Run the full clause 7.2.4 transient-simulation setup assessment.

    spec keys: rise_time_ps, slowest_time_constant_ns, residual_error_fraction,
    events, supply_v, load_capacitance_pf, source_resistance_ohm,
    max_steps; optional points_per_edge, oversample_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "rise_time_ps",
        "slowest_time_constant_ns",
        "residual_error_fraction",
        "events",
        "supply_v",
        "load_capacitance_pf",
        "source_resistance_ohm",
        "max_steps",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    rise = validate_positive("rise_time_ps", spec["rise_time_ps"])
    tau = validate_positive("slowest_time_constant_ns", spec["slowest_time_constant_ns"])
    error = validate_fraction("residual_error_fraction", spec["residual_error_fraction"])
    max_steps = spec["max_steps"]
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
        raise ValueError("max_steps must be a positive integer, got %r" % (max_steps,))
    points_per_edge = spec.get("points_per_edge", MIN_POINTS_PER_EDGE)
    oversample = validate_positive("oversample_factor", spec.get("oversample_factor", MIN_OVERSAMPLE_FACTOR))

    timestep = max_timestep_ps(rise, points_per_edge)
    knee = knee_frequency_ghz(rise)
    rate = sample_rate_ghz(timestep)
    settle = settling_time_ns(tau, error)

    # The window has to reach past the last declared event by a full settling
    # time, or the run stops while the circuit is still moving. A caller may
    # declare its own window; the assessment then grades that window rather
    # than silently replacing it with a sufficient one.
    probe = sorted(
        float(e.get("time_ns", 0.0)) for e in spec["events"]
        if isinstance(e, dict) and isinstance(e.get("time_ns"), (int, float))
        and not isinstance(e.get("time_ns"), bool)
    )
    last_event = probe[-1] if probe else 0.0
    needed_stop = last_event + settle
    if spec.get("window_ns") is None:
        stop_time = needed_stop
    else:
        stop_time = validate_positive("window_ns", spec["window_ns"])
    events = validate_event_schedule(spec["events"], stop_time)

    steps = required_steps(stop_time, timestep)
    inrush = inrush_peak_a(spec["supply_v"], spec["source_resistance_ohm"])
    energy = stored_energy_nj(spec["load_capacitance_pf"], spec["supply_v"])
    slew = supply_slew_rate_v_per_ns(spec["supply_v"], rise)

    kinds = set(event["kind"] for event in events)
    findings = []
    if rate < oversample * knee - TIME_TOLERANCE_NS:
        findings.append(
            "timestep of %.4f ps samples at %.3f GHz, below the %.3f GHz needed to "
            "clear the %.3f GHz edge knee by %.1f times"
            % (timestep, rate, oversample * knee, knee, oversample)
        )
    if "switch_on" not in kinds:
        findings.append("no switch-on event was declared; turn-on behaviour is not covered")
    if "switch_off" not in kinds:
        findings.append(
            "no switch-off event was declared; turn-off is the stressing edge for an "
            "inductive or charged load and is not covered"
        )
    if needed_stop > stop_time + TIME_TOLERANCE_NS:
        findings.append(
            "the %g ns window ends %g ns before the last event has settled to the "
            "required residual" % (stop_time, needed_stop - stop_time)
        )
    if steps > max_steps:
        findings.append(
            "the setup needs %d integration steps against a budget of %d; refine the "
            "timestep locally around the edges instead of globally" % (steps, max_steps)
        )

    return {
        "knee_frequency_ghz": knee,
        "timestep_ps": timestep,
        "sample_rate_ghz": rate,
        "settling_time_ns": settle,
        "stop_time_ns": stop_time,
        "required_steps": steps,
        "needed_stop_time_ns": needed_stop,
        "max_steps": max_steps,
        "events": events,
        "event_kinds": sorted(kinds),
        "inrush_peak_a": inrush,
        "stored_energy_nj": energy,
        "supply_slew_rate_v_per_ns": slew,
        "findings": findings,
        "adequate": not findings,
    }
