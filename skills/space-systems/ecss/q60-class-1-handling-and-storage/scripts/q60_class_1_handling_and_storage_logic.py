"""Handling, packaging and storage of class 1 EEE parts.

Anchor: ECSS-Q-ST-60C clause 4.4 (handling, packaging and storage procedures
that keep class 1 parts free of damage and degradation). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the packaging layers a part owes from its fragility category and
   whether it needs a moisture barrier, then name the layers the delivered
   pack does not carry.
2. Test the container as received: seal state and the humidity indicator
   reading against its threshold.
3. Compare the recorded transport shock peak with the part's allowable and
   return the exposure ratio rather than a yes-or-no answer.
4. Accumulate a thermal degradation index over the storage duration, so warm
   storage for a short time and cool storage for a long time can be compared
   on one scale against a declared allowance.
5. Confirm the handling authorizations the movement owed were in place.
6. Rank the findings and return one handling disposition: fit-for-issue,
   issue-with-actions, or hold-for-reconditioning.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "BASE_PACKAGING_LAYERS",
    "FRAGILITY_LAYERS",
    "MOISTURE_BARRIER_LAYERS",
    "HANDLING_AUTHORIZATIONS",
    "REFERENCE_TEMPERATURE_C",
    "DOUBLING_INTERVAL_C",
    "SEVERITY_ORDER",
    "required_packaging_layers",
    "missing_packaging_layers",
    "container_findings",
    "shock_exposure_ratio",
    "thermal_degradation_index",
    "degradation_allowance_exceeded",
    "missing_authorizations",
    "handling_verdict",
    "assess_class_1_handling",
]

# Ratios and accumulated indices are quotients and products of measured
# values; a case sitting exactly on an allowance can land a few ULP on the
# wrong side. Absorb the representation error here, never by moving the
# allowance itself.
BOUND_TOLERANCE = 1e-9

# Layers every class 1 pack carries, whatever the part is.
BASE_PACKAGING_LAYERS = (
    "static-shielding-inner-bag",
    "part-identity-label",
    "rigid-outer-container",
)

# Additional layers owed by fragility category. A category is a statement
# about what the part cannot survive, not about how expensive it is.
FRAGILITY_LAYERS = {
    "standard": (),
    "fragile": ("cushioned-inner-tray",),
    "very-fragile": ("cushioned-inner-tray", "foam-suspension-insert",
                     "shock-recorder-in-container"),
}

# Additional layers owed when the part needs a moisture barrier.
MOISTURE_BARRIER_LAYERS = (
    "sealed-moisture-barrier-bag",
    "desiccant-charge",
    "humidity-indicator-card",
)

# Authorizations a class 1 movement owes before a part leaves its container.
HANDLING_AUTHORIZATIONS = (
    "trained-handler-certification",
    "open-work-order",
    "protected-area-release",
)

# The storage temperature the degradation index is normalised to, and the
# temperature rise that doubles the accumulation rate. Both are declared here
# so a review can restate them rather than rediscover them.
REFERENCE_TEMPERATURE_C = 22.0
DOUBLING_INTERVAL_C = 10.0

SEVERITY_ORDER = ("critical", "major", "minor")


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_flag(value, label):
    """Return a validated boolean or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def required_packaging_layers(fragility, moisture_barrier_required=False):
    """Return the sorted packaging layers a part owes."""
    key = _require_text(fragility, "fragility").casefold()
    if key not in FRAGILITY_LAYERS:
        raise ValueError(
            "fragility %r is not one of %r" % (fragility, sorted(FRAGILITY_LAYERS))
        )
    layers = set(BASE_PACKAGING_LAYERS) | set(FRAGILITY_LAYERS[key])
    if _require_flag(moisture_barrier_required, "moisture_barrier_required"):
        layers |= set(MOISTURE_BARRIER_LAYERS)
    return sorted(layers)


def missing_packaging_layers(fragility, moisture_barrier_required, layers_present):
    """Return the owed packaging layers the delivered pack does not carry."""
    if not isinstance(layers_present, (list, tuple, set, frozenset)):
        raise ValueError("layers_present must be a sequence or set")
    present = {_require_text(item, "packaging layer").casefold()
               for item in layers_present}
    owed = required_packaging_layers(fragility, moisture_barrier_required)
    return [layer for layer in owed if layer.casefold() not in present]


def container_findings(seal_intact, indicator_percent, indicator_threshold_percent):
    """Return the sorted defect codes carried by the container as received.

    An indicator reading exactly on its threshold counts as inside, with the
    boundary absorbed by the named tolerance rather than by moving the
    threshold.
    """
    reading = _require_number(indicator_percent, "indicator_percent")
    threshold = _require_number(indicator_threshold_percent,
                                "indicator_threshold_percent")
    if reading > 100.0 or threshold > 100.0:
        raise ValueError("humidity indicator values are percentages of at most 100")
    if threshold <= 0.0:
        raise ValueError("indicator_threshold_percent must be positive")
    codes = []
    if not _require_flag(seal_intact, "seal_intact"):
        codes.append("container-seal-breached")
    if reading > threshold and not math.isclose(
        reading, threshold, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    ):
        codes.append("humidity-indicator-over-threshold")
    return sorted(codes)


def shock_exposure_ratio(peak_shock_g, allowable_shock_g):
    """Return the recorded transport shock peak as a fraction of the allowable.

    One means the peak landed exactly on the allowable. The ratio is returned
    rather than a yes-or-no answer because a pack five percent over its
    allowable and one three times over are different dispositions.
    """
    peak = _require_number(peak_shock_g, "peak_shock_g")
    allowable = _require_number(allowable_shock_g, "allowable_shock_g")
    if allowable <= 0.0:
        raise ValueError("allowable_shock_g must be positive, got %g" % allowable)
    return peak / allowable


def thermal_degradation_index(storage_days, mean_temperature_c,
                              reference_temperature_c=REFERENCE_TEMPERATURE_C,
                              doubling_interval_c=DOUBLING_INTERVAL_C):
    """Return the storage duration normalised to the reference temperature.

    The index is expressed in reference-temperature days: storage at the
    reference temperature returns the duration unchanged, and every rise of
    one doubling interval doubles the rate at which the index accumulates.
    """
    days = _require_number(storage_days, "storage_days")
    mean_temperature = _require_number(mean_temperature_c, "mean_temperature_c",
                                       allow_negative=True)
    reference = _require_number(reference_temperature_c, "reference_temperature_c",
                                allow_negative=True)
    interval = _require_number(doubling_interval_c, "doubling_interval_c")
    if interval <= 0.0:
        raise ValueError("doubling_interval_c must be positive, got %g" % interval)
    if mean_temperature < -273.15:
        raise ValueError("mean_temperature_c is below absolute zero")
    exponent = (mean_temperature - reference) / interval
    return days * (2.0 ** exponent)


def degradation_allowance_exceeded(index, allowance_days):
    """Return True when the accumulated index has passed its allowance.

    An index sitting exactly on the allowance reads as inside.
    """
    value = _require_number(index, "index")
    allowance = _require_number(allowance_days, "allowance_days")
    if allowance <= 0.0:
        raise ValueError("allowance_days must be positive, got %g" % allowance)
    if math.isclose(value, allowance, rel_tol=0.0, abs_tol=BOUND_TOLERANCE):
        return False
    return value > allowance


def missing_authorizations(authorizations_held):
    """Return the handling authorizations the movement did not hold."""
    if not isinstance(authorizations_held, (list, tuple, set, frozenset)):
        raise ValueError("authorizations_held must be a sequence or set")
    held = set()
    for item in authorizations_held:
        name = _require_text(item, "authorization").casefold()
        if name not in HANDLING_AUTHORIZATIONS:
            raise ValueError(
                "unknown authorization %r; expected one of %r"
                % (item, list(HANDLING_AUTHORIZATIONS))
            )
        held.add(name)
    return [name for name in HANDLING_AUTHORIZATIONS if name not in held]


def handling_verdict(findings):
    """Return the handling disposition implied by the ranked findings."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    severities = set()
    for finding in findings:
        if not isinstance(finding, dict) or "severity" not in finding:
            raise ValueError("each finding must carry a severity")
        severity = finding["severity"]
        if severity not in SEVERITY_ORDER:
            raise ValueError("severity %r is not one of %r" % (severity, SEVERITY_ORDER))
        severities.add(severity)
    if "critical" in severities:
        return "hold-for-reconditioning"
    if severities:
        return "issue-with-actions"
    return "fit-for-issue"


def _finding(severity, topic, message):
    return {"severity": severity, "topic": topic, "message": message}


def assess_class_1_handling(pack):
    """Grade one class 1 pack and its storage history against clause 4.4.

    pack keys: fragility, moisture_barrier_required, layers_present,
    seal_intact, indicator_percent, indicator_threshold_percent,
    peak_shock_g, allowable_shock_g, storage_days, mean_temperature_c,
    degradation_allowance_days and authorizations_held.
    """
    if not isinstance(pack, dict):
        raise ValueError("pack must be a mapping")
    for key in (
        "fragility",
        "moisture_barrier_required",
        "layers_present",
        "seal_intact",
        "indicator_percent",
        "indicator_threshold_percent",
        "peak_shock_g",
        "allowable_shock_g",
        "storage_days",
        "mean_temperature_c",
        "degradation_allowance_days",
        "authorizations_held",
    ):
        if key not in pack:
            raise ValueError("pack missing required key '%s'" % key)

    missing_layers = missing_packaging_layers(
        pack["fragility"], pack["moisture_barrier_required"], pack["layers_present"]
    )
    container = container_findings(
        pack["seal_intact"], pack["indicator_percent"], pack["indicator_threshold_percent"]
    )
    ratio = shock_exposure_ratio(pack["peak_shock_g"], pack["allowable_shock_g"])
    index = thermal_degradation_index(pack["storage_days"], pack["mean_temperature_c"])
    over_allowance = degradation_allowance_exceeded(
        index, pack["degradation_allowance_days"]
    )
    gaps = missing_authorizations(pack["authorizations_held"])

    findings = []
    for layer in missing_layers:
        findings.append(
            _finding("critical", "packaging",
                     "the pack owes %s and does not carry it" % layer)
        )
    for code in container:
        severity = "critical" if code == "container-seal-breached" else "major"
        findings.append(
            _finding(severity, "container-integrity",
                     "the container as received carries %s" % code)
        )
    over_shock = ratio > 1.0 and not math.isclose(
        ratio, 1.0, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    )
    if over_shock:
        findings.append(
            _finding(
                "critical" if ratio > 2.0 else "major",
                "transport-shock",
                "the recorded peak reads %.4f of the part's allowable" % ratio,
            )
        )
    if over_allowance:
        findings.append(
            _finding("critical", "storage-degradation",
                     "the degradation index reads %.2f reference-temperature days "
                     "against an allowance of %.2f"
                     % (index, float(pack["degradation_allowance_days"])))
        )
    elif index > 0.75 * float(pack["degradation_allowance_days"]):
        findings.append(
            _finding("minor", "storage-degradation",
                     "the degradation index reads %.2f reference-temperature days "
                     "and is inside its final quarter" % index)
        )
    for name in gaps:
        findings.append(
            _finding("major", "handling-authorization",
                     "the movement was made without %s" % name)
        )

    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["topic"]))
    verdict = handling_verdict(findings)
    return {
        "required_layers": required_packaging_layers(
            pack["fragility"], pack["moisture_barrier_required"]
        ),
        "missing_layers": missing_layers,
        "container_defects": container,
        "shock_exposure_ratio": ratio,
        "thermal_degradation_index": index,
        "degradation_allowance_exceeded": over_allowance,
        "missing_authorizations": gaps,
        "findings": findings,
        "verdict": verdict,
        "fit_for_issue": verdict == "fit-for-issue",
    }
