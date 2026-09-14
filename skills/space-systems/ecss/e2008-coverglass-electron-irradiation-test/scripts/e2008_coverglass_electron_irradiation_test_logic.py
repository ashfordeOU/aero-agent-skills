"""Coverglass electron irradiation: how far the beam darkens the optics.

Anchor: ECSS-E-ST-20-08C clause 8.7.13 (accelerated ageing of a coverglass
under electron bombardment, read as the stability of the coverglass coatings
and of the glass beneath them). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the beam energy doses the whole coverglass. An electron whose range
   dies inside the article front-loads the damage into a surface layer and
   darkens a specimen the mission would have darkened evenly; an electron of
   far too high an energy crosses so freely that the fluence needed to reach
   the mission dose is out of reach of the beam line.
2. Turn each step's fluence into an absorbed dose through the glass, because
   coloured-centre growth follows the energy the glass took, not the count of
   particles that delivered it.
3. Divide each step's fluence by its beam-on time and hold the flux under the
   cap. A beam delivered too fast charges an insulating coverglass and heats
   it, and both anneal or crack what the mission would simply accumulate.
4. Require the conductive coating to be grounded when one is declared, since
   an ungrounded conductive face collects the beam and discharges through the
   article rather than ageing under it.
5. Turn each fluence step's band transmittance into an optical density against
   the unirradiated scan. Darkening adds in density, not in transmittance,
   which is why the density is the quantity that gets fitted.
6. Refuse a density that falls as fluence rises: electron damage in glass does
   not undo itself between steps, so a fall is the bench, a remount or a
   bleached specimen, and it invalidates the step.
7. Fit the density as a power law in fluence by least squares on the logarithm
   of both, because coloured-centre growth saturates and a straight line in
   fluence throws the low-fluence points away. A band that never darkened
   carries no power law, and it is reported as unfitted rather than as zero.
8. Project the density at the mission end-of-life fluence, convert it back to
   a transmittance, and compare that with what the power budget requires.
9. Report densities, fit, projection, findings and verdict; the run is
   conformant only with no finding.
"""

import math

__all__ = [
    "BANDS",
    "TOLERANCE",
    "MIN_DENSITY",
    "DENSITY_NOISE_ALLOWANCE",
    "MAX_FLUX_E_PER_CM2_S",
    "MIN_TRAVERSAL_RATIO",
    "MAX_TRAVERSAL_RATIO",
    "RANGE_DENSITY_G_PER_CM3",
    "STOPPING_POWER_MEV_CM2_G",
    "GRAY_PER_MEV_PER_GRAM",
    "electron_range_um",
    "traversal_ratio",
    "absorbed_dose_gy",
    "energy_findings",
    "beam_flux",
    "flux_findings",
    "grounding_findings",
    "optical_density",
    "density_series",
    "density_monotonicity_findings",
    "fit_density_power_law",
    "predict_density",
    "transmittance_from_density",
    "assess_coverglass_electron_irradiation",
]

# The bands the coverglass optics are read on.
BANDS = ("ultraviolet", "visible", "near-infrared")

# A value sitting exactly on a declared bound is conformant; the comparison
# absorbs representation error and the bound itself never moves.
TOLERANCE = 1e-9

# A power-law fit is taken on logarithms, so a density has to be above zero.
MIN_DENSITY = 1e-9

# A density may fall this far between steps before the fall is the specimen
# rather than the measurement.
DENSITY_NOISE_ALLOWANCE = 0.0005

# Above this flux the beam charges and heats the glass instead of ageing it.
MAX_FLUX_E_PER_CM2_S = 1.0e10

# The electron range must be at least this many coverglass thicknesses, or
# the beam stops inside the article and front-loads the damage.
MIN_TRAVERSAL_RATIO = 1.0

# Past this many thicknesses each electron leaves so little behind that the
# fluence needed for the mission dose is out of reach of the beam line.
MAX_TRAVERSAL_RATIO = 100.0

# Density of a fused-silica-like coverglass, used to turn the mass range the
# empirical fit returns into a depth. Override it for a doped glass.
RANGE_DENSITY_G_PER_CM3 = 2.2

# Collision stopping power of a fused-silica-like glass around a megaelectron-
# volt, used to turn a fluence into the dose the glass actually took.
STOPPING_POWER_MEV_CM2_G = 1.85

# One megaelectronvolt deposited per gram, expressed in gray.
GRAY_PER_MEV_PER_GRAM = 1.602e-10


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
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


def _rising(values, label):
    """Return a validated, strictly rising sequence of positive floats."""
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        raise ValueError("%s needs at least two points to fit against" % label)
    steps = [_positive(value, label) for value in values]
    for earlier, later in zip(steps, steps[1:]):
        if later <= earlier:
            raise ValueError(
                "%s must strictly rise, got %g after %g" % (label, later, earlier)
            )
    return steps


def electron_range_um(energy_mev, density_g_cm3=RANGE_DENSITY_G_PER_CM3):
    """Return how deep into the coverglass an electron of this energy reaches.

    Empirical continuous-slowing-down fit for light oxides in the tenth-of-a-
    megaelectronvolt to few-megaelectronvolt band, returned as a depth rather
    than a mass thickness so it can be compared with the glass directly.
    """
    energy = _positive(energy_mev, "energy_mev")
    density = _positive(density_g_cm3, "density_g_cm3")
    exponent = 1.265 - 0.0954 * math.log(energy)
    mass_range = 0.412 * math.pow(energy, exponent)
    return mass_range / density * 1.0e4


def traversal_ratio(energy_mev, coating_thickness_um, glass_thickness_um,
                    density_g_cm3=RANGE_DENSITY_G_PER_CM3):
    """Return how many coverglass thicknesses the electron range spans."""
    coating = _positive(coating_thickness_um, "coating_thickness_um")
    glass = _positive(glass_thickness_um, "glass_thickness_um")
    depth = electron_range_um(energy_mev, density_g_cm3)
    return depth / (coating + glass)


def absorbed_dose_gy(fluence_e_per_cm2,
                     stopping_power_mev_cm2_g=STOPPING_POWER_MEV_CM2_G):
    """Return the dose a fluence leaves in the glass, in gray."""
    fluence = _positive(fluence_e_per_cm2, "fluence_e_per_cm2")
    stopping = _positive(stopping_power_mev_cm2_g, "stopping_power_mev_cm2_g")
    return fluence * stopping * GRAY_PER_MEV_PER_GRAM


def energy_findings(energy_mev, coating_thickness_um, glass_thickness_um,
                    density_g_cm3=RANGE_DENSITY_G_PER_CM3,
                    min_ratio=MIN_TRAVERSAL_RATIO,
                    max_ratio=MAX_TRAVERSAL_RATIO):
    """Return findings where the beam does not dose the whole coverglass."""
    floor = _positive(min_ratio, "min_ratio")
    ceiling = _positive(max_ratio, "max_ratio")
    if ceiling <= floor:
        raise ValueError("max_ratio must sit above min_ratio")
    energy = _positive(energy_mev, "energy_mev")
    ratio = traversal_ratio(
        energy, coating_thickness_um, glass_thickness_um, density_g_cm3
    )
    findings = []
    if ratio < floor - TOLERANCE:
        findings.append(
            "a %g MeV beam spans %.3g coverglass thicknesses, under the %g it "
            "takes to cross the article, so the damage is front-loaded into a "
            "surface layer" % (energy, ratio, floor)
        )
    if ratio > ceiling + TOLERANCE:
        findings.append(
            "a %g MeV beam spans %.3g coverglass thicknesses, past the %g the "
            "beam line can dose to, so each electron leaves too little behind"
            % (energy, ratio, ceiling)
        )
    return findings


def beam_flux(fluence_e_per_cm2, duration_s):
    """Return the delivered electron flux of one exposure step."""
    fluence = _positive(fluence_e_per_cm2, "fluence_e_per_cm2")
    duration = _positive(duration_s, "duration_s")
    return fluence / duration


def flux_findings(label, fluence_e_per_cm2, duration_s,
                  max_flux=MAX_FLUX_E_PER_CM2_S):
    """Return findings where a step was delivered faster than the cap."""
    tag = _name(label, "label")
    cap = _positive(max_flux, "max_flux")
    flux = beam_flux(fluence_e_per_cm2, duration_s)
    if flux > cap + TOLERANCE:
        return [
            "step '%s' ran at %.3g e/cm2/s against the %.3g e/cm2/s cap, fast "
            "enough to charge and heat the glass rather than age it"
            % (tag, flux, cap)
        ]
    return []


def grounding_findings(coating_is_conductive, coating_is_grounded):
    """Return findings where a conductive coating rode the beam ungrounded."""
    for label, flag in (("coating_is_conductive", coating_is_conductive),
                        ("coating_is_grounded", coating_is_grounded)):
        if not isinstance(flag, bool):
            raise ValueError("%s must be a boolean, got %r" % (label, flag))
    if coating_is_conductive and not coating_is_grounded:
        return [
            "the conductive coating was not grounded, so it collected the beam "
            "and discharged through the article instead of ageing under it"
        ]
    return []


def optical_density(transmittance, reference_transmittance):
    """Return the darkening of one reading against the unirradiated scan."""
    measured = _transmittance(transmittance, "transmittance")
    base = _transmittance(reference_transmittance, "reference_transmittance")
    return -math.log10(measured / base)


def density_series(reference_scan, step_scans):
    """Return each band's optical density across the fluence steps."""
    base = _scan(reference_scan, "reference_scan")
    if not isinstance(step_scans, (list, tuple)) or not step_scans:
        raise ValueError("step_scans must be a non-empty sequence of scans")
    series = {key: [] for key in BANDS}
    for index, scan in enumerate(step_scans):
        values = _scan(scan, "step %d scan" % (index + 1))
        for key in BANDS:
            series[key].append(optical_density(values[key], base[key]))
    return series


def density_monotonicity_findings(band, fluences, densities,
                                  noise_allowance=DENSITY_NOISE_ALLOWANCE):
    """Return findings where the darkening undid itself between steps."""
    name = _band(band)
    steps = _rising(fluences, "fluence_e_per_cm2")
    if not isinstance(densities, (list, tuple)) or len(densities) != len(steps):
        raise ValueError("one optical density is needed per fluence step")
    allowance = _positive(noise_allowance, "noise_allowance")
    values = [_real(value, "optical density") for value in densities]
    findings = []
    for index, value in enumerate(values):
        if value < -allowance - TOLERANCE:
            findings.append(
                "the %s band reads %.4f density at %.3g e/cm2, brighter than "
                "its unirradiated scan" % (name, value, steps[index])
            )
    for index in range(1, len(values)):
        fall = values[index - 1] - values[index]
        if fall > allowance + TOLERANCE:
            findings.append(
                "the %s band lightened from %.4f to %.4f density between %.3g "
                "and %.3g e/cm2, which electron damage does not do"
                % (name, values[index - 1], values[index],
                   steps[index - 1], steps[index])
            )
    return findings


def fit_density_power_law(fluences, densities):
    """Return the least-squares power law of density against fluence."""
    steps = _rising(fluences, "fluence_e_per_cm2")
    if not isinstance(densities, (list, tuple)) or len(densities) != len(steps):
        raise ValueError("one optical density is needed per fluence step")
    values = []
    for value in densities:
        number = _real(value, "optical density")
        if number < MIN_DENSITY:
            raise ValueError(
                "a power-law fit needs a density above %g, got %g"
                % (MIN_DENSITY, number)
            )
        values.append(number)
    log_steps = [math.log(step) for step in steps]
    log_values = [math.log(value) for value in values]
    count = len(log_steps)
    mean_step = sum(log_steps) / count
    mean_value = sum(log_values) / count
    covariance = sum(
        (step - mean_step) * (value - mean_value)
        for step, value in zip(log_steps, log_values)
    )
    spread = sum((step - mean_step) ** 2 for step in log_steps)
    if spread <= 0.0:
        raise ValueError("the fluence steps carry no spread to fit against")
    exponent = covariance / spread
    log_coefficient = mean_value - exponent * mean_step
    return {
        "exponent": exponent,
        "log_coefficient": log_coefficient,
        "point_count": count,
    }


def predict_density(fit, fluence_e_per_cm2):
    """Return the optical density the fit puts at a given fluence."""
    if not isinstance(fit, dict):
        raise ValueError("fit must be a mapping with exponent and coefficient")
    for key in ("exponent", "log_coefficient"):
        if key not in fit:
            raise ValueError("fit missing key '%s'" % key)
    exponent = _real(fit["exponent"], "exponent")
    log_coefficient = _real(fit["log_coefficient"], "log_coefficient")
    point = _positive(fluence_e_per_cm2, "fluence_e_per_cm2")
    return math.exp(log_coefficient + exponent * math.log(point))


def transmittance_from_density(reference_transmittance, density):
    """Return the transmittance left once a darkening density is applied."""
    base = _transmittance(reference_transmittance, "reference_transmittance")
    amount = _real(density, "density")
    return base * math.pow(10.0, -amount)


def assess_coverglass_electron_irradiation(spec):
    """Run the full clause 8.7.13 coverglass electron irradiation assessment.

    spec keys: reference_scan, steps (label, fluence_e_per_cm2, duration_s,
    scan), beam_energy_mev, coating_thickness_um, glass_thickness_um,
    eol_fluence_e_per_cm2, required_transmittance (band to fraction);
    optional coating_is_conductive, coating_is_grounded, max_flux,
    noise_allowance, glass_density_g_cm3, stopping_power_mev_cm2_g,
    min_traversal_ratio, max_traversal_ratio.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("reference_scan", "steps", "beam_energy_mev",
                "coating_thickness_um", "glass_thickness_um",
                "eol_fluence_e_per_cm2", "required_transmittance"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    steps = spec["steps"]
    if not isinstance(steps, (list, tuple)) or len(steps) < 2:
        raise ValueError("steps must carry at least two fluence points")
    required = spec["required_transmittance"]
    if not isinstance(required, dict) or not required:
        raise ValueError("required_transmittance must name at least one band")
    for key in required:
        _band(key)

    reference = _scan(spec["reference_scan"], "reference_scan")
    findings = []
    findings.extend(
        energy_findings(
            spec["beam_energy_mev"],
            spec["coating_thickness_um"],
            spec["glass_thickness_um"],
            spec.get("glass_density_g_cm3", RANGE_DENSITY_G_PER_CM3),
            spec.get("min_traversal_ratio", MIN_TRAVERSAL_RATIO),
            spec.get("max_traversal_ratio", MAX_TRAVERSAL_RATIO),
        )
    )
    findings.extend(
        grounding_findings(
            spec.get("coating_is_conductive", False),
            spec.get("coating_is_grounded", False),
        )
    )

    fluences = []
    scans = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("each step must be a mapping")
        for key in ("label", "fluence_e_per_cm2", "duration_s", "scan"):
            if key not in step:
                raise ValueError("step %d missing key '%s'" % (index + 1, key))
        fluences.append(step["fluence_e_per_cm2"])
        scans.append(step["scan"])
        findings.extend(
            flux_findings(
                step["label"], step["fluence_e_per_cm2"], step["duration_s"],
                spec.get("max_flux", MAX_FLUX_E_PER_CM2_S),
            )
        )
    fluences = _rising(fluences, "fluence_e_per_cm2")
    series = density_series(reference, scans)
    eol = _positive(spec["eol_fluence_e_per_cm2"], "eol_fluence_e_per_cm2")
    if eol < fluences[-1] - TOLERANCE:
        findings.append(
            "the run stopped at %.3g e/cm2, past the %.3g e/cm2 end-of-life "
            "point, so the projection runs backwards into the measured range"
            % (fluences[-1], eol)
        )

    report = {}
    for band in BANDS:
        densities = series[band]
        band_findings = density_monotonicity_findings(
            band, fluences, densities,
            spec.get("noise_allowance", DENSITY_NOISE_ALLOWANCE),
        )
        if all(value >= MIN_DENSITY for value in densities):
            fit = fit_density_power_law(fluences, densities)
            projected_density = predict_density(fit, eol)
            projected = transmittance_from_density(
                reference[band], projected_density
            )
            if band in required:
                floor = _transmittance(
                    required[band], "required_transmittance '%s'" % band
                )
                if projected < floor - TOLERANCE:
                    band_findings.append(
                        "the %s band is projected at %.4f transmittance at "
                        "end of life, under the %.4f the budget asks for"
                        % (band, projected, floor)
                    )
        else:
            fit = None
            projected_density = None
            projected = None
            band_findings.append(
                "the %s band carries a step at or below its unirradiated "
                "reading, so no power law fits it and no end-of-life "
                "transmittance can be projected from it" % band
            )
        report[band] = {
            "optical_densities": densities,
            "fit": fit,
            "projected_density": projected_density,
            "projected_transmittance": projected,
            "findings": band_findings,
        }
        findings.extend(band_findings)

    return {
        "fluences_e_per_cm2": fluences,
        "step_count": len(fluences),
        "eol_fluence_e_per_cm2": eol,
        "electron_range_um": electron_range_um(
            spec["beam_energy_mev"],
            spec.get("glass_density_g_cm3", RANGE_DENSITY_G_PER_CM3),
        ),
        "traversal_ratio": traversal_ratio(
            spec["beam_energy_mev"],
            spec["coating_thickness_um"],
            spec["glass_thickness_um"],
            spec.get("glass_density_g_cm3", RANGE_DENSITY_G_PER_CM3),
        ),
        "step_doses_gy": [
            absorbed_dose_gy(
                step, spec.get("stopping_power_mev_cm2_g",
                               STOPPING_POWER_MEV_CM2_G)
            )
            for step in fluences
        ],
        "eol_dose_gy": absorbed_dose_gy(
            eol,
            spec.get("stopping_power_mev_cm2_g", STOPPING_POWER_MEV_CM2_G),
        ),
        "bands": report,
        "findings": findings,
        "run_conformant": not findings,
    }
