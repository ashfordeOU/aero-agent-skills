"""In-house wound magnetic part assessment for class 1 commercial EEE activities.

Anchor: ECSS-Q-ST-60-13C clause 4.6.8 (magnetic parts wound in house rather
than bought as a catalogue item, the design basis behind them and the
screening they receive). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the part identity and the process basis. A self-made magnetic has
   no manufacturer qualification behind it, so the released winding process
   document and the qualification of the operator who wound it stand in that
   place and are validated, not defaulted.
2. Validate every winding: turns, conductor cross-section and root-mean-square
   current, and reject a winding declared twice.
3. Compute the conductor current density of each winding and hold it to the
   declared limit, with an exactly-met limit admissible under a named
   tolerance because the density is a quotient of two measured values.
4. Compute the saturation utilization of the core as the peak working flux
   density over the saturation flux density at the hot case, and hold it to
   its own ceiling under the same tolerance.
5. Compare the winding hot-spot temperature with the rating of the insulation
   system, and the demonstrated dielectric withstand voltage with the required
   multiple of the working voltage.
6. Compare the declared screening steps with the mandatory set and name every
   absent one.
7. Return the per-topic records and a verdict carrying every finding.
"""

import math

__all__ = [
    "MANDATORY_SCREENING",
    "DEFAULT_CURRENT_DENSITY_LIMIT_A_PER_MM2",
    "DEFAULT_SATURATION_UTILIZATION_CEILING",
    "DEFAULT_DIELECTRIC_WITHSTAND_FACTOR",
    "VALUE_TOLERANCE",
    "normalize_token",
    "validate_part_identity",
    "validate_process_basis",
    "validate_winding",
    "current_density",
    "assess_winding",
    "saturation_utilization",
    "assess_core_flux",
    "assess_insulation_system",
    "missing_screening_steps",
    "assess_self_made_magnetic",
]

# Screening every in-house wound magnetic receives before it is fitted.
MANDATORY_SCREENING = (
    "winding-visual-inspection",
    "turns-ratio-and-continuity",
    "winding-resistance-measurement",
    "insulation-resistance-measurement",
    "dielectric-withstand-test",
    "thermal-vacuum-bakeout",
)

# Conductor current density default ceiling, in ampere per square millimetre.
DEFAULT_CURRENT_DENSITY_LIMIT_A_PER_MM2 = 4.0

# Peak working flux density as a fraction of the hot-case saturation value.
DEFAULT_SATURATION_UTILIZATION_CEILING = 0.8

# Dielectric withstand demanded as a multiple of the working voltage.
DEFAULT_DIELECTRIC_WITHSTAND_FACTOR = 2.0

# Densities, utilizations and voltages are quotients and products of measured
# values; an exactly-met limit must not fail on representation alone.
VALUE_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _positive_real(value, label):
    """Return a finite strictly positive float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %g" % (label, number))
    return number


def _nonnegative_real(value, label):
    """Return a finite non-negative float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _positive_int(value, label):
    """Return a strictly positive integer."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (label, value))
    return value


def _not_above(value, limit):
    """Return True when value does not exceed limit, equality taken as within."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=VALUE_TOLERANCE
    )


def _not_below(value, floor):
    """Return True when value reaches floor, equality taken as reached."""
    return value >= floor or math.isclose(
        value, floor, rel_tol=0.0, abs_tol=VALUE_TOLERANCE
    )


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_part_identity(part):
    """Return the validated identity of the in-house wound magnetic part."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("designation", "core_reference", "winding_shop"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)
    return {
        "designation": _require_text(part["designation"], "designation"),
        "core_reference": _require_text(part["core_reference"], "core_reference"),
        "winding_shop": _require_text(part["winding_shop"], "winding_shop"),
    }


def validate_process_basis(basis):
    """Return the validated process basis standing in for a maker's qualification."""
    if not isinstance(basis, dict):
        raise ValueError("process basis must be a mapping")
    for key in ("winding_process_document", "process_issue", "operator_qualified"):
        if key not in basis:
            raise ValueError("process basis missing required key '%s'" % key)
    qualified = basis["operator_qualified"]
    if not isinstance(qualified, bool):
        raise ValueError("operator_qualified must be a boolean")
    return {
        "winding_process_document": _require_text(
            basis["winding_process_document"], "winding_process_document"
        ),
        "process_issue": _require_text(basis["process_issue"], "process_issue"),
        "operator_qualified": qualified,
    }


def validate_winding(winding):
    """Return one validated winding record."""
    if not isinstance(winding, dict):
        raise ValueError("each winding must be a mapping")
    for key in ("name", "turns", "conductor_area_mm2", "rms_current_a"):
        if key not in winding:
            raise ValueError("winding missing required key '%s'" % key)
    return {
        "name": _require_text(winding["name"], "winding name"),
        "turns": _positive_int(winding["turns"], "turns"),
        "conductor_area_mm2": _positive_real(
            winding["conductor_area_mm2"], "conductor_area_mm2"
        ),
        "rms_current_a": _nonnegative_real(winding["rms_current_a"], "rms_current_a"),
    }


def current_density(rms_current_a, conductor_area_mm2):
    """Return the conductor current density in ampere per square millimetre."""
    current = _nonnegative_real(rms_current_a, "rms current")
    area = _positive_real(conductor_area_mm2, "conductor area")
    return current / area


def assess_winding(winding, limit_a_per_mm2=None):
    """Return one winding record carrying its current density and findings."""
    record = validate_winding(winding)
    if limit_a_per_mm2 is None:
        limit = DEFAULT_CURRENT_DENSITY_LIMIT_A_PER_MM2
    else:
        limit = _positive_real(limit_a_per_mm2, "current density limit")
    density = current_density(record["rms_current_a"], record["conductor_area_mm2"])
    within = _not_above(density, limit)
    findings = []
    if not within:
        findings.append(
            "winding '%s' runs at %.4f A/mm2, above the limit of %.4f A/mm2"
            % (record["name"], density, limit)
        )
    record["current_density_a_per_mm2"] = density
    record["current_density_limit_a_per_mm2"] = limit
    record["within_current_density_limit"] = within
    record["findings"] = findings
    return record


def saturation_utilization(peak_flux_density_t, saturation_flux_density_t):
    """Return the peak working flux density as a fraction of the saturation value."""
    peak = _nonnegative_real(peak_flux_density_t, "peak flux density")
    saturation = _positive_real(saturation_flux_density_t, "saturation flux density")
    return peak / saturation


def assess_core_flux(core, ceiling=None):
    """Return the core record: how far the design works into its saturation."""
    if not isinstance(core, dict):
        raise ValueError("core must be a mapping")
    for key in ("peak_flux_density_t", "saturation_flux_density_hot_t"):
        if key not in core:
            raise ValueError("core missing required key '%s'" % key)
    if ceiling is None:
        applied_ceiling = DEFAULT_SATURATION_UTILIZATION_CEILING
    else:
        applied_ceiling = _positive_real(ceiling, "saturation utilization ceiling")
        if applied_ceiling > DEFAULT_SATURATION_UTILIZATION_CEILING and not math.isclose(
            applied_ceiling,
            DEFAULT_SATURATION_UTILIZATION_CEILING,
            rel_tol=0.0,
            abs_tol=VALUE_TOLERANCE,
        ):
            raise ValueError(
                "declared utilization ceiling %g is looser than the default %g"
                % (applied_ceiling, DEFAULT_SATURATION_UTILIZATION_CEILING)
            )
    utilization = saturation_utilization(
        core["peak_flux_density_t"], core["saturation_flux_density_hot_t"]
    )
    within = _not_above(utilization, applied_ceiling)
    findings = []
    if not within:
        findings.append(
            "core works to %.4f of its hot-case saturation, above the ceiling of %.4f"
            % (utilization, applied_ceiling)
        )
    return {
        "utilization": utilization,
        "ceiling": applied_ceiling,
        "within_ceiling": within,
        "findings": findings,
    }


def assess_insulation_system(insulation, withstand_factor=None):
    """Return the insulation record: thermal rating and demonstrated withstand."""
    if not isinstance(insulation, dict):
        raise ValueError("insulation must be a mapping")
    for key in (
        "hot_spot_temperature_c",
        "system_rated_temperature_c",
        "working_voltage_v",
        "demonstrated_withstand_v",
    ):
        if key not in insulation:
            raise ValueError("insulation missing required key '%s'" % key)
    if withstand_factor is None:
        factor = DEFAULT_DIELECTRIC_WITHSTAND_FACTOR
    else:
        factor = _positive_real(withstand_factor, "withstand factor")
        if factor < DEFAULT_DIELECTRIC_WITHSTAND_FACTOR and not math.isclose(
            factor,
            DEFAULT_DIELECTRIC_WITHSTAND_FACTOR,
            rel_tol=0.0,
            abs_tol=VALUE_TOLERANCE,
        ):
            raise ValueError(
                "declared withstand factor %g is weaker than the default %g"
                % (factor, DEFAULT_DIELECTRIC_WITHSTAND_FACTOR)
            )
    hot_spot = _nonnegative_real(
        insulation["hot_spot_temperature_c"], "hot_spot_temperature_c"
    )
    rated = _nonnegative_real(
        insulation["system_rated_temperature_c"], "system_rated_temperature_c"
    )
    working = _positive_real(insulation["working_voltage_v"], "working_voltage_v")
    demonstrated = _nonnegative_real(
        insulation["demonstrated_withstand_v"], "demonstrated_withstand_v"
    )
    required = factor * working
    findings = []
    thermally_within = _not_above(hot_spot, rated)
    if not thermally_within:
        findings.append(
            "winding hot spot reaches %.2f C, above the insulation system rating of "
            "%.2f C" % (hot_spot, rated)
        )
    withstand_met = _not_below(demonstrated, required)
    if not withstand_met:
        findings.append(
            "demonstrated withstand of %.2f V does not reach the required %.2f V"
            % (demonstrated, required)
        )
    return {
        "hot_spot_temperature_c": hot_spot,
        "system_rated_temperature_c": rated,
        "thermally_within_rating": thermally_within,
        "working_voltage_v": working,
        "required_withstand_v": required,
        "demonstrated_withstand_v": demonstrated,
        "withstand_met": withstand_met,
        "findings": findings,
    }


def missing_screening_steps(declared_steps):
    """Return the mandatory screening steps the part does not declare."""
    if declared_steps is None:
        declared_steps = []
    if not isinstance(declared_steps, (list, tuple)):
        raise ValueError("declared screening steps must be a sequence")
    declared = []
    for index, value in enumerate(declared_steps):
        token = normalize_token(value, "screening_steps[%d]" % index)
        if token in declared:
            raise ValueError("screening step '%s' is declared twice" % token)
        declared.append(token)
    return [step for step in MANDATORY_SCREENING if step not in declared]


def assess_self_made_magnetic(part_record):
    """Run the full clause 4.6.8 assessment for one in-house wound magnetic.

    part_record keys: part, process_basis, windings, core, insulation, and
    optionally current_density_limit_a_per_mm2, saturation_utilization_ceiling,
    withstand_factor, screening_steps.
    """
    if not isinstance(part_record, dict):
        raise ValueError("part_record must be a mapping")
    for key in ("part", "process_basis", "windings", "core", "insulation"):
        if key not in part_record:
            raise ValueError("part_record missing required key '%s'" % key)

    identity = validate_part_identity(part_record["part"])
    basis = validate_process_basis(part_record["process_basis"])
    findings = []
    if not basis["operator_qualified"]:
        findings.append(
            "magnetic '%s' was wound by an operator with no recorded qualification"
            % identity["designation"]
        )

    windings = part_record["windings"]
    if not isinstance(windings, (list, tuple)) or not windings:
        raise ValueError("windings must be a non-empty sequence")
    winding_records = []
    seen = set()
    for winding in windings:
        record = assess_winding(
            winding, part_record.get("current_density_limit_a_per_mm2")
        )
        key = record["name"].lower()
        if key in seen:
            raise ValueError("winding '%s' is declared twice" % record["name"])
        seen.add(key)
        winding_records.append(record)
        findings.extend(record["findings"])

    core = assess_core_flux(
        part_record["core"], part_record.get("saturation_utilization_ceiling")
    )
    findings.extend(core["findings"])

    insulation = assess_insulation_system(
        part_record["insulation"], part_record.get("withstand_factor")
    )
    findings.extend(insulation["findings"])

    absent = missing_screening_steps(part_record.get("screening_steps"))
    for step in absent:
        findings.append("screening step '%s' is not declared" % step)

    return {
        "part": identity,
        "process_basis": basis,
        "windings": winding_records,
        "core": core,
        "insulation": insulation,
        "absent_screening_steps": absent,
        "fit_for_class_1_use": not findings,
        "findings": findings,
    }
