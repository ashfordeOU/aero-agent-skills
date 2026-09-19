#!/usr/bin/env python3
"""Device pre-tailoring applicability matrix (ECSS-E-ST-20-40C 6.2).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
A pre-tailoring matrix is a ready-made table: one row per requirement, one
column per device category, one disposition in every cell. Its value is
that a project inherits an applicability decision it would otherwise make
by hand for each device, so the matrix is only usable when it is complete
and self-consistent:

* every requirement carries a disposition for EVERY declared category --
  an empty cell is the defect the matrix exists to prevent, and it is
  reported as a gap rather than silently read as not-applicable;
* a modified disposition without a modification note is unusable, because
  the reader cannot tell what the requirement became;
* a requirement not applicable to any category is dead weight in the
  table, and a category with no applicable requirement is a column
  nobody can build to -- both are matrix defects, not device properties;
* project tailoring applied on top is a DELTA against this baseline, so
  the removals it makes are listed and each one has to carry a
  justification. An unjustified removal is the way a pre-tailored
  baseline quietly becomes an arbitrary one.
"""

# The three dispositions a cell may carry, in their canonical spelling.
APPLICABLE = "applicable"
NOT_APPLICABLE = "not-applicable"
MODIFIED = "modified"
DISPOSITIONS = (APPLICABLE, NOT_APPLICABLE, MODIFIED)

# Accepted input spellings, folded to the canonical value above.
_DISPOSITION_ALIASES = {
    "applicable": APPLICABLE,
    "a": APPLICABLE,
    "yes": APPLICABLE,
    "not-applicable": NOT_APPLICABLE,
    "not applicable": NOT_APPLICABLE,
    "n/a": NOT_APPLICABLE,
    "na": NOT_APPLICABLE,
    "no": NOT_APPLICABLE,
    "modified": MODIFIED,
    "m": MODIFIED,
    "tailored": MODIFIED,
}

_SPEC_REQUIRED_KEYS = ("categories", "requirements")
_SPEC_OPTIONAL_KEYS = ("tailoring",)
_REQUIREMENT_KEYS = ("id", "title", "dispositions", "notes")
_TAILORING_KEYS = ("requirement_id", "disposition", "justification")


def normalize_disposition(value):
    """Fold an input spelling onto one of the three canonical dispositions."""
    if not isinstance(value, str):
        raise ValueError("disposition must be a string, got %r" % (value,))
    key = " ".join(value.strip().lower().split())
    if key in _DISPOSITION_ALIASES:
        return _DISPOSITION_ALIASES[key]
    raise ValueError(
        "unknown disposition %r; use one of %s" % (value, ", ".join(DISPOSITIONS))
    )


def normalize_category(value, index=0):
    """Check and trim one device category name."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("categories[%d] must be a non-empty string" % index)
    return value.strip()


def normalize_categories(categories):
    """Check the column set of the matrix and return it in declared order."""
    if not isinstance(categories, (list, tuple)):
        raise ValueError("categories must be a list or tuple of device categories")
    if len(categories) == 0:
        raise ValueError("categories must declare at least one device category")
    out = []
    for index, value in enumerate(categories):
        name = normalize_category(value, index)
        if name in out:
            raise ValueError("duplicate device category %r" % name)
        out.append(name)
    return out


def validate_requirement(requirement, categories, index=0):
    """Check one matrix row and return its id, title, cells and notes."""
    if not isinstance(requirement, dict):
        raise ValueError("requirements[%d] must be a mapping" % index)
    unknown = sorted(set(requirement) - set(_REQUIREMENT_KEYS))
    if unknown:
        raise ValueError(
            "requirements[%d] has unknown keys: %s" % (index, ", ".join(unknown))
        )
    for key in ("id", "dispositions"):
        if key not in requirement:
            raise ValueError("requirements[%d] missing key: %s" % (index, key))
    req_id = requirement["id"]
    if not isinstance(req_id, str) or not req_id.strip():
        raise ValueError("requirements[%d].id must be a non-empty string" % index)
    req_id = req_id.strip()
    title = requirement.get("title", "")
    if not isinstance(title, str):
        raise ValueError("requirements[%d].title must be a string" % index)
    cells = requirement["dispositions"]
    if not isinstance(cells, dict):
        raise ValueError(
            "requirements[%d].dispositions must be a mapping of category to "
            "disposition" % index
        )
    stray = sorted(set(cells) - set(categories))
    if stray:
        raise ValueError(
            "requirements[%d] (%s) dispositions name undeclared categories: %s"
            % (index, req_id, ", ".join(stray))
        )
    resolved = {}
    for category, value in cells.items():
        resolved[category] = normalize_disposition(value)
    notes = requirement.get("notes", {})
    if not isinstance(notes, dict):
        raise ValueError("requirements[%d].notes must be a mapping" % index)
    stray_notes = sorted(set(notes) - set(categories))
    if stray_notes:
        raise ValueError(
            "requirements[%d] (%s) notes name undeclared categories: %s"
            % (index, req_id, ", ".join(stray_notes))
        )
    return req_id, title.strip(), resolved, notes


def build_matrix(categories, requirements):
    """Resolve the declared rows and columns into a checked matrix."""
    columns = normalize_categories(categories)
    if not isinstance(requirements, (list, tuple)):
        raise ValueError("requirements must be a list or tuple of matrix rows")
    if len(requirements) == 0:
        raise ValueError("requirements must hold at least one row")
    rows = []
    seen = set()
    for index, requirement in enumerate(requirements):
        req_id, title, cells, notes = validate_requirement(
            requirement, columns, index
        )
        if req_id in seen:
            raise ValueError("duplicate requirement id %r" % req_id)
        seen.add(req_id)
        rows.append(
            {"id": req_id, "title": title, "dispositions": cells, "notes": notes}
        )
    return {"categories": columns, "rows": rows}


def matrix_gaps(matrix):
    """Cells the matrix never filled in, as (requirement id, category) pairs."""
    gaps = []
    for row in matrix["rows"]:
        for category in matrix["categories"]:
            if category not in row["dispositions"]:
                gaps.append((row["id"], category))
    return gaps


def missing_modification_notes(matrix):
    """Modified cells with no note saying what the requirement became."""
    out = []
    for row in matrix["rows"]:
        for category, disposition in row["dispositions"].items():
            if disposition != MODIFIED:
                continue
            note = row["notes"].get(category, "")
            if not isinstance(note, str) or not note.strip():
                out.append((row["id"], category))
    return sorted(out)


def applicable_requirements(matrix, category):
    """Requirement ids a device in this category has to answer."""
    if category not in matrix["categories"]:
        raise ValueError("undeclared device category %r" % category)
    return sorted(
        row["id"]
        for row in matrix["rows"]
        if row["dispositions"].get(category) in (APPLICABLE, MODIFIED)
    )


def coverage_summary(matrix):
    """Per-category counts and the applicable fraction of the whole table."""
    total = len(matrix["rows"])
    summary = {}
    for category in matrix["categories"]:
        counts = {APPLICABLE: 0, NOT_APPLICABLE: 0, MODIFIED: 0, "unset": 0}
        for row in matrix["rows"]:
            counts[row["dispositions"].get(category, "unset")] += 1
        applicable = counts[APPLICABLE] + counts[MODIFIED]
        summary[category] = {
            "applicable": applicable,
            "not_applicable": counts[NOT_APPLICABLE],
            "modified": counts[MODIFIED],
            "unset": counts["unset"],
            "total": total,
            "applicable_fraction": applicable / total,
        }
    return summary


def orphan_requirements(matrix):
    """Rows that no declared category has to answer."""
    return sorted(
        row["id"]
        for row in matrix["rows"]
        if not any(
            disposition in (APPLICABLE, MODIFIED)
            for disposition in row["dispositions"].values()
        )
    )


def empty_categories(matrix):
    """Columns with nothing applicable in them at all."""
    return sorted(
        category
        for category in matrix["categories"]
        if not applicable_requirements(matrix, category)
    )


def _validate_tailoring_entry(entry, matrix, category, index):
    if not isinstance(entry, dict):
        raise ValueError("tailoring[%s][%d] must be a mapping" % (category, index))
    unknown = sorted(set(entry) - set(_TAILORING_KEYS))
    if unknown:
        raise ValueError(
            "tailoring[%s][%d] has unknown keys: %s"
            % (category, index, ", ".join(unknown))
        )
    for key in ("requirement_id", "disposition"):
        if key not in entry:
            raise ValueError(
                "tailoring[%s][%d] missing key: %s" % (category, index, key)
            )
    req_id = entry["requirement_id"]
    if not isinstance(req_id, str) or not req_id.strip():
        raise ValueError(
            "tailoring[%s][%d].requirement_id must be a non-empty string"
            % (category, index)
        )
    req_id = req_id.strip()
    known = {row["id"] for row in matrix["rows"]}
    if req_id not in known:
        raise ValueError(
            "tailoring[%s][%d] names requirement %r which is not in the matrix"
            % (category, index, req_id)
        )
    disposition = normalize_disposition(entry["disposition"])
    justification = entry.get("justification", "")
    if not isinstance(justification, str):
        raise ValueError(
            "tailoring[%s][%d].justification must be a string" % (category, index)
        )
    return req_id, disposition, justification.strip()


def apply_tailoring(matrix, category, entries):
    """Overlay a project delta on the baseline column and report the change.

    Returns the resulting applicable set, the requirements the delta added
    and removed, and the removals that carry no justification.
    """
    baseline = set(applicable_requirements(matrix, category))
    if entries is None:
        entries = []
    if not isinstance(entries, (list, tuple)):
        raise ValueError("tailoring[%s] must be a list of delta entries" % category)
    resulting = set(baseline)
    unjustified = []
    for index, entry in enumerate(entries):
        req_id, disposition, justification = _validate_tailoring_entry(
            entry, matrix, category, index
        )
        if disposition in (APPLICABLE, MODIFIED):
            resulting.add(req_id)
        else:
            resulting.discard(req_id)
            if req_id in baseline and not justification:
                unjustified.append(req_id)
    added = sorted(resulting - baseline)
    removed = sorted(baseline - resulting)
    reduction = (len(removed) / len(baseline)) if baseline else 0.0
    return {
        "baseline_applicable": sorted(baseline),
        "resulting_applicable": sorted(resulting),
        "added": added,
        "removed": removed,
        "unjustified_removals": sorted(unjustified),
        "reduction_fraction": reduction,
    }


def evaluate_pre_tailoring_matrix(spec):
    """Full clause 6.2 assessment of one pre-tailoring applicability table.

    Returns the per-category applicable sets, the coverage summary, any
    project tailoring delta, the findings and the verdict.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping of categories and requirements")
    known = set(_SPEC_REQUIRED_KEYS) | set(_SPEC_OPTIONAL_KEYS)
    unknown = sorted(set(spec) - known)
    if unknown:
        raise ValueError("unknown spec keys: %s" % ", ".join(unknown))
    missing = [key for key in _SPEC_REQUIRED_KEYS if key not in spec]
    if missing:
        raise ValueError("spec missing required keys: %s" % ", ".join(missing))

    matrix = build_matrix(spec["categories"], spec["requirements"])
    findings = []
    gaps = matrix_gaps(matrix)
    if gaps:
        findings.append(
            {
                "code": "matrix-cell-unset",
                "cells": gaps,
                "detail": "%d cell(s) carry no disposition, so the table cannot be "
                "read as pre-tailored" % len(gaps),
            }
        )
    notes_missing = missing_modification_notes(matrix)
    if notes_missing:
        findings.append(
            {
                "code": "modified-cell-without-note",
                "cells": notes_missing,
                "detail": "%d modified cell(s) do not say what the requirement "
                "became" % len(notes_missing),
            }
        )
    orphans = orphan_requirements(matrix)
    if orphans:
        findings.append(
            {
                "code": "requirement-applicable-to-no-category",
                "requirements": orphans,
                "detail": "rows %s apply to nothing in the table" % ", ".join(orphans),
            }
        )
    barren = empty_categories(matrix)
    if barren:
        findings.append(
            {
                "code": "category-with-no-applicable-requirement",
                "categories": barren,
                "detail": "categories %s inherit no requirement at all"
                % ", ".join(barren),
            }
        )

    tailoring = spec.get("tailoring", {}) or {}
    if not isinstance(tailoring, dict):
        raise ValueError("tailoring must be a mapping of category to delta entries")
    stray = sorted(set(tailoring) - set(matrix["categories"]))
    if stray:
        raise ValueError(
            "tailoring names undeclared categories: %s" % ", ".join(stray)
        )
    deltas = {}
    for category, entries in tailoring.items():
        delta = apply_tailoring(matrix, category, entries)
        deltas[category] = delta
        if delta["unjustified_removals"]:
            findings.append(
                {
                    "code": "unjustified-tailoring-removal",
                    "category": category,
                    "requirements": delta["unjustified_removals"],
                    "detail": "%s drops %s from the pre-tailored baseline with no "
                    "justification"
                    % (category, ", ".join(delta["unjustified_removals"])),
                }
            )

    return {
        "categories": matrix["categories"],
        "requirement_count": len(matrix["rows"]),
        "applicable_by_category": {
            category: applicable_requirements(matrix, category)
            for category in matrix["categories"]
        },
        "coverage": coverage_summary(matrix),
        "tailoring_delta": deltas,
        "findings": findings,
        "usable": not findings,
    }
