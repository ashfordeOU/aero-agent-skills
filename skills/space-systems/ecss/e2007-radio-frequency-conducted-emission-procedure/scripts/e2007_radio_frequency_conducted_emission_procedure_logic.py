#!/usr/bin/env python3
"""Radio-frequency conducted-emission procedure, ECSS-E-ST-20-07C 5.4.3.4.

Paraphrased procedure, no verbatim standard text. The clause walks the
radio-frequency conducted-emission run from the instruments coming up to
temperature, through the check that proves the current-probe chain reads a
known injected current truthfully, to the swept capture that produces the
record and the repeat of the chain check afterwards. This module turns that
walk into a deterministic plan and verdict:

  phase records   -> mandatory phases present, in the clause order
  warm-up         -> elapsed soak against the required soak
  chain check     -> injected current carried through the probe transfer
                     impedance, compared with what the receiver read back
  drift           -> pre-capture against post-capture read-back
  capture segments-> detector, resolution bandwidth and sweep time per
                     segment, and whether the segments tile the method band
  sweep time      -> span * coefficient / bandwidth^2 per segment

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. Chain errors are differences of float levels,
# so an exactly-met tolerance can land a few units in the last place outside.
# It absorbs representation error only; it never widens a tolerance.
DB_TOL = 1e-9

# Generic relative tolerance for frequency and time comparisons.
REL_TOL = 1e-12

# Soak the receiver, the probe and the injection source need before the
# first reading, minutes.
DEFAULT_WARMUP_MINUTES = 30.0

# Largest acceptable difference between the level the probe chain should
# read for the injected current and the level it actually read, decibels.
DEFAULT_CHAIN_TOLERANCE_DB = 3.0

# Largest acceptable movement between the pre-capture and post-capture
# read-back of the same injected current, decibels.
DEFAULT_DRIFT_TOLERANCE_DB = 2.0

# Sweep-time coefficient. The swept receiver needs a time proportional to
# the span divided by the square of the resolution bandwidth; anything
# faster reads the resolution filter before it has settled.
DEFAULT_SWEEP_COEFFICIENT = 1.0

# Fraction of the required warm-up below which the remaining soak margin is
# carried as a limitation rather than passed silently.
DEFAULT_WARMUP_MARGIN_FRACTION = 0.1

PHASE_WARMUP = "warm-up"
PHASE_PRE_VERIFICATION = "pre-verification"
PHASE_AMBIENT_CHECK = "ambient-check"
PHASE_DATA_CAPTURE = "data-capture"
PHASE_POST_VERIFICATION = "post-verification"
MANDATORY_PHASES = (
    PHASE_WARMUP,
    PHASE_PRE_VERIFICATION,
    PHASE_AMBIENT_CHECK,
    PHASE_DATA_CAPTURE,
    PHASE_POST_VERIFICATION,
)

DETECTOR_PEAK = "peak"
DETECTOR_QUASI_PEAK = "quasi-peak"
DETECTOR_AVERAGE = "average"
DETECTORS = (DETECTOR_PEAK, DETECTOR_QUASI_PEAK, DETECTOR_AVERAGE)

VERDICT_VALID = "procedure-valid"
VERDICT_REJECTED = "procedure-rejected"


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


def at_most(value, limit, tol=DB_TOL):
    """True when value stays within the limit, absorbing float error only."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=tol)


def at_least(value, requirement, tol=DB_TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value >= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=0.0, abs_tol=tol)


def normalize_phase(phase):
    """Return the recognized procedure phase for a raw phase name."""
    if not isinstance(phase, str):
        raise ValueError("procedure phase must be a string, got %r" % (phase,))
    key = phase.strip().lower()
    if key not in MANDATORY_PHASES:
        raise ValueError(
            "unrecognized procedure phase %r; recognized: %s"
            % (phase, ", ".join(MANDATORY_PHASES))
        )
    return key


def normalize_detector(detector):
    """Return the recognized receiver detector for a raw detector name."""
    if not isinstance(detector, str):
        raise ValueError("detector must be a string, got %r" % (detector,))
    key = detector.strip().lower()
    if key not in DETECTORS:
        raise ValueError(
            "unrecognized detector %r; recognized: %s" % (detector, ", ".join(DETECTORS))
        )
    return key


def sequence_phases(phases):
    """Order the executed phases and report what is absent or swapped."""
    if not isinstance(phases, (list, tuple)):
        raise ValueError("phases: must be a list of phase names")
    if len(phases) == 0:
        raise ValueError("phases: at least one executed phase is required")
    seen = []
    for raw in phases:
        phase = normalize_phase(raw)
        if phase in seen:
            raise ValueError("phases: phase %r appears twice" % phase)
        seen.append(phase)
    missing = [phase for phase in MANDATORY_PHASES if phase not in seen]
    expected = [phase for phase in MANDATORY_PHASES if phase in seen]
    return {
        "executed": seen,
        "expected_order": expected,
        "missing": missing,
        "out_of_order": seen != expected,
    }


def warmup_headroom_minutes(elapsed_minutes, required_minutes=DEFAULT_WARMUP_MINUTES):
    """Minutes of soak beyond the required warm-up; negative when short."""
    elapsed = _scalar(elapsed_minutes, "elapsed_minutes")
    required = _scalar(required_minutes, "required_minutes")
    if elapsed < 0.0:
        raise ValueError("elapsed_minutes must be >= 0, got %g" % elapsed)
    if required <= 0.0:
        raise ValueError("required_minutes must be > 0, got %g" % required)
    return elapsed - required


def expected_readback_dbuv(
    injected_dbua, transfer_impedance_dbohm, insertion_loss_db=0.0
):
    """Level the receiver should show for a current injected at the probe.

    A current probe converts current to voltage through its transfer
    impedance, so in decibel terms the level adds: dBuV = dBuA + dBohm,
    less whatever the cable and attenuators take out of the chain.
    """
    current = _scalar(injected_dbua, "injected_dbua")
    impedance = _scalar(transfer_impedance_dbohm, "transfer_impedance_dbohm")
    loss = _scalar(insertion_loss_db, "insertion_loss_db")
    if loss < 0.0:
        raise ValueError("insertion_loss_db must be >= 0, got %g" % loss)
    return current + impedance - loss


def chain_error_db(
    read_back_dbuv, injected_dbua, transfer_impedance_dbohm, insertion_loss_db=0.0
):
    """Magnitude of the probe-chain read-back error, decibels."""
    read_back = _scalar(read_back_dbuv, "read_back_dbuv")
    expected = expected_readback_dbuv(
        injected_dbua, transfer_impedance_dbohm, insertion_loss_db
    )
    return abs(read_back - expected)


def chain_drift_db(pre_read_back_dbuv, post_read_back_dbuv):
    """Magnitude of the movement between the two chain read-backs."""
    pre = _scalar(pre_read_back_dbuv, "pre_read_back_dbuv")
    post = _scalar(post_read_back_dbuv, "post_read_back_dbuv")
    return abs(post - pre)


def minimum_sweep_time_s(span_hz, bandwidth_hz, coefficient=DEFAULT_SWEEP_COEFFICIENT):
    """Shortest swept capture that lets the resolution filter settle."""
    span = _scalar(span_hz, "span_hz")
    bandwidth = _scalar(bandwidth_hz, "bandwidth_hz")
    factor = _scalar(coefficient, "coefficient")
    if span <= 0.0:
        raise ValueError("span_hz must be > 0, got %g" % span)
    if bandwidth <= 0.0:
        raise ValueError("bandwidth_hz must be > 0, got %g" % bandwidth)
    if factor <= 0.0:
        raise ValueError("coefficient must be > 0, got %g" % factor)
    return factor * span / (bandwidth * bandwidth)


def validate_capture_segment(
    segment,
    required_detector=DETECTOR_PEAK,
    coefficient=DEFAULT_SWEEP_COEFFICIENT,
):
    """Validate one swept capture segment and return a normalized record."""
    if not isinstance(segment, dict):
        raise ValueError("capture_segment: record must be a mapping")
    where = "capture_segment"
    low = _number(segment, "low_hz", where)
    high = _number(segment, "high_hz", where)
    if low <= 0.0:
        raise ValueError("%s: low_hz must be > 0, got %g" % (where, low))
    if high <= low:
        raise ValueError("%s: high_hz %g must exceed low_hz %g" % (where, high, low))
    bandwidth = _number(segment, "bandwidth_hz", where)
    if bandwidth <= 0.0:
        raise ValueError("%s: bandwidth_hz must be > 0, got %g" % (where, bandwidth))
    sweep = _number(segment, "sweep_time_s", where)
    if sweep <= 0.0:
        raise ValueError("%s: sweep_time_s must be > 0, got %g" % (where, sweep))
    detector = normalize_detector(segment.get("detector", required_detector))
    wanted = normalize_detector(required_detector)
    span = high - low
    floor = minimum_sweep_time_s(span, bandwidth, coefficient)
    return {
        "low_hz": low,
        "high_hz": high,
        "span_hz": span,
        "bandwidth_hz": bandwidth,
        "detector": detector,
        "detector_ok": detector == wanted,
        "required_detector": wanted,
        "sweep_time_s": sweep,
        "sweep_floor_s": floor,
        "sweep_ok": at_least(sweep, floor, tol=floor * REL_TOL),
    }


def segment_coverage(segments, band_low_hz, band_high_hz):
    """Report how a set of capture segments tiles the declared method band."""
    if not isinstance(segments, (list, tuple)) or len(segments) == 0:
        raise ValueError("segments: at least one capture segment is required")
    low = _scalar(band_low_hz, "band_low_hz")
    high = _scalar(band_high_hz, "band_high_hz")
    if low <= 0.0:
        raise ValueError("band_low_hz must be > 0, got %g" % low)
    if high <= low:
        raise ValueError("band_high_hz %g must exceed band_low_hz %g" % (high, low))
    ordered = sorted(segments, key=lambda seg: (seg["low_hz"], seg["high_hz"]))
    gaps = []
    overlaps = []
    if ordered[0]["low_hz"] > low + abs(low) * REL_TOL:
        gaps.append((low, ordered[0]["low_hz"]))
    reach = ordered[0]["high_hz"]
    for seg in ordered[1:]:
        if seg["low_hz"] > reach + abs(reach) * REL_TOL:
            gaps.append((reach, seg["low_hz"]))
        elif seg["low_hz"] < reach - abs(reach) * REL_TOL:
            overlaps.append((seg["low_hz"], min(reach, seg["high_hz"])))
        if seg["high_hz"] > reach:
            reach = seg["high_hz"]
    if reach < high - abs(high) * REL_TOL:
        gaps.append((reach, high))
    return {
        "band_hz": (low, high),
        "ordered_low_hz": [seg["low_hz"] for seg in ordered],
        "gaps_hz": gaps,
        "overlaps_hz": overlaps,
        "covered": not gaps,
    }


def assess_procedure(
    phases,
    warmup_minutes,
    verification,
    capture_segments,
    method_band_hz,
    required_warmup_minutes=DEFAULT_WARMUP_MINUTES,
    chain_tolerance_db=DEFAULT_CHAIN_TOLERANCE_DB,
    drift_tolerance_db=DEFAULT_DRIFT_TOLERANCE_DB,
    required_detector=DETECTOR_PEAK,
    sweep_coefficient=DEFAULT_SWEEP_COEFFICIENT,
    warmup_margin_fraction=DEFAULT_WARMUP_MARGIN_FRACTION,
):
    """Full clause 5.4.3.4 assessment of one conducted-emission run."""
    sequence = sequence_phases(phases)
    headroom = warmup_headroom_minutes(warmup_minutes, required_warmup_minutes)
    required_soak = _scalar(required_warmup_minutes, "required_warmup_minutes")

    if not isinstance(verification, dict):
        raise ValueError("verification: record must be a mapping")
    chain_tol = _scalar(chain_tolerance_db, "chain_tolerance_db")
    if chain_tol <= 0.0:
        raise ValueError("chain_tolerance_db must be > 0, got %g" % chain_tol)
    drift_tol = _scalar(drift_tolerance_db, "drift_tolerance_db")
    if drift_tol <= 0.0:
        raise ValueError("drift_tolerance_db must be > 0, got %g" % drift_tol)
    margin_fraction = _scalar(warmup_margin_fraction, "warmup_margin_fraction")
    if not 0.0 <= margin_fraction < 1.0:
        raise ValueError(
            "warmup_margin_fraction must lie in [0, 1), got %g" % margin_fraction
        )

    injected = _number(verification, "injected_dbua", "verification")
    impedance = _number(verification, "transfer_impedance_dbohm", "verification")
    loss = (
        _number(verification, "insertion_loss_db", "verification")
        if "insertion_loss_db" in verification
        else 0.0
    )
    pre = _number(verification, "pre_read_back_dbuv", "verification")
    post = _number(verification, "post_read_back_dbuv", "verification")
    expected = expected_readback_dbuv(injected, impedance, loss)
    pre_error = chain_error_db(pre, injected, impedance, loss)
    post_error = chain_error_db(post, injected, impedance, loss)
    drift = chain_drift_db(pre, post)

    if not isinstance(method_band_hz, (list, tuple)) or len(method_band_hz) != 2:
        raise ValueError("method_band_hz: must be a (low_hz, high_hz) pair")
    graded = [
        validate_capture_segment(seg, required_detector, sweep_coefficient)
        for seg in capture_segments
    ]
    coverage = segment_coverage(graded, method_band_hz[0], method_band_hz[1])
    total_sweep_s = sum(seg["sweep_time_s"] for seg in graded)

    findings = []
    limitations = []
    for phase in sequence["missing"]:
        findings.append("mandatory phase not executed: %s" % phase)
    if sequence["out_of_order"]:
        findings.append(
            "phases executed out of order: %s" % ", ".join(sequence["executed"])
        )
    if headroom < 0.0 and not math.isclose(headroom, 0.0, rel_tol=0.0, abs_tol=DB_TOL):
        findings.append(
            "warm-up short by %.1f minute(s) of the %g required"
            % (-headroom, required_soak)
        )
    elif headroom <= required_soak * margin_fraction:
        limitations.append("warm-up left only %.1f minute(s) of margin" % headroom)
    if not at_most(pre_error, chain_tol):
        findings.append(
            "pre-capture chain read back %.2f dB from the expected %.2f dBuV, "
            "past the %g dB tolerance" % (pre_error, expected, chain_tol)
        )
    if not at_most(post_error, chain_tol):
        findings.append(
            "post-capture chain read back %.2f dB from the expected %.2f dBuV, "
            "past the %g dB tolerance" % (post_error, expected, chain_tol)
        )
    if not at_most(drift, drift_tol):
        findings.append(
            "chain drifted %.2f dB across the capture, past the %g dB tolerance"
            % (drift, drift_tol)
        )
    for seg in graded:
        if not seg["detector_ok"]:
            findings.append(
                "segment from %g Hz captured with the %s detector rather than %s"
                % (seg["low_hz"], seg["detector"], seg["required_detector"])
            )
        if not seg["sweep_ok"]:
            findings.append(
                "segment from %g Hz swept in %g s, faster than the %g s its %g Hz "
                "bandwidth needs"
                % (
                    seg["low_hz"],
                    seg["sweep_time_s"],
                    seg["sweep_floor_s"],
                    seg["bandwidth_hz"],
                )
            )
    for gap in coverage["gaps_hz"]:
        findings.append(
            "method band not captured between %g Hz and %g Hz" % (gap[0], gap[1])
        )
    for overlap in coverage["overlaps_hz"]:
        limitations.append(
            "segments overlap between %g Hz and %g Hz; the band is recorded twice"
            % (overlap[0], overlap[1])
        )

    return {
        "sequence": sequence,
        "warmup_headroom_minutes": headroom,
        "expected_readback_dbuv": expected,
        "pre_error_db": pre_error,
        "post_error_db": post_error,
        "chain_tolerance_db": chain_tol,
        "drift_db": drift,
        "drift_tolerance_db": drift_tol,
        "segments": graded,
        "coverage": coverage,
        "total_sweep_time_s": total_sweep_s,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_VALID if not findings else VERDICT_REJECTED,
    }
