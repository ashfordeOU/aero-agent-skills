#!/usr/bin/env python3
"""Lamina failure criteria under plane stress: Tsai-Wu, Tsai-Hill, and
max-stress failure indices (paraphrase, common knowledge).

UNITS: every stress and allowable is in MPa (megapascals), consistently.
s1: fiber-direction stress, s2: transverse stress, t12: in-plane shear
stress. s1 and s2 are signed (tension positive), t12 enters by
magnitude. Allowables (all > 0, MPa): Xt tensile, Xc compressive along
the fiber, Yt tensile, Yc compressive transverse, S in-plane shear.
A failure index >= 1.0 means the ply fails that criterion.

Common-knowledge summary (standards-map.yaml, far-25: public-domain
regulation context): composite airframe certification under 14 CFR
Part 25 builds on statistically based ply allowables; the criteria
below are the standard strength-of-materials checks that compare a
ply stress state with those allowables.
"""

import math


def _check_allowables(Xt, Xc, Yt, Yc, S):
    """Raise ValueError if any allowable is not > 0 MPa."""
    for key, value in (("Xt", Xt), ("Xc", Xc), ("Yt", Yt),
                       ("Yc", Yc), ("S", S)):
        if value <= 0:
            raise ValueError(
                "allowable %s must be > 0 MPa, got %r" % (key, value))


def tsai_wu_index(s1, s2, t12, Xt, Xc, Yt, Yc, S):
    """Tsai-Wu failure index, F.I. = F1 s1 + F2 s2 + F11 s1^2 +
    F22 s2^2 + F66 t12^2 + 2 F12 s1 s2, with F1 = 1/Xt - 1/Xc,
    F2 = 1/Yt - 1/Yc, F11 = 1/(Xt Xc), F22 = 1/(Yt Yc), F66 = 1/S^2,
    and F12 = -0.5 sqrt(F11 F22) (standard choice, documented)."""
    _check_allowables(Xt, Xc, Yt, Yc, S)
    f1 = 1.0 / Xt - 1.0 / Xc
    f2 = 1.0 / Yt - 1.0 / Yc
    f11 = 1.0 / (Xt * Xc)
    f22 = 1.0 / (Yt * Yc)
    f66 = 1.0 / (S * S)
    f12 = -0.5 * math.sqrt(f11 * f22)
    return (f1 * s1 + f2 * s2 + f11 * s1 * s1 + f22 * s2 * s2
            + f66 * t12 * t12 + 2.0 * f12 * s1 * s2)


def tsai_hill_index(s1, s2, t12, Xt, Xc, Yt, Yc, S):
    """Tsai-Hill failure index, tension convention:
    (s1/Xt)^2 - (s1 s2)/Xt^2 + (s2/Yt)^2 + (t12/S)^2.
    Xc and Yc are validated but not used in this classic form."""
    _check_allowables(Xt, Xc, Yt, Yc, S)
    return ((s1 / Xt) ** 2 - (s1 * s2) / (Xt * Xt)
            + (s2 / Yt) ** 2 + (t12 / S) ** 2)


def max_stress_index(s1, s2, t12, Xt, Xc, Yt, Yc, S):
    """Max-stress failure index: the largest of the three component
    ratios |s1|/Xt or |s1|/Xc by sign, |s2|/Yt or |s2|/Yc by sign,
    and |t12|/S."""
    _check_allowables(Xt, Xc, Yt, Yc, S)
    r1 = abs(s1) / (Xt if s1 >= 0.0 else Xc)
    r2 = abs(s2) / (Yt if s2 >= 0.0 else Yc)
    r12 = abs(t12) / S
    return max(r1, r2, r12)


def failure_verdict(s1, s2, t12, allowables):
    """Verdict dict: per-criterion indices, the governing criterion
    (largest index), and the overall failure flag (any index >= 1.0).
    allowables is a dict with keys Xt, Xc, Yt, Yc, S, all in MPa."""
    tw = tsai_wu_index(s1, s2, t12, allowables["Xt"], allowables["Xc"],
                       allowables["Yt"], allowables["Yc"], allowables["S"])
    th = tsai_hill_index(s1, s2, t12, allowables["Xt"], allowables["Xc"],
                         allowables["Yt"], allowables["Yc"], allowables["S"])
    ms = max_stress_index(s1, s2, t12, allowables["Xt"], allowables["Xc"],
                          allowables["Yt"], allowables["Yc"], allowables["S"])
    criteria = (("tsai-wu", tw), ("tsai-hill", th), ("max-stress", ms))
    governing = max(criteria, key=lambda pair: pair[1])[0]
    return {
        "tsai_wu": tw,
        "tsai_hill": th,
        "max_stress": ms,
        "governing": governing,
        "failure": any(index >= 1.0 for _, index in criteria),
    }
