#!/usr/bin/env python3
"""Swept wing aerodynamics logic (simple sweep theory paraphrase).

Common-knowledge summary (standards-map.yaml, naca-tr-824: public
domain): simple sweep theory treats a yawed infinite wing as an
unswept wing at the velocity component normal to the leading edge. For
sweep angle Lambda in degrees the cosine of the sweep is cos(Lambda),
the section (effective) Mach number is M_eff = M * cos(Lambda), and
the velocity components are M_n = M * cos(Lambda) normal and
M_t = M * sin(Lambda) tangential to the leading edge. The lift curve
slope of the swept wing is a_swept = a0 * cos(Lambda) with a0 the
unswept section slope (2 * pi for thin sections). The critical Mach
number rises because the section behaves at the reduced effective
Mach: M_crit,swept = M_crit,0 / cos(Lambda), and the design form
Lambda = acos(M_crit,0 / M_crit,target) gives the sweep needed for a
target critical Mach. The cosine corrections are subsonic
small-disturbance results, valid for 0 <= Lambda < 90 degrees with the
effective Mach kept subsonic.
"""

import math


def _check_sweep(sweep_deg):
    if not (0.0 <= sweep_deg < 90.0):
        raise ValueError("sweep angle must be in [0, 90) degrees, got %r" % (sweep_deg,))


def _check_mach(mach):
    if not (0.0 <= mach < 1.0):
        raise ValueError("Mach number must be in [0, 1), got %r" % (mach,))


def cos_sweep(sweep_deg):
    """Cosine of the leading-edge sweep angle Lambda in degrees."""
    _check_sweep(sweep_deg)
    return math.cos(math.radians(sweep_deg))


def effective_mach(mach, sweep_deg):
    """Section Mach number seen by a yawed wing: M * cos(Lambda)."""
    _check_mach(mach)
    return mach * cos_sweep(sweep_deg)


def mach_components(mach, sweep_deg):
    """(normal, tangential) Mach components about the leading edge.

    Normal M_n = M * cos(Lambda), tangential M_t = M * sin(Lambda).
    """
    _check_mach(mach)
    _check_sweep(sweep_deg)
    lam = math.radians(sweep_deg)
    return (mach * math.cos(lam), mach * math.sin(lam))


def swept_lift_slope(a0, sweep_deg):
    """Swept wing lift curve slope per radian: a0 * cos(Lambda).

    a0 is the unswept section slope (2 * pi thin-airfoil value), per
    radian. Simple sweep theory first-order estimate for an infinite
    yawed wing; finite wings add planform corrections.
    """
    if not (a0 > 0.0):
        raise ValueError("section lift slope a0 must be positive, got %r" % (a0,))
    return a0 * cos_sweep(sweep_deg)


def critical_mach(mcrit0, sweep_deg):
    """Critical Mach number of the swept wing: mcrit0 / cos(Lambda).

    From the condition that the section reaches its critical Mach at
    the reduced effective Mach. Raises when the result reaches or
    exceeds 1: the wing would be transonic or supersonic there and the
    subsonic simple sweep theory no longer applies.
    """
    if not (0.0 < mcrit0 < 1.0):
        raise ValueError("unswept critical Mach must be in (0, 1), got %r" % (mcrit0,))
    mcrit = mcrit0 / cos_sweep(sweep_deg)
    if mcrit >= 1.0:
        raise ValueError(
            "swept critical Mach %r reaches 1; simple sweep theory is subsonic only"
            % (mcrit,)
        )
    return mcrit


def sweep_for_critical_mach(mcrit0, mcrit_target):
    """Sweep angle in degrees needed for a target critical Mach.

    Lambda = acos(mcrit0 / mcrit_target), valid when the target exceeds
    the unswept value and stays below 1.
    """
    if not (0.0 < mcrit0 < mcrit_target < 1.0):
        raise ValueError(
            "need 0 < mcrit0 < mcrit_target < 1, got (%r, %r)" % (mcrit0, mcrit_target)
        )
    return math.degrees(math.acos(mcrit0 / mcrit_target))
