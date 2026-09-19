#!/usr/bin/env python3
"""Application control for threaded fasteners: preload, locking, reuse.

Anchor: ECSS-Q-ST-70-46 application clause on threaded fasteners, read
together with the companion design-and-application standard it points
at for the joint analysis itself. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Three things have to hold before a fastener may be installed.

The preload window. A target preload is set as a fraction of the proof
load of the part, and the tightening method spreads that target into a
band. The band, not the target, is what the joint sees: the low end has
to still hold the joint closed against the separating load, and the
high end has to stay under the proof load of the fastener. A method
with a wide scatter can fail both ends of that window at once even
though its nominal target looked comfortable.

The locking. A feature that holds by friction alone decays, and it
decays fastest under the vibration that made someone ask for locking in
the first place. Where losing the fastener loses the function, the
locking has to be positive: a physical obstruction, not a friction
torque.

The reuse. A prevailing-torque feature is consumed by use, so reuse is
allowed only while the measured prevailing torque still reaches the
minimum. A fastener tightened by a method that takes it past yield has
no elastic range left and is single-use whatever the thread looks like.

Preload and torque are floating-point quantities, so every comparison
here carries a small relative slack and the module never reports a
verdict that turns on the last bit of a computed value.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Relative slack on every comparison against a computed limit, so a
# value landing on its own limit reads the same on every platform.
_REL_SLACK = 1e-9

# Tightening methods and the scatter each one puts on the target
# preload, as (low factor, high factor) applied to the target.
_METHOD_SCATTER = {
    "hand-wrench-no-control": (0.55, 1.45),
    "torque-wrench": (0.75, 1.25),
    "torque-and-angle": (0.90, 1.10),
    "yield-controlled": (0.92, 1.08),
    "ultrasonic-preload": (0.95, 1.05),
}

TIGHTENING_METHODS = tuple(sorted(_METHOD_SCATTER))

# Methods that take the fastener past its elastic range.
PLASTIC_METHODS = ("yield-controlled",)

LOCKING_FRICTION = "friction-prevailing-torque"
LOCKING_ADHESIVE = "thread-locking-adhesive"
LOCKING_POSITIVE = "positive-mechanical-locking"
LOCKING_NONE = "none"

LOCKING_FEATURES = (
    LOCKING_NONE,
    LOCKING_FRICTION,
    LOCKING_ADHESIVE,
    LOCKING_POSITIVE,
)

# Features that hold by friction and therefore decay with use and
# vibration rather than obstructing rotation outright.
FRICTION_LOCKING = (LOCKING_FRICTION, LOCKING_ADHESIVE)

CONSEQUENCES = ("loss-of-mission", "loss-of-function", "degraded-performance",
                "cosmetic")

# Consequences severe enough that the locking has to obstruct rotation
# rather than resist it.
POSITIVE_LOCKING_CONSEQUENCES = ("loss-of-mission", "loss-of-function")

PASS = "pass"
FAIL = "fail"


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %s" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %s" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def tensile_stress_area(diameter_mm, pitch_mm):
    """Stress area of an ISO metric thread, in square millimetres."""
    diameter = _require_positive("diameter_mm", diameter_mm)
    pitch = _require_positive("pitch_mm", pitch_mm)
    if pitch >= diameter:
        raise ValueError(
            "pitch %s mm is not smaller than the diameter %s mm; that is not a "
            "thread" % (pitch_mm, diameter_mm)
        )
    effective = diameter - 0.9382 * pitch
    return math.pi / 4.0 * effective * effective


def proof_load_n(diameter_mm, pitch_mm, proof_stress_mpa):
    """Load at which the fastener starts to take a permanent set."""
    stress = _require_positive("proof_stress_mpa", proof_stress_mpa)
    return tensile_stress_area(diameter_mm, pitch_mm) * stress


def target_preload_n(diameter_mm, pitch_mm, proof_stress_mpa, utilisation):
    """Target preload as a fraction of the proof load."""
    fraction = _require_positive("utilisation", utilisation)
    if fraction > 1.0:
        raise ValueError(
            "utilisation %s targets a preload past the proof load; the joint "
            "cannot be designed to yield its own fasteners" % utilisation
        )
    return proof_load_n(diameter_mm, pitch_mm, proof_stress_mpa) * fraction


def tightening_scatter(method):
    """Low and high factors the method puts on the target preload."""
    _require_choice("method", method, TIGHTENING_METHODS)
    return _METHOD_SCATTER[method]


def preload_band_n(target_n, method):
    """Preload the joint actually sees, as a low and high pair."""
    target = _require_positive("target_n", target_n)
    low, high = tightening_scatter(method)
    return (target * low, target * high)


def torque_for_preload_nm(preload_n, diameter_mm, nut_factor):
    """Tightening torque for a preload, through the nut factor."""
    preload = _require_positive("preload_n", preload_n)
    diameter = _require_positive("diameter_mm", diameter_mm)
    factor = _require_positive("nut_factor", nut_factor)
    if factor > 0.5:
        raise ValueError(
            "nut factor %s is outside any lubricated or dry thread condition; "
            "check the units" % nut_factor
        )
    return factor * (diameter / 1000.0) * preload


def assess_preload_window(case):
    """Check the delivered preload band against both of its limits."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    diameter = _require_positive("diameter_mm", case.get("diameter_mm"))
    pitch = _require_positive("pitch_mm", case.get("pitch_mm"))
    stress = _require_positive("proof_stress_mpa", case.get("proof_stress_mpa"))
    utilisation = _require_positive("utilisation", case.get("utilisation"))
    method = _require_choice("method", case.get("method"), TIGHTENING_METHODS)
    separating = _require_non_negative(
        "separating_load_n", case.get("separating_load_n", 0.0)
    )
    proof = proof_load_n(diameter, pitch, stress)
    target = target_preload_n(diameter, pitch, stress, utilisation)
    low, high = preload_band_n(target, method)
    findings = []
    holds_closed = low >= separating * (1.0 - _REL_SLACK)
    under_proof = high <= proof * (1.0 + _REL_SLACK)
    if not holds_closed:
        findings.append(
            "the low end of the band, %.1f N, does not hold the joint closed "
            "against a separating load of %.1f N" % (low, separating)
        )
    if not under_proof:
        findings.append(
            "the high end of the band, %.1f N, passes the proof load of "
            "%.1f N" % (high, proof)
        )
    return {
        "proof_load_n": proof,
        "target_preload_n": target,
        "preload_low_n": low,
        "preload_high_n": high,
        "separating_load_n": separating,
        "method": method,
        "holds_joint_closed": holds_closed,
        "stays_under_proof": under_proof,
        "verdict": PASS if not findings else FAIL,
        "findings": findings,
    }


def locking_requirement(consequence, locking_feature):
    """Whether the locking provided is adequate for what failure costs."""
    _require_choice("consequence", consequence, CONSEQUENCES)
    _require_choice("locking_feature", locking_feature, LOCKING_FEATURES)
    positive_needed = consequence in POSITIVE_LOCKING_CONSEQUENCES
    if not positive_needed:
        adequate = locking_feature != LOCKING_NONE or consequence == "cosmetic"
        reason = "" if adequate else (
            "a joint whose loss degrades performance still needs some locking "
            "feature"
        )
        return {
            "positive_locking_required": False,
            "adequate": adequate,
            "reason": reason,
        }
    adequate = locking_feature == LOCKING_POSITIVE
    reason = "" if adequate else (
        "%s holds by friction and decays under the vibration that made the "
        "locking necessary; a %s consequence needs an obstruction to rotation"
        % (locking_feature, consequence)
    ) if locking_feature in FRICTION_LOCKING else (
        "a %s consequence cannot be left without a locking feature"
        % consequence
    )
    return {
        "positive_locking_required": True,
        "adequate": adequate,
        "reason": reason,
    }


def reuse_verdict(case):
    """Whether this fastener may be installed again, and why not."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    method = _require_choice(
        "method", case.get("method"), TIGHTENING_METHODS
    )
    locking_feature = _require_choice(
        "locking_feature", case.get("locking_feature"), LOCKING_FEATURES
    )
    cycles = _require_count("cycles_used", case.get("cycles_used", 0))
    findings = []
    if method in PLASTIC_METHODS:
        findings.append(
            "a fastener tightened by %s has no elastic range left and is "
            "single-use" % method
        )
    if locking_feature == LOCKING_ADHESIVE:
        findings.append(
            "a thread-locking adhesive is consumed on removal; the thread has "
            "to be cleaned and fresh adhesive applied, so the old feature does "
            "not carry over"
        )
    if locking_feature == LOCKING_FRICTION:
        measured = case.get("measured_prevailing_torque_nm")
        minimum = case.get("minimum_prevailing_torque_nm")
        if measured is None or minimum is None:
            raise ValueError(
                "a prevailing-torque feature needs both the measured and the "
                "minimum prevailing torque before reuse can be judged"
            )
        measured = _require_non_negative(
            "measured_prevailing_torque_nm", measured
        )
        minimum = _require_positive("minimum_prevailing_torque_nm", minimum)
        if measured < minimum * (1.0 - _REL_SLACK):
            findings.append(
                "the prevailing torque has decayed to %.3f N.m against a "
                "minimum of %.3f N.m" % (measured, minimum)
            )
    if cycles == 0:
        findings.append(
            "this fastener has no recorded installation, so the question is "
            "first use rather than reuse"
        )
    reusable = not [f for f in findings if "first use" not in f]
    return {
        "method": method,
        "locking_feature": locking_feature,
        "cycles_used": cycles,
        "reusable": reusable,
        "findings": findings,
    }


def plan_application(case):
    """Preload window, locking adequacy and reuse for one installation."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    preload = assess_preload_window(case)
    locking = locking_requirement(
        _require_choice("consequence", case.get("consequence"), CONSEQUENCES),
        _require_choice(
            "locking_feature", case.get("locking_feature"), LOCKING_FEATURES
        ),
    )
    nut_factor = case.get("nut_factor")
    torque = None
    if nut_factor is not None:
        torque = torque_for_preload_nm(
            preload["target_preload_n"], case["diameter_mm"], nut_factor
        )
    findings = list(preload["findings"])
    if not locking["adequate"]:
        findings.append(locking["reason"])
    reuse = None
    if case.get("is_reinstallation"):
        reuse = reuse_verdict(case)
        if not reuse["reusable"]:
            findings.extend(reuse["findings"])
    return {
        "preload": preload,
        "locking": locking,
        "target_torque_nm": torque,
        "reuse": reuse,
        "findings": findings,
        "verdict": PASS if not findings else FAIL,
    }
