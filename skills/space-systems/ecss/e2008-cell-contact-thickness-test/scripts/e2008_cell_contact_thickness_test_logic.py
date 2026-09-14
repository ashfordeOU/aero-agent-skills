#!/usr/bin/env python3
"""Acceptance measurement of contact metallisation depth before lot release.

Anchor: ECSS-E-ST-20-08C clause 7.5.10. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

This is a lot-release measurement, not a qualification one. A batch of
bare solar cells is about to be handed on, and the question is whether
the metal laid on their contacts is deep enough -- and not so deep that
it adds mass and stiffens the contact against the cell it sits on. So
there is a floor and there is a ceiling, and a lot fails at either.

Three things separate this from a spot check:

    the sample has to be big enough for the lot it stands in for
    a reading close to a limit cannot claim conformance on its own
    a lot that passes on count can still be incapable of repeating it

The second is metrology rather than statistics. Every gauge carries an
uncertainty, and a reading that sits inside that uncertainty of a limit
is consistent with being on either side of it. Counting it as a pass
transfers the gauge error into the lot disposition, so it is returned
as indeterminate and sent back for a better measurement.

The third is why the capability index is computed. A lot whose readings
all clear the floor by a whisker is a lot whose next batch will not,
and the count of nonconforming cells says nothing about that.

Thickness is carried in micrometres. Standard library only, offline,
deterministic.
"""

from __future__ import annotations

import math

CONTACT_TYPES = (
    "front-bus-bar",
    "front-grid-finger",
    "rear-contact",
)

DEFAULT_ACCEPTANCE_POLICY = {
    "minimum_thickness_um": 3.0,
    "maximum_thickness_um": 12.0,
    "measurement_uncertainty_um": 0.15,
    "sample_fraction": 0.10,
    "sample_size_floor": 5,
    "maximum_nonconforming_fraction": 0.0,
    "minimum_capability_index": 1.33,
}

CONFORMING = "conforming"
BELOW_MINIMUM = "below-minimum"
ABOVE_MAXIMUM = "above-maximum"
INDETERMINATE_LOW = "indeterminate-at-lower-limit"
INDETERMINATE_HIGH = "indeterminate-at-upper-limit"

DISPOSITIONS = (
    CONFORMING,
    BELOW_MINIMUM,
    ABOVE_MAXIMUM,
    INDETERMINATE_LOW,
    INDETERMINATE_HIGH,
)

LOT_RELEASED = "lot-released"
LOT_REJECTED = "lot-rejected"
LOT_INDETERMINATE = "lot-indeterminate"
SAMPLE_INADEQUATE = "acceptance-sample-inadequate"

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


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A limit and a reading written down in different places are compared
    here after arithmetic that can move either a few units in the last
    place. The limit is never relaxed; only the comparison tolerates the
    representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_acceptance_policy(policy=None):
    """Normalise the declared acceptance limits, rejecting an unusable set."""
    if policy is None:
        policy = DEFAULT_ACCEPTANCE_POLICY
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_ACCEPTANCE_POLICY)
    for key in policy:
        if key not in DEFAULT_ACCEPTANCE_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = policy[key]
    low = _require_positive("minimum_thickness_um", merged["minimum_thickness_um"])
    high = _require_positive("maximum_thickness_um", merged["maximum_thickness_um"])
    if not high > low:
        raise ValueError(
            "maximum_thickness_um %g must sit above minimum_thickness_um %g"
            % (high, low)
        )
    uncertainty = _require_non_negative(
        "measurement_uncertainty_um", merged["measurement_uncertainty_um"]
    )
    if uncertainty * 2.0 >= high - low:
        raise ValueError(
            "measurement uncertainty %g um consumes the whole %g um tolerance band"
            % (uncertainty, high - low)
        )
    fraction = _require_number("sample_fraction", merged["sample_fraction"])
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError(
            "sample_fraction must sit above zero and at most one, got %r" % (fraction,)
        )
    merged["minimum_thickness_um"] = low
    merged["maximum_thickness_um"] = high
    merged["measurement_uncertainty_um"] = uncertainty
    merged["sample_fraction"] = fraction
    merged["sample_size_floor"] = _require_count(
        "sample_size_floor", merged["sample_size_floor"], 1
    )
    nonconforming = _require_number(
        "maximum_nonconforming_fraction", merged["maximum_nonconforming_fraction"]
    )
    if nonconforming < 0.0 or nonconforming > 1.0:
        raise ValueError(
            "maximum_nonconforming_fraction must lie between zero and one, got %r"
            % (nonconforming,)
        )
    merged["maximum_nonconforming_fraction"] = nonconforming
    merged["minimum_capability_index"] = _require_positive(
        "minimum_capability_index", merged["minimum_capability_index"]
    )
    return merged


def acceptance_limits(policy=None):
    """The floor and the ceiling a contact thickness is judged against."""
    limits = validate_acceptance_policy(policy)
    return (limits["minimum_thickness_um"], limits["maximum_thickness_um"])


def conformance_zone(policy=None):
    """The narrower band inside which a reading can claim conformance.

    A reading nearer a limit than the gauge uncertainty is consistent
    with sitting on either side of that limit, so conformance is only
    claimed inside the limits pulled in by the uncertainty at each end.
    """
    limits = validate_acceptance_policy(policy)
    uncertainty = limits["measurement_uncertainty_um"]
    return (
        limits["minimum_thickness_um"] + uncertainty,
        limits["maximum_thickness_um"] - uncertainty,
    )


def required_sample_size(lot_size, policy=None):
    """How many cells of this lot have to be measured before release."""
    limits = validate_acceptance_policy(policy)
    size = _require_count("lot_size", lot_size, 1)
    raw = size * limits["sample_fraction"]
    # A whole-number product such as 100 x 0.10 lands a few units in the
    # last place above ten in binary, and a bare ceiling would then buy an
    # eleventh cell. The tolerance is relative so it stays correct across
    # lot sizes and never rounds a genuine fraction down.
    wanted = int(math.ceil(raw - 1e-9 * max(1.0, abs(raw))))
    wanted = max(wanted, limits["sample_size_floor"])
    return min(wanted, size)


def normalise_measurements(measurements):
    """Validate the measured sample and return it as identifier/value pairs."""
    if isinstance(measurements, dict) or isinstance(measurements, (str, bytes)):
        raise ValueError("measurements must be a sequence of sampled cells")
    try:
        items = list(measurements)
    except TypeError:
        raise ValueError("measurements must be a sequence of sampled cells")
    if not items:
        raise ValueError("at least one measured cell is needed")
    normalised = []
    seen = set()
    for index, item in enumerate(items):
        if isinstance(item, dict):
            identifier = item.get("cell_identifier", "cell-%d" % index)
            thickness = item.get("thickness_um")
        elif isinstance(item, (list, tuple)):
            try:
                identifier, thickness = item
            except ValueError:
                raise ValueError(
                    "measurement %d must be an identifier/thickness pair" % (index,)
                )
        else:
            identifier = "cell-%d" % index
            thickness = item
        if not isinstance(identifier, str) or not identifier:
            raise ValueError(
                "measurement %d needs a non-empty cell identifier" % (index,)
            )
        if identifier in seen:
            raise ValueError(
                "cell %s appears twice in the sample; one reading per cell"
                % (identifier,)
            )
        seen.add(identifier)
        normalised.append(
            (identifier, _require_positive("%s thickness_um" % identifier, thickness))
        )
    return tuple(normalised)


def reading_disposition(thickness_um, policy=None):
    """Categorize one reading against the limits and the gauge uncertainty."""
    limits = validate_acceptance_policy(policy)
    value = _require_positive("thickness_um", thickness_um)
    low, high = limits["minimum_thickness_um"], limits["maximum_thickness_um"]
    guard_low, guard_high = conformance_zone(limits)
    if not _at_least(value, low):
        return BELOW_MINIMUM
    if not _at_most(value, high):
        return ABOVE_MAXIMUM
    if not _at_least(value, guard_low):
        return INDETERMINATE_LOW
    if not _at_most(value, guard_high):
        return INDETERMINATE_HIGH
    return CONFORMING


def disposition_counts(measurements, policy=None):
    """How many sampled cells fall into each disposition."""
    limits = validate_acceptance_policy(policy)
    sample = normalise_measurements(measurements)
    counts = dict((name, 0) for name in DISPOSITIONS)
    for _, value in sample:
        counts[reading_disposition(value, limits)] += 1
    return counts


def nonconforming_cells(measurements, policy=None):
    """Identifiers of the sampled cells that sit outside a limit."""
    limits = validate_acceptance_policy(policy)
    sample = normalise_measurements(measurements)
    return tuple(
        identifier
        for identifier, value in sample
        if reading_disposition(value, limits) in (BELOW_MINIMUM, ABOVE_MAXIMUM)
    )


def indeterminate_cells(measurements, policy=None):
    """Identifiers of the sampled cells the gauge cannot place."""
    limits = validate_acceptance_policy(policy)
    sample = normalise_measurements(measurements)
    return tuple(
        identifier
        for identifier, value in sample
        if reading_disposition(value, limits)
        in (INDETERMINATE_LOW, INDETERMINATE_HIGH)
    )


def nonconforming_fraction(measurements, policy=None):
    """Share of the sample that sits outside a limit."""
    sample = normalise_measurements(measurements)
    return len(nonconforming_cells(sample, policy)) / len(sample)


def lot_statistics(measurements):
    """Central value and spread of the measured sample."""
    sample = normalise_measurements(measurements)
    values = [value for _, value in sample]
    count = len(values)
    mean = sum(values) / count
    if count > 1:
        variance = sum((value - mean) ** 2 for value in values) / (count - 1)
        stdev = math.sqrt(variance)
    else:
        stdev = 0.0
    return {
        "sample_size": count,
        "mean_um": mean,
        "minimum_um": min(values),
        "maximum_um": max(values),
        "range_um": max(values) - min(values),
        "sample_stdev_um": stdev,
    }


def capability_indices(measurements, policy=None):
    """How much room the process leaves against each limit.

    A lot can clear both limits on count and still be a lot that will
    not repeat, and the count alone never says so. A spread of zero is
    a sample too small or a gauge too coarse to resolve one, not an
    infinitely capable process, so it is reported as unbounded rather
    than as a number that would be compared against a floor.
    """
    limits = validate_acceptance_policy(policy)
    statistics = lot_statistics(measurements)
    mean = statistics["mean_um"]
    stdev = statistics["sample_stdev_um"]
    low, high = limits["minimum_thickness_um"], limits["maximum_thickness_um"]
    if stdev <= 0.0:
        return {
            "lower_capability": None,
            "upper_capability": None,
            "capability_index": None,
            "resolved": False,
        }
    lower = (mean - low) / (3.0 * stdev)
    upper = (high - mean) / (3.0 * stdev)
    return {
        "lower_capability": lower,
        "upper_capability": upper,
        "capability_index": min(lower, upper),
        "resolved": True,
    }


def sample_adequacy(lot_size, measurements, policy=None):
    """Whether the measured sample is big enough to release the lot on."""
    limits = validate_acceptance_policy(policy)
    sample = normalise_measurements(measurements)
    required = required_sample_size(lot_size, limits)
    findings = []
    adequate = len(sample) >= required
    if not adequate:
        findings.append(
            "%d cells measured, %d required for a lot of %d"
            % (len(sample), required, lot_size)
        )
    return {
        "lot_size": lot_size,
        "sample_size": len(sample),
        "required_sample_size": required,
        "adequate": adequate,
        "findings": findings,
    }


def assess_lot_release(case, policy=None):
    """Full clause 7.5.10 disposition of one bare cell lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    limits = validate_acceptance_policy(
        policy if policy is not None else case.get("policy")
    )
    contact = _require_choice("contact_type", case.get("contact_type"), CONTACT_TYPES)
    sample = normalise_measurements(case.get("measurements"))
    adequacy = sample_adequacy(case.get("lot_size"), sample, limits)
    counts = disposition_counts(sample, limits)
    failures = nonconforming_cells(sample, limits)
    unplaced = indeterminate_cells(sample, limits)
    fraction = len(failures) / len(sample)
    statistics = lot_statistics(sample)
    capability = capability_indices(sample, limits)
    findings = list(adequacy["findings"])
    for identifier in failures:
        findings.append(
            "%s %s reading sits outside the acceptance band" % (identifier, contact)
        )
    for identifier in unplaced:
        findings.append(
            "%s sits within gauge uncertainty of a limit; remeasure before release"
            % (identifier,)
        )
    count_ok = _at_most(fraction, limits["maximum_nonconforming_fraction"])
    if not count_ok:
        findings.append(
            "%.1f%% of the sample is nonconforming, limit %.1f%%"
            % (fraction * 100.0, limits["maximum_nonconforming_fraction"] * 100.0)
        )
    capable = True
    if capability["resolved"]:
        capable = _at_least(
            capability["capability_index"], limits["minimum_capability_index"]
        )
        if not capable:
            findings.append(
                "capability index %.2f is below the floor of %.2f; the lot clears"
                " the limits without room to repeat it"
                % (
                    capability["capability_index"],
                    limits["minimum_capability_index"],
                )
            )
    else:
        findings.append(
            "sample shows no resolvable spread; capability against the limits"
            " cannot be stated"
        )
    if not adequacy["adequate"]:
        verdict = SAMPLE_INADEQUATE
    elif failures or not count_ok:
        verdict = LOT_REJECTED
    elif unplaced:
        verdict = LOT_INDETERMINATE
    elif not capability["resolved"]:
        verdict = LOT_INDETERMINATE
    elif not capable:
        verdict = LOT_REJECTED
    else:
        verdict = LOT_RELEASED
    return {
        "contact_type": contact,
        "lot_identifier": case.get("lot_identifier"),
        "sample_adequacy": adequacy,
        "disposition_counts": counts,
        "nonconforming_cells": failures,
        "indeterminate_cells": unplaced,
        "nonconforming_fraction": fraction,
        "statistics": statistics,
        "capability": capability,
        "acceptance_limits_um": (
            limits["minimum_thickness_um"],
            limits["maximum_thickness_um"],
        ),
        "conformance_zone_um": conformance_zone(limits),
        "released": verdict == LOT_RELEASED,
        "verdict": verdict,
        "findings": findings,
    }
