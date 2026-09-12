"""
Parametric degradation from Displacement Damage (DD) — ECSS-E-ST-10-12C §8.6.

Paraphrased engineering procedure (not verbatim ECSS text):
1. Retrieve the displacement damage dose (DDD) at the shielded component location.
2. Select the curve model (power-law, exponential, or tabular) for the part lot.
3. Compute the normalized EOL parameter fraction P_eol/P_0 from the model.
4. Apply the radiation design margin factor to obtain the margin-adjusted fraction.
5. Compare the margin-adjusted fraction to the circuit minimum fraction;
   record a non-compliance finding when it falls short.
6. Raise an error when no curve is on record or the DDD is outside the
   characterized range.
"""

import math

SUPPORTED_MODELS = ("power_law", "exponential", "tabular")


def compute_degraded_fraction(model, params, ddd):
    """
    Return the normalized EOL parameter fraction P_eol/P_0 for a given DDD.

    model:
        "power_law"  — P_eol/P_0 = 1 − alpha * ddd**beta
                       params: {"alpha": float>=0, "beta": float>=0}
        "exponential" — P_eol/P_0 = exp(−k * ddd)
                        params: {"k": float>=0}
        "tabular"    — linear interpolation through (ddd_points, fraction_points)
                        params: {"ddd_points": list[float], "fraction_points": list[float]}
                        ddd_points must be sorted ascending.

    ddd: displacement damage dose (must be >= 0, consistent units with params).

    Raises ValueError for unsupported model, negative ddd, invalid params,
    or tabular ddd outside the characterized range.
    """
    if ddd < 0:
        raise ValueError(f"DDD must be non-negative, got {ddd}")

    if model == "power_law":
        alpha = params.get("alpha")
        beta = params.get("beta")
        if alpha is None or beta is None:
            raise ValueError("power_law requires 'alpha' and 'beta' in params")
        if alpha < 0:
            raise ValueError("power_law alpha must be non-negative")
        if beta < 0:
            raise ValueError("power_law beta must be non-negative")
        return 1.0 - alpha * (ddd ** beta)

    if model == "exponential":
        k = params.get("k")
        if k is None:
            raise ValueError("exponential requires 'k' in params")
        if k < 0:
            raise ValueError("exponential k must be non-negative")
        return math.exp(-k * ddd)

    if model == "tabular":
        ddd_pts = params.get("ddd_points")
        frac_pts = params.get("fraction_points")
        if ddd_pts is None or frac_pts is None:
            raise ValueError(
                "tabular requires 'ddd_points' and 'fraction_points' in params"
            )
        if len(ddd_pts) != len(frac_pts):
            raise ValueError(
                "ddd_points and fraction_points must have equal length"
            )
        if len(ddd_pts) < 2:
            raise ValueError("tabular model requires at least 2 data points")
        if ddd < ddd_pts[0] or ddd > ddd_pts[-1]:
            raise ValueError(
                f"DDD {ddd} is outside characterized range "
                f"[{ddd_pts[0]}, {ddd_pts[-1]}]; "
                "extend the curve before re-running the assessment"
            )
        for i in range(len(ddd_pts) - 1):
            if ddd_pts[i] <= ddd <= ddd_pts[i + 1]:
                span = ddd_pts[i + 1] - ddd_pts[i]
                if span == 0:
                    return frac_pts[i]
                t = (ddd - ddd_pts[i]) / span
                return frac_pts[i] + t * (frac_pts[i + 1] - frac_pts[i])
        return frac_pts[-1]

    raise ValueError(
        f"Unknown model '{model}'. Supported models: {SUPPORTED_MODELS}"
    )


def apply_margin(degraded_fraction, margin_factor):
    """
    Return the margin-adjusted EOL fraction.

    margin_adjusted = degraded_fraction / margin_factor

    A margin_factor > 1 is conservative (reduces the effective EOL fraction).
    Raises ValueError for non-positive margin_factor.
    """
    if margin_factor <= 0:
        raise ValueError(f"margin_factor must be positive, got {margin_factor}")
    return degraded_fraction / margin_factor


def check_dd_compliance(component_id, model, params, ddd, min_fraction, margin_factor=1.0):
    """
    Full DD parametric degradation compliance check for one component.

    Returns a result dict:
        component_id           — the identifier passed in
        ddd                    — displacement damage dose used
        degraded_fraction      — P_eol/P_0 from the curve model
        margin_adjusted_fraction — degraded_fraction / margin_factor
        min_fraction           — circuit minimum fraction required
        margin_factor          — margin factor applied
        compliant              — True if margin_adjusted_fraction >= min_fraction
        finding                — human-readable non-compliance description, or None

    Raises ValueError for bad inputs (propagated from sub-functions).
    """
    degraded = compute_degraded_fraction(model, params, ddd)
    adjusted = apply_margin(degraded, margin_factor)
    compliant = adjusted >= min_fraction
    finding = None
    if not compliant:
        finding = (
            f"margin-adjusted EOL fraction {adjusted:.4f} is below minimum "
            f"{min_fraction:.4f} (RDM factor {margin_factor}, DDD {ddd})"
        )
    return {
        "component_id": component_id,
        "ddd": ddd,
        "degraded_fraction": degraded,
        "margin_adjusted_fraction": adjusted,
        "min_fraction": min_fraction,
        "margin_factor": margin_factor,
        "compliant": compliant,
        "finding": finding,
    }


def assess_dd_degradation(component_records):
    """
    Assess a list of component records for DD parametric degradation compliance.

    Each record is a dict with keys:
        component_id  (str)    — part identifier
        model         (str)    — "power_law", "exponential", or "tabular"
        params        (dict)   — model-specific coefficient dictionary
        ddd           (float)  — displacement damage dose at the component location
        min_fraction  (float)  — circuit minimum as a fraction of BOL nominal
        margin_factor (float, optional, default 1.0) — radiation design margin factor

    Returns a list of result dicts (same structure as check_dd_compliance).

    Raises ValueError when the record list is empty, a model key is absent,
    or mandatory fields are missing.
    """
    if not component_records:
        raise ValueError("No component records provided")

    results = []
    for rec in component_records:
        cid = rec.get("component_id", "<unknown>")
        model = rec.get("model")
        if model is None:
            raise ValueError(
                f"Component '{cid}' has no degradation curve model on record"
            )
        params = rec.get("params", {})
        ddd = rec.get("ddd")
        if ddd is None:
            raise ValueError(f"Component '{cid}' has no DDD value")
        min_frac = rec.get("min_fraction")
        if min_frac is None:
            raise ValueError(
                f"Component '{cid}' has no min_fraction requirement"
            )
        margin = rec.get("margin_factor", 1.0)
        result = check_dd_compliance(cid, model, params, ddd, min_frac, margin)
        results.append(result)

    return results
