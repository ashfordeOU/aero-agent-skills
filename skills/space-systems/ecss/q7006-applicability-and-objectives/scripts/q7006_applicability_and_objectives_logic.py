"""Applicability and objectives for a particle and UV radiation test campaign.

Anchor: ECSS-Q-ST-70-06C, framework clause -- deciding whether a space
material has to be irradiated at all, which agents (charged particles,
ultraviolet, or both) drive its degradation, what objective the campaign
carries, and which properties the degradation is read on. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Scale the mission exposure from the predicted environment: an integrated
   particle fluence from flux and duration, and an ultraviolet dose in
   equivalent sun hours from the illuminated fraction of the orbit.
2. Read the exposure regime off the item's location and its shielding: an
   externally exposed surface sees ultraviolet and low-energy particles, a
   shielded internal item sees only the penetrating part of the spectrum.
3. Decide which agents are applicable, and whether the mission exposure is
   large enough for a test to be raised at all for the material concerned.
4. Fix the objective -- screening, qualification or characterization -- and
   apply the test-level factor it demands to the mission exposure.
5. Derive the degradation properties the campaign has to measure from the
   material category and the function it performs.
6. Grade an identical-material heritage claim against envelope, spectrum and
   process before it is allowed to displace a test.
"""

import math

__all__ = [
    "OBJECTIVES",
    "TEST_LEVEL_FACTOR",
    "SHIELDING_OPAQUE_MM_AL",
    "PENETRATING_ENERGY_MEV",
    "PARTICLE_SCREENING_FLUENCE",
    "UV_SCREENING_ESH",
    "SECONDS_PER_YEAR",
    "validate_positive",
    "mission_particle_fluence",
    "mission_uv_dose_esh",
    "exposure_regime",
    "applicable_agents",
    "test_objective",
    "test_level",
    "degradation_properties",
    "heritage_findings",
    "assess_applicability",
]

SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0

# Objectives a radiation campaign can carry. Screening eliminates weak
# candidates, qualification demonstrates capability at the required level,
# characterization produces degradation data for a model.
OBJECTIVES = ("screening", "qualification", "characterization")

# Qualification is run above the predicted exposure; the other two objectives
# are run at it, because their output is data rather than a pass statement.
TEST_LEVEL_FACTOR = {
    "screening": 1.0,
    "qualification": 2.0,
    "characterization": 1.0,
}

# Any solid cover stops ultraviolet outright, so a very thin shield already
# removes the UV agent; particles need real mass to be stopped.
SHIELDING_OPAQUE_MM_AL = 0.05

# Below this energy a particle does not reach a shielded internal item behind
# a conventional equipment wall, so only the penetrating tail is applicable.
PENETRATING_ENERGY_MEV = 1.0

# Exposure below which raising a degradation test is not proportionate for a
# material that is not optically functional.
PARTICLE_SCREENING_FLUENCE = 1.0e10
UV_SCREENING_ESH = 100.0

# Categories whose bulk properties are not degraded by the space particle and
# ultraviolet environment at mission levels.
_ROBUST_MATERIALS = ("metal", "ceramic", "glass")

_MATERIAL_CATEGORIES = (
    "polymer",
    "coating",
    "adhesive",
    "composite",
    "elastomer",
) + _ROBUST_MATERIALS

_FUNCTION_PROPERTIES = {
    "thermal-control": ("infrared-emittance", "solar-absorptance"),
    "optical": ("haze", "spectral-transmittance"),
    "structural": ("elongation-at-break", "tensile-strength"),
    "electrical": ("dielectric-strength", "surface-resistivity"),
    "sealing": ("compression-set", "elongation-at-break"),
}

_CATEGORY_PROPERTIES = {
    "polymer": ("mass-loss",),
    "elastomer": ("mass-loss",),
    "adhesive": ("bond-strength", "mass-loss"),
    "coating": ("coating-adhesion",),
    "composite": ("mass-loss",),
    "metal": (),
    "ceramic": (),
    "glass": (),
}


def validate_positive(value, label, allow_zero=False):
    """Return value as a finite positive float, raising on anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _validate_fraction(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return number


def mission_particle_fluence(flux_per_cm2_s, duration_years, duty_fraction=1.0):
    """Return the integrated mission particle fluence in particles per cm^2."""
    flux = validate_positive(flux_per_cm2_s, "flux_per_cm2_s", allow_zero=True)
    years = validate_positive(duration_years, "duration_years")
    duty = _validate_fraction(duty_fraction, "duty_fraction")
    return flux * years * SECONDS_PER_YEAR * duty


def mission_uv_dose_esh(sun_fraction, duration_years, intensity_suns=1.0):
    """Return the mission ultraviolet dose in equivalent sun hours."""
    fraction = _validate_fraction(sun_fraction, "sun_fraction")
    years = validate_positive(duration_years, "duration_years")
    intensity = validate_positive(intensity_suns, "intensity_suns")
    return fraction * intensity * years * SECONDS_PER_YEAR / 3600.0


def exposure_regime(location, shielding_mm_al):
    """Return 'external-surface' or 'shielded-internal' for the item."""
    if not isinstance(location, str) or not location.strip():
        raise ValueError("location must be a non-empty string")
    thickness = validate_positive(shielding_mm_al, "shielding_mm_al", allow_zero=True)
    key = location.strip().lower()
    if key not in ("external", "internal"):
        raise ValueError("location must be 'external' or 'internal', got %r" % location)
    if key == "external" and thickness < SHIELDING_OPAQUE_MM_AL:
        return "external-surface"
    return "shielded-internal"


def applicable_agents(regime, particle_fluence, uv_dose_esh, spectrum_max_mev,
                      optically_functional=False, material_category="polymer"):
    """Return the sorted agents that drive degradation for this item."""
    if regime not in ("external-surface", "shielded-internal"):
        raise ValueError("regime must come from exposure_regime(), got %r" % regime)
    if material_category not in _MATERIAL_CATEGORIES:
        raise ValueError("unknown material_category %r" % material_category)
    fluence = validate_positive(particle_fluence, "particle_fluence", allow_zero=True)
    esh = validate_positive(uv_dose_esh, "uv_dose_esh", allow_zero=True)
    top_energy = validate_positive(spectrum_max_mev, "spectrum_max_mev")
    if material_category in _ROBUST_MATERIALS and not optically_functional:
        return ()
    agents = []
    particle_floor = 0.0 if optically_functional else PARTICLE_SCREENING_FLUENCE
    uv_floor = 0.0 if optically_functional else UV_SCREENING_ESH
    if regime == "external-surface":
        if esh > uv_floor:
            agents.append("ultraviolet")
        if fluence > particle_floor:
            agents.append("particles")
    else:
        if fluence > particle_floor and top_energy >= PENETRATING_ENERGY_MEV:
            agents.append("particles")
    return tuple(sorted(agents))


def test_objective(agents, heritage_accepted, model_data_required=False):
    """Return the objective a campaign with these drivers has to carry."""
    if not isinstance(agents, (list, tuple)):
        raise ValueError("agents must be a sequence")
    if not isinstance(heritage_accepted, bool):
        raise ValueError("heritage_accepted must be a boolean")
    if not isinstance(model_data_required, bool):
        raise ValueError("model_data_required must be a boolean")
    if not agents:
        return "not-applicable"
    if model_data_required:
        return "characterization"
    if heritage_accepted:
        return "screening"
    return "qualification"


def test_level(mission_value, objective, extra_factor=1.0):
    """Return the exposure the campaign is run to for this objective."""
    value = validate_positive(mission_value, "mission_value", allow_zero=True)
    if objective not in TEST_LEVEL_FACTOR:
        raise ValueError("objective must be one of %r, got %r" % (OBJECTIVES, objective))
    extra = validate_positive(extra_factor, "extra_factor")
    return value * TEST_LEVEL_FACTOR[objective] * extra


def degradation_properties(material_category, function):
    """Return the sorted property set the degradation has to be read on."""
    if material_category not in _MATERIAL_CATEGORIES:
        raise ValueError("unknown material_category %r" % material_category)
    if function not in _FUNCTION_PROPERTIES:
        raise ValueError(
            "function must be one of %r, got %r"
            % (tuple(sorted(_FUNCTION_PROPERTIES)), function)
        )
    merged = set(_FUNCTION_PROPERTIES[function])
    merged.update(_CATEGORY_PROPERTIES[material_category])
    return tuple(sorted(merged))


def heritage_findings(heritage, mission_fluence, mission_esh, mission_max_mev):
    """Return the findings that stop a heritage claim displacing a test."""
    if not isinstance(heritage, dict):
        raise ValueError("heritage must be a mapping")
    for key in ("fluence", "uv_esh", "max_energy_mev", "same_process", "same_material"):
        if key not in heritage:
            raise ValueError("heritage missing required key '%s'" % key)
    fluence = validate_positive(heritage["fluence"], "heritage fluence", allow_zero=True)
    esh = validate_positive(heritage["uv_esh"], "heritage uv_esh", allow_zero=True)
    energy = validate_positive(heritage["max_energy_mev"], "heritage max_energy_mev")
    need_fluence = validate_positive(mission_fluence, "mission_fluence", allow_zero=True)
    need_esh = validate_positive(mission_esh, "mission_esh", allow_zero=True)
    need_energy = validate_positive(mission_max_mev, "mission_max_mev")
    findings = []
    if not heritage["same_material"]:
        findings.append("heritage material is not the same material and lot family")
    if not heritage["same_process"]:
        findings.append("heritage item was produced by a different process route")
    if fluence < need_fluence and not math.isclose(
        fluence, need_fluence, rel_tol=1e-12, abs_tol=0.0
    ):
        findings.append(
            "heritage fluence %.3e is below the mission fluence %.3e" % (fluence, need_fluence)
        )
    if esh < need_esh and not math.isclose(esh, need_esh, rel_tol=1e-12, abs_tol=0.0):
        findings.append(
            "heritage ultraviolet dose %.1f ESH is below the mission %.1f ESH" % (esh, need_esh)
        )
    if energy < need_energy and not math.isclose(
        energy, need_energy, rel_tol=1e-12, abs_tol=0.0
    ):
        findings.append(
            "heritage spectrum stops at %.3f MeV, mission reaches %.3f MeV"
            % (energy, need_energy)
        )
    return findings


def assess_applicability(spec):
    """Run the framework assessment and return the campaign decision record.

    spec keys: location, shielding_mm_al, material_category, function,
    particle_flux_per_cm2_s, duration_years, sun_fraction, spectrum_max_mev,
    optional duty_fraction, uv_intensity_suns, optically_functional,
    model_data_required, heritage, extra_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "location",
        "shielding_mm_al",
        "material_category",
        "function",
        "particle_flux_per_cm2_s",
        "duration_years",
        "sun_fraction",
        "spectrum_max_mev",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    regime = exposure_regime(spec["location"], spec["shielding_mm_al"])
    fluence = mission_particle_fluence(
        spec["particle_flux_per_cm2_s"],
        spec["duration_years"],
        spec.get("duty_fraction", 1.0),
    )
    esh = mission_uv_dose_esh(
        spec["sun_fraction"],
        spec["duration_years"],
        spec.get("uv_intensity_suns", 1.0),
    )
    optical = bool(spec.get("optically_functional", spec["function"] == "optical"))
    agents = applicable_agents(
        regime,
        fluence,
        esh,
        spec["spectrum_max_mev"],
        optically_functional=optical,
        material_category=spec["material_category"],
    )
    findings = []
    heritage = spec.get("heritage")
    if heritage is None:
        heritage_accepted = False
    else:
        heritage_notes = heritage_findings(
            heritage, fluence, esh, spec["spectrum_max_mev"]
        )
        heritage_accepted = not heritage_notes
        findings.extend(heritage_notes)
    objective = test_objective(
        agents, heritage_accepted, bool(spec.get("model_data_required", False))
    )
    if objective == "not-applicable":
        return {
            "regime": regime,
            "mission_particle_fluence": fluence,
            "mission_uv_dose_esh": esh,
            "agents": agents,
            "objective": objective,
            "test_particle_fluence": 0.0,
            "test_uv_dose_esh": 0.0,
            "properties": (),
            "heritage_accepted": heritage_accepted,
            "findings": findings,
            "test_required": False,
        }
    extra = spec.get("extra_factor", 1.0)
    return {
        "regime": regime,
        "mission_particle_fluence": fluence,
        "mission_uv_dose_esh": esh,
        "agents": agents,
        "objective": objective,
        "test_particle_fluence": (
            test_level(fluence, objective, extra) if "particles" in agents else 0.0
        ),
        "test_uv_dose_esh": (
            test_level(esh, objective, extra) if "ultraviolet" in agents else 0.0
        ),
        "properties": degradation_properties(spec["material_category"], spec["function"]),
        "heritage_accepted": heritage_accepted,
        "findings": findings,
        "test_required": True,
    }
