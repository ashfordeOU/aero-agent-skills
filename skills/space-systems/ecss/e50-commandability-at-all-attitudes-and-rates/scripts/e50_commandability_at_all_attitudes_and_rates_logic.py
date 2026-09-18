#!/usr/bin/env python3
"""Commandability at all attitudes and rates, ECSS-E-ST-50C clause 5.4.1.

Paraphrased requirement, no standard text reproduced. The clause places one
obligation on the telecommand chain: the spacecraft has to remain commandable
whatever attitude it is in and whatever rate it is turning at. This module
turns that into two computations that can actually fail:

  gain sample + uplink budget  -> received power and margin in that direction
  margin over the sphere       -> the directions with no command link at all
  solid-angle weighting        -> the fraction of attitudes that are covered
  body rate + beam geometry    -> the dwell the receiver gets in the beam
  dwell vs. acquisition + frame -> the rate above which commanding stops

Attitude coverage and rate capability are separate failures with separate
fixes, so they are reported separately and combined only in the verdict.

Margins are sums of decibel quantities and dwell times are simple ratios;
every comparison against a bound carries an explicit tolerance so a design
that lands exactly on its bound reads the same on every host.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibels of slack when a margin lands on its required value.
MARGIN_TOLERANCE_DB = 1e-9

# Seconds of slack when a dwell lands on the time the receiver needs.
TIME_TOLERANCE_S = 1e-9

# Required link margin, in dB, when a project states none.
DEFAULT_REQUIRED_MARGIN_DB = 3.0

# Verdict tokens.
COMMANDABLE = "commandable-at-all-attitudes-and-rates"
ATTITUDE_GAP = "attitude-coverage-gap"
RATE_LIMITED = "rate-limited"
ATTITUDE_AND_RATE = "attitude-gap-and-rate-limited"
VERDICTS = (COMMANDABLE, ATTITUDE_GAP, RATE_LIMITED, ATTITUDE_AND_RATE)

_SAMPLE_KEYS = ("theta_deg", "phi_deg", "gain_dbi")
_BUDGET_KEYS = ("eirp_dbw", "path_loss_db", "other_losses_db", "sensitivity_dbw")


def _number(value, name):
    """Return value as a finite float, refusing bools, text and NaN."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return number


def _positive(value, name):
    """Return value as a finite float strictly above zero."""
    number = _number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be above zero, got %r" % (name, value))
    return number


def _non_negative(value, name):
    """Return value as a finite float at or above zero."""
    number = _number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_direction(sample):
    """Validate one antenna gain sample and return it normalized."""
    if not isinstance(sample, dict):
        raise ValueError("gain sample must be a mapping, got %r" % (sample,))
    missing = [key for key in _SAMPLE_KEYS if key not in sample]
    if missing:
        raise ValueError("gain sample is missing keys: %s" % ", ".join(missing))
    theta = _number(sample["theta_deg"], "theta_deg")
    phi = _number(sample["phi_deg"], "phi_deg")
    if theta < 0.0 or theta > 180.0:
        raise ValueError("theta_deg must lie in 0..180, got %r" % (theta,))
    if phi < 0.0 or phi >= 360.0:
        raise ValueError("phi_deg must lie in 0..360 exclusive of 360, got %r" % (phi,))
    return {
        "theta_deg": theta,
        "phi_deg": phi,
        "gain_dbi": _number(sample["gain_dbi"], "gain_dbi"),
    }


def validate_uplink_budget(budget):
    """Validate the uplink budget terms shared by every direction."""
    if not isinstance(budget, dict):
        raise ValueError("uplink budget must be a mapping, got %r" % (budget,))
    missing = [key for key in _BUDGET_KEYS if key not in budget]
    if missing:
        raise ValueError("uplink budget is missing keys: %s" % ", ".join(missing))
    return {
        "eirp_dbw": _number(budget["eirp_dbw"], "eirp_dbw"),
        "path_loss_db": _non_negative(budget["path_loss_db"], "path_loss_db"),
        "other_losses_db": _non_negative(budget["other_losses_db"], "other_losses_db"),
        "sensitivity_dbw": _number(budget["sensitivity_dbw"], "sensitivity_dbw"),
    }


def received_power_dbw(gain_dbi, budget):
    """Power at the receiver input for one direction of arrival."""
    terms = validate_uplink_budget(budget)
    gain = _number(gain_dbi, "gain_dbi")
    return (
        terms["eirp_dbw"] + gain - terms["path_loss_db"] - terms["other_losses_db"]
    )


def direction_margin_db(sample, budget):
    """Link margin, in dB, available in the direction of one gain sample."""
    record = validate_direction(sample)
    terms = validate_uplink_budget(budget)
    return received_power_dbw(record["gain_dbi"], terms) - terms["sensitivity_dbw"]


def direction_is_commandable(
    sample, budget, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB
):
    """True when one direction holds at least the required margin."""
    required = _number(required_margin_db, "required_margin_db")
    margin = direction_margin_db(sample, budget)
    return margin >= required - MARGIN_TOLERANCE_DB


def solid_angle_weight(theta_deg):
    """Relative solid angle carried by a sample at this polar angle."""
    theta = _number(theta_deg, "theta_deg")
    if theta < 0.0 or theta > 180.0:
        raise ValueError("theta_deg must lie in 0..180, got %r" % (theta,))
    return math.sin(math.radians(theta))


def coverage_gaps(samples, budget, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB):
    """Directions with too little margin to accept a telecommand."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence of gain samples")
    gaps = []
    for sample in samples:
        record = validate_direction(sample)
        if not direction_is_commandable(record, budget, required_margin_db):
            gaps.append(
                {
                    "theta_deg": record["theta_deg"],
                    "phi_deg": record["phi_deg"],
                    "margin_db": direction_margin_db(record, budget),
                }
            )
    return tuple(gaps)


def attitude_coverage_fraction(
    samples, budget, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB
):
    """Fraction of the sphere, weighted by solid angle, that is commandable."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence of gain samples")
    total = 0.0
    covered = 0.0
    for sample in samples:
        record = validate_direction(sample)
        weight = solid_angle_weight(record["theta_deg"])
        total += weight
        if direction_is_commandable(record, budget, required_margin_db):
            covered += weight
    if total == 0.0:
        raise ValueError(
            "samples carry no solid angle; a pole-only sample set cannot be weighted"
        )
    return covered / total


def dwell_time_s(beam_half_angle_deg, body_rate_deg_s):
    """Seconds the ground station stays inside the usable beam while tumbling."""
    half_angle = _positive(beam_half_angle_deg, "beam_half_angle_deg")
    if half_angle > 180.0:
        raise ValueError("beam_half_angle_deg must not exceed 180, got %r" % (half_angle,))
    rate = _non_negative(body_rate_deg_s, "body_rate_deg_s")
    if rate == 0.0:
        return math.inf
    return (2.0 * half_angle) / rate


def receiver_time_needed_s(acquisition_s, frame_duration_s):
    """Seconds the receiver needs to lock up and take one command frame."""
    return _non_negative(acquisition_s, "acquisition_s") + _non_negative(
        frame_duration_s, "frame_duration_s"
    )


def rate_is_supported(beam_half_angle_deg, body_rate_deg_s, acquisition_s, frame_duration_s):
    """True when the dwell at this rate covers acquisition plus one frame."""
    dwell = dwell_time_s(beam_half_angle_deg, body_rate_deg_s)
    needed = receiver_time_needed_s(acquisition_s, frame_duration_s)
    if math.isinf(dwell):
        return True
    return dwell >= needed - TIME_TOLERANCE_S


def max_supported_rate_deg_s(beam_half_angle_deg, acquisition_s, frame_duration_s):
    """Highest body rate at which one command frame still fits in the dwell."""
    half_angle = _positive(beam_half_angle_deg, "beam_half_angle_deg")
    needed = receiver_time_needed_s(acquisition_s, frame_duration_s)
    if needed == 0.0:
        return math.inf
    return (2.0 * half_angle) / needed


def assess_commandability(
    samples,
    budget,
    beam_half_angle_deg,
    worst_case_rate_deg_s,
    acquisition_s,
    frame_duration_s,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Assess attitude coverage and rate capability against clause 5.4.1."""
    gaps = coverage_gaps(samples, budget, required_margin_db)
    fraction = attitude_coverage_fraction(samples, budget, required_margin_db)
    dwell = dwell_time_s(beam_half_angle_deg, worst_case_rate_deg_s)
    needed = receiver_time_needed_s(acquisition_s, frame_duration_s)
    supported = rate_is_supported(
        beam_half_angle_deg, worst_case_rate_deg_s, acquisition_s, frame_duration_s
    )
    ceiling = max_supported_rate_deg_s(
        beam_half_angle_deg, acquisition_s, frame_duration_s
    )

    findings = []
    if gaps:
        findings.append(
            "%d of %d sampled directions hold less than %.6f dB margin"
            % (len(gaps), len(samples), _number(required_margin_db, "required_margin_db"))
        )
    if not supported:
        findings.append(
            "at %.6f deg/s the dwell is %.6f s against the %.6f s the receiver needs"
            % (_number(worst_case_rate_deg_s, "worst_case_rate_deg_s"), dwell, needed)
        )

    if gaps and not supported:
        verdict = ATTITUDE_AND_RATE
    elif gaps:
        verdict = ATTITUDE_GAP
    elif not supported:
        verdict = RATE_LIMITED
    else:
        verdict = COMMANDABLE

    return {
        "required_margin_db": _number(required_margin_db, "required_margin_db"),
        "sampled_directions": len(samples),
        "gap_directions": gaps,
        "coverage_fraction": fraction,
        "dwell_s": dwell,
        "receiver_time_needed_s": needed,
        "max_supported_rate_deg_s": ceiling,
        "rate_supported": supported,
        "findings": findings,
        "verdict": verdict,
        "commandable": verdict == COMMANDABLE,
    }
