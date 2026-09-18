"""Reverse current peak a latching limiter tolerates when reverse capability applies.

Anchor: ECSS-E-ST-20-20C clause 5.4.1.2.1 (the reverse current peak a latching
current limiter withstands where a reverse current capability is called for).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the clause bites at all. It addresses the latching category
   and only where a reverse current capability applies to the channel. A
   foldback or retriggerable limiter, or a latching channel with no reverse
   capability called for, is reported outside the clause rather than failed by
   it -- but a reverse transient presented against a channel that carries no
   reverse capability is still named, because nothing in this clause bounds it.
2. Validate the declared rating: a nominal limitation current, the peak
   multiple of that current the channel is rated to withstand in reverse, and
   the pulse duration that multiple is rated for.
3. Derate the rating for the event actually presented. A pulse longer than the
   rated duration carries more charge, so the tolerated peak falls with the
   square root of the duration ratio; repeated events erode the margin
   linearly down to a floor, below which the rating no longer bounds the
   event count at all.
4. Compare the applied peak against the derated tolerated peak, and report the
   margin in amperes together with the peak multiple the rating would have to
   carry for the applied transient to sit inside it.

The derated tolerated peak, not the catalogue figure, is the number a review
needs: a channel rated for a short single pulse can be a long way inside its
headline multiple and still be outside what a long or repeated reverse
transient asks of it.
"""

import math

__all__ = [
    "PEAK_TOLERANCE_A",
    "DURATION_TOLERANCE_MS",
    "REPETITION_DERATING_PER_EVENT",
    "REPETITION_DERATING_FLOOR",
    "LIMITER_CATEGORIES",
    "REVERSE_CLAUSE_CATEGORIES",
    "CAPABILITY_STATES",
    "normalise_category",
    "normalise_capability",
    "validate_channel",
    "validate_transient",
    "duration_derating_factor",
    "repetition_derating_factor",
    "tolerated_reverse_peak_a",
    "peak_margin_a",
    "required_rated_multiple",
    "assess_reverse_current_peak",
]

# Currents are quoted in amperes and a transient routinely lands exactly on the
# rating. Absorb the representation error, never the engineering margin.
PEAK_TOLERANCE_A = 1e-9
DURATION_TOLERANCE_MS = 1e-9

# Each repeated event past the first erodes the withstand linearly, down to a
# floor. At the floor the rating has stopped bounding the event count and the
# channel needs a repetitive figure of its own.
REPETITION_DERATING_PER_EVENT = 0.05
REPETITION_DERATING_FLOOR = 0.5

# The clause addresses the latching category; the others regulate or recover
# differently and are graded elsewhere.
REVERSE_CLAUSE_CATEGORIES = ("latching",)
LIMITER_CATEGORIES = REVERSE_CLAUSE_CATEGORIES + (
    "high-power",
    "retriggerable",
    "foldback",
)

CAPABILITY_STATES = ("applicable", "not-applicable")

_CATEGORY_ALIASES = {
    "lcl": "latching",
    "latching-current-limiter": "latching",
    "hpc": "high-power",
    "high-power-limiter": "high-power",
    "rcl": "retriggerable",
    "fcl": "foldback",
}

_CAPABILITY_ALIASES = {
    "required": "applicable",
    "yes": "applicable",
    "true": "applicable",
    "none": "not-applicable",
    "no": "not-applicable",
    "false": "not-applicable",
    "not-required": "not-applicable",
}


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _positive_real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError("%s must be positive and finite, got %g" % (label, number))
    return number


def normalise_category(category):
    """Return the canonical limiter category name."""
    key = _text(category, "category")
    key = _CATEGORY_ALIASES.get(key, key)
    if key not in LIMITER_CATEGORIES:
        raise ValueError(
            "unknown limiter category %r; known: %s"
            % (category, ", ".join(LIMITER_CATEGORIES))
        )
    return key


def normalise_capability(state):
    """Return the canonical reverse current capability state."""
    key = _text(state, "reverse capability")
    key = _CAPABILITY_ALIASES.get(key, key)
    if key not in CAPABILITY_STATES:
        raise ValueError(
            "unknown reverse capability %r; known: %s"
            % (state, ", ".join(CAPABILITY_STATES))
        )
    return key


def validate_channel(spec):
    """Return the validated reverse current rating of one limiter channel.

    spec keys: category, reverse_capability, nominal_limitation_current_a,
    rated_peak_multiple, rated_peak_duration_ms.
    """
    if not isinstance(spec, dict):
        raise ValueError("channel spec must be a mapping")
    required = (
        "category",
        "reverse_capability",
        "nominal_limitation_current_a",
        "rated_peak_multiple",
        "rated_peak_duration_ms",
    )
    for key in required:
        if key not in spec:
            raise ValueError("channel spec missing required key '%s'" % key)
    return {
        "category": normalise_category(spec["category"]),
        "reverse_capability": normalise_capability(spec["reverse_capability"]),
        "nominal_limitation_current_a": _positive_real(
            spec["nominal_limitation_current_a"], "nominal_limitation_current_a"
        ),
        "rated_peak_multiple": _positive_real(
            spec["rated_peak_multiple"], "rated_peak_multiple"
        ),
        "rated_peak_duration_ms": _positive_real(
            spec["rated_peak_duration_ms"], "rated_peak_duration_ms"
        ),
    }


def validate_transient(spec):
    """Return the validated reverse transient presented to the channel.

    spec keys: peak_current_a, duration_ms, repetitions.
    """
    if not isinstance(spec, dict):
        raise ValueError("transient spec must be a mapping")
    for key in ("peak_current_a", "duration_ms", "repetitions"):
        if key not in spec:
            raise ValueError("transient spec missing required key '%s'" % key)
    repetitions = spec["repetitions"]
    if not isinstance(repetitions, int) or isinstance(repetitions, bool):
        raise ValueError("repetitions must be an integer, got %r" % (repetitions,))
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1, got %d" % repetitions)
    return {
        "peak_current_a": _positive_real(spec["peak_current_a"], "peak_current_a"),
        "duration_ms": _positive_real(spec["duration_ms"], "duration_ms"),
        "repetitions": repetitions,
    }


def duration_derating_factor(duration_ms, rated_duration_ms):
    """Return the withstand factor for a pulse of the given duration.

    A pulse inside the rated duration carries the full rating. Beyond it the
    tolerated peak falls with the square root of the duration ratio, which is
    the constant-energy roll-off a withstand rating follows.
    """
    applied = _positive_real(duration_ms, "duration_ms")
    rated = _positive_real(rated_duration_ms, "rated_peak_duration_ms")
    if applied <= rated or math.isclose(
        applied, rated, rel_tol=0.0, abs_tol=DURATION_TOLERANCE_MS
    ):
        return 1.0
    return math.sqrt(rated / applied)


def repetition_derating_factor(repetitions):
    """Return the withstand factor for a repeated reverse event."""
    if not isinstance(repetitions, int) or isinstance(repetitions, bool):
        raise ValueError("repetitions must be an integer, got %r" % (repetitions,))
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1, got %d" % repetitions)
    if repetitions == 1:
        return 1.0
    eroded = 1.0 - REPETITION_DERATING_PER_EVENT * (repetitions - 1)
    return max(REPETITION_DERATING_FLOOR, eroded)


def tolerated_reverse_peak_a(channel, transient):
    """Return the reverse current peak the channel tolerates for this event."""
    base = channel["nominal_limitation_current_a"] * channel["rated_peak_multiple"]
    return (
        base
        * duration_derating_factor(
            transient["duration_ms"], channel["rated_peak_duration_ms"]
        )
        * repetition_derating_factor(transient["repetitions"])
    )


def peak_margin_a(channel, transient):
    """Return the tolerated peak less the applied peak, in amperes."""
    return tolerated_reverse_peak_a(channel, transient) - transient["peak_current_a"]


def required_rated_multiple(channel, transient):
    """Return the peak multiple the rating needs to carry this transient."""
    derated = duration_derating_factor(
        transient["duration_ms"], channel["rated_peak_duration_ms"]
    ) * repetition_derating_factor(transient["repetitions"])
    return transient["peak_current_a"] / (
        channel["nominal_limitation_current_a"] * derated
    )


def assess_reverse_current_peak(channel_spec, transient_spec):
    """Grade one latching channel's reverse current peak tolerance."""
    channel = validate_channel(channel_spec)
    transient = validate_transient(transient_spec)

    scope_findings = []
    findings = []

    category_in_scope = channel["category"] in REVERSE_CLAUSE_CATEGORIES
    capability_applies = channel["reverse_capability"] == "applicable"
    in_scope = category_in_scope and capability_applies

    if not category_in_scope:
        scope_findings.append(
            "category %s is outside the clause, which addresses the latching "
            "current limiter" % channel["category"]
        )
    if not capability_applies:
        scope_findings.append(
            "no reverse current capability is called for on this channel, so "
            "the clause places no reverse peak rating on it; the %g A reverse "
            "transient presented here is bounded by nothing in this clause"
            % transient["peak_current_a"]
        )

    duration_factor = duration_derating_factor(
        transient["duration_ms"], channel["rated_peak_duration_ms"]
    )
    repetition_factor = repetition_derating_factor(transient["repetitions"])
    tolerated = tolerated_reverse_peak_a(channel, transient)
    margin = peak_margin_a(channel, transient)
    needed_multiple = required_rated_multiple(channel, transient)

    if channel["rated_peak_multiple"] < 1.0:
        findings.append(
            "the rated peak multiple %g puts the reverse withstand below the "
            "channel's own limitation current"
            % channel["rated_peak_multiple"]
        )
    if margin < 0.0 and not math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=PEAK_TOLERANCE_A
    ):
        findings.append(
            "the %g A reverse peak exceeds the %g A the channel tolerates for a "
            "%g ms event repeated %d time(s); the rating has to reach %g times "
            "the limitation current"
            % (
                transient["peak_current_a"],
                tolerated,
                transient["duration_ms"],
                transient["repetitions"],
                needed_multiple,
            )
        )
    if math.isclose(
        repetition_factor, REPETITION_DERATING_FLOOR, rel_tol=0.0, abs_tol=1e-12
    ) and transient["repetitions"] > 1:
        findings.append(
            "repetition derating has reached its floor at %d events; a "
            "repetitive reverse peak rating has to be declared separately"
            % transient["repetitions"]
        )

    tolerant = not findings
    if not in_scope:
        verdict = "out-of-scope"
    elif tolerant:
        verdict = "compliant"
    else:
        verdict = "non-compliant"

    return {
        "category": channel["category"],
        "reverse_capability": channel["reverse_capability"],
        "in_scope": in_scope,
        "rated_peak_a": channel["nominal_limitation_current_a"]
        * channel["rated_peak_multiple"],
        "duration_derating_factor": duration_factor,
        "repetition_derating_factor": repetition_factor,
        "tolerated_peak_a": tolerated,
        "applied_peak_a": transient["peak_current_a"],
        "peak_margin_a": margin,
        "required_rated_multiple": needed_multiple,
        "tolerant": tolerant,
        "verdict": verdict,
        "findings": scope_findings + findings,
    }
