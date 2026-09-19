"""Content check for the mission radiation environment specification.

Anchor: ECSS-Q-ST-60-15C Annex A (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Establish what the deliverable has to contain. The environment
   specification is the document every later radiation analysis reads
   from, so it has to define the mission and orbit, each particle
   population the mission meets, and the derived products -- the
   ionising dose against shielding, the displacement damage fluence
   and the linear energy transfer spectra -- that the analyses
   actually consume.
2. Insist each environment is attributed. An environment given as a
   number is unusable later; it has to name the model it came from and
   the version of that model, and cite the standard the model was
   taken from, because a model is revised and an analysis has to be
   reproducible against the revision that was used.
3. Ask each model for what its own kind requires. A statistical model
   -- a solar particle event fluence is the usual one -- is meaningless
   without the confidence level it was evaluated at. A trapped or
   cosmic ray model is evaluated for a solar activity condition
   instead, and a confidence level attached to one of those is a
   category error rather than extra rigour.
4. Cross-check the derived products against the design. A dose-depth
   curve whose thinnest tabulated shielding is thicker than the
   thinnest shielding in the equipment cannot be read at the parts
   that need it most.
5. Report what is missing, what is mis-declared, and how much of the
   required content is actually there.

Stdlib only, offline, deterministic.
"""

import math

REQUIRED_CONTENT = (
    "mission-and-orbit-definition",
    "trapped-proton-environment",
    "trapped-electron-environment",
    "solar-particle-event-environment",
    "galactic-cosmic-ray-environment",
    "ionising-dose-depth-curve",
    "displacement-damage-fluence",
    "linear-energy-transfer-spectra",
    "shielding-assumptions",
)

OPTIONAL_CONTENT = (
    "secondary-particle-environment",
    "surface-charging-environment",
    "internal-charging-environment",
)

VALID_CONTENT = REQUIRED_CONTENT + OPTIONAL_CONTENT

# Items that name a particle environment and therefore owe a model
# identifier, a model version and a cited standard.
MODELLED_CONTENT = (
    "trapped-proton-environment",
    "trapped-electron-environment",
    "solar-particle-event-environment",
    "galactic-cosmic-ray-environment",
    "secondary-particle-environment",
    "surface-charging-environment",
    "internal-charging-environment",
)

# Statistical environments: evaluated at a confidence level.
STATISTICAL_CONTENT = ("solar-particle-event-environment",)

# Environments evaluated for a solar activity condition instead.
ACTIVITY_CONDITIONED_CONTENT = (
    "trapped-proton-environment",
    "trapped-electron-environment",
    "galactic-cosmic-ray-environment",
)

VALID_ACTIVITY_CONDITIONS = (
    "solar-minimum",
    "solar-maximum",
    "mission-averaged",
)

# Derived products read at a shielding thickness.
SHIELDING_SPANNED_CONTENT = (
    "ionising-dose-depth-curve",
    "displacement-damage-fluence",
)

# A statistical environment quoted below this confidence adds little
# to a worst-case design case.
MINIMUM_CONFIDENCE_PERCENT = 90.0

# Thicknesses are measured floats; a span ending exactly on the
# thinnest equipment shielding does reach it.
RELATIVE_TOLERANCE = 1.0e-9

FINDING_ITEM_MISSING = "required-content-item-missing"
FINDING_NO_MODEL = "model-identifier-not-declared"
FINDING_NO_VERSION = "model-version-not-declared"
FINDING_NO_STANDARD = "referenced-standard-not-cited"
FINDING_NO_CONFIDENCE = "confidence-level-not-declared"
FINDING_LOW_CONFIDENCE = "confidence-level-below-minimum"
FINDING_CONFIDENCE_MISPLACED = "confidence-level-on-a-deterministic-model"
FINDING_NO_ACTIVITY = "solar-activity-condition-not-declared"
FINDING_SPAN_TOO_THICK = "shielding-span-does-not-reach-thinnest-equipment-shielding"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def _optional_text(label, value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string when given" % label)
    return value.strip()


def validate_entry(entry):
    """Validate one content entry and return a normalized copy."""
    if not isinstance(entry, dict):
        raise ValueError("content entry must be a mapping")
    item = entry.get("item")
    if item not in VALID_CONTENT:
        raise ValueError(
            "content item %r unknown (expected one of %s)"
            % (item, ", ".join(VALID_CONTENT))
        )
    confidence = entry.get("confidence_level_percent")
    if confidence is not None:
        confidence = _numeric("%s confidence_level_percent" % item, confidence)
        if confidence <= 0.0 or confidence >= 100.0:
            raise ValueError(
                "%s confidence_level_percent must lie strictly between 0 and "
                "100, got %r" % (item, confidence)
            )
    condition = entry.get("solar_activity_condition")
    if condition is not None and condition not in VALID_ACTIVITY_CONDITIONS:
        raise ValueError(
            "%s solar_activity_condition %r unknown (expected one of %s)"
            % (item, condition, ", ".join(VALID_ACTIVITY_CONDITIONS))
        )
    span = entry.get("shielding_span_mm")
    if span is not None:
        if not isinstance(span, (list, tuple)) or len(span) != 2:
            raise ValueError("%s shielding_span_mm must be a two-value span" % item)
        low = _numeric("%s shielding_span_mm lower" % item, span[0])
        high = _numeric("%s shielding_span_mm upper" % item, span[1])
        if low <= 0.0 or high <= low:
            raise ValueError(
                "%s shielding_span_mm must be positive and ascending" % item
            )
        span = (low, high)
    return {
        "item": item,
        "model_identifier": _optional_text(
            "%s model_identifier" % item, entry.get("model_identifier")
        ),
        "model_version": _optional_text(
            "%s model_version" % item, entry.get("model_version")
        ),
        "reference_standard": _optional_text(
            "%s reference_standard" % item, entry.get("reference_standard")
        ),
        "confidence_level_percent": confidence,
        "solar_activity_condition": condition,
        "shielding_span_mm": span,
    }


def validate_specification(spec):
    """Validate the specification document and return a normalized copy."""
    if not isinstance(spec, dict):
        raise ValueError("specification must be a mapping")
    contents = spec.get("contents")
    if not isinstance(contents, list) or not contents:
        raise ValueError("specification contents must be a non-empty list")
    entries = []
    seen = set()
    for entry in contents:
        record = validate_entry(entry)
        if record["item"] in seen:
            raise ValueError("duplicate content item %r" % (record["item"],))
        seen.add(record["item"])
        entries.append(record)
    thinnest = spec.get("thinnest_equipment_shielding_mm")
    if thinnest is not None:
        thinnest = _numeric("thinnest_equipment_shielding_mm", thinnest)
        if thinnest <= 0.0:
            raise ValueError("thinnest_equipment_shielding_mm must be positive")
    return {"contents": entries, "thinnest_equipment_shielding_mm": thinnest}


def missing_required_items(spec):
    """Required content items the document does not carry."""
    normalized = validate_specification(spec)
    present = {entry["item"] for entry in normalized["contents"]}
    return [item for item in REQUIRED_CONTENT if item not in present]


def entry_findings(entry):
    """Findings about one content entry's own declarations."""
    record = validate_entry(entry)
    item = record["item"]
    findings = []
    if item in MODELLED_CONTENT:
        if not record["model_identifier"]:
            findings.append("%s:%s" % (FINDING_NO_MODEL, item))
        if not record["model_version"]:
            findings.append("%s:%s" % (FINDING_NO_VERSION, item))
        if not record["reference_standard"]:
            findings.append("%s:%s" % (FINDING_NO_STANDARD, item))
    if item in STATISTICAL_CONTENT:
        if record["confidence_level_percent"] is None:
            findings.append("%s:%s" % (FINDING_NO_CONFIDENCE, item))
        elif record["confidence_level_percent"] < MINIMUM_CONFIDENCE_PERCENT * (
            1.0 - RELATIVE_TOLERANCE
        ):
            findings.append("%s:%s" % (FINDING_LOW_CONFIDENCE, item))
    elif record["confidence_level_percent"] is not None:
        findings.append("%s:%s" % (FINDING_CONFIDENCE_MISPLACED, item))
    if item in ACTIVITY_CONDITIONED_CONTENT and not record[
        "solar_activity_condition"
    ]:
        findings.append("%s:%s" % (FINDING_NO_ACTIVITY, item))
    return findings


def shielding_coverage_findings(spec):
    """Findings about derived products not reaching the thinnest shielding."""
    normalized = validate_specification(spec)
    thinnest = normalized["thinnest_equipment_shielding_mm"]
    findings = []
    if thinnest is None:
        return findings
    for entry in normalized["contents"]:
        if entry["item"] not in SHIELDING_SPANNED_CONTENT:
            continue
        span = entry["shielding_span_mm"]
        if span is None:
            continue
        if span[0] > thinnest * (1.0 + RELATIVE_TOLERANCE):
            findings.append("%s:%s" % (FINDING_SPAN_TOO_THICK, entry["item"]))
    return findings


def completeness_ratio(spec):
    """Fraction of the required content items the document carries."""
    missing = missing_required_items(spec)
    return (len(REQUIRED_CONTENT) - len(missing)) / float(len(REQUIRED_CONTENT))


def assess_environment_specification(spec):
    """Run the Annex A content check over one environment specification."""
    normalized = validate_specification(spec)
    missing = missing_required_items(spec)
    findings = ["%s:%s" % (FINDING_ITEM_MISSING, item) for item in missing]
    for entry in normalized["contents"]:
        findings.extend(entry_findings(entry))
    findings.extend(shielding_coverage_findings(spec))
    return {
        "declared_items": [entry["item"] for entry in normalized["contents"]],
        "missing_items": missing,
        "completeness_ratio": completeness_ratio(spec),
        "findings": findings,
        "compliant": not findings,
    }
