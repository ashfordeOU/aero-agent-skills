"""Teardown construction analysis of sample units inside a category two validation.

Anchor: ECSS-Q-ST-60-05 clause 6.3.2 (the destructive examination of
representative units taken from a supplier's production run, carried out to
confirm build quality and the internal construction of the product).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The units are destroyed to be read, so where they came from is part of the
  evidence. A unit built on an engineering bench is not a unit off the line
  the validation is about, and a set resting on such units says nothing about
  serial production no matter how carefully it was torn down.
* The unit count comes from three directions at once: a floor for the product
  family, one unit for each declared production lot, and one unit for each
  declared design variant. The largest governs, so a family floor of three
  does not cover five lots.
* Count and coverage are separate questions. A set can be the right size and
  still leave a declared lot or a declared build standard with no unit
  speaking for it, and the analysis then has nothing to say about them.
* Each teardown step carries a weight. A few are the steps the analysis exists
  for -- opening the package, the internal visual examination, the
  cross-section, the attach-integrity examination and the interconnect
  examination -- and an analysis missing any of them is incomplete rather than
  merely weaker.
* A deviation is graded from what it touches and how widely it appears across
  the set, never from how bad it looked. Construction outside the declared
  build standard is critical on a single unit; an attach or interconnect
  integrity deviation is critical once it spans the set and major below that;
  dimensional or cosmetic workmanship on a minority of units is minor.
* The build-conformity index is weighted credit over total weight. It ranks
  what is outstanding; a critical deviation, an inadmissible unit source or a
  missing mandatory step decides the outcome on its own, at any index.
"""

from __future__ import annotations

import math

# Smallest unit set that can carry the teardown for a product family.
FAMILY_MINIMUM_UNITS = {
    "thick-film-hybrid": 3,
    "thin-film-hybrid": 3,
    "multichip-module": 4,
    "mixed-technology-hybrid": 4,
    "power-hybrid": 3,
}

UNITS_PER_PRODUCTION_LOT = 1
UNITS_PER_DESIGN_VARIANT = 1

# Where a unit came from, and whether that source can carry the analysis.
ADMISSIBLE_UNIT_SOURCES = ("serial-production-run", "qualification-production-run")
INADMISSIBLE_UNIT_SOURCES = ("engineering-build", "breadboard-build", "reworked-stock")

# Teardown steps and the share of the build argument each supplies.
TEARDOWN_STEP_WEIGHTS = {
    "external-visual-and-dimensional-check": 0.5,
    "marking-and-identification-check": 0.4,
    "package-opening-and-delidding": 1.0,
    "internal-visual-examination": 1.0,
    "cross-section-preparation-and-review": 1.0,
    "die-and-substrate-attach-examination": 0.9,
    "interconnect-and-bond-examination": 0.9,
    "materials-and-finish-verification": 0.7,
    "internal-dimension-measurement": 0.6,
}

# The steps the teardown exists for; without one the analysis is incomplete.
MANDATORY_TEARDOWN_STEPS = (
    "package-opening-and-delidding",
    "internal-visual-examination",
    "cross-section-preparation-and-review",
    "die-and-substrate-attach-examination",
    "interconnect-and-bond-examination",
)

STEP_OUTCOME_CREDIT = {
    "matches-declared-build": 1.0,
    "minor-deviation": 0.7,
    "major-deviation": 0.0,
    "step-not-performed": 0.0,
}

DEVIATION_CATEGORIES = (
    "critical-build-deviation",
    "major-build-deviation",
    "minor-build-deviation",
)

# A deviation on at least this share of the units is a feature of the build
# rather than a one-off escape.
SET_WIDE_UNIT_FRACTION = 0.5

# Build-conformity index an acceptable teardown has to reach.
ACCEPTANCE_INDEX = 0.90

# Indices are ratios of sums of weights; a case meant to sit on a bound can
# land a few units in the last place away from it.
TEARDOWN_TOLERANCE = 1e-9

VERDICTS = (
    "construction-confirms-declared-build",
    "construction-confirms-build-with-open-actions",
    "construction-does-not-confirm-declared-build",
    "construction-analysis-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _count(value, label):
    """Return ``value`` as a positive whole count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (label, value))
    return value


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def family_minimum_units(family):
    """Smallest unit set for a product family; unknown families are rejected."""
    if family not in FAMILY_MINIMUM_UNITS:
        raise ValueError(
            "unknown product family %r (known: %s)"
            % (family, ", ".join(sorted(FAMILY_MINIMUM_UNITS)))
        )
    return FAMILY_MINIMUM_UNITS[family]


def required_unit_count(family, production_lots, design_variants):
    """Units the teardown needs before it can speak for the declared build."""
    minimum = family_minimum_units(family)
    lots = _count(production_lots, "production_lots")
    variants = _count(design_variants, "design_variants")
    return max(
        minimum,
        lots * UNITS_PER_PRODUCTION_LOT,
        variants * UNITS_PER_DESIGN_VARIANT,
    )


def unit_source_is_admissible(source):
    """True when a unit's origin can carry a production construction argument."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError("unit source must be a non-empty string, got %r" % (source,))
    if source in ADMISSIBLE_UNIT_SOURCES:
        return True
    if source in INADMISSIBLE_UNIT_SOURCES:
        return False
    raise ValueError(
        "unknown unit source %r (known: %s)"
        % (source, ", ".join(sorted(ADMISSIBLE_UNIT_SOURCES + INADMISSIBLE_UNIT_SOURCES)))
    )


def normalize_units(units):
    """Validate the unit set and reject a repeated unit identifier."""
    if not isinstance(units, (list, tuple)):
        raise ValueError("units must be a list or tuple, got %r" % (type(units).__name__,))
    seen = set()
    normalized = []
    for raw in units:
        if not isinstance(raw, dict):
            raise ValueError("unit must be a mapping, got %r" % (type(raw).__name__,))
        unit_id = raw.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise ValueError("unit_id must be a non-empty string, got %r" % (unit_id,))
        if unit_id in seen:
            raise ValueError("duplicate unit identifier %r" % (unit_id,))
        seen.add(unit_id)
        record = {"unit_id": unit_id}
        for key in ("production_lot", "design_variant", "build_standard"):
            value = raw.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "unit %r must name its %s" % (unit_id, key.replace("_", " "))
                )
            record[key] = value
        source = raw.get("source")
        record["source"] = source
        record["source_admissible"] = unit_source_is_admissible(source)
        normalized.append(record)
    return normalized


def inadmissible_units(units):
    """Identifiers of units whose origin cannot carry the analysis."""
    return sorted(
        record["unit_id"] for record in normalize_units(units) if not record["source_admissible"]
    )


def unit_coverage(units, declared):
    """Declared lots, variants and build standards no unit in the set represents."""
    if not isinstance(declared, dict):
        raise ValueError("declared must be a mapping, got %r" % (type(declared).__name__,))
    normalized = [r for r in normalize_units(units) if r["source_admissible"]]
    uncovered = []
    for key, field, prefix in (
        ("production_lots", "production_lot", "production-lot"),
        ("design_variants", "design_variant", "design-variant"),
        ("build_standards", "build_standard", "build-standard"),
    ):
        listed = declared.get(key)
        if not isinstance(listed, (list, tuple)) or len(listed) == 0:
            raise ValueError("declared %s must be a non-empty list" % (key,))
        represented = {record[field] for record in normalized}
        for item in listed:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("declared %s entries must be non-empty strings" % (key,))
            if item not in represented:
                uncovered.append("%s:%s" % (prefix, item))
    return sorted(uncovered)


def step_weight(name):
    """Weight of one teardown step; unknown step names are rejected."""
    if name not in TEARDOWN_STEP_WEIGHTS:
        raise ValueError(
            "unknown teardown step %r (known: %s)"
            % (name, ", ".join(sorted(TEARDOWN_STEP_WEIGHTS)))
        )
    return TEARDOWN_STEP_WEIGHTS[name]


def outcome_credit(outcome):
    """Credit a teardown-step outcome earns."""
    if outcome not in STEP_OUTCOME_CREDIT:
        raise ValueError(
            "unknown step outcome %r (known: %s)"
            % (outcome, ", ".join(sorted(STEP_OUTCOME_CREDIT)))
        )
    return STEP_OUTCOME_CREDIT[outcome]


def normalize_step(raw):
    """Validate one teardown-step record and fill its default outcome."""
    if not isinstance(raw, dict):
        raise ValueError("step must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("step")
    step_weight(name)  # validation only
    outcome = raw.get("outcome", "step-not-performed")
    outcome_credit(outcome)  # validation only
    return {"step": name, "outcome": outcome}


def assess_step(raw):
    """Grade one teardown step into a credit and its findings."""
    record = normalize_step(raw)
    name = record["step"]
    outcome = record["outcome"]
    weight = step_weight(name)
    credit = outcome_credit(outcome)
    findings = []
    if outcome == "minor-deviation":
        findings.append("step-minor-deviation")
    elif outcome == "major-deviation":
        findings.append("step-major-deviation")
    elif outcome == "step-not-performed":
        findings.append("step-not-performed")
    mandatory_missing = name in MANDATORY_TEARDOWN_STEPS and outcome == "step-not-performed"
    if mandatory_missing:
        findings.append("mandatory-teardown-step-not-performed")
    return {
        "step": name,
        "outcome": outcome,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory_missing": mandatory_missing,
        "findings": findings,
    }


def build_conformity_index(records):
    """Weighted credit of a set of graded teardown steps over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a teardown must carry at least one step")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total teardown weight must be positive")
    return earned / total_weight


def categorize_deviation(deviation, unit_count):
    """Group one observed build deviation into a severity category.

    The category comes from what the deviation touches and how widely it
    appears across the unit set, never from how bad it looked on the bench.
    """
    if not isinstance(deviation, dict):
        raise ValueError("deviation must be a mapping, got %r" % (type(deviation).__name__,))
    total = _count(unit_count, "unit_count")
    observed = deviation.get("observed_on_units")
    if isinstance(observed, bool) or not isinstance(observed, int):
        raise ValueError("observed_on_units must be a whole number, got %r" % (observed,))
    if observed < 1:
        raise ValueError("observed_on_units must be at least one, got %r" % (observed,))
    if observed > total:
        raise ValueError(
            "observed_on_units (%d) exceeds the unit count (%d)" % (observed, total)
        )
    outside_build_standard = _flag(deviation, "outside_declared_build_standard")
    touches_attach_or_bond = _flag(deviation, "affects_attach_or_bond_integrity")
    dimensional_or_cosmetic = _flag(deviation, "dimensional_or_cosmetic_only")
    fraction = float(observed) / float(total)
    set_wide = fraction >= SET_WIDE_UNIT_FRACTION - TEARDOWN_TOLERANCE
    if outside_build_standard:
        return "critical-build-deviation"
    if touches_attach_or_bond and set_wide:
        return "critical-build-deviation"
    if touches_attach_or_bond:
        return "major-build-deviation"
    if dimensional_or_cosmetic and not set_wide:
        return "minor-build-deviation"
    return "major-build-deviation"


def assess_construction_analysis(
    product_id, family, declared, units, steps, deviations=()
):
    """Grade a whole teardown construction analysis and name one verdict."""
    if not isinstance(product_id, str) or not product_id.strip():
        raise ValueError("product_id must be a non-empty string, got %r" % (product_id,))
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list or tuple, got %r" % (type(steps).__name__,))
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a list or tuple, got %r" % (type(deviations).__name__,))
    if not isinstance(declared, dict):
        raise ValueError("declared must be a mapping, got %r" % (type(declared).__name__,))

    normalized_units = normalize_units(units)
    if len(normalized_units) == 0:
        raise ValueError("a construction analysis must carry at least one unit")

    # unit_coverage validates the declared lists, so it runs before the count
    # is required against lists now known to be well formed.
    uncovered = unit_coverage(normalized_units, declared)
    rejected_units = [r["unit_id"] for r in normalized_units if not r["source_admissible"]]
    admissible = [r for r in normalized_units if r["source_admissible"]]
    required = required_unit_count(
        family,
        len(declared["production_lots"]),
        len(declared["design_variants"]),
    )

    declared_steps = {}
    for raw in steps:
        record = normalize_step(raw)
        if record["step"] in declared_steps:
            raise ValueError("duplicate teardown step %r" % (record["step"],))
        declared_steps[record["step"]] = record
    step_records = []
    for name in sorted(TEARDOWN_STEP_WEIGHTS):
        step_records.append(assess_step(declared_steps.get(name, {"step": name})))
    index = build_conformity_index(step_records)

    findings = []
    if len(admissible) < required:
        findings.append(
            {
                "item": "unit-set",
                "finding": "unit-count-below-minimum",
                "detail": "%d of %d" % (len(admissible), required),
            }
        )
    for unit_id in sorted(rejected_units):
        findings.append(
            {
                "item": unit_id,
                "finding": "unit-source-not-admissible",
                "detail": "unit was not drawn from a production run",
            }
        )
    for item in uncovered:
        findings.append(
            {"item": item, "finding": "declared-build-not-represented", "detail": item}
        )
    for record in step_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["step"], "finding": finding, "detail": record["outcome"]}
            )

    categorized = []
    unit_total = max(len(admissible), 1)
    for deviation in deviations:
        severity = categorize_deviation(deviation, unit_total)
        categorized.append({"deviation": deviation.get("deviation_id"), "severity": severity})
        findings.append(
            {
                "item": deviation.get("deviation_id"),
                "finding": severity,
                "detail": "%d of %d units" % (deviation.get("observed_on_units"), unit_total),
            }
        )

    incomplete = (
        len(admissible) < required
        or bool(uncovered)
        or bool(rejected_units)
        or any(r["mandatory_missing"] for r in step_records)
    )
    critical = any(entry["severity"] == "critical-build-deviation" for entry in categorized)
    if incomplete:
        verdict = "construction-analysis-incomplete"
    elif critical or index < ACCEPTANCE_INDEX - TEARDOWN_TOLERANCE:
        verdict = "construction-does-not-confirm-declared-build"
    elif findings:
        verdict = "construction-confirms-build-with-open-actions"
    else:
        verdict = "construction-confirms-declared-build"
    return {
        "product_id": product_id,
        "product_family": family,
        "unit_count": len(normalized_units),
        "admissible_unit_count": len(admissible),
        "required_unit_count": required,
        "rejected_units": sorted(rejected_units),
        "uncovered_declarations": uncovered,
        "step_records": step_records,
        "build_conformity_index": index,
        "deviations": categorized,
        "findings": findings,
        "verdict": verdict,
        "build_confirmed": verdict
        in (
            "construction-confirms-declared-build",
            "construction-confirms-build-with-open-actions",
        ),
    }
