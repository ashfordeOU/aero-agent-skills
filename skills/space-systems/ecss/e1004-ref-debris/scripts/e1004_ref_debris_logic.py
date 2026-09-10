"""Meteoroid and orbital-debris flux model reference data per
ECSS-E-ST-10-04C Annex J (info).

Implements a reference registry of illustrative meteoroid and
orbital-debris engineering flux models, each with an applicability
envelope (altitude, epoch, particle diameter) and an uncertainty
factor, plus the applicability-check, model-selection, and
uncertainty-bounding logic a mission engineer runs before trusting a
model's flux output. See SKILL.md "Data provenance and fidelity
notice" for the calibration caveat on the embedded registry.
"""

MODEL_FAMILIES = frozenset({"meteoroid", "debris"})

# Illustrative flux-model registry. Each entry's "family" is
# "meteoroid" (natural, effectively time-invariant population) or
# "debris" (anthropogenic, altitude- and epoch-dependent population).
# Range tuples are inclusive (lo, hi). uncertainty_factor is the
# multiplicative band applied to a nominal flux value.
MODELS = {
    "grun_interplanetary": {
        "family": "meteoroid",
        "altitude_km": (100.0, 2_000_000.0),
        "epoch_year": (1985, 2100),
        "diameter_m": (1e-6, 1.0),
        "uncertainty_factor": 3.0,
    },
    "ordem": {
        "family": "debris",
        "altitude_km": (200.0, 2000.0),
        "epoch_year": (1990, 2035),
        "diameter_m": (1e-5, 1.0),
        "uncertainty_factor": 2.0,
    },
    "master": {
        "family": "debris",
        "altitude_km": (200.0, 40000.0),
        "epoch_year": (1990, 2060),
        "diameter_m": (1e-6, 10.0),
        "uncertainty_factor": 2.5,
    },
}


def model_names():
    """Return the sorted names of every registered flux model."""
    return sorted(MODELS)


def _model(model_name):
    """Return the registry entry for model_name. Raises ValueError for
    an unregistered name."""
    if model_name not in MODELS:
        raise ValueError(
            "unknown flux model %r; known models: %s"
            % (model_name, model_names())
        )
    return MODELS[model_name]


def classify_object_family(object_family):
    """Return object_family if it is a known family ("meteoroid" or
    "debris"). Raises ValueError otherwise."""
    if object_family not in MODEL_FAMILIES:
        raise ValueError(
            "unrecognized object family %r under E-ST-10-04C Annex J; "
            "known families: %s" % (object_family, sorted(MODEL_FAMILIES))
        )
    return object_family


def applicability_gaps(model_name, object_family, altitude_km, epoch_year, diameter_m):
    """Return a dict of the dimensions of model_name's applicability
    envelope that the case falls outside of. Keys present only for
    dimensions that fail: "family" -> (given, expected), "altitude_km"
    / "epoch_year" / "diameter_m" -> (given, (lo, hi)). An empty dict
    means the model is fully applicable to the case. Raises ValueError
    for an unregistered model_name."""
    model = _model(model_name)
    gaps = {}
    if object_family != model["family"]:
        gaps["family"] = (object_family, model["family"])
    for field, value in (
        ("altitude_km", altitude_km),
        ("epoch_year", epoch_year),
        ("diameter_m", diameter_m),
    ):
        lo, hi = model[field]
        if not (lo <= value <= hi):
            gaps[field] = (value, (lo, hi))
    return gaps


def is_model_applicable(gaps):
    """True when applicability_gaps returned an empty dict -- the case
    is fully inside the model's envelope."""
    return len(gaps) == 0


def applicable_models(object_family, altitude_km, epoch_year, diameter_m):
    """Return the sorted names of every registered model whose
    envelope covers the case. Raises ValueError for an unrecognized
    object_family."""
    classify_object_family(object_family)
    return sorted(
        name
        for name in MODELS
        if is_model_applicable(
            applicability_gaps(name, object_family, altitude_km, epoch_year, diameter_m)
        )
    )


def recommend_model(object_family, altitude_km, epoch_year, diameter_m):
    """Return the applicable model with the lowest uncertainty_factor
    for the case. Raises ValueError when no registered model's
    envelope covers the case, or for an unrecognized object_family."""
    candidates = applicable_models(object_family, altitude_km, epoch_year, diameter_m)
    if not candidates:
        raise ValueError(
            "no registered flux model covers family=%r altitude_km=%r "
            "epoch_year=%r diameter_m=%r"
            % (object_family, altitude_km, epoch_year, diameter_m)
        )
    return min(candidates, key=lambda name: MODELS[name]["uncertainty_factor"])


def uncertainty_bounds(model_name, nominal_flux):
    """Return (low, high) bounds for nominal_flux using model_name's
    uncertainty_factor: (nominal_flux / factor, nominal_flux * factor).
    Raises ValueError for a negative nominal_flux or an unregistered
    model_name."""
    model = _model(model_name)
    if nominal_flux < 0:
        raise ValueError("nominal_flux must be >= 0, got %r" % (nominal_flux,))
    factor = model["uncertainty_factor"]
    return (nominal_flux / factor, nominal_flux * factor)


def cross_check_reported_flux(
    model_name, object_family, altitude_km, epoch_year, diameter_m, reported_flux
):
    """Cross-check a reported flux value against the model it claims
    to come from.

    Returns {"issue": "reported_flux_outside_model_envelope", "model":
    model_name, "gaps": {...}} when the case falls outside model_name's
    applicability envelope (the reported flux cannot be trusted as-is).
    Otherwise returns {"issue": None, "model": model_name,
    "uncertainty_low": ..., "uncertainty_high": ...}. Raises ValueError
    for an unregistered model_name or a negative reported_flux."""
    gaps = applicability_gaps(model_name, object_family, altitude_km, epoch_year, diameter_m)
    if gaps:
        return {"issue": "reported_flux_outside_model_envelope", "model": model_name, "gaps": gaps}
    low, high = uncertainty_bounds(model_name, reported_flux)
    return {
        "issue": None,
        "model": model_name,
        "uncertainty_low": low,
        "uncertainty_high": high,
    }
