#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex G (informative) reference atmosphere data
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
Annex G points a mission engineer at empirical/semi-empirical
reference atmosphere models rather than defining an atmosphere model
itself. NRLMSISE-00 and JB-2006 are Earth thermosphere/exosphere
density models used for orbital drag and lifetime work; NRLMSISE-00
covers a broad density-reference role while JB-2006 is tuned for
higher-fidelity drag prediction; both require solar-activity and
geomagnetic-activity inputs to run. GRAM-class models (Earth-GRAM,
Mars-GRAM, Venus-GRAM, ...) give a full surface-to-orbit engineering
profile (including perturbation/Monte-Carlo variability) for a given
body. This module implements the model-applicability lookup by body
and altitude, the purpose-driven model-selection rule, the required-
input validation for a selected model, and an Earth altitude-regime
classification; it does not implement any model's internal density or
wind computation.
"""

EARTH = "earth"
MARS = "mars"
VENUS = "venus"
KNOWN_BODIES = frozenset({EARTH, MARS, VENUS})

DRAG_PREDICTION = "drag_prediction"
DENSITY_REFERENCE = "density_reference"
FULL_PROFILE = "full_profile"
KNOWN_PURPOSES = frozenset({DRAG_PREDICTION, DENSITY_REFERENCE, FULL_PROFILE})

# Model catalog: altitude coverage (km), body, and the inputs each model
# needs before it can be run. Ranges and input lists are reference data,
# not verbatim standard text.
MODEL_CATALOG = {
    "nrlmsise00": {
        "body": EARTH,
        "min_altitude_km": 0.0,
        "max_altitude_km": 1000.0,
        "required_inputs": frozenset(
            {"f10_7_solar_flux", "ap_geomagnetic_index", "day_of_year", "local_solar_time"}
        ),
    },
    "jb2006": {
        "body": EARTH,
        "min_altitude_km": 120.0,
        "max_altitude_km": 1000.0,
        "required_inputs": frozenset(
            {"f10_7_solar_flux", "s10_7_solar_index", "dst_geomagnetic_index", "day_of_year"}
        ),
    },
    "earth_gram": {
        "body": EARTH,
        "min_altitude_km": 0.0,
        "max_altitude_km": 1000.0,
        "required_inputs": frozenset({"date", "latitude_deg", "longitude_deg", "altitude_km"}),
    },
    "mars_gram": {
        "body": MARS,
        "min_altitude_km": 0.0,
        "max_altitude_km": 1000.0,
        "required_inputs": frozenset({"date", "latitude_deg", "longitude_deg", "altitude_km"}),
    },
    "venus_gram": {
        "body": VENUS,
        "min_altitude_km": 0.0,
        "max_altitude_km": 1000.0,
        "required_inputs": frozenset({"date", "latitude_deg", "longitude_deg", "altitude_km"}),
    },
}

# Earth atmospheric regime boundaries (km), lower bound inclusive, upper
# bound exclusive except for the final, open-ended regime.
ALTITUDE_REGIMES_KM = (
    ("troposphere", 0.0, 12.0),
    ("stratosphere", 12.0, 50.0),
    ("mesosphere", 50.0, 85.0),
    ("thermosphere", 85.0, 600.0),
    ("exosphere", 600.0, None),
)


def _require_known_model(model_id):
    if model_id not in MODEL_CATALOG:
        raise ValueError(
            "unrecognized atmosphere model %r under E-ST-10-04C Annex G" % (model_id,)
        )
    return MODEL_CATALOG[model_id]


def model_altitude_range(model_id):
    """(min_altitude_km, max_altitude_km) for a cataloged model. Raises
    ValueError for an unrecognized model_id."""
    entry = _require_known_model(model_id)
    return entry["min_altitude_km"], entry["max_altitude_km"]


def is_altitude_in_range(model_id, altitude_km):
    """True when altitude_km falls within the model's supported range
    (inclusive both ends). Raises ValueError for an unrecognized
    model_id or a negative altitude_km."""
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")
    min_km, max_km = model_altitude_range(model_id)
    return min_km <= altitude_km <= max_km


def models_for_body(body):
    """Sorted list of model ids in the catalog applicable to a
    celestial body. Raises ValueError for a body outside
    KNOWN_BODIES."""
    if body not in KNOWN_BODIES:
        raise ValueError("unrecognized body %r under E-ST-10-04C Annex G" % (body,))
    return sorted(
        model_id for model_id, entry in MODEL_CATALOG.items() if entry["body"] == body
    )


def select_atmosphere_model(body, altitude_km, purpose):
    """Select the reference model id for a body/altitude/purpose
    combination.

    Selection rule: a non-Earth body always uses its GRAM-class full-
    profile model, regardless of purpose, since NRLMSISE-00 and JB-2006
    are Earth-only. For Earth, drag_prediction prefers JB-2006 (falling
    back to NRLMSISE-00, then Earth-GRAM, on altitude coverage),
    density_reference prefers NRLMSISE-00 (falling back to Earth-GRAM),
    and full_profile always uses Earth-GRAM.

    Raises ValueError for an unrecognized body, an unrecognized
    purpose, a negative altitude_km, or an altitude no cataloged model
    for that body covers.
    """
    if purpose not in KNOWN_PURPOSES:
        raise ValueError("unrecognized purpose %r" % (purpose,))
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")
    candidates = models_for_body(body)

    if body != EARTH:
        ordered = candidates
    elif purpose == DRAG_PREDICTION:
        ordered = ["jb2006", "nrlmsise00", "earth_gram"]
    elif purpose == DENSITY_REFERENCE:
        ordered = ["nrlmsise00", "earth_gram"]
    else:
        ordered = ["earth_gram"]

    for model_id in ordered:
        if model_id in candidates and is_altitude_in_range(model_id, altitude_km):
            return model_id
    raise ValueError(
        "no cataloged model covers body=%r altitude_km=%r purpose=%r"
        % (body, altitude_km, purpose)
    )


def model_input_gaps(model_id, provided_inputs):
    """Sorted list of required input names missing from
    provided_inputs (empty when every requirement is satisfied). Does
    not mutate provided_inputs. Raises ValueError for an unrecognized
    model_id."""
    entry = _require_known_model(model_id)
    provided = set(provided_inputs)
    return sorted(entry["required_inputs"] - provided)


def classify_altitude_regime(altitude_km):
    """Earth atmospheric regime name (troposphere .. exosphere) for
    altitude_km. Raises ValueError for a negative altitude_km."""
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")
    for name, lower, upper in ALTITUDE_REGIMES_KM:
        if upper is None or altitude_km < upper:
            if altitude_km >= lower:
                return name
    raise ValueError("altitude_km %r outside defined regime table" % (altitude_km,))


def atmosphere_model_review(body, altitude_km, purpose, provided_inputs):
    """Full Annex G reference-model review for one lookup.

    Returns {"model_id": str | None, "issues": [...]}. When no
    cataloged model covers the body/altitude/purpose combination,
    model_id is None and issues carries a single "no_model_coverage"
    finding. Otherwise model_id is the selected model and issues
    carries one "missing_model_input" finding per unsatisfied
    requirement (empty when provided_inputs is complete). Raises
    ValueError only for structurally invalid input (unrecognized body,
    unrecognized purpose, or negative altitude_km) -- coverage gaps and
    input gaps are reported as findings, not raised.
    """
    if body not in KNOWN_BODIES:
        raise ValueError("unrecognized body %r under E-ST-10-04C Annex G" % (body,))
    if purpose not in KNOWN_PURPOSES:
        raise ValueError("unrecognized purpose %r" % (purpose,))
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")

    try:
        model_id = select_atmosphere_model(body, altitude_km, purpose)
    except ValueError:
        return {
            "model_id": None,
            "issues": [
                {
                    "issue": "no_model_coverage",
                    "body": body,
                    "altitude_km": altitude_km,
                    "purpose": purpose,
                }
            ],
        }

    issues = [
        {"issue": "missing_model_input", "model_id": model_id, "input": name}
        for name in model_input_gaps(model_id, provided_inputs)
    ]
    return {"model_id": model_id, "issues": issues}


def is_atmosphere_review_compliant(review):
    """True when an atmosphere_model_review result has a selected
    model and no outstanding issues."""
    return review["model_id"] is not None and len(review["issues"]) == 0
