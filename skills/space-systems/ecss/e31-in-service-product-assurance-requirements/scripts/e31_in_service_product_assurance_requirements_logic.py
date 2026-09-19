"""In-service thermal monitoring, verification and the product assurance interface.

Anchor: ECSS-E-ST-31C clauses 4.7 and 4.8 (in-service thermal monitoring and
verification of the thermal control system, and the interface the thermal
discipline owes to product assurance and dependability, notably the failure
mode and effects analysis). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Size the on-orbit monitoring of each thermal item: how many sensors, on how
   many independent acquisition chains, sampled how often relative to the
   thermal time constant of the item.
2. Place the alarm limit inside the band between the operational limit and the
   design limit, and report where in that band it sits, because an alarm at
   the design limit leaves no time to act.
3. Perform the in-service verification: compare the flight maximum with the
   predicted maximum as a model drift, and report the margin still standing
   against the design limit.
4. Grade the product assurance interface: each thermal failure mode carries a
   severity category, a statement of whether telemetry can see it, and a
   mitigation. A severe mode with no mitigation is a single point failure and
   is carried out of the assessment by name.
"""

import math

__all__ = [
    "TEMPERATURE_TOLERANCE_K",
    "INTERVAL_TOLERANCE_S",
    "SEVERITIES",
    "MIN_SAMPLES_PER_TIME_CONSTANT",
    "validate_positive",
    "validate_temperature_k",
    "validate_severity",
    "severity_rank",
    "required_sampling_interval_s",
    "sampling_adequate",
    "sensor_coverage_findings",
    "alarm_band_findings",
    "alarm_margin_fraction",
    "in_service_margin_k",
    "model_drift_k",
    "drift_acceptable",
    "criticality_score",
    "evaluate_failure_mode",
    "evaluate_monitored_item",
    "assess_in_service_pa",
]

# Margins, drifts and intervals are differences and quotients of floats. A
# quantity that should sit exactly on its limit can land a few ULPs either
# side, so absorb the representation error here instead of loosening the
# engineering limit.
TEMPERATURE_TOLERANCE_K = 1e-9
INTERVAL_TOLERANCE_S = 1e-9

# Severity categories, most severe first.
SEVERITIES = ("catastrophic", "critical", "major", "minor")

# A thermal transient sampled fewer times than this across one time constant
# cannot be reconstructed from the telemetry.
MIN_SAMPLES_PER_TIME_CONSTANT = 2


def validate_positive(value, label, allow_zero=False):
    """Return a validated positive (optionally non-negative) real quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_temperature_k(value, label):
    """Return a validated absolute temperature in kelvin."""
    temperature = validate_positive(value, label)
    return temperature


def validate_severity(severity):
    """Return a validated severity category name."""
    if not isinstance(severity, str):
        raise ValueError("severity must be a string")
    name = severity.strip().lower()
    if name not in SEVERITIES:
        raise ValueError("unknown severity %r; expected one of %s" % (severity, SEVERITIES))
    return name


def severity_rank(severity):
    """Return the ordinal of a severity category (0 is the most severe)."""
    return SEVERITIES.index(validate_severity(severity))


def required_sampling_interval_s(time_constant_s, samples_per_time_constant):
    """Return the telemetry interval a thermal time constant demands."""
    tau = validate_positive(time_constant_s, "time_constant_s")
    if not isinstance(samples_per_time_constant, int) or isinstance(
        samples_per_time_constant, bool
    ):
        raise ValueError("samples_per_time_constant must be an integer")
    if samples_per_time_constant < MIN_SAMPLES_PER_TIME_CONSTANT:
        raise ValueError(
            "samples_per_time_constant must be at least %d, got %d"
            % (MIN_SAMPLES_PER_TIME_CONSTANT, samples_per_time_constant)
        )
    return tau / float(samples_per_time_constant)


def sampling_adequate(actual_interval_s, required_interval_s):
    """Return True when the telemetry interval is no longer than the required one."""
    actual = validate_positive(actual_interval_s, "actual_interval_s")
    required = validate_positive(required_interval_s, "required_interval_s")
    if actual < required:
        return True
    return math.isclose(actual, required, rel_tol=0.0, abs_tol=INTERVAL_TOLERANCE_S)


def sensor_coverage_findings(identifier, sensors, required_sensors,
                             independent_chains, required_chains):
    """Return the findings raised by the sensor fit of one monitored item."""
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("identifier must be a non-empty string")
    values = {
        "sensors": sensors,
        "required_sensors": required_sensors,
        "independent_chains": independent_chains,
        "required_chains": required_chains,
    }
    for label, value in values.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer" % label)
        if value < 0:
            raise ValueError("%s must be non-negative, got %d" % (label, value))
    if required_sensors < 1:
        raise ValueError("required_sensors must be at least 1")
    if required_chains < 1:
        raise ValueError("required_chains must be at least 1")
    if independent_chains > sensors:
        raise ValueError(
            "independent_chains %d exceeds the sensor count %d" % (independent_chains, sensors)
        )
    name = identifier.strip()
    findings = []
    if sensors < required_sensors:
        findings.append(
            "%s: %d thermal sensors fitted against %d required" % (name, sensors, required_sensors)
        )
    if independent_chains < required_chains:
        findings.append(
            "%s: sensors sit on %d independent acquisition chains against %d required"
            % (name, independent_chains, required_chains)
        )
    return findings


def alarm_band_findings(identifier, operational_limit_k, alarm_limit_k, design_limit_k):
    """Return the findings raised by where an alarm limit sits in its band."""
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("identifier must be a non-empty string")
    operational = validate_temperature_k(operational_limit_k, "operational_limit_k")
    alarm = validate_temperature_k(alarm_limit_k, "alarm_limit_k")
    design = validate_temperature_k(design_limit_k, "design_limit_k")
    if design <= operational:
        raise ValueError(
            "design limit %g K must sit above the operational limit %g K" % (design, operational)
        )
    name = identifier.strip()
    findings = []
    if alarm <= operational and not math.isclose(
        alarm, operational, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K
    ):
        findings.append(
            "%s: alarm limit %g K sits at or below the operational limit %g K and will nuisance-trip"
            % (name, alarm, operational)
        )
    if alarm >= design and not math.isclose(
        alarm, design, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K
    ):
        findings.append(
            "%s: alarm limit %g K sits at or above the design limit %g K and leaves no reaction time"
            % (name, alarm, design)
        )
    return findings


def alarm_margin_fraction(operational_limit_k, alarm_limit_k, design_limit_k):
    """Return where the alarm sits in the operational-to-design band, as a fraction."""
    operational = validate_temperature_k(operational_limit_k, "operational_limit_k")
    alarm = validate_temperature_k(alarm_limit_k, "alarm_limit_k")
    design = validate_temperature_k(design_limit_k, "design_limit_k")
    span = design - operational
    if span <= 0.0:
        raise ValueError("design limit must sit above the operational limit")
    return (alarm - operational) / span


def in_service_margin_k(design_limit_k, flight_maximum_k):
    """Return the margin still standing between the flight maximum and the design limit."""
    design = validate_temperature_k(design_limit_k, "design_limit_k")
    flight = validate_temperature_k(flight_maximum_k, "flight_maximum_k")
    return design - flight


def model_drift_k(predicted_maximum_k, flight_maximum_k):
    """Return the signed in-service model drift: flight minus predicted."""
    predicted = validate_temperature_k(predicted_maximum_k, "predicted_maximum_k")
    flight = validate_temperature_k(flight_maximum_k, "flight_maximum_k")
    return flight - predicted


def drift_acceptable(drift_k, tolerance_k):
    """Return True when a signed model drift sits inside a two-sided tolerance."""
    if not isinstance(drift_k, (int, float)) or isinstance(drift_k, bool):
        raise ValueError("drift_k must be a real number")
    value = float(drift_k)
    if not math.isfinite(value):
        raise ValueError("drift_k must be finite")
    tolerance = validate_positive(tolerance_k, "tolerance_k")
    magnitude = abs(value)
    if magnitude < tolerance:
        return True
    return math.isclose(magnitude, tolerance, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K)


def criticality_score(severity, telemetry_detectable, mitigated):
    """Return the criticality score of a thermal failure mode (higher is worse)."""
    rank = severity_rank(severity)
    score = len(SEVERITIES) - rank
    if not bool(telemetry_detectable):
        score += 1
    if not bool(mitigated):
        score += 1
    return score


def evaluate_failure_mode(mode):
    """Evaluate one thermal failure mode for the product assurance interface."""
    if not isinstance(mode, dict):
        raise ValueError("failure mode must be a mapping")
    for key in ("id", "severity", "telemetry_detectable", "mitigated"):
        if key not in mode:
            raise ValueError("failure mode missing required key '%s'" % key)
    identifier = mode["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("failure mode id must be a non-empty string")
    identifier = identifier.strip()
    severity = validate_severity(mode["severity"])
    detectable = bool(mode["telemetry_detectable"])
    mitigated = bool(mode["mitigated"])
    score = criticality_score(severity, detectable, mitigated)
    single_point = severity_rank(severity) <= severity_rank("critical") and not mitigated
    findings = []
    if single_point:
        findings.append(
            "%s: %s mode carries no mitigation and stands as a single point failure"
            % (identifier, severity)
        )
    if not detectable and severity_rank(severity) <= severity_rank("critical"):
        findings.append(
            "%s: %s mode is not visible in telemetry, so no in-service verification sees it"
            % (identifier, severity)
        )
    return {
        "id": identifier,
        "severity": severity,
        "telemetry_detectable": detectable,
        "mitigated": mitigated,
        "criticality_score": score,
        "single_point_failure": single_point,
        "findings": findings,
    }


def evaluate_monitored_item(item):
    """Evaluate the on-orbit monitoring and in-service verification of one item."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    required_keys = (
        "id", "sensors", "required_sensors", "independent_chains", "required_chains",
        "time_constant_s", "samples_per_time_constant", "telemetry_interval_s",
        "operational_limit_k", "alarm_limit_k", "design_limit_k",
        "predicted_maximum_k", "flight_maximum_k", "drift_tolerance_k",
    )
    for key in required_keys:
        if key not in item:
            raise ValueError("item missing required key '%s'" % key)
    identifier = item["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("item id must be a non-empty string")
    identifier = identifier.strip()

    findings = sensor_coverage_findings(
        identifier, item["sensors"], item["required_sensors"],
        item["independent_chains"], item["required_chains"],
    )
    required_interval = required_sampling_interval_s(
        item["time_constant_s"], item["samples_per_time_constant"]
    )
    sampling_ok = sampling_adequate(item["telemetry_interval_s"], required_interval)
    if not sampling_ok:
        findings.append(
            "%s: telemetry sampled every %g s against a required %g s for a %g s time constant"
            % (identifier, float(item["telemetry_interval_s"]), required_interval,
               float(item["time_constant_s"]))
        )
    findings.extend(alarm_band_findings(
        identifier, item["operational_limit_k"], item["alarm_limit_k"], item["design_limit_k"]
    ))
    placement = alarm_margin_fraction(
        item["operational_limit_k"], item["alarm_limit_k"], item["design_limit_k"]
    )
    margin = in_service_margin_k(item["design_limit_k"], item["flight_maximum_k"])
    margin_ok = margin > 0.0 or math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K
    )
    if not margin_ok:
        findings.append(
            "%s: flight maximum exceeds the design limit by %g K" % (identifier, -margin)
        )
    drift = model_drift_k(item["predicted_maximum_k"], item["flight_maximum_k"])
    drift_ok = drift_acceptable(drift, item["drift_tolerance_k"])
    if not drift_ok:
        findings.append(
            "%s: in-service model drift of %+.2f K exceeds the tolerance of %g K"
            % (identifier, drift, float(item["drift_tolerance_k"]))
        )
    return {
        "id": identifier,
        "required_interval_s": required_interval,
        "sampling_adequate": sampling_ok,
        "alarm_placement_fraction": placement,
        "in_service_margin_k": margin,
        "margin_positive": margin_ok,
        "model_drift_k": drift,
        "drift_acceptable": drift_ok,
        "monitored": not findings,
        "findings": findings,
    }


def assess_in_service_pa(spec):
    """Run the full clause 4.7 and 4.8 in-service and product assurance assessment.

    spec keys: items (monitored thermal items), failure_modes (thermal failure
    modes for the product assurance interface).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("items", "failure_modes"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    items = spec["items"]
    modes = spec["failure_modes"]
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("spec['items'] must be a non-empty sequence")
    if not isinstance(modes, (list, tuple)) or not modes:
        raise ValueError("spec['failure_modes'] must be a non-empty sequence")

    item_records = []
    seen_items = set()
    for item in items:
        record = evaluate_monitored_item(item)
        if record["id"] in seen_items:
            raise ValueError("duplicate monitored item id %r" % record["id"])
        seen_items.add(record["id"])
        item_records.append(record)

    mode_records = []
    seen_modes = set()
    for mode in modes:
        record = evaluate_failure_mode(mode)
        if record["id"] in seen_modes:
            raise ValueError("duplicate failure mode id %r" % record["id"])
        seen_modes.add(record["id"])
        mode_records.append(record)

    findings = []
    for record in item_records:
        findings.extend(record["findings"])
    for record in mode_records:
        findings.extend(record["findings"])

    single_points = [r["id"] for r in mode_records if r["single_point_failure"]]
    worst_mode = max(
        mode_records, key=lambda r: (r["criticality_score"], r["id"])
    )["id"]
    tightest = min(item_records, key=lambda r: (r["in_service_margin_k"], r["id"]))["id"]
    monitored = [r["id"] for r in item_records if r["monitored"]]
    return {
        "items": item_records,
        "failure_modes": mode_records,
        "single_point_failures": single_points,
        "worst_criticality_mode": worst_mode,
        "tightest_margin_item": tightest,
        "monitored_fraction": len(monitored) / float(len(item_records)),
        "compliant": not findings,
        "findings": findings,
    }
