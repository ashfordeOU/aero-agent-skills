"""Coverglass ultraviolet exposure: does the coating hold its optics.

Anchor: ECSS-E-ST-20-08C clause 8.7.12 (accelerated ageing of a coverglass
under ultraviolet light, read as whether the coverglass coatings stay
optically stable). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Turn the lamp setting and the exposure hours into equivalent sun hours,
   because the run is an accelerated mission only if the accumulated dose
   reaches the ultraviolet dose the mission itself delivers.
2. Refuse an acceleration factor above the reciprocity cap. Piling suns on to
   shorten the run stops being the same experiment once the lamp drives
   mechanisms the orbit never would.
3. Check the chamber held vacuum and the specimen held its temperature.
   Ultraviolet ageing in air is a different chemistry, and a hot specimen
   anneals while it is being aged.
4. Check the dark control that rode the run. It sees the handling, the mounts
   and the bench but not the lamp, so its drift is the floor under every
   number the exposed specimens produce.
5. Turn each post-exposure band transmittance into a retention factor and an
   absolute loss against the same specimen's own pre-exposure scan.
6. Judge the absolute loss band by band against the allowed loss, and weight
   the bands into one solar-weighted figure when weights are supplied.
7. Bound the delay between opening the chamber and taking the scan, because
   ultraviolet darkening bleaches back in air and a late scan reports a
   recovered specimen rather than an aged one.
8. Report dose, retentions, losses, findings and verdict; the run is
   conformant only with no finding.
"""

__all__ = [
    "BANDS",
    "TOLERANCE",
    "WEIGHT_SUM_TOLERANCE",
    "MAX_ACCELERATION_FACTOR",
    "MAX_CHAMBER_PRESSURE_PA",
    "TEMPERATURE_TOLERANCE_C",
    "MAX_CONTROL_DRIFT",
    "MAX_MEASUREMENT_DELAY_H",
    "MAX_TRANSMITTANCE_LOSS",
    "equivalent_sun_hours",
    "acceleration_findings",
    "dose_findings",
    "chamber_findings",
    "retention_factor",
    "band_retention",
    "band_loss",
    "solarisation_findings",
    "control_findings",
    "measurement_delay_findings",
    "solar_weighted_transmittance",
    "assess_coverglass_uv_exposure",
]

# The three bands the coverglass optics are read on.
BANDS = ("ultraviolet", "visible", "near-infrared")

# A value sitting exactly on a declared bound is conformant; the comparison
# absorbs representation error and the bound itself never moves.
TOLERANCE = 1e-9

# Supplied band weights are a distribution, so they must add to one.
WEIGHT_SUM_TOLERANCE = 1e-6

# Above this many ultraviolet suns the lamp is no longer a faster orbit.
MAX_ACCELERATION_FACTOR = 5.0

# Ultraviolet ageing is a vacuum test; above this pressure it is a different
# chemistry with a different answer.
MAX_CHAMBER_PRESSURE_PA = 1.0e-3

# The specimen may sit this far from the declared exposure temperature.
TEMPERATURE_TOLERANCE_C = 5.0

# A dark control that moved more than this took the bench, not the lamp.
MAX_CONTROL_DRIFT = 0.002

# Darkening bleaches in air, so the scan follows the run inside this window.
MAX_MEASUREMENT_DELAY_H = 24.0

# Allowed absolute drop in band transmittance across the exposure.
MAX_TRANSMITTANCE_LOSS = 0.02


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _non_negative(value, label):
    """Return value as a finite float that is not below zero."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _name(value, label):
    """Return a trimmed, non-empty identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("%s must not be empty" % label)
    return cleaned


def _band(value):
    """Return a validated optical band name."""
    name = _name(value, "band")
    if name not in BANDS:
        raise ValueError(
            "band must be one of %s, got '%s'" % (", ".join(BANDS), name)
        )
    return name


def _transmittance(value, label):
    """Return a transmittance as a fraction above zero and at most one."""
    number = _positive(value, label)
    if number > 1.0 + TOLERANCE:
        raise ValueError(
            "%s must be a fraction at or below one, got %g" % (label, number)
        )
    return min(number, 1.0)


def _scan(mapping, label):
    """Return a validated mapping of every band to a transmittance."""
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping of band to transmittance" % label)
    for key in mapping:
        _band(key)
    result = {}
    for key in BANDS:
        if key not in mapping:
            raise ValueError("%s is missing the '%s' band" % (label, key))
        result[key] = _transmittance(mapping[key], "%s '%s'" % (label, key))
    return result


def equivalent_sun_hours(uv_suns, hours):
    """Return the accumulated ultraviolet dose in equivalent sun hours."""
    suns = _positive(uv_suns, "uv_suns")
    duration = _positive(hours, "hours")
    return suns * duration


def acceleration_findings(uv_suns, max_factor=MAX_ACCELERATION_FACTOR):
    """Return findings where the lamp was driven past the reciprocity cap."""
    suns = _positive(uv_suns, "uv_suns")
    cap = _positive(max_factor, "max_factor")
    if suns > cap + TOLERANCE:
        return [
            "the lamp ran at %g ultraviolet suns, past the %g the reciprocity "
            "assumption holds to, so the ageing is no longer a faster orbit"
            % (suns, cap)
        ]
    return []


def dose_findings(accumulated_esh, required_esh):
    """Return findings where the run fell short of the mission dose."""
    accumulated = _positive(accumulated_esh, "accumulated_esh")
    required = _positive(required_esh, "required_esh")
    if accumulated < required - TOLERANCE:
        return [
            "the run accumulated %g equivalent sun hours against the %g the "
            "mission delivers, so the ageing is incomplete"
            % (accumulated, required)
        ]
    return []


def chamber_findings(exposure,
                     temperature_tolerance_c=TEMPERATURE_TOLERANCE_C,
                     max_pressure_pa=MAX_CHAMBER_PRESSURE_PA):
    """Return findings where the chamber did not hold the exposure state."""
    if not isinstance(exposure, dict):
        raise ValueError("exposure must be a mapping")
    for key in ("pressure_pa", "temperature_c", "reference_temperature_c"):
        if key not in exposure:
            raise ValueError("exposure missing key '%s'" % key)
    tolerance = _positive(temperature_tolerance_c, "temperature_tolerance_c")
    cap = _positive(max_pressure_pa, "max_pressure_pa")
    pressure = _positive(exposure["pressure_pa"], "pressure_pa")
    temperature = _real(exposure["temperature_c"], "temperature_c")
    declared = _real(exposure["reference_temperature_c"],
                     "reference_temperature_c")
    findings = []
    if pressure > cap + TOLERANCE:
        findings.append(
            "the chamber sat at %.3g Pa against the %.3g Pa the vacuum ageing "
            "needs, so the run aged the specimen in residual gas"
            % (pressure, cap)
        )
    if abs(temperature - declared) > tolerance + TOLERANCE:
        findings.append(
            "the specimen held %g C against the declared %g C, outside the "
            "%g C the exposure allows" % (temperature, declared, tolerance)
        )
    return findings


def retention_factor(after, before):
    """Return the fraction of a pre-exposure reading that survived."""
    aged = _transmittance(after, "after")
    start = _transmittance(before, "before")
    return aged / start


def band_retention(before_scan, after_scan):
    """Return each band's surviving fraction of its pre-exposure reading."""
    start = _scan(before_scan, "before_scan")
    aged = _scan(after_scan, "after_scan")
    return {key: aged[key] / start[key] for key in BANDS}


def band_loss(before_scan, after_scan):
    """Return each band's absolute drop in transmittance across the run."""
    start = _scan(before_scan, "before_scan")
    aged = _scan(after_scan, "after_scan")
    return {key: start[key] - aged[key] for key in BANDS}


def solarisation_findings(losses, max_loss=MAX_TRANSMITTANCE_LOSS):
    """Return findings where a band darkened past the allowed loss."""
    if not isinstance(losses, dict):
        raise ValueError("losses must be a mapping of band to loss")
    limit = _positive(max_loss, "max_loss")
    findings = []
    for key in BANDS:
        if key not in losses:
            raise ValueError("losses is missing the '%s' band" % key)
        drop = _real(losses[key], "loss '%s'" % key)
        if drop > limit + TOLERANCE:
            findings.append(
                "the %s band lost %.4f of its transmittance, past the %.4f "
                "the coating is allowed to darken" % (key, drop, limit)
            )
    return findings


def control_findings(before_scan, after_scan, max_drift=MAX_CONTROL_DRIFT):
    """Return findings where the dark control moved during the run."""
    allowance = _positive(max_drift, "max_drift")
    drifts = band_loss(before_scan, after_scan)
    findings = []
    for key in BANDS:
        if abs(drifts[key]) > allowance + TOLERANCE:
            findings.append(
                "the dark control moved %.4f in the %s band, past the %.4f "
                "the bench is allowed, so the exposed readings carry it too"
                % (drifts[key], key, allowance)
            )
    return findings


def measurement_delay_findings(delay_h, max_delay_h=MAX_MEASUREMENT_DELAY_H):
    """Return findings where the post-exposure scan was taken too late."""
    delay = _non_negative(delay_h, "delay_h")
    window = _positive(max_delay_h, "max_delay_h")
    if delay > window + TOLERANCE:
        return [
            "the scan followed the exposure by %g h, past the %g h window, so "
            "bleaching in air has flattered the result" % (delay, window)
        ]
    return []


def solar_weighted_transmittance(scan, weights):
    """Return one transmittance figure from the bands and their weights."""
    values = _scan(scan, "scan")
    if not isinstance(weights, dict):
        raise ValueError("weights must be a mapping of band to weight")
    for key in weights:
        _band(key)
    total = 0.0
    weighted = 0.0
    for key in BANDS:
        if key not in weights:
            raise ValueError("weights is missing the '%s' band" % key)
        share = _positive(weights[key], "weight '%s'" % key)
        total += share
        weighted += share * values[key]
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise ValueError("band weights must add to one, got %.9g" % total)
    return weighted


def assess_coverglass_uv_exposure(spec):
    """Run the full clause 8.7.12 coverglass ultraviolet exposure assessment.

    spec keys: specimen (label, before, after), control (label, before,
    after), exposure (uv_suns, hours, pressure_pa, temperature_c,
    reference_temperature_c), required_esh, measurement_delay_h; optional
    max_transmittance_loss, max_control_drift, temperature_tolerance_c,
    max_pressure_pa, max_acceleration_factor, max_delay_h, band_weights.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("specimen", "control", "exposure", "required_esh",
                "measurement_delay_h"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    specimen = spec["specimen"]
    control = spec["control"]
    exposure = spec["exposure"]
    for label, item in (("specimen", specimen), ("control", control)):
        if not isinstance(item, dict):
            raise ValueError("%s must be a mapping" % label)
        for key in ("label", "before", "after"):
            if key not in item:
                raise ValueError("%s missing key '%s'" % (label, key))
    if not isinstance(exposure, dict):
        raise ValueError("exposure must be a mapping")
    for key in ("uv_suns", "hours"):
        if key not in exposure:
            raise ValueError("exposure missing key '%s'" % key)

    tag = _name(specimen["label"], "specimen label")
    _name(control["label"], "control label")
    suns = _positive(exposure["uv_suns"], "uv_suns")
    dose = equivalent_sun_hours(suns, exposure["hours"])
    required = _positive(spec["required_esh"], "required_esh")

    findings = []
    findings.extend(
        acceleration_findings(
            suns, spec.get("max_acceleration_factor", MAX_ACCELERATION_FACTOR)
        )
    )
    findings.extend(dose_findings(dose, required))
    findings.extend(
        chamber_findings(
            exposure,
            spec.get("temperature_tolerance_c", TEMPERATURE_TOLERANCE_C),
            spec.get("max_pressure_pa", MAX_CHAMBER_PRESSURE_PA),
        )
    )
    findings.extend(
        control_findings(
            control["before"], control["after"],
            spec.get("max_control_drift", MAX_CONTROL_DRIFT),
        )
    )
    findings.extend(
        measurement_delay_findings(
            spec["measurement_delay_h"],
            spec.get("max_delay_h", MAX_MEASUREMENT_DELAY_H),
        )
    )

    retention = band_retention(specimen["before"], specimen["after"])
    losses = band_loss(specimen["before"], specimen["after"])
    findings.extend(
        solarisation_findings(
            losses, spec.get("max_transmittance_loss", MAX_TRANSMITTANCE_LOSS)
        )
    )

    weights = spec.get("band_weights")
    weighted_before = None
    weighted_after = None
    weighted_loss = None
    if weights is not None:
        weighted_before = solar_weighted_transmittance(
            specimen["before"], weights
        )
        weighted_after = solar_weighted_transmittance(
            specimen["after"], weights
        )
        weighted_loss = weighted_before - weighted_after

    return {
        "specimen": tag,
        "acceleration_factor": suns,
        "equivalent_sun_hours": dose,
        "required_esh": required,
        "band_retention": retention,
        "band_loss": losses,
        "solar_weighted_before": weighted_before,
        "solar_weighted_after": weighted_after,
        "solar_weighted_loss": weighted_loss,
        "findings": findings,
        "run_conformant": not findings,
    }
