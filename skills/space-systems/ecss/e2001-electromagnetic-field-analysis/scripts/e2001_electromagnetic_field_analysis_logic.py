#!/usr/bin/env python3
"""Internal electromagnetic-field analysis preceding a multipactor threshold.

Anchor: ECSS-E-ST-20-01C clause 5.2 (analysis of the internal fields of a
radio-frequency item, which has to be in place before a worst-case multipactor
threshold can be established). Paraphrased into an implementable procedure; no
verbatim standard text is reproduced.

Stdlib only, offline, deterministic.

Procedure implemented here:

1. categorize the field model against the recognized solver list and check the
   solver is able to represent what the item contains (a dielectric-loaded
   region needs a solver that carries dielectric material);
2. check mesh or mode convergence: enough refinement levels for that solver,
   and a relative change between the two finest levels inside the convergence
   tolerance;
3. check the frequency sampling: enough samples across the operating band to
   resolve the narrowest loaded resonance the item supports;
4. scale every region's reference peak field to the operating power by the
   square-root-power law, since the field goes as the square root of power;
5. convert the peak field into the equivalent parallel-plate gap voltage
   through the region's field-uniformity factor, and record the
   frequency-gap-product the region sits at;
6. select the governing region and every region within the closeness band of
   it, so a second nearly-equal region is not dropped;
7. permit threshold establishment only when the model is converged, sampled
   and free of findings.

This leaf stops at the field description. It does not compute a multipactor
threshold or a margin; it decides whether the field analysis is sound enough
for a threshold to be established from it at all.
"""

import math

# A quantity landing exactly on a limit is the design point: the comparison
# absorbs floating-point representation error instead of moving the limit.
FIELD_REL_TOL = 1e-9
FIELD_ABS_TOL = 1e-12

# Recognized field solvers. min_refinement_levels is the smallest number of
# successively refined runs that can demonstrate convergence for that solver;
# carries_dielectric says whether the formulation represents dielectric
# material rather than metal boundaries alone.
SOLVER_TYPES = {
    "mode-matching": {"min_refinement_levels": 2, "carries_dielectric": False},
    "finite-element-frequency-domain": {
        "min_refinement_levels": 3,
        "carries_dielectric": True,
    },
    "finite-difference-time-domain": {
        "min_refinement_levels": 3,
        "carries_dielectric": True,
    },
    "method-of-moments": {"min_refinement_levels": 2, "carries_dielectric": False},
    "boundary-integral": {"min_refinement_levels": 2, "carries_dielectric": False},
}

# Largest accepted relative change of the peak field between the two finest
# refinement levels, in percent.
CONVERGENCE_TOLERANCE_PCT = 2.0

# Frequency samples demanded per loaded-resonance width, and the absolute
# floor on samples across the band.
POINTS_PER_RESONANCE_WIDTH = 5
MIN_BAND_SAMPLES = 11

# A region whose gap voltage sits within this band of the governing region
# also governs, and is carried forward with it.
GOVERNING_CLOSENESS_DB = 0.5


def _as_float(value, label):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    """Return value as a strictly positive finite float or raise ValueError."""
    out = _as_float(value, label)
    if out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def _at_most(value, limit):
    """True when value stays within limit, absorbing representation error."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=FIELD_REL_TOL, abs_tol=FIELD_ABS_TOL)


def ceil_with_tolerance(value):
    """Ceiling that first absorbs floating-point representation error.

    A sample count computed from a product of decimals can land a few units in
    the last place above a whole number; a bare ceiling would then demand one
    extra sample that the physics never asked for.
    """
    out = _as_float(value, "value")
    nearest = round(out)
    if math.isclose(out, nearest, rel_tol=FIELD_REL_TOL, abs_tol=FIELD_ABS_TOL):
        return int(nearest)
    return int(math.ceil(out))


def resolve_solver(solver):
    """Resolve a solver name to its recognized specification."""
    if not isinstance(solver, str):
        raise ValueError("solver must be a string, got %r" % (solver,))
    key = solver.strip().lower()
    if key not in SOLVER_TYPES:
        raise ValueError(
            "unrecognized solver %r; known: %s"
            % (solver, ", ".join(sorted(SOLVER_TYPES)))
        )
    spec = dict(SOLVER_TYPES[key])
    spec["solver"] = key
    return spec


def scale_field_to_power(reference_field_v_per_m, reference_power_w, operating_power_w):
    """Scale a peak field from its reference power to the operating power.

    The field of a linear passive structure goes as the square root of the
    delivered power, so the ratio of the fields is the square root of the
    ratio of the powers.
    """
    field = _positive(reference_field_v_per_m, "reference_field_v_per_m")
    p_ref = _positive(reference_power_w, "reference_power_w")
    p_op = _positive(operating_power_w, "operating_power_w")
    return field * math.sqrt(p_op / p_ref)


def equivalent_gap_voltage(peak_field_v_per_m, gap_mm, uniformity_factor):
    """Equivalent parallel-plate voltage across a gap, in volt.

    The line integral of the field across the gap never exceeds the peak field
    times the separation; the uniformity factor is the ratio of the two and is
    unity for a perfectly uniform gap.
    """
    field = _positive(peak_field_v_per_m, "peak_field_v_per_m")
    gap = _positive(gap_mm, "gap_mm")
    factor = _as_float(uniformity_factor, "uniformity_factor")
    if factor <= 0.0 or factor > 1.0:
        raise ValueError(
            "uniformity_factor must lie in (0, 1], got %r" % (uniformity_factor,)
        )
    return field * (gap / 1000.0) * factor


def frequency_gap_product(frequency_ghz, gap_mm):
    """Frequency-gap product of a region, in gigahertz-millimetre."""
    frequency = _positive(frequency_ghz, "frequency_ghz")
    gap = _positive(gap_mm, "gap_mm")
    return frequency * gap


def mesh_convergence(peak_fields_v_per_m, min_levels):
    """Relative change of the peak field between the two finest levels."""
    if isinstance(peak_fields_v_per_m, (str, bytes)) or not isinstance(
        peak_fields_v_per_m, (list, tuple)
    ):
        raise ValueError("peak_fields_v_per_m must be a list or tuple")
    if not isinstance(min_levels, int) or isinstance(min_levels, bool):
        raise ValueError("min_levels must be an integer, got %r" % (min_levels,))
    if len(peak_fields_v_per_m) < 2:
        raise ValueError(
            "convergence needs at least two refinement levels, got %d"
            % len(peak_fields_v_per_m)
        )
    values = [
        _positive(v, "peak_fields_v_per_m[%d]" % i)
        for i, v in enumerate(peak_fields_v_per_m)
    ]
    finest = values[-1]
    previous = values[-2]
    change_pct = abs(finest - previous) / finest * 100.0
    findings = []
    if len(values) < min_levels:
        findings.append(
            "convergence shown over %d refinement levels; this solver needs %d"
            % (len(values), min_levels)
        )
    converged = _at_most(change_pct, CONVERGENCE_TOLERANCE_PCT)
    if not converged:
        findings.append(
            "peak field still moving %.4f percent between the two finest levels, "
            "above the %.2f percent convergence tolerance"
            % (change_pct, CONVERGENCE_TOLERANCE_PCT)
        )
    return {
        "levels": len(values),
        "finest_peak_field_v_per_m": finest,
        "relative_change_pct": change_pct,
        "converged": converged and not findings,
        "findings": findings,
    }


def required_band_samples(band_start_ghz, band_stop_ghz, loaded_q):
    """Frequency samples needed to resolve the narrowest loaded resonance."""
    start = _positive(band_start_ghz, "band_start_ghz")
    stop = _positive(band_stop_ghz, "band_stop_ghz")
    if stop <= start:
        raise ValueError(
            "band_stop_ghz must exceed band_start_ghz, got %r and %r"
            % (band_stop_ghz, band_start_ghz)
        )
    quality = _positive(loaded_q, "loaded_q")
    bandwidth = stop - start
    centre = (start + stop) / 2.0
    resonance_widths = bandwidth * quality / centre
    needed = ceil_with_tolerance(POINTS_PER_RESONANCE_WIDTH * resonance_widths)
    return max(needed, MIN_BAND_SAMPLES)


def frequency_sampling_findings(band_start_ghz, band_stop_ghz, sample_count, loaded_q):
    """Report whether the frequency sampling resolves the band."""
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise ValueError("sample_count must be an integer, got %r" % (sample_count,))
    if sample_count < 2:
        raise ValueError("sample_count must be at least 2, got %d" % sample_count)
    needed = required_band_samples(band_start_ghz, band_stop_ghz, loaded_q)
    findings = []
    if sample_count < needed:
        findings.append(
            "band sampled at %d points; %d are needed to resolve the loaded "
            "resonances" % (sample_count, needed)
        )
    return {
        "required_samples": needed,
        "declared_samples": sample_count,
        "adequate": not findings,
        "findings": findings,
    }


def assess_region(region, reference_power_w, operating_power_w, solver_spec):
    """Assess one field region and produce its equivalent gap voltage."""
    if not isinstance(region, dict):
        raise ValueError("region must be a mapping, got %r" % (region,))
    region_id = region.get("region_id")
    if not isinstance(region_id, str) or not region_id.strip():
        raise ValueError(
            "region 'region_id' must be a non-empty string, got %r" % (region_id,)
        )
    gap_mm = _positive(region.get("gap_mm"), "gap_mm")
    frequency_ghz = _positive(region.get("frequency_ghz"), "frequency_ghz")
    peak_field = scale_field_to_power(
        region.get("reference_peak_field_v_per_m"),
        reference_power_w,
        operating_power_w,
    )
    uniformity = region.get("uniformity_factor", 1.0)
    voltage = equivalent_gap_voltage(peak_field, gap_mm, uniformity)
    dielectric = region.get("dielectric_loaded", False)
    if not isinstance(dielectric, bool):
        raise ValueError(
            "region 'dielectric_loaded' must be a boolean, got %r" % (dielectric,)
        )
    findings = []
    if dielectric and not solver_spec["carries_dielectric"]:
        findings.append(
            "region %r is dielectric-loaded but solver %r carries metal "
            "boundaries only" % (region_id.strip(), solver_spec["solver"])
        )
    return {
        "region_id": region_id.strip(),
        "gap_mm": gap_mm,
        "frequency_ghz": frequency_ghz,
        "peak_field_v_per_m": peak_field,
        "equivalent_gap_voltage_v": voltage,
        "frequency_gap_product_ghz_mm": frequency_gap_product(frequency_ghz, gap_mm),
        "dielectric_loaded": dielectric,
        "findings": findings,
    }


def select_governing_regions(assessed_regions):
    """Return the governing region plus every region within its closeness band."""
    if isinstance(assessed_regions, (str, bytes)) or not isinstance(
        assessed_regions, (list, tuple)
    ):
        raise ValueError("assessed_regions must be a list or tuple")
    if not assessed_regions:
        raise ValueError("assessed_regions must not be empty")
    highest = max(r["equivalent_gap_voltage_v"] for r in assessed_regions)
    governing = []
    for region in assessed_regions:
        separation_db = 20.0 * math.log10(highest / region["equivalent_gap_voltage_v"])
        if _at_most(separation_db, GOVERNING_CLOSENESS_DB):
            governing.append(region["region_id"])
    return {
        "highest_gap_voltage_v": highest,
        "governing_region_ids": governing,
        "co_governing": len(governing) > 1,
    }


def assess_field_analysis(model):
    """Decide whether a field model can support a worst-case threshold."""
    if not isinstance(model, dict):
        raise ValueError("model must be a mapping, got %r" % (model,))
    model_id = model.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError(
            "model 'model_id' must be a non-empty string, got %r" % (model_id,)
        )
    solver_spec = resolve_solver(model.get("solver"))
    reference_power_w = _positive(model.get("reference_power_w"), "reference_power_w")
    operating_power_w = _positive(model.get("operating_power_w"), "operating_power_w")
    convergence = mesh_convergence(
        model.get("mesh_peak_fields_v_per_m"), solver_spec["min_refinement_levels"]
    )
    sampling = frequency_sampling_findings(
        model.get("band_start_ghz"),
        model.get("band_stop_ghz"),
        model.get("frequency_samples"),
        model.get("loaded_q"),
    )
    regions = model.get("regions")
    if isinstance(regions, (str, bytes)) or not isinstance(regions, (list, tuple)):
        raise ValueError("model 'regions' must be a list or tuple")
    if not regions:
        raise ValueError("model 'regions' must not be empty")
    assessed = []
    seen = set()
    for region in regions:
        result = assess_region(
            region, reference_power_w, operating_power_w, solver_spec
        )
        if result["region_id"] in seen:
            raise ValueError("duplicate region_id %r" % result["region_id"])
        seen.add(result["region_id"])
        assessed.append(result)
    governing = select_governing_regions(assessed)
    findings = list(convergence["findings"]) + list(sampling["findings"])
    for result in assessed:
        for finding in result["findings"]:
            findings.append(finding)
    return {
        "model_id": model_id.strip(),
        "solver": solver_spec["solver"],
        "region_count": len(assessed),
        "regions": assessed,
        "convergence": convergence,
        "sampling": sampling,
        "governing_region_ids": governing["governing_region_ids"],
        "co_governing": governing["co_governing"],
        "highest_gap_voltage_v": governing["highest_gap_voltage_v"],
        "findings": findings,
        "threshold_establishment_permitted": not findings,
    }
