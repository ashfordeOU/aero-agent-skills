"""
e1012_sensor_bg_margin_logic.py

Radiation-induced sensor background margin assessment.
Paraphrased procedure — no verbatim ECSS text.
Anchor: ECSS-E-ST-10C §5.5.4.
"""

VALID_PARTICLE_TYPES = frozenset({
    "proton",
    "electron",
    "heavy-ion",
    "cosmic-ray",
    "alpha",
    "neutron",
    "sep-proton",
})


def validate_population(pop):
    """
    Validate a single particle population dict.

    Required keys:
        particle_type  (str)   — one of VALID_PARTICLE_TYPES
        flux           (float) — particles/cm²/s, must be >= 0
        sensitive_area (float) — cm², must be > 0
        bg_conversion  (float) — counts/particle, must be >= 0

    Raises ValueError on any invalid value or unrecognised particle type.
    """
    required = {"particle_type", "flux", "sensitive_area", "bg_conversion"}
    missing = required - pop.keys()
    if missing:
        raise ValueError(f"Population missing required keys: {sorted(missing)}")

    if pop["particle_type"] not in VALID_PARTICLE_TYPES:
        raise ValueError(
            f"Unknown particle type '{pop['particle_type']}'. "
            f"Recognised types: {sorted(VALID_PARTICLE_TYPES)}"
        )

    if pop["flux"] < 0:
        raise ValueError(
            f"Particle flux must be >= 0, got {pop['flux']}"
        )

    if pop["sensitive_area"] <= 0:
        raise ValueError(
            f"Sensitive area must be > 0, got {pop['sensitive_area']}"
        )

    if pop["bg_conversion"] < 0:
        raise ValueError(
            f"Background conversion factor must be >= 0, got {pop['bg_conversion']}"
        )


def compute_population_background(pop, integration_time):
    """
    Raw background counts from one particle population.

    background_counts = flux [particles/cm²/s]
                      × sensitive_area [cm²]
                      × bg_conversion [counts/particle]
                      × integration_time [s]

    Parameters
    ----------
    pop : dict
        Validated population dict (keys: particle_type, flux,
        sensitive_area, bg_conversion).
    integration_time : float
        Exposure duration in seconds (>= 0).

    Returns
    -------
    float
        Raw background counts for this population over the integration.
    """
    return (
        pop["flux"]
        * pop["sensitive_area"]
        * pop["bg_conversion"]
        * integration_time
    )


def assess_sensor_background(
    sensor_id,
    populations,
    integration_time,
    margin_factor,
    budget,
):
    """
    Assess radiation-induced background margin for a sensor.

    Steps (ECSS-E-ST-10C §5.5.4):
    1. Validate all inputs and each particle population.
    2. Compute raw background counts per population.
    3. Sum all population contributions.
    4. Apply radiation design margin: margined = raw_total × margin_factor.
    5. Compare against budget; record exceedance and compliance flag.

    Parameters
    ----------
    sensor_id : str
        Non-empty identifier for the sensor under assessment.
    populations : list[dict]
        Each dict requires: particle_type (str), flux (float),
        sensitive_area (float), bg_conversion (float).
    integration_time : float
        Exposure duration in seconds; must be >= 0.
    margin_factor : float
        Radiation design margin multiplier; must be >= 1.0.
    budget : float
        Sensor's allowable background count budget; must be > 0.

    Returns
    -------
    dict with keys:
        sensor_id         (str)
        raw_background    (float) — total raw counts, pre-margin
        margined_background (float) — raw × margin_factor
        margin_factor     (float)
        budget            (float)
        compliant         (bool)  — True when margined_background <= budget
        exceedance        (float) — max(0, margined_background - budget)
        population_details (list[dict]) — per-population breakdown
    """
    if not isinstance(sensor_id, str) or not sensor_id:
        raise ValueError("sensor_id must be a non-empty string")

    if not isinstance(populations, list):
        raise ValueError("populations must be a list of dicts")

    if integration_time < 0:
        raise ValueError(
            f"integration_time must be >= 0, got {integration_time}"
        )

    if margin_factor < 1.0:
        raise ValueError(
            f"margin_factor must be >= 1.0 (no sub-unity margins per §5.5.4), "
            f"got {margin_factor}"
        )

    if budget <= 0:
        raise ValueError(f"budget must be > 0, got {budget}")

    population_details = []
    raw_total = 0.0

    for pop in populations:
        validate_population(pop)
        raw_counts = compute_population_background(pop, integration_time)
        raw_total += raw_counts
        population_details.append({
            "particle_type": pop["particle_type"],
            "raw_counts": raw_counts,
        })

    margined = raw_total * margin_factor
    exceedance = max(0.0, margined - budget)
    compliant = margined <= budget

    return {
        "sensor_id": sensor_id,
        "raw_background": raw_total,
        "margined_background": margined,
        "margin_factor": margin_factor,
        "budget": budget,
        "compliant": compliant,
        "exceedance": exceedance,
        "population_details": population_details,
    }
