"""Ball-bearing preload sizing, measurement and re-verification for mechanisms.

Anchor: ECSS-E-ST-33-01C clause 4.7.3.4.2 (ball bearings are preloaded against
the mechanical environment; the preload is computed, applied, measured and
re-verified, with solid and flexible arrangements treated differently).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Pick the separation factor the mounting arrangement earns. A solidly
   preloaded duplex pair shares an external axial load between the two rows
   through a Hertzian load-deflection law, so the loaded row does not lift
   until the external load reaches several times the preload. A flexible
   (spring) arrangement gives no such sharing: the unloading row lifts as soon
   as the external load reaches the preload.
2. Size the preload from the worst-case axial reaction and the safety factor.
3. Relate preload to axial stiffness through the Hertzian one-third power law,
   and stiffness to the axial natural frequency of the supported mass, so an
   installed preload can be inferred from a measurement rather than assumed
   from the assembly procedure.
4. Predict the preload shift differential thermal expansion produces between
   shaft and housing, through the effective axial stiffness of the preload
   path -- the bearing stack alone for a solid mount, the bearing stack in
   series with the preload spring for a flexible one.
5. Re-verify: the preload at every thermal case must stay above the no-unload
   floor and below the torque-and-life ceiling, and a measured preload must
   agree with the applied value inside the measurement tolerance.
"""

import math

__all__ = [
    "SEPARATION_FACTORS",
    "PRELOAD_TOLERANCE_N",
    "separation_factor",
    "required_preload_n",
    "axial_stiffness_n_per_m",
    "preload_from_stiffness_n",
    "axial_natural_frequency_hz",
    "preload_from_frequency_n",
    "effective_preload_path_stiffness",
    "differential_axial_growth_m",
    "preload_after_temperature_n",
    "assess_preload",
]

# A solidly preloaded duplex pair shares an external axial load between its
# rows; the unloading row lifts only near this multiple of the preload. A
# flexible arrangement shares nothing, so the multiple is one.
SEPARATION_FACTORS = {
    "solid": 2.8,
    "flexible": 1.0,
}

# Preload comparisons are differences of products of measured quantities; an
# exact equality at a bound can land a few ULPs on either side.
PRELOAD_TOLERANCE_N = 1e-9


def _require_real(label, value):
    """Return value as a finite float, refusing anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(label, value):
    """Return value as a strictly positive float."""
    out = _require_real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def separation_factor(mount_type):
    """Return the external-load multiple at which the unloading row lifts."""
    if not isinstance(mount_type, str):
        raise ValueError("mount_type must be a string, got %r" % (mount_type,))
    key = mount_type.strip().lower()
    if key not in SEPARATION_FACTORS:
        raise ValueError(
            "unknown mount_type %r; expected one of %s"
            % (mount_type, ", ".join(sorted(SEPARATION_FACTORS)))
        )
    return SEPARATION_FACTORS[key]


def required_preload_n(worst_case_axial_load_n, safety_factor, mount_type):
    """Return the preload that keeps the pair seated under the worst-case load."""
    load = _require_positive("worst_case_axial_load_n", worst_case_axial_load_n)
    factor = _require_positive("safety_factor", safety_factor)
    if factor < 1.0:
        raise ValueError("safety_factor must be at least 1.0, got %g" % factor)
    return load * factor / separation_factor(mount_type)


def axial_stiffness_n_per_m(preload_n, stiffness_coefficient):
    """Return the axial stiffness of a preloaded pair, k = C * P**(1/3).

    The one-third power comes from the Hertzian point-contact load-deflection
    law: stiffening with preload is real but strongly sub-linear, which is why
    doubling a preload does not double a measured natural frequency.
    """
    preload = _require_positive("preload_n", preload_n)
    coefficient = _require_positive("stiffness_coefficient", stiffness_coefficient)
    return coefficient * preload ** (1.0 / 3.0)


def preload_from_stiffness_n(stiffness_n_per_m, stiffness_coefficient):
    """Invert the one-third power law to recover a preload from a stiffness."""
    stiffness = _require_positive("stiffness_n_per_m", stiffness_n_per_m)
    coefficient = _require_positive("stiffness_coefficient", stiffness_coefficient)
    return (stiffness / coefficient) ** 3.0


def axial_natural_frequency_hz(stiffness_n_per_m, supported_mass_kg):
    """Return the axial natural frequency of the supported mass on the pair."""
    stiffness = _require_positive("stiffness_n_per_m", stiffness_n_per_m)
    mass = _require_positive("supported_mass_kg", supported_mass_kg)
    return math.sqrt(stiffness / mass) / (2.0 * math.pi)


def preload_from_frequency_n(frequency_hz, supported_mass_kg, stiffness_coefficient):
    """Infer the installed preload from a measured axial natural frequency."""
    frequency = _require_positive("frequency_hz", frequency_hz)
    mass = _require_positive("supported_mass_kg", supported_mass_kg)
    omega = 2.0 * math.pi * frequency
    stiffness = mass * omega * omega
    return preload_from_stiffness_n(stiffness, stiffness_coefficient)


def effective_preload_path_stiffness(bearing_stiffness_n_per_m, mount_type,
                                     spring_rate_n_per_m=None):
    """Return the stiffness the preload path presents to a differential growth.

    A solid mount presents the bearing stack alone. A flexible mount puts the
    preload spring in series with it, and the softer member dominates -- which
    is the whole point of choosing a flexible arrangement.
    """
    bearing = _require_positive("bearing_stiffness_n_per_m", bearing_stiffness_n_per_m)
    key = mount_type.strip().lower() if isinstance(mount_type, str) else mount_type
    separation_factor(key)
    if key == "solid":
        if spring_rate_n_per_m is not None:
            raise ValueError("a solid preload arrangement has no preload spring rate")
        return bearing
    if spring_rate_n_per_m is None:
        raise ValueError("a flexible preload arrangement needs spring_rate_n_per_m")
    spring = _require_positive("spring_rate_n_per_m", spring_rate_n_per_m)
    return 1.0 / (1.0 / bearing + 1.0 / spring)


def differential_axial_growth_m(cte_housing_per_k, cte_shaft_per_k, span_m, delta_t_k):
    """Return the axial growth mismatch between housing and shaft over a span.

    A positive result means the housing grew more than the shaft, which pulls
    the preload down on a solid mount.
    """
    cte_h = _require_real("cte_housing_per_k", cte_housing_per_k)
    cte_s = _require_real("cte_shaft_per_k", cte_shaft_per_k)
    span = _require_positive("span_m", span_m)
    delta_t = _require_real("delta_t_k", delta_t_k)
    return (cte_h - cte_s) * span * delta_t


def preload_after_temperature_n(applied_preload_n, path_stiffness_n_per_m, growth_m):
    """Return the preload left after a differential growth, floored at zero."""
    applied = _require_positive("applied_preload_n", applied_preload_n)
    stiffness = _require_positive("path_stiffness_n_per_m", path_stiffness_n_per_m)
    growth = _require_real("growth_m", growth_m)
    shifted = applied - stiffness * growth
    if shifted < 0.0:
        return 0.0
    return shifted


def assess_preload(spec):
    """Run the full clause 4.7.3.4.2 preload assessment.

    spec keys: mount_type, worst_case_axial_load_n, safety_factor,
    applied_preload_n, stiffness_coefficient, supported_mass_kg,
    cte_housing_per_k, cte_shaft_per_k, span_m, thermal_cases (list of
    {name, delta_t_k}); optional spring_rate_n_per_m, max_preload_n,
    measured_frequency_hz, measurement_tolerance.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "mount_type",
        "worst_case_axial_load_n",
        "safety_factor",
        "applied_preload_n",
        "stiffness_coefficient",
        "supported_mass_kg",
        "cte_housing_per_k",
        "cte_shaft_per_k",
        "span_m",
        "thermal_cases",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    mount = spec["mount_type"]
    factor = separation_factor(mount)
    required = required_preload_n(
        spec["worst_case_axial_load_n"], spec["safety_factor"], mount
    )
    applied = _require_positive("applied_preload_n", spec["applied_preload_n"])
    coefficient = _require_positive("stiffness_coefficient", spec["stiffness_coefficient"])
    bearing_stiffness = axial_stiffness_n_per_m(applied, coefficient)
    path_stiffness = effective_preload_path_stiffness(
        bearing_stiffness, mount, spec.get("spring_rate_n_per_m")
    )

    findings = []
    if applied < required and not math.isclose(
        applied, required, rel_tol=0.0, abs_tol=PRELOAD_TOLERANCE_N
    ):
        findings.append(
            "applied preload %.4g N is below the %.4g N the worst-case axial load "
            "needs at a separation factor of %.2f" % (applied, required, factor)
        )

    cases = spec["thermal_cases"]
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("thermal_cases must be a non-empty sequence")
    ceiling = spec.get("max_preload_n")
    if ceiling is not None:
        ceiling = _require_positive("max_preload_n", ceiling)
    case_records = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or "name" not in case or "delta_t_k" not in case:
            raise ValueError("thermal_cases[%d] needs 'name' and 'delta_t_k'" % index)
        growth = differential_axial_growth_m(
            spec["cte_housing_per_k"], spec["cte_shaft_per_k"], spec["span_m"],
            case["delta_t_k"],
        )
        preload_here = preload_after_temperature_n(applied, path_stiffness, growth)
        record = {
            "name": case["name"],
            "delta_t_k": float(case["delta_t_k"]),
            "differential_growth_m": growth,
            "preload_n": preload_here,
        }
        case_records.append(record)
        if preload_here < required and not math.isclose(
            preload_here, required, rel_tol=0.0, abs_tol=PRELOAD_TOLERANCE_N
        ):
            findings.append(
                "thermal case '%s' leaves %.4g N, below the %.4g N no-unload floor"
                % (record["name"], preload_here, required)
            )
        if ceiling is not None and preload_here > ceiling and not math.isclose(
            preload_here, ceiling, rel_tol=0.0, abs_tol=PRELOAD_TOLERANCE_N
        ):
            findings.append(
                "thermal case '%s' reaches %.4g N, above the %.4g N torque-and-life "
                "ceiling" % (record["name"], preload_here, ceiling)
            )

    inferred = None
    if "measured_frequency_hz" in spec:
        inferred = preload_from_frequency_n(
            spec["measured_frequency_hz"], spec["supported_mass_kg"], coefficient
        )
        tolerance = _require_positive(
            "measurement_tolerance", spec.get("measurement_tolerance", 0.10)
        )
        if tolerance >= 1.0:
            raise ValueError("measurement_tolerance must be a fraction below 1.0")
        deviation = abs(inferred - applied) / applied
        if deviation > tolerance and not math.isclose(
            deviation, tolerance, rel_tol=1e-12, abs_tol=0.0
        ):
            findings.append(
                "preload measured from the axial frequency is %.4g N, %.1f%% off the "
                "%.4g N applied, outside the %.1f%% tolerance"
                % (inferred, 100.0 * deviation, applied, 100.0 * tolerance)
            )

    coldest = min(case_records, key=lambda r: r["preload_n"])
    hottest = max(case_records, key=lambda r: r["preload_n"])
    return {
        "mount_type": mount.strip().lower(),
        "separation_factor": factor,
        "required_preload_n": required,
        "applied_preload_n": applied,
        "bearing_stiffness_n_per_m": bearing_stiffness,
        "preload_path_stiffness_n_per_m": path_stiffness,
        "axial_frequency_hz": axial_natural_frequency_hz(
            bearing_stiffness, spec["supported_mass_kg"]
        ),
        "thermal_cases": case_records,
        "lowest_preload_case": coldest,
        "highest_preload_case": hottest,
        "measured_preload_n": inferred,
        "compliant": not findings,
        "findings": findings,
    }
