"""High voltage and high power microwave part assessment for class 1 commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 4.6.7 (commercial electrical, electronic and
electromechanical parts serving high voltage and high power microwave
applications). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate the part identity and its declared service category. A part is
   assessed as a high voltage part or as a high power microwave part, and the
   two categories carry different ceilings and different screening.
2. Compare the applied voltage with the rated voltage as a derating ratio and
   hold that ratio to the ceiling applying to the category. A ratio landing
   exactly on the ceiling is admissible, and the equality is taken under a
   named tolerance because the ratio is a quotient of two measured values.
3. For microwave service in vacuum, convert the applied peak power and the
   multipaction threshold power into a margin in decibels and compare it with
   the required margin floor, again with the boundary taken under a tolerance.
4. Where the part stays energized while the ambient pressure passes through
   the low pressure band in which a gas discharge starts most easily, require
   a declared mitigation: a sealed or encapsulated construction, an actively
   pressurized housing, or the part held de-energized through that band.
5. Compare the declared screening steps with the steps the category requires
   and name every absent one.
6. Return the per-topic records and a verdict carrying every finding.
"""

import math

__all__ = [
    "SERVICE_CATEGORIES",
    "DERATING_CEILINGS",
    "MANDATORY_SCREENING",
    "CORONA_MITIGATIONS",
    "REQUIRED_MULTIPACTION_MARGIN_DB",
    "CORONA_PRESSURE_BAND_PA",
    "RATIO_TOLERANCE",
    "MARGIN_TOLERANCE",
    "normalize_token",
    "validate_part_identity",
    "validate_service_category",
    "voltage_derating_ratio",
    "assess_voltage_derating",
    "multipaction_margin_db",
    "assess_multipaction",
    "assess_corona_control",
    "missing_screening_steps",
    "assess_high_voltage_part",
]

# The two service categories this clause separates.
SERVICE_CATEGORIES = ("high-voltage", "high-power-microwave")

# Default applied-to-rated voltage ceilings per category. An application may
# declare a tighter ceiling of its own; it may never declare a looser one.
DERATING_CEILINGS = {"high-voltage": 0.5, "high-power-microwave": 0.6}

# Screening steps each category adds on top of the ordinary part screening.
MANDATORY_SCREENING = {
    "high-voltage": (
        "construction-analysis",
        "voltage-conditioning",
        "partial-discharge-measurement",
    ),
    "high-power-microwave": (
        "construction-analysis",
        "power-conditioning",
        "multipaction-verification",
    ),
}

# Recognized ways of keeping a gas discharge from starting in the low
# pressure band.
CORONA_MITIGATIONS = (
    "hermetic-sealing",
    "encapsulation",
    "pressurization",
    "de-energized-through-ascent",
)

# Default microwave power margin floor, in decibels.
REQUIRED_MULTIPACTION_MARGIN_DB = 6.0

# Ambient pressure band, in pascal, in which a discharge starts most easily.
CORONA_PRESSURE_BAND_PA = (1.0e2, 1.0e4)

# A derating ratio is a quotient of two measured values and a decibel margin
# comes out of a logarithm; neither may fail on representation alone.
RATIO_TOLERANCE = 1e-9
MARGIN_TOLERANCE = 1e-9


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


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_service_category(value):
    """Return the validated service category of the part."""
    category = normalize_token(value, "service category")
    if category not in SERVICE_CATEGORIES:
        raise ValueError(
            "service category '%s' is not recognized; expected one of %s"
            % (category, ", ".join(SERVICE_CATEGORIES))
        )
    return category


def validate_part_identity(part):
    """Return the validated identity of the part under assessment."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("manufacturer", "part_number", "service_category"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)
    return {
        "manufacturer": _require_text(part["manufacturer"], "manufacturer"),
        "part_number": _require_text(part["part_number"], "part_number"),
        "service_category": validate_service_category(part["service_category"]),
    }


def voltage_derating_ratio(applied_v, rated_v):
    """Return the applied-to-rated voltage ratio."""
    applied = _nonnegative_real(applied_v, "applied voltage")
    rated = _positive_real(rated_v, "rated voltage")
    return applied / rated


def assess_voltage_derating(applied_v, rated_v, category, ceiling=None):
    """Return the derating record for one part, carrying its own findings."""
    service_category = validate_service_category(category)
    default_ceiling = DERATING_CEILINGS[service_category]
    if ceiling is None:
        applied_ceiling = default_ceiling
    else:
        applied_ceiling = _positive_real(ceiling, "derating ceiling")
        if applied_ceiling > default_ceiling and not math.isclose(
            applied_ceiling, default_ceiling, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
        ):
            raise ValueError(
                "declared ceiling %g is looser than the %s ceiling %g"
                % (applied_ceiling, service_category, default_ceiling)
            )
    ratio = voltage_derating_ratio(applied_v, rated_v)
    within = ratio <= applied_ceiling or math.isclose(
        ratio, applied_ceiling, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    findings = []
    if not within:
        findings.append(
            "applied voltage reaches %.4f of rated, above the %s ceiling of %.4f"
            % (ratio, service_category, applied_ceiling)
        )
    return {
        "service_category": service_category,
        "ratio": ratio,
        "ceiling": applied_ceiling,
        "within_ceiling": within,
        "findings": findings,
    }


def multipaction_margin_db(applied_peak_power_w, threshold_power_w):
    """Return the margin, in decibels, between applied peak power and threshold."""
    applied = _positive_real(applied_peak_power_w, "applied peak power")
    threshold = _positive_real(threshold_power_w, "multipaction threshold power")
    return 10.0 * math.log10(threshold / applied)


def assess_multipaction(block, required_margin_db=None):
    """Return the microwave power-margin record for a part operated in vacuum."""
    if not isinstance(block, dict):
        raise ValueError("multipaction block must be a mapping")
    for key in ("applied_peak_power_w", "multipaction_threshold_power_w"):
        if key not in block:
            raise ValueError("multipaction block missing required key '%s'" % key)
    if required_margin_db is None:
        required = REQUIRED_MULTIPACTION_MARGIN_DB
    else:
        required = _nonnegative_real(required_margin_db, "required margin")
    margin = multipaction_margin_db(
        block["applied_peak_power_w"], block["multipaction_threshold_power_w"]
    )
    meets = margin >= required or math.isclose(
        margin, required, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    findings = []
    if not meets:
        findings.append(
            "microwave power margin is %.4f dB, below the required %.4f dB"
            % (margin, required)
        )
    return {
        "margin_db": margin,
        "required_margin_db": required,
        "meets_margin": meets,
        "findings": findings,
    }


def _within_band(pressure_pa, band=CORONA_PRESSURE_BAND_PA):
    """Return True when a pressure lies inside the discharge-prone band."""
    low, high = band
    above_low = pressure_pa >= low or math.isclose(
        pressure_pa, low, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    below_high = pressure_pa <= high or math.isclose(
        pressure_pa, high, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    return above_low and below_high


def assess_corona_control(energized_pressures_pa, mitigations):
    """Return the discharge-control record for the pressures the part is live at."""
    if not isinstance(energized_pressures_pa, (list, tuple)):
        raise ValueError("energized_pressures_pa must be a sequence")
    pressures = []
    for index, value in enumerate(energized_pressures_pa):
        pressures.append(
            _positive_real(value, "energized_pressures_pa[%d]" % index)
        )
    if mitigations is None:
        mitigations = []
    if not isinstance(mitigations, (list, tuple)):
        raise ValueError("mitigations must be a sequence or None")
    declared = []
    for index, value in enumerate(mitigations):
        token = normalize_token(value, "mitigations[%d]" % index)
        if token not in CORONA_MITIGATIONS:
            raise ValueError(
                "mitigation '%s' is not recognized; expected one of %s"
                % (token, ", ".join(CORONA_MITIGATIONS))
            )
        if token in declared:
            raise ValueError("mitigation '%s' is declared twice" % token)
        declared.append(token)
    exposed = [p for p in pressures if _within_band(p)]
    findings = []
    if exposed and not declared:
        findings.append(
            "part stays energized at %d pressure point(s) inside the discharge-prone "
            "band with no declared mitigation" % len(exposed)
        )
    return {
        "energized_pressures_pa": pressures,
        "exposed_pressures_pa": exposed,
        "mitigations": declared,
        "findings": findings,
    }


def missing_screening_steps(category, declared_steps):
    """Return the screening steps the category requires and the part does not declare."""
    service_category = validate_service_category(category)
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
    return [s for s in MANDATORY_SCREENING[service_category] if s not in declared]


def assess_high_voltage_part(application):
    """Run the full clause 4.6.7 assessment for one part application.

    application keys: part, applied_voltage_v, rated_voltage_v, and optionally
    derating_ceiling, operates_in_vacuum, multipaction, required_margin_db,
    energized_pressures_pa, corona_mitigations, screening_steps.
    """
    if not isinstance(application, dict):
        raise ValueError("application must be a mapping")
    for key in ("part", "applied_voltage_v", "rated_voltage_v"):
        if key not in application:
            raise ValueError("application missing required key '%s'" % key)

    identity = validate_part_identity(application["part"])
    category = identity["service_category"]
    findings = []

    derating = assess_voltage_derating(
        application["applied_voltage_v"],
        application["rated_voltage_v"],
        category,
        application.get("derating_ceiling"),
    )
    findings.extend(derating["findings"])

    vacuum = application.get("operates_in_vacuum", True)
    if not isinstance(vacuum, bool):
        raise ValueError("operates_in_vacuum must be a boolean")

    multipaction = None
    if category == "high-power-microwave" and vacuum:
        block = application.get("multipaction")
        if block is None:
            findings.append(
                "microwave part operated in vacuum carries no power-margin assessment"
            )
        else:
            multipaction = assess_multipaction(
                block, application.get("required_margin_db")
            )
            findings.extend(multipaction["findings"])

    corona = assess_corona_control(
        application.get("energized_pressures_pa", []),
        application.get("corona_mitigations"),
    )
    findings.extend(corona["findings"])

    absent = missing_screening_steps(category, application.get("screening_steps"))
    for step in absent:
        findings.append(
            "screening step '%s' required for %s service is not declared"
            % (step, category)
        )

    return {
        "part": identity,
        "derating": derating,
        "multipaction": multipaction,
        "corona": corona,
        "absent_screening_steps": absent,
        "fit_for_class_1_use": not findings,
        "findings": findings,
    }
