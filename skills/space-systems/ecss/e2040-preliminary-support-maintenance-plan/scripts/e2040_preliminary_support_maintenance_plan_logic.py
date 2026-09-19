#!/usr/bin/env python3
"""Preliminary support and maintenance plan (ECSS-E-ST-20-40C 5.2.5).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The plan is written while the device is still being defined and it has to
answer three questions about the years after delivery:

* what is maintained, and how often. A task is defined by its interval,
  and an interval longer than the support window means the task never
  falls due -- it reads as diligence and buys nothing;
* what is held as spares. The demand is computed from the total
  operating hours across the units in service divided by the mean time
  between failures, so a part failing once every two missions has a
  fractional demand that is still a demand;
* which parts stop being available before the obligation ends. A part
  whose end of life falls inside the support window needs a mitigation
  behind it, and a lifetime buy only counts as one when the quantity
  covers the demand from the end-of-life date to the end of the window.

Every comparison here is against a computed division, so each one
absorbs representation error at the bound rather than failing a plan
that is precisely sufficient.
"""

import math

MONTHS_PER_YEAR = 12.0

# What can be done about a part that goes obsolete inside the window.
MITIGATIONS = ("lifetime-buy", "alternate-source", "planned-redesign", "none")
_MITIGATION_ALIASES = {
    "lifetime-buy": "lifetime-buy",
    "last-time-buy": "lifetime-buy",
    "bridge-buy": "lifetime-buy",
    "alternate-source": "alternate-source",
    "second-source": "alternate-source",
    "alternative-part": "alternate-source",
    "planned-redesign": "planned-redesign",
    "redesign": "planned-redesign",
    "none": "none",
    "unmitigated": "none",
    "not addressed": "none",
}

# Skill levels a maintenance task can call for.
MAINTENANCE_SKILLS = ("operator", "technician", "specialist")
_SKILL_ALIASES = {
    "operator": "operator",
    "user": "operator",
    "technician": "technician",
    "maintainer": "technician",
    "specialist": "specialist",
    "manufacturer": "specialist",
}

REL_TOL = 1e-12
ABS_TOL = 1e-12

_PLAN_REQUIRED_KEYS = ("support",)
_PLAN_OPTIONAL_KEYS = (
    "maintenance_tasks",
    "spares",
    "obsolescence",
    "mitigation_target",
)
_SUPPORT_KEYS = (
    "period_years",
    "operating_hours_per_year",
    "units_in_service",
    "delivery_year",
)
_TASK_KEYS = ("name", "interval_months", "duration_hours", "skill")
_SPARE_KEYS = ("part", "quantity_held", "mtbf_hours")
_OBSOLESCENCE_KEYS = (
    "part",
    "end_of_life_year",
    "mitigation",
    "lifetime_buy_quantity",
    "mtbf_hours",
)


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(value):
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _number(name, value, minimum=None, strict=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if minimum is not None:
        if strict and out <= minimum:
            raise ValueError("%s must be greater than %g, got %g" % (name, minimum, out))
        if not strict and out < minimum:
            raise ValueError("%s must be at least %g, got %g" % (name, minimum, out))
    return out


def _fraction(name, value):
    out = _number(name, value)
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def _count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (name, value))
    return value


def _year(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer year, got %r" % (name, value))
    if value < 1900:
        raise ValueError("%s must be a four digit year, got %d" % (name, value))
    return value


def at_least(held, needed):
    """True when a holding covers a computed demand, exact landings included."""
    held = _number("held", held)
    needed = _number("needed", needed)
    return held > needed or math.isclose(
        held, needed, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def meets_mitigation_target(achieved, target):
    """True when mitigation coverage reaches the target, landings included."""
    achieved = _fraction("achieved", achieved)
    target = _fraction("target", target)
    return achieved > target or math.isclose(
        achieved, target, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_mitigation(value):
    """Fold an obsolescence mitigation onto one of the recognised names."""
    key = _key(_text("mitigation", value))
    for candidate in (key, key.replace(" ", "-"), key.replace("-", " ")):
        if candidate in _MITIGATION_ALIASES:
            return _MITIGATION_ALIASES[candidate]
    raise ValueError(
        "unknown mitigation %r; use one of %s" % (value, ", ".join(MITIGATIONS))
    )


def normalize_skill(value):
    """Fold a maintenance skill level onto one of the recognised levels."""
    key = _key(_text("skill", value))
    if key in _SKILL_ALIASES:
        return _SKILL_ALIASES[key]
    raise ValueError(
        "unknown maintenance skill %r; use one of %s"
        % (value, ", ".join(MAINTENANCE_SKILLS))
    )


def support_period_months(period_years):
    """The support obligation expressed in months."""
    return _number("period_years", period_years, minimum=0.0, strict=True) * (
        MONTHS_PER_YEAR
    )


def maintenance_occurrences(interval_months, window_months):
    """How many times a task falls due inside the support window."""
    interval = _number("interval_months", interval_months, minimum=0.0, strict=True)
    window = _number("window_months", window_months, minimum=0.0, strict=True)
    ratio = window / interval
    whole = math.floor(ratio)
    if math.isclose(ratio, whole + 1, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        whole += 1
    return int(whole)


def expected_demand(operating_hours_total, mtbf_hours):
    """Units expected to be consumed over the operating hours given."""
    hours = _number("operating_hours_total", operating_hours_total, minimum=0.0)
    mtbf = _number("mtbf_hours", mtbf_hours, minimum=0.0, strict=True)
    return hours / mtbf


def total_operating_hours(hours_per_year, units_in_service, years):
    """Operating hours accumulated across the fleet over the window."""
    hours = _number("operating_hours_per_year", hours_per_year, minimum=0.0)
    units = _count("units_in_service", units_in_service)
    span = _number("years", years, minimum=0.0)
    if units < 1:
        raise ValueError("units_in_service must be at least 1")
    return hours * units * span


def validate_support(support):
    """Check the support window block and return it resolved."""
    if not isinstance(support, dict):
        raise ValueError("support must be a mapping describing the support window")
    unknown = sorted(set(support) - set(_SUPPORT_KEYS))
    if unknown:
        raise ValueError("support has unknown keys: %s" % ", ".join(unknown))
    for key in ("period_years", "operating_hours_per_year", "units_in_service"):
        if key not in support:
            raise ValueError("support missing key: %s" % key)
    period = _number(
        "support.period_years", support["period_years"], minimum=0.0, strict=True
    )
    return {
        "period_years": period,
        "period_months": period * MONTHS_PER_YEAR,
        "operating_hours_per_year": _number(
            "support.operating_hours_per_year",
            support["operating_hours_per_year"],
            minimum=0.0,
        ),
        "units_in_service": _count(
            "support.units_in_service", support["units_in_service"]
        ),
        "delivery_year": _year(
            "support.delivery_year", support.get("delivery_year", 2030)
        ),
    }


def validate_maintenance_tasks(entries):
    """Check the maintenance task list and return it in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("maintenance_tasks must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("maintenance_tasks[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_TASK_KEYS))
        if unknown:
            raise ValueError(
                "maintenance_tasks[%d] has unknown keys: %s"
                % (index, ", ".join(unknown))
            )
        for key in ("name", "interval_months"):
            if key not in entry:
                raise ValueError(
                    "maintenance_tasks[%d] missing key: %s" % (index, key)
                )
        name = _text("maintenance_tasks[%d].name" % index, entry["name"])
        if name in seen:
            raise ValueError("duplicate maintenance task %r" % name)
        seen.add(name)
        resolved.append(
            {
                "name": name,
                "interval_months": _number(
                    "maintenance_tasks[%d].interval_months" % index,
                    entry["interval_months"],
                    minimum=0.0,
                    strict=True,
                ),
                "duration_hours": _number(
                    "maintenance_tasks[%d].duration_hours" % index,
                    entry.get("duration_hours", 0.0),
                    minimum=0.0,
                ),
                "skill": normalize_skill(entry.get("skill", "technician")),
            }
        )
    return resolved


def validate_spares(entries):
    """Check the spares list and return it in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("spares must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("spares[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_SPARE_KEYS))
        if unknown:
            raise ValueError(
                "spares[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("part", "mtbf_hours"):
            if key not in entry:
                raise ValueError("spares[%d] missing key: %s" % (index, key))
        part = _text("spares[%d].part" % index, entry["part"])
        if part in seen:
            raise ValueError("duplicate spare part %r" % part)
        seen.add(part)
        resolved.append(
            {
                "part": part,
                "quantity_held": _count(
                    "spares[%d].quantity_held" % index, entry.get("quantity_held", 0)
                ),
                "mtbf_hours": _number(
                    "spares[%d].mtbf_hours" % index,
                    entry["mtbf_hours"],
                    minimum=0.0,
                    strict=True,
                ),
            }
        )
    return resolved


def validate_obsolescence(entries):
    """Check the obsolescence list and return it in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("obsolescence must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("obsolescence[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_OBSOLESCENCE_KEYS))
        if unknown:
            raise ValueError(
                "obsolescence[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("part", "end_of_life_year"):
            if key not in entry:
                raise ValueError("obsolescence[%d] missing key: %s" % (index, key))
        part = _text("obsolescence[%d].part" % index, entry["part"])
        if part in seen:
            raise ValueError("duplicate obsolescence entry %r" % part)
        seen.add(part)
        quantity = entry.get("lifetime_buy_quantity")
        mtbf = entry.get("mtbf_hours")
        resolved.append(
            {
                "part": part,
                "end_of_life_year": _year(
                    "obsolescence[%d].end_of_life_year" % index,
                    entry["end_of_life_year"],
                ),
                "mitigation": normalize_mitigation(entry.get("mitigation", "none")),
                "lifetime_buy_quantity": (
                    None
                    if quantity is None
                    else _count(
                        "obsolescence[%d].lifetime_buy_quantity" % index, quantity
                    )
                ),
                "mtbf_hours": (
                    None
                    if mtbf is None
                    else _number(
                        "obsolescence[%d].mtbf_hours" % index,
                        mtbf,
                        minimum=0.0,
                        strict=True,
                    )
                ),
            }
        )
    return resolved


def support_end_year(support):
    """The last year the support obligation runs into."""
    return support["delivery_year"] + support["period_years"]


def at_risk_parts(parts, end_year):
    """Parts whose end of life falls on or before the support end."""
    bound = _number("end_year", end_year)
    return [
        part
        for part in parts
        if part["end_of_life_year"] < bound
        or math.isclose(
            float(part["end_of_life_year"]), bound, rel_tol=REL_TOL, abs_tol=ABS_TOL
        )
    ]


def mitigation_coverage(parts, end_year):
    """Share of the at-risk parts carrying a mitigation other than none."""
    at_risk = at_risk_parts(parts, end_year)
    if not at_risk:
        raise ValueError("no part is at risk inside the support window")
    mitigated = sum(1 for part in at_risk if part["mitigation"] != "none")
    return mitigated / len(at_risk)


def evaluate_support_maintenance_plan(plan):
    """Full clause 5.2.5 assessment of one preliminary support plan.

    Returns the support window figures, the spares demand, the findings
    and whether the plan is sufficient for the obligation it carries.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping with a support block")
    known = set(_PLAN_REQUIRED_KEYS) | set(_PLAN_OPTIONAL_KEYS)
    unknown = sorted(set(plan) - known)
    if unknown:
        raise ValueError("unknown plan keys: %s" % ", ".join(unknown))
    if "support" not in plan:
        raise ValueError("plan missing required keys: support")

    support = validate_support(plan["support"])
    tasks = validate_maintenance_tasks(plan.get("maintenance_tasks", []) or [])
    spares = validate_spares(plan.get("spares", []) or [])
    parts = validate_obsolescence(plan.get("obsolescence", []) or [])
    target = _fraction("mitigation_target", plan.get("mitigation_target", 1.0))

    fleet_hours = total_operating_hours(
        support["operating_hours_per_year"],
        support["units_in_service"],
        support["period_years"],
    )

    findings = []
    schedule = []
    for task in tasks:
        if not at_least(support["period_months"], task["interval_months"]):
            findings.append(
                {
                    "code": "maintenance-task-never-due",
                    "task": task["name"],
                    "detail": "%s repeats every %g months inside a %g month "
                    "support window, so it never falls due"
                    % (
                        task["name"],
                        task["interval_months"],
                        support["period_months"],
                    ),
                }
            )
            continue
        schedule.append(
            {
                "task": task["name"],
                "occurrences": maintenance_occurrences(
                    task["interval_months"], support["period_months"]
                ),
                "skill": task["skill"],
            }
        )

    demands = []
    for spare in spares:
        demand = expected_demand(fleet_hours, spare["mtbf_hours"])
        demands.append({"part": spare["part"], "demand": demand})
        if not at_least(spare["quantity_held"], demand):
            findings.append(
                {
                    "code": "spares-below-expected-demand",
                    "part": spare["part"],
                    "held": spare["quantity_held"],
                    "demand": demand,
                    "detail": "%s holds %d against an expected demand of %.3f over "
                    "the support window"
                    % (spare["part"], spare["quantity_held"], demand),
                }
            )

    end_year = support_end_year(support)
    spare_names = {spare["part"] for spare in spares}
    assessed = {part["part"] for part in parts}
    for name in sorted(spare_names - assessed):
        findings.append(
            {
                "code": "spare-without-obsolescence-assessment",
                "part": name,
                "detail": "%s is held as a spare and carries no obsolescence "
                "assessment" % name,
            }
        )

    for part in at_risk_parts(parts, end_year):
        if part["mitigation"] == "none":
            findings.append(
                {
                    "code": "obsolescence-unmitigated",
                    "part": part["part"],
                    "detail": "%s reaches end of life in %d, inside a support "
                    "window running to %g, with no mitigation"
                    % (part["part"], part["end_of_life_year"], end_year),
                }
            )
            continue
        if part["mitigation"] != "lifetime-buy":
            continue
        if part["mtbf_hours"] is None:
            findings.append(
                {
                    "code": "lifetime-buy-unsized",
                    "part": part["part"],
                    "detail": "the lifetime buy for %s cannot be sized without a "
                    "mean time between failures" % part["part"],
                }
            )
            continue
        remaining_years = max(0.0, end_year - part["end_of_life_year"])
        remaining_hours = total_operating_hours(
            support["operating_hours_per_year"],
            support["units_in_service"],
            remaining_years,
        )
        needed = expected_demand(remaining_hours, part["mtbf_hours"])
        held = 0 if part["lifetime_buy_quantity"] is None else (
            part["lifetime_buy_quantity"]
        )
        if not at_least(held, needed):
            findings.append(
                {
                    "code": "lifetime-buy-quantity-short",
                    "part": part["part"],
                    "held": held,
                    "needed": needed,
                    "detail": "the lifetime buy for %s holds %d against %.3f needed "
                    "from end of life to the end of support"
                    % (part["part"], held, needed),
                }
            )

    coverage = None
    if at_risk_parts(parts, end_year):
        coverage = mitigation_coverage(parts, end_year)
        if not meets_mitigation_target(coverage, target):
            findings.append(
                {
                    "code": "mitigation-coverage-below-target",
                    "achieved": coverage,
                    "target": target,
                    "detail": "obsolescence mitigation reaches %.1f %% of the "
                    "at-risk parts against a %.1f %% target"
                    % (100.0 * coverage, 100.0 * target),
                }
            )

    return {
        "support_period_months": support["period_months"],
        "support_end_year": end_year,
        "fleet_operating_hours": fleet_hours,
        "maintenance_schedule": schedule,
        "spares_demand": demands,
        "at_risk_parts": sorted(p["part"] for p in at_risk_parts(parts, end_year)),
        "mitigation_coverage": coverage,
        "mitigation_target": target,
        "findings": findings,
        "sufficient": not findings,
    }
