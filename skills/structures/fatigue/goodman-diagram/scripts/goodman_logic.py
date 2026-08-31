#!/usr/bin/env python3
"""Mean-stress fatigue corrections (stdlib only).

Computes the allowable stress amplitude for infinite life under a
tensile mean stress for the three standard criteria:

  modified Goodman:  Sa = Se * (1 - Sm / Sut)
  Gerber:            Sa = Se * (1 - (Sm / Sut)**2)
  Soderberg:         Sa = Se * (1 - Sm / Sy)

with endurance limit Se, ultimate strength Sut, yield strength Sy,
mean stress Sm, applied amplitude Sa. Cycle conversion helpers give
mean stress, amplitude, and stress ratio R = Smin / Smax from the
cycle extrema. The Haigh diagram data helper returns the (Sm, Sa)
points of each criterion line for plotting. Generic mechanical
engineering methodology; FAR-25 / CS-25 are cited reference-only in
the skill, nothing here quotes either regulation.

Conventions: all stresses share one unit. Tensile mean stress is
assumed (Sm >= 0); positive allowable amplitudes shrink as the mean
stress grows and go non-positive when the mean stress reaches the
criterion's intercept. A non-positive allowable means no positive
amplitude satisfies infinite life under that criterion.
"""

import json
import math


def _require_positive(se, sut, sy):
    """Raise ValueError unless the material allowables are positive."""
    for value, label in ((se, "Se"), (sut, "Sut"), (sy, "Sy")):
        if not value > 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))


def _require_mean(sm, limit):
    """Raise ValueError unless the mean stress is non-negative and below
    the criterion intercept (Sut for Goodman/Gerber, Sy for Soderberg)
    at which the allowable amplitude reaches zero."""
    if sm < 0.0:
        raise ValueError("mean stress must be non-negative, got %r" % (sm,))
    if sm > limit:
        raise ValueError(
            "mean stress %r must not exceed the criterion intercept %r" % (sm, limit)
        )


def goodman_allowable(se, sut, sm):
    """Modified Goodman allowable amplitude Se * (1 - Sm / Sut)."""
    _require_positive(se, sut, sut)
    _require_mean(sm, sut)
    return se * (1.0 - sm / sut)


def gerber_allowable(se, sut, sm):
    """Gerber allowable amplitude Se * (1 - (Sm / Sut)**2)."""
    _require_positive(se, sut, sut)
    _require_mean(sm, sut)
    return se * (1.0 - (sm / sut) ** 2)


def soderberg_allowable(se, sut, sy, sm):
    """Soderberg allowable amplitude Se * (1 - Sm / Sy)."""
    _require_positive(se, sut, sy)
    _require_mean(sm, sy)
    return se * (1.0 - sm / sy)


def mean_and_amplitude(smax, smin):
    """Cycle mean stress Sm = (Smax + Smin) / 2 and stress amplitude
    Sa = (Smax - Smin) / 2. Raises ValueError unless Smax > Smin."""
    if not smax > smin:
        raise ValueError("Smax must exceed Smin, got %r and %r" % (smax, smin))
    return (smax + smin) / 2.0, (smax - smin) / 2.0


def stress_ratio(smax, smin):
    """Stress ratio R = Smin / Smax. Fully reversed loading is R = -1."""
    if smax == 0.0:
        raise ValueError("Smax is zero: stress ratio undefined")
    return smin / smax


def infinite_life_check(se, sut, sy, sm, sa):
    """Verdict for all three criteria at one (Sm, Sa) design point.

    Returns a dict with each criterion's allowable amplitude, margin
    (allowable - applied), pass flag, the governing (most restrictive)
    criterion, and an overall verdict. Non-positive allowables fail.
    """
    allowables = {
        "goodman": goodman_allowable(se, sut, sm),
        "gerber": gerber_allowable(se, sut, sm),
        "soderberg": soderberg_allowable(se, sut, sy, sm),
    }
    results = {}
    for criterion, allowable in allowables.items():
        ok = allowable > 0.0 and sa <= allowable
        results[criterion] = {
            "allowable_amplitude": allowable,
            "margin": allowable - sa,
            "pass": ok,
        }
    governing = min(allowables.items(), key=lambda kv: kv[1])[0]
    overall = all(results[c]["pass"] for c in allowables)
    return {
        "se": se,
        "sut": sut,
        "sy": sy,
        "mean_stress": sm,
        "applied_amplitude": sa,
        "stress_ratio": stress_ratio(sm + sa, sm - sa),
        "criteria": results,
        "governing_criterion": governing,
        "pass": overall,
    }


def haigh_diagram_points(se, sut, sy, sm_values):
    """Haigh diagram data: for each mean stress in sm_values, the
    allowable amplitude of each criterion line. Returns a dict of
    lists aligned with sm_values, ready to plot."""
    points = {"mean_stress": list(sm_values)}
    points["goodman"] = [
        goodman_allowable(se, sut, sm) for sm in sm_values
    ]
    points["gerber"] = [
        gerber_allowable(se, sut, sm) for sm in sm_values
    ]
    points["soderberg"] = [
        soderberg_allowable(se, sut, sy, sm) for sm in sm_values
    ]
    return points


def report_json(report):
    """JSON dump of an infinite_life_check report (round-trip safe)."""
    return json.dumps(report, sort_keys=True)


def _sm_max(se, sut, sy):
    """Largest mean stress at which every criterion still has a
    positive allowable (the Soderberg intercept Se-side cutoff is not
    relevant here; the yield intercept governs)."""
    return min(se, sut, sy)


def haigh_diagram_sample(se, sut, sy, n=9):
    """Evenly spaced mean stresses from 0 to the first criterion
    intercept for a smooth Haigh diagram plot."""
    _require_positive(se, sut, sy)
    if n < 2:
        raise ValueError("need at least 2 sample points, got %d" % n)
    top = _sm_max(se, sut, sy)
    step = top / (n - 1)
    return [i * step for i in range(n)]
