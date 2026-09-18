"""Anodizing parameters for a black-anodizing-with-inorganic-dyes line.

Anchor: ECSS-Q-ST-70-03C, process clause, anodizing (paraphrased into
an implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Grade the electrolyte. Free acid concentration, dissolved aluminium
   and chloride each carry a window, and each one moves the coating in
   a different way: acid outside its window changes the pore
   structure, dissolved aluminium raises bath resistance and softens
   the coating, chloride pits the part.
2. Grade the electrical and thermal parameters. Current density sets
   how fast the coating grows; temperature sets how fast the
   electrolyte dissolves it back. Agitation is what keeps the second
   from running away locally, because the heat that drives dissolution
   is generated in the pores.
3. Turn those into a thickness. Growth is the product of a rate
   constant, the current density and the time, reduced by a
   dissolution term that rises linearly with the temperature above the
   reference point. Above a limiting temperature nothing accumulates
   at all and the model refuses to return a thickness.
4. Invert it. The time needed for a target thickness follows from the
   same relation, and it is the number a process sheet actually needs.
5. Size the rectifier from the racked area and the current density.
6. Report findings, the achieved thickness and one run verdict.

Stdlib only, offline, deterministic.
"""

# Sulphuric electrolyte windows.
MIN_FREE_ACID_G_L = 160.0
MAX_FREE_ACID_G_L = 200.0
MAX_DISSOLVED_ALUMINIUM_G_L = 12.0
MAX_CHLORIDE_G_L = 0.05

# Electrical and thermal windows.
MIN_CURRENT_DENSITY_A_DM2 = 1.0
MAX_CURRENT_DENSITY_A_DM2 = 2.0
MIN_BATH_TEMPERATURE_C = 18.0
MAX_BATH_TEMPERATURE_C = 22.0

# Coating growth per unit of current density per minute at the
# reference temperature, in micrometres.
COATING_RATE_UM_PER_A_DM2_MIN = 0.32

# Dissolution: above the reference temperature the electrolyte takes
# coating back, and the fraction lost rises linearly with the excess.
REFERENCE_TEMPERATURE_C = 20.0
DISSOLUTION_PER_DEGREE = 0.035

# Temperature at which the dissolution term consumes the whole growth.
LIMITING_TEMPERATURE_C = REFERENCE_TEMPERATURE_C + 1.0 / DISSOLUTION_PER_DEGREE

VALID_AGITATION = ("air-sparge", "solution-pumping", "cathode-rocking", "none")

# Thickness is a product of several floats, so a run sitting exactly on
# its target can land a few units in the last place below it. A
# picometre is far below any coating-thickness gauge and absorbs that
# representation error without relaxing the target itself.
THICKNESS_TOLERANCE_UM = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def dissolution_factor(temperature_c):
    """Fraction of the nominal growth that survives at a bath temperature."""
    temperature = _numeric("temperature_c", temperature_c)
    if temperature <= REFERENCE_TEMPERATURE_C:
        return 1.0
    return 1.0 - DISSOLUTION_PER_DEGREE * (temperature - REFERENCE_TEMPERATURE_C)


def growth_rate_um_per_min(current_density_a_dm2, temperature_c):
    """Net coating growth rate, in micrometres per minute."""
    density = _numeric("current_density_a_dm2", current_density_a_dm2, 0.0)
    factor = dissolution_factor(temperature_c)
    if factor <= 0.0:
        raise ValueError(
            "bath temperature %r dissolves the coating as fast as it grows"
            % (temperature_c,)
        )
    return COATING_RATE_UM_PER_A_DM2_MIN * density * factor


def coating_thickness_um(current_density_a_dm2, temperature_c, minutes):
    """Coating thickness a run produces, in micrometres."""
    time_min = _numeric("minutes", minutes, 0.0)
    return growth_rate_um_per_min(current_density_a_dm2, temperature_c) * time_min


def required_time_min(target_thickness_um, current_density_a_dm2, temperature_c):
    """Immersion time a target thickness needs, in minutes."""
    target = _numeric("target_thickness_um", target_thickness_um, 0.0)
    rate = growth_rate_um_per_min(current_density_a_dm2, temperature_c)
    if rate <= 0.0:
        raise ValueError("growth rate is not positive at these parameters")
    return target / rate


def total_current_a(current_density_a_dm2, racked_area_dm2):
    """Rectifier current the racked load draws, in amperes."""
    density = _numeric("current_density_a_dm2", current_density_a_dm2, 0.0)
    area = _numeric("racked_area_dm2", racked_area_dm2, 0.0)
    if area <= 0.0:
        raise ValueError("racked_area_dm2 must be positive")
    return density * area


def check_electrolyte(free_acid_g_l, dissolved_aluminium_g_l, chloride_g_l):
    """Findings about the electrolyte composition."""
    acid = _numeric("free_acid_g_l", free_acid_g_l, 0.0)
    aluminium = _numeric("dissolved_aluminium_g_l", dissolved_aluminium_g_l, 0.0)
    chloride = _numeric("chloride_g_l", chloride_g_l, 0.0)
    findings = []
    if acid < MIN_FREE_ACID_G_L:
        findings.append("free-acid-below-the-electrolyte-window")
    if acid > MAX_FREE_ACID_G_L:
        findings.append("free-acid-above-the-electrolyte-window")
    if aluminium > MAX_DISSOLVED_ALUMINIUM_G_L:
        findings.append("dissolved-aluminium-above-the-bath-limit")
    if chloride > MAX_CHLORIDE_G_L:
        findings.append("chloride-above-the-pitting-limit")
    return findings


def check_electrical(current_density_a_dm2, temperature_c, agitation):
    """Findings about current density, temperature and agitation."""
    density = _numeric("current_density_a_dm2", current_density_a_dm2, 0.0)
    temperature = _numeric("temperature_c", temperature_c)
    if agitation not in VALID_AGITATION:
        raise ValueError(
            "agitation must be one of %s, got %r"
            % (", ".join(VALID_AGITATION), agitation)
        )
    findings = []
    if density < MIN_CURRENT_DENSITY_A_DM2:
        findings.append("current-density-below-the-process-window")
    if density > MAX_CURRENT_DENSITY_A_DM2:
        findings.append("current-density-above-the-process-window")
    if temperature < MIN_BATH_TEMPERATURE_C:
        findings.append("bath-temperature-below-the-process-window")
    if temperature > MAX_BATH_TEMPERATURE_C:
        findings.append("bath-temperature-above-the-process-window")
    if agitation == "none":
        findings.append("no-agitation-declared-for-the-anodizing-tank")
    return findings


def validate_run(run):
    """Validate one anodizing run record and return a normalized copy."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping")
    run_id = run.get("id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run needs a non-empty string id")
    agitation = run.get("agitation", "air-sparge")
    if agitation not in VALID_AGITATION:
        raise ValueError("run %s has unknown agitation %r" % (run_id, agitation))
    return {
        "id": run_id.strip(),
        "free_acid_g_l": _numeric(
            "run %s free_acid_g_l" % run_id, run.get("free_acid_g_l", 180.0), 0.0
        ),
        "dissolved_aluminium_g_l": _numeric(
            "run %s dissolved_aluminium_g_l" % run_id,
            run.get("dissolved_aluminium_g_l", 5.0),
            0.0,
        ),
        "chloride_g_l": _numeric(
            "run %s chloride_g_l" % run_id, run.get("chloride_g_l", 0.01), 0.0
        ),
        "current_density_a_dm2": _numeric(
            "run %s current_density_a_dm2" % run_id,
            run.get("current_density_a_dm2", 1.5),
            0.0,
        ),
        "temperature_c": _numeric(
            "run %s temperature_c" % run_id, run.get("temperature_c", 20.0)
        ),
        "minutes": _numeric("run %s minutes" % run_id, run.get("minutes", 20.0), 0.0),
        "racked_area_dm2": _numeric(
            "run %s racked_area_dm2" % run_id, run.get("racked_area_dm2", 10.0), 0.0
        ),
        "target_thickness_um": _numeric(
            "run %s target_thickness_um" % run_id,
            run.get("target_thickness_um", 10.0),
            0.0,
        ),
        "agitation": agitation,
    }


def assess_anodizing_run(run):
    """Assess one anodizing run against the process clause."""
    norm = validate_run(run)
    findings = []
    findings.extend(
        check_electrolyte(
            norm["free_acid_g_l"],
            norm["dissolved_aluminium_g_l"],
            norm["chloride_g_l"],
        )
    )
    findings.extend(
        check_electrical(
            norm["current_density_a_dm2"], norm["temperature_c"], norm["agitation"]
        )
    )
    achieved = None
    needed = None
    if dissolution_factor(norm["temperature_c"]) > 0.0:
        achieved = coating_thickness_um(
            norm["current_density_a_dm2"], norm["temperature_c"], norm["minutes"]
        )
        needed = required_time_min(
            norm["target_thickness_um"],
            norm["current_density_a_dm2"],
            norm["temperature_c"],
        )
        if achieved + THICKNESS_TOLERANCE_UM < norm["target_thickness_um"]:
            findings.append("achieved-thickness-below-the-target")
    else:
        findings.append("bath-temperature-at-or-above-the-limiting-temperature")
    return {
        "id": norm["id"],
        "achieved_thickness_um": achieved,
        "required_time_min": needed,
        "total_current_a": total_current_a(
            norm["current_density_a_dm2"], norm["racked_area_dm2"]
        ),
        "findings": findings,
        "compliant": not findings,
    }


def assess_anodizing_runs(runs):
    """Assess several anodizing runs together."""
    if not isinstance(runs, list) or not runs:
        raise ValueError("runs must be a non-empty list")
    results = []
    seen = set()
    for run in runs:
        result = assess_anodizing_run(run)
        if result["id"] in seen:
            raise ValueError("duplicate run id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    return {
        "runs": results,
        "non_compliant_ids": [r["id"] for r in results if not r["compliant"]],
        "compliant": all(r["compliant"] for r in results),
    }
