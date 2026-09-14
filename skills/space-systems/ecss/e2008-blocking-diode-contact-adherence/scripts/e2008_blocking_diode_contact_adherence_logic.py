#!/usr/bin/env python3
"""Judging whether the contacts on a planar blocking diode stay attached,
from a pull sample drawn against the lot.

Anchor: ECSS-E-ST-20-08C clause 12.6.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause verifies the durability of the contacts on planar blocking
diodes by adherence testing. Three decisions sit inside that sentence:

    the contacts    a planar device is pulled at its bonded pads -- the
                    anode pad and the cathode pad -- and a device is
                    sentenced by whichever of them is weakest, because a
                    string does not care which pad let go
    durability      a raw pull load is not comparable between part
                    numbers. A large pad holds more for the same
                    metallurgy, so the reading is turned into a stress
                    over the bonded pad area before it is judged
    by testing      a pull is a pull only if it was applied normally to
                    the pad and at the declared crosshead rate. Off
                    angle it peels, too fast it shocks, and either way
                    the number describes a different experiment

The sample is part of the evidence, not an administrative detail. A lot
owes a sample sized against its own population with a floor underneath,
and a verdict drawn from fewer devices than that is reported as an
insufficient sample rather than as an acceptance.

A lifted pad fails the lot outright rather than being diluted into a
reject fraction: a fraction describes a spread of strengths, a lift-off
describes a bond that was never made.

The stresses, angles, rates and caps below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANODE_PAD = "anode-pad"
CATHODE_PAD = "cathode-pad"

BONDED_PADS = (ANODE_PAD, CATHODE_PAD)

ADHERENT = "adherent"
BELOW_LIMIT = "below-limit"
LIFTED = "lifted"

ADHERENCE_CATEGORIES = (ADHERENT, BELOW_LIMIT, LIFTED)

SAMPLE_INSUFFICIENT = "blocking-diode-adherence-sample-insufficient"
FIXTURE_DEFICIENT = "blocking-diode-adherence-fixture-deficient"
LOT_REJECTED = "blocking-diode-adherence-lot-rejected"
LOT_ACCEPTED = "blocking-diode-adherence-lot-accepted"

RUN_VERDICTS = (
    SAMPLE_INSUFFICIENT,
    FIXTURE_DEFICIENT,
    LOT_REJECTED,
    LOT_ACCEPTED,
)

DEFAULT_ADHERENCE_POLICY = {
    "min_adherence_stress_n_per_mm2": 1.5,
    "lift_off_stress_n_per_mm2": 0.1,
    "sample_fraction": 0.10,
    "min_sample_devices": 5,
    "max_pull_angle_deviation_deg": 5.0,
    "min_crosshead_rate_mm_per_min": 0.5,
    "max_crosshead_rate_mm_per_min": 5.0,
    "max_reject_fraction": 0.05,
}

NORMAL_PULL_ANGLE_DEG = 90.0

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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r"
            % (name, value)
        )
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_adherence_policy(policy):
    """Check a planar contact adherence sampling and pull policy is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    limit = _require_positive(
        "min_adherence_stress_n_per_mm2",
        policy.get("min_adherence_stress_n_per_mm2"),
    )
    lift = _require_positive(
        "lift_off_stress_n_per_mm2", policy.get("lift_off_stress_n_per_mm2")
    )
    if lift >= limit:
        raise ValueError(
            "lift_off_stress_n_per_mm2 %g must sit below the "
            "min_adherence_stress_n_per_mm2 %g it is a lift-off threshold under"
            % (lift, limit)
        )
    _require_fraction("sample_fraction", policy.get("sample_fraction"))
    _require_count("min_sample_devices", policy.get("min_sample_devices"))
    deviation = _require_positive(
        "max_pull_angle_deviation_deg",
        policy.get("max_pull_angle_deviation_deg"),
    )
    if deviation >= NORMAL_PULL_ANGLE_DEG:
        raise ValueError(
            "max_pull_angle_deviation_deg %g would allow a pull along the pad "
            "rather than off it" % (deviation,)
        )
    low = _require_positive(
        "min_crosshead_rate_mm_per_min",
        policy.get("min_crosshead_rate_mm_per_min"),
    )
    high = _require_positive(
        "max_crosshead_rate_mm_per_min",
        policy.get("max_crosshead_rate_mm_per_min"),
    )
    if not low < high:
        raise ValueError(
            "min_crosshead_rate_mm_per_min %g must sit below "
            "max_crosshead_rate_mm_per_min %g" % (low, high)
        )
    _require_fraction("max_reject_fraction", policy.get("max_reject_fraction"))
    return policy


def required_sample_size(lot_size, policy=DEFAULT_ADHERENCE_POLICY):
    """Devices the lot owes the pull test: a share of it, with a floor."""
    validate_adherence_policy(policy)
    lot = _require_count("lot_size", lot_size)
    share = int(math.ceil(lot * float(policy["sample_fraction"]) - _ABS_TOL))
    floor = int(policy["min_sample_devices"])
    return min(lot, max(share, floor))


def contact_stress_n_per_mm2(pull_load_n, pad_area_mm2):
    """Turn one pull reading into a stress over the bonded pad area."""
    load = _require_non_negative("pull_load_n", pull_load_n)
    area = _require_positive("pad_area_mm2", pad_area_mm2)
    return load / area


def pull_angle_deviation_deg(pull_angle_deg):
    """How far off normal to the pad the pull was applied."""
    angle = _require_non_negative("pull_angle_deg", pull_angle_deg)
    if angle > 180.0:
        raise ValueError("pull_angle_deg %g is not an angle off a pad" % (angle,))
    return abs(angle - NORMAL_PULL_ANGLE_DEG)


def fixture_is_conforming(fixture, policy=DEFAULT_ADHERENCE_POLICY):
    """True when the pull was applied near normal and at a declared rate."""
    validate_adherence_policy(policy)
    if not isinstance(fixture, dict):
        raise ValueError("fixture must be a mapping, got %r" % (fixture,))
    deviation = pull_angle_deviation_deg(fixture.get("pull_angle_deg"))
    rate = _require_positive(
        "fixture crosshead_rate_mm_per_min",
        fixture.get("crosshead_rate_mm_per_min"),
    )
    return (
        _at_most(deviation, float(policy["max_pull_angle_deviation_deg"]))
        and _at_least(rate, float(policy["min_crosshead_rate_mm_per_min"]))
        and _at_most(rate, float(policy["max_crosshead_rate_mm_per_min"]))
    )


def categorize_pad_adherence(
    pull_load_n, pad_area_mm2, policy=DEFAULT_ADHERENCE_POLICY
):
    """Group one pad reading as adherent, below limit or lifted."""
    validate_adherence_policy(policy)
    stress = contact_stress_n_per_mm2(pull_load_n, pad_area_mm2)
    if _at_least(stress, float(policy["min_adherence_stress_n_per_mm2"])):
        return ADHERENT
    if _at_most(stress, float(policy["lift_off_stress_n_per_mm2"])):
        return LIFTED
    return BELOW_LIMIT


def sentence_planar_device(device, policy=DEFAULT_ADHERENCE_POLICY):
    """Sentence one planar device by the weakest of its bonded pads."""
    validate_adherence_policy(policy)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    pads = device.get("pads")
    if not isinstance(pads, dict) or not pads:
        raise ValueError(
            "device is missing a non-empty pads mapping, got %r" % (pads,)
        )
    per_pad = {}
    stresses = {}
    for name, reading in pads.items():
        if name not in BONDED_PADS:
            raise ValueError(
                "unrecognised bonded pad %r; known pads are %s"
                % (name, ", ".join(BONDED_PADS))
            )
        if not isinstance(reading, dict):
            raise ValueError(
                "pad %r must be a mapping with a load and an area, got %r"
                % (name, reading)
            )
        stresses[name] = contact_stress_n_per_mm2(
            reading.get("pull_load_n"), reading.get("pad_area_mm2")
        )
        per_pad[name] = categorize_pad_adherence(
            reading.get("pull_load_n"), reading.get("pad_area_mm2"), policy
        )
    if LIFTED in per_pad.values():
        worst = LIFTED
    elif BELOW_LIMIT in per_pad.values():
        worst = BELOW_LIMIT
    else:
        worst = ADHERENT
    return {
        "id": device.get("id"),
        "pad_categories": per_pad,
        "pad_stress_n_per_mm2": stresses,
        "weakest_stress_n_per_mm2": min(stresses.values()),
        "category": worst,
    }


def assess_contact_adherence_run(run, policy=DEFAULT_ADHERENCE_POLICY):
    """Full clause 12.6.6 judgement for one planar adherence test."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (run,))
    validate_adherence_policy(policy)
    lot = run.get("lot")
    if not isinstance(lot, dict):
        raise ValueError("run is missing a lot block")
    fixture = run.get("fixture")
    if not isinstance(fixture, dict):
        raise ValueError("run is missing a fixture block")
    devices = run.get("devices")
    if not isinstance(devices, list) or not devices:
        raise ValueError("run is missing a non-empty devices list")

    lot_size = _require_count("lot diode_count", lot.get("diode_count"))
    required = required_sample_size(lot_size, policy)
    pulled = len(devices)
    if pulled > lot_size:
        raise ValueError(
            "%d devices were pulled from a lot of %d" % (pulled, lot_size)
        )

    conforming = fixture_is_conforming(fixture, policy)
    deviation = pull_angle_deviation_deg(fixture.get("pull_angle_deg"))
    rate = _require_positive(
        "fixture crosshead_rate_mm_per_min",
        fixture.get("crosshead_rate_mm_per_min"),
    )

    sentences = [sentence_planar_device(device, policy) for device in devices]
    lifted = [s for s in sentences if s["category"] == LIFTED]
    below = [s for s in sentences if s["category"] == BELOW_LIMIT]
    reject_fraction = (len(lifted) + len(below)) / pulled

    findings = []
    result = {
        "lot_size": lot_size,
        "required_sample_devices": required,
        "pulled_devices": pulled,
        "fixture_conforming": conforming,
        "pull_angle_deviation_deg": deviation,
        "crosshead_rate_mm_per_min": rate,
        "sentences": sentences,
        "lifted_devices": len(lifted),
        "below_limit_devices": len(below),
        "reject_fraction": reject_fraction,
        "findings": findings,
    }

    undersized = pulled < required
    if undersized:
        findings.append(
            "%d device(s) were pulled where a lot of %d owes %d, so this "
            "result does not cover the lot" % (pulled, lot_size, required)
        )

    if not conforming:
        if not _at_most(
            deviation, float(policy["max_pull_angle_deviation_deg"])
        ):
            findings.append(
                "the pull ran %.2f deg off normal against the %.2f deg the "
                "fixture allows, so the pads were peeled rather than pulled"
                % (deviation, float(policy["max_pull_angle_deviation_deg"]))
            )
        if not _at_least(
            rate, float(policy["min_crosshead_rate_mm_per_min"])
        ) or not _at_most(rate, float(policy["max_crosshead_rate_mm_per_min"])):
            findings.append(
                "the crosshead ran %.3f mm/min against the %.3f to %.3f mm/min "
                "band this test is defined at"
                % (
                    rate,
                    float(policy["min_crosshead_rate_mm_per_min"]),
                    float(policy["max_crosshead_rate_mm_per_min"]),
                )
            )

    if lifted:
        findings.append(
            "%d device(s) had a pad come away rather than reading low"
            % (len(lifted),)
        )
    if not _at_most(reject_fraction, float(policy["max_reject_fraction"])):
        findings.append(
            "%.4f of the devices pulled fall short against the %.4f the lot "
            "allows" % (reject_fraction, float(policy["max_reject_fraction"]))
        )

    if undersized:
        result["verdict"] = SAMPLE_INSUFFICIENT
    elif not conforming:
        result["verdict"] = FIXTURE_DEFICIENT
    elif lifted or not _at_most(
        reject_fraction, float(policy["max_reject_fraction"])
    ):
        result["verdict"] = LOT_REJECTED
    else:
        result["verdict"] = LOT_ACCEPTED
    return result
