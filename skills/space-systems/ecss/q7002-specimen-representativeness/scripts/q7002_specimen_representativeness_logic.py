"""Representativeness of the test item offered to an outgassing screening run.

Anchor: ECSS-Q-ST-70-02C, test-item clause -- the specimens taken into a
thermal-vacuum outgassing screening have to stand for the material in its
flight state. Paraphrased into an implementable procedure; no standard text is
reproduced.

What this module decides
------------------------
Whether the coupons on the balance bench may be weighed in as the screening
sample for a material, and what has to be raised before they are.

1. Size. Each piece has to sit inside the per-specimen mass window of the
   method, because the window is what keeps the loaded compartment inside the
   effusion behaviour the collector geometry was built for.
2. Number. A screening result is the behaviour of a replicate set, not of one
   coupon, so a set below the replicate minimum is a finding about the set.
3. Shape. Outgassing scales with exposed area, not with mass, so the specific
   surface area of the coupon is compared with the flight part it stands for;
   a thin slice of the same material is a different specimen.
4. State. Cure schedule, cleaning process, surface treatment and material lot
   are each named separately when they drift from the flight build, because a
   screening run carries the state it was given, not the state intended.
5. Preconditioning. The soak that precedes the initial weighing has declared
   hours, temperature and humidity; a soak outside any of them leaves the
   initial mass carrying an unknown amount of absorbed water.
"""

import math

__all__ = [
    "DEFAULT_MASS_WINDOW_MG",
    "MIN_REPLICATES",
    "DEFAULT_CONDITIONING_HOURS",
    "DEFAULT_CONDITIONING_TEMP_BAND_C",
    "DEFAULT_CONDITIONING_RH_BAND_PCT",
    "AREA_RATIO_TOLERANCE",
    "FLIGHT_STATE_KEYS",
    "as_positive_float",
    "normalize_state_value",
    "specific_surface_area",
    "mass_window_finding",
    "area_ratio_deviation",
    "area_finding",
    "state_deviations",
    "conditioning_findings",
    "replicate_finding",
    "evaluate_specimen",
    "assess_specimen_representativeness",
]

# Per-specimen mass window of the screening method, in milligrams.
DEFAULT_MASS_WINDOW_MG = (100.0, 300.0)

# A screening sample below this many coupons reports one piece, not a material.
MIN_REPLICATES = 3

# Declared preconditioning soak before the initial weighing.
DEFAULT_CONDITIONING_HOURS = 24.0
DEFAULT_CONDITIONING_TEMP_BAND_C = (22.0, 24.0)
DEFAULT_CONDITIONING_RH_BAND_PCT = (45.0, 55.0)

# Relative departure of the coupon specific surface area from the flight part
# that is still accepted as the same geometry family.
AREA_RATIO_TOLERANCE = 0.20

# Process attributes that together fix the flight material state.
FLIGHT_STATE_KEYS = (
    "cure-schedule",
    "cleaning-process",
    "surface-treatment",
    "material-lot",
)

# Band comparisons are inclusive; absorb representation error at the edge
# rather than widening the band itself.
BAND_TOLERANCE = 1e-9


def as_positive_float(value, label):
    """Return value as a strictly positive finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _as_finite_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _validate_band(band, label):
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _as_finite_float(band[0], "%s low" % label)
    high = _as_finite_float(band[1], "%s high" % label)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def _in_band(value, band):
    low, high = band
    return (value >= low - BAND_TOLERANCE) and (value <= high + BAND_TOLERANCE)


def normalize_state_value(value):
    """Return a process-attribute value in a form two builds can be compared in."""
    if not isinstance(value, str):
        raise ValueError("process attribute value must be a string, got %r" % (value,))
    collapsed = " ".join(value.split())
    if not collapsed:
        raise ValueError("process attribute value must not be blank")
    return collapsed.casefold()


def specific_surface_area(area_mm2, mass_mg):
    """Return exposed area per unit mass in mm^2/mg for one coupon."""
    area = as_positive_float(area_mm2, "area_mm2")
    mass = as_positive_float(mass_mg, "mass_mg")
    return area / mass


def mass_window_finding(mass_mg, window=DEFAULT_MASS_WINDOW_MG):
    """Return a finding when the coupon mass sits outside the method window."""
    mass = as_positive_float(mass_mg, "mass_mg")
    low, high = _validate_band(window, "mass window")
    if mass < low - BAND_TOLERANCE:
        return "specimen mass %.1f mg is below the %.1f mg window minimum" % (mass, low)
    if mass > high + BAND_TOLERANCE:
        return "specimen mass %.1f mg is above the %.1f mg window maximum" % (mass, high)
    return None


def area_ratio_deviation(specimen_ratio, flight_ratio):
    """Return the signed relative departure of the coupon area ratio from flight."""
    coupon = as_positive_float(specimen_ratio, "specimen_ratio")
    flight = as_positive_float(flight_ratio, "flight_ratio")
    return (coupon - flight) / flight


def area_finding(specimen_ratio, flight_ratio, tolerance=AREA_RATIO_TOLERANCE):
    """Return a finding when the coupon geometry is not the flight geometry."""
    limit = as_positive_float(tolerance, "tolerance")
    deviation = area_ratio_deviation(specimen_ratio, flight_ratio)
    if abs(deviation) <= limit + BAND_TOLERANCE:
        return None
    return (
        "specific surface area departs from the flight part by %+.1f %%, "
        "beyond the %.1f %% allowance" % (deviation * 100.0, limit * 100.0)
    )


def state_deviations(specimen_state, flight_state, keys=FLIGHT_STATE_KEYS):
    """Return the process attributes on which the coupon left the flight build."""
    if not isinstance(specimen_state, dict):
        raise ValueError("specimen_state must be a mapping")
    if not isinstance(flight_state, dict):
        raise ValueError("flight_state must be a mapping")
    if not isinstance(keys, (list, tuple)) or not keys:
        raise ValueError("keys must be a non-empty sequence of attribute names")
    deviations = []
    for key in keys:
        if key not in flight_state:
            raise ValueError("flight_state is missing the attribute '%s'" % key)
        if key not in specimen_state:
            deviations.append(key)
            continue
        if normalize_state_value(specimen_state[key]) != normalize_state_value(
            flight_state[key]
        ):
            deviations.append(key)
    return sorted(deviations)


def conditioning_findings(record, hours=DEFAULT_CONDITIONING_HOURS,
                          temp_band=DEFAULT_CONDITIONING_TEMP_BAND_C,
                          rh_band=DEFAULT_CONDITIONING_RH_BAND_PCT):
    """Return the findings raised by the preconditioning soak of one coupon."""
    if not isinstance(record, dict):
        raise ValueError("conditioning record must be a mapping")
    required = as_positive_float(hours, "hours")
    temperature_band = _validate_band(temp_band, "temperature band")
    humidity_band = _validate_band(rh_band, "humidity band")
    for key in ("hours", "temperature_c", "relative_humidity_pct"):
        if key not in record:
            raise ValueError("conditioning record is missing '%s'" % key)
    soaked = _as_finite_float(record["hours"], "conditioning hours")
    if soaked < 0.0:
        raise ValueError("conditioning hours must not be negative, got %r" % (soaked,))
    temperature = _as_finite_float(record["temperature_c"], "conditioning temperature_c")
    humidity = _as_finite_float(
        record["relative_humidity_pct"], "conditioning relative_humidity_pct"
    )
    if humidity < 0.0 or humidity > 100.0:
        raise ValueError("relative humidity must be a percentage, got %r" % (humidity,))
    findings = []
    if soaked < required - BAND_TOLERANCE:
        findings.append(
            "preconditioning soak of %.1f h is short of the declared %.1f h"
            % (soaked, required)
        )
    if not _in_band(temperature, temperature_band):
        findings.append(
            "preconditioning temperature %.1f C left the %.1f-%.1f C band"
            % (temperature, temperature_band[0], temperature_band[1])
        )
    if not _in_band(humidity, humidity_band):
        findings.append(
            "preconditioning humidity %.1f %% left the %.1f-%.1f %% band"
            % (humidity, humidity_band[0], humidity_band[1])
        )
    return findings


def replicate_finding(count, minimum=MIN_REPLICATES):
    """Return a finding when the screening sample carries too few coupons."""
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("count must be an integer, got %r" % (count,))
    if not isinstance(minimum, int) or isinstance(minimum, bool):
        raise ValueError("minimum must be an integer, got %r" % (minimum,))
    if count < 0:
        raise ValueError("count must not be negative, got %d" % count)
    if minimum < 1:
        raise ValueError("minimum must be at least one, got %d" % minimum)
    if count < minimum:
        return "screening sample carries %d coupon(s); %d are required" % (count, minimum)
    return None


def evaluate_specimen(specimen, flight, options=None):
    """Evaluate one coupon against the flight material state it stands for."""
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping")
    if not isinstance(flight, dict):
        raise ValueError("flight must be a mapping")
    settings = dict(options or {})
    for key in ("id", "mass_mg", "area_mm2", "state", "conditioning"):
        if key not in specimen:
            raise ValueError("specimen is missing '%s'" % key)
    identifier = specimen["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("specimen id must be a non-blank string")
    for key in ("area_mm2", "mass_mg", "state"):
        if key not in flight:
            raise ValueError("flight reference is missing '%s'" % key)
    ratio = specific_surface_area(specimen["area_mm2"], specimen["mass_mg"])
    flight_ratio = specific_surface_area(flight["area_mm2"], flight["mass_mg"])
    findings = []
    mass_note = mass_window_finding(
        specimen["mass_mg"], settings.get("mass_window", DEFAULT_MASS_WINDOW_MG)
    )
    if mass_note:
        findings.append(mass_note)
    geometry_note = area_finding(
        ratio, flight_ratio, settings.get("area_tolerance", AREA_RATIO_TOLERANCE)
    )
    if geometry_note:
        findings.append(geometry_note)
    deviations = state_deviations(
        specimen["state"], flight["state"], settings.get("state_keys", FLIGHT_STATE_KEYS)
    )
    for key in deviations:
        findings.append("process attribute '%s' does not match the flight build" % key)
    findings.extend(
        conditioning_findings(
            specimen["conditioning"],
            settings.get("conditioning_hours", DEFAULT_CONDITIONING_HOURS),
            settings.get("conditioning_temp_band", DEFAULT_CONDITIONING_TEMP_BAND_C),
            settings.get("conditioning_rh_band", DEFAULT_CONDITIONING_RH_BAND_PCT),
        )
    )
    return {
        "id": identifier.strip(),
        "mass_mg": float(specimen["mass_mg"]),
        "specific_surface_area_mm2_per_mg": ratio,
        "flight_specific_surface_area_mm2_per_mg": flight_ratio,
        "area_ratio_deviation": area_ratio_deviation(ratio, flight_ratio),
        "state_deviations": deviations,
        "findings": findings,
        "representative": not findings,
    }


def assess_specimen_representativeness(spec):
    """Run the full test-item representativeness assessment for one material.

    spec keys: specimens (sequence of coupon records), flight (reference part),
    optional options mapping and min_replicates.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("specimens", "flight"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    specimens = spec["specimens"]
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("spec['specimens'] must be a non-empty sequence")
    options = spec.get("options")
    records = [evaluate_specimen(item, spec["flight"], options) for item in specimens]
    seen = set()
    duplicate_ids = []
    for record in records:
        if record["id"] in seen and record["id"] not in duplicate_ids:
            duplicate_ids.append(record["id"])
        seen.add(record["id"])
    findings = []
    minimum = spec.get("min_replicates", MIN_REPLICATES)
    sample_note = replicate_finding(len(records), minimum)
    if sample_note:
        findings.append(sample_note)
    for identifier in sorted(duplicate_ids):
        findings.append("specimen identifier '%s' is used more than once" % identifier)
    rejected = [record["id"] for record in records if not record["representative"]]
    for identifier in rejected:
        findings.append("specimen '%s' is not representative of the flight state" % identifier)
    return {
        "records": records,
        "accepted": [record["id"] for record in records if record["representative"]],
        "rejected": rejected,
        "findings": findings,
        "representative_sample": not findings,
    }
