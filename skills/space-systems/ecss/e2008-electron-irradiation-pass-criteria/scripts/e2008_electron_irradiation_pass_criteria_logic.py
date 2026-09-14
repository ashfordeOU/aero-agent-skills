#!/usr/bin/env python3
"""Drawing limits applied to a blocking diode once exposure and anneal are done.

Anchor: ECSS-E-ST-20-08C clause 12.6.11.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The criterion is one sentence and everything here follows from it: after the
electron exposure and after the thermal anneal that follows it, the diode's
characteristics still have to sit inside the limits its own source control
drawing fixes.

Three things fall out of that sentence, and each is a way a campaign gets
it wrong.

The reading that sentences the device is the one taken after the anneal.
The post-irradiation reading is the worst the part will ever look, and a
device sentenced on it is being refused for a shift the anneal was always
expected to take back. A device whose record carries no post-anneal reading
is therefore left unsentenced rather than passed on the pre-anneal numbers
or failed on them.

The limits come from the drawing that governs this diode type. Not the
vendor datasheet typical, not the value the last programme flew, not a
house limit carried forward. A verdict quoted with no drawing reference
behind it is not a verdict against this clause.

The three characteristics point in two directions. The forward drop and
the reverse leakage are ceilings -- less is better -- and the blocking
voltage is a floor. Landing exactly on a limit is admissible in all three
cases, and the comparison tolerance exists to absorb representation error
rather than to widen the drawing.

How much of the irradiation shift the anneal gave back is worth recording
beside the verdict. Two devices can both sit inside the drawing and one of
them recovered nine tenths of its shift while the other recovered a tenth;
the word "accepted" hides that difference and nobody can recover it later.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FORWARD_VOLTAGE = "forward-voltage-drop"
REVERSE_LEAKAGE = "reverse-leakage-current"
BLOCKING_VOLTAGE = "blocking-voltage"

DRAWING_REQUIREMENT_NOT_ESTABLISHED = (
    "source-control-drawing-requirement-not-established"
)
POST_ANNEAL_READING_NOT_EVIDENCED = "post-anneal-reading-not-evidenced"
LOT_REJECT_FRACTION_EXCEEDED = "lot-reject-fraction-exceeded"
LOT_MEETS_DRAWING_LIMITS = "lot-meets-drawing-limits"

DEFAULT_PASS_POLICY = {
    "max_reject_fraction": 0.1,
    "marginal_band_fraction": 0.02,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


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


def validate_pass_policy(policy):
    """Check the lot sentencing policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    reject = _require_non_negative(
        "max_reject_fraction", policy.get("max_reject_fraction")
    )
    if reject > 1.0:
        raise ValueError(
            "max_reject_fraction %g is above one; an allowance that admits a "
            "lot with no usable diode is not a sentencing policy" % reject
        )
    marginal = _require_positive(
        "marginal_band_fraction", policy.get("marginal_band_fraction")
    )
    if marginal > 1.0:
        raise ValueError(
            "marginal_band_fraction %g is above one; every accepted diode "
            "would be flagged marginal" % marginal
        )
    return policy


def validate_drawing_limits(limits):
    """Check the post-exposure limits the source control drawing fixes."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    reference = _require_label("drawing_reference", limits.get("drawing_reference"))
    forward = _require_positive(
        "max_forward_voltage_v", limits.get("max_forward_voltage_v")
    )
    leakage = _require_positive(
        "max_reverse_leakage_a", limits.get("max_reverse_leakage_a")
    )
    blocking = _require_positive(
        "min_blocking_voltage_v", limits.get("min_blocking_voltage_v")
    )
    junction = _require_number(
        "reference_junction_temperature_c",
        limits.get("reference_junction_temperature_c"),
    )
    if not _at_most(forward, blocking):
        raise ValueError(
            "the drawing allows a %g V forward drop against a %g V blocking "
            "floor, which describes no diode" % (forward, blocking)
        )
    return {
        "drawing_reference": reference,
        "max_forward_voltage_v": forward,
        "max_reverse_leakage_a": leakage,
        "min_blocking_voltage_v": blocking,
        "reference_junction_temperature_c": junction,
    }


def validate_reading(label, reading):
    """Read one set of three characteristics taken at a single stage."""
    if not isinstance(reading, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, reading))
    return {
        "forward_voltage_v": _require_positive(
            "forward_voltage_v in %s" % label, reading.get("forward_voltage_v")
        ),
        "reverse_leakage_a": _require_positive(
            "reverse_leakage_a in %s" % label, reading.get("reverse_leakage_a")
        ),
        "blocking_voltage_v": _require_positive(
            "blocking_voltage_v in %s" % label, reading.get("blocking_voltage_v")
        ),
    }


def validate_device_record(device):
    """Read one exposed diode: its identifier and the readings it carries.

    The post-anneal reading is the one the clause sentences on. The
    pre-exposure and post-irradiation readings are optional here because a
    device can be sentenced without them; they only add the recovery figure.
    """
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    identifier = _require_label("device id", device.get("id"))
    if not identifier:
        raise ValueError("device id must not be blank")
    record = {"id": identifier, "post_anneal": None}
    post_anneal = device.get("post_anneal")
    if post_anneal is not None:
        record["post_anneal"] = validate_reading(
            "post_anneal on %s" % identifier, post_anneal
        )
    for stage in ("pre_irradiation", "post_irradiation"):
        value = device.get(stage)
        record[stage] = (
            None
            if value is None
            else validate_reading("%s on %s" % (stage, identifier), value)
        )
    return record


def ceiling_margin_fraction(measured, limit):
    """Headroom below a ceiling, as a fraction of the ceiling."""
    value = _require_positive("measured", measured)
    bound = _require_positive("limit", limit)
    return 1.0 - value / bound


def floor_margin_fraction(measured, limit):
    """Headroom above a floor, as a fraction of the floor."""
    value = _require_positive("measured", measured)
    bound = _require_positive("limit", limit)
    return value / bound - 1.0


def anneal_recovery_fraction(pre_value, post_irradiation_value, post_anneal_value):
    """Share of the exposure-induced shift the anneal gave back.

    One means the anneal returned the characteristic to where it started;
    zero means the anneal moved nothing. A negative figure means the part
    kept drifting through the soak, which is a finding rather than an error.
    """
    pre = _require_positive("pre_value", pre_value)
    irradiated = _require_positive(
        "post_irradiation_value", post_irradiation_value
    )
    annealed = _require_positive("post_anneal_value", post_anneal_value)
    shift = irradiated - pre
    if math.isclose(shift, 0.0, rel_tol=_REL_TOL, abs_tol=1e-12):
        raise ValueError(
            "the exposure moved this characteristic by nothing, so there is "
            "no shift for the anneal to have recovered"
        )
    return (irradiated - annealed) / shift


def device_verdict(device, limits):
    """Sentence one exposed diode on its post-anneal reading."""
    checked = validate_drawing_limits(limits)
    record = validate_device_record(device)
    verdict = {
        "id": record["id"],
        "sentenced": False,
        "breaches": (),
        "margins": {},
        "limiting_margin_fraction": None,
        "forward_recovery_fraction": None,
        "accepted": False,
    }
    reading = record["post_anneal"]
    if reading is None:
        return verdict

    margins = {
        FORWARD_VOLTAGE: ceiling_margin_fraction(
            reading["forward_voltage_v"], checked["max_forward_voltage_v"]
        ),
        REVERSE_LEAKAGE: ceiling_margin_fraction(
            reading["reverse_leakage_a"], checked["max_reverse_leakage_a"]
        ),
        BLOCKING_VOLTAGE: floor_margin_fraction(
            reading["blocking_voltage_v"], checked["min_blocking_voltage_v"]
        ),
    }
    breaches = []
    if not _at_most(reading["forward_voltage_v"], checked["max_forward_voltage_v"]):
        breaches.append(FORWARD_VOLTAGE)
    if not _at_most(reading["reverse_leakage_a"], checked["max_reverse_leakage_a"]):
        breaches.append(REVERSE_LEAKAGE)
    if not _at_least(
        reading["blocking_voltage_v"], checked["min_blocking_voltage_v"]
    ):
        breaches.append(BLOCKING_VOLTAGE)

    recovery = None
    if record["pre_irradiation"] is not None and record["post_irradiation"] is not None:
        try:
            recovery = anneal_recovery_fraction(
                record["pre_irradiation"]["forward_voltage_v"],
                record["post_irradiation"]["forward_voltage_v"],
                reading["forward_voltage_v"],
            )
        except ValueError:
            recovery = None

    verdict["sentenced"] = True
    verdict["breaches"] = tuple(breaches)
    verdict["margins"] = margins
    verdict["limiting_margin_fraction"] = min(margins.values())
    verdict["forward_recovery_fraction"] = recovery
    verdict["accepted"] = not breaches
    return verdict


def device_verdicts(devices, limits):
    """Sentence every exposed diode, in record order."""
    if not isinstance(devices, (list, tuple)):
        raise ValueError("devices must be a sequence of exposed diode records")
    if not devices:
        raise ValueError("no exposed diode was recorded, so there is nothing to judge")
    verdicts = []
    seen = set()
    for device in devices:
        verdict = device_verdict(device, limits)
        if verdict["id"] in seen:
            raise ValueError("duplicate device id %r in the record" % verdict["id"])
        seen.add(verdict["id"])
        verdicts.append(verdict)
    return tuple(verdicts)


def unsentenced_devices(verdicts):
    """Devices left without a verdict because no post-anneal reading exists."""
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence")
    return tuple(v["id"] for v in verdicts if not v["sentenced"])


def lot_reject_fraction(verdicts):
    """Share of the sentenced diodes that breached at least one drawing limit."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    sentenced = [v for v in verdicts if v["sentenced"]]
    if not sentenced:
        raise ValueError(
            "no diode carries a post-anneal reading, so no reject share exists"
        )
    rejected = sum(1 for v in sentenced if not v["accepted"])
    return rejected / len(sentenced)


def lot_within_reject_allowance(verdicts, policy=DEFAULT_PASS_POLICY):
    """True when the rejected share is inside the declared lot allowance."""
    validate_pass_policy(policy)
    return _at_most(
        lot_reject_fraction(verdicts), float(policy["max_reject_fraction"])
    )


def weakest_device(verdicts):
    """The sentenced diode with the smallest margin against any drawing limit."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    sentenced = [v for v in verdicts if v["sentenced"]]
    if not sentenced:
        raise ValueError("no sentenced diode to take a weakest margin from")
    return min(sentenced, key=lambda v: v["limiting_margin_fraction"])


def marginal_device_advisories(verdicts, policy=DEFAULT_PASS_POLICY):
    """Name accepted diodes sitting only just inside a drawing limit.

    These do not move the verdict -- an accepted diode is accepted -- but a
    part that clears the drawing by a hair after its anneal has nothing left
    for the rest of the mission, and that is worth saying once here.
    """
    validate_pass_policy(policy)
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence")
    band = float(policy["marginal_band_fraction"])
    advisories = []
    for verdict in verdicts:
        if not verdict["sentenced"] or not verdict["accepted"]:
            continue
        if _at_most(verdict["limiting_margin_fraction"], band):
            advisories.append(
                "diode %s is accepted on a margin of %.3g per cent, inside the "
                "%.3g per cent marginal band; it meets the drawing after its "
                "anneal and has almost nothing left for the mission"
                % (
                    verdict["id"],
                    verdict["limiting_margin_fraction"] * 100.0,
                    band * 100.0,
                )
            )
    return tuple(advisories)


def assess_post_exposure_pass_criteria(case, policy=DEFAULT_PASS_POLICY):
    """Full clause 12.6.11.2.3 decision for one exposed and annealed lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_pass_policy(policy)

    findings = []
    advisories = []
    result = {
        "drawing_reference": None,
        "max_forward_voltage_v": None,
        "max_reverse_leakage_a": None,
        "min_blocking_voltage_v": None,
        "device_verdicts": (),
        "accepted_devices": (),
        "rejected_devices": (),
        "unsentenced_devices": (),
        "lot_reject_fraction": None,
        "weakest_device_id": None,
        "weakest_device_margin_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    limits = case.get("drawing_limits")
    if limits is None:
        findings.append(
            "no source control drawing limit set is referenced, so the "
            "post-exposure readings have nothing to be judged against"
        )
        result["verdict"] = DRAWING_REQUIREMENT_NOT_ESTABLISHED
        return result
    checked = validate_drawing_limits(limits)
    result["drawing_reference"] = checked["drawing_reference"]
    result["max_forward_voltage_v"] = checked["max_forward_voltage_v"]
    result["max_reverse_leakage_a"] = checked["max_reverse_leakage_a"]
    result["min_blocking_voltage_v"] = checked["min_blocking_voltage_v"]
    if not checked["drawing_reference"]:
        findings.append(
            "the limits carry no drawing reference; a post-exposure limit "
            "with no drawing behind it is not the criterion of this clause"
        )
        result["verdict"] = DRAWING_REQUIREMENT_NOT_ESTABLISHED
        return result

    verdicts = device_verdicts(case.get("devices"), limits)
    result["device_verdicts"] = verdicts
    result["unsentenced_devices"] = unsentenced_devices(verdicts)
    result["accepted_devices"] = tuple(
        v["id"] for v in verdicts if v["sentenced"] and v["accepted"]
    )
    result["rejected_devices"] = tuple(
        v["id"] for v in verdicts if v["sentenced"] and not v["accepted"]
    )

    if result["unsentenced_devices"]:
        findings.append(
            "no post-anneal reading exists for %s; the clause sentences on "
            "the reading taken after the anneal, and the post-irradiation "
            "reading alone cannot stand in for it"
            % ", ".join(result["unsentenced_devices"])
        )
        result["verdict"] = POST_ANNEAL_READING_NOT_EVIDENCED
        return result

    result["lot_reject_fraction"] = lot_reject_fraction(verdicts)
    weakest = weakest_device(verdicts)
    result["weakest_device_id"] = weakest["id"]
    result["weakest_device_margin_fraction"] = weakest["limiting_margin_fraction"]

    for verdict in verdicts:
        if verdict["accepted"]:
            continue
        findings.append(
            "diode %s breaches the %s limit of drawing %s after its anneal, "
            "by %.3g per cent"
            % (
                verdict["id"],
                " and ".join(verdict["breaches"]),
                checked["drawing_reference"],
                abs(verdict["limiting_margin_fraction"]) * 100.0,
            )
        )

    advisories.extend(marginal_device_advisories(verdicts, policy))

    if not lot_within_reject_allowance(verdicts, policy):
        findings.append(
            "%.3g per cent of the sentenced lot breaches a drawing limit "
            "after anneal, above the %.3g per cent the policy allows"
            % (
                result["lot_reject_fraction"] * 100.0,
                float(policy["max_reject_fraction"]) * 100.0,
            )
        )
        result["verdict"] = LOT_REJECT_FRACTION_EXCEEDED
        return result

    result["verdict"] = LOT_MEETS_DRAWING_LIMITS
    return result
