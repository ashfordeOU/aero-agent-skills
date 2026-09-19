"""Solar absorptance by spectral integration, reference standard and calorimetry.

Anchor: ECSS-Q-ST-70-09C method clauses for solar absorptance -- weighted
integration of a measured spectral reflectance, the transfer of a relative
scan through a certified reference standard, and the steady-state calorimetric
determination. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the spectral tables: wavelengths strictly increasing, values inside
   the unit interval for reflectance-like quantities and non-negative for the
   solar spectral irradiance.
2. Rescale a relative scan into an absolute reflectance through the certified
   reflectance of the reference standard at the same wavelengths.
3. Integrate the spectral absorptance against the solar spectral irradiance
   over the span the scan actually covers, and report the fraction of the solar
   irradiance that span carries so a short scan cannot pass as a full one.
4. Determine the calorimetric absorptance from the steady-state balance of
   absorbed solar flux against radiated and parasitic losses.
5. Grade the two determinations against their combined expanded uncertainty
   with a normalised error ratio.
"""

import math

__all__ = [
    "STEFAN_BOLTZMANN",
    "MIN_SOLAR_COVERAGE",
    "SPAN_TOLERANCE",
    "DEFAULT_COVERAGE_FACTOR",
    "validate_spectral_table",
    "interpolate_at",
    "integrate_trapezoid",
    "partial_irradiance",
    "overlap_span",
    "solar_weighted_mean",
    "apply_reference_standard",
    "spectrophotometric_absorptance",
    "calorimetric_absorptance",
    "method_agreement",
    "assess_solar_absorptance",
]

# Radiation constant used by the steady-state calorimetric balance, W/(m^2 K^4).
STEFAN_BOLTZMANN = 5.670374419e-8

# A scan carrying less of the solar irradiance than this is reported as
# incomplete: the uncovered tail is absorptance nobody measured.
MIN_SOLAR_COVERAGE = 0.95

# Spans and weighted sums that should land exactly on a bound land a few ULPs
# off it; absorb that here rather than by relaxing the engineering limit.
SPAN_TOLERANCE = 1.0e-9

# Coverage factor applied to standard uncertainties when methods are compared.
DEFAULT_COVERAGE_FACTOR = 2.0


def _require_real(value, label):
    """Return value as a finite float, refusing booleans and non-numerics."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _require_positive(value, label):
    """Return a strictly positive finite float."""
    number = _require_real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def validate_spectral_table(table, name="table", bounded=True):
    """Return the table as (wavelength_nm, value) float pairs, checked.

    Wavelengths must be positive and strictly increasing. When bounded, the
    values are reflectance-like and must sit in the closed unit interval;
    otherwise they only have to be non-negative, as a spectral irradiance is.
    """
    if not isinstance(table, (list, tuple)) or len(table) < 2:
        raise ValueError("%s needs at least two (wavelength_nm, value) points" % name)
    points = []
    for index, item in enumerate(table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be a (wavelength_nm, value) pair" % (name, index))
        wavelength = _require_positive(item[0], "%s[%d] wavelength_nm" % (name, index))
        value = _require_real(item[1], "%s[%d] value" % (name, index))
        if value < 0.0:
            raise ValueError("%s[%d] value must be non-negative, got %g" % (name, index, value))
        if bounded and value > 1.0 + SPAN_TOLERANCE:
            raise ValueError(
                "%s[%d] value %g exceeds unity; a reflectance-like quantity cannot"
                % (name, index, value)
            )
        points.append((wavelength, min(value, 1.0) if bounded else value))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError("%s wavelengths must strictly increase (index %d)" % (name, index))
    return points


def interpolate_at(points, wavelength_nm, name="table"):
    """Linearly interpolate a validated point list; refuse to extrapolate."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("%s needs at least two points to interpolate" % name)
    target = _require_positive(wavelength_nm, "wavelength_nm")
    low = points[0][0]
    high = points[-1][0]
    if target < low - SPAN_TOLERANCE or target > high + SPAN_TOLERANCE:
        raise ValueError(
            "%s spans [%g, %g] nm; %g nm is outside it, extrapolation refused"
            % (name, low, high, target)
        )
    if target <= low:
        return points[0][1]
    if target >= high:
        return points[-1][1]
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        if target <= x1:
            if x1 == x0:
                return y0
            fraction = (target - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)
    return points[-1][1]


def integrate_trapezoid(points):
    """Return the trapezoidal integral of a validated point list."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("integration needs at least two points")
    total = 0.0
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        if x1 < x0:
            raise ValueError("integration abscissae must not decrease")
        total += 0.5 * (y0 + y1) * (x1 - x0)
    return total


def partial_irradiance(irradiance, low_nm, high_nm):
    """Return the solar irradiance carried between two wavelengths."""
    points = validate_spectral_table(irradiance, "irradiance", bounded=False)
    low = _require_positive(low_nm, "low_nm")
    high = _require_positive(high_nm, "high_nm")
    if high < low:
        raise ValueError("high_nm %g is below low_nm %g" % (high, low))
    if math.isclose(high, low, rel_tol=0.0, abs_tol=SPAN_TOLERANCE):
        return 0.0
    grid = [low]
    for wavelength, _ in points:
        if low < wavelength < high:
            grid.append(wavelength)
    grid.append(high)
    sampled = [(w, interpolate_at(points, w, "irradiance")) for w in grid]
    return integrate_trapezoid(sampled)


def overlap_span(first, second):
    """Return the wavelength span two validated point lists share."""
    low = max(first[0][0], second[0][0])
    high = min(first[-1][0], second[-1][0])
    if high <= low:
        raise ValueError(
            "the two spectral tables do not overlap: [%g, %g] and [%g, %g] nm"
            % (first[0][0], first[-1][0], second[0][0], second[-1][0])
        )
    return (low, high)


def solar_weighted_mean(value_table, irradiance, bounded=True):
    """Return (solar-weighted mean over the shared span, covered irradiance fraction)."""
    values = validate_spectral_table(value_table, "value-table", bounded=bounded)
    solar = validate_spectral_table(irradiance, "irradiance", bounded=False)
    low, high = overlap_span(values, solar)
    grid = sorted(
        {low, high}
        | {w for w, _ in values if low < w < high}
        | {w for w, _ in solar if low < w < high}
    )
    numerator = [
        (w, interpolate_at(solar, w, "irradiance") * interpolate_at(values, w, "value-table"))
        for w in grid
    ]
    denominator = [(w, interpolate_at(solar, w, "irradiance")) for w in grid]
    weight = integrate_trapezoid(denominator)
    if weight <= 0.0:
        raise ValueError("the solar irradiance carries no energy over the shared span")
    total = integrate_trapezoid(solar)
    if total <= 0.0:
        raise ValueError("the solar irradiance table carries no energy at all")
    return (integrate_trapezoid(numerator) / weight, weight / total)


def apply_reference_standard(ratio_table, standard_table):
    """Return the absolute reflectance of a relative scan read against a standard."""
    ratios = validate_spectral_table(ratio_table, "ratio-table", bounded=False)
    standard = validate_spectral_table(standard_table, "standard-table", bounded=True)
    absolute = []
    for wavelength, ratio in ratios:
        certified = interpolate_at(standard, wavelength, "standard-table")
        if certified <= 0.0:
            raise ValueError(
                "the reference standard has zero certified reflectance at %g nm; "
                "a relative scan cannot be transferred there" % wavelength
            )
        value = ratio * certified
        if value > 1.0 + SPAN_TOLERANCE:
            raise ValueError(
                "transferred reflectance %g at %g nm exceeds unity; the scan and "
                "the standard do not belong together" % (value, wavelength)
            )
        absolute.append((wavelength, min(value, 1.0)))
    return absolute


def spectrophotometric_absorptance(reflectance_table, irradiance,
                                   transmittance_table=None):
    """Return the solar-weighted absorptance of a measured spectral scan."""
    reflectance = validate_spectral_table(reflectance_table, "reflectance", bounded=True)
    solar = validate_spectral_table(irradiance, "irradiance", bounded=False)
    low, high = overlap_span(reflectance, solar)
    transmittance = None
    if transmittance_table is not None:
        transmittance = validate_spectral_table(
            transmittance_table, "transmittance", bounded=True
        )
        low_t, high_t = overlap_span(transmittance, reflectance)
        low = max(low, low_t)
        high = min(high, high_t)
        if high <= low:
            raise ValueError("reflectance and transmittance scans do not share a span")
    absorptance_points = []
    grid = sorted(
        {low, high}
        | {w for w, _ in reflectance if low < w < high}
        | {w for w, _ in solar if low < w < high}
        | ({w for w, _ in transmittance if low < w < high} if transmittance else set())
    )
    for wavelength in grid:
        rho = interpolate_at(reflectance, wavelength, "reflectance")
        tau = 0.0
        if transmittance is not None:
            tau = interpolate_at(transmittance, wavelength, "transmittance")
        if rho + tau > 1.0 + SPAN_TOLERANCE:
            raise ValueError(
                "reflectance plus transmittance exceeds unity at %g nm; the "
                "energy balance cannot close" % wavelength
            )
        absorptance_points.append((wavelength, max(0.0, 1.0 - rho - tau)))
    alpha, coverage = solar_weighted_mean(absorptance_points, solar, bounded=True)
    return {
        "alpha_s": alpha,
        "coverage_fraction": coverage,
        "span_nm": (low, high),
        "coverage_sufficient": coverage > MIN_SOLAR_COVERAGE
        or math.isclose(coverage, MIN_SOLAR_COVERAGE, rel_tol=0.0, abs_tol=SPAN_TOLERANCE),
    }


def calorimetric_absorptance(solar_irradiance_w_m2, illuminated_area_m2,
                             emittance, radiating_area_m2,
                             specimen_temperature_k, sink_temperature_k,
                             parasitic_loss_w=0.0):
    """Return the absorptance closing a steady-state calorimetric energy balance."""
    flux = _require_positive(solar_irradiance_w_m2, "solar_irradiance_w_m2")
    area_in = _require_positive(illuminated_area_m2, "illuminated_area_m2")
    area_out = _require_positive(radiating_area_m2, "radiating_area_m2")
    eps = _require_real(emittance, "emittance")
    if eps <= 0.0 or eps > 1.0 + SPAN_TOLERANCE:
        raise ValueError("emittance must lie in (0, 1], got %g" % eps)
    t_specimen = _require_positive(specimen_temperature_k, "specimen_temperature_k")
    t_sink = _require_positive(sink_temperature_k, "sink_temperature_k")
    parasitic = _require_real(parasitic_loss_w, "parasitic_loss_w")
    if t_specimen < t_sink:
        raise ValueError(
            "specimen temperature %g K sits below the sink %g K under illumination; "
            "the balance is inconsistent" % (t_specimen, t_sink)
        )
    # Explicit products, not a power call: pow is not correctly rounded and the
    # fourth power sits inside an equality the tests check.
    hot = t_specimen * t_specimen * t_specimen * t_specimen
    cold = t_sink * t_sink * t_sink * t_sink
    radiated = min(eps, 1.0) * STEFAN_BOLTZMANN * area_out * (hot - cold)
    absorbed = radiated + parasitic
    if absorbed < 0.0:
        raise ValueError("the balance requires a negative absorbed power; check the losses")
    return absorbed / (flux * area_in)


def method_agreement(value_a, uncertainty_a, value_b, uncertainty_b,
                     coverage_factor=DEFAULT_COVERAGE_FACTOR):
    """Compare two determinations through their combined expanded uncertainty."""
    first = _require_real(value_a, "value_a")
    second = _require_real(value_b, "value_b")
    u_first = _require_real(uncertainty_a, "uncertainty_a")
    u_second = _require_real(uncertainty_b, "uncertainty_b")
    if u_first < 0.0 or u_second < 0.0:
        raise ValueError("standard uncertainties must be non-negative")
    factor = _require_positive(coverage_factor, "coverage_factor")
    difference = first - second
    expanded = factor * math.sqrt(u_first * u_first + u_second * u_second)
    if expanded <= 0.0:
        raise ValueError(
            "both determinations claim zero uncertainty; agreement cannot be graded"
        )
    ratio = abs(difference) / expanded
    consistent = ratio < 1.0 or math.isclose(
        ratio, 1.0, rel_tol=0.0, abs_tol=SPAN_TOLERANCE
    )
    return {
        "difference": difference,
        "expanded_uncertainty": expanded,
        "normalised_error": ratio,
        "consistent": consistent,
    }


def assess_solar_absorptance(spec):
    """Run the full solar-absorptance determination for one specimen.

    spec keys: irradiance; one of reflectance or (ratio_scan and standard_scan);
    optional transmittance; optional calorimetric (a mapping of the balance
    arguments); optional spectrophotometric_uncertainty and
    calorimetric_uncertainty; optional coverage_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "irradiance" not in spec:
        raise ValueError("spec missing required key 'irradiance'")
    has_direct = "reflectance" in spec
    has_relative = "ratio_scan" in spec and "standard_scan" in spec
    if has_direct == has_relative:
        raise ValueError(
            "supply exactly one of 'reflectance' or the pair "
            "('ratio_scan', 'standard_scan')"
        )
    if has_relative:
        reflectance = apply_reference_standard(spec["ratio_scan"], spec["standard_scan"])
        route = "reference-standard-transfer"
    else:
        reflectance = spec["reflectance"]
        route = "direct-absolute-scan"
    spectro = spectrophotometric_absorptance(
        reflectance, spec["irradiance"], spec.get("transmittance")
    )
    findings = []
    if not spectro["coverage_sufficient"]:
        findings.append(
            "the scan covers %.4f of the solar irradiance, under the %.2f the "
            "weighted integration needs" % (spectro["coverage_fraction"], MIN_SOLAR_COVERAGE)
        )
    result = {
        "route": route,
        "alpha_s_spectrophotometric": spectro["alpha_s"],
        "coverage_fraction": spectro["coverage_fraction"],
        "span_nm": spectro["span_nm"],
        "alpha_s_calorimetric": None,
        "agreement": None,
        "findings": findings,
    }
    calorimetric = spec.get("calorimetric")
    if calorimetric is not None:
        if not isinstance(calorimetric, dict):
            raise ValueError("spec['calorimetric'] must be a mapping of balance arguments")
        alpha_cal = calorimetric_absorptance(**calorimetric)
        result["alpha_s_calorimetric"] = alpha_cal
        agreement = method_agreement(
            spectro["alpha_s"],
            spec.get("spectrophotometric_uncertainty", 0.01),
            alpha_cal,
            spec.get("calorimetric_uncertainty", 0.02),
            spec.get("coverage_factor", DEFAULT_COVERAGE_FACTOR),
        )
        result["agreement"] = agreement
        if not agreement["consistent"]:
            findings.append(
                "the two determinations differ by %.4f, a normalised error of "
                "%.2f against their combined expanded uncertainty"
                % (agreement["difference"], agreement["normalised_error"])
            )
    result["reportable"] = not findings
    return result
