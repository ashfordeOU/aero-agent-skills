#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 7.2.1.2.1 antenna terminology definitions
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires a project to
adopt one recognised source of antenna terminology and to use it
consistently in every specification, drawing and report. The
implementable form of that requirement is a registry check. Exactly one
recognised vocabulary is declared; every term appearing in project
documentation resolves either to a canonical term of that vocabulary, to
a deprecated synonym that must be rewritten onto its canonical form, or
to nothing at all; every project glossary entry that repeats a registry
term agrees with it on defining vocabulary and unit; and the fraction of
term occurrences needing no rewrite is held against a project threshold.

This module implements term normalisation, term resolution against the
canonical registry and the deprecated-synonym map, terminology-source
validation, per-document scanning, glossary consistency checking, the
conformance ratio and the aggregate project review. It does not define
the terms themselves -- the registry records which recognised vocabulary
defines each term and in which unit it is expressed.
"""

import math

# Recognised antenna terminology vocabularies. A project declares exactly
# one of these; a name outside the registry is not a recognised source.
RECOGNIZED_TERMINOLOGY_SOURCES = {
    "ieee-std-145": "IEEE standard definitions of terms for antennas",
    "iec-60050-712": "International electrotechnical vocabulary, antennas chapter",
    "itu-r-v-573": "ITU radiocommunication vocabulary",
}

# Canonical terms, the vocabulary that defines each one, and the unit the
# quantity is expressed in. "none" marks a term that names a direction,
# a surface or a construct rather than a measured quantity.
CANONICAL_TERMS = {
    "antenna-gain": {"source": "ieee-std-145", "unit": "dBi"},
    "directivity": {"source": "ieee-std-145", "unit": "dBi"},
    "radiation-efficiency": {"source": "ieee-std-145", "unit": "ratio"},
    "aperture-efficiency": {"source": "ieee-std-145", "unit": "ratio"},
    "half-power-beamwidth": {"source": "ieee-std-145", "unit": "degree"},
    "side-lobe-level": {"source": "ieee-std-145", "unit": "dB"},
    "axial-ratio": {"source": "ieee-std-145", "unit": "dB"},
    "boresight": {"source": "ieee-std-145", "unit": "none"},
    "radiation-pattern": {"source": "ieee-std-145", "unit": "none"},
    "cross-polar-discrimination": {"source": "itu-r-v-573", "unit": "dB"},
    "effective-isotropic-radiated-power": {"source": "itu-r-v-573", "unit": "dBW"},
    "edge-of-coverage-gain": {"source": "itu-r-v-573", "unit": "dBi"},
    "voltage-standing-wave-ratio": {"source": "iec-60050-712", "unit": "ratio"},
    "characteristic-impedance": {"source": "iec-60050-712", "unit": "ohm"},
}

# Terms still in circulation that a recognised vocabulary replaces. Each
# one is rewritten onto its canonical form rather than accepted.
DEPRECATED_SYNONYMS = {
    "aerial-gain": "antenna-gain",
    "gain-over-isotropic": "antenna-gain",
    "3-db-beamwidth": "half-power-beamwidth",
    "hpbw": "half-power-beamwidth",
    "first-side-lobe": "side-lobe-level",
    "ellipticity-ratio": "axial-ratio",
    "electrical-axis": "boresight",
    "beam-peak": "boresight",
    "antenna-pattern": "radiation-pattern",
    "xpd": "cross-polar-discrimination",
    "eirp": "effective-isotropic-radiated-power",
    "eoc-gain": "edge-of-coverage-gain",
    "swr": "voltage-standing-wave-ratio",
}

STATUS_CANONICAL = "canonical"
STATUS_DEPRECATED_SYNONYM = "deprecated-synonym"
STATUS_UNCATEGORIZED = "uncategorized"

# House minimum fraction of term occurrences needing no rewrite.
MINIMUM_TERMINOLOGY_CONFORMANCE = 0.95

# The ratio is formed by subtraction, so a project exactly on the
# threshold can land a few units in the last place below it. The
# threshold itself is never lowered -- only the round-off is absorbed.
CONFORMANCE_TOLERANCE = 1e-9


def normalize_term(term):
    """Fold one term into the registry key form: lowercase and hyphenated."""
    if not isinstance(term, str):
        raise ValueError("term must be a string, got %r" % (term,))
    folded = term.strip().lower().replace("_", " ").replace("-", " ")
    parts = [part for part in folded.split() if part]
    if not parts:
        raise ValueError("term must not be empty")
    return "-".join(parts)


def resolve_term(term):
    """Resolve one term to its canonical form, status and defining vocabulary."""
    key = normalize_term(term)
    if key in CANONICAL_TERMS:
        entry = CANONICAL_TERMS[key]
        return {
            "term": key,
            "canonical": key,
            "status": STATUS_CANONICAL,
            "source": entry["source"],
            "unit": entry["unit"],
        }
    if key in DEPRECATED_SYNONYMS:
        canonical = DEPRECATED_SYNONYMS[key]
        entry = CANONICAL_TERMS[canonical]
        return {
            "term": key,
            "canonical": canonical,
            "status": STATUS_DEPRECATED_SYNONYM,
            "source": entry["source"],
            "unit": entry["unit"],
        }
    return {
        "term": key,
        "canonical": None,
        "status": STATUS_UNCATEGORIZED,
        "source": None,
        "unit": None,
    }


def validate_terminology_source(declared_sources):
    """Require exactly one declared vocabulary, and that it is recognised."""
    if isinstance(declared_sources, str) or not isinstance(
        declared_sources, (list, tuple)
    ):
        raise ValueError("declared sources must be a list or tuple of vocabulary names")
    declared = []
    for name in declared_sources:
        if not isinstance(name, str):
            raise ValueError("declared source name must be a string, got %r" % (name,))
        folded = name.strip().lower().replace("_", "-").replace(" ", "-")
        if not folded:
            raise ValueError("declared source name must not be empty")
        declared.append(folded)
    findings = []
    unrecognised = [name for name in declared if name not in RECOGNIZED_TERMINOLOGY_SOURCES]
    for name in unrecognised:
        findings.append("declared terminology source %s is not a recognised vocabulary" % name)
    recognised = [name for name in declared if name in RECOGNIZED_TERMINOLOGY_SOURCES]
    if not declared:
        findings.append("no antenna terminology source is declared for the project")
    elif len(declared) > 1:
        findings.append(
            "%d terminology sources are declared; the clause allows exactly one"
            % len(declared)
        )
    source = recognised[0] if len(recognised) == 1 and len(declared) == 1 else None
    return {
        "declared": declared,
        "source": source,
        "findings": findings,
        "valid": not findings,
    }


def scan_document_terms(document, declared_source=None):
    """Resolve every term of one document and report the rewrites it needs."""
    if not isinstance(document, dict):
        raise ValueError("document record must be a mapping")
    document_id = document.get("document_id")
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document record needs a non-empty document_id")
    terms = document.get("terms")
    if isinstance(terms, str) or not isinstance(terms, (list, tuple)):
        raise ValueError("document %s needs a list of terms" % document_id)
    if not terms:
        raise ValueError("document %s lists no terms to check" % document_id)
    if declared_source is not None and declared_source not in RECOGNIZED_TERMINOLOGY_SOURCES:
        raise ValueError("declared source %r is not a recognised vocabulary" % (declared_source,))
    resolutions = []
    findings = []
    nonconforming = 0
    for term in terms:
        resolution = resolve_term(term)
        resolutions.append(resolution)
        if resolution["status"] == STATUS_DEPRECATED_SYNONYM:
            nonconforming += 1
            findings.append(
                "%s uses deprecated-synonym %s; the canonical term is %s"
                % (document_id, resolution["term"], resolution["canonical"])
            )
        elif resolution["status"] == STATUS_UNCATEGORIZED:
            nonconforming += 1
            findings.append(
                "%s uses uncategorized term %s, absent from the registry"
                % (document_id, resolution["term"])
            )
        elif declared_source is not None and resolution["source"] != declared_source:
            nonconforming += 1
            findings.append(
                "%s uses %s, defined by %s rather than the declared %s"
                % (document_id, resolution["term"], resolution["source"], declared_source)
            )
    return {
        "document_id": document_id,
        "term_count": len(terms),
        "nonconforming_count": nonconforming,
        "conforming_count": len(terms) - nonconforming,
        "resolutions": resolutions,
        "findings": findings,
        "conformant": not findings,
    }


def check_glossary_entry(term, entry, declared_source=None):
    """Hold one project-glossary entry against the canonical registry."""
    if not isinstance(entry, dict):
        raise ValueError("glossary entry for %r must be a mapping" % (term,))
    for field in ("source", "unit"):
        if field not in entry:
            raise ValueError("glossary entry for %r is missing %s" % (term, field))
        if not isinstance(entry[field], str) or not entry[field].strip():
            raise ValueError("glossary entry for %r has an empty %s" % (term, field))
    resolution = resolve_term(term)
    entry_source = entry["source"].strip().lower().replace("_", "-").replace(" ", "-")
    entry_unit = entry["unit"].strip()
    findings = []
    if resolution["status"] == STATUS_UNCATEGORIZED:
        findings.append(
            "project-glossary defines %s, which no recognised vocabulary carries"
            % resolution["term"]
        )
    elif resolution["status"] == STATUS_DEPRECATED_SYNONYM:
        findings.append(
            "project-glossary is keyed on deprecated-synonym %s; key it on %s"
            % (resolution["term"], resolution["canonical"])
        )
    else:
        if entry_source != resolution["source"]:
            findings.append(
                "project-glossary cites %s for %s; the registry defines it in %s"
                % (entry_source, resolution["term"], resolution["source"])
            )
        elif declared_source is not None and entry_source != declared_source:
            findings.append(
                "project-glossary entry %s sits outside the declared %s"
                % (resolution["term"], declared_source)
            )
        if entry_unit != resolution["unit"]:
            findings.append(
                "project-glossary expresses %s in %s; the registry uses %s"
                % (resolution["term"], entry_unit, resolution["unit"])
            )
    return {
        "term": resolution["term"],
        "canonical": resolution["canonical"],
        "findings": findings,
        "consistent": not findings,
    }


def terminology_conformance_ratio(term_count, nonconforming_count):
    """Fraction of term occurrences needing no rewrite, as one minus the rest."""
    for name, value in (
        ("term_count", term_count),
        ("nonconforming_count", nonconforming_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be an integer, got %r" % (name, value))
        if value < 0:
            raise ValueError("%s must not be negative, got %r" % (name, value))
    if term_count == 0:
        raise ValueError("term_count must be strictly positive to form a ratio")
    if nonconforming_count > term_count:
        raise ValueError(
            "nonconforming_count %d exceeds term_count %d"
            % (nonconforming_count, term_count)
        )
    return 1.0 - (float(nonconforming_count) / float(term_count))


def assess_terminology_conformance(ratio, threshold=MINIMUM_TERMINOLOGY_CONFORMANCE):
    """Hold a conformance ratio against the project threshold."""
    for name, value in (("ratio", ratio), ("threshold", threshold)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number, got %r" % (name, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite, got %r" % (name, value))
    ratio = float(ratio)
    threshold = float(threshold)
    if not 0.0 <= ratio <= 1.0:
        raise ValueError("ratio must lie between 0 and 1, got %r" % (ratio,))
    if not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must lie above 0 and at most 1, got %r" % (threshold,))
    meets = ratio >= threshold or math.isclose(
        ratio, threshold, rel_tol=0.0, abs_tol=CONFORMANCE_TOLERANCE
    )
    return {
        "ratio": ratio,
        "threshold": threshold,
        "meets_threshold": meets,
        "shortfall": 0.0 if meets else threshold - ratio,
    }


def review_project_terminology(project):
    """Run the clause 7.2.1.2.1 check over one project's documentation set."""
    if not isinstance(project, dict):
        raise ValueError("project record must be a mapping")
    for key in ("declared_sources", "documents"):
        if key not in project:
            raise ValueError("project record is missing required key %s" % key)
    documents = project["documents"]
    if isinstance(documents, dict) or not isinstance(documents, (list, tuple)):
        raise ValueError("project documents must be a list or tuple of document records")
    if not documents:
        raise ValueError("project must carry at least one document record")
    source_review = validate_terminology_source(project["declared_sources"])
    findings = list(source_review["findings"])
    declared_source = source_review["source"]

    document_reviews = []
    term_count = 0
    nonconforming_count = 0
    for document in documents:
        review = scan_document_terms(document, declared_source)
        document_reviews.append(review)
        findings.extend(review["findings"])
        term_count += review["term_count"]
        nonconforming_count += review["nonconforming_count"]

    glossary = project.get("glossary", {})
    if not isinstance(glossary, dict):
        raise ValueError("project glossary must be a mapping of term to entry")
    glossary_reviews = []
    for term in sorted(glossary):
        review = check_glossary_entry(term, glossary[term], declared_source)
        glossary_reviews.append(review)
        findings.extend(review["findings"])

    ratio = terminology_conformance_ratio(term_count, nonconforming_count)
    assessment = assess_terminology_conformance(
        ratio, project.get("conformance_threshold", MINIMUM_TERMINOLOGY_CONFORMANCE)
    )
    if not assessment["meets_threshold"]:
        findings.append(
            "terminology-conformance-ratio %.4f falls below the %.4f threshold"
            % (assessment["ratio"], assessment["threshold"])
        )
    return {
        "source": source_review,
        "documents": document_reviews,
        "glossary": glossary_reviews,
        "term_count": term_count,
        "nonconforming_count": nonconforming_count,
        "conformance": assessment,
        "findings": findings,
        "conformant": not findings,
    }
