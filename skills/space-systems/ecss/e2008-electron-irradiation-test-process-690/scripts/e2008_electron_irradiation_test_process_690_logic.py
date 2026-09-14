#!/usr/bin/env python3
"""Process for the one megaelectronvolt electron irradiation of planar blocking diodes.

Anchor: ECSS-E-ST-20-08C clause 12.6.11.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause puts planar blocking diodes in front of a one
megaelectronvolt electron beam and says the method is the stated one.
Everything that follows is what "the stated method" has to be checked
against once the run is over.

A run is not one exposure. It is a ladder of fluence points, and at each
point the parts come out of the beam and are measured, so the campaign
ends with a degradation curve rather than a single before-and-after
pair. That shape is what the checks below are built around:

    beam        energy near the nominal electron, flux inside the
                window the method allows
    ladder      cumulative fluence points that actually rise, each one
                reached by the flux that was delivered for the time it
                ran
    readouts    a forward drop and a reverse leakage either side of
                every step, on the irradiated parts and on a control
                part that never entered the beam
    verdict     one disposition naming every finding, not the first

Two details carry most of the weight. The bias condition the parts are
held at during exposure changes the damage a given fluence does, so it
is declared, recognised and held the same across the ladder, or the
steps are not points on one curve. And the control part exists because
a forward drop that drifts by a few millivolts on the bench looks
exactly like a small radiation effect; without an unirradiated part
carried through the same readouts, instrument drift is read as damage.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BIAS_SHORTED = "terminals-shorted"
BIAS_REVERSE = "reverse-biased"
BIAS_FORWARD = "forward-biased"
_BIAS_CONDITIONS = (BIAS_SHORTED, BIAS_REVERSE, BIAS_FORWARD)

RUN_NOT_PERFORMED = "electron-irradiation-run-not-performed"
RUN_BEAM_OUTSIDE_METHOD = "electron-irradiation-beam-outside-the-stated-method"
RUN_LADDER_INVALID = "electron-irradiation-fluence-ladder-invalid"
RUN_CHARACTERISATION_INCOMPLETE = "electron-irradiation-characterisation-incomplete"
RUN_ACCEPTED = "electron-irradiation-run-accepted"

DEFAULT_RUN_POLICY = {
    "nominal_energy_mev": 1.0,
    "energy_tolerance_mev": 0.05,
    "min_flux_per_cm2_s": 1.0e9,
    "max_flux_per_cm2_s": 1.0e11,
    "fluence_match_tolerance_fraction": 0.10,
    "max_control_drift_fraction": 0.02,
    "min_sample_count": 5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _strictly_above(value, other):
    """A rise that survives representation error, not a tie dressed up as one."""
    return value > other and not math.isclose(
        value, other, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_run_policy(policy):
    """Check the irradiation-run policy is complete and internally consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("nominal_energy_mev", policy.get("nominal_energy_mev"))
    _require_positive("energy_tolerance_mev", policy.get("energy_tolerance_mev"))
    low = _require_positive("min_flux_per_cm2_s", policy.get("min_flux_per_cm2_s"))
    high = _require_positive("max_flux_per_cm2_s", policy.get("max_flux_per_cm2_s"))
    if not high > low:
        raise ValueError(
            "max_flux_per_cm2_s %g must be above min_flux_per_cm2_s %g"
            % (high, low)
        )
    _require_fraction(
        "fluence_match_tolerance_fraction",
        policy.get("fluence_match_tolerance_fraction"),
    )
    _require_fraction(
        "max_control_drift_fraction", policy.get("max_control_drift_fraction")
    )
    count = _require_count("min_sample_count", policy.get("min_sample_count"))
    if count < 1:
        raise ValueError("min_sample_count must be at least one part")
    return policy


def beam_energy_error_mev(measured_energy_mev, policy=DEFAULT_RUN_POLICY):
    """How far the beam sits from the nominal electron the method names."""
    validate_run_policy(policy)
    measured = _require_positive("measured_energy_mev", measured_energy_mev)
    return measured - float(policy["nominal_energy_mev"])


def beam_energy_within_method(measured_energy_mev, policy=DEFAULT_RUN_POLICY):
    """True when the beam energy sits inside the method's tolerance band."""
    error = abs(beam_energy_error_mev(measured_energy_mev, policy))
    return _at_most(error, float(policy["energy_tolerance_mev"]))


def flux_within_window(flux_per_cm2_s, policy=DEFAULT_RUN_POLICY):
    """True when the delivered flux sits inside the allowed rate window."""
    validate_run_policy(policy)
    flux = _require_positive("flux_per_cm2_s", flux_per_cm2_s)
    return _at_least(flux, float(policy["min_flux_per_cm2_s"])) and _at_most(
        flux, float(policy["max_flux_per_cm2_s"])
    )


def validate_segment(segment):
    """Refuse an exposure segment that states no rate or no duration."""
    if not isinstance(segment, dict):
        raise ValueError("segment must be a mapping, got %r" % (segment,))
    _require_positive("flux_per_cm2_s", segment.get("flux_per_cm2_s"))
    _require_positive("duration_s", segment.get("duration_s"))
    return segment


def segment_fluence(segment):
    """Fluence one exposure segment delivers: its rate over its own duration."""
    validate_segment(segment)
    return float(segment["flux_per_cm2_s"]) * float(segment["duration_s"])


def delivered_fluence(step):
    """Fluence a ladder step actually delivered, summed over its segments."""
    if not isinstance(step, dict):
        raise ValueError("step must be a mapping, got %r" % (step,))
    segments = step.get("segments")
    if not isinstance(segments, (list, tuple)) or not segments:
        raise ValueError(
            "a ladder step needs at least one exposure segment; an unexposed "
            "step delivered nothing, not an unknown amount"
        )
    return sum(segment_fluence(segment) for segment in segments)


def validate_step(step):
    """Refuse a ladder step missing its target, bias state or either readout."""
    if not isinstance(step, dict):
        raise ValueError("step must be a mapping, got %r" % (step,))
    _require_positive(
        "target_fluence_per_cm2", step.get("target_fluence_per_cm2")
    )
    bias = step.get("bias_condition")
    if bias not in _BIAS_CONDITIONS:
        raise ValueError(
            "bias_condition must be one of %s, got %r"
            % (list(_BIAS_CONDITIONS), bias)
        )
    delivered_fluence(step)
    for key in (
        "pre_forward_drop_v",
        "post_forward_drop_v",
        "pre_reverse_leakage_ua",
        "post_reverse_leakage_ua",
    ):
        if key not in step:
            raise ValueError(
                "step is missing %s; a step with no readout either side of it "
                "is not a point on a degradation curve" % (key,)
            )
        _require_positive(key, step[key])
    return step


def cumulative_fluence(steps):
    """Running total of delivered fluence after each ladder step."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of ladder steps")
    totals = []
    running = 0.0
    for step in steps:
        validate_step(step)
        running += delivered_fluence(step)
        totals.append(running)
    return tuple(totals)


def ladder_rises(steps):
    """True when every target fluence sits genuinely above the one before it."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of ladder steps")
    targets = [float(validate_step(step)["target_fluence_per_cm2"]) for step in steps]
    return all(
        _strictly_above(later, earlier)
        for earlier, later in zip(targets, targets[1:])
    )


def bias_conditions(steps):
    """Every distinct bias state the ladder was run under, in order of first use."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of ladder steps")
    seen = []
    for step in steps:
        bias = validate_step(step)["bias_condition"]
        if bias not in seen:
            seen.append(bias)
    return tuple(seen)


def fluence_reconciliation_error(target_fluence_per_cm2, delivered_fluence_per_cm2):
    """Signed shortfall or overshoot against a planned fluence point, as a fraction."""
    target = _require_positive("target_fluence_per_cm2", target_fluence_per_cm2)
    delivered = _require_non_negative(
        "delivered_fluence_per_cm2", delivered_fluence_per_cm2
    )
    return (delivered - target) / target


def ladder_reconciliation_errors(steps):
    """Per-step error between the fluence actually reached and its planned point."""
    totals = cumulative_fluence(steps)
    return tuple(
        fluence_reconciliation_error(float(step["target_fluence_per_cm2"]), total)
        for step, total in zip(steps, totals)
    )


def forward_drop_rise_v(step):
    """How much the forward drop grew across one step."""
    validate_step(step)
    return float(step["post_forward_drop_v"]) - float(step["pre_forward_drop_v"])


def leakage_growth_ratio(step):
    """How many times the reverse leakage multiplied across one step."""
    validate_step(step)
    return float(step["post_reverse_leakage_ua"]) / float(
        step["pre_reverse_leakage_ua"]
    )


def control_drift_fraction(control):
    """Relative movement of the unirradiated control part's forward drop."""
    if not isinstance(control, dict):
        raise ValueError("control must be a mapping, got %r" % (control,))
    before = _require_positive(
        "pre_forward_drop_v", control.get("pre_forward_drop_v")
    )
    after = _require_positive(
        "post_forward_drop_v", control.get("post_forward_drop_v")
    )
    return abs(after - before) / before


def assess_irradiation_run(case, policy=DEFAULT_RUN_POLICY):
    """Full clause 12.6.11.2.2 judgement for one planar blocking diode run."""
    validate_run_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    steps = case.get("steps")
    if steps is None:
        raise ValueError(
            "case is missing steps; an absent ladder is not an empty one"
        )
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a sequence of ladder steps")

    findings = []
    result = {
        "step_count": len(steps),
        "cumulative_fluence_per_cm2": (),
        "bias_conditions": (),
        "beam_energy_error_mev": None,
        "forward_drop_rise_v": None,
        "leakage_growth_ratio": None,
        "control_drift_fraction": None,
        "findings": findings,
    }

    if not steps:
        findings.append(
            "the run holds no fluence step; a degradation curve is not drawn "
            "through an empty ladder"
        )
        result["verdict"] = RUN_NOT_PERFORMED
        return result

    sample_count = _require_count("sample_count", case.get("sample_count", 0))
    if not _at_least(sample_count, policy["min_sample_count"]):
        findings.append(
            "the run carried %d part(s) against the %d the method asks for"
            % (sample_count, policy["min_sample_count"])
        )

    measured_energy = case.get("measured_energy_mev")
    if measured_energy is None:
        raise ValueError(
            "case is missing measured_energy_mev; the method is named by its "
            "electron energy and an unrecorded beam cannot be checked against it"
        )
    energy_error = beam_energy_error_mev(measured_energy, policy)
    result["beam_energy_error_mev"] = energy_error
    beam_ok = beam_energy_within_method(measured_energy, policy)
    if not beam_ok:
        findings.append(
            "the beam ran at %.4f MeV, %.4f MeV off the nominal electron and "
            "outside the %.4f MeV the method allows"
            % (
                float(measured_energy),
                energy_error,
                float(policy["energy_tolerance_mev"]),
            )
        )

    out_of_window = []
    for index, step in enumerate(steps, start=1):
        validate_step(step)
        for segment in step["segments"]:
            if not flux_within_window(segment["flux_per_cm2_s"], policy):
                out_of_window.append((index, float(segment["flux_per_cm2_s"])))
    if out_of_window:
        beam_ok = False
        findings.append(
            "%d exposure segment(s) ran outside the rate window, first at step "
            "%d with %.4g particles per square centimetre per second"
            % (len(out_of_window), out_of_window[0][0], out_of_window[0][1])
        )

    result["cumulative_fluence_per_cm2"] = cumulative_fluence(steps)
    result["bias_conditions"] = bias_conditions(steps)

    ladder_ok = True
    if not ladder_rises(steps):
        ladder_ok = False
        findings.append(
            "the target fluences do not rise across the ladder, so the steps "
            "are not successive points on one degradation curve"
        )
    if len(result["bias_conditions"]) > 1:
        ladder_ok = False
        findings.append(
            "the ladder was run under %d different bias conditions (%s); a "
            "given fluence does not do the same damage under each"
            % (
                len(result["bias_conditions"]),
                ", ".join(result["bias_conditions"]),
            )
        )
    tolerance = float(policy["fluence_match_tolerance_fraction"])
    for index, error in enumerate(ladder_reconciliation_errors(steps), start=1):
        if not _at_most(abs(error), tolerance):
            ladder_ok = False
            findings.append(
                "step %d delivered %.4f of its target off, against the %.4f "
                "the method tolerates" % (index, error, tolerance)
            )

    last = steps[-1]
    first = steps[0]
    result["forward_drop_rise_v"] = float(last["post_forward_drop_v"]) - float(
        first["pre_forward_drop_v"]
    )
    result["leakage_growth_ratio"] = float(
        last["post_reverse_leakage_ua"]
    ) / float(first["pre_reverse_leakage_ua"])

    characterisation_ok = True
    control = case.get("control_part")
    if control is None:
        characterisation_ok = False
        findings.append(
            "no unirradiated control part was carried through the readouts, so "
            "bench drift cannot be separated from radiation effect"
        )
    else:
        drift = control_drift_fraction(control)
        result["control_drift_fraction"] = drift
        if not _at_most(drift, float(policy["max_control_drift_fraction"])):
            characterisation_ok = False
            findings.append(
                "the control part moved by %.4f of its forward drop against the "
                "%.4f allowed, so the readouts carry bench drift"
                % (drift, float(policy["max_control_drift_fraction"]))
            )

    if not beam_ok:
        result["verdict"] = RUN_BEAM_OUTSIDE_METHOD
        return result
    if not ladder_ok:
        result["verdict"] = RUN_LADDER_INVALID
        return result
    if not characterisation_ok or findings:
        result["verdict"] = RUN_CHARACTERISATION_INCOMPLETE
        return result

    result["verdict"] = RUN_ACCEPTED
    return result
