"""Thermal control verification by analysis: steady, transient and correlation.

Anchor: ECSS-E-ST-31C clauses 4.5.1 and 4.5.2.1 (verification by analysis;
thermal mathematical model and its correlation). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Close the steady-state radiative balance of a radiating surface and invert
   it to size the radiator area a load needs at its temperature limit.
2. Form the linearised radiative time constant and integrate the lumped
   capacitance transient with an explicit step the stability limit allows.
3. Correlate the model against measured temperatures: per-sensor residuals,
   their mean and spread, and a ranking of which model parameter can absorb
   the systematic part inside its credible range.
"""

import math

__all__ = [
    "STEFAN_BOLTZMANN_W_M2_K4",
    "TEMPERATURE_TOLERANCE_K",
    "STABILITY_SAFETY_FACTOR",
    "validate_surface",
    "radiative_rejection_w",
    "steady_state_temperature_k",
    "required_radiator_area_m2",
    "linearised_time_constant_s",
    "max_stable_step_s",
    "integrate_transient",
    "sensor_residuals_k",
    "correlation_statistics",
    "rank_parameter_attribution",
    "assess_tcs_analysis",
]

STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8

# Temperature comparisons are fourth-root results and can land exactly on a
# limit. Absorb the representation error here instead of moving the limit.
TEMPERATURE_TOLERANCE_K = 1e-9

# An explicit step is only offered up to this fraction of the linearised time
# constant; beyond it the trajectory oscillates instead of relaxing.
STABILITY_SAFETY_FACTOR = 0.5


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


def _require_emittance(value, label):
    """Return an emittance validated into the open unit interval."""
    out = _require_real(value, label)
    if out <= 0.0 or out > 1.0:
        raise ValueError("%s must lie in (0, 1], got %g" % (label, out))
    return out


def validate_surface(area_m2, emittance, sink_k):
    """Return the validated radiating surface of a case."""
    area = _require_positive(area_m2, "area_m2")
    eps = _require_emittance(emittance, "emittance")
    sink = _require_non_negative(sink_k, "sink_k")
    return (area, eps, sink)


def radiative_rejection_w(area_m2, emittance, surface_k, sink_k):
    """Return the net power a surface radiates to its sink.

    A surface below its sink returns a negative value: it is absorbing, which
    is a legitimate case and not an error.
    """
    area, eps, sink = validate_surface(area_m2, emittance, sink_k)
    surface = _require_positive(surface_k, "surface_k")
    return area * eps * STEFAN_BOLTZMANN_W_M2_K4 * (surface ** 4 - sink ** 4)


def steady_state_temperature_k(dissipation_w, absorbed_external_w, area_m2,
                               emittance, sink_k):
    """Return the equilibrium surface temperature of the radiative balance."""
    area, eps, sink = validate_surface(area_m2, emittance, sink_k)
    dissipation = _require_non_negative(dissipation_w, "dissipation_w")
    absorbed = _require_non_negative(absorbed_external_w, "absorbed_external_w")
    load = dissipation + absorbed
    fourth_power = load / (area * eps * STEFAN_BOLTZMANN_W_M2_K4) + sink ** 4
    return fourth_power ** 0.25


def required_radiator_area_m2(load_w, emittance, limit_k, sink_k):
    """Return the radiator area the load needs to stay at its temperature limit."""
    load = _require_positive(load_w, "load_w")
    eps = _require_emittance(emittance, "emittance")
    limit = _require_positive(limit_k, "limit_k")
    sink = _require_non_negative(sink_k, "sink_k")
    if limit <= sink + TEMPERATURE_TOLERANCE_K:
        raise ValueError(
            "a limit of %g K at or below the %g K sink rejects no load at any "
            "area" % (limit, sink)
        )
    return load / (eps * STEFAN_BOLTZMANN_W_M2_K4 * (limit ** 4 - sink ** 4))


def linearised_time_constant_s(capacitance_j_per_k, area_m2, emittance,
                               reference_k):
    """Return the radiative time constant linearised about a temperature."""
    capacitance = _require_positive(capacitance_j_per_k, "capacitance_j_per_k")
    area = _require_positive(area_m2, "area_m2")
    eps = _require_emittance(emittance, "emittance")
    reference = _require_positive(reference_k, "reference_k")
    conductance = 4.0 * area * eps * STEFAN_BOLTZMANN_W_M2_K4 * reference ** 3
    return capacitance / conductance


def max_stable_step_s(capacitance_j_per_k, area_m2, emittance, reference_k):
    """Return the largest explicit step this integration will accept."""
    tau = linearised_time_constant_s(
        capacitance_j_per_k, area_m2, emittance, reference_k
    )
    return STABILITY_SAFETY_FACTOR * tau


def integrate_transient(initial_k, dissipation_w, absorbed_external_w, area_m2,
                        emittance, sink_k, capacitance_j_per_k, step_s, steps):
    """Integrate the lumped-capacitance transient explicitly.

    The step is refused when it exceeds the stability limit at the initial
    temperature, because an oscillating trajectory still terminates with a
    plausible looking number.
    """
    area, eps, sink = validate_surface(area_m2, emittance, sink_k)
    temperature = _require_positive(initial_k, "initial_k")
    dissipation = _require_non_negative(dissipation_w, "dissipation_w")
    absorbed = _require_non_negative(absorbed_external_w, "absorbed_external_w")
    capacitance = _require_positive(capacitance_j_per_k, "capacitance_j_per_k")
    step = _require_positive(step_s, "step_s")
    if not isinstance(steps, int) or isinstance(steps, bool) or steps < 1:
        raise ValueError("steps must be an integer of at least one, got %r" % (steps,))
    limit = max_stable_step_s(capacitance, area, eps, temperature)
    if step > limit + TEMPERATURE_TOLERANCE_K:
        raise ValueError(
            "step %g s exceeds the stable limit %g s for this capacitance and "
            "radiator" % (step, limit)
        )
    trajectory = [temperature]
    for _ in range(steps):
        net = dissipation + absorbed - radiative_rejection_w(
            area, eps, temperature, sink
        )
        temperature = temperature + step * net / capacitance
        if temperature <= 0.0:
            raise ValueError(
                "the trajectory left the physical range; reduce the step"
            )
        trajectory.append(temperature)
    return {
        "trajectory": trajectory,
        "final_k": temperature,
        "step_s": step,
        "max_stable_step_s": limit,
    }


def sensor_residuals_k(predicted, measured):
    """Return the per-sensor predicted-minus-measured residuals.

    Both arguments are mappings keyed by sensor name. A measured sensor with
    no predicted counterpart is reported rather than silently dropped.
    """
    for label, value in (("predicted", predicted), ("measured", measured)):
        if not isinstance(value, dict):
            raise ValueError("%s must be a mapping keyed by sensor name" % label)
    if not measured:
        raise ValueError("measured must carry at least one sensor")
    residuals = {}
    unmodelled = []
    for name in sorted(measured):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("sensor names must be non-empty strings")
        observed = _require_real(measured[name], "measured['%s']" % name)
        if observed <= 0.0:
            raise ValueError("measured['%s'] must be an absolute temperature" % name)
        if name not in predicted:
            unmodelled.append(name)
            continue
        model = _require_real(predicted[name], "predicted['%s']" % name)
        if model <= 0.0:
            raise ValueError("predicted['%s'] must be an absolute temperature" % name)
        residuals[name] = model - observed
    return {"residuals": residuals, "unmodelled_sensors": unmodelled}


def correlation_statistics(residuals):
    """Return the mean, spread and worst magnitude of a residual set."""
    if isinstance(residuals, dict):
        values = [
            _require_real(residuals[name], "residuals['%s']" % name)
            for name in sorted(residuals)
        ]
    elif isinstance(residuals, (list, tuple)):
        values = [
            _require_real(value, "residuals[%d]" % index)
            for index, value in enumerate(residuals)
        ]
    else:
        raise ValueError("residuals must be a mapping or a sequence")
    if not values:
        raise ValueError("residuals must carry at least one sensor")
    count = len(values)
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / count
    return {
        "count": count,
        "mean_k": mean,
        "spread_k": math.sqrt(variance),
        "max_abs_k": max(abs(value) for value in values),
    }


def rank_parameter_attribution(mean_residual_k, parameters):
    """Rank model parameters by the change each needs to absorb the residual.

    Each parameter carries a name, a temperature sensitivity in K per unit and
    a credible range in the same units; a parameter needing more than its
    range is marked as not defensible.
    """
    residual = _require_real(mean_residual_k, "mean_residual_k")
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("parameters must be a non-empty sequence")
    ranked = []
    for index, item in enumerate(parameters):
        if not isinstance(item, dict):
            raise ValueError("parameters[%d] must be a mapping" % index)
        for key in ("name", "sensitivity_k_per_unit", "credible_range"):
            if key not in item:
                raise ValueError("parameters[%d] missing '%s'" % (index, key))
        name = item["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("parameters[%d]['name'] must be a non-empty string" % index)
        sensitivity = _require_real(
            item["sensitivity_k_per_unit"], "parameters[%d] sensitivity" % index
        )
        if sensitivity == 0.0:
            raise ValueError(
                "parameter %s has zero temperature sensitivity and cannot "
                "explain a residual" % name
            )
        credible = _require_non_negative(
            item["credible_range"], "parameters[%d] credible_range" % index
        )
        required_change = -residual / sensitivity
        defensible = abs(required_change) <= credible + TEMPERATURE_TOLERANCE_K
        ranked.append({
            "name": name,
            "required_change": required_change,
            "credible_range": credible,
            "defensible": defensible,
        })
    ranked.sort(key=lambda record: (abs(record["required_change"]), record["name"]))
    return ranked


def assess_tcs_analysis(spec):
    """Run the full clauses 4.5.1 and 4.5.2.1 analysis verification.

    spec keys: area_m2, emittance, sink_k, dissipation_w, absorbed_external_w,
    limit_k, predicted, measured, parameters; optional capacitance_j_per_k,
    step_s, steps, initial_k, mean_tolerance_k, spread_tolerance_k.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "area_m2", "emittance", "sink_k", "dissipation_w", "absorbed_external_w",
        "limit_k", "predicted", "measured", "parameters",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    equilibrium = steady_state_temperature_k(
        spec["dissipation_w"], spec["absorbed_external_w"], spec["area_m2"],
        spec["emittance"], spec["sink_k"],
    )
    limit = _require_positive(spec["limit_k"], "limit_k")
    load = _require_non_negative(spec["dissipation_w"], "dissipation_w") + \
        _require_non_negative(spec["absorbed_external_w"], "absorbed_external_w")
    area_needed = required_radiator_area_m2(
        load, spec["emittance"], limit, spec["sink_k"]
    ) if load > 0.0 else 0.0
    findings = []
    if equilibrium > limit + TEMPERATURE_TOLERANCE_K:
        findings.append(
            "the steady-state balance settles at %.3f K against a %.3f K limit"
            % (equilibrium, limit)
        )
    if area_needed > _require_positive(spec["area_m2"], "area_m2") + TEMPERATURE_TOLERANCE_K:
        findings.append(
            "the load needs %.4f m2 of radiator against the %.4f m2 installed"
            % (area_needed, spec["area_m2"])
        )
    transient = None
    if "capacitance_j_per_k" in spec:
        transient = integrate_transient(
            spec.get("initial_k", equilibrium),
            spec["dissipation_w"], spec["absorbed_external_w"], spec["area_m2"],
            spec["emittance"], spec["sink_k"], spec["capacitance_j_per_k"],
            spec.get("step_s", max_stable_step_s(
                spec["capacitance_j_per_k"], spec["area_m2"], spec["emittance"],
                spec.get("initial_k", equilibrium),
            )),
            spec.get("steps", 10),
        )
    residual_set = sensor_residuals_k(spec["predicted"], spec["measured"])
    if not residual_set["residuals"]:
        raise ValueError("no measured sensor has a predicted counterpart")
    statistics = correlation_statistics(residual_set["residuals"])
    for name in residual_set["unmodelled_sensors"]:
        findings.append("sensor %s has no counterpart in the model" % name)
    mean_tolerance = spec.get("mean_tolerance_k")
    if mean_tolerance is not None:
        mean_tolerance = _require_non_negative(mean_tolerance, "mean_tolerance_k")
        if abs(statistics["mean_k"]) > mean_tolerance + TEMPERATURE_TOLERANCE_K:
            findings.append(
                "the mean residual %.3f K exceeds the %.3f K allowance"
                % (statistics["mean_k"], mean_tolerance)
            )
    spread_tolerance = spec.get("spread_tolerance_k")
    if spread_tolerance is not None:
        spread_tolerance = _require_non_negative(spread_tolerance, "spread_tolerance_k")
        if statistics["spread_k"] > spread_tolerance + TEMPERATURE_TOLERANCE_K:
            findings.append(
                "the residual spread %.3f K exceeds the %.3f K allowance"
                % (statistics["spread_k"], spread_tolerance)
            )
    attribution = rank_parameter_attribution(statistics["mean_k"], spec["parameters"])
    if not any(record["defensible"] for record in attribution):
        findings.append(
            "no declared parameter can absorb the mean residual inside its "
            "credible range"
        )
    return {
        "equilibrium_k": equilibrium,
        "required_area_m2": area_needed,
        "transient": transient,
        "residuals": residual_set["residuals"],
        "unmodelled_sensors": residual_set["unmodelled_sensors"],
        "statistics": statistics,
        "attribution": attribution,
        "findings": findings,
        "compliant": not findings,
    }
