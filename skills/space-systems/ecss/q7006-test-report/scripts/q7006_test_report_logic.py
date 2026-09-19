"""Particle and UV radiation testing: the test report.

Anchor: ECSS-Q-ST-70-06C, the reporting clause of particle and UV
radiation testing for space materials (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. A radiation test report answers four questions: what environment the
   specimen was in, how much of it the specimen received, what the
   properties did, and how well any of it is known. A report missing one
   of the four cannot be reused by anybody.
2. The environment is the beam and the chamber together: the species and
   energy of the particles, the spectral band and irradiance of the
   ultraviolet, the pressure, the specimen temperature, and where the
   dosimetry traceability comes from. A fluence with no dosimetry behind
   it is a controller setpoint wearing a measurement's clothes.
3. The exposure is reported as planned and as achieved. The two differ,
   and the relative deviation between them is the number a later reader
   needs; an achieved value reported alone hides whether the run met its
   own plan.
4. Radiation tests are accelerated. The ratio of the test flux to the
   mission flux, and the ultraviolet irradiance in suns, are part of the
   report because a degradation measured far above the mission rate may
   not be the degradation the mission produces.
5. Results carry uncertainties. Components combine in quadrature, the
   expanded figure is that times the declared coverage factor, and the
   value and its uncertainty are written at the same resolution.

Stdlib only, offline, deterministic.
"""

import math

IDENTIFICATION_FIELDS = (
    "report_id",
    "material_designation",
    "batch_or_lot",
    "dosimetry_traceability",
)

ENVIRONMENT_NUMERIC_FIELDS = (
    "particle_energy_kev",
    "particle_flux_cm2_s",
    "uv_irradiance_suns",
    "chamber_pressure_pa",
    "specimen_temperature_c",
)

ENVIRONMENT_TEXT_FIELDS = (
    "particle_species",
    "uv_spectral_band",
)

# Exposure quantities reported as a planned and an achieved value.
EXPOSURE_QUANTITIES = (
    "particle_fluence_cm2",
    "uv_dose_esh",
    "exposure_duration_h",
)

RESULT_FIELDS = (
    "pristine_value",
    "exposed_value",
)

# An achieved exposure may sit this far either side of its planned value
# before the run has to explain itself.
EXPOSURE_TOLERANCE = 0.10

# Acceleration beyond these ratios is reportable in its own right.
MAX_PARTICLE_ACCELERATION = 100.0
MAX_UV_ACCELERATION_SUNS = 5.0

# Chamber pressure ceiling for a representative exposure.
MAX_CHAMBER_PRESSURE_PA = 1.0e-3

REPORT_DECIMALS = 3
REPORT_STEP = 0.001

DEFAULT_COVERAGE_FACTOR = 2.0
MIN_COVERAGE_FACTOR = 1.0
MAX_COVERAGE_FACTOR = 3.0

# Deviations, ratios and ceilings are built from decimal literals, so a
# value sitting exactly on a bound can land a few units in the last place
# past it. This tolerance absorbs that representation error only; no
# bound is ever widened.
REPORT_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    val = float(value)
    if minimum is not None and val < minimum - REPORT_TOLERANCE:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return val


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def missing_identification(report):
    """Identification fields absent or blank in a report record."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    missing = []
    for field in IDENTIFICATION_FIELDS:
        value = report.get(field)
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return missing


def missing_environment(report):
    """Environment fields absent, blank or non-numeric in a report record."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    missing = []
    for field in ENVIRONMENT_TEXT_FIELDS:
        value = report.get(field)
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    for field in ENVIRONMENT_NUMERIC_FIELDS:
        value = report.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            missing.append(field)
    return sorted(missing)


def missing_exposure(report):
    """Exposure quantities without both a planned and an achieved value."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    exposure = report.get("exposure", {})
    if not isinstance(exposure, dict):
        raise ValueError("exposure must be a mapping")
    missing = []
    for quantity in EXPOSURE_QUANTITIES:
        pair = exposure.get(quantity)
        if not isinstance(pair, dict):
            missing.append(quantity)
            continue
        for side in ("planned", "achieved"):
            value = pair.get(side)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                missing.append("%s.%s" % (quantity, side))
    return sorted(missing)


def missing_results(report):
    """Result fields absent or non-numeric in a report record."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    results = report.get("results", {})
    if not isinstance(results, dict):
        raise ValueError("results must be a mapping")
    missing = []
    for field in RESULT_FIELDS:
        value = results.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            missing.append(field)
    return missing


def exposure_deviation(planned, achieved):
    """Relative gap between a planned exposure and the one achieved."""
    want = _numeric("planned", planned, 0.0)
    got = _numeric("achieved", achieved, 0.0)
    if want <= 0.0:
        raise ValueError("planned exposure must be greater than zero")
    return (got - want) / want


def exposure_within_tolerance(planned, achieved):
    """True when an achieved exposure sits inside its reporting tolerance."""
    return abs(exposure_deviation(planned, achieved)) <= (
        EXPOSURE_TOLERANCE + REPORT_TOLERANCE
    )


def acceleration_factor(test_flux, mission_flux):
    """How much faster the test delivered the environment than the mission."""
    test = _numeric("test_flux", test_flux, 0.0)
    mission = _numeric("mission_flux", mission_flux, 0.0)
    if mission <= 0.0:
        raise ValueError("mission_flux must be greater than zero")
    return test / mission


def combined_standard_uncertainty(components):
    """Combine uncertainty components in quadrature."""
    if not isinstance(components, dict) or not components:
        raise ValueError("components must be a non-empty mapping")
    total = 0.0
    for name, value in components.items():
        _text("uncertainty component name", name)
        contribution = _numeric("uncertainty component %s" % name, value, 0.0)
        total += contribution * contribution
    return math.sqrt(total)


def expanded_uncertainty(combined, coverage_factor=DEFAULT_COVERAGE_FACTOR):
    """Expanded uncertainty from the combined figure and a coverage factor."""
    u_c = _numeric("combined", combined, 0.0)
    k = _numeric("coverage_factor", coverage_factor)
    if k < MIN_COVERAGE_FACTOR or k > MAX_COVERAGE_FACTOR:
        raise ValueError(
            "coverage_factor %r is outside the reportable range %r..%r"
            % (k, MIN_COVERAGE_FACTOR, MAX_COVERAGE_FACTOR)
        )
    return k * u_c


def round_to_report(value):
    """Round a reported value to the resolution the report is written at."""
    return round(_numeric("value", value), REPORT_DECIMALS)


def resolution_findings(value, expanded):
    """Findings about the match between a reported value and its uncertainty."""
    val = abs(_numeric("value", value))
    exp = _numeric("expanded", expanded, 0.0)
    findings = []
    if exp > val + REPORT_TOLERANCE:
        findings.append("expanded-uncertainty-exceeds-the-reported-change")
    if exp + REPORT_TOLERANCE < REPORT_STEP / 2.0:
        findings.append("expanded-uncertainty-finer-than-the-reporting-step")
    return findings


def assess_test_report(report):
    """Assess one particle or UV radiation test report for reportability."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")

    findings = []
    missing_id = missing_identification(report)
    missing_env = missing_environment(report)
    missing_exp = missing_exposure(report)
    missing_res = missing_results(report)
    if missing_id:
        findings.append("identification-or-traceability-incomplete")
    if missing_env:
        findings.append("environment-description-incomplete")
    if missing_exp:
        findings.append("exposure-not-reported-as-planned-and-achieved")
    if missing_res:
        findings.append("results-incomplete")

    deviations = {}
    out_of_tolerance = []
    exposure = report.get("exposure", {})
    for quantity in EXPOSURE_QUANTITIES:
        pair = exposure.get(quantity) if isinstance(exposure, dict) else None
        if not isinstance(pair, dict):
            continue
        if any(q.startswith(quantity) for q in missing_exp):
            continue
        deviation = exposure_deviation(pair["planned"], pair["achieved"])
        deviations[quantity] = deviation
        if not exposure_within_tolerance(pair["planned"], pair["achieved"]):
            out_of_tolerance.append(quantity)
    if out_of_tolerance:
        findings.append("achieved-exposure-outside-its-reporting-tolerance")

    recorded = report.get("deviation_notes", [])
    if not isinstance(recorded, (list, tuple)):
        raise ValueError("deviation_notes must be a sequence")
    noted = set()
    for item in recorded:
        if not isinstance(item, dict):
            raise ValueError("each deviation note must be a mapping")
        noted.add(_text("deviation quantity", item.get("quantity")))
        _text("deviation justification", item.get("justification"))
    unexplained = sorted(set(out_of_tolerance) - noted)
    if unexplained:
        findings.append("out-of-tolerance-exposure-without-a-recorded-note")

    particle_acceleration = None
    if "particle_flux_cm2_s" not in missing_env and report.get(
        "mission_particle_flux_cm2_s"
    ) is not None:
        particle_acceleration = acceleration_factor(
            report["particle_flux_cm2_s"], report["mission_particle_flux_cm2_s"]
        )
        if particle_acceleration > MAX_PARTICLE_ACCELERATION + REPORT_TOLERANCE:
            findings.append("particle-dose-rate-acceleration-beyond-the-limit")
    else:
        findings.append("particle-dose-rate-acceleration-not-reported")

    if "uv_irradiance_suns" not in missing_env:
        if (
            _numeric("uv_irradiance_suns", report["uv_irradiance_suns"], 0.0)
            > MAX_UV_ACCELERATION_SUNS + REPORT_TOLERANCE
        ):
            findings.append("uv-irradiance-beyond-the-acceleration-limit")

    if "chamber_pressure_pa" not in missing_env:
        if (
            _numeric("chamber_pressure_pa", report["chamber_pressure_pa"], 0.0)
            > MAX_CHAMBER_PRESSURE_PA + REPORT_TOLERANCE
        ):
            findings.append("chamber-pressure-above-the-representative-ceiling")

    components = report.get("uncertainty_components")
    combined = None
    expanded = None
    if not isinstance(components, dict) or not components:
        findings.append("uncertainty-budget-absent")
    else:
        combined = combined_standard_uncertainty(components)
        expanded = expanded_uncertainty(
            combined, report.get("coverage_factor", DEFAULT_COVERAGE_FACTOR)
        )
        if not missing_res:
            change = report["results"]["exposed_value"] - report["results"][
                "pristine_value"
            ]
            findings.extend(resolution_findings(change, expanded))

    reported = {}
    if not missing_res:
        for field in RESULT_FIELDS:
            reported[field] = round_to_report(report["results"][field])
    if expanded is not None:
        reported["expanded_uncertainty"] = round_to_report(expanded)

    return {
        "report_id": report.get("report_id"),
        "missing_identification": missing_id,
        "missing_environment": missing_env,
        "missing_exposure": missing_exp,
        "missing_results": missing_res,
        "exposure_deviations": deviations,
        "out_of_tolerance_exposures": sorted(out_of_tolerance),
        "unexplained_exposures": unexplained,
        "particle_acceleration_factor": particle_acceleration,
        "combined_standard_uncertainty": combined,
        "expanded_uncertainty": expanded,
        "reported_values": reported,
        "findings": findings,
        "reportable": not findings,
    }
