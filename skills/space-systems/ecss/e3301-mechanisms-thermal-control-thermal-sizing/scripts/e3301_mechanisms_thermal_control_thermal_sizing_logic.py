"""Passive thermal sizing of a spacecraft mechanism.

Anchor: ECSS-E-ST-33-01C clauses 4.7.4.1 and 4.7.4.2 (the mechanism is kept
inside its operational temperature limits by the passive thermal design;
conductive and radiative paths are sized, and the gradients they leave are
held below the distortion the mechanism can tolerate). Paraphrased into an
implementable procedure; no standard text is reproduced.

Scope note: this is the mechanism-level sizing of clause 4.7.4. It shares the
conduction and radiation algebra with a general thermal-design method but
answers a different question -- not what the equipment temperature is, but
whether a mechanism stays inside the band its lubricant, its bearing preload
and its alignment budget were sized for, and what conductance would have to be
added to put it there.

Procedure implemented here
--------------------------
1. Turn a conductive path (conductivity, section, length, joints in series)
   into a conductance, and a radiative path (emittance, area, view factor)
   into a radiative coupling.
2. Solve the one-node steady-state balance for each declared case, with the
   dissipation and the absorbed environmental flux on one side and the
   conductive and radiative losses to the sink on the other. The balance is
   quartic in temperature and is solved by bracketed bisection, which cannot
   diverge, rather than by a linearisation that hides a hot case.
3. Grade the solved temperature against the operational band.
4. Size the conductance that would be needed to hold a case at a limit, so a
   failing case comes back with a design action and not only a verdict.
5. Convert the interface gradient into a thermo-elastic distortion and grade
   that against the distortion the mechanism tolerates.
"""

import math

__all__ = [
    "STEFAN_BOLTZMANN",
    "TEMPERATURE_TOLERANCE_K",
    "conductive_conductance_w_per_k",
    "series_conductance_w_per_k",
    "radiative_coupling_m2",
    "heat_balance_residual_w",
    "steady_state_temperature_k",
    "interface_gradient_k",
    "required_conductance_w_per_k",
    "thermoelastic_distortion_m",
    "assess_thermal_sizing",
]

STEFAN_BOLTZMANN = 5.670374419e-8

# Temperature comparisons come out of an iterative solve; an exact equality at
# a limit can land a few ULPs on either side.
TEMPERATURE_TOLERANCE_K = 1e-9

_BISECTION_STEPS = 200


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


def _require_non_negative(label, value):
    """Return value as a non-negative float."""
    out = _require_real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def conductive_conductance_w_per_k(conductivity_w_per_m_k, area_m2, length_m):
    """Return the conductance of one conductive path, k*A/L."""
    k = _require_positive("conductivity_w_per_m_k", conductivity_w_per_m_k)
    area = _require_positive("area_m2", area_m2)
    length = _require_positive("length_m", length_m)
    return k * area / length


def series_conductance_w_per_k(conductances):
    """Return the conductance of several paths in series.

    A bolted or bonded joint in the path is a conductance like any other, and
    the softest member dominates -- which is why a well-conducting bracket
    bolted through a poor interface still runs hot.
    """
    if not isinstance(conductances, (list, tuple)) or not conductances:
        raise ValueError("conductances must be a non-empty sequence")
    reciprocal = 0.0
    for index, value in enumerate(conductances):
        g = _require_positive("conductances[%d]" % index, value)
        reciprocal += 1.0 / g
    return 1.0 / reciprocal


def radiative_coupling_m2(emittance, area_m2, view_factor=1.0):
    """Return the radiative coupling area eps*A*F of a surface to its sink."""
    eps = _require_positive("emittance", emittance)
    if eps > 1.0:
        raise ValueError("emittance %g exceeds unity" % eps)
    area = _require_positive("area_m2", area_m2)
    view = _require_positive("view_factor", view_factor)
    if view > 1.0:
        raise ValueError("view_factor %g exceeds unity" % view)
    return eps * area * view


def heat_balance_residual_w(temperature_k, heat_in_w, conductance_w_per_k,
                            coupling_m2, sink_temperature_k):
    """Return heat in minus heat out at a trial temperature.

    The residual falls monotonically with temperature, which is what makes a
    bracketed bisection safe here.
    """
    t = _require_positive("temperature_k", temperature_k)
    q_in = _require_real("heat_in_w", heat_in_w)
    g = _require_non_negative("conductance_w_per_k", conductance_w_per_k)
    coupling = _require_non_negative("coupling_m2", coupling_m2)
    t_sink = _require_positive("sink_temperature_k", sink_temperature_k)
    conducted = g * (t - t_sink)
    radiated = STEFAN_BOLTZMANN * coupling * (t ** 4 - t_sink ** 4)
    return q_in - conducted - radiated


def steady_state_temperature_k(heat_in_w, conductance_w_per_k, coupling_m2,
                               sink_temperature_k):
    """Solve the one-node steady-state balance for the mechanism temperature."""
    q_in = _require_real("heat_in_w", heat_in_w)
    g = _require_non_negative("conductance_w_per_k", conductance_w_per_k)
    coupling = _require_non_negative("coupling_m2", coupling_m2)
    t_sink = _require_positive("sink_temperature_k", sink_temperature_k)
    if g <= 0.0 and coupling <= 0.0:
        raise ValueError(
            "a mechanism with neither a conductive nor a radiative path to the sink "
            "has no steady state"
        )

    def residual(t):
        return heat_balance_residual_w(t, q_in, g, coupling, t_sink)

    lo = 1e-3
    hi = t_sink
    if residual(hi) > 0.0:
        step = max(t_sink, 1.0)
        for _ in range(200):
            hi += step
            step *= 2.0
            if residual(hi) <= 0.0:
                break
        else:
            raise ValueError("no steady state found above the sink temperature")
        lo = t_sink
    else:
        hi = t_sink
        lo = 1e-3
        if residual(lo) < 0.0:
            raise ValueError("no steady state found below the sink temperature")
    for _ in range(_BISECTION_STEPS):
        mid = 0.5 * (lo + hi)
        if residual(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def interface_gradient_k(heat_w, conductance_w_per_k):
    """Return the temperature drop a heat flow leaves across a conductance."""
    q = _require_non_negative("heat_w", heat_w)
    g = _require_positive("conductance_w_per_k", conductance_w_per_k)
    return q / g


def required_conductance_w_per_k(heat_in_w, limit_temperature_k, sink_temperature_k,
                                 coupling_m2=0.0):
    """Return the conductance needed to hold a case at a temperature limit.

    A non-positive answer means the radiative path alone already holds the
    limit, and is reported as zero rather than as a negative conductance.
    """
    q_in = _require_non_negative("heat_in_w", heat_in_w)
    t_limit = _require_positive("limit_temperature_k", limit_temperature_k)
    t_sink = _require_positive("sink_temperature_k", sink_temperature_k)
    coupling = _require_non_negative("coupling_m2", coupling_m2)
    if t_limit <= t_sink:
        raise ValueError(
            "limit temperature %g K is not above the sink temperature %g K; no "
            "conductance can hold it" % (t_limit, t_sink)
        )
    radiated = STEFAN_BOLTZMANN * coupling * (t_limit ** 4 - t_sink ** 4)
    needed = (q_in - radiated) / (t_limit - t_sink)
    if needed < 0.0:
        return 0.0
    return needed


def thermoelastic_distortion_m(cte_per_k, length_m, gradient_k):
    """Return the thermo-elastic length change a gradient produces."""
    cte = _require_real("cte_per_k", cte_per_k)
    length = _require_positive("length_m", length_m)
    gradient = _require_real("gradient_k", gradient_k)
    return cte * length * gradient


def assess_thermal_sizing(spec):
    """Run the full clause 4.7.4.1 and 4.7.4.2 mechanism thermal sizing.

    spec keys: conductance_w_per_k, coupling_m2, cases (list of {name,
    dissipation_w, absorbed_flux_w, sink_temperature_k}), min_operational_k,
    max_operational_k; optional distortion_length_m, cte_per_k,
    allowable_distortion_m.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("conductance_w_per_k", "coupling_m2", "cases",
                "min_operational_k", "max_operational_k"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    g = _require_non_negative("conductance_w_per_k", spec["conductance_w_per_k"])
    coupling = _require_non_negative("coupling_m2", spec["coupling_m2"])
    t_min = _require_positive("min_operational_k", spec["min_operational_k"])
    t_max = _require_positive("max_operational_k", spec["max_operational_k"])
    if t_min >= t_max:
        raise ValueError(
            "min_operational_k %g is not below max_operational_k %g" % (t_min, t_max)
        )
    cases = spec["cases"]
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence")

    distortion_wanted = any(
        key in spec for key in ("distortion_length_m", "cte_per_k", "allowable_distortion_m")
    )
    if distortion_wanted:
        for key in ("distortion_length_m", "cte_per_k", "allowable_distortion_m"):
            if key not in spec:
                raise ValueError(
                    "a distortion check needs distortion_length_m, cte_per_k and "
                    "allowable_distortion_m together"
                )

    findings = []
    records = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError("cases[%d] must be a mapping" % index)
        for key in ("name", "dissipation_w", "absorbed_flux_w", "sink_temperature_k"):
            if key not in case:
                raise ValueError("cases[%d] missing '%s'" % (index, key))
        heat_in = (
            _require_non_negative("dissipation_w", case["dissipation_w"])
            + _require_non_negative("absorbed_flux_w", case["absorbed_flux_w"])
        )
        t_sink = _require_positive("sink_temperature_k", case["sink_temperature_k"])
        temperature = steady_state_temperature_k(heat_in, g, coupling, t_sink)
        conducted = g * (temperature - t_sink)
        gradient = interface_gradient_k(abs(conducted), g) if g > 0.0 else 0.0
        record = {
            "name": case["name"],
            "heat_in_w": heat_in,
            "sink_temperature_k": t_sink,
            "temperature_k": temperature,
            "interface_gradient_k": gradient,
        }
        if temperature > t_max and not math.isclose(
            temperature, t_max, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K
        ):
            findings.append(
                "case '%s' settles at %.2f K, above the %.2f K operational ceiling"
                % (record["name"], temperature, t_max)
            )
            if t_max > t_sink:
                record["required_conductance_w_per_k"] = required_conductance_w_per_k(
                    heat_in, t_max, t_sink, coupling
                )
        if temperature < t_min and not math.isclose(
            temperature, t_min, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K
        ):
            findings.append(
                "case '%s' settles at %.2f K, below the %.2f K operational floor"
                % (record["name"], temperature, t_min)
            )
        if distortion_wanted:
            distortion = thermoelastic_distortion_m(
                spec["cte_per_k"], spec["distortion_length_m"], gradient
            )
            record["distortion_m"] = distortion
            allowed = _require_positive(
                "allowable_distortion_m", spec["allowable_distortion_m"]
            )
            if abs(distortion) > allowed and not math.isclose(
                abs(distortion), allowed, rel_tol=1e-12, abs_tol=0.0
            ):
                findings.append(
                    "case '%s' distorts %.4g m across the interface, above the %.4g m "
                    "allowance" % (record["name"], distortion, allowed)
                )
        records.append(record)

    hottest = max(records, key=lambda r: r["temperature_k"])
    coldest = min(records, key=lambda r: r["temperature_k"])
    return {
        "conductance_w_per_k": g,
        "coupling_m2": coupling,
        "cases": records,
        "hottest_case": hottest,
        "coldest_case": coldest,
        "hot_margin_k": t_max - hottest["temperature_k"],
        "cold_margin_k": coldest["temperature_k"] - t_min,
        "compliant": not findings,
        "findings": findings,
    }
