"""Re-test plan and acceptance after a shelf-life extension.

Anchor: ECSS-Q-ST-70-22 life-extension clause -- the re-test carried out before
a stored material's life is extended, and the acceptance applied to its
results. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Build the plan from the material family: which properties have to be
   re-tested, which direction each one may drift in, and how many specimens the
   lot size owes.
2. Derive an acceptance threshold per property from the value recorded at
   manufacture and a declared retention fraction. The direction matters: a
   strength may only fall so far, a viscosity may only rise so far, and a
   banded property may move either way by the same relative slack.
3. Compare each result against its threshold with a relative tolerance, so a
   result sitting exactly on the limit is accepted on every platform rather
   than on whichever one rounded kindly.
4. Separate a FAILED re-test from an INCOMPLETE one: a property that was tested
   and missed its threshold is a different outcome from a property nobody
   tested, and only the first is evidence about the material.
5. Close with passed / failed / incomplete and the extension period the re-test
   can carry.
"""

import math

__all__ = [
    "REL_TOLERANCE",
    "ABS_TOLERANCE",
    "DEFAULT_RETENTION",
    "PROPERTY_SENSE",
    "FAMILY_PROPERTIES",
    "SAMPLE_SIZE_BRACKETS",
    "LARGE_LOT_SAMPLE_SIZE",
    "sample_size",
    "required_properties",
    "acceptance_threshold",
    "build_re_test_plan",
    "evaluate_property",
    "evaluate_results",
    "assess_re_test",
]

# Thresholds are products of a declared fraction and a recorded value; a result
# meant to sit exactly on the limit lands a few ULPs either side of it, and
# differently on different platforms. The comparison carries the tolerance.
REL_TOLERANCE = 1e-9
ABS_TOLERANCE = 1e-12

# Default share of the as-manufactured value a re-tested property must retain.
DEFAULT_RETENTION = 0.90

# Which way a property is allowed to drift: 'min' may only fall, 'max' may only
# rise, 'band' may move either way by the same relative slack.
PROPERTY_SENSE = {
    "lap-shear-strength": "min",
    "adhesion-strength": "min",
    "tensile-strength": "min",
    "flexural-strength": "min",
    "elongation": "min",
    "peel-strength": "min",
    "viscosity": "max",
    "volatile-content": "max",
    "hardness": "band",
    "cure-hardness": "band",
    "gel-time": "band",
    "application-life": "band",
    "resin-content": "band",
    "flow": "band",
    "tack": "band",
}

# Properties a re-test has to cover, per material family.
FAMILY_PROPERTIES = {
    "sealant": ("application-life", "cure-hardness", "adhesion-strength"),
    "adhesive-paste": ("viscosity", "gel-time", "lap-shear-strength"),
    "film-adhesive": ("flow", "volatile-content", "lap-shear-strength"),
    "prepreg": ("resin-content", "gel-time", "tack", "flexural-strength"),
    "elastomer": ("hardness", "tensile-strength", "elongation"),
    "coating": ("viscosity", "cure-hardness", "adhesion-strength"),
}

# Specimens owed per property, by lot size. Upper bound of the bracket, count.
SAMPLE_SIZE_BRACKETS = ((8, 2), (25, 3), (90, 5), (150, 8))
LARGE_LOT_SAMPLE_SIZE = 13


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _retention(value):
    fraction = _real(value, "retention")
    if fraction <= 0.0 or fraction >= 1.0:
        raise ValueError("retention must lie strictly inside (0, 1), got %g" % fraction)
    return fraction


def sample_size(lot_units):
    """Return the specimens owed per property for a lot of this size."""
    if not isinstance(lot_units, int) or isinstance(lot_units, bool):
        raise ValueError("lot_units must be an integer, got %r" % (lot_units,))
    if lot_units < 1:
        raise ValueError("lot_units must be at least 1, got %d" % lot_units)
    for upper, count in SAMPLE_SIZE_BRACKETS:
        if lot_units <= upper:
            return count
    return LARGE_LOT_SAMPLE_SIZE


def required_properties(family):
    """Return the properties a re-test of this family has to cover."""
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string")
    key = family.strip().lower()
    if key not in FAMILY_PROPERTIES:
        raise ValueError(
            "unknown material family %r; known families: %s"
            % (family, ", ".join(sorted(FAMILY_PROPERTIES)))
        )
    return list(FAMILY_PROPERTIES[key])


def acceptance_threshold(prop, original_value, retention=DEFAULT_RETENTION):
    """Return the acceptance threshold record for one property."""
    if prop not in PROPERTY_SENSE:
        raise ValueError(
            "unknown property %r; known properties: %s"
            % (prop, ", ".join(sorted(PROPERTY_SENSE)))
        )
    original = _real(original_value, "original_value")
    if original <= 0.0:
        raise ValueError("original_value must be positive, got %g" % original)
    fraction = _retention(retention)
    sense = PROPERTY_SENSE[prop]
    slack = 1.0 - fraction
    if sense == "min":
        return {"property": prop, "sense": sense, "lower": fraction * original, "upper": None}
    if sense == "max":
        return {"property": prop, "sense": sense, "lower": None,
                "upper": (1.0 + slack) * original}
    return {"property": prop, "sense": sense,
            "lower": (1.0 - slack) * original, "upper": (1.0 + slack) * original}


def build_re_test_plan(family, lot_units, originals, retention=DEFAULT_RETENTION):
    """Return the re-test plan: property, sense, specimens and thresholds."""
    props = required_properties(family)
    if not isinstance(originals, dict):
        raise ValueError("originals must be a mapping of property to as-manufactured value")
    specimens = sample_size(lot_units)
    fraction = _retention(retention)
    plan = []
    for prop in props:
        if prop not in originals:
            raise ValueError("originals is missing the as-manufactured value for %r" % prop)
        record = acceptance_threshold(prop, originals[prop], fraction)
        record["specimens"] = specimens
        record["original_value"] = _real(originals[prop], prop)
        plan.append(record)
    return {
        "family": family.strip().lower(),
        "lot_units": lot_units,
        "retention": fraction,
        "specimens_per_property": specimens,
        "properties": plan,
    }


def _at_least(value, bound):
    return value >= bound - abs(bound) * REL_TOLERANCE - ABS_TOLERANCE


def _at_most(value, bound):
    return value <= bound + abs(bound) * REL_TOLERANCE + ABS_TOLERANCE


def evaluate_property(record, measured_values):
    """Grade one property's specimen results against its threshold record."""
    if not isinstance(record, dict) or "sense" not in record:
        raise ValueError("record must be a threshold record from acceptance_threshold")
    if not isinstance(measured_values, (list, tuple)) or not measured_values:
        raise ValueError("measured_values must be a non-empty sequence")
    specimens = record.get("specimens")
    values = [_real(value, "measured value") for value in measured_values]
    short = specimens is not None and len(values) < specimens
    worst = None
    accepted = True
    for value in values:
        ok = True
        if record["lower"] is not None and not _at_least(value, record["lower"]):
            ok = False
        if record["upper"] is not None and not _at_most(value, record["upper"]):
            ok = False
        if not ok:
            accepted = False
            if worst is None:
                worst = value
    return {
        "property": record["property"],
        "sense": record["sense"],
        "specimens_required": specimens,
        "specimens_reported": len(values),
        "under_sampled": short,
        "mean": sum(values) / float(len(values)),
        "first_failing_value": worst,
        "accepted": accepted and not short,
    }


def evaluate_results(plan, results):
    """Grade a whole result set against a plan, separating missing from failing."""
    if not isinstance(plan, dict) or "properties" not in plan:
        raise ValueError("plan must be a mapping produced by build_re_test_plan")
    if not isinstance(results, dict):
        raise ValueError("results must be a mapping of property to specimen values")
    graded = []
    missing = []
    for record in plan["properties"]:
        prop = record["property"]
        if prop not in results:
            missing.append(prop)
            continue
        graded.append(evaluate_property(record, results[prop]))
    planned = {record["property"] for record in plan["properties"]}
    unplanned = sorted(prop for prop in results if prop not in planned)
    failed = [item["property"] for item in graded if not item["accepted"]]
    return {
        "graded": graded,
        "missing_properties": missing,
        "unplanned_properties": unplanned,
        "failed_properties": failed,
    }


def assess_re_test(spec):
    """Build the plan, grade the results and say what extension the re-test carries.

    spec keys: family, lot_units, originals, results, requested_extension_days,
    optional retention.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("family", "lot_units", "originals", "results", "requested_extension_days"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    requested = spec["requested_extension_days"]
    if not isinstance(requested, int) or isinstance(requested, bool):
        raise ValueError("requested_extension_days must be an integer, got %r" % (requested,))
    if requested < 1:
        raise ValueError("requested_extension_days must be at least 1, got %d" % requested)
    plan = build_re_test_plan(spec["family"], spec["lot_units"], spec["originals"],
                              spec.get("retention", DEFAULT_RETENTION))
    outcome = evaluate_results(plan, spec["results"])
    findings = []
    for prop in outcome["missing_properties"]:
        findings.append("property %s was not re-tested" % prop)
    for item in outcome["graded"]:
        if item["under_sampled"]:
            findings.append(
                "property %s reported %d specimen(s) against %d required"
                % (item["property"], item["specimens_reported"], item["specimens_required"])
            )
        elif not item["accepted"]:
            findings.append(
                "property %s has a specimen at %.4f outside its acceptance"
                % (item["property"], item["first_failing_value"])
            )
    for prop in outcome["unplanned_properties"]:
        findings.append("result reported for %s, which this family's plan does not call for"
                        % prop)
    under_sampled = [item["property"] for item in outcome["graded"] if item["under_sampled"]]
    hard_failures = [item["property"] for item in outcome["graded"]
                     if not item["accepted"] and not item["under_sampled"]]
    if hard_failures:
        disposition = "re-test-failed"
    elif outcome["missing_properties"] or under_sampled:
        disposition = "re-test-incomplete"
    else:
        disposition = "re-test-passed"
    return {
        "plan": plan,
        "outcome": outcome,
        "under_sampled_properties": under_sampled,
        "findings": findings,
        "disposition": disposition,
        "supports_extension": disposition == "re-test-passed",
        "extension_days_supported": requested if disposition == "re-test-passed" else 0,
    }
