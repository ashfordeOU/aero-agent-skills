"""Reference basis of the reported current offset of an output telemetry.

Anchor: ECSS-E-ST-20-20C clause 5.2.8.5.1 (the offset of the reported current
is expressed relative to the class current of the device). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the basis a declaration was written against, accepting the
   spellings a datasheet uses and refusing a reading basis outright, since an
   offset lives at zero applied current where a percentage of reading has no
   value.
2. Convert the declared figure into an absolute current, then re-express it
   against the class current of the device, which is the basis this clause
   fixes.
3. Report by how much a full-scale declaration understated the offset, which
   is exactly the ratio of the telemetry full scale to the class current.
4. Settle the offset actually measured from a set of zero-applied-current
   readings, refusing a set too scattered to be one offset.
5. Compare the governing class-referenced offset with its allowance and report
   a declaration that disagrees with the measurement.
"""

import math

__all__ = [
    "OFFSET_TOLERANCE",
    "BASES",
    "normalise_basis",
    "to_absolute_amps",
    "offset_ratio_to_class",
    "express_offset",
    "restate_declaration",
    "offset_from_zero_readings",
    "within_allowed_offset",
    "assess_offset_reference",
]

# The verdict is a comparison between two ratios a design can place exactly on
# top of each other. Absorb the representation error here rather than widening
# the allowance.
OFFSET_TOLERANCE = 1e-12

BASES = ("absolute", "class-current", "full-scale")

_ABSOLUTE_ALIASES = frozenset(
    ["absolute", "a", "amp", "amps", "ampere", "amperes", "current"]
)
_CLASS_ALIASES = frozenset(
    ["class", "class-current", "of-class-current", "class-rating", "i-class", "iclass"]
)
_FULL_SCALE_ALIASES = frozenset(
    ["full-scale", "fullscale", "fs", "of-full-scale", "range"]
)
_READING_ALIASES = frozenset(["reading", "of-reading", "rd", "measured-value"])


def _real(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def normalise_basis(basis):
    """Return the canonical reference basis behind a declared spelling."""
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError("basis must be a non-empty string, got %r" % (basis,))
    text = basis.strip().lower().replace("%", " ").replace("_", "-")
    text = "-".join(part for part in text.replace(" ", "-").split("-") if part)
    for prefix in ("percent-of-", "percentage-of-", "percent-", "of-"):
        if text.startswith(prefix) and len(text) > len(prefix):
            text = text[len(prefix):]
            break
    if text in _READING_ALIASES:
        raise ValueError(
            "a reading basis cannot express an offset: the offset is the value "
            "reported at zero applied current, where a percentage of reading "
            "has no value"
        )
    if text in _ABSOLUTE_ALIASES:
        return "absolute"
    if text in _CLASS_ALIASES:
        return "class-current"
    if text in _FULL_SCALE_ALIASES:
        return "full-scale"
    raise ValueError(
        "unrecognised basis '%s'; recognised: %s" % (basis, ", ".join(BASES))
    )


def to_absolute_amps(value, basis, class_current_a, full_scale_current_a=None):
    """Return a declared offset as an absolute current in amperes."""
    canonical = normalise_basis(basis)
    declared = _real("declared offset", value)
    class_current = _positive("class_current_a", class_current_a)
    if canonical == "absolute":
        return declared
    if canonical == "class-current":
        return declared * class_current
    if full_scale_current_a is None:
        raise ValueError(
            "a full-scale declaration cannot be converted without the telemetry "
            "full-scale current"
        )
    return declared * _positive("full_scale_current_a", full_scale_current_a)


def offset_ratio_to_class(offset_a, class_current_a):
    """Return the signed offset as a fraction of the class current."""
    offset = _real("offset_a", offset_a)
    return offset / _positive("class_current_a", class_current_a)


def express_offset(offset_a, class_current_a):
    """Return the offset expressed on the basis this clause fixes."""
    ratio = offset_ratio_to_class(offset_a, class_current_a)
    return {
        "basis": "class-current",
        "offset_a": _real("offset_a", offset_a),
        "class_ratio": ratio,
        "class_percent": ratio * 100.0,
    }


def restate_declaration(value, basis, class_current_a, full_scale_current_a=None):
    """Restate a declared offset against the class current and say what moved."""
    canonical = normalise_basis(basis)
    absolute = to_absolute_amps(value, canonical, class_current_a, full_scale_current_a)
    class_current = _positive("class_current_a", class_current_a)
    understatement = None
    if canonical == "full-scale":
        understatement = (
            _positive("full_scale_current_a", full_scale_current_a) / class_current
        )
    return {
        "declared_value": _real("declared offset", value),
        "declared_basis": canonical,
        "absolute_a": absolute,
        "class_ratio": absolute / class_current,
        "restated": canonical != "class-current",
        "understatement_factor": understatement,
    }


def offset_from_zero_readings(readings, max_spread_a=None):
    """Return the offset settled from readings taken at zero applied current."""
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence of reported currents")
    values = [
        _real("readings[%d]" % i, item) for i, item in enumerate(readings)
    ]
    spread = max(values) - min(values)
    if max_spread_a is not None:
        allowed = _positive("max_spread_a", max_spread_a)
        too_wide = spread > allowed and not math.isclose(
            spread, allowed, rel_tol=0.0, abs_tol=OFFSET_TOLERANCE
        )
        if too_wide:
            raise ValueError(
                "zero-current readings scatter by %g A against an allowed %g A; "
                "this is noise, not a settled offset" % (spread, allowed)
            )
    return {
        "offset_a": sum(values) / float(len(values)),
        "spread_a": spread,
        "count": len(values),
    }


def within_allowed_offset(class_ratio, allowed_ratio):
    """Return whether a class-referenced offset magnitude sits inside its allowance."""
    ratio = abs(_real("class_ratio", class_ratio))
    allowed = _positive("allowed_ratio", allowed_ratio)
    return ratio < allowed or math.isclose(
        ratio, allowed, rel_tol=0.0, abs_tol=OFFSET_TOLERANCE
    )


def assess_offset_reference(spec):
    """Run the clause 5.2.8.5.1 offset reference-basis assessment.

    spec keys: declared_offset, declared_basis, class_current_a,
    allowed_offset_ratio; optional full_scale_current_a, zero_readings,
    zero_reading_spread_a, agreement_a.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("declared_offset", "declared_basis", "class_current_a",
                "allowed_offset_ratio"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    allowed = _positive("allowed_offset_ratio", spec["allowed_offset_ratio"])
    if allowed >= 1.0:
        raise ValueError(
            "allowed_offset_ratio is a fraction of the class current below 1.0, "
            "got %g" % allowed
        )
    class_current = _positive("class_current_a", spec["class_current_a"])
    declaration = restate_declaration(
        spec["declared_offset"],
        spec["declared_basis"],
        class_current,
        spec.get("full_scale_current_a"),
    )
    findings = []
    if declaration["restated"]:
        if declaration["declared_basis"] == "full-scale":
            findings.append(
                "the offset was declared against telemetry full scale; against "
                "the class current it is %.3f%%, larger by a factor of %.3f"
                % (declaration["class_ratio"] * 100.0,
                   declaration["understatement_factor"])
            )
        else:
            findings.append(
                "the offset was declared as an absolute current; against the "
                "class current it is %.3f%%" % (declaration["class_ratio"] * 100.0)
            )
    measured = None
    governing_a = declaration["absolute_a"]
    if "zero_readings" in spec:
        measured = offset_from_zero_readings(
            spec["zero_readings"], spec.get("zero_reading_spread_a")
        )
        governing_a = measured["offset_a"]
        if "agreement_a" in spec:
            agreement = _positive("agreement_a", spec["agreement_a"])
            gap = abs(measured["offset_a"] - declaration["absolute_a"])
            apart = gap > agreement and not math.isclose(
                gap, agreement, rel_tol=0.0, abs_tol=OFFSET_TOLERANCE
            )
            if apart:
                findings.append(
                    "the measured offset %.6f A sits %.6f A from the declared "
                    "%.6f A, past the %.6f A they were expected to agree within"
                    % (measured["offset_a"], gap, declaration["absolute_a"],
                       agreement)
                )
    governing = express_offset(governing_a, class_current)
    within = within_allowed_offset(governing["class_ratio"], allowed)
    if not within:
        findings.append(
            "the offset is %.3f%% of the class current, past the allowed %.3f%%"
            % (governing["class_percent"], allowed * 100.0)
        )
    return {
        "declaration": declaration,
        "measured": measured,
        "governing_offset_a": governing_a,
        "governing_class_ratio": governing["class_ratio"],
        "allowed_offset_ratio": allowed,
        "expressed_against_class_current": not declaration["restated"],
        "within_allowance": within,
        "compliant": within and not findings,
        "findings": findings,
    }
