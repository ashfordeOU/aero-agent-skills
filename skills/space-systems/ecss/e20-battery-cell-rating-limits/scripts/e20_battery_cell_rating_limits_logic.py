#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.6.3 -- maximum cell rating limits.

Deterministic, offline, standard-library-only helpers that hold a cell
rating set for temperature, voltage and current, tighten it through a
derating policy, and test declared operating points against the resulting
envelope mode by mode.

The procedure is a paraphrase of the clause intent; no standard text is
reproduced. The clause is cited as the anchor only.
"""

MODES = ("charge", "discharge", "storage")

_CURRENT_LIMIT_KEY = {
    "charge": "max_charge",
    "discharge": "max_discharge",
    "storage": "max_storage_leakage",
}

_DEFAULT_STORAGE_LEAKAGE_A = 0.01


def _number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    return float(value)


def _positive(label, value):
    number = _number(label, value)
    if number <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return number


def _check_mode(mode):
    if mode not in MODES:
        raise ValueError(
            "mode must be one of %s, got %r" % (", ".join(MODES), mode)
        )
    return mode


def _window(label, pair):
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        raise ValueError("%s must be a (lower, upper) pair, got %r" % (label, pair))
    lower = _number("%s lower" % label, pair[0])
    upper = _number("%s upper" % label, pair[1])
    if lower >= upper:
        raise ValueError(
            "%s lower %r is not below upper %r" % (label, lower, upper)
        )
    return (lower, upper)


def validate_cell_ratings(ratings):
    """Normalize a cell rating set covering temperature, voltage and current.

    Required: chemistry, capacity_ah, a temperature window for each of the
    three modes, a maximum charge and minimum discharge voltage, and maximum
    charge and discharge currents. Raises ValueError on any gap or inversion.
    """
    if not isinstance(ratings, dict):
        raise ValueError("cell ratings must be a mapping, got %r" % (ratings,))
    chemistry = ratings.get("chemistry")
    if not isinstance(chemistry, str) or not chemistry.strip():
        raise ValueError("cell ratings need a non-empty string 'chemistry'")
    capacity_ah = _positive("capacity_ah", ratings.get("capacity_ah"))

    raw_temp = ratings.get("temperature_c")
    if not isinstance(raw_temp, dict):
        raise ValueError("cell ratings need a 'temperature_c' mapping per mode")
    temperature_c = {}
    for mode in MODES:
        if mode not in raw_temp:
            raise ValueError("temperature_c is missing the %s window" % mode)
        temperature_c[mode] = _window("temperature_c[%s]" % mode, raw_temp[mode])

    raw_v = ratings.get("voltage_v")
    if not isinstance(raw_v, dict):
        raise ValueError("cell ratings need a 'voltage_v' mapping")
    max_charge_v = _positive("voltage_v.max_charge", raw_v.get("max_charge"))
    min_discharge_v = _positive("voltage_v.min_discharge", raw_v.get("min_discharge"))
    if min_discharge_v >= max_charge_v:
        raise ValueError(
            "voltage_v.min_discharge %r is not below max_charge %r"
            % (min_discharge_v, max_charge_v)
        )

    raw_i = ratings.get("current_a")
    if not isinstance(raw_i, dict):
        raise ValueError("cell ratings need a 'current_a' mapping")
    current_a = {
        "max_charge": _positive("current_a.max_charge", raw_i.get("max_charge")),
        "max_discharge": _positive(
            "current_a.max_discharge", raw_i.get("max_discharge")
        ),
        "max_storage_leakage": _positive(
            "current_a.max_storage_leakage",
            raw_i.get("max_storage_leakage", _DEFAULT_STORAGE_LEAKAGE_A),
        ),
    }
    return {
        "chemistry": chemistry.strip().lower(),
        "capacity_ah": capacity_ah,
        "temperature_c": temperature_c,
        "voltage_v": {
            "max_charge": max_charge_v,
            "min_discharge": min_discharge_v,
        },
        "current_a": current_a,
        "derated": bool(ratings.get("derated", False)),
    }


def apply_derating(ratings, policy):
    """Tighten a rating set by a derating policy.

    policy keys: voltage_factor and current_factor in (0, 1], and
    temperature_margin_k >= 0 removed from both ends of every window.
    Raises ValueError if the policy collapses any window.
    """
    base = validate_cell_ratings(ratings)
    if not isinstance(policy, dict):
        raise ValueError("derating policy must be a mapping, got %r" % (policy,))
    v_factor = _number("voltage_factor", policy.get("voltage_factor", 1.0))
    i_factor = _number("current_factor", policy.get("current_factor", 1.0))
    for label, factor in (("voltage_factor", v_factor), ("current_factor", i_factor)):
        if not 0.0 < factor <= 1.0:
            raise ValueError("%s must lie in (0, 1], got %r" % (label, factor))
    margin_k = _number("temperature_margin_k", policy.get("temperature_margin_k", 0.0))
    if margin_k < 0.0:
        raise ValueError("temperature_margin_k must be >= 0, got %r" % (margin_k,))

    temperature_c = {}
    for mode, (lower, upper) in base["temperature_c"].items():
        new_lower = lower + margin_k
        new_upper = upper - margin_k
        if new_lower >= new_upper:
            raise ValueError(
                "temperature_margin_k %r collapses the %s window" % (margin_k, mode)
            )
        temperature_c[mode] = (new_lower, new_upper)

    max_charge_v = base["voltage_v"]["max_charge"] * v_factor
    min_discharge_v = base["voltage_v"]["min_discharge"] / v_factor
    if min_discharge_v >= max_charge_v:
        raise ValueError(
            "voltage_factor %r collapses the cell voltage window" % (v_factor,)
        )
    current_a = {
        key: value * i_factor for key, value in base["current_a"].items()
    }
    derated = dict(base)
    derated["temperature_c"] = temperature_c
    derated["voltage_v"] = {
        "max_charge": max_charge_v,
        "min_discharge": min_discharge_v,
    }
    derated["current_a"] = current_a
    derated["derated"] = True
    return derated


def c_rate(current_a, capacity_ah):
    """Current expressed as a multiple of the one-hour rate."""
    capacity = _positive("capacity_ah", capacity_ah)
    current = _number("current_a", current_a)
    if current < 0.0:
        raise ValueError("current_a magnitude must be >= 0, got %r" % (current_a,))
    return current / capacity


def _verdict(parameter, mode, value, lower, upper, span):
    margins = []
    if lower is not None:
        margins.append(value - lower)
    if upper is not None:
        margins.append(upper - value)
    margin = min(margins)
    return {
        "parameter": parameter,
        "mode": mode,
        "value": value,
        "lower_limit": lower,
        "upper_limit": upper,
        "margin": margin,
        "normalized_margin": margin / span,
        "within_limits": margin >= 0.0,
    }


def check_temperature(temperature_c, mode, ratings):
    """Test a cell temperature against the window for that mode."""
    validated = validate_cell_ratings(ratings)
    _check_mode(mode)
    value = _number("temperature_c", temperature_c)
    lower, upper = validated["temperature_c"][mode]
    return _verdict("temperature", mode, value, lower, upper, upper - lower)


def check_voltage(voltage_v, mode, ratings):
    """Test a cell voltage against the limits that bound the given mode."""
    validated = validate_cell_ratings(ratings)
    _check_mode(mode)
    value = _positive("voltage_v", voltage_v)
    max_charge = validated["voltage_v"]["max_charge"]
    min_discharge = validated["voltage_v"]["min_discharge"]
    if mode == "charge":
        lower, upper = None, max_charge
        span = max_charge
    elif mode == "discharge":
        lower, upper = min_discharge, max_charge
        span = max_charge - min_discharge
    else:
        lower, upper = min_discharge, max_charge
        span = max_charge - min_discharge
    return _verdict("voltage", mode, value, lower, upper, span)


def check_current(current_a, mode, ratings):
    """Test a current magnitude against the limit that bounds the given mode."""
    validated = validate_cell_ratings(ratings)
    _check_mode(mode)
    value = _number("current_a", current_a)
    if value < 0.0:
        raise ValueError("current_a magnitude must be >= 0, got %r" % (current_a,))
    limit = validated["current_a"][_CURRENT_LIMIT_KEY[mode]]
    verdict = _verdict("current", mode, value, None, limit, limit)
    verdict["c_rate"] = c_rate(value, validated["capacity_ah"])
    return verdict


def evaluate_operating_point(point, ratings):
    """Run all three parameter checks on one declared operating point."""
    if not isinstance(point, dict):
        raise ValueError("operating point must be a mapping, got %r" % (point,))
    point_id = point.get("id")
    if not isinstance(point_id, str) or not point_id.strip():
        raise ValueError("operating point needs a non-empty string 'id'")
    point_id = point_id.strip()
    mode = _check_mode(point.get("mode"))
    for key in ("temperature_c", "voltage_v", "current_a"):
        if point.get(key) is None:
            raise ValueError("%s: operating point is missing %s" % (point_id, key))
    checks = (
        check_temperature(point["temperature_c"], mode, ratings),
        check_voltage(point["voltage_v"], mode, ratings),
        check_current(point["current_a"], mode, ratings),
    )
    exceedances = tuple(
        "%s: %s in %s at %r outside limits (margin %.4f)"
        % (point_id, chk["parameter"], mode, chk["value"], chk["margin"])
        for chk in checks
        if not chk["within_limits"]
    )
    limiting = min(checks, key=lambda chk: chk["normalized_margin"])
    return {
        "id": point_id,
        "mode": mode,
        "checks": checks,
        "exceedances": exceedances,
        "within_limits": not exceedances,
        "limiting_parameter": limiting["parameter"],
        "limiting_normalized_margin": limiting["normalized_margin"],
    }


def assess_operating_envelope(points, ratings, policy=None):
    """Evaluate a duty profile against the rating set, derated if a policy is given."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("points must be a non-empty list of operating points")
    effective = (
        validate_cell_ratings(ratings)
        if policy is None
        else apply_derating(ratings, policy)
    )
    records = []
    findings = []
    seen = set()
    for point in points:
        record = evaluate_operating_point(point, effective)
        if record["id"] in seen:
            raise ValueError("duplicate operating point id %r" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
        findings.extend(record["exceedances"])
    worst = min(records, key=lambda rec: rec["limiting_normalized_margin"])
    return {
        "ratings": effective,
        "records": tuple(records),
        "findings": tuple(findings),
        "worst_point_id": worst["id"],
        "worst_parameter": worst["limiting_parameter"],
        "worst_normalized_margin": worst["limiting_normalized_margin"],
        "within_envelope": not findings,
    }
