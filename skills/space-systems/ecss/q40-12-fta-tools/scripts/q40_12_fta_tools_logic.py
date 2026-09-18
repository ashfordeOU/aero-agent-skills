#!/usr/bin/env python3
"""Acceptance of a software tool used to support fault tree analysis.

Anchor: ECSS-Q-ST-40-12C clause 5.1.3, on the software tools that
support the adopted IEC 61025 method. The steps below are a paraphrase
into implementable form; no standard text is reproduced.

A tool is not accepted because it is popular. It is accepted against
four questions asked in order: does it compute what this analysis
actually needs, does it reproduce reference results inside a declared
tolerance, does it give the same answer twice on the same model, and
does the model survive leaving the tool and coming back. The effort
behind those answers scales with the consequence of the result the tool
produces, not with the size of the tool.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TOOL_CAPABILITIES = (
    "minimal-cut-set-expansion",
    "exact-quantification",
    "rare-event-quantification",
    "voting-gate-support",
    "importance-measures",
    "sensitivity-sweep",
    "common-cause-modelling",
    "uncertainty-propagation",
)

EXCHANGE_FORMATS = (
    "neutral-model-exchange",
    "vendor-native-model",
    "cut-set-table-export",
    "human-readable-report",
)

RESULT_CRITICALITY = ("catastrophic", "critical", "major", "minor")

QUALIFICATION_REQUIRED = "tool-qualification-required"
VALIDATION_BY_BENCHMARK = "validation-by-benchmark"
USE_WITH_INDEPENDENT_CHECK = "use-with-independent-check"

TOOL_ACCEPTABLE = "tool-acceptable"
TOOL_RESTRICTED = "tool-acceptable-with-restrictions"
TOOL_NOT_ACCEPTABLE = "tool-not-acceptable"

DEFAULT_BENCHMARK_TOLERANCE = 1.0e-3
DEFAULT_REPEATABILITY_TOLERANCE = 0.0

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A relative error is a quotient of differences, so a result that sits
    exactly on its tolerance can land a few units in the last place
    above it. The tolerance is never relaxed; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _relative_error(observed, reference):
    observed = _require_number("observed value", observed)
    reference = _require_number("reference value", reference)
    if reference == 0.0:
        return abs(observed)
    return abs(observed - reference) / abs(reference)


def validate_tool(tool):
    """Normalize a tool declaration before anything is graded against it."""
    if not isinstance(tool, dict):
        raise ValueError("tool must be a mapping, got %r" % (tool,))
    name = _require_text("name", tool.get("name"))
    version = _require_text("version", tool.get("version"))
    capabilities = tool.get("capabilities")
    if not isinstance(capabilities, (list, tuple, set, frozenset)) or not capabilities:
        raise ValueError("tool needs a non-empty capabilities sequence")
    resolved = []
    for item in capabilities:
        resolved.append(_require_choice("capability", item, TOOL_CAPABILITIES))
    formats = tool.get("exchange_formats", ())
    if not isinstance(formats, (list, tuple, set, frozenset)):
        raise ValueError("exchange_formats must be a sequence, got %r" % (formats,))
    resolved_formats = []
    for item in formats:
        resolved_formats.append(_require_choice("exchange format", item, EXCHANGE_FORMATS))
    return {
        "name": name,
        "version": version,
        "capabilities": tuple(sorted(set(resolved))),
        "exchange_formats": tuple(sorted(set(resolved_formats))),
        "under_configuration_control": _require_bool(
            "under_configuration_control", tool.get("under_configuration_control")
        ),
        "deterministic": _require_bool("deterministic", tool.get("deterministic")),
    }


def capability_gap(tool, required_capabilities):
    """Capabilities the analysis needs that the tool does not offer."""
    tool = validate_tool(tool)
    if not isinstance(required_capabilities, (list, tuple, set, frozenset)):
        raise ValueError(
            "required_capabilities must be a sequence, got %r"
            % (required_capabilities,)
        )
    needed = set()
    for item in required_capabilities:
        needed.add(_require_choice("required capability", item, TOOL_CAPABILITIES))
    return tuple(sorted(needed - set(tool["capabilities"])))


def format_gap(required_formats, supported_formats):
    """Exchange formats the project needs that the tool does not write."""
    for label, value in (
        ("required_formats", required_formats),
        ("supported_formats", supported_formats),
    ):
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise ValueError("%s must be a sequence, got %r" % (label, value))
    needed = {
        _require_choice("required format", item, EXCHANGE_FORMATS)
        for item in required_formats
    }
    offered = {
        _require_choice("supported format", item, EXCHANGE_FORMATS)
        for item in supported_formats
    }
    return tuple(sorted(needed - offered))


def grade_benchmark(cases, tolerance=DEFAULT_BENCHMARK_TOLERANCE):
    """Grade tool results against reference values inside a tolerance."""
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence, got %r" % (cases,))
    tolerance = _require_non_negative("tolerance", tolerance)
    graded = []
    seen = set()
    worst = 0.0
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("every benchmark case must be a mapping")
        case_id = _require_text("case id", case.get("case"))
        if case_id in seen:
            raise ValueError("benchmark case %r appears twice" % case_id)
        seen.add(case_id)
        error = _relative_error(case.get("tool_value"), case.get("reference_value"))
        within = _at_most(error, tolerance)
        worst = max(worst, error)
        graded.append(
            {
                "case": case_id,
                "relative_error": error,
                "verdict": "within-tolerance" if within else "out-of-tolerance",
            }
        )
    graded.sort(key=lambda item: (-item["relative_error"], item["case"]))
    failed = tuple(
        item["case"] for item in graded if item["verdict"] == "out-of-tolerance"
    )
    return {
        "cases": tuple(graded),
        "worst_relative_error": worst,
        "failed": failed,
        "verdict": "benchmark-clean" if not failed else "benchmark-shortfall",
    }


def repeatability_deviation(first_run, second_run,
                            tolerance=DEFAULT_REPEATABILITY_TOLERANCE):
    """Largest relative deviation between two runs of the same model."""
    for label, value in (("first_run", first_run), ("second_run", second_run)):
        if not isinstance(value, dict) or not value:
            raise ValueError("%s must be a non-empty mapping, got %r" % (label, value))
    tolerance = _require_non_negative("tolerance", tolerance)
    if set(first_run) != set(second_run):
        raise ValueError(
            "the two runs report different quantities: %s"
            % ", ".join(sorted(set(first_run) ^ set(second_run)))
        )
    worst = 0.0
    worst_key = None
    for key in sorted(first_run):
        error = _relative_error(second_run[key], first_run[key])
        if error > worst:
            worst = error
            worst_key = key
    return {
        "worst_relative_deviation": worst,
        "worst_quantity": worst_key,
        "verdict": (
            "repeatable" if _at_most(worst, tolerance) else "not-repeatable"
        ),
    }


def exchange_round_trip(exported_model, reimported_model):
    """Compare a model before export with the same model after re-import."""
    for label, value in (
        ("exported_model", exported_model),
        ("reimported_model", reimported_model),
    ):
        if not isinstance(value, dict) or not value:
            raise ValueError("%s must be a non-empty mapping, got %r" % (label, value))
    lost = tuple(sorted(set(exported_model) - set(reimported_model)))
    added = tuple(sorted(set(reimported_model) - set(exported_model)))
    changed = []
    for key in sorted(set(exported_model) & set(reimported_model)):
        before = exported_model[key]
        after = reimported_model[key]
        if _is_finite_number(before) and _is_finite_number(after):
            if not math.isclose(float(before), float(after),
                                rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
                changed.append(key)
        elif before != after:
            changed.append(key)
    faithful = not lost and not added and not changed
    return {
        "lost_keys": lost,
        "added_keys": added,
        "changed_keys": tuple(changed),
        "faithful": faithful,
        "verdict": "round-trip-faithful" if faithful else "round-trip-lossy",
    }


def qualification_level(result_criticality, independently_reproduced,
                        benchmark_clean):
    """Effort the result's consequence demands behind the tool."""
    _require_choice("result_criticality", result_criticality, RESULT_CRITICALITY)
    independently_reproduced = _require_bool(
        "independently_reproduced", independently_reproduced
    )
    benchmark_clean = _require_bool("benchmark_clean", benchmark_clean)
    if result_criticality in ("catastrophic", "critical"):
        if independently_reproduced and benchmark_clean:
            return USE_WITH_INDEPENDENT_CHECK
        return QUALIFICATION_REQUIRED
    if benchmark_clean:
        return VALIDATION_BY_BENCHMARK
    if independently_reproduced:
        return USE_WITH_INDEPENDENT_CHECK
    return QUALIFICATION_REQUIRED


def evaluate_fta_tool(case):
    """Full clause 5.1.3 tool acceptance with restrictions and findings."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    tool = validate_tool(case.get("tool"))
    required = case.get("required_capabilities", ())
    missing = capability_gap(case.get("tool"), required)
    benchmark = grade_benchmark(
        case.get("benchmark_cases"),
        case.get("benchmark_tolerance", DEFAULT_BENCHMARK_TOLERANCE),
    )
    repeatability = repeatability_deviation(
        case.get("first_run"),
        case.get("second_run"),
        case.get("repeatability_tolerance", DEFAULT_REPEATABILITY_TOLERANCE),
    )
    round_trip = exchange_round_trip(
        case.get("exported_model"), case.get("reimported_model")
    )
    formats_missing = format_gap(
        case.get("required_formats", ()), tool["exchange_formats"]
    )
    criticality = _require_choice(
        "result_criticality", case.get("result_criticality"), RESULT_CRITICALITY
    )
    level = qualification_level(
        criticality,
        _require_bool(
            "independently_reproduced", case.get("independently_reproduced")
        ),
        benchmark["verdict"] == "benchmark-clean",
    )
    findings = []
    restrictions = []
    if missing:
        findings.append(
            "the tool does not compute: %s" % ", ".join(missing)
        )
    if benchmark["failed"]:
        findings.append(
            "benchmark cases outside tolerance: %s" % ", ".join(benchmark["failed"])
        )
    if repeatability["verdict"] != "repeatable":
        findings.append(
            "a rerun of the same model moved %s by %.3g"
            % (repeatability["worst_quantity"],
               repeatability["worst_relative_deviation"])
        )
    if not round_trip["faithful"]:
        findings.append(
            "the model did not survive an export and re-import: lost %s, "
            "changed %s"
            % (
                ", ".join(round_trip["lost_keys"]) or "nothing",
                ", ".join(round_trip["changed_keys"]) or "nothing",
            )
        )
    if formats_missing:
        restrictions.append(
            "results have to be converted by hand into: %s"
            % ", ".join(formats_missing)
        )
    if not tool["under_configuration_control"]:
        restrictions.append(
            "the tool version is not under configuration control, so a result "
            "cannot be tied to the build that produced it"
        )
    if not tool["deterministic"]:
        restrictions.append(
            "the tool is not declared deterministic, so every reported value "
            "needs its run recorded with it"
        )
    if level == QUALIFICATION_REQUIRED:
        restrictions.append(
            "the result consequence demands a tool qualification record before "
            "the output is used as evidence"
        )
    blocking = bool(missing) or bool(benchmark["failed"]) or not round_trip["faithful"]
    if blocking:
        verdict = TOOL_NOT_ACCEPTABLE
    elif restrictions or repeatability["verdict"] != "repeatable":
        verdict = TOOL_RESTRICTED
    else:
        verdict = TOOL_ACCEPTABLE
    return {
        "tool": "%s %s" % (tool["name"], tool["version"]),
        "capability_gap": missing,
        "benchmark": benchmark,
        "repeatability": repeatability,
        "round_trip": round_trip,
        "format_gap": formats_missing,
        "qualification_level": level,
        "restrictions": tuple(restrictions),
        "findings": findings,
        "verdict": verdict,
    }
