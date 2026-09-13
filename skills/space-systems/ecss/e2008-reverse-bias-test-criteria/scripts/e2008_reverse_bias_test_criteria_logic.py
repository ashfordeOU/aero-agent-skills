#!/usr/bin/env python3
"""Reverse-bias measurement settings a photovoltaic assembly drawing sets.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.14.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause puts the measurement settings of the reverse-bias test on the
assembly drawing: the temperature the assembly is held at, how long it is
held there, and the current the supply is allowed to push into it. Two
consequences follow, and both are easy to miss.

First, a setting the drawing does not carry is not a criterion. A run can
be executed impeccably at a temperature nobody specified and there is still
nothing to judge it against; that is a specification defect, and it belongs
in the report as one rather than being quietly filled in from custom.

Second, the three settings are not compared the same way. They differ in
direction, and treating them alike is how a run passes on paper:

    temperature     a band. Too cold and too hot are both off-drawing,
                    because reverse behaviour is strongly temperature
                    dependent in both directions.
    hold time       a floor. Longer than drawn is a longer exposure and
                    still satisfies the criterion; shorter does not, because
                    the point of the hold is to let the assembly reach the
                    state being measured.
    current limit   a ceiling. Lower than drawn is conservative and
                    acceptable; higher lets the supply push more into the
                    assembly than the drawing permits.

A limit that was actually reached during the hold is a third thing again.
The assembly then sat at the limiter's condition rather than the drawing's,
so the recorded hold does not describe the intended one even when every
declared number matches.

Standard library only, offline, deterministic.
"""

import math

__all__ = [
    "COMPARISONS",
    "COMPARISON_ABSOLUTE_TOLERANCE",
    "COMPARISON_RELATIVE_TOLERANCE",
    "CRITERIA_NOT_SPECIFIED",
    "REQUIRED_SETTINGS",
    "SETTINGS_AS_DRAWN",
    "SETTINGS_NOT_RECORDED",
    "SETTINGS_OFF_DRAWING",
    "SETTING_LABELS",
    "SETTING_RULES",
    "assess_reverse_bias_criteria",
    "assess_setting",
    "assess_settings",
    "missing_settings",
    "normalize_setting",
    "setting_is_met",
    "validate_drawing",
    "validate_drawn_setting",
]

# Settings arrive as scaled instrument readings, so a value physically equal
# to a drawn bound can land a few ULPs on the wrong side. Absorb that here
# rather than moving anything the drawing sets.
COMPARISON_RELATIVE_TOLERANCE = 1e-12
COMPARISON_ABSOLUTE_TOLERANCE = 1e-12

# How each drawn setting is compared with what the run applied.
COMPARISONS = ("within-band", "at-least", "at-most")

SETTING_RULES = {
    "temperature_c": "within-band",
    "hold_time_s": "at-least",
    "current_limit_a": "at-most",
}

SETTING_LABELS = {
    "temperature_c": "hold temperature",
    "hold_time_s": "hold time",
    "current_limit_a": "current limit",
}

# The settings clause 6.4.3.14.3 expects the drawing to carry.
REQUIRED_SETTINGS = ("temperature_c", "hold_time_s", "current_limit_a")

# Settings that cannot be negative; temperature is signed.
NON_NEGATIVE_SETTINGS = ("hold_time_s", "current_limit_a")

CRITERIA_NOT_SPECIFIED = "reverse-bias-criteria-not-specified"
SETTINGS_NOT_RECORDED = "reverse-bias-settings-not-recorded"
SETTINGS_OFF_DRAWING = "reverse-bias-settings-off-drawing"
SETTINGS_AS_DRAWN = "reverse-bias-settings-as-drawn"


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _close(left, right):
    """Return True when two quantities are equal within tolerance."""
    return math.isclose(
        left,
        right,
        rel_tol=COMPARISON_RELATIVE_TOLERANCE,
        abs_tol=COMPARISON_ABSOLUTE_TOLERANCE,
    )


def _at_or_below(value, limit):
    """Return True when value stays at or under limit, tolerating equality."""
    return value < limit or _close(value, limit)


def _at_or_above(value, limit):
    """Return True when value reaches limit, tolerating equality."""
    return value > limit or _close(value, limit)


def normalize_setting(name):
    """Return a recognized setting name, refusing anything else."""
    if not isinstance(name, str):
        raise ValueError("setting name must be a string, got %r" % (name,))
    cleaned = name.strip().lower()
    if cleaned not in SETTING_RULES:
        raise ValueError(
            "unrecognized setting %r; recognized: %s"
            % (name, ", ".join(REQUIRED_SETTINGS))
        )
    return cleaned


def validate_drawn_setting(name, entry):
    """Return one drawn setting as a validated value-and-tolerance pair."""
    key = normalize_setting(name)
    if not isinstance(entry, dict):
        raise ValueError("drawn setting '%s' must be a mapping" % key)
    for field in ("value", "tolerance"):
        if field not in entry:
            raise ValueError(
                "drawn setting '%s' missing required key '%s'" % (key, field)
            )
    if key in NON_NEGATIVE_SETTINGS:
        value = _positive(entry["value"], "drawn %s value" % key)
    else:
        value = _real(entry["value"], "drawn %s value" % key)
    return {
        "setting": key,
        "label": SETTING_LABELS[key],
        "comparison": SETTING_RULES[key],
        "value": value,
        "tolerance": _non_negative(entry["tolerance"], "drawn %s tolerance" % key),
    }


def validate_drawing(drawing):
    """Return the drawn settings as validated records, keyed by setting."""
    if not isinstance(drawing, dict):
        raise ValueError("drawing must be a mapping of setting to value and tolerance")
    validated = {}
    for name, entry in drawing.items():
        record = validate_drawn_setting(name, entry)
        if record["setting"] in validated:
            raise ValueError("setting '%s' drawn twice" % record["setting"])
        validated[record["setting"]] = record
    return validated


def missing_settings(drawing):
    """Return the required settings the drawing does not carry."""
    validated = validate_drawing(drawing)
    return tuple(name for name in REQUIRED_SETTINGS if name not in validated)


def setting_is_met(applied, drawn):
    """Return True when an applied value satisfies one validated drawn setting.

    The comparison follows the setting's direction: a band for temperature,
    a floor for hold time, a ceiling for current limit.
    """
    if not isinstance(drawn, dict) or "comparison" not in drawn:
        raise ValueError("drawn must be a validated drawn setting")
    value = _real(applied, "applied %s" % drawn.get("setting", "setting"))
    comparison = drawn["comparison"]
    if comparison == "within-band":
        return _at_or_below(abs(value - drawn["value"]), drawn["tolerance"])
    if comparison == "at-least":
        return _at_or_above(value, drawn["value"] - drawn["tolerance"])
    if comparison == "at-most":
        return _at_or_below(value, drawn["value"] + drawn["tolerance"])
    raise ValueError(
        "unrecognized comparison %r; recognized: %s"
        % (comparison, ", ".join(COMPARISONS))
    )


def assess_setting(name, applied, drawing):
    """Return the conformance record of one applied setting against the drawing."""
    key = normalize_setting(name)
    validated = validate_drawing(drawing)
    if key not in validated:
        raise ValueError("the drawing sets no '%s', so there is no criterion" % key)
    drawn = validated[key]
    value = _real(applied, "applied %s" % key)
    if key in NON_NEGATIVE_SETTINGS and value <= 0.0:
        raise ValueError("applied %s must be positive, got %g" % (key, value))
    return {
        "setting": key,
        "label": drawn["label"],
        "comparison": drawn["comparison"],
        "applied": value,
        "drawn": drawn["value"],
        "tolerance": drawn["tolerance"],
        "deviation": value - drawn["value"],
        "met": setting_is_met(value, drawn),
    }


def assess_settings(applied, drawing):
    """Return one conformance record per setting the run actually applied."""
    if not isinstance(applied, dict):
        raise ValueError("applied must be a mapping of setting to value")
    validated = validate_drawing(drawing)
    records = []
    for name in REQUIRED_SETTINGS:
        if name not in validated or name not in applied:
            continue
        records.append(assess_setting(name, applied[name], drawing))
    for name in applied:
        if normalize_setting(name) not in validated:
            raise ValueError(
                "the run applied '%s', which the drawing does not set"
                % normalize_setting(name)
            )
    return records


def assess_reverse_bias_criteria(spec):
    """Run the full clause 6.4.3.14.3 settings check for one reverse-bias run.

    spec keys: drawing, applied; optional current_limit_reached (bool).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("drawing", "applied"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    limit_reached = spec.get("current_limit_reached", False)
    if not isinstance(limit_reached, bool):
        raise ValueError(
            "current_limit_reached must be a boolean, got %r" % (limit_reached,)
        )

    drawing = validate_drawing(spec["drawing"])
    applied = spec["applied"]
    if not isinstance(applied, dict):
        raise ValueError("applied must be a mapping of setting to value")

    undrawn = missing_settings(spec["drawing"])
    records = assess_settings(applied, spec["drawing"])
    unrecorded = tuple(
        name for name in REQUIRED_SETTINGS
        if name in drawing and name not in applied
    )

    findings = []
    breached = [record for record in records if not record["met"]]
    for record in breached:
        findings.append(
            "the %s was %g against a drawn %g with a tolerance of %g (%s)"
            % (record["label"], record["applied"], record["drawn"],
               record["tolerance"], record["comparison"])
        )
    for name in undrawn:
        findings.append(
            "the drawing sets no %s, so the run has no criterion to be read "
            "against" % SETTING_LABELS[name]
        )
    for name in unrecorded:
        findings.append(
            "the run recorded no %s, though the drawing sets one"
            % SETTING_LABELS[name]
        )
    if limit_reached:
        findings.append(
            "the run reached its current limit during the hold, so the assembly "
            "sat at the limiter's condition rather than the drawn one"
        )

    if breached or limit_reached:
        outcome = SETTINGS_OFF_DRAWING
    elif undrawn:
        outcome = CRITERIA_NOT_SPECIFIED
    elif unrecorded:
        outcome = SETTINGS_NOT_RECORDED
    else:
        outcome = SETTINGS_AS_DRAWN

    return {
        "settings": records,
        "undrawn_settings": undrawn,
        "unrecorded_settings": unrecorded,
        "breached_settings": tuple(r["setting"] for r in breached),
        "current_limit_reached": limit_reached,
        "findings": findings,
        "outcome": outcome,
        "passed": outcome == SETTINGS_AS_DRAWN,
    }
