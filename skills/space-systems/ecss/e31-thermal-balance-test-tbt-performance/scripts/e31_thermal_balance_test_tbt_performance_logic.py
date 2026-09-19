"""Thermal balance test definition and performance grading.

Anchor: ECSS-E-ST-31C clause 4.5.3.1 and its test-case annex (performance of
the thermal balance test). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared balance cases and check the set brackets the mission
   with at least one hot and one cold case.
2. Size the compensation heater power of each case as the absorbed-flux
   shortfall of the lamp bank plus the extra rejection of the colder chamber
   shroud, refusing a negative demand rather than clamping it.
3. Fit the drift rate of each temperature history over the declared window and
   declare steady state only when the window is long enough and every
   reference point sits inside the drift criterion.
4. Cover the declared temperature reference points against the instrumentation
   and its accuracy.
"""

import math

__all__ = [
    "STEFAN_BOLTZMANN_W_M2_K4",
    "SECONDS_PER_HOUR",
    "POWER_TOLERANCE_W",
    "DRIFT_TOLERANCE_K_PER_H",
    "CASE_SENSES",
    "validate_case",
    "validate_case_set",
    "shroud_rejection_delta_w",
    "compensation_heater_power_w",
    "grade_case_compensation",
    "drift_rate_k_per_h",
    "steady_state_verdict",
    "instrumentation_findings",
    "assess_balance_test",
]

STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8
SECONDS_PER_HOUR = 3600.0

# A compensation demand or a drift rate can land exactly on its criterion.
# Absorb the representation error here instead of moving the criterion.
POWER_TOLERANCE_W = 1e-9
DRIFT_TOLERANCE_K_PER_H = 1e-9

CASE_SENSES = ("hot", "cold")


def _require_real(value, label):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _require_real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def _require_non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _require_real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _require_name(value, label):
    """Return a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _require_emittance(value, label):
    """Return an emittance validated into the open unit interval."""
    out = _require_real(value, label)
    if out <= 0.0 or out > 1.0:
        raise ValueError("%s must lie in (0, 1], got %g" % (label, out))
    return out


def validate_case(case):
    """Return one validated thermal balance case.

    case keys: name, sense ('hot' or 'cold'), flight_sink_k, test_sink_k,
    flight_absorbed_w, test_absorbed_w, dissipation_w.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    required = ("name", "sense", "flight_sink_k", "test_sink_k",
                "flight_absorbed_w", "test_absorbed_w", "dissipation_w")
    for key in required:
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    sense = case["sense"]
    if sense not in CASE_SENSES:
        raise ValueError(
            "case sense must be one of %s, got %r" % (", ".join(CASE_SENSES), sense)
        )
    return {
        "name": _require_name(case["name"], "case name"),
        "sense": sense,
        "flight_sink_k": _require_non_negative(case["flight_sink_k"], "flight_sink_k"),
        "test_sink_k": _require_non_negative(case["test_sink_k"], "test_sink_k"),
        "flight_absorbed_w": _require_non_negative(
            case["flight_absorbed_w"], "flight_absorbed_w"
        ),
        "test_absorbed_w": _require_non_negative(
            case["test_absorbed_w"], "test_absorbed_w"
        ),
        "dissipation_w": _require_non_negative(case["dissipation_w"], "dissipation_w"),
    }


def validate_case_set(cases):
    """Return the validated case set, refusing one that does not bracket."""
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence of balance cases")
    validated = [validate_case(case) for case in cases]
    names = [case["name"] for case in validated]
    if len(set(names)) != len(names):
        raise ValueError("balance case names must be unique")
    senses = set(case["sense"] for case in validated)
    if senses != set(CASE_SENSES):
        raise ValueError(
            "the case set must bracket the mission with a hot and a cold case; "
            "got %s" % ", ".join(sorted(senses))
        )
    return validated


def shroud_rejection_delta_w(area_m2, emittance, flight_sink_k, test_sink_k):
    """Return the extra rejection a colder chamber shroud pulls out of the article."""
    area = _require_positive(area_m2, "area_m2")
    eps = _require_emittance(emittance, "emittance")
    flight_sink = _require_non_negative(flight_sink_k, "flight_sink_k")
    test_sink = _require_non_negative(test_sink_k, "test_sink_k")
    return area * eps * STEFAN_BOLTZMANN_W_M2_K4 * (
        flight_sink ** 4 - test_sink ** 4
    )


def compensation_heater_power_w(case, area_m2, emittance):
    """Return the balance heater power that makes a case reproduce flight.

    The demand is the absorbed-flux shortfall of the lamp bank plus the extra
    rejection of the colder shroud. A negative demand is returned as is: the
    caller grades it, because clamping it at zero hides an infeasible case.
    """
    validated = validate_case(case)
    flux_shortfall = validated["flight_absorbed_w"] - validated["test_absorbed_w"]
    shroud_term = shroud_rejection_delta_w(
        area_m2, emittance, validated["flight_sink_k"], validated["test_sink_k"]
    )
    return flux_shortfall + shroud_term


def grade_case_compensation(case, area_m2, emittance, installed_heater_w):
    """Grade one case's compensation demand against the installed heaters."""
    validated = validate_case(case)
    installed = _require_non_negative(installed_heater_w, "installed_heater_w")
    demand = compensation_heater_power_w(case, area_m2, emittance)
    findings = []
    feasible = True
    if demand < -POWER_TOLERANCE_W:
        feasible = False
        findings.append(
            "case %s demands %.3f W of compensation, which balance heaters "
            "cannot deliver; raise the shroud or lower the lamp power"
            % (validated["name"], demand)
        )
    elif demand > installed + POWER_TOLERANCE_W:
        feasible = False
        findings.append(
            "case %s needs %.3f W of compensation against %.3f W installed"
            % (validated["name"], demand, installed)
        )
    return {
        "name": validated["name"],
        "sense": validated["sense"],
        "demand_w": demand,
        "installed_w": installed,
        "feasible": feasible,
        "findings": findings,
    }


def drift_rate_k_per_h(samples):
    """Return the least-squares drift rate of a temperature history in K/h.

    samples is a sequence of (time_s, temperature_k) pairs with strictly
    increasing times.
    """
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("samples needs at least two (time_s, temperature_k) pairs")
    times = []
    values = []
    for index, item in enumerate(samples):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("samples[%d] must be a (time_s, temperature_k) pair" % index)
        time_s = _require_real(item[0], "samples[%d] time_s" % index)
        temperature = _require_real(item[1], "samples[%d] temperature_k" % index)
        if temperature <= 0.0:
            raise ValueError("samples[%d] temperature must be absolute" % index)
        if times and time_s <= times[-1]:
            raise ValueError("sample times must strictly increase (index %d)" % index)
        times.append(time_s)
        values.append(temperature)
    count = len(times)
    mean_t = sum(times) / count
    mean_v = sum(values) / count
    covariance = sum(
        (times[i] - mean_t) * (values[i] - mean_v) for i in range(count)
    )
    variance = sum((times[i] - mean_t) ** 2 for i in range(count))
    if variance <= 0.0:
        raise ValueError("sample times carry no span; the drift rate is undefined")
    return covariance / variance * SECONDS_PER_HOUR


def steady_state_verdict(histories, drift_limit_k_per_h, min_window_s):
    """Decide steady state from the drift of every reference point.

    histories maps a reference point name to its sample sequence.
    """
    if not isinstance(histories, dict) or not histories:
        raise ValueError("histories must be a non-empty mapping of sample sequences")
    limit = _require_positive(drift_limit_k_per_h, "drift_limit_k_per_h")
    window = _require_positive(min_window_s, "min_window_s")
    drifts = {}
    findings = []
    for name in sorted(histories):
        _require_name(name, "history name")
        samples = histories[name]
        rate = drift_rate_k_per_h(samples)
        drifts[name] = rate
        span = samples[-1][0] - samples[0][0]
        if span < window - POWER_TOLERANCE_W:
            findings.append(
                "reference point %s was watched for %.0f s against a %.0f s "
                "window" % (name, span, window)
            )
        if abs(rate) > limit + DRIFT_TOLERANCE_K_PER_H:
            findings.append(
                "reference point %s drifts %.4f K/h against a %.4f K/h criterion"
                % (name, rate, limit)
            )
    worst = max(drifts, key=lambda name: abs(drifts[name]))
    return {
        "drifts_k_per_h": drifts,
        "worst_point": worst,
        "worst_drift_k_per_h": drifts[worst],
        "steady": not findings,
        "findings": findings,
    }


def instrumentation_findings(reference_points, sensors, required_accuracy_k):
    """Return the instrumentation findings of a balance test configuration.

    Each sensor carries a name, the reference point it sits on ('at') and its
    accuracy in kelvin.
    """
    if not isinstance(reference_points, (list, tuple)) or not reference_points:
        raise ValueError("reference_points must be a non-empty sequence")
    if not isinstance(sensors, (list, tuple)):
        raise ValueError("sensors must be a sequence")
    accuracy_limit = _require_positive(required_accuracy_k, "required_accuracy_k")
    declared = [
        _require_name(name, "reference_points[%d]" % index)
        for index, name in enumerate(reference_points)
    ]
    if len(set(declared)) != len(declared):
        raise ValueError("reference_points contains a duplicate name")
    best = {}
    for index, sensor in enumerate(sensors):
        if not isinstance(sensor, dict):
            raise ValueError("sensors[%d] must be a mapping" % index)
        for key in ("name", "at", "accuracy_k"):
            if key not in sensor:
                raise ValueError("sensors[%d] missing '%s'" % (index, key))
        _require_name(sensor["name"], "sensors[%d]['name']" % index)
        at = _require_name(sensor["at"], "sensors[%d]['at']" % index)
        accuracy = _require_positive(sensor["accuracy_k"], "sensors[%d]['accuracy_k']" % index)
        if at not in best or accuracy < best[at]:
            best[at] = accuracy
    findings = []
    for name in declared:
        if name not in best:
            findings.append("temperature reference point %s carries no sensor" % name)
        elif best[name] > accuracy_limit + DRIFT_TOLERANCE_K_PER_H:
            findings.append(
                "the best sensor at %s reads to %.3f K against a %.3f K "
                "requirement" % (name, best[name], accuracy_limit)
            )
    return findings


def assess_balance_test(spec):
    """Run the full clause 4.5.3.1 thermal balance test assessment.

    spec keys: cases, radiator_area_m2, emittance, installed_heater_w,
    reference_points, sensors, required_accuracy_k; optional histories,
    drift_limit_k_per_h, min_window_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = ("cases", "radiator_area_m2", "emittance", "installed_heater_w",
                "reference_points", "sensors", "required_accuracy_k")
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    cases = validate_case_set(spec["cases"])
    graded = [
        grade_case_compensation(
            case, spec["radiator_area_m2"], spec["emittance"],
            spec["installed_heater_w"],
        )
        for case in cases
    ]
    findings = []
    for record in graded:
        findings.extend(record["findings"])
    steady = None
    if "histories" in spec:
        steady = steady_state_verdict(
            spec["histories"],
            spec.get("drift_limit_k_per_h", 0.5),
            spec.get("min_window_s", 3600.0),
        )
        findings.extend(steady["findings"])
    instrumentation = instrumentation_findings(
        spec["reference_points"], spec["sensors"], spec["required_accuracy_k"]
    )
    findings.extend(instrumentation)
    return {
        "cases": graded,
        "total_compensation_w": sum(record["demand_w"] for record in graded),
        "feasible": all(record["feasible"] for record in graded),
        "steady_state": steady,
        "instrumentation_findings": instrumentation,
        "findings": findings,
        "ready": not findings,
    }
