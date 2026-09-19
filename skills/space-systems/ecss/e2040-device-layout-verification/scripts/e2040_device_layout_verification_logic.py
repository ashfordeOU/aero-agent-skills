#!/usr/bin/env python3
"""Device layout verification (ECSS-E-ST-20-40C 5.6.3).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
Layout verification is the comprehensive check of the physical layout and
of the netlists taken back out of it, run against the checks the
verification plan nominated. The interesting failures are never that a
check reported violations -- that is the check working. They are:

* a planned check that was never run. The campaign summary reads clean
  because a check that did not execute reports nothing;
* a check run against a netlist view that cannot answer it. Static timing
  taken on the pre-layout netlist is a real run producing real numbers
  about a device that does not exist yet, and it looks identical in a
  results table to the post-layout run that was supposed to happen;
* a violation carried by a waiver with no rationale or no approver. The
  count reaches zero and nobody can say later why it was allowed.

Coverage is therefore the fraction of planned checks that were executed
on a view able to answer them, and a coverage figure landing exactly on
its goal meets it -- the comparison absorbs representation error rather
than failing a campaign that is exactly on target.
"""

import math

# Checks a layout verification plan can nominate.
CHECK_KINDS = (
    "design-rule-check",
    "layout-versus-schematic",
    "electrical-rule-check",
    "antenna-check",
    "static-timing-analysis",
    "power-integrity-analysis",
    "formal-equivalence",
    "post-layout-simulation",
)

_CHECK_ALIASES = {
    "design-rule-check": "design-rule-check",
    "drc": "design-rule-check",
    "layout-versus-schematic": "layout-versus-schematic",
    "lvs": "layout-versus-schematic",
    "electrical-rule-check": "electrical-rule-check",
    "erc": "electrical-rule-check",
    "antenna-check": "antenna-check",
    "antenna": "antenna-check",
    "static-timing-analysis": "static-timing-analysis",
    "sta": "static-timing-analysis",
    "post-layout-timing": "static-timing-analysis",
    "power-integrity-analysis": "power-integrity-analysis",
    "ir-drop": "power-integrity-analysis",
    "formal-equivalence": "formal-equivalence",
    "equivalence-check": "formal-equivalence",
    "post-layout-simulation": "post-layout-simulation",
    "back-annotated-simulation": "post-layout-simulation",
}

# Netlist views a check can be run against.
NETLIST_VIEWS = ("pre-layout", "post-layout", "extracted")

# Views able to answer each check. A view outside this set produces real
# numbers about the wrong device.
SUITABLE_VIEWS = {
    "design-rule-check": ("post-layout", "extracted"),
    "layout-versus-schematic": ("post-layout", "extracted"),
    "electrical-rule-check": ("post-layout", "extracted"),
    "antenna-check": ("post-layout", "extracted"),
    "static-timing-analysis": ("extracted",),
    "power-integrity-analysis": ("extracted",),
    "formal-equivalence": ("pre-layout", "post-layout"),
    "post-layout-simulation": ("extracted",),
}

# Outcomes an executed check can report.
OUTCOMES = ("clean", "violations", "aborted")

REL_TOL = 1e-12
ABS_TOL = 1e-18

_EXECUTION_KEYS = ("check", "view", "outcome", "violations", "waivers")
_WAIVER_KEYS = ("id", "rationale", "approver")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def normalize_check(value):
    """Fold a check name onto one of the recognised layout checks."""
    key = " ".join(_text("check", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    if key in _CHECK_ALIASES:
        return _CHECK_ALIASES[key]
    raise ValueError(
        "unknown layout check %r; use one of %s" % (value, ", ".join(CHECK_KINDS))
    )


def normalize_view(value):
    """Fold a netlist view onto one of the recognised views."""
    key = " ".join(_text("view", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    aliases = {
        "pre-layout": "pre-layout",
        "synthesised": "pre-layout",
        "synthesized": "pre-layout",
        "post-layout": "post-layout",
        "routed": "post-layout",
        "extracted": "extracted",
        "parasitic-annotated": "extracted",
        "back-annotated": "extracted",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown netlist view %r; use one of %s" % (value, ", ".join(NETLIST_VIEWS))
    )


def suitable_views_for(check):
    """Netlist views able to answer this check."""
    return SUITABLE_VIEWS[normalize_check(check)]


def view_can_answer(check, view):
    """True when this netlist view can answer this check."""
    return normalize_view(view) in suitable_views_for(check)


def validate_plan(entries):
    """Check the nominated check list and return it folded, without repeats."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("the verification plan must be a list of checks")
    resolved = []
    for index, entry in enumerate(entries):
        check = normalize_check(_text("plan[%d]" % index, entry))
        if check in resolved:
            raise ValueError("check %r is nominated twice in the plan" % check)
        resolved.append(check)
    return resolved


def validate_waivers(entries, where):
    """Check the waivers carried by one execution."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("%s.waivers must be a list" % where)
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("%s.waivers[%d] must be a mapping" % (where, index))
        unknown = sorted(set(entry) - set(_WAIVER_KEYS))
        if unknown:
            raise ValueError(
                "%s.waivers[%d] has unknown keys: %s"
                % (where, index, ", ".join(unknown))
            )
        if "id" not in entry:
            raise ValueError("%s.waivers[%d] missing key: id" % (where, index))
        waiver_id = _text("%s.waivers[%d].id" % (where, index), entry["id"])
        if waiver_id in seen:
            raise ValueError("duplicate waiver id %r on %s" % (waiver_id, where))
        seen.add(waiver_id)
        resolved.append(
            {
                "id": waiver_id,
                "rationale": _text(
                    "%s.waivers[%d].rationale" % (where, index),
                    entry.get("rationale", ""),
                    allow_empty=True,
                ),
                "approver": _text(
                    "%s.waivers[%d].approver" % (where, index),
                    entry.get("approver", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def validate_executions(entries):
    """Check the executed runs and return them keyed by folded check name."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("executions must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("executions[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_EXECUTION_KEYS))
        if unknown:
            raise ValueError(
                "executions[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("check", "view", "outcome"):
            if key not in entry:
                raise ValueError("executions[%d] missing key: %s" % (index, key))
        check = normalize_check(entry["check"])
        if check in resolved:
            raise ValueError("check %r was executed twice" % check)
        outcome = " ".join(
            _text("executions[%d].outcome" % index, entry["outcome"]).lower().split()
        )
        if outcome not in OUTCOMES:
            raise ValueError(
                "unknown outcome %r; use one of %s" % (outcome, ", ".join(OUTCOMES))
            )
        violations = _count(
            "executions[%d].violations" % index, entry.get("violations", 0)
        )
        if outcome == "violations" and violations == 0:
            raise ValueError(
                "executions[%d] reports violations and counts none" % index
            )
        resolved[check] = {
            "check": check,
            "view": normalize_view(entry["view"]),
            "outcome": outcome,
            "violations": violations,
            "waivers": validate_waivers(
                entry.get("waivers", []), "executions[%d]" % index
            ),
        }
    return resolved


def verification_coverage(plan, executions):
    """Fraction of planned checks executed on a view able to answer them."""
    if not plan:
        raise ValueError("coverage needs at least one planned check")
    answered = 0
    for check in plan:
        run = executions.get(check)
        if run is None or run["outcome"] == "aborted":
            continue
        if view_can_answer(check, run["view"]):
            answered += 1
    return answered / len(plan)


def meets_goal(achieved, goal):
    """True when coverage reaches its goal, exact landings included."""
    achieved = _fraction("achieved", achieved)
    goal = _fraction("goal", goal)
    return achieved > goal or math.isclose(
        achieved, goal, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def evaluate_layout_verification(plan, executions, coverage_goal=1.0):
    """Full 5.6.3 assessment of one device layout verification campaign.

    Returns the coverage reached, the unresolved violation count, the
    findings and the verdict.
    """
    planned = validate_plan(plan)
    if not planned:
        raise ValueError("the verification plan must nominate at least one check")
    runs = validate_executions(executions)
    coverage_goal = _fraction("coverage_goal", coverage_goal)

    findings = []
    for stray in sorted(set(runs) - set(planned)):
        findings.append(
            {
                "code": "check-executed-outside-the-plan",
                "check": stray,
                "detail": "%s was run and the verification plan does not nominate "
                "it" % stray,
            }
        )

    unresolved = 0
    for check in planned:
        run = runs.get(check)
        if run is None:
            findings.append(
                {
                    "code": "planned-check-not-run",
                    "check": check,
                    "detail": "%s is nominated by the plan and was never executed, "
                    "so it reports nothing" % check,
                }
            )
            continue
        if run["outcome"] == "aborted":
            findings.append(
                {
                    "code": "check-aborted",
                    "check": check,
                    "detail": "%s aborted, so its result is absent rather than "
                    "clean" % check,
                }
            )
        if not view_can_answer(check, run["view"]):
            findings.append(
                {
                    "code": "check-run-on-unsuitable-netlist-view",
                    "check": check,
                    "view": run["view"],
                    "detail": "%s was run on the %s netlist; it can only be "
                    "answered on %s"
                    % (check, run["view"], ", ".join(suitable_views_for(check))),
                }
            )
        waived = len(run["waivers"])
        if waived > run["violations"]:
            raise ValueError(
                "check %r carries %d waivers against %d violations"
                % (check, waived, run["violations"])
            )
        for waiver in run["waivers"]:
            if not waiver["rationale"]:
                findings.append(
                    {
                        "code": "waiver-without-rationale",
                        "check": check,
                        "waiver": waiver["id"],
                        "detail": "waiver %s on %s records no rationale"
                        % (waiver["id"], check),
                    }
                )
            if not waiver["approver"]:
                findings.append(
                    {
                        "code": "waiver-without-approver",
                        "check": check,
                        "waiver": waiver["id"],
                        "detail": "waiver %s on %s names no approver"
                        % (waiver["id"], check),
                    }
                )
        remaining = run["violations"] - waived
        unresolved += remaining
        if remaining > 0:
            findings.append(
                {
                    "code": "violations-neither-fixed-nor-waived",
                    "check": check,
                    "remaining": remaining,
                    "detail": "%s leaves %d violations neither fixed nor waived"
                    % (check, remaining),
                }
            )

    coverage = verification_coverage(planned, runs)
    if not meets_goal(coverage, coverage_goal):
        findings.append(
            {
                "code": "verification-coverage-goal-missed",
                "achieved": coverage,
                "goal": coverage_goal,
                "detail": "the campaign answers %.1f %% of the plan against a "
                "%.1f %% goal" % (100.0 * coverage, 100.0 * coverage_goal),
            }
        )

    return {
        "planned_checks": planned,
        "executed_checks": sorted(runs),
        "coverage": coverage,
        "unresolved_violations": unresolved,
        "checks_not_run": sorted(c for c in planned if c not in runs),
        "findings": findings,
        "layout_verified": not findings,
    }
