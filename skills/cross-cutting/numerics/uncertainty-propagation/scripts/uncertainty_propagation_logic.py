"""Uncertainty propagation logic (GUM first order law, coverage factor).

Paraphrase of the standard measurement uncertainty procedure. NACA
Report 824 is the pack's public-domain anchor (standards-map.yaml);
the combined standard uncertainty follows the GUM (JCGM 100) first
order Taylor series law, which is generic measurement methodology, not
RTCA or SAE content.

Conventions: input i has sensitivity coefficient s_i = df/dx_i
evaluated at the operating point and standard uncertainty u_i (one
sigma). The combined standard uncertainty for independent inputs is
u_c = sqrt(sum_i (s_i * u_i)^2); the term (s_i * u_i)^2 is the
variance contribution of input i. The expanded uncertainty is
U = k * u_c with coverage factor k, 2.0 by convention (roughly 95
percent coverage for a normal distribution). The percent share of
input i is 100 * (s_i * u_i)^2 / u_c^2; shares sum to 100.

uncertainty_contributions returns per-input dicts sorted by
contribution magnitude descending; dominant_contribution reports the
largest share. The first order law assumes independent inputs;
correlated inputs need the full covariance form, which these functions
do not implement.

Units: sensitivities and uncertainties in any consistent unit system
(SI recommended); no unit conversion is performed. Negative
uncertainties are physically meaningless and raise ValueError; empty
or length-mismatched lists raise ValueError.
"""

import math


def _validate(sensitivities, uncertainties):
    """Shared input checks: non-empty, equal length, non-negative.

    Raises ValueError on any violation.
    """
    if not sensitivities or not uncertainties:
        raise ValueError("sensitivities and uncertainties must be non-empty")
    if len(sensitivities) != len(uncertainties):
        raise ValueError(
            "sensitivities and uncertainties must have equal length: got %d and %d"
            % (len(sensitivities), len(uncertainties))
        )
    for i, u in enumerate(uncertainties):
        if u < 0.0:
            raise ValueError(
                "uncertainties must be non-negative: got u[%d]=%r" % (i, u)
            )


def combined_standard_uncertainty(sensitivities, uncertainties):
    """Combined standard uncertainty u_c = sqrt(sum((s_i * u_i)^2)).

    GUM first order law for independent inputs. Raises ValueError when
    either list is empty, when lengths differ, or when any uncertainty
    is negative.
    """
    _validate(sensitivities, uncertainties)
    return math.sqrt(
        sum((s * u) ** 2 for s, u in zip(sensitivities, uncertainties))
    )


def expanded_uncertainty(combined, k=2.0):
    """Expanded uncertainty U = k * combined.

    Coverage factor k defaults to 2.0 (roughly 95 percent coverage for
    a normal distribution). Raises ValueError when k <= 0.
    """
    if k <= 0.0:
        raise ValueError("coverage factor k must be > 0: got k=%r" % (k,))
    return k * combined


def uncertainty_contributions(sensitivities, uncertainties):
    """Per-input variance contributions, sorted by magnitude descending.

    Each dict has 'index' (position in the input lists), 'sensitivity',
    'uncertainty', 'contribution' = (s_i * u_i)^2, and 'percent' =
    100 * contribution / total. When the total contribution is zero all
    percents are 0.0. Raises ValueError on empty lists, length
    mismatch, or negative uncertainties.
    """
    _validate(sensitivities, uncertainties)
    contribs = []
    total = 0.0
    for i, (s, u) in enumerate(zip(sensitivities, uncertainties)):
        c = (s * u) ** 2
        total += c
        contribs.append(
            {"index": i, "sensitivity": s, "uncertainty": u, "contribution": c}
        )
    for entry in contribs:
        if total == 0.0:
            entry["percent"] = 0.0
        else:
            entry["percent"] = 100.0 * entry["contribution"] / total
    contribs.sort(key=lambda e: e["contribution"], reverse=True)
    return contribs


def dominant_contribution(sensitivities, uncertainties):
    """Largest variance contribution as {'index', 'percent'}.

    Returns None when either input list is empty; raises ValueError on
    length mismatch or negative uncertainties. With a zero total the
    dominant share is 0.0 at index 0.
    """
    if not sensitivities or not uncertainties:
        return None
    _validate(sensitivities, uncertainties)
    top = uncertainty_contributions(sensitivities, uncertainties)[0]
    return {"index": top["index"], "percent": top["percent"]}
