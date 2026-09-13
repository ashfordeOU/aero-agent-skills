"""General provisions for the humidity test of a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.4.2 (humidity test -- general provisions:
the mission-specific environmental conditions are captured in the assembly
control drawing before the test is run). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the mission exposure phases declared for the assembly (storage,
   transport, integration hall, launch-site stand-by) -- each carries a
   relative humidity, an air temperature and a duration.
2. Envelope those phases into the worst-case humidity requirement: the highest
   relative humidity, the highest air temperature and the cumulative exposure
   duration seen across the whole mission ground phase.
3. Apply the agreed per-parameter margin factors to turn the mission envelope
   into the condition the assembly control drawing has to declare.
4. Check the drawing declaration carries every required parameter, that each
   declared value envelopes the margined requirement, and that no value is
   over-declared beyond the agreed over-test factor.
5. Check the drawing revision that carries the declaration was issued no later
   than the test start date, so the conditions were captured before testing.
6. Report the envelope, the required declaration, the per-parameter comparison
   and every finding: omission, shortfall, over-declaration, late capture.
"""

import datetime
import math

__all__ = [
    "REQUIRED_ENVIRONMENTAL_PARAMETERS",
    "DEFAULT_MARGIN_FACTORS",
    "DEFAULT_OVER_TEST_FACTOR",
    "ENVELOPE_TOLERANCE_REL",
    "MAX_RELATIVE_HUMIDITY_PCT",
    "validate_iso_date",
    "validate_positive",
    "validate_mission_phase",
    "mission_envelope",
    "required_declaration",
    "missing_parameters",
    "envelopes_requirement",
    "parameter_comparison",
    "capture_precedes_test",
    "assess_general_provisions",
]

# The three quantities that fix a humidity exposure. A drawing that omits any
# one of them does not define the test, whatever else it carries.
REQUIRED_ENVIRONMENTAL_PARAMETERS = (
    "relative_humidity_pct",
    "air_temperature_c",
    "exposure_duration_h",
)

# Agreed uplift applied to the mission envelope before it is written on the
# drawing. Humidity and temperature are already worst cases, so their default
# uplift is unity; duration carries the usual ground-phase schedule reserve.
DEFAULT_MARGIN_FACTORS = {
    "relative_humidity_pct": 1.0,
    "air_temperature_c": 1.0,
    "exposure_duration_h": 1.5,
}

# A declaration far above the margined requirement is an over-test: it stresses
# the encapsulant and the interconnect for no mission reason.
DEFAULT_OVER_TEST_FACTOR = 2.0

# Margined requirements are products of floats. A declaration that physically
# equals its requirement can land a few ULP either side of it, so the envelope
# comparison absorbs that representation error instead of moving the limit.
ENVELOPE_TOLERANCE_REL = 1e-9

# Relative humidity is a percentage of saturation; above this it is condensing,
# which is a different exposure and a different clause.
MAX_RELATIVE_HUMIDITY_PCT = 100.0

# Absolute zero in degrees Celsius; an air temperature below it is an input
# error, not a cold case.
MIN_AIR_TEMPERATURE_C = -273.15


def validate_iso_date(value, label):
    """Return an ISO-8601 calendar date parsed from value."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO-8601 date string (YYYY-MM-DD)" % label)
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not a valid ISO-8601 date: %r" % (label, value))


def validate_positive(value, label, allow_zero=False):
    """Return value as a finite positive float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if allow_zero:
        if number < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    elif number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_mission_phase(phase, index=0):
    """Return one validated mission exposure phase."""
    if not isinstance(phase, dict):
        raise ValueError("mission phase %d must be a mapping" % index)
    name = phase.get("phase")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("mission phase %d must carry a non-empty 'phase' name" % index)
    for key in REQUIRED_ENVIRONMENTAL_PARAMETERS:
        if key not in phase:
            raise ValueError("mission phase %r is missing '%s'" % (name, key))
    humidity = validate_positive(
        phase["relative_humidity_pct"], "relative_humidity_pct of phase %r" % name
    )
    if humidity > MAX_RELATIVE_HUMIDITY_PCT:
        raise ValueError(
            "relative_humidity_pct of phase %r exceeds saturation: %g" % (name, humidity)
        )
    temperature = phase["air_temperature_c"]
    if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
        raise ValueError("air_temperature_c of phase %r must be a real number" % name)
    temperature = float(temperature)
    if not math.isfinite(temperature) or temperature < MIN_AIR_TEMPERATURE_C:
        raise ValueError(
            "air_temperature_c of phase %r is below absolute zero: %r"
            % (name, phase["air_temperature_c"])
        )
    duration = validate_positive(
        phase["exposure_duration_h"], "exposure_duration_h of phase %r" % name
    )
    return {
        "phase": name.strip(),
        "relative_humidity_pct": humidity,
        "air_temperature_c": temperature,
        "exposure_duration_h": duration,
    }


def mission_envelope(mission_phases):
    """Envelope the mission phases into the worst-case humidity requirement."""
    if not isinstance(mission_phases, (list, tuple)) or not mission_phases:
        raise ValueError("mission_phases must be a non-empty sequence of phases")
    phases = [validate_mission_phase(p, i) for i, p in enumerate(mission_phases)]
    names = [p["phase"] for p in phases]
    if len(set(names)) != len(names):
        raise ValueError("mission phase names must be unique, got %r" % (names,))
    return {
        "relative_humidity_pct": max(p["relative_humidity_pct"] for p in phases),
        "air_temperature_c": max(p["air_temperature_c"] for p in phases),
        "exposure_duration_h": math.fsum(p["exposure_duration_h"] for p in phases),
        "phase_count": len(phases),
        "driving_phase": max(
            phases, key=lambda p: (p["relative_humidity_pct"], p["air_temperature_c"])
        )["phase"],
    }


def _margin_factors(margins):
    """Return the per-parameter margin factors, defaults filled in."""
    factors = dict(DEFAULT_MARGIN_FACTORS)
    if margins is None:
        return factors
    if not isinstance(margins, dict):
        raise ValueError("margins must be a mapping of parameter to factor")
    for key, value in margins.items():
        if key not in REQUIRED_ENVIRONMENTAL_PARAMETERS:
            raise ValueError("margins carries unknown parameter '%s'" % key)
        factor = validate_positive(value, "margin factor for '%s'" % key)
        if factor < 1.0:
            raise ValueError(
                "margin factor for '%s' must not shrink the mission value, got %g"
                % (key, factor)
            )
        factors[key] = factor
    return factors


def required_declaration(envelope, margins=None):
    """Return the condition the assembly control drawing has to declare."""
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a mapping")
    factors = _margin_factors(margins)
    required = {}
    for key in REQUIRED_ENVIRONMENTAL_PARAMETERS:
        if key not in envelope:
            raise ValueError("envelope is missing '%s'" % key)
        value = envelope[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("envelope['%s'] must be a real number" % key)
        required[key] = float(value) * factors[key]
    # Humidity is capped at saturation however generous the agreed factor is.
    if required["relative_humidity_pct"] > MAX_RELATIVE_HUMIDITY_PCT:
        required["relative_humidity_pct"] = MAX_RELATIVE_HUMIDITY_PCT
    return required


def missing_parameters(declaration):
    """Return the required parameters the drawing declaration does not carry."""
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping")
    absent = []
    for key in REQUIRED_ENVIRONMENTAL_PARAMETERS:
        if key not in declaration or declaration[key] is None:
            absent.append(key)
    return absent


def envelopes_requirement(declared, required):
    """Return True when the declared value reaches or exceeds the requirement."""
    for label, value in (("declared", declared), ("required", required)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s value must be a real number" % label)
        if not math.isfinite(float(value)):
            raise ValueError("%s value must be finite" % label)
    declared = float(declared)
    required = float(required)
    if math.isclose(declared, required, rel_tol=ENVELOPE_TOLERANCE_REL, abs_tol=0.0):
        return True
    return declared > required


def parameter_comparison(declaration, required, over_test_factor=DEFAULT_OVER_TEST_FACTOR):
    """Compare every declared parameter with its margined requirement."""
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping")
    if not isinstance(required, dict):
        raise ValueError("required must be a mapping")
    factor = validate_positive(over_test_factor, "over_test_factor")
    if factor < 1.0:
        raise ValueError("over_test_factor must not be below unity, got %g" % factor)
    rows = []
    for key in REQUIRED_ENVIRONMENTAL_PARAMETERS:
        if key not in declaration or declaration[key] is None:
            continue
        if key not in required:
            raise ValueError("required is missing '%s'" % key)
        declared_value = declaration[key]
        if not isinstance(declared_value, (int, float)) or isinstance(declared_value, bool):
            raise ValueError("declaration['%s'] must be a real number" % key)
        declared_value = float(declared_value)
        if not math.isfinite(declared_value):
            raise ValueError("declaration['%s'] must be finite" % key)
        required_value = float(required[key])
        covered = envelopes_requirement(declared_value, required_value)
        ceiling = required_value * factor
        over = (
            declared_value > ceiling
            and not math.isclose(
                declared_value, ceiling, rel_tol=ENVELOPE_TOLERANCE_REL, abs_tol=0.0
            )
        )
        rows.append(
            {
                "parameter": key,
                "declared": declared_value,
                "required": required_value,
                "covered": covered,
                "over_declared": over,
            }
        )
    return rows


def capture_precedes_test(revision_date, test_start_date):
    """Return True when the drawing revision was issued no later than test start."""
    revision = validate_iso_date(revision_date, "revision_date")
    start = validate_iso_date(test_start_date, "test_start_date")
    return revision <= start


def assess_general_provisions(spec):
    """Run the full clause 5.5.1.4.2 general-provisions assessment.

    spec keys: drawing_revision, revision_date, test_start_date, declaration,
    mission_phases, optional margins and over_test_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "drawing_revision",
        "revision_date",
        "test_start_date",
        "declaration",
        "mission_phases",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    revision_id = spec["drawing_revision"]
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise ValueError("drawing_revision must be a non-empty identifier")
    declaration = spec["declaration"]
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping")

    envelope = mission_envelope(spec["mission_phases"])
    required = required_declaration(envelope, spec.get("margins"))
    absent = missing_parameters(declaration)
    rows = parameter_comparison(
        declaration, required, spec.get("over_test_factor", DEFAULT_OVER_TEST_FACTOR)
    )
    captured_in_time = capture_precedes_test(spec["revision_date"], spec["test_start_date"])

    findings = []
    for key in absent:
        findings.append(
            "assembly control drawing revision %s does not declare '%s'"
            % (revision_id.strip(), key)
        )
    for row in rows:
        if not row["covered"]:
            findings.append(
                "declared %s of %g does not envelope the margined mission requirement %g"
                % (row["parameter"], row["declared"], row["required"])
            )
        elif row["over_declared"]:
            findings.append(
                "declared %s of %g over-tests the assembly against a requirement of %g"
                % (row["parameter"], row["declared"], row["required"])
            )
    if not captured_in_time:
        findings.append(
            "drawing revision %s was issued after the test start date; the mission "
            "conditions were not captured before testing" % revision_id.strip()
        )

    return {
        "drawing_revision": revision_id.strip(),
        "mission_envelope": envelope,
        "required_declaration": required,
        "comparison": rows,
        "missing_parameters": absent,
        "captured_before_test": captured_in_time,
        "ready_to_test": not findings,
        "findings": findings,
    }
