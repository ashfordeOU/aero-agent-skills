"""Contamination control of solar arrays and second-surface mirrors.

Anchor: ECSS-Q-ST-70-01C, the sensitive-hardware provisions protecting
photovoltaic arrays and optical solar reflectors. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the array: beginning-of-life power at a reference cell
   temperature, the power the mission needs at end of life, the cover-glass
   thermo-optical properties, the sink temperature and the cell temperature
   coefficient.
2. Turn the predicted contamination into an illumination factor: particulate
   fallout removes a fraction of the aperture outright, and a condensed
   molecular film attenuates what passes through the rest.
3. Turn the same contamination into a cover absorptance rise, because the
   light the film stops is absorbed rather than reflected, and the particles
   are darker than the cover they sit on.
4. Solve the cell temperature from the absorbed solar load net of the
   electrical power actually extracted, and convert the rise above the
   reference temperature into a power derating through the cell temperature
   coefficient.
5. Combine the illumination factor and the temperature factor into an
   end-of-life power, compare it with the required power, and report the
   margin. Run the same absorptance model over any second-surface mirror in
   the same contamination environment.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "STEFAN_BOLTZMANN",
    "array_power_w",
    "assess_solar_array",
    "cell_temperature_k",
    "contaminated_absorptance",
    "film_transmittance",
    "illumination_factor",
    "obscured_area_fraction",
    "power_margin_fraction",
    "second_surface_mirror_ratio",
    "temperature_power_factor",
    "validate_array",
]

STEFAN_BOLTZMANN = 5.670374419e-8

# Power margin is a quotient of two quantities built through exp() and a
# fourth root; an exactly on-requirement case can land a few ULP either side.
MARGIN_TOLERANCE = 1e-12

MIN_EMITTANCE = 1.0e-3


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _fraction(value, label):
    number = _non_negative(value, label)
    if number > 1.0:
        raise ValueError("%s must not exceed 1, got %r" % (label, value))
    return number


def obscured_area_fraction(percent_area_coverage):
    """Convert a particulate percent-area-coverage into an obscured fraction."""
    value = _non_negative(percent_area_coverage, "percent_area_coverage")
    if value > 100.0:
        raise ValueError(
            "percent_area_coverage must not exceed 100, got %r" % (percent_area_coverage,)
        )
    return value / 100.0


def film_transmittance(deposition_ng_cm2, absorption_per_ng_cm2):
    """Return the solar-band transmittance of a condensed molecular film."""
    deposition = _non_negative(deposition_ng_cm2, "deposition_ng_cm2")
    absorption = _non_negative(absorption_per_ng_cm2, "absorption_per_ng_cm2")
    return math.exp(-absorption * deposition)


def illumination_factor(obscured_fraction, transmittance):
    """Return the fraction of the reference solar input the cells still see."""
    obscured = _fraction(obscured_fraction, "obscured_fraction")
    passed = _fraction(transmittance, "transmittance")
    return (1.0 - obscured) * passed


def contaminated_absorptance(
    alpha_bol, obscured_fraction, transmittance, particle_absorptance=0.95
):
    """Return the solar absorptance of a contaminated cover or mirror."""
    clean = _fraction(alpha_bol, "alpha_bol")
    obscured = _fraction(obscured_fraction, "obscured_fraction")
    passed = _fraction(transmittance, "transmittance")
    particle = _fraction(particle_absorptance, "particle_absorptance")
    film_rise = (1.0 - passed) * (1.0 - clean)
    particulate_rise = obscured * max(0.0, particle - clean)
    return min(1.0, clean + film_rise + particulate_rise)


def cell_temperature_k(
    absorptance, emittance, solar_flux_w_m2, electrical_output_w_m2, sink_temperature_k
):
    """Solve the cell temperature from the absorbed load net of extracted power."""
    alpha = _fraction(absorptance, "absorptance")
    eps = _fraction(emittance, "emittance")
    if eps < MIN_EMITTANCE:
        raise ValueError("emittance must be at least %g" % MIN_EMITTANCE)
    solar = _non_negative(solar_flux_w_m2, "solar_flux_w_m2")
    extracted = _non_negative(electrical_output_w_m2, "electrical_output_w_m2")
    sink = _non_negative(sink_temperature_k, "sink_temperature_k")
    net = alpha * solar - extracted
    if net < 0.0:
        raise ValueError(
            "extracted electrical power %g W/m2 exceeds the absorbed solar load "
            "%g W/m2; the array cannot deliver more than it absorbs"
            % (extracted, alpha * solar)
        )
    return (sink ** 4 + net / (eps * STEFAN_BOLTZMANN)) ** 0.25


def temperature_power_factor(
    cell_temperature, reference_temperature_k, temperature_coefficient_per_k
):
    """Return the power derating factor for a cell above its reference point."""
    cell = _positive(cell_temperature, "cell_temperature")
    reference = _positive(reference_temperature_k, "reference_temperature_k")
    if (
        not isinstance(temperature_coefficient_per_k, (int, float))
        or isinstance(temperature_coefficient_per_k, bool)
        or not math.isfinite(float(temperature_coefficient_per_k))
    ):
        raise ValueError("temperature_coefficient_per_k must be a finite real number")
    coefficient = float(temperature_coefficient_per_k)
    if coefficient > 0.0:
        raise ValueError(
            "temperature_coefficient_per_k must not be positive; photovoltaic output "
            "falls as the cell warms, got %r" % (temperature_coefficient_per_k,)
        )
    factor = 1.0 + coefficient * (cell - reference)
    if factor <= 0.0:
        raise ValueError(
            "the declared coefficient drives output to zero at %g K; the linear "
            "derating model is outside its validity" % cell
        )
    return factor


def array_power_w(bol_power_w, illumination, temperature_factor):
    """Return the delivered array power for an illumination and derating pair."""
    power = _positive(bol_power_w, "bol_power_w")
    light = _fraction(illumination, "illumination")
    factor = _positive(temperature_factor, "temperature_factor")
    return power * light * factor


def power_margin_fraction(available_w, required_w):
    """Return the fractional power margin above the requirement."""
    available = _non_negative(available_w, "available_w")
    required = _positive(required_w, "required_w")
    return available / required - 1.0


def second_surface_mirror_ratio(alpha_eol, emittance):
    """Return the alpha-over-epsilon ratio of a contaminated second-surface mirror."""
    alpha = _fraction(alpha_eol, "alpha_eol")
    eps = _fraction(emittance, "emittance")
    if eps < MIN_EMITTANCE:
        raise ValueError("emittance must be at least %g" % MIN_EMITTANCE)
    return alpha / eps


def validate_array(spec):
    """Return a normalised solar-array contamination record."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = ("bol_power_w", "required_power_w", "solar_flux_w_m2", "array_area_m2")
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    coefficient = spec.get("temperature_coefficient_per_k", -0.0035)
    if (
        not isinstance(coefficient, (int, float))
        or isinstance(coefficient, bool)
        or not math.isfinite(float(coefficient))
    ):
        raise ValueError("temperature_coefficient_per_k must be a finite real number")
    if float(coefficient) > 0.0:
        raise ValueError("temperature_coefficient_per_k must not be positive")
    record = {
        "bol_power_w": _positive(spec["bol_power_w"], "bol_power_w"),
        "required_power_w": _positive(spec["required_power_w"], "required_power_w"),
        "solar_flux_w_m2": _positive(spec["solar_flux_w_m2"], "solar_flux_w_m2"),
        "array_area_m2": _positive(spec["array_area_m2"], "array_area_m2"),
        "alpha_cover_bol": _fraction(
            spec.get("alpha_cover_bol", 0.75), "alpha_cover_bol"
        ),
        "emittance_cover": _fraction(spec.get("emittance_cover", 0.82), "emittance_cover"),
        "reference_temperature_k": _positive(
            spec.get("reference_temperature_k", 301.15), "reference_temperature_k"
        ),
        "sink_temperature_k": _non_negative(
            spec.get("sink_temperature_k", 4.0), "sink_temperature_k"
        ),
        "temperature_coefficient_per_k": float(coefficient),
        "deposition_ng_cm2": _non_negative(
            spec.get("deposition_ng_cm2", 0.0), "deposition_ng_cm2"
        ),
        "absorption_per_ng_cm2": _non_negative(
            spec.get("absorption_per_ng_cm2", 2.0e-5), "absorption_per_ng_cm2"
        ),
        "percent_area_coverage": spec.get("percent_area_coverage", 0.0),
        "particle_absorptance": _fraction(
            spec.get("particle_absorptance", 0.95), "particle_absorptance"
        ),
    }
    if record["emittance_cover"] < MIN_EMITTANCE:
        raise ValueError("emittance_cover must be at least %g" % MIN_EMITTANCE)
    record["obscured_fraction"] = obscured_area_fraction(record["percent_area_coverage"])
    mirror = spec.get("mirror")
    if mirror is not None:
        if not isinstance(mirror, dict):
            raise ValueError("mirror must be a mapping when present")
        for key in ("alpha_bol", "emittance", "max_ratio"):
            if key not in mirror:
                raise ValueError("mirror missing required key '%s'" % key)
        record["mirror"] = {
            "alpha_bol": _fraction(mirror["alpha_bol"], "mirror alpha_bol"),
            "emittance": _fraction(mirror["emittance"], "mirror emittance"),
            "max_ratio": _positive(mirror["max_ratio"], "mirror max_ratio"),
        }
    else:
        record["mirror"] = None
    return record


def assess_solar_array(spec):
    """Run the full solar-array and second-surface-mirror contamination assessment."""
    record = validate_array(spec)
    passed = film_transmittance(
        record["deposition_ng_cm2"], record["absorption_per_ng_cm2"]
    )
    light = illumination_factor(record["obscured_fraction"], passed)
    alpha_eol = contaminated_absorptance(
        record["alpha_cover_bol"],
        record["obscured_fraction"],
        passed,
        record["particle_absorptance"],
    )
    extracted_bol = record["bol_power_w"] / record["array_area_m2"]
    t_bol = cell_temperature_k(
        record["alpha_cover_bol"],
        record["emittance_cover"],
        record["solar_flux_w_m2"],
        extracted_bol,
        record["sink_temperature_k"],
    )
    extracted_eol = record["bol_power_w"] * light / record["array_area_m2"]
    t_eol = cell_temperature_k(
        alpha_eol,
        record["emittance_cover"],
        record["solar_flux_w_m2"],
        extracted_eol,
        record["sink_temperature_k"],
    )
    factor = temperature_power_factor(
        t_eol, record["reference_temperature_k"], record["temperature_coefficient_per_k"]
    )
    delivered = array_power_w(record["bol_power_w"], light, factor)
    margin = power_margin_fraction(delivered, record["required_power_w"])
    findings = []
    meets_power = margin > 0.0 or math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    if not meets_power:
        findings.append(
            "end-of-life array power %.4f W falls short of the required %.4f W"
            % (delivered, record["required_power_w"])
        )
    mirror_result = None
    if record["mirror"] is not None:
        mirror_alpha = contaminated_absorptance(
            record["mirror"]["alpha_bol"],
            record["obscured_fraction"],
            passed,
            record["particle_absorptance"],
        )
        ratio = second_surface_mirror_ratio(mirror_alpha, record["mirror"]["emittance"])
        within = ratio < record["mirror"]["max_ratio"] or math.isclose(
            ratio, record["mirror"]["max_ratio"], rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
        )
        if not within:
            findings.append(
                "second-surface mirror alpha-over-epsilon %.5f exceeds the allowable "
                "%.5f" % (ratio, record["mirror"]["max_ratio"])
            )
        mirror_result = {
            "alpha_bol": record["mirror"]["alpha_bol"],
            "alpha_eol": mirror_alpha,
            "ratio_eol": ratio,
            "max_ratio": record["mirror"]["max_ratio"],
            "within_limit": within,
        }
    return {
        "film_transmittance": passed,
        "obscured_fraction": record["obscured_fraction"],
        "illumination_factor": light,
        "alpha_cover_bol": record["alpha_cover_bol"],
        "alpha_cover_eol": alpha_eol,
        "cell_temperature_bol_k": t_bol,
        "cell_temperature_eol_k": t_eol,
        "temperature_power_factor": factor,
        "delivered_power_w": delivered,
        "required_power_w": record["required_power_w"],
        "power_margin_fraction": margin,
        "mirror": mirror_result,
        "compliant": meets_power
        and (mirror_result is None or mirror_result["within_limit"]),
        "findings": findings,
    }
