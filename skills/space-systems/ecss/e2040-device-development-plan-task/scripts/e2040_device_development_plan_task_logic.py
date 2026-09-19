#!/usr/bin/env python3
"""Device development plan task (ECSS-E-ST-20-40C clause 5.2.3).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The task is to set out the development strategy the supplier will follow
for the device. Four strands have to describe one development:

* the model philosophy is an ordered sequence. Models run from
  breadboard through engineering and qualification hardware to flight
  hardware, each one retiring what the next cannot afford to discover,
  and the sequence has to reach an article that can carry
  qualification;
* the phase windows meet end to start. A gap is time nobody owns, an
  overlap is two phases competing for one team, and both are reported;
* milestones belong to phases, so a milestone outside the window of its
  own phase is either mis-assigned or the trace of a window that moved
  without it;
* a critical technology below the readiness floor needs a maturation
  activity that completes before the design depends on it, and a bought
  item needs a named source.

Window joins and need dates land exactly on each other, so every
comparison here absorbs the representation error of floating point
arithmetic rather than reporting a gap of a fraction of a day.
"""

import math

# Development models, in the canonical order they are built.
DEVELOPMENT_MODELS = (
    "breadboard",
    "elegant-breadboard",
    "engineering-model",
    "structural-thermal-model",
    "engineering-qualification-model",
    "qualification-model",
    "proto-flight-model",
    "flight-model",
)
_MODEL_ALIASES = {
    "breadboard": "breadboard",
    "bb": "breadboard",
    "elegant-breadboard": "elegant-breadboard",
    "ebb": "elegant-breadboard",
    "engineering-model": "engineering-model",
    "em": "engineering-model",
    "structural-thermal-model": "structural-thermal-model",
    "stm": "structural-thermal-model",
    "engineering-qualification-model": "engineering-qualification-model",
    "eqm": "engineering-qualification-model",
    "qualification-model": "qualification-model",
    "qm": "qualification-model",
    "proto-flight-model": "proto-flight-model",
    "pfm": "proto-flight-model",
    "flight-model": "flight-model",
    "fm": "flight-model",
}

# Models that can carry a qualification campaign.
QUALIFICATION_BEARING_MODELS = (
    "engineering-qualification-model",
    "qualification-model",
    "proto-flight-model",
)

# Make-or-buy routes.
PROCUREMENT_ROUTES = ("make", "buy")
_ROUTE_ALIASES = {
    "make": "make",
    "in-house": "make",
    "internal": "make",
    "buy": "buy",
    "procure": "buy",
    "subcontract": "buy",
}

TRL_MIN = 1
TRL_MAX = 9
DEFAULT_TRL_FLOOR = 5

REL_TOL = 1e-12
ABS_TOL = 1e-9

_PLAN_REQUIRED_KEYS = ("models", "phases")
_PLAN_OPTIONAL_KEYS = (
    "milestones",
    "technologies",
    "procurements",
    "trl_floor",
    "target_duration_months",
)
_PHASE_KEYS = ("name", "start_month", "end_month")
_MILESTONE_KEYS = ("name", "month", "phase")
_TECHNOLOGY_KEYS = (
    "name",
    "trl",
    "maturation_activity",
    "maturation_complete_month",
    "needed_by_month",
)
_PROCUREMENT_KEYS = ("item", "route", "source")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(value):
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _months(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number of months, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out < 0.0:
        raise ValueError("%s must not be negative, got %g" % (name, out))
    return out


def same_month(left, right):
    """True when two schedule points coincide within representation error."""
    return math.isclose(
        _months("left", left), _months("right", right),
        rel_tol=REL_TOL, abs_tol=ABS_TOL,
    )


def not_later_than(point, bound):
    """True when a schedule point sits on or before a bound."""
    point = _months("point", point)
    bound = _months("bound", bound)
    return point < bound or same_month(point, bound)


def not_earlier_than(point, bound):
    """True when a schedule point sits on or after a bound."""
    point = _months("point", point)
    bound = _months("bound", bound)
    return point > bound or same_month(point, bound)


def normalize_model(value):
    """Fold a development model spelling onto a canonical model name."""
    key = _key(_text("model", value)).replace(" ", "-")
    if key in _MODEL_ALIASES:
        return _MODEL_ALIASES[key]
    raise ValueError(
        "unknown development model %r; use one of %s"
        % (value, ", ".join(DEVELOPMENT_MODELS))
    )


def normalize_route(value):
    """Fold a make-or-buy route onto make or buy."""
    key = _key(_text("route", value)).replace(" ", "-")
    if key in _ROUTE_ALIASES:
        return _ROUTE_ALIASES[key]
    raise ValueError(
        "unknown procurement route %r; use one of %s"
        % (value, ", ".join(PROCUREMENT_ROUTES))
    )


def validate_model_sequence(models):
    """Fold the declared model sequence and refuse repeats."""
    if not isinstance(models, (list, tuple)):
        raise ValueError("models must be a list of development models")
    resolved = []
    for index, model in enumerate(models):
        folded = normalize_model(model)
        if folded in resolved:
            raise ValueError("model %r is declared twice" % folded)
        resolved.append(folded)
    if not resolved:
        raise ValueError("the plan must declare at least one development model")
    return resolved


def sequence_in_canonical_order(models):
    """True when the declared models run in the canonical build order."""
    positions = [DEVELOPMENT_MODELS.index(model) for model in models]
    return all(a < b for a, b in zip(positions, positions[1:]))


def carries_qualification(models):
    """True when the sequence reaches a qualification-bearing article."""
    return any(model in QUALIFICATION_BEARING_MODELS for model in models)


def validate_phases(entries):
    """Check the phase windows and return them in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("phases must be a list of phase windows")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("phases[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_PHASE_KEYS))
        if unknown:
            raise ValueError(
                "phases[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in _PHASE_KEYS:
            if key not in entry:
                raise ValueError("phases[%d] missing key: %s" % (index, key))
        name = _text("phases[%d].name" % index, entry["name"])
        if name in seen:
            raise ValueError("duplicate phase name %r" % name)
        seen.add(name)
        start = _months("phases[%d].start_month" % index, entry["start_month"])
        end = _months("phases[%d].end_month" % index, entry["end_month"])
        if not_later_than(end, start):
            raise ValueError(
                "phase %r ends at month %g, on or before its start at %g"
                % (name, end, start)
            )
        resolved.append({"name": name, "start_month": start, "end_month": end})
    if not resolved:
        raise ValueError("the plan must declare at least one phase")
    return resolved


def phase_continuity_findings(phases):
    """Gaps and overlaps between consecutive phase windows."""
    out = []
    for previous, following in zip(phases, phases[1:]):
        if same_month(previous["end_month"], following["start_month"]):
            continue
        if following["start_month"] > previous["end_month"]:
            out.append(
                {
                    "code": "phase-window-gap",
                    "between": [previous["name"], following["name"]],
                    "months": following["start_month"] - previous["end_month"],
                }
            )
        else:
            out.append(
                {
                    "code": "phase-window-overlap",
                    "between": [previous["name"], following["name"]],
                    "months": previous["end_month"] - following["start_month"],
                }
            )
    return out


def total_duration(phases):
    """Months from the first phase start to the last phase end."""
    if not phases:
        raise ValueError("total_duration needs at least one phase")
    return max(p["end_month"] for p in phases) - min(
        p["start_month"] for p in phases
    )


def validate_milestones(entries):
    """Check the milestone list and return it in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("milestones must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("milestones[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_MILESTONE_KEYS))
        if unknown:
            raise ValueError(
                "milestones[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in _MILESTONE_KEYS:
            if key not in entry:
                raise ValueError("milestones[%d] missing key: %s" % (index, key))
        name = _text("milestones[%d].name" % index, entry["name"])
        if name in seen:
            raise ValueError("duplicate milestone name %r" % name)
        seen.add(name)
        resolved.append(
            {
                "name": name,
                "month": _months("milestones[%d].month" % index, entry["month"]),
                "phase": _text("milestones[%d].phase" % index, entry["phase"]),
            }
        )
    return resolved


def validate_technologies(entries):
    """Check the critical technology list and return it in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("technologies must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("technologies[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_TECHNOLOGY_KEYS))
        if unknown:
            raise ValueError(
                "technologies[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("name", "trl"):
            if key not in entry:
                raise ValueError("technologies[%d] missing key: %s" % (index, key))
        name = _text("technologies[%d].name" % index, entry["name"])
        if name in seen:
            raise ValueError("duplicate technology %r" % name)
        seen.add(name)
        trl = entry["trl"]
        if isinstance(trl, bool) or not isinstance(trl, int):
            raise ValueError("technologies[%d].trl must be an integer" % index)
        if not TRL_MIN <= trl <= TRL_MAX:
            raise ValueError(
                "technologies[%d].trl must lie in %d..%d, got %d"
                % (index, TRL_MIN, TRL_MAX, trl)
            )
        complete = entry.get("maturation_complete_month")
        needed = entry.get("needed_by_month")
        resolved.append(
            {
                "name": name,
                "trl": trl,
                "maturation_activity": _text(
                    "technologies[%d].maturation_activity" % index,
                    entry.get("maturation_activity", ""),
                    allow_empty=True,
                ),
                "maturation_complete_month": (
                    None
                    if complete is None
                    else _months(
                        "technologies[%d].maturation_complete_month" % index, complete
                    )
                ),
                "needed_by_month": (
                    None
                    if needed is None
                    else _months("technologies[%d].needed_by_month" % index, needed)
                ),
            }
        )
    return resolved


def validate_procurements(entries):
    """Check the make-or-buy list and return it in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("procurements must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("procurements[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_PROCUREMENT_KEYS))
        if unknown:
            raise ValueError(
                "procurements[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("item", "route"):
            if key not in entry:
                raise ValueError("procurements[%d] missing key: %s" % (index, key))
        item = _text("procurements[%d].item" % index, entry["item"])
        if item in seen:
            raise ValueError("duplicate procurement item %r" % item)
        seen.add(item)
        resolved.append(
            {
                "item": item,
                "route": normalize_route(entry["route"]),
                "source": _text(
                    "procurements[%d].source" % index,
                    entry.get("source", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def evaluate_development_plan(plan):
    """Full clause 5.2.3 assessment of one device development plan.

    Returns the model sequence, the schedule figures, the findings and
    whether the strategy is coherent.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping of models and phases")
    known = set(_PLAN_REQUIRED_KEYS) | set(_PLAN_OPTIONAL_KEYS)
    unknown = sorted(set(plan) - known)
    if unknown:
        raise ValueError("unknown plan keys: %s" % ", ".join(unknown))
    missing = [key for key in _PLAN_REQUIRED_KEYS if key not in plan]
    if missing:
        raise ValueError("plan missing required keys: %s" % ", ".join(missing))

    models = validate_model_sequence(plan["models"])
    phases = validate_phases(plan["phases"])
    milestones = validate_milestones(plan.get("milestones", []) or [])
    technologies = validate_technologies(plan.get("technologies", []) or [])
    procurements = validate_procurements(plan.get("procurements", []) or [])

    floor = plan.get("trl_floor", DEFAULT_TRL_FLOOR)
    if isinstance(floor, bool) or not isinstance(floor, int):
        raise ValueError("trl_floor must be an integer")
    if not TRL_MIN <= floor <= TRL_MAX:
        raise ValueError(
            "trl_floor must lie in %d..%d, got %d" % (TRL_MIN, TRL_MAX, floor)
        )
    target = plan.get("target_duration_months")
    if target is not None:
        target = _months("target_duration_months", target)

    findings = []
    if not sequence_in_canonical_order(models):
        findings.append(
            {
                "code": "model-sequence-out-of-order",
                "detail": "the declared model sequence %s does not run in the "
                "canonical build order" % " -> ".join(models),
            }
        )
    if not carries_qualification(models):
        findings.append(
            {
                "code": "no-qualification-bearing-model",
                "detail": "no declared model can carry qualification; add one of %s"
                % ", ".join(QUALIFICATION_BEARING_MODELS),
            }
        )

    findings.extend(
        {
            "code": entry["code"],
            "between": entry["between"],
            "months": entry["months"],
            "detail": "%s and %s leave a %s of %g months"
            % (
                entry["between"][0],
                entry["between"][1],
                "gap" if entry["code"] == "phase-window-gap" else "overlap",
                entry["months"],
            ),
        }
        for entry in phase_continuity_findings(phases)
    )

    by_name = {phase["name"]: phase for phase in phases}
    for milestone in milestones:
        window = by_name.get(milestone["phase"])
        if window is None:
            findings.append(
                {
                    "code": "milestone-phase-not-declared",
                    "milestone": milestone["name"],
                    "detail": "milestone %s names phase %r, which the plan does "
                    "not declare" % (milestone["name"], milestone["phase"]),
                }
            )
            continue
        inside = not_earlier_than(
            milestone["month"], window["start_month"]
        ) and not_later_than(milestone["month"], window["end_month"])
        if not inside:
            findings.append(
                {
                    "code": "milestone-outside-phase",
                    "milestone": milestone["name"],
                    "detail": "milestone %s sits at month %g, outside the %s window "
                    "%g to %g"
                    % (
                        milestone["name"],
                        milestone["month"],
                        window["name"],
                        window["start_month"],
                        window["end_month"],
                    ),
                }
            )

    for technology in technologies:
        if technology["trl"] >= floor:
            continue
        if not technology["maturation_activity"]:
            findings.append(
                {
                    "code": "low-readiness-without-maturation",
                    "technology": technology["name"],
                    "detail": "%s sits at readiness level %d below the floor of %d "
                    "and carries no maturation activity"
                    % (technology["name"], technology["trl"], floor),
                }
            )
            continue
        if technology["maturation_complete_month"] is None:
            findings.append(
                {
                    "code": "maturation-without-completion-date",
                    "technology": technology["name"],
                    "detail": "the maturation activity for %s has no completion "
                    "month, so no need date can object to it" % technology["name"],
                }
            )
            continue
        if technology["needed_by_month"] is None:
            continue
        if not not_later_than(
            technology["maturation_complete_month"], technology["needed_by_month"]
        ):
            findings.append(
                {
                    "code": "maturation-later-than-needed",
                    "technology": technology["name"],
                    "detail": "%s matures at month %g, after the design needs it at "
                    "%g"
                    % (
                        technology["name"],
                        technology["maturation_complete_month"],
                        technology["needed_by_month"],
                    ),
                }
            )

    for procurement in procurements:
        if procurement["route"] == "buy" and not procurement["source"]:
            findings.append(
                {
                    "code": "bought-item-without-source",
                    "item": procurement["item"],
                    "detail": "%s is bought and names no source, so its lead time "
                    "is unquoted" % procurement["item"],
                }
            )
        if procurement["route"] == "make" and procurement["source"]:
            findings.append(
                {
                    "code": "made-item-sourced-externally",
                    "item": procurement["item"],
                    "detail": "%s is declared made in house and names the external "
                    "source %s" % (procurement["item"], procurement["source"]),
                }
            )

    duration = total_duration(phases)
    if target is not None and not not_later_than(duration, target):
        findings.append(
            {
                "code": "plan-exceeds-target-duration",
                "duration_months": duration,
                "target_months": target,
                "detail": "the phase windows span %g months against a %g month "
                "target" % (duration, target),
            }
        )

    return {
        "models": models,
        "qualification_bearing": carries_qualification(models),
        "phase_count": len(phases),
        "duration_months": duration,
        "target_duration_months": target,
        "trl_floor": floor,
        "findings": findings,
        "coherent": not findings,
    }
