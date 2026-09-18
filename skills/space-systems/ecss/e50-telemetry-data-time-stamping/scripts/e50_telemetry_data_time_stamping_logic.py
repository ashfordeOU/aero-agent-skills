"""Telemetry time-stamp error budget and field sizing.

Anchor: ECSS-E-ST-50C clause 5.5.5 (telemetry data carries the time of the
sampling instant, to a stated accuracy, traceable to a ground reference).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the error contributors that separate the sampling instant from
   the stamp that is downlinked.
2. Compute the on-board clock drift since the last time correlation and the
   quantisation error of the time field.
3. Combine the contributors by the declared rule -- worst-case sum or
   root-sum-square -- and rank them so the dominant term is visible.
4. Compare the total with the required stamp accuracy.
5. Size the time field from the mission span and the least significant bit,
   and compare with the declared field width.
6. Screen the stamp sequence for a backward step.
"""

import math

__all__ = [
    "ACCURACY_TOLERANCE_S",
    "COMBINATION_RULES",
    "validate_contributor",
    "validate_contributors",
    "clock_drift_error_s",
    "quantisation_error_s",
    "combine_errors_s",
    "rank_contributors",
    "required_field_bits",
    "monotonicity_breaks",
    "assess_time_stamping",
]

# The accuracy comparison is a combined budget against a declared limit: an
# exact equality can land a few ULPs on the wrong side. Absorb the
# representation error here instead of relaxing the accuracy requirement.
ACCURACY_TOLERANCE_S = 1e-12

COMBINATION_RULES = ("worst-case", "root-sum-square")


def _require_text(value, label):
    """Return a non-empty stripped string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _require_non_negative(value, label):
    """Return a non-negative finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def _require_positive(value, label):
    """Return a positive finite float or raise."""
    number = _require_non_negative(value, label)
    if number == 0.0:
        raise ValueError("%s must be positive" % label)
    return number


def validate_contributor(contributor):
    """Return a normalised (name, magnitude in seconds) error contributor."""
    if not isinstance(contributor, dict):
        raise ValueError("contributor must be a mapping, got %r" % (contributor,))
    for key in ("name", "magnitude_s"):
        if key not in contributor:
            raise ValueError("contributor missing required key '%s'" % key)
    return {
        "name": _require_text(contributor["name"], "name"),
        "magnitude_s": _require_non_negative(contributor["magnitude_s"], "magnitude_s"),
    }


def validate_contributors(contributors):
    """Return the validated contributor list; names must be unique."""
    if isinstance(contributors, dict) or not isinstance(contributors, (list, tuple)):
        raise ValueError("contributors must be a sequence of contributor mappings")
    if not contributors:
        raise ValueError("the contributor list must not be empty")
    records = [validate_contributor(item) for item in contributors]
    seen = set()
    for record in records:
        if record["name"] in seen:
            raise ValueError("duplicate contributor name '%s'" % record["name"])
        seen.add(record["name"])
    return records


def clock_drift_error_s(stability_ppm, elapsed_since_correlation_s):
    """Return the free-running clock drift accumulated since the last correlation."""
    stability = _require_non_negative(stability_ppm, "stability_ppm")
    elapsed = _require_non_negative(
        elapsed_since_correlation_s, "elapsed_since_correlation_s"
    )
    return stability * 1e-6 * elapsed


def quantisation_error_s(least_significant_bit_s):
    """Return the quantisation error of the time field: half its least significant bit."""
    lsb = _require_positive(least_significant_bit_s, "least_significant_bit_s")
    return lsb / 2.0


def combine_errors_s(magnitudes, rule="worst-case"):
    """Combine error magnitudes by the declared rule."""
    if isinstance(magnitudes, dict) or not isinstance(magnitudes, (list, tuple)):
        raise ValueError("magnitudes must be a sequence of error magnitudes")
    if not magnitudes:
        raise ValueError("magnitudes must contain at least one value")
    if rule not in COMBINATION_RULES:
        raise ValueError(
            "rule must be one of %s, got %r" % (", ".join(COMBINATION_RULES), rule)
        )
    values = [_require_non_negative(m, "error magnitude") for m in magnitudes]
    if rule == "worst-case":
        return math.fsum(values)
    return math.sqrt(math.fsum(v * v for v in values))


def rank_contributors(contributors):
    """Return the contributors ordered by descending magnitude, ties by name."""
    records = validate_contributors(contributors)
    return sorted(records, key=lambda r: (-r["magnitude_s"], r["name"]))


def required_field_bits(mission_span_s, least_significant_bit_s):
    """Return the time-field width needed to span the mission at a given resolution."""
    span = _require_positive(mission_span_s, "mission_span_s")
    lsb = _require_positive(least_significant_bit_s, "least_significant_bit_s")
    ticks = int(math.ceil(span / lsb))
    if ticks < 1:
        ticks = 1
    if ticks == 1:
        return 1
    return (ticks - 1).bit_length()


def monotonicity_breaks(stamps_s):
    """Return the (index, backward step in seconds) pairs where a stamp goes back."""
    if isinstance(stamps_s, dict) or not isinstance(stamps_s, (list, tuple)):
        raise ValueError("stamps_s must be a sequence of time stamps")
    if len(stamps_s) < 2:
        raise ValueError("stamps_s must hold at least two stamps to be ordered")
    values = []
    for index, stamp in enumerate(stamps_s):
        if not isinstance(stamp, (int, float)) or isinstance(stamp, bool):
            raise ValueError("stamp %d must be a real number, got %r" % (index, stamp))
        value = float(stamp)
        if not math.isfinite(value):
            raise ValueError("stamp %d must be finite" % index)
        values.append(value)
    breaks = []
    for index in range(1, len(values)):
        step = values[index] - values[index - 1]
        if step < 0.0:
            breaks.append((index, step))
    return breaks


def assess_time_stamping(spec):
    """Run the full clause 5.5.5 time-stamping assessment.

    spec keys: latency_contributors, stability_ppm,
    elapsed_since_correlation_s, correlation_residual_s,
    least_significant_bit_s, required_accuracy_s, mission_span_s,
    declared_field_bits, optional combination_rule and stamps_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("latency_contributors", "stability_ppm", "elapsed_since_correlation_s",
                "correlation_residual_s", "least_significant_bit_s",
                "required_accuracy_s", "mission_span_s", "declared_field_bits"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    rule = spec.get("combination_rule", "worst-case")
    declared_bits = spec["declared_field_bits"]
    if not isinstance(declared_bits, int) or isinstance(declared_bits, bool):
        raise ValueError("declared_field_bits must be an integer")
    if declared_bits <= 0:
        raise ValueError("declared_field_bits must be positive, got %d" % declared_bits)

    lsb = _require_positive(spec["least_significant_bit_s"], "least_significant_bit_s")
    required = _require_positive(spec["required_accuracy_s"], "required_accuracy_s")

    contributors = list(validate_contributors(spec["latency_contributors"]))
    contributors.append({
        "name": "on-board-clock-drift",
        "magnitude_s": clock_drift_error_s(
            spec["stability_ppm"], spec["elapsed_since_correlation_s"]
        ),
    })
    contributors.append({
        "name": "time-correlation-residual",
        "magnitude_s": _require_non_negative(
            spec["correlation_residual_s"], "correlation_residual_s"
        ),
    })
    contributors.append({
        "name": "stamp-field-quantisation",
        "magnitude_s": quantisation_error_s(lsb),
    })
    ranked = rank_contributors(contributors)
    total = combine_errors_s([r["magnitude_s"] for r in ranked], rule)

    within = total < required or math.isclose(
        total, required, rel_tol=0.0, abs_tol=ACCURACY_TOLERANCE_S
    )
    needed_bits = required_field_bits(spec["mission_span_s"], lsb)

    findings = []
    if not within:
        findings.append(
            "combined time-stamp error %.6g s (%s) exceeds the required accuracy "
            "%.6g s" % (total, rule, required)
        )
    if lsb / 2.0 > required:
        findings.append(
            "time-field least significant bit %.6g s cannot resolve the required "
            "accuracy %.6g s whatever the clock does" % (lsb, required)
        )
    if needed_bits > declared_bits:
        findings.append(
            "time field needs %d bits to span the mission at this resolution but "
            "carries %d; it wraps before end of mission" % (needed_bits, declared_bits)
        )
    breaks = []
    if "stamps_s" in spec:
        breaks = monotonicity_breaks(spec["stamps_s"])
        for index, step in breaks:
            findings.append(
                "stamp %d steps backwards by %.6g s; a correlation update was applied "
                "inside the stream or two references were merged" % (index, -step)
            )

    return {
        "contributors": ranked,
        "dominant_contributor": ranked[0]["name"],
        "combination_rule": rule,
        "total_error_s": total,
        "required_accuracy_s": required,
        "within_accuracy": within,
        "required_field_bits": needed_bits,
        "declared_field_bits": declared_bits,
        "monotonicity_breaks": breaks,
        "compliant": not findings,
        "findings": findings,
    }
