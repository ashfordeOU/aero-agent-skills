#!/usr/bin/env python3
"""Netlist generation (ECSS-E-ST-20-40C clause 5.5.2).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The clause opens the detailed design phase with the synthesised netlist
and the record that goes with it. The netlist alone is not evidence of
anything; what makes it usable downstream is the record of what went in:

* sources and constraint files pinned to a revision, and the synthesis
  tool and the technology library pinned to a version. A run missing any
  one pin is not reproducible, and the gap is invisible at the time;
* a constraint set that is not empty. A run with no constraints
  completes and optimises against nothing;
* the outputs named, so the netlist and the reports can be found;
* the cells the run could not bind, reported rather than left in the
  log;
* utilisation as a ratio against a budget. A figure landing exactly on
  the budget is inside it, so the comparison absorbs representation
  error rather than rejecting a design that exactly fits;
* warnings grouped by category, with a disposition demanded on the
  categories that block.
"""

import math

BLOCKING = "blocking"
ADVISORY = "advisory"
INFORMATIONAL = "informational"
WARNING_CATEGORIES = (BLOCKING, ADVISORY, INFORMATIONAL)
CATEGORIES_NEEDING_DISPOSITION = (BLOCKING,)
_CATEGORY_ALIASES = {
    "blocking": BLOCKING,
    "error": BLOCKING,
    "critical": BLOCKING,
    "must fix": BLOCKING,
    "advisory": ADVISORY,
    "warning": ADVISORY,
    "review": ADVISORY,
    "informational": INFORMATIONAL,
    "info": INFORMATIONAL,
    "note": INFORMATIONAL,
}

REL_TOL = 1e-12
ABS_TOL = 1e-18

_FILE_KEYS = ("id", "revision")
_TOOL_KEYS = ("name", "version", "options")
_LIBRARY_KEYS = ("id", "version")
_OUTPUT_KEYS = ("netlist", "reports")
_UTILISATION_KEYS = ("resource", "used", "available", "budget")
_WARNING_KEYS = ("id", "category", "disposition", "subject")
_RUN_REQUIRED_KEYS = ("sources", "constraints", "tool", "technology_library", "outputs")
_RUN_OPTIONAL_KEYS = ("utilisation", "unresolved_cells", "warnings")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out <= 0.0:
        raise ValueError("%s must be greater than zero, got %g" % (name, out))
    return out


def _non_negative(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out < 0.0:
        raise ValueError("%s must not be negative, got %g" % (name, out))
    return out


def _fraction(name, value):
    out = _non_negative(name, value)
    if out > 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def normalize_warning_category(value):
    """Fold a synthesis warning category onto a recognised one."""
    key = " ".join(_text("warning category", value).lower().replace("_", " ").split())
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    raise ValueError(
        "unknown warning category %r; use one of %s"
        % (value, ", ".join(WARNING_CATEGORIES))
    )


def utilisation_ratio(used, available):
    """Fraction of an available resource the run consumed."""
    consumed = _non_negative("used", used)
    capacity = _positive("available", available)
    return consumed / capacity


def within_utilisation_budget(ratio, budget):
    """True when a utilisation ratio sits inside its budget, the budget included.

    A figure landing exactly on the budget is inside it, so representation
    error in a computed ratio cannot reject a design that exactly fits.
    """
    value = _non_negative("ratio", ratio)
    limit = _fraction("budget", budget)
    return value < limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_file_set(name, records):
    """Check a set of source or constraint files and return it resolved."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("%s must be a list" % name)
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("%s[%d] must be a mapping" % (name, index))
        unknown = sorted(set(record) - set(_FILE_KEYS))
        if unknown:
            raise ValueError(
                "%s[%d] has unknown keys: %s" % (name, index, ", ".join(unknown))
            )
        if "id" not in record:
            raise ValueError("%s[%d] missing key: id" % (name, index))
        file_id = _text("%s[%d].id" % (name, index), record["id"])
        if file_id in seen:
            raise ValueError("duplicate %s id %r" % (name, file_id))
        seen.add(file_id)
        resolved.append(
            {
                "id": file_id,
                "revision": _text(
                    "%s[%d].revision" % (name, index),
                    record.get("revision", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def validate_tool(record):
    """Check the synthesis tool block and return it resolved."""
    if not isinstance(record, dict):
        raise ValueError("tool must be a mapping of name, version and options")
    unknown = sorted(set(record) - set(_TOOL_KEYS))
    if unknown:
        raise ValueError("tool has unknown keys: %s" % ", ".join(unknown))
    if "name" not in record:
        raise ValueError("tool missing key: name")
    options = record.get("options", "")
    return {
        "name": _text("tool.name", record["name"]),
        "version": _text("tool.version", record.get("version", ""), allow_empty=True),
        "options": _text("tool.options", options, allow_empty=True),
    }


def validate_library(record):
    """Check the technology library block and return it resolved."""
    if not isinstance(record, dict):
        raise ValueError("technology_library must be a mapping of id and version")
    unknown = sorted(set(record) - set(_LIBRARY_KEYS))
    if unknown:
        raise ValueError("technology_library has unknown keys: %s" % ", ".join(unknown))
    if "id" not in record:
        raise ValueError("technology_library missing key: id")
    return {
        "id": _text("technology_library.id", record["id"]),
        "version": _text(
            "technology_library.version", record.get("version", ""), allow_empty=True
        ),
    }


def validate_outputs(record):
    """Check the outputs block and return the netlist and report names."""
    if not isinstance(record, dict):
        raise ValueError("outputs must be a mapping of netlist and reports")
    unknown = sorted(set(record) - set(_OUTPUT_KEYS))
    if unknown:
        raise ValueError("outputs has unknown keys: %s" % ", ".join(unknown))
    reports = record.get("reports", [])
    if isinstance(reports, str) or not isinstance(reports, (list, tuple)):
        raise ValueError("outputs.reports must be a list")
    named = []
    for index, report in enumerate(reports):
        text = _text("outputs.reports[%d]" % index, report)
        if text not in named:
            named.append(text)
    return {
        "netlist": _text("outputs.netlist", record.get("netlist", ""), allow_empty=True),
        "reports": named,
    }


def validate_utilisation(records):
    """Check the utilisation figures and return them resolved."""
    if records is None:
        return []
    if not isinstance(records, (list, tuple)):
        raise ValueError("utilisation must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("utilisation[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_UTILISATION_KEYS))
        if unknown:
            raise ValueError(
                "utilisation[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("resource", "used", "available"):
            if key not in record:
                raise ValueError("utilisation[%d] missing key: %s" % (index, key))
        resource = _text("utilisation[%d].resource" % index, record["resource"])
        if resource in seen:
            raise ValueError("duplicate utilisation resource %r" % resource)
        seen.add(resource)
        resolved.append(
            {
                "resource": resource,
                "used": _non_negative("utilisation[%d].used" % index, record["used"]),
                "available": _positive(
                    "utilisation[%d].available" % index, record["available"]
                ),
                "budget": _fraction(
                    "utilisation[%d].budget" % index, record.get("budget", 1.0)
                ),
            }
        )
    return resolved


def validate_warnings(records):
    """Check the warning list and return it resolved in declared order."""
    if records is None:
        return []
    if not isinstance(records, (list, tuple)):
        raise ValueError("warnings must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("warnings[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_WARNING_KEYS))
        if unknown:
            raise ValueError(
                "warnings[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "category"):
            if key not in record:
                raise ValueError("warnings[%d] missing key: %s" % (index, key))
        warning_id = _text("warnings[%d].id" % index, record["id"])
        if warning_id in seen:
            raise ValueError("duplicate warning id %r" % warning_id)
        seen.add(warning_id)
        resolved.append(
            {
                "id": warning_id,
                "category": normalize_warning_category(record["category"]),
                "disposition": _text(
                    "warnings[%d].disposition" % index,
                    record.get("disposition", ""),
                    allow_empty=True,
                ),
                "subject": _text(
                    "warnings[%d].subject" % index,
                    record.get("subject", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def unpinned_inputs(sources, constraints, tool, library):
    """Every input the run did not pin, as (kind, identifier)."""
    out = []
    for source in sources:
        if not source["revision"]:
            out.append(("source", source["id"]))
    for constraint in constraints:
        if not constraint["revision"]:
            out.append(("constraint", constraint["id"]))
    if not tool["version"]:
        out.append(("tool", tool["name"]))
    if not library["version"]:
        out.append(("technology-library", library["id"]))
    return out


def run_is_reproducible(sources, constraints, tool, library):
    """True when every input carries the pin a repeat run would need."""
    return not unpinned_inputs(sources, constraints, tool, library) and bool(
        sources and constraints
    )


def resources_over_budget(utilisation):
    """Resources whose utilisation exceeds its budget, as (resource, ratio, budget)."""
    out = []
    for figure in utilisation:
        ratio = utilisation_ratio(figure["used"], figure["available"])
        if not within_utilisation_budget(ratio, figure["budget"]):
            out.append((figure["resource"], ratio, figure["budget"]))
    return out


def undispositioned_warnings(warnings):
    """Warning ids in a blocking category that nobody answered."""
    return sorted(
        w["id"]
        for w in warnings
        if w["category"] in CATEGORIES_NEEDING_DISPOSITION and not w["disposition"]
    )


def evaluate_netlist_generation(run):
    """Full clause 5.5.2 assessment of one synthesis run and its record.

    Returns the utilisation reached, the findings, the reproducibility
    verdict and whether the record may be carried into netlist verification.
    """
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping describing the synthesis run")
    known = set(_RUN_REQUIRED_KEYS) | set(_RUN_OPTIONAL_KEYS)
    unknown = sorted(set(run) - known)
    if unknown:
        raise ValueError("unknown run keys: %s" % ", ".join(unknown))
    absent = [key for key in _RUN_REQUIRED_KEYS if key not in run]
    if absent:
        raise ValueError("run missing required keys: %s" % ", ".join(absent))

    sources = validate_file_set("sources", run["sources"])
    if not sources:
        raise ValueError("run must name at least one source file")
    constraints = validate_file_set("constraints", run["constraints"])
    tool = validate_tool(run["tool"])
    library = validate_library(run["technology_library"])
    outputs = validate_outputs(run["outputs"])
    utilisation = validate_utilisation(run.get("utilisation"))
    warnings = validate_warnings(run.get("warnings"))

    cells = run.get("unresolved_cells", [])
    if isinstance(cells, str) or not isinstance(cells, (list, tuple)):
        raise ValueError("unresolved_cells must be a list")
    unresolved = []
    for index, cell in enumerate(cells):
        text = _text("unresolved_cells[%d]" % index, cell)
        if text not in unresolved:
            unresolved.append(text)

    findings = []
    for kind, identifier in unpinned_inputs(sources, constraints, tool, library):
        findings.append(
            {
                "code": "input-not-pinned",
                "kind": kind,
                "input": identifier,
                "detail": "%s %s carries no revision or version, so the run cannot "
                "be repeated from the record" % (kind, identifier),
            }
        )

    if not constraints:
        findings.append(
            {
                "code": "run-without-constraints",
                "detail": "the run names no constraint file, so the tool optimised "
                "against nothing",
            }
        )

    if not outputs["netlist"]:
        findings.append(
            {
                "code": "netlist-output-not-recorded",
                "detail": "the record names no netlist, so the output of the run "
                "cannot be found",
            }
        )
    if not outputs["reports"]:
        findings.append(
            {
                "code": "synthesis-reports-not-recorded",
                "detail": "the record names no synthesis report, so the figures the "
                "run produced are not retained",
            }
        )

    for cell in unresolved:
        findings.append(
            {
                "code": "unresolved-cell-in-netlist",
                "cell": cell,
                "detail": "the run left %s unresolved, so the netlist has a hole in "
                "it" % cell,
            }
        )

    for resource, ratio, budget in resources_over_budget(utilisation):
        findings.append(
            {
                "code": "resource-over-budget",
                "resource": resource,
                "ratio": ratio,
                "budget": budget,
                "detail": "%s reaches %.1f %% of the device against a %.1f %% budget"
                % (resource, 100.0 * ratio, 100.0 * budget),
            }
        )

    for warning_id in undispositioned_warnings(warnings):
        findings.append(
            {
                "code": "blocking-warning-without-disposition",
                "warning": warning_id,
                "detail": "blocking warning %s carries no disposition, so the "
                "decision is deferred to whoever reads the log next" % warning_id,
            }
        )

    reproducible = run_is_reproducible(sources, constraints, tool, library)
    return {
        "reproducible": reproducible,
        "source_count": len(sources),
        "constraint_count": len(constraints),
        "unpinned_inputs": unpinned_inputs(sources, constraints, tool, library),
        "utilisation": {
            figure["resource"]: utilisation_ratio(figure["used"], figure["available"])
            for figure in utilisation
        },
        "resources_over_budget": resources_over_budget(utilisation),
        "unresolved_cells": unresolved,
        "undispositioned_warnings": undispositioned_warnings(warnings),
        "findings": findings,
        "acceptable": not findings,
    }
