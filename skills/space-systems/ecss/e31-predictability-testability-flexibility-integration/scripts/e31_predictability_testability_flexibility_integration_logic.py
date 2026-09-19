"""Predictability, testability, flexibility and integration of a thermal design.

Anchor: ECSS-E-ST-31C clauses 4.4.6 to 4.4.8 (design provisions for predictable
and testable performance, robustness to uncertainty, and integration and
accessibility). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Weight the heat paths by the conductance they carry and report the fraction
   of the thermal network that is characterised by measurement rather than
   assumed.
2. Combine the independent uncertainty contributors as a root sum of squares,
   add the bounding excursions of the swept design parameters, widen the
   nominal prediction and grade it against the temperature limit.
3. Measure the unspent heater authority as the flexibility the design keeps.
4. Cover the declared temperature reference points against the instrumented
   points and report the uninstrumented ones.
5. Report every item that cannot be reached after close-out or that another
   item has to come off first.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE_K",
    "validate_heat_paths",
    "weighted_characterized_fraction",
    "rss_uncertainty_k",
    "bounding_excursion_k",
    "combined_uncertainty_k",
    "widened_prediction_k",
    "grade_widened_prediction",
    "heater_authority_margin",
    "reference_point_coverage",
    "accessibility_findings",
    "assess_design_properties",
]

# A widened prediction can land exactly on a limit. Absorb the representation
# error here instead of relaxing the limit.
LIMIT_TOLERANCE_K = 1e-9


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


def validate_heat_paths(paths):
    """Return the validated heat-path list of the thermal network.

    Each path is a mapping with a name, a positive conductance in W/K and an
    explicit boolean saying whether that conductance was measured.
    """
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("paths must be a non-empty sequence of heat paths")
    out = []
    seen = set()
    for index, path in enumerate(paths):
        if not isinstance(path, dict):
            raise ValueError("paths[%d] must be a mapping" % index)
        for key in ("name", "conductance_w_per_k", "characterized"):
            if key not in path:
                raise ValueError("paths[%d] missing required key '%s'" % (index, key))
        name = _require_name(path["name"], "paths[%d]['name']" % index)
        if name in seen:
            raise ValueError("duplicate heat path name '%s'" % name)
        seen.add(name)
        conductance = _require_positive(
            path["conductance_w_per_k"], "paths[%d]['conductance_w_per_k']" % index
        )
        characterized = path["characterized"]
        if not isinstance(characterized, bool):
            raise ValueError("paths[%d]['characterized'] must be a boolean" % index)
        out.append({
            "name": name,
            "conductance_w_per_k": conductance,
            "characterized": characterized,
        })
    return out


def weighted_characterized_fraction(paths):
    """Return the conductance-weighted fraction of the network that is measured."""
    validated = validate_heat_paths(paths)
    total = sum(p["conductance_w_per_k"] for p in validated)
    measured = sum(
        p["conductance_w_per_k"] for p in validated if p["characterized"]
    )
    return measured / total


def rss_uncertainty_k(contributors):
    """Return the root-sum-square combination of independent contributors.

    Each contributor is either a non-negative number or a mapping carrying
    'sigma_k'.
    """
    if not isinstance(contributors, (list, tuple)):
        raise ValueError("contributors must be a sequence")
    total = 0.0
    for index, item in enumerate(contributors):
        if isinstance(item, dict):
            if "sigma_k" not in item:
                raise ValueError("contributors[%d] missing 'sigma_k'" % index)
            sigma = _require_non_negative(item["sigma_k"], "contributors[%d]" % index)
        else:
            sigma = _require_non_negative(item, "contributors[%d]" % index)
        total += sigma * sigma
    return math.sqrt(total)


def bounding_excursion_k(sensitivities):
    """Return the additive bounding excursion of the swept design parameters.

    Each entry carries 'sensitivity_k_per_unit' and a non-negative
    'parameter_range'; the excursion of one parameter is the sensitivity
    magnitude times half its range, and the excursions add.
    """
    if not isinstance(sensitivities, (list, tuple)):
        raise ValueError("sensitivities must be a sequence")
    total = 0.0
    for index, item in enumerate(sensitivities):
        if not isinstance(item, dict):
            raise ValueError("sensitivities[%d] must be a mapping" % index)
        for key in ("sensitivity_k_per_unit", "parameter_range"):
            if key not in item:
                raise ValueError("sensitivities[%d] missing '%s'" % (index, key))
        sensitivity = _require_real(
            item["sensitivity_k_per_unit"], "sensitivities[%d] sensitivity" % index
        )
        span = _require_non_negative(
            item["parameter_range"], "sensitivities[%d] parameter_range" % index
        )
        total += abs(sensitivity) * span / 2.0
    return total


def combined_uncertainty_k(contributors, sensitivities=None):
    """Return the total uncertainty: random in quadrature plus bounding sweeps."""
    random_part = rss_uncertainty_k(contributors)
    swept_part = 0.0 if sensitivities is None else bounding_excursion_k(sensitivities)
    return random_part + swept_part


def widened_prediction_k(nominal_k, uncertainty_k, sense="hot"):
    """Return the prediction widened by the uncertainty towards the graded side."""
    nominal = _require_real(nominal_k, "nominal_k")
    if nominal <= 0.0:
        raise ValueError("nominal_k must be an absolute temperature above zero")
    uncertainty = _require_non_negative(uncertainty_k, "uncertainty_k")
    if sense == "hot":
        return nominal + uncertainty
    if sense == "cold":
        widened = nominal - uncertainty
        if widened <= 0.0:
            raise ValueError(
                "cold-side widening drives the prediction to %g K, which is not "
                "an absolute temperature" % widened
            )
        return widened
    raise ValueError("sense must be 'hot' or 'cold', got %r" % (sense,))


def grade_widened_prediction(nominal_k, uncertainty_k, limit_k, sense="hot"):
    """Grade the uncertainty-widened prediction against its temperature limit."""
    widened = widened_prediction_k(nominal_k, uncertainty_k, sense)
    limit = _require_real(limit_k, "limit_k")
    if limit <= 0.0:
        raise ValueError("limit_k must be an absolute temperature above zero")
    if sense == "hot":
        exceedance = widened - limit
    else:
        exceedance = limit - widened
    acceptable = exceedance <= LIMIT_TOLERANCE_K
    return {
        "sense": sense,
        "widened_k": widened,
        "limit_k": limit,
        "exceedance_k": exceedance,
        "acceptable": acceptable,
        "finding": None if acceptable
        else "the %s prediction widened to %.3f K against a %.3f K limit"
             % (sense, widened, limit),
    }


def heater_authority_margin(installed_w, required_w):
    """Return the unspent heater authority as a fraction of what is required."""
    installed = _require_non_negative(installed_w, "installed_w")
    required = _require_positive(required_w, "required_w")
    return (installed - required) / required


def reference_point_coverage(reference_points, instrumented_points):
    """Return the test coverage of the declared temperature reference points."""
    if not isinstance(reference_points, (list, tuple)) or not reference_points:
        raise ValueError("reference_points must be a non-empty sequence")
    if not isinstance(instrumented_points, (list, tuple)):
        raise ValueError("instrumented_points must be a sequence")
    declared = []
    for index, name in enumerate(reference_points):
        declared.append(_require_name(name, "reference_points[%d]" % index))
    if len(set(declared)) != len(declared):
        raise ValueError("reference_points contains a duplicate name")
    measured = set()
    for index, name in enumerate(instrumented_points):
        measured.add(_require_name(name, "instrumented_points[%d]" % index))
    uncovered = [name for name in declared if name not in measured]
    stray = sorted(name for name in measured if name not in set(declared))
    return {
        "declared": declared,
        "uncovered": uncovered,
        "stray_sensors": stray,
        "coverage_fraction": (len(declared) - len(uncovered)) / len(declared),
        "findings": [
            "temperature reference point %s carries no sensor" % name
            for name in uncovered
        ],
    }


def accessibility_findings(items):
    """Return the integration and accessibility findings of the hardware list.

    Each item carries a name, 'access_after_closeout' (whether the item still
    needs to be reached once the blankets are on) and 'blocked_by' (the item,
    if any, that has to be removed first).
    """
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a sequence")
    findings = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("items[%d] must be a mapping" % index)
        if "name" not in item:
            raise ValueError("items[%d] missing 'name'" % index)
        name = _require_name(item["name"], "items[%d]['name']" % index)
        needs_access = item.get("access_after_closeout", False)
        if not isinstance(needs_access, bool):
            raise ValueError("items[%d]['access_after_closeout'] must be a boolean" % index)
        blocked_by = item.get("blocked_by")
        if blocked_by is not None and not isinstance(blocked_by, str):
            raise ValueError("items[%d]['blocked_by'] must be a string or absent" % index)
        if needs_access:
            findings.append(
                "item %s still needs access after blanket close-out" % name
            )
        if isinstance(blocked_by, str) and blocked_by.strip():
            findings.append(
                "item %s cannot be removed before %s comes off" % (name, blocked_by)
            )
    return findings


def assess_design_properties(spec):
    """Run the full clauses 4.4.6 to 4.4.8 design-property assessment.

    spec keys: heat_paths, predictability_threshold, uncertainty_contributors,
    nominal_k, limit_k, heater_installed_w, heater_required_w,
    flexibility_threshold, reference_points, instrumented_points; optional
    parameter_sensitivities, sense, accessibility_items.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "heat_paths", "predictability_threshold", "uncertainty_contributors",
        "nominal_k", "limit_k", "heater_installed_w", "heater_required_w",
        "flexibility_threshold", "reference_points", "instrumented_points",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    predictability_threshold = _require_non_negative(
        spec["predictability_threshold"], "predictability_threshold"
    )
    if predictability_threshold > 1.0:
        raise ValueError("predictability_threshold must lie in [0, 1]")
    flexibility_threshold = _require_real(
        spec["flexibility_threshold"], "flexibility_threshold"
    )
    characterized = weighted_characterized_fraction(spec["heat_paths"])
    uncertainty = combined_uncertainty_k(
        spec["uncertainty_contributors"], spec.get("parameter_sensitivities")
    )
    grading = grade_widened_prediction(
        spec["nominal_k"], uncertainty, spec["limit_k"], spec.get("sense", "hot")
    )
    margin = heater_authority_margin(spec["heater_installed_w"], spec["heater_required_w"])
    coverage = reference_point_coverage(
        spec["reference_points"], spec["instrumented_points"]
    )
    access = accessibility_findings(spec.get("accessibility_items", []))
    findings = []
    predictable = characterized >= predictability_threshold - LIMIT_TOLERANCE_K
    if not predictable:
        findings.append(
            "only %.3f of the network conductance is characterised against a "
            "%.3f threshold" % (characterized, predictability_threshold)
        )
    if grading["finding"]:
        findings.append(grading["finding"])
    flexible = margin >= flexibility_threshold - LIMIT_TOLERANCE_K
    if not flexible:
        findings.append(
            "heater authority margin %.3f falls short of the %.3f threshold"
            % (margin, flexibility_threshold)
        )
    findings.extend(coverage["findings"])
    findings.extend(access)
    return {
        "characterized_fraction": characterized,
        "predictable": predictable,
        "combined_uncertainty_k": uncertainty,
        "grading": grading,
        "heater_authority_margin": margin,
        "flexible": flexible,
        "coverage": coverage,
        "testable": not coverage["findings"],
        "accessibility": access,
        "integrable": not access,
        "findings": findings,
        "compliant": not findings,
    }
