"""High-temperature thermal protection verification by agreed test and analysis.

Anchor: ECSS-E-ST-31C clause 4.5.2.3 (verification of thermal protection items
by the thermal tests and the thermal analyses agreed for them). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the qualification temperature of a protection item from its
   predicted peak surface temperature plus the agreed qualification margin,
   and grade the material capability against that, never against the
   prediction.
2. Size the protection thickness from the recession allowance (rate, exposure
   duration and the agreed scatter factor), the insulation thickness the
   bondline limit demands, and the manufacturing tolerance, then compare it
   with the as-built thickness.
3. Grade the bondline: the predicted bondline temperature is compared with the
   adhesive or substrate limit, which is a different and usually much lower
   limit than the surface capability.
4. Grade the correlation between the thermal test and the analysis that
   claims to represent it, as an absolute temperature error against the
   agreed correlation tolerance.
5. Check method coverage: an item whose agreed plan calls for a thermal test
   is not verified by analysis alone, and a correlated analysis needs a test
   to correlate against.
"""

import math

__all__ = [
    "TEMPERATURE_TOLERANCE_K",
    "THICKNESS_TOLERANCE_MM",
    "METHODS",
    "validate_temperature_k",
    "validate_non_negative",
    "validate_method_set",
    "qualification_temperature_k",
    "capability_margin_k",
    "capability_adequate",
    "recession_allowance_mm",
    "required_thickness_mm",
    "thickness_margin_mm",
    "bondline_margin_k",
    "correlation_error_k",
    "correlation_acceptable",
    "method_coverage_findings",
    "evaluate_tps_item",
    "assess_tps_verification",
]

# Temperature margins are differences of measured and predicted floats, and
# thicknesses are sums of products. A quantity that should sit exactly on its
# limit can land a few ULPs either side, so absorb the representation error
# here instead of relaxing the engineering limit.
TEMPERATURE_TOLERANCE_K = 1e-9
THICKNESS_TOLERANCE_MM = 1e-9

# Verification methods an agreed plan can call for.
METHODS = ("thermal-test", "thermal-analysis", "correlated-analysis")


def validate_temperature_k(value, label):
    """Return a validated absolute temperature in kelvin."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    temperature = float(value)
    if not math.isfinite(temperature):
        raise ValueError("%s must be finite" % label)
    if temperature <= 0.0:
        raise ValueError("%s must be above absolute zero, got %r" % (label, value))
    return temperature


def validate_non_negative(value, label):
    """Return a validated non-negative real quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def validate_method_set(methods, label="methods"):
    """Return a validated, de-duplicated set of verification method names."""
    if not isinstance(methods, (list, tuple, set, frozenset)) or not methods:
        raise ValueError("%s must be a non-empty collection of method names" % label)
    normalised = set()
    for item in methods:
        if not isinstance(item, str):
            raise ValueError("%s entries must be strings" % label)
        name = item.strip().lower()
        if name not in METHODS:
            raise ValueError("unknown verification method %r; expected one of %s"
                             % (item, METHODS))
        normalised.add(name)
    return normalised


def qualification_temperature_k(predicted_peak_k, qualification_margin_k):
    """Return the temperature the item is qualified to, prediction plus agreed margin."""
    predicted = validate_temperature_k(predicted_peak_k, "predicted_peak_k")
    margin = validate_non_negative(qualification_margin_k, "qualification_margin_k")
    return predicted + margin


def capability_margin_k(capability_k, qualification_k):
    """Return the material capability margin over the qualification temperature."""
    capability = validate_temperature_k(capability_k, "capability_k")
    qualification = validate_temperature_k(qualification_k, "qualification_k")
    return capability - qualification


def capability_adequate(margin_k):
    """Return True when a capability margin is non-negative within tolerance."""
    if not isinstance(margin_k, (int, float)) or isinstance(margin_k, bool):
        raise ValueError("margin_k must be a real number")
    value = float(margin_k)
    if not math.isfinite(value):
        raise ValueError("margin_k must be finite")
    if value > 0.0:
        return True
    return math.isclose(value, 0.0, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K)


def recession_allowance_mm(recession_rate_mm_per_s, exposure_s, scatter_factor):
    """Return the recession thickness to be sacrificed over the agreed exposure."""
    rate = validate_non_negative(recession_rate_mm_per_s, "recession_rate_mm_per_s")
    exposure = validate_non_negative(exposure_s, "exposure_s")
    scatter = validate_non_negative(scatter_factor, "scatter_factor")
    if scatter < 1.0:
        raise ValueError("scatter_factor must be at least 1.0, got %r" % (scatter_factor,))
    return rate * exposure * scatter


def required_thickness_mm(recession_mm, insulation_mm, manufacturing_tolerance_mm):
    """Return the protection thickness required: recession plus insulation plus tolerance."""
    recession = validate_non_negative(recession_mm, "recession_mm")
    insulation = validate_non_negative(insulation_mm, "insulation_mm")
    tolerance = validate_non_negative(manufacturing_tolerance_mm, "manufacturing_tolerance_mm")
    if insulation <= 0.0:
        raise ValueError("insulation_mm must be positive; a bondline needs insulating thickness")
    return recession + insulation + tolerance


def thickness_margin_mm(as_built_mm, required_mm):
    """Return the as-built thickness margin over the required thickness."""
    as_built = validate_non_negative(as_built_mm, "as_built_mm")
    required = validate_non_negative(required_mm, "required_mm")
    if required <= 0.0:
        raise ValueError("required_mm must be positive")
    return as_built - required


def bondline_margin_k(bondline_limit_k, bondline_predicted_k):
    """Return the bondline margin: limit minus predicted bondline temperature."""
    limit = validate_temperature_k(bondline_limit_k, "bondline_limit_k")
    predicted = validate_temperature_k(bondline_predicted_k, "bondline_predicted_k")
    return limit - predicted


def correlation_error_k(predicted_k, measured_k):
    """Return the absolute model-to-test correlation error in kelvin."""
    predicted = validate_temperature_k(predicted_k, "predicted_k")
    measured = validate_temperature_k(measured_k, "measured_k")
    return abs(predicted - measured)


def correlation_acceptable(error_k, tolerance_k):
    """Return True when a correlation error sits inside the agreed tolerance."""
    error = validate_non_negative(error_k, "error_k")
    tolerance = validate_non_negative(tolerance_k, "tolerance_k")
    if tolerance <= 0.0:
        raise ValueError("tolerance_k must be positive; a zero tolerance grades nothing")
    if error < tolerance:
        return True
    return math.isclose(error, tolerance, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K)


def method_coverage_findings(agreed, performed, identifier):
    """Return the findings raised by the methods performed against those agreed."""
    agreed_set = validate_method_set(agreed, "agreed methods")
    performed_set = validate_method_set(performed, "performed methods")
    findings = []
    for method in sorted(agreed_set - performed_set):
        findings.append("%s: agreed %s was not performed" % (identifier, method))
    if "correlated-analysis" in performed_set and "thermal-test" not in performed_set:
        findings.append(
            "%s: a correlated analysis is claimed with no thermal test to correlate against"
            % identifier
        )
    return findings


def evaluate_tps_item(item):
    """Evaluate one thermal protection item against clause 4.5.2.3."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    required_keys = (
        "id", "predicted_peak_k", "qualification_margin_k", "capability_k",
        "bondline_limit_k", "bondline_predicted_k", "recession_rate_mm_per_s",
        "exposure_s", "scatter_factor", "insulation_mm", "manufacturing_tolerance_mm",
        "as_built_mm", "agreed_methods", "performed_methods",
    )
    for key in required_keys:
        if key not in item:
            raise ValueError("item missing required key '%s'" % key)
    identifier = item["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("item id must be a non-empty string")
    identifier = identifier.strip()

    qualification = qualification_temperature_k(
        item["predicted_peak_k"], item["qualification_margin_k"]
    )
    capability = capability_margin_k(item["capability_k"], qualification)
    capability_ok = capability_adequate(capability)

    recession = recession_allowance_mm(
        item["recession_rate_mm_per_s"], item["exposure_s"], item["scatter_factor"]
    )
    required = required_thickness_mm(
        recession, item["insulation_mm"], item["manufacturing_tolerance_mm"]
    )
    thickness = thickness_margin_mm(item["as_built_mm"], required)
    thickness_ok = thickness > 0.0 or math.isclose(
        thickness, 0.0, rel_tol=0.0, abs_tol=THICKNESS_TOLERANCE_MM
    )

    bondline = bondline_margin_k(item["bondline_limit_k"], item["bondline_predicted_k"])
    bondline_ok = bondline > 0.0 or math.isclose(
        bondline, 0.0, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K
    )

    findings = method_coverage_findings(
        item["agreed_methods"], item["performed_methods"], identifier
    )
    if not capability_ok:
        findings.append(
            "%s: material capability %.2f K is below the qualification temperature %.2f K"
            % (identifier, float(item["capability_k"]), qualification)
        )
    if not thickness_ok:
        findings.append(
            "%s: as-built thickness is %.4f mm short of the required %.4f mm"
            % (identifier, -thickness, required)
        )
    if not bondline_ok:
        findings.append(
            "%s: predicted bondline temperature exceeds its limit by %.2f K"
            % (identifier, -bondline)
        )

    correlation = None
    correlation_ok = None
    if "measured_peak_k" in item and item["measured_peak_k"] is not None:
        if "correlation_tolerance_k" not in item:
            raise ValueError("a measured peak needs a 'correlation_tolerance_k'")
        correlation = correlation_error_k(item["predicted_peak_k"], item["measured_peak_k"])
        correlation_ok = correlation_acceptable(correlation, item["correlation_tolerance_k"])
        if not correlation_ok:
            findings.append(
                "%s: model-to-test correlation error %.2f K exceeds the agreed %.2f K"
                % (identifier, correlation, float(item["correlation_tolerance_k"]))
            )
    elif "thermal-test" in validate_method_set(item["performed_methods"], "performed methods"):
        findings.append(
            "%s: a thermal test is recorded with no measured peak to correlate the model against"
            % identifier
        )

    return {
        "id": identifier,
        "qualification_temperature_k": qualification,
        "capability_margin_k": capability,
        "capability_adequate": capability_ok,
        "recession_allowance_mm": recession,
        "required_thickness_mm": required,
        "thickness_margin_mm": thickness,
        "thickness_adequate": thickness_ok,
        "bondline_margin_k": bondline,
        "bondline_adequate": bondline_ok,
        "correlation_error_k": correlation,
        "correlation_acceptable": correlation_ok,
        "verified": not findings,
        "findings": findings,
    }


def assess_tps_verification(spec):
    """Run the full clause 4.5.2.3 thermal protection verification assessment.

    spec keys: items (sequence of protection item mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "items" not in spec:
        raise ValueError("spec missing required key 'items'")
    items = spec["items"]
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("spec['items'] must be a non-empty sequence")
    records = []
    seen = set()
    for item in items:
        record = evaluate_tps_item(item)
        if record["id"] in seen:
            raise ValueError("duplicate protection item id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    findings = []
    for record in records:
        findings.extend(record["findings"])
    verified = [record["id"] for record in records if record["verified"]]
    driving = min(
        records, key=lambda r: (r["capability_margin_k"], r["id"])
    )["id"]
    return {
        "items": records,
        "verified_items": verified,
        "verified_fraction": len(verified) / float(len(records)),
        "driving_item": driving,
        "verified": not findings,
        "findings": findings,
    }
