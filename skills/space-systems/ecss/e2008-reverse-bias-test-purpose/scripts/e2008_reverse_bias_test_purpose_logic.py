#!/usr/bin/env python3
"""Purpose of the reverse-bias test on a photovoltaic cell assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.14.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A cell assembly is driven into reverse bias whenever the string it sits in
keeps pushing current while that particular assembly stops producing it --
a shadow edge crossing the wing, a cracked cell, a mismatched string. The
assembly then dissipates instead of generating, and the question the test
exists to settle is narrow: after that exposure, does the assembly still
perform the way it did before it?

That makes the purpose a comparison, not a measurement. A single
post-exposure characterisation says nothing; only a before-and-after pair
against a declared allowance does. Three things therefore have to hold
before the purpose is served at all:

    coverage      every performance parameter the purpose rests on was
                  characterised on both sides of the exposure
    allowance     each of those parameters carries a declared allowance,
                  because without one there is no degradation criterion
    resolution    the allowance is coarser than the measurement
                  uncertainty by a stated margin, otherwise a loss the
                  size of the allowance is indistinguishable from noise

Maximum power is the parameter that carries the verdict, because reverse
bias degrades an assembly through shunt paths and localised heating that
move the knee of the curve long before they touch the open-circuit
voltage or the short-circuit current. It is derived here from the
maximum-power current and voltage rather than trusted as a reported
number, so a characterisation that reports an inconsistent triple is
caught instead of averaged in.

The resolution margin and the allowances below are declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

import math

__all__ = [
    "COMPARISON_ABSOLUTE_TOLERANCE",
    "COMPARISON_RELATIVE_TOLERANCE",
    "DEFAULT_RESOLUTION_MARGIN",
    "DEGRADATION_FOUND",
    "EVIDENCE_INCOMPLETE",
    "MEASURED_KEYS",
    "NOT_DEMONSTRATED",
    "PARAMETER_LABELS",
    "PERFORMANCE_PARAMETERS",
    "PERFORMANCE_RETAINED",
    "PURPOSE_OBJECTIVES",
    "assess_parameter",
    "assess_parameters",
    "evaluate_purpose",
    "maximum_power",
    "objective_parameter",
    "relative_loss",
    "resolution_is_adequate",
    "validate_characterisation",
]

# Characterisation values arrive as scaled instrument readings, so a value
# physically equal to a limit can land a few ULPs on the wrong side. Absorb
# that here rather than moving any allowance.
COMPARISON_RELATIVE_TOLERANCE = 1e-12
COMPARISON_ABSOLUTE_TOLERANCE = 1e-12

# An allowance must be at least this many times the measurement uncertainty
# before a loss the size of the allowance can be separated from noise.
DEFAULT_RESOLUTION_MARGIN = 3.0

# What a characterisation has to report on each side of the exposure.
MEASURED_KEYS = ("isc_a", "voc_v", "imp_a", "vmp_v")

# The parameters the purpose is expressed in; pmax_w is derived, not reported.
PERFORMANCE_PARAMETERS = ("isc_a", "voc_v", "imp_a", "vmp_v", "pmax_w")

PARAMETER_LABELS = {
    "isc_a": "short-circuit current",
    "voc_v": "open-circuit voltage",
    "imp_a": "maximum-power current",
    "vmp_v": "maximum-power voltage",
    "pmax_w": "maximum power",
}

# What clause 6.4.3.14.1 wants the test to settle, and the parameter each
# question rests on.
PURPOSE_OBJECTIVES = {
    "reverse-bias-power-retention": "pmax_w",
    "reverse-bias-shunt-path-formation": "vmp_v",
    "reverse-bias-junction-integrity": "voc_v",
    "reverse-bias-active-area-loss": "isc_a",
}

NOT_DEMONSTRATED = "reverse-bias-degradation-not-demonstrated"
EVIDENCE_INCOMPLETE = "reverse-bias-purpose-evidence-incomplete"
DEGRADATION_FOUND = "reverse-bias-degradation-found"
PERFORMANCE_RETAINED = "reverse-bias-performance-retained"


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _fraction(value, label):
    """Return value as a fraction in the open-above-zero, at-most-one range."""
    out = _real(value, label)
    if out <= 0.0 or out > 1.0:
        raise ValueError(
            "%s must be a fraction greater than 0 and at most 1, got %g" % (label, out)
        )
    return out


def _non_negative_fraction(value, label):
    """Return value as a fraction between zero and one inclusive."""
    out = _real(value, label)
    if out < 0.0 or out > 1.0:
        raise ValueError(
            "%s must be a fraction between 0 and 1, got %g" % (label, out)
        )
    return out


def _close(left, right):
    """Return True when two measured quantities are equal within tolerance."""
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


def validate_characterisation(record, label="characterisation"):
    """Return one illuminated characterisation as a validated record.

    The maximum-power point must lie inside the short-circuit current and
    the open-circuit voltage; a triple that does not is an inconsistent
    measurement, not a degraded assembly.
    """
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in MEASURED_KEYS:
        if key not in record:
            raise ValueError("%s missing required key '%s'" % (label, key))
    out = {}
    for key in MEASURED_KEYS:
        out[key] = _positive(record[key], "%s %s" % (label, key))
    if not _at_or_below(out["imp_a"], out["isc_a"]):
        raise ValueError(
            "%s maximum-power current %g A exceeds the short-circuit current %g A"
            % (label, out["imp_a"], out["isc_a"])
        )
    if not _at_or_below(out["vmp_v"], out["voc_v"]):
        raise ValueError(
            "%s maximum-power voltage %g V exceeds the open-circuit voltage %g V"
            % (label, out["vmp_v"], out["voc_v"])
        )
    out["pmax_w"] = maximum_power(out)
    return out


def maximum_power(record):
    """Return the maximum power a validated characterisation stands for."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("imp_a", "vmp_v"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    return _positive(record["imp_a"], "imp_a") * _positive(record["vmp_v"], "vmp_v")


def relative_loss(before_value, after_value):
    """Return the fractional loss from before to after; negative is a gain."""
    before = _positive(before_value, "before_value")
    after = _real(after_value, "after_value")
    if after < 0.0:
        raise ValueError("after_value must be non-negative, got %g" % after)
    return (before - after) / before


def resolution_is_adequate(allowance, uncertainty, margin=DEFAULT_RESOLUTION_MARGIN):
    """Return True when an allowance stands clear of the measurement noise."""
    allowed = _fraction(allowance, "allowance")
    noise = _non_negative_fraction(uncertainty, "uncertainty")
    factor = _positive(margin, "margin")
    return _at_or_above(allowed, noise * factor)


def objective_parameter(objective):
    """Return the performance parameter a purpose objective rests on."""
    if not isinstance(objective, str) or not objective.strip():
        raise ValueError("objective must be a non-empty string")
    cleaned = objective.strip().lower()
    if cleaned not in PURPOSE_OBJECTIVES:
        raise ValueError(
            "unrecognized objective %r; recognized: %s"
            % (objective, ", ".join(sorted(PURPOSE_OBJECTIVES)))
        )
    return PURPOSE_OBJECTIVES[cleaned]


def assess_parameter(parameter, before, after, allowance, uncertainty=0.0,
                     margin=DEFAULT_RESOLUTION_MARGIN):
    """Return the degradation record of one performance parameter."""
    if parameter not in PERFORMANCE_PARAMETERS:
        raise ValueError(
            "unrecognized parameter %r; recognized: %s"
            % (parameter, ", ".join(PERFORMANCE_PARAMETERS))
        )
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("before and after must be validated characterisations")
    for side, record in (("before", before), ("after", after)):
        if parameter not in record:
            raise ValueError(
                "%s characterisation carries no '%s'" % (side, parameter)
            )
    loss = relative_loss(before[parameter], after[parameter])
    allowed = _fraction(allowance, "allowance for %s" % parameter)
    resolved = resolution_is_adequate(allowed, uncertainty, margin)
    return {
        "parameter": parameter,
        "label": PARAMETER_LABELS[parameter],
        "before": float(before[parameter]),
        "after": float(after[parameter]),
        "relative_loss": loss,
        "allowance": allowed,
        "uncertainty": _non_negative_fraction(uncertainty, "uncertainty"),
        "resolution_margin": _positive(margin, "margin"),
        "resolution_adequate": resolved,
        "within_allowance": _at_or_below(loss, allowed),
    }


def assess_parameters(before, after, allowances, uncertainties=None,
                      margin=DEFAULT_RESOLUTION_MARGIN):
    """Return one degradation record per parameter that carries an allowance."""
    if not isinstance(allowances, dict) or not allowances:
        raise ValueError("allowances must be a non-empty mapping")
    noise = uncertainties if uncertainties is not None else {}
    if not isinstance(noise, dict):
        raise ValueError("uncertainties must be a mapping when given")
    for key in noise:
        if key not in PERFORMANCE_PARAMETERS:
            raise ValueError("uncertainty declared for unknown parameter %r" % key)
    records = []
    for parameter in PERFORMANCE_PARAMETERS:
        if parameter not in allowances:
            continue
        records.append(
            assess_parameter(
                parameter,
                before,
                after,
                allowances[parameter],
                noise.get(parameter, 0.0),
                margin,
            )
        )
    if not records:
        raise ValueError(
            "allowances name no recognized performance parameter; recognized: %s"
            % ", ".join(PERFORMANCE_PARAMETERS)
        )
    return records


def evaluate_purpose(spec):
    """Run the full clause 6.4.3.14.1 purpose evaluation for one assembly.

    spec keys: before, objectives, allowances; optional after (None when no
    post-exposure characterisation exists), uncertainties, resolution_margin.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("before", "objectives", "allowances"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    objectives = spec["objectives"]
    if not isinstance(objectives, (list, tuple)) or not objectives:
        raise ValueError("objectives must be a non-empty sequence")
    margin = spec.get("resolution_margin", DEFAULT_RESOLUTION_MARGIN)
    before = validate_characterisation(spec["before"], "before")

    wanted = []
    for objective in objectives:
        parameter = objective_parameter(objective)
        entry = {"objective": objective.strip().lower(), "parameter": parameter}
        if entry not in wanted:
            wanted.append(entry)

    after_raw = spec.get("after")
    findings = []
    if after_raw is None:
        for entry in wanted:
            findings.append(
                "objective %s has no post-exposure characterisation to compare against"
                % entry["objective"]
            )
        return {
            "objectives": wanted,
            "parameters": [],
            "findings": findings,
            "outcome": NOT_DEMONSTRATED,
            "passed": False,
        }

    after = validate_characterisation(after_raw, "after")
    allowances = spec["allowances"]
    if not isinstance(allowances, dict) or not allowances:
        raise ValueError("allowances must be a non-empty mapping")

    uncovered = [e for e in wanted if e["parameter"] not in allowances]
    for entry in uncovered:
        findings.append(
            "objective %s rests on the %s, for which no allowance is declared"
            % (entry["objective"], PARAMETER_LABELS[entry["parameter"]])
        )

    records = assess_parameters(
        before, after, allowances, spec.get("uncertainties"), margin
    )
    unresolved = [r for r in records if not r["resolution_adequate"]]
    for record in unresolved:
        findings.append(
            "the %s allowance of %g is not %g times its measurement uncertainty of %g,"
            " so a loss that size cannot be separated from noise"
            % (record["label"], record["allowance"], record["resolution_margin"],
               record["uncertainty"])
        )

    exceeded = [r for r in records if not r["within_allowance"]]
    for record in exceeded:
        findings.append(
            "the %s fell %.4g against an allowance of %g"
            % (record["label"], record["relative_loss"], record["allowance"])
        )

    if exceeded:
        outcome = DEGRADATION_FOUND
    elif uncovered or unresolved:
        outcome = EVIDENCE_INCOMPLETE
    else:
        outcome = PERFORMANCE_RETAINED

    return {
        "objectives": wanted,
        "parameters": records,
        "findings": findings,
        "outcome": outcome,
        "passed": outcome == PERFORMANCE_RETAINED,
    }
