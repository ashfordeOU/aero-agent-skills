#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.1.4 -- telemetry monitoring coverage.

Deterministic, offline, stdlib-only helpers that decide whether the
telemetry produced by a subsystem or payload is sufficient to monitor it
during flight operations: each parameter is categorized into a family,
its required sample rate is derived from the observed bandwidth and the
family oversampling factor, its onboard limit set is checked for
ordering and for fit inside the sensor range, the resulting source bit
rate is summed against the downlink allocation, and the monitored
functions are checked for a covering parameter.

Modelling assumptions (documented so a reviewer can challenge them):
  * Required rate = 2 x observed bandwidth x family oversampling
    factor. The factor is a screening value per family, not a
    replacement for a dedicated sampling analysis of a specific sensor.
  * Source bit rate is bits per sample x sample rate, with no packet,
    frame or coding overhead applied; the allocation passed in is
    therefore the allocation at the same reference point.
  * A critical monitored function needs at least one limit-checked
    parameter among the parameters covering it.

No network, no third-party imports, no randomness.
"""

PARAMETER_FAMILIES = {
    "housekeeping-analog": 1.25,
    "discrete-status": 2.0,
    "payload-measurement": 1.0,
    "event-diagnostic": 2.5,
}

FAMILY_ALIASES = {
    "housekeeping-analog": "housekeeping-analog",
    "housekeeping": "housekeeping-analog",
    "analog": "housekeeping-analog",
    "discrete-status": "discrete-status",
    "discrete": "discrete-status",
    "status": "discrete-status",
    "payload-measurement": "payload-measurement",
    "payload": "payload-measurement",
    "science": "payload-measurement",
    "event-diagnostic": "event-diagnostic",
    "event": "event-diagnostic",
    "diagnostic": "event-diagnostic",
}

NYQUIST_FACTOR = 2.0

LIMIT_ORDER = ("low_alarm", "low_warning", "high_warning", "high_alarm")

REQUIRED_PARAMETER_KEYS = (
    "id",
    "kind",
    "bandwidth_hz",
    "sample_rate_hz",
    "bits_per_sample",
    "limit_checked",
    "functions_covered",
)


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    return float(value)


def _bool(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def categorize_telemetry_parameter(kind):
    """Map a free-form parameter kind onto one of the four families."""
    if not isinstance(kind, str):
        raise ValueError("parameter kind must be a string, got %r" % (kind,))
    key = kind.strip().lower().replace("_", "-").replace(" ", "-")
    if not key:
        raise ValueError("parameter kind must not be empty")
    if key not in FAMILY_ALIASES:
        raise ValueError(
            "uncategorized parameter kind %r; expected one of %s"
            % (kind, sorted(PARAMETER_FAMILIES))
        )
    return FAMILY_ALIASES[key]


def required_sample_rate_hz(bandwidth_hz, family):
    """Nyquist rate scaled by the family's oversampling factor, in hertz."""
    if family not in PARAMETER_FAMILIES:
        raise ValueError("uncategorized parameter family %r" % (family,))
    bandwidth = _number(bandwidth_hz, "bandwidth_hz")
    if bandwidth <= 0.0:
        raise ValueError("bandwidth_hz must be > 0, got %r" % (bandwidth_hz,))
    return NYQUIST_FACTOR * PARAMETER_FAMILIES[family] * bandwidth


def check_sampling_adequacy(bandwidth_hz, sample_rate_hz, family):
    """Compare an allocated sample rate against the rate the family demands."""
    required = required_sample_rate_hz(bandwidth_hz, family)
    allocated = _number(sample_rate_hz, "sample_rate_hz")
    if allocated <= 0.0:
        raise ValueError("sample_rate_hz must be > 0, got %r" % (sample_rate_hz,))
    findings = []
    if allocated < required:
        findings.append(
            "sample rate %.3f Hz is below the %.3f Hz required for a %s parameter"
            % (allocated, required, family)
        )
    return {
        "required_hz": required,
        "allocated_hz": allocated,
        "ratio": allocated / required,
        "adequate": not findings,
        "findings": findings,
    }


def check_limit_monitoring(limits, sensor_range):
    """Check the four onboard thresholds are ordered and inside the range."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping of the four thresholds")
    missing = [k for k in LIMIT_ORDER if k not in limits]
    if missing:
        raise ValueError("limits missing thresholds: %s" % ", ".join(sorted(missing)))
    values = [_number(limits[k], k) for k in LIMIT_ORDER]
    if not isinstance(sensor_range, (list, tuple)) or len(sensor_range) != 2:
        raise ValueError("sensor_range must be a (minimum, maximum) pair")
    low = _number(sensor_range[0], "sensor_range minimum")
    high = _number(sensor_range[1], "sensor_range maximum")
    if low >= high:
        raise ValueError("sensor_range minimum must be below its maximum")
    findings = []
    for i in range(len(LIMIT_ORDER) - 1):
        if values[i] >= values[i + 1]:
            findings.append(
                "threshold order broken: %s (%.3f) is not below %s (%.3f)"
                % (LIMIT_ORDER[i], values[i], LIMIT_ORDER[i + 1], values[i + 1])
            )
    for name, value in zip(LIMIT_ORDER, values):
        if value < low or value > high:
            findings.append(
                "threshold %s (%.3f) lies outside the sensor range [%.3f, %.3f]"
                % (name, value, low, high)
            )
    return {"ordered": not findings, "findings": findings}


def parameter_bit_rate_bps(bits_per_sample, sample_rate_hz):
    """Source bit rate of one parameter, bits per second."""
    if isinstance(bits_per_sample, bool) or not isinstance(bits_per_sample, int):
        raise ValueError("bits_per_sample must be an integer, got %r" % (bits_per_sample,))
    if bits_per_sample <= 0:
        raise ValueError("bits_per_sample must be > 0, got %d" % bits_per_sample)
    rate = _number(sample_rate_hz, "sample_rate_hz")
    if rate <= 0.0:
        raise ValueError("sample_rate_hz must be > 0, got %r" % (sample_rate_hz,))
    return bits_per_sample * rate


def compute_downlink_budget(parameters, allocation_bps):
    """Sum the source bit rate of a parameter set against its allocation."""
    if not isinstance(parameters, list):
        raise ValueError("parameters must be a list")
    if not parameters:
        raise ValueError("parameters must not be empty")
    allocation = _number(allocation_bps, "allocation_bps")
    if allocation <= 0.0:
        raise ValueError("allocation_bps must be > 0, got %r" % (allocation_bps,))
    total = 0.0
    for param in parameters:
        if not isinstance(param, dict):
            raise ValueError("each parameter must be a mapping")
        for key in ("bits_per_sample", "sample_rate_hz"):
            if key not in param:
                raise ValueError("parameter missing required key %r" % (key,))
        total += parameter_bit_rate_bps(param["bits_per_sample"], param["sample_rate_hz"])
    findings = []
    if total > allocation:
        findings.append(
            "source bit rate %.1f bit/s exceeds the %.1f bit/s downlink allocation"
            % (total, allocation)
        )
    return {
        "total_bps": total,
        "allocation_bps": allocation,
        "margin_fraction": (allocation - total) / allocation,
        "within_allocation": not findings,
        "findings": findings,
    }


def check_function_coverage(functions, parameters):
    """Flag monitored functions with no parameter, or no onboard monitor."""
    if not isinstance(functions, list) or not functions:
        raise ValueError("functions must be a non-empty list")
    if not isinstance(parameters, list) or not parameters:
        raise ValueError("parameters must be a non-empty list")
    coverage = {}
    for param in parameters:
        if not isinstance(param, dict):
            raise ValueError("each parameter must be a mapping")
        covered = param.get("functions_covered")
        if not isinstance(covered, (list, tuple)):
            raise ValueError("functions_covered must be a list for %r" % (param.get("id"),))
        checked = _bool(param.get("limit_checked", False), "limit_checked")
        for fid in covered:
            if not isinstance(fid, str) or not fid.strip():
                raise ValueError("function id %r must be a non-empty string" % (fid,))
            entry = coverage.setdefault(fid, {"count": 0, "monitored": False})
            entry["count"] += 1
            entry["monitored"] = entry["monitored"] or checked
    findings = []
    for function in functions:
        if not isinstance(function, dict):
            raise ValueError("each function must be a mapping")
        for key in ("id", "critical"):
            if key not in function:
                raise ValueError("function missing required key %r" % (key,))
        critical = _bool(function["critical"], "critical")
        entry = coverage.get(function["id"])
        if entry is None or entry["count"] == 0:
            findings.append("monitored function %s has no telemetry parameter" % function["id"])
            continue
        if critical and not entry["monitored"]:
            findings.append(
                "critical function %s is observed but has no limit-checked parameter"
                % function["id"]
            )
    return {"covered": not findings, "findings": findings}


def assess_telemetry_coverage(subsystem):
    """Full clause 4.1.4 sufficiency check of one telemetry set."""
    if not isinstance(subsystem, dict):
        raise ValueError("subsystem must be a mapping")
    for key in ("id", "parameters", "functions", "downlink_allocation_bps"):
        if key not in subsystem:
            raise ValueError("subsystem missing required key %r" % (key,))
    parameters = subsystem["parameters"]
    if not isinstance(parameters, list) or not parameters:
        raise ValueError("parameters must be a non-empty list")
    findings = []
    per_parameter = []
    seen = set()
    for param in parameters:
        if not isinstance(param, dict):
            raise ValueError("each parameter must be a mapping")
        absent = [k for k in REQUIRED_PARAMETER_KEYS if k not in param]
        if absent:
            raise ValueError("parameter missing required keys: %s" % ", ".join(sorted(absent)))
        if param["id"] in seen:
            raise ValueError("duplicate parameter id %r" % (param["id"],))
        seen.add(param["id"])
        family = categorize_telemetry_parameter(param["kind"])
        sampling = check_sampling_adequacy(
            param["bandwidth_hz"], param["sample_rate_hz"], family
        )
        entry = {
            "id": param["id"],
            "family": family,
            "required_hz": sampling["required_hz"],
            "ratio": sampling["ratio"],
            "findings": list(sampling["findings"]),
        }
        if _bool(param["limit_checked"], "limit_checked"):
            if "limits" not in param or "sensor_range" not in param:
                raise ValueError(
                    "limit-checked parameter %r needs limits and sensor_range" % (param["id"],)
                )
            limits = check_limit_monitoring(param["limits"], param["sensor_range"])
            entry["findings"].extend(limits["findings"])
        entry["findings"] = ["%s: %s" % (param["id"], f) for f in entry["findings"]]
        findings.extend(entry["findings"])
        per_parameter.append(entry)

    budget = compute_downlink_budget(parameters, subsystem["downlink_allocation_bps"])
    findings.extend(budget["findings"])
    coverage = check_function_coverage(subsystem["functions"], parameters)
    findings.extend(coverage["findings"])
    return {
        "id": subsystem["id"],
        "parameters": per_parameter,
        "total_bps": budget["total_bps"],
        "margin_fraction": budget["margin_fraction"],
        "findings": findings,
        "sufficient": not findings,
    }
