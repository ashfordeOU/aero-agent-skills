"""Heat treatment control for threaded fasteners and the properties it buys.

Anchor: ECSS-Q-ST-70-46, manufacturing clause, heat treatment
(paraphrased into an implementable procedure; no standard text is
reproduced).

Procedure implemented here:

1. A property class is a pair of numbers that already states the
   mechanical properties the heat treatment has to produce: the first
   gives the tensile strength in hundreds of megapascals, the second
   the yield as a tenth-fraction of that tensile. The proof stress
   follows from the yield by a declared policy fraction. So the
   acceptance targets are derived from the designation rather than
   copied off a sheet.
2. The charge is controlled before the parts are. Soak time follows
   from the governing section thickness, the furnace has to survey
   uniform inside its band at every thermocouple rather than on
   average, and the transfer to the quenchant has its own clock
   because the part is cooling in air while it travels.
3. Tempering is what separates a class from its neighbours, and each
   class carries a minimum tempering temperature. Under-tempering
   produces a part that passes a tensile test and has no business in
   a joint that sees sustained load.
4. Hardness and tensile strength are two views of the same
   condition. A hardness reading converts to an estimated tensile
   strength through the proportional relation, valid only over the
   range the relation was fitted on, and a conversion that disagrees
   with the measured tensile beyond the declared band means one of
   the two measurements is describing a different part.
5. The proof load a fastener must hold follows from the thread stress
   area and the class proof stress, so it is derived from the
   designation and the geometry rather than looked up, and the charge
   verdict is the worst finding across the whole of it.

Stdlib only, offline, deterministic.
"""

CONFORMING = "conforming"
CONDITIONAL = "conditional"
NONCONFORMING = "nonconforming"

_RANK = {CONFORMING: 0, CONDITIONAL: 1, NONCONFORMING: 2}

# Admitted ISO metric property classes.
VALID_PROPERTY_CLASSES = ("4.6", "4.8", "5.8", "6.8", "8.8", "9.8", "10.9", "12.9")

# Minimum tempering temperature by class, in degrees Celsius.
MINIMUM_TEMPER_TEMPERATURE_C = {
    "4.6": 0.0,
    "4.8": 0.0,
    "5.8": 0.0,
    "6.8": 0.0,
    "8.8": 425.0,
    "9.8": 425.0,
    "10.9": 425.0,
    "12.9": 380.0,
}

# Proof stress as a fraction of the class yield, a declared policy.
PROOF_STRESS_FRACTION_OF_YIELD = 0.90

# Soak time model: a fixed base plus a rate on the governing section.
SOAK_BASE_MINUTES = 30.0
SOAK_RATE_MINUTES_PER_MM = 1.5

# Transfer to the quenchant, in seconds.
QUENCH_DELAY_LIMIT_S = 10.0

# Proportional constant relating Brinell hardness to tensile strength
# in megapascals, valid only over the fitted hardness range.
BRINELL_TO_TENSILE_MPA = 3.3
BRINELL_VALID_MIN = 80.0
BRINELL_VALID_MAX = 650.0

# Band inside which a hardness-derived tensile strength is taken to
# agree with a measured one.
HARDNESS_TENSILE_AGREEMENT_FRACTION = 0.10

# Stress area constant of the ISO metric thread form.
STRESS_AREA_OFFSET = 0.9382

# Strengths, times and areas are products of measured floats, so a
# case exactly on a bound can land a few units in the last place
# outside it. These absorb that without moving a bound.
STRESS_TOLERANCE_MPA = 1.0e-9
TIME_TOLERANCE = 1.0e-9
FRACTION_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def class_strengths(property_class):
    """Tensile, yield and proof stress a property class demands, in MPa."""
    if not isinstance(property_class, str) or property_class not in VALID_PROPERTY_CLASSES:
        raise ValueError(
            "unknown property class %r (expected one of %s)"
            % (property_class, ", ".join(VALID_PROPERTY_CLASSES))
        )
    first, second = property_class.split(".")
    tensile = float(first) * 100.0
    yield_stress = tensile * float(second) / 10.0
    return {
        "tensile_mpa": tensile,
        "yield_mpa": yield_stress,
        "proof_stress_mpa": yield_stress * PROOF_STRESS_FRACTION_OF_YIELD,
    }


def minimum_temper_temperature_c(property_class):
    """Lowest tempering temperature a property class admits."""
    if property_class not in MINIMUM_TEMPER_TEMPERATURE_C:
        raise ValueError("unknown property class %r" % (property_class,))
    return MINIMUM_TEMPER_TEMPERATURE_C[property_class]


def soak_time_minutes(
    section_mm, base_minutes=SOAK_BASE_MINUTES, rate_min_per_mm=SOAK_RATE_MINUTES_PER_MM
):
    """Soak time the governing section calls for, in minutes."""
    section = _numeric("section_mm", section_mm, 0.0)
    if section <= 0.0:
        raise ValueError("section_mm must be positive")
    base = _numeric("base_minutes", base_minutes, 0.0)
    rate = _numeric("rate_min_per_mm", rate_min_per_mm, 0.0)
    return base + rate * section


def uniformity_survey(setpoint_c, readings_c, band_c):
    """Judge a furnace survey at every thermocouple, not on average."""
    setpoint = _numeric("setpoint_c", setpoint_c)
    band = _numeric("band_c", band_c, 0.0)
    if band <= 0.0:
        raise ValueError("band_c must be positive")
    if not isinstance(readings_c, (list, tuple)) or not readings_c:
        raise ValueError("readings_c must be a non-empty sequence")
    deviations = [
        abs(_numeric("reading", reading) - setpoint) for reading in readings_c
    ]
    worst = max(deviations)
    return {
        "setpoint_c": setpoint,
        "band_c": band,
        "max_deviation_c": worst,
        "failing_thermocouples": [
            index
            for index, deviation in enumerate(deviations)
            if deviation > band + STRESS_TOLERANCE_MPA
        ],
        "uniform": worst <= band + STRESS_TOLERANCE_MPA,
    }


def quench_delay_finding(delay_s, limit_s=QUENCH_DELAY_LIMIT_S):
    """Whether the transfer to the quenchant stayed inside its clock."""
    delay = _numeric("delay_s", delay_s, 0.0)
    limit = _numeric("limit_s", limit_s, 0.0)
    if limit <= 0.0:
        raise ValueError("limit_s must be positive")
    return {
        "delay_s": delay,
        "limit_s": limit,
        "within_limit": delay <= limit + TIME_TOLERANCE,
        "overrun_s": max(0.0, delay - limit),
    }


def tensile_from_brinell_mpa(brinell):
    """Tensile strength a Brinell reading implies, in megapascals."""
    hardness = _numeric("brinell", brinell, 0.0)
    if hardness < BRINELL_VALID_MIN or hardness > BRINELL_VALID_MAX:
        raise ValueError(
            "brinell %r sits outside the fitted range %r to %r"
            % (hardness, BRINELL_VALID_MIN, BRINELL_VALID_MAX)
        )
    return BRINELL_TO_TENSILE_MPA * hardness


def hardness_tensile_agreement(brinell, measured_tensile_mpa):
    """Whether a hardness reading and a tensile result describe one part."""
    derived = tensile_from_brinell_mpa(brinell)
    measured = _numeric("measured_tensile_mpa", measured_tensile_mpa, 0.0)
    if measured <= 0.0:
        raise ValueError("measured_tensile_mpa must be positive")
    difference = abs(derived - measured) / measured
    return {
        "derived_tensile_mpa": derived,
        "measured_tensile_mpa": measured,
        "difference_fraction": difference,
        "agree": difference
        <= HARDNESS_TENSILE_AGREEMENT_FRACTION + FRACTION_TOLERANCE,
    }


def stress_area_mm2(nominal_diameter_mm, pitch_mm):
    """Thread stress area of a metric thread, in square millimetres."""
    diameter = _numeric("nominal_diameter_mm", nominal_diameter_mm, 0.0)
    pitch = _numeric("pitch_mm", pitch_mm, 0.0)
    if diameter <= 0.0 or pitch <= 0.0:
        raise ValueError("diameter and pitch must be positive")
    if pitch >= diameter:
        raise ValueError("pitch_mm must sit below nominal_diameter_mm")
    effective = diameter - STRESS_AREA_OFFSET * pitch
    return 3.141592653589793 / 4.0 * effective * effective


def proof_load_kn(nominal_diameter_mm, pitch_mm, property_class):
    """Proof load a class and thread size demand, in kilonewtons."""
    area = stress_area_mm2(nominal_diameter_mm, pitch_mm)
    proof_stress = class_strengths(property_class)["proof_stress_mpa"]
    return area * proof_stress / 1000.0


def validate_charge(record):
    """Validate one heat-treatment charge record and normalize it."""
    if not isinstance(record, dict):
        raise ValueError("charge must be a mapping")
    charge_id = record.get("charge_id")
    if not isinstance(charge_id, str) or not charge_id.strip():
        raise ValueError("charge needs a non-empty charge_id")
    property_class = record.get("property_class")
    class_strengths(property_class)
    readings = record.get("survey_readings_c", [])
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("charge %s needs survey_readings_c" % charge_id)
    return {
        "charge_id": charge_id.strip(),
        "property_class": property_class,
        "section_mm": _numeric("section_mm", record.get("section_mm", 10.0), 0.0),
        "declared_soak_minutes": _numeric(
            "declared_soak_minutes", record.get("declared_soak_minutes", 60.0), 0.0
        ),
        "setpoint_c": _numeric("setpoint_c", record.get("setpoint_c", 860.0)),
        "survey_readings_c": [float(r) for r in readings],
        "survey_band_c": _numeric(
            "survey_band_c", record.get("survey_band_c", 10.0), 0.0
        ),
        "quench_delay_s": _numeric(
            "quench_delay_s", record.get("quench_delay_s", 5.0), 0.0
        ),
        "temper_temperature_c": _numeric(
            "temper_temperature_c", record.get("temper_temperature_c", 500.0)
        ),
        "brinell": _numeric("brinell", record.get("brinell", 320.0), 0.0),
        "measured_tensile_mpa": _numeric(
            "measured_tensile_mpa", record.get("measured_tensile_mpa", 1050.0), 0.0
        ),
        "nominal_diameter_mm": _numeric(
            "nominal_diameter_mm", record.get("nominal_diameter_mm", 10.0), 0.0
        ),
        "pitch_mm": _numeric("pitch_mm", record.get("pitch_mm", 1.5), 0.0),
    }


def assess_charge(record):
    """Assess one heat-treatment charge end to end."""
    norm = validate_charge(record)
    findings = []
    disposition = CONFORMING

    def escalate(level):
        if _RANK[level] > _RANK[disposition]:
            return level
        return disposition

    targets = class_strengths(norm["property_class"])

    required_soak = soak_time_minutes(norm["section_mm"])
    if norm["declared_soak_minutes"] + TIME_TOLERANCE < required_soak:
        findings.append("soak-shorter-than-the-governing-section-calls-for")
        disposition = escalate(NONCONFORMING)

    survey = uniformity_survey(
        norm["setpoint_c"], norm["survey_readings_c"], norm["survey_band_c"]
    )
    if not survey["uniform"]:
        findings.append("furnace-survey-outside-its-uniformity-band")
        disposition = escalate(NONCONFORMING)

    quench = quench_delay_finding(norm["quench_delay_s"])
    if not quench["within_limit"]:
        findings.append("quench-transfer-slower-than-its-clock")
        disposition = escalate(NONCONFORMING)

    temper_floor = minimum_temper_temperature_c(norm["property_class"])
    tempered_enough = (
        norm["temper_temperature_c"] >= temper_floor - STRESS_TOLERANCE_MPA
    )
    if not tempered_enough:
        findings.append("tempered-below-the-class-minimum")
        disposition = escalate(NONCONFORMING)

    agreement = hardness_tensile_agreement(
        norm["brinell"], norm["measured_tensile_mpa"]
    )
    if not agreement["agree"]:
        findings.append("hardness-and-tensile-describe-different-conditions")
        disposition = escalate(CONDITIONAL)

    tensile_met = (
        norm["measured_tensile_mpa"] >= targets["tensile_mpa"] - STRESS_TOLERANCE_MPA
    )
    if not tensile_met:
        findings.append("measured-tensile-below-the-class-target")
        disposition = escalate(NONCONFORMING)

    return {
        "charge_id": norm["charge_id"],
        "property_class": norm["property_class"],
        "targets": targets,
        "required_soak_minutes": required_soak,
        "survey": survey,
        "quench": quench,
        "minimum_temper_temperature_c": temper_floor,
        "tempered_above_minimum": tempered_enough,
        "hardness_agreement": agreement,
        "tensile_target_met": tensile_met,
        "proof_load_kn": proof_load_kn(
            norm["nominal_diameter_mm"], norm["pitch_mm"], norm["property_class"]
        ),
        "findings": findings,
        "disposition": disposition,
    }


def assess_heat_treatment_log(records):
    """Assess every charge in a heat-treatment log and roll them up."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_charge(record)
        if result["charge_id"] in seen:
            raise ValueError("duplicate charge %r" % (result["charge_id"],))
        seen.add(result["charge_id"])
        results.append(result)
    log = CONFORMING
    for result in results:
        if _RANK[result["disposition"]] > _RANK[log]:
            log = result["disposition"]
    return {
        "charges": results,
        "log_disposition": log,
        "nonconforming_charges": [
            r["charge_id"] for r in results if r["disposition"] == NONCONFORMING
        ],
        "charges_needing_recheck": [
            r["charge_id"] for r in results if r["disposition"] == CONDITIONAL
        ],
    }
