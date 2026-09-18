"""Blind-commanding session planning for a spacecraft telecommand uplink.

Anchor: ECSS-E-ST-50C clause 5.4.7 (commanding in the blind). One normative
item, paraphrased into an implementable procedure; no standard text is
reproduced.

Commanding in the blind is uplinking with no return link to confirm what
arrived -- launch and early orbit before the downlink is up, a safe mode with
the transmitter off, an occultation, a recovery from a lost attitude. Nothing
comes back, so the session has to be survivable by construction rather than by
observation.

Procedure implemented here
--------------------------
1. Validate the blind window and the uplink rate.
2. Group the command set by blind suitability: a command that is idempotent
   and does not depend on an on-board state the ground cannot observe is
   repeatable; anything else is a finding, because repetition is the only
   defence available and repetition of a non-idempotent command is a hazard.
3. Derive the repetition count from the per-pass loss probability and the
   confidence the session has to reach, by accumulating the residual failure
   probability rather than inverting a logarithm.
4. Size the repeated sequence in seconds from the command lengths, the uplink
   rate and the inter-command gap.
5. Check the sized sequence fits inside the window with the guard time held
   back, and report the residual failure probability actually achieved.
"""

import math

__all__ = [
    "FIT_TOLERANCE_S",
    "PROBABILITY_TOLERANCE",
    "MAX_REPETITIONS",
    "validate_window",
    "command_duration_s",
    "residual_failure_probability",
    "required_repetitions",
    "sequence_duration_s",
    "categorize_blind_suitability",
    "assess_blind_commanding",
]

# A sequence that ends exactly on the window edge fits; the difference of two
# divisions can land a few ULPs either side of zero.
FIT_TOLERANCE_S = 1e-9
PROBABILITY_TOLERANCE = 1e-12

# A repetition count that runs away means the loss probability, not the plan,
# is the thing to fix.
MAX_REPETITIONS = 10000


def _require_number(value, label, positive=True, allow_zero=False):
    """Return value as a float after rejecting bools, non-numbers and non-finites."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive:
        if allow_zero:
            if number < 0.0:
                raise ValueError("%s must be non-negative, got %r" % (label, value))
        elif number <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _require_probability(value, label, allow_one=False):
    """Return value as a float probability strictly inside (0, 1), or (0, 1]."""
    number = _require_number(value, label)
    upper_ok = number <= 1.0 if allow_one else number < 1.0
    if not upper_ok:
        raise ValueError(
            "%s must be below %s, got %r" % (label, "or equal to one" if allow_one else "one", value)
        )
    return number


def validate_window(window_s, guard_time_s):
    """Return the usable blind window in seconds after the guard time is held back."""
    window = _require_number(window_s, "window_s")
    guard = _require_number(guard_time_s, "guard_time_s", allow_zero=True)
    if guard >= window:
        raise ValueError(
            "guard_time_s %g consumes the whole %g s window" % (guard, window)
        )
    return window - guard


def command_duration_s(command_bits, uplink_rate_bps):
    """Return the on-air time of one command at the uplink rate."""
    bits = _require_number(command_bits, "command_bits")
    rate = _require_number(uplink_rate_bps, "uplink_rate_bps")
    return bits / rate


def residual_failure_probability(loss_probability, repetitions):
    """Return the probability every copy of a command is lost.

    Accumulated by repeated multiplication rather than exponentiation so the
    result is the same on every platform.
    """
    loss = _require_probability(loss_probability, "loss_probability", allow_one=True)
    count = repetitions
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("repetitions must be an integer, got %r" % (repetitions,))
    if count < 1:
        raise ValueError("repetitions must be at least one, got %d" % count)
    residual = 1.0
    for _ in range(count):
        residual *= loss
    return residual


def required_repetitions(loss_probability, target_confidence):
    """Return the smallest repetition count reaching the target confidence."""
    loss = _require_probability(loss_probability, "loss_probability")
    target = _require_probability(target_confidence, "target_confidence")
    allowed_residual = 1.0 - target
    residual = 1.0
    for count in range(1, MAX_REPETITIONS + 1):
        residual *= loss
        if residual < allowed_residual or math.isclose(
            residual, allowed_residual, rel_tol=0.0, abs_tol=PROBABILITY_TOLERANCE
        ):
            return count
    raise ValueError(
        "loss probability %g cannot reach confidence %g within %d repetitions"
        % (loss, target, MAX_REPETITIONS)
    )


def sequence_duration_s(command_bits_list, repetitions, uplink_rate_bps, inter_command_gap_s=0.0):
    """Return the on-air time of the whole repeated sequence in seconds."""
    if not isinstance(command_bits_list, (list, tuple)) or not command_bits_list:
        raise ValueError("command_bits_list must be a non-empty sequence")
    count = repetitions
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("repetitions must be an integer, got %r" % (repetitions,))
    if count < 1:
        raise ValueError("repetitions must be at least one, got %d" % count)
    rate = _require_number(uplink_rate_bps, "uplink_rate_bps")
    gap = _require_number(inter_command_gap_s, "inter_command_gap_s", allow_zero=True)
    total_bits = 0.0
    for index, bits in enumerate(command_bits_list):
        total_bits += _require_number(bits, "command_bits_list[%d]" % index)
    slots = len(command_bits_list) * count
    return (total_bits * count) / rate + gap * (slots - 1)


def categorize_blind_suitability(commands):
    """Group a command set by whether it can be repeated into a blind window.

    A command is repeatable only when applying it twice leaves the spacecraft
    where applying it once did, and when it does not branch on an on-board
    state the ground cannot see during the window.
    """
    if not isinstance(commands, (list, tuple)) or not commands:
        raise ValueError("commands must be a non-empty sequence of command records")
    repeatable = []
    unsafe = []
    seen = set()
    for index, record in enumerate(commands):
        if not isinstance(record, dict):
            raise ValueError("commands[%d] must be a mapping" % index)
        for key in ("name", "bits", "idempotent", "state_dependent"):
            if key not in record:
                raise ValueError("commands[%d] missing '%s'" % (index, key))
        name = record["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("commands[%d] name must be a non-empty string" % index)
        if name in seen:
            raise ValueError("duplicate command name %r in the blind sequence" % name)
        seen.add(name)
        for flag in ("idempotent", "state_dependent"):
            if not isinstance(record[flag], bool):
                raise ValueError("commands[%d] '%s' must be a bool" % (index, flag))
        _require_number(record["bits"], "commands[%d] bits" % index)
        if record["idempotent"] and not record["state_dependent"]:
            repeatable.append(name)
        else:
            unsafe.append(name)
    return {"repeatable": repeatable, "unsafe": unsafe}


def assess_blind_commanding(spec):
    """Run the full clause 5.4.7 blind-commanding assessment.

    spec keys: commands (sequence of {name, bits, idempotent, state_dependent}),
    window_s, guard_time_s, uplink_rate_bps, loss_probability,
    target_confidence, optional inter_command_gap_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "commands",
        "window_s",
        "guard_time_s",
        "uplink_rate_bps",
        "loss_probability",
        "target_confidence",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    grouping = categorize_blind_suitability(spec["commands"])
    usable = validate_window(spec["window_s"], spec["guard_time_s"])
    repetitions = required_repetitions(spec["loss_probability"], spec["target_confidence"])
    bits_list = [record["bits"] for record in spec["commands"]]
    duration = sequence_duration_s(
        bits_list, repetitions, spec["uplink_rate_bps"], spec.get("inter_command_gap_s", 0.0)
    )
    residual = residual_failure_probability(spec["loss_probability"], repetitions)

    fits = duration < usable or math.isclose(
        duration, usable, rel_tol=0.0, abs_tol=FIT_TOLERANCE_S
    )
    findings = []
    if grouping["unsafe"]:
        findings.append(
            "%d command(s) cannot be repeated into a blind window: %s"
            % (len(grouping["unsafe"]), ", ".join(grouping["unsafe"]))
        )
    if not fits:
        findings.append(
            "repeated sequence needs %.3f s but only %.3f s is usable after the guard time"
            % (duration, usable)
        )
    return {
        "repeatable": grouping["repeatable"],
        "unsafe": grouping["unsafe"],
        "repetitions": repetitions,
        "sequence_duration_s": duration,
        "usable_window_s": usable,
        "residual_failure_probability": residual,
        "fits_window": fits,
        "compliant": fits and not grouping["unsafe"],
        "findings": findings,
    }
