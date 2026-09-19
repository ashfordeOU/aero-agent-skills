"""Contamination degradation of thermal-control surfaces.

Anchor: ECSS-Q-ST-70-01C, the sensitive-hardware provisions covering radiators,
multi-layer-insulation outer layers and thermal-control coatings. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the surface: its beginning-of-life solar absorptance and infrared
   emittance, the heat it has to reject, its sink temperature and the highest
   temperature the hardware behind it tolerates.
2. Degrade the absorptance for the two contamination mechanisms that act on a
   thermal-control surface at once: a condensed molecular film, which darkens
   the surface towards a saturation value, and particulate fallout, which
   replaces a fraction of the clean surface with the optical properties of the
   particles themselves.
3. Degrade the emittance for the same film. On a high-emittance radiator or a
   second-surface coating a film costs far less emittance than absorptance,
   which is exactly why the ratio moves.
4. Solve the radiative equilibrium of the degraded surface against its sink
   and the absorbed solar load, and compare with the allowable temperature.
5. Recompute the heat the degraded surface can still reject per unit area and
   turn the difference into the extra radiator area the degradation costs.
"""

import math

__all__ = [
    "AREA_TOLERANCE_M2",
    "STEFAN_BOLTZMANN",
    "TEMPERATURE_TOLERANCE_K",
    "absorptance_to_emittance_ratio",
    "assess_thermal_surface",
    "degraded_absorptance",
    "degraded_emittance",
    "equilibrium_temperature_k",
    "molecular_absorptance_increase",
    "obscuration_fraction",
    "particulate_absorptance",
    "radiator_rejection_w_m2",
    "required_radiator_area_m2",
    "validate_surface",
]

STEFAN_BOLTZMANN = 5.670374419e-8

# An equilibrium temperature is a fourth root of a sum of quotients; an exactly
# on-limit case can land a few ULP either side of the allowable value.
TEMPERATURE_TOLERANCE_K = 1e-9
AREA_TOLERANCE_M2 = 1e-12

# Emittance is never driven to zero by a contaminant film; a floor keeps the
# radiative solution finite and makes an over-deep model an input error.
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


def obscuration_fraction(percent_area_coverage):
    """Convert a particulate percent-area-coverage into an obscured fraction."""
    value = _non_negative(percent_area_coverage, "percent_area_coverage")
    if value > 100.0:
        raise ValueError(
            "percent_area_coverage must not exceed 100, got %r" % (percent_area_coverage,)
        )
    return value / 100.0


def molecular_absorptance_increase(deposition_ng_cm2, saturation_delta, scale_ng_cm2):
    """Return the solar-absorptance rise produced by a condensed film."""
    deposition = _non_negative(deposition_ng_cm2, "deposition_ng_cm2")
    saturation = _fraction(saturation_delta, "saturation_delta")
    scale = _positive(scale_ng_cm2, "scale_ng_cm2")
    return saturation * (1.0 - math.exp(-deposition / scale))


def particulate_absorptance(clean_absorptance, obscured_fraction, particle_absorptance):
    """Blend the clean surface and the particulate layer by area fraction."""
    clean = _fraction(clean_absorptance, "clean_absorptance")
    obscured = _fraction(obscured_fraction, "obscured_fraction")
    particle = _fraction(particle_absorptance, "particle_absorptance")
    return clean * (1.0 - obscured) + particle * obscured


def degraded_absorptance(
    alpha_bol,
    deposition_ng_cm2,
    percent_area_coverage,
    saturation_delta=0.25,
    scale_ng_cm2=1000.0,
    particle_absorptance=0.95,
):
    """Return the end-of-life solar absorptance of a contaminated surface."""
    obscured = obscuration_fraction(percent_area_coverage)
    blended = particulate_absorptance(alpha_bol, obscured, particle_absorptance)
    rise = molecular_absorptance_increase(
        deposition_ng_cm2, saturation_delta, scale_ng_cm2
    )
    return min(1.0, blended + rise)


def degraded_emittance(
    emittance_bol,
    deposition_ng_cm2,
    saturation_drop=0.02,
    scale_ng_cm2=1000.0,
):
    """Return the end-of-life infrared emittance of a contaminated surface."""
    clean = _fraction(emittance_bol, "emittance_bol")
    if clean < MIN_EMITTANCE:
        raise ValueError(
            "emittance_bol must be at least %g for a thermal-control surface" % MIN_EMITTANCE
        )
    deposition = _non_negative(deposition_ng_cm2, "deposition_ng_cm2")
    drop = _fraction(saturation_drop, "saturation_drop")
    scale = _positive(scale_ng_cm2, "scale_ng_cm2")
    value = clean - drop * (1.0 - math.exp(-deposition / scale))
    if value < MIN_EMITTANCE:
        raise ValueError(
            "the declared emittance degradation drives emittance below %g; the model "
            "is outside its validity, not a degenerate case to clamp" % MIN_EMITTANCE
        )
    return value


def absorptance_to_emittance_ratio(absorptance, emittance):
    """Return the alpha-over-epsilon ratio that drives the equilibrium."""
    alpha = _fraction(absorptance, "absorptance")
    eps = _fraction(emittance, "emittance")
    if eps < MIN_EMITTANCE:
        raise ValueError("emittance must be at least %g" % MIN_EMITTANCE)
    return alpha / eps


def equilibrium_temperature_k(
    absorptance, emittance, solar_flux_w_m2, internal_flux_w_m2, sink_temperature_k
):
    """Solve the radiative equilibrium temperature of the surface."""
    alpha = _fraction(absorptance, "absorptance")
    eps = _fraction(emittance, "emittance")
    if eps < MIN_EMITTANCE:
        raise ValueError("emittance must be at least %g" % MIN_EMITTANCE)
    solar = _non_negative(solar_flux_w_m2, "solar_flux_w_m2")
    internal = _non_negative(internal_flux_w_m2, "internal_flux_w_m2")
    sink = _non_negative(sink_temperature_k, "sink_temperature_k")
    absorbed = alpha * solar + internal
    quartic = sink ** 4 + absorbed / (eps * STEFAN_BOLTZMANN)
    return quartic ** 0.25


def radiator_rejection_w_m2(emittance, surface_temperature_k, sink_temperature_k):
    """Return the net heat a radiator rejects per unit area."""
    eps = _fraction(emittance, "emittance")
    if eps < MIN_EMITTANCE:
        raise ValueError("emittance must be at least %g" % MIN_EMITTANCE)
    surface = _positive(surface_temperature_k, "surface_temperature_k")
    sink = _non_negative(sink_temperature_k, "sink_temperature_k")
    if sink >= surface:
        raise ValueError(
            "sink_temperature_k %g is not below surface_temperature_k %g; the radiator "
            "cannot reject heat into a sink at or above its own temperature"
            % (sink, surface)
        )
    return eps * STEFAN_BOLTZMANN * (surface ** 4 - sink ** 4)


def required_radiator_area_m2(heat_load_w, rejection_w_m2):
    """Return the radiator area needed to reject a heat load."""
    load = _positive(heat_load_w, "heat_load_w")
    rejection = _positive(rejection_w_m2, "rejection_w_m2")
    return load / rejection


def validate_surface(surface):
    """Return a normalised thermal-control-surface record."""
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping")
    required = (
        "alpha_bol",
        "emittance_bol",
        "heat_load_w",
        "installed_area_m2",
        "sink_temperature_k",
        "max_allowable_temperature_k",
    )
    for key in required:
        if key not in surface:
            raise ValueError("surface missing required key '%s'" % key)
    record = {
        "alpha_bol": _fraction(surface["alpha_bol"], "alpha_bol"),
        "emittance_bol": _fraction(surface["emittance_bol"], "emittance_bol"),
        "heat_load_w": _positive(surface["heat_load_w"], "heat_load_w"),
        "installed_area_m2": _positive(surface["installed_area_m2"], "installed_area_m2"),
        "sink_temperature_k": _non_negative(
            surface["sink_temperature_k"], "sink_temperature_k"
        ),
        "max_allowable_temperature_k": _positive(
            surface["max_allowable_temperature_k"], "max_allowable_temperature_k"
        ),
        "solar_flux_w_m2": _non_negative(
            surface.get("solar_flux_w_m2", 0.0), "solar_flux_w_m2"
        ),
        "deposition_ng_cm2": _non_negative(
            surface.get("deposition_ng_cm2", 0.0), "deposition_ng_cm2"
        ),
        "percent_area_coverage": surface.get("percent_area_coverage", 0.0),
        "saturation_delta_alpha": _fraction(
            surface.get("saturation_delta_alpha", 0.25), "saturation_delta_alpha"
        ),
        "saturation_drop_emittance": _fraction(
            surface.get("saturation_drop_emittance", 0.02), "saturation_drop_emittance"
        ),
        "scale_ng_cm2": _positive(surface.get("scale_ng_cm2", 1000.0), "scale_ng_cm2"),
        "particle_absorptance": _fraction(
            surface.get("particle_absorptance", 0.95), "particle_absorptance"
        ),
    }
    if record["emittance_bol"] < MIN_EMITTANCE:
        raise ValueError("emittance_bol must be at least %g" % MIN_EMITTANCE)
    # Validates the range and raises on a bad coverage value.
    record["obscured_fraction"] = obscuration_fraction(record["percent_area_coverage"])
    if record["sink_temperature_k"] >= record["max_allowable_temperature_k"]:
        raise ValueError(
            "sink_temperature_k must be below max_allowable_temperature_k"
        )
    return record


def assess_thermal_surface(spec):
    """Run the full sensitive thermal-control-surface contamination assessment.

    spec keys: the validate_surface record keys. Returns beginning-of-life and
    end-of-life thermo-optical properties, the degraded equilibrium
    temperature, the degraded rejection capability and the area shortfall.
    """
    record = validate_surface(spec)
    alpha_eol = degraded_absorptance(
        record["alpha_bol"],
        record["deposition_ng_cm2"],
        record["percent_area_coverage"],
        record["saturation_delta_alpha"],
        record["scale_ng_cm2"],
        record["particle_absorptance"],
    )
    eps_eol = degraded_emittance(
        record["emittance_bol"],
        record["deposition_ng_cm2"],
        record["saturation_drop_emittance"],
        record["scale_ng_cm2"],
    )
    internal = record["heat_load_w"] / record["installed_area_m2"]
    t_bol = equilibrium_temperature_k(
        record["alpha_bol"],
        record["emittance_bol"],
        record["solar_flux_w_m2"],
        internal,
        record["sink_temperature_k"],
    )
    t_eol = equilibrium_temperature_k(
        alpha_eol,
        eps_eol,
        record["solar_flux_w_m2"],
        internal,
        record["sink_temperature_k"],
    )
    limit = record["max_allowable_temperature_k"]
    rejection = radiator_rejection_w_m2(
        eps_eol, limit, record["sink_temperature_k"]
    ) - alpha_eol * record["solar_flux_w_m2"]
    findings = []
    if rejection <= 0.0:
        required_area = float("inf")
        findings.append(
            "at end of life the degraded surface absorbs at least as much solar load "
            "as it can reject at the allowable temperature; no finite area closes"
        )
    else:
        required_area = required_radiator_area_m2(record["heat_load_w"], rejection)
    within_temperature = t_eol < limit or math.isclose(
        t_eol, limit, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K
    )
    if not within_temperature:
        findings.append(
            "end-of-life equilibrium temperature %.4f K exceeds the allowable %.4f K"
            % (t_eol, limit)
        )
    within_area = required_area < record["installed_area_m2"] or math.isclose(
        required_area, record["installed_area_m2"], rel_tol=0.0, abs_tol=AREA_TOLERANCE_M2
    )
    if not within_area and math.isfinite(required_area):
        findings.append(
            "end-of-life rejection needs %.4f m2 against %.4f m2 installed"
            % (required_area, record["installed_area_m2"])
        )
    return {
        "alpha_bol": record["alpha_bol"],
        "alpha_eol": alpha_eol,
        "emittance_bol": record["emittance_bol"],
        "emittance_eol": eps_eol,
        "ratio_bol": absorptance_to_emittance_ratio(
            record["alpha_bol"], record["emittance_bol"]
        ),
        "ratio_eol": absorptance_to_emittance_ratio(alpha_eol, eps_eol),
        "temperature_bol_k": t_bol,
        "temperature_eol_k": t_eol,
        "temperature_rise_k": t_eol - t_bol,
        "rejection_eol_w_m2": rejection,
        "required_area_m2": required_area,
        "installed_area_m2": record["installed_area_m2"],
        "compliant": within_temperature and within_area,
        "findings": findings,
    }
