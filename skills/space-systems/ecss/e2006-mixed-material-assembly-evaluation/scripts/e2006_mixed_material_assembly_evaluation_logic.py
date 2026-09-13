#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 6.3.3.4 -- mixed-material assembly evaluation.

Deterministic, offline, stdlib-only support for the rule that an externally
exposed assembly combining dissimilar ungrounded materials is qualified as a
complete unit rather than by stacking evidence gathered on its individual
constituents.

The module supplies four steps:

1. categorize every constituent of the assembly as a grounded conductor, a
   floating (ungrounded) conductor or an exposed dielectric, from its surface
   resistivity and its grounding state;
2. decide whether the assembly is a mixed-material assembly at all -- two or
   more ungrounded constituents that are dissimilar, either by category or by
   a surface-resistivity separation of at least one decade;
3. quantify the differential-charging driver as the largest resistivity
   decade span between any two ungrounded constituents that share the exposed
   face, and compare it with the unit-level review threshold;
4. check the verification evidence on record: a mixed-material assembly needs
   complete-unit evidence (an assembly-level electrostatic assessment or an
   assembly-level qualification run on a representative specimen), covering
   every constituent, over an environment envelope that bounds the worst case.

All thresholds are module constants so a project can re-baseline them without
touching the procedure.
"""

import math

# Surfaces at or below this surface resistivity are treated as conductive for
# the purposes of the clause; above it the surface behaves as a dielectric.
CONDUCTIVE_CEILING_OHM_SQ = 1.0e5

# Two ungrounded constituents count as dissimilar once their surface
# resistivities are separated by at least this many decades.
DISSIMILARITY_DECADES = 1.0

# Decade span between ungrounded constituents above which differential
# charging across the junction drives the unit-level review.
DECADE_SPAN_LIMIT = 4.0

# Absolute tolerance absorbing the representation error of a log10 difference
# so a span that is physically exactly at the limit is not reported as over.
DECADE_TOLERANCE = 1.0e-9

CATEGORY_GROUNDED_CONDUCTOR = "grounded-conductor"
CATEGORY_FLOATING_CONDUCTOR = "floating-conductor"
CATEGORY_EXPOSED_DIELECTRIC = "exposed-dielectric"

UNGROUNDED_CATEGORIES = (CATEGORY_FLOATING_CONDUCTOR, CATEGORY_EXPOSED_DIELECTRIC)

EVIDENCE_METHODS = ("assembly-assessment", "assembly-qualification")
EVIDENCE_COVERAGE = ("complete-unit", "per-constituent")

EVIDENCE_LEVEL_UNIT = "complete-unit"
EVIDENCE_LEVEL_CONSTITUENT = "per-constituent"


def _require_mapping(record, label):
    """Return record when it is a mapping, else raise ValueError."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, type(record).__name__))
    return record


def _require_name(record, label):
    """Return a non-empty constituent/assembly identifier."""
    value = record.get("name")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s needs a non-empty 'name'" % label)
    return value.strip()


def _require_positive(record, key, label):
    """Return a strictly positive finite float pulled from record[key]."""
    if key not in record:
        raise ValueError("%s missing required '%s'" % (label, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s '%s' must be numeric, got %r" % (label, key, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s '%s' must be finite, got %r" % (label, key, value))
    if value <= 0.0:
        raise ValueError("%s '%s' must be > 0, got %r" % (label, key, value))
    return value


def _require_non_negative(record, key, label, default=None):
    """Return a finite float >= 0, falling back to default when absent."""
    if key not in record:
        if default is None:
            raise ValueError("%s missing required '%s'" % (label, key))
        return float(default)
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s '%s' must be numeric, got %r" % (label, key, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s '%s' must be finite, got %r" % (label, key, value))
    if value < 0.0:
        raise ValueError("%s '%s' must be >= 0, got %r" % (label, key, value))
    return value


def _require_bool(record, key, label):
    """Return a boolean field, rejecting truthy stand-ins such as 'yes'."""
    if key not in record:
        raise ValueError("%s missing required '%s'" % (label, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s '%s' must be a boolean, got %r" % (label, key, value))
    return value


def resistivity_decades(surface_resistivity_ohm_sq):
    """Return the base-10 decade coordinate of a surface resistivity."""
    if isinstance(surface_resistivity_ohm_sq, bool) or not isinstance(
        surface_resistivity_ohm_sq, (int, float)
    ):
        raise ValueError("surface resistivity must be numeric")
    value = float(surface_resistivity_ohm_sq)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("surface resistivity must be finite and > 0, got %r" % (value,))
    return math.log10(value)


def categorize_constituent(constituent):
    """Categorize one constituent of the assembly.

    Expects: name, surface_resistivity_ohm_sq, grounded (bool) and optionally
    exposed_area_m2 (defaults to 0.0, meaning an internal constituent).
    Returns a normalized record carrying the category and the ungrounded flag.
    """
    _require_mapping(constituent, "constituent")
    name = _require_name(constituent, "constituent")
    label = "constituent '%s'" % name
    resistivity = _require_positive(constituent, "surface_resistivity_ohm_sq", label)
    grounded = _require_bool(constituent, "grounded", label)
    area = _require_non_negative(constituent, "exposed_area_m2", label, default=0.0)

    conductive = resistivity <= CONDUCTIVE_CEILING_OHM_SQ or math.isclose(
        resistivity, CONDUCTIVE_CEILING_OHM_SQ, rel_tol=1e-12, abs_tol=0.0
    )
    if conductive and grounded:
        category = CATEGORY_GROUNDED_CONDUCTOR
    elif conductive:
        category = CATEGORY_FLOATING_CONDUCTOR
    else:
        category = CATEGORY_EXPOSED_DIELECTRIC

    return {
        "name": name,
        "category": category,
        "surface_resistivity_ohm_sq": resistivity,
        "decades": resistivity_decades(resistivity),
        "grounded": grounded,
        "exposed_area_m2": area,
        "ungrounded": category in UNGROUNDED_CATEGORIES,
        "externally_exposed": area > 0.0,
    }


def categorize_assembly(constituents):
    """Categorize every constituent, rejecting an empty or duplicated set."""
    if not isinstance(constituents, (list, tuple)):
        raise ValueError("constituents must be a list")
    if len(constituents) == 0:
        raise ValueError("assembly needs at least one constituent")
    categorized = [categorize_constituent(item) for item in constituents]
    seen = set()
    for item in categorized:
        if item["name"] in seen:
            raise ValueError("duplicate constituent name '%s'" % item["name"])
        seen.add(item["name"])
    return categorized


def ungrounded_constituents(categorized):
    """Return the ungrounded members of a categorized assembly."""
    return [item for item in categorized if item["ungrounded"]]


def pairwise_decade_span(categorized):
    """Return the resistivity separation between ungrounded constituents.

    Only externally exposed ungrounded constituents can charge differentially
    against one another on the outer face, so the pairing is restricted to
    them. The driving pair is the widest separation found.
    """
    exposed = [
        item
        for item in ungrounded_constituents(categorized)
        if item["externally_exposed"]
    ]
    pairs = []
    for i in range(len(exposed)):
        for j in range(i + 1, len(exposed)):
            first, second = exposed[i], exposed[j]
            span = abs(first["decades"] - second["decades"])
            pairs.append(
                {
                    "pair": (first["name"], second["name"]),
                    "span_decades": span,
                    "dissimilar": span >= DISSIMILARITY_DECADES
                    or first["category"] != second["category"],
                }
            )
    pairs.sort(key=lambda entry: (-entry["span_decades"], entry["pair"]))
    max_span = pairs[0]["span_decades"] if pairs else 0.0
    exceeds = max_span > DECADE_SPAN_LIMIT and not math.isclose(
        max_span, DECADE_SPAN_LIMIT, rel_tol=0.0, abs_tol=DECADE_TOLERANCE
    )
    return {
        "pairs": pairs,
        "max_span_decades": max_span,
        "driving_pair": pairs[0]["pair"] if pairs else None,
        "exceeds_review_threshold": exceeds,
    }


def is_mixed_material_assembly(categorized):
    """True when two or more dissimilar ungrounded constituents are exposed."""
    span = pairwise_decade_span(categorized)
    return any(entry["dissimilar"] for entry in span["pairs"])


def required_evidence_level(categorized):
    """Return the evidence level the clause demands for this assembly."""
    if is_mixed_material_assembly(categorized):
        return EVIDENCE_LEVEL_UNIT
    return EVIDENCE_LEVEL_CONSTITUENT


def validate_evidence(evidence):
    """Normalize a verification-evidence record, rejecting unknown fields."""
    _require_mapping(evidence, "evidence")
    method = evidence.get("method")
    if method not in EVIDENCE_METHODS:
        raise ValueError(
            "evidence method %r is not one of %s" % (method, list(EVIDENCE_METHODS))
        )
    coverage = evidence.get("coverage")
    if coverage not in EVIDENCE_COVERAGE:
        raise ValueError(
            "evidence coverage %r is not one of %s" % (coverage, list(EVIDENCE_COVERAGE))
        )
    representative = _require_bool(evidence, "specimen_representative", "evidence")
    envelope = _require_bool(evidence, "envelope_bounds_worst_case", "evidence")
    covered = evidence.get("constituents_covered", [])
    if not isinstance(covered, (list, tuple)):
        raise ValueError("evidence 'constituents_covered' must be a list")
    names = []
    for item in covered:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("evidence 'constituents_covered' entries must be names")
        names.append(item.strip())
    return {
        "method": method,
        "coverage": coverage,
        "specimen_representative": representative,
        "envelope_bounds_worst_case": envelope,
        "constituents_covered": names,
    }


def evidence_findings(normalized_evidence, categorized, level):
    """Return the open findings against the evidence for this assembly."""
    findings = []
    if level == EVIDENCE_LEVEL_UNIT:
        if normalized_evidence is None:
            return ["no verification evidence on record for a mixed-material assembly"]
        if normalized_evidence["coverage"] != EVIDENCE_LEVEL_UNIT:
            findings.append(
                "evidence coverage is '%s'; a mixed-material assembly is verified "
                "as a complete unit" % normalized_evidence["coverage"]
            )
        if not normalized_evidence["specimen_representative"]:
            findings.append(
                "evidence specimen is not representative of the delivered assembly"
            )
        if not normalized_evidence["envelope_bounds_worst_case"]:
            findings.append(
                "evidence environment envelope does not bound the worst-case case"
            )
        covered = set(normalized_evidence["constituents_covered"])
        missing = sorted(
            item["name"] for item in categorized if item["name"] not in covered
        )
        for name in missing:
            findings.append("constituent '%s' is absent from the evidence" % name)
        return findings
    if normalized_evidence is None:
        return ["no verification evidence on record"]
    if not normalized_evidence["envelope_bounds_worst_case"]:
        findings.append(
            "evidence environment envelope does not bound the worst-case case"
        )
    return findings


def evaluate_mixed_material_assembly(assembly):
    """Run the full clause 6.3.3.4 evaluation over one assembly record."""
    _require_mapping(assembly, "assembly")
    assembly_id = _require_name(assembly, "assembly")
    categorized = categorize_assembly(assembly.get("constituents"))
    span = pairwise_decade_span(categorized)
    mixed = any(entry["dissimilar"] for entry in span["pairs"])
    level = EVIDENCE_LEVEL_UNIT if mixed else EVIDENCE_LEVEL_CONSTITUENT

    raw_evidence = assembly.get("evidence")
    normalized = validate_evidence(raw_evidence) if raw_evidence is not None else None
    findings = evidence_findings(normalized, categorized, level)
    if span["exceeds_review_threshold"] and (
        normalized is None or normalized["method"] != "assembly-qualification"
    ):
        findings.append(
            "resistivity span of %.2f decades between %s exceeds the unit-level "
            "review threshold; an assembly-level qualification run is required"
            % (span["max_span_decades"], span["driving_pair"])
        )
    return {
        "assembly": assembly_id,
        "constituents": categorized,
        "ungrounded_count": len(ungrounded_constituents(categorized)),
        "mixed_material": mixed,
        "required_evidence_level": level,
        "differential_charge_driver": span,
        "findings": findings,
        "compliant": not findings,
    }
