#!/usr/bin/env python3
"""Device development plan contents (ECSS-E-ST-20-40C Annex B).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The data item fixes what a device development plan has to contain: the
organisation doing the work, the tasks it will carry out, the tooling
those tasks need, and the schedule they run to. Those four are not four
independent lists -- the plan is only a plan when they refer to each
other, so the checks that matter are referential:

* every task is owned by a role the organisation actually declares, and
  every declared role owns at least one task;
* every tool a task names is declared in the tooling list with a
  qualification state, and a tool nobody uses is dead weight in the plan;
* every task belongs to a milestone the schedule declares, finishes on
  or before that milestone's date, and has a positive duration;
* milestone dates rise in declared order.

Dates are carried as day numbers on a single project timeline, which
keeps the arithmetic exact and the plan free of calendar assumptions.
"""

import math

MANDATORY_SECTIONS = ("organisation", "tasks", "tooling", "schedule")

# Qualification states a tool may be in when the plan is written.
QUALIFIED = "qualified"
UNDER_QUALIFICATION = "under-qualification"
UNQUALIFIED = "unqualified"
QUALIFICATION_STATES = (QUALIFIED, UNDER_QUALIFICATION, UNQUALIFIED)
_STATE_ALIASES = {
    "qualified": QUALIFIED,
    "validated": QUALIFIED,
    "under-qualification": UNDER_QUALIFICATION,
    "under qualification": UNDER_QUALIFICATION,
    "in qualification": UNDER_QUALIFICATION,
    "unqualified": UNQUALIFIED,
    "not qualified": UNQUALIFIED,
    "none": UNQUALIFIED,
}

_ROLE_KEYS = ("role", "holder", "responsibilities")
_TASK_KEYS = ("id", "title", "owner_role", "tools", "start_day", "finish_day", "milestone")
_TOOL_KEYS = ("id", "name", "version", "qualification_status")
_MILESTONE_KEYS = ("milestone", "day")

REL_TOL = 1e-12
ABS_TOL = 1e-18


def _as_day(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a day number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %g" % (name, out))
    return out


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def within_limit(value, limit):
    """True when ``value`` is at or under ``limit``, representation error absorbed."""
    return value < limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_qualification_state(value):
    """Fold a tool qualification state onto the three recognised names."""
    key = " ".join(_text("qualification_status", value).lower().split())
    if key in _STATE_ALIASES:
        return _STATE_ALIASES[key]
    raise ValueError(
        "unknown qualification_status %r; use one of %s"
        % (value, ", ".join(QUALIFICATION_STATES))
    )


def validate_organisation(entries):
    """Check the roster and return role name to holder and responsibilities."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("organisation must be a list of roles")
    roster = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("organisation[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_ROLE_KEYS))
        if unknown:
            raise ValueError(
                "organisation[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "role" not in entry:
            raise ValueError("organisation[%d] missing key: role" % index)
        role = _text("organisation[%d].role" % index, entry["role"])
        if role in roster:
            raise ValueError("duplicate role %r in organisation" % role)
        holder = _text(
            "organisation[%d].holder" % index, entry.get("holder", ""), allow_empty=True
        )
        responsibilities = entry.get("responsibilities", [])
        if not isinstance(responsibilities, (list, tuple)):
            raise ValueError(
                "organisation[%d].responsibilities must be a list" % index
            )
        roster[role] = {
            "holder": holder,
            "responsibilities": [
                _text("organisation[%d].responsibilities[%d]" % (index, j), r)
                for j, r in enumerate(responsibilities)
            ],
        }
    return roster


def validate_tooling(entries):
    """Check the tool list and return tool id to name, version and state."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("tooling must be a list of tools")
    tools = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("tooling[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_TOOL_KEYS))
        if unknown:
            raise ValueError(
                "tooling[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "id" not in entry:
            raise ValueError("tooling[%d] missing key: id" % index)
        tool_id = _text("tooling[%d].id" % index, entry["id"])
        if tool_id in tools:
            raise ValueError("duplicate tool id %r in tooling" % tool_id)
        state = entry.get("qualification_status", UNQUALIFIED)
        tools[tool_id] = {
            "name": _text("tooling[%d].name" % index, entry.get("name", ""), True),
            "version": _text(
                "tooling[%d].version" % index, entry.get("version", ""), True
            ),
            "qualification_status": normalize_qualification_state(state),
        }
    return tools


def validate_schedule(entries):
    """Check the milestone list and return it in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("schedule must be a list of milestones")
    milestones = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("schedule[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_MILESTONE_KEYS))
        if unknown:
            raise ValueError(
                "schedule[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in _MILESTONE_KEYS:
            if key not in entry:
                raise ValueError("schedule[%d] missing key: %s" % (index, key))
        name = _text("schedule[%d].milestone" % index, entry["milestone"])
        if name in seen:
            raise ValueError("duplicate milestone %r in schedule" % name)
        seen.add(name)
        milestones.append(
            {"milestone": name, "day": _as_day("schedule[%d].day" % index, entry["day"])}
        )
    return milestones


def validate_tasks(entries):
    """Check the task list and return it resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("tasks must be a list of tasks")
    tasks = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("tasks[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_TASK_KEYS))
        if unknown:
            raise ValueError(
                "tasks[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "start_day", "finish_day"):
            if key not in entry:
                raise ValueError("tasks[%d] missing key: %s" % (index, key))
        task_id = _text("tasks[%d].id" % index, entry["id"])
        if task_id in seen:
            raise ValueError("duplicate task id %r in tasks" % task_id)
        seen.add(task_id)
        tools = entry.get("tools", [])
        if not isinstance(tools, (list, tuple)):
            raise ValueError("tasks[%d].tools must be a list" % index)
        tasks.append(
            {
                "id": task_id,
                "title": _text("tasks[%d].title" % index, entry.get("title", ""), True),
                "owner_role": _text(
                    "tasks[%d].owner_role" % index, entry.get("owner_role", ""), True
                ),
                "tools": [
                    _text("tasks[%d].tools[%d]" % (index, j), t)
                    for j, t in enumerate(tools)
                ],
                "start_day": _as_day("tasks[%d].start_day" % index, entry["start_day"]),
                "finish_day": _as_day(
                    "tasks[%d].finish_day" % index, entry["finish_day"]
                ),
                "milestone": _text(
                    "tasks[%d].milestone" % index, entry.get("milestone", ""), True
                ),
            }
        )
    return tasks


def plan_span_days(tasks):
    """Days from the earliest task start to the latest task finish."""
    if not tasks:
        raise ValueError("plan_span_days needs at least one task")
    return max(t["finish_day"] for t in tasks) - min(t["start_day"] for t in tasks)


def schedule_slack_days(tasks, milestones):
    """Days between the last task finish and the last milestone."""
    if not tasks:
        raise ValueError("schedule_slack_days needs at least one task")
    if not milestones:
        raise ValueError("schedule_slack_days needs at least one milestone")
    return max(m["day"] for m in milestones) - max(t["finish_day"] for t in tasks)


def evaluate_development_plan(plan):
    """Full Annex B assessment of one device development plan.

    Returns the resolved four content areas, the span and slack figures,
    the findings and the verdict.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping of the four content areas")
    unknown = sorted(set(plan) - set(MANDATORY_SECTIONS))
    if unknown:
        raise ValueError("unknown plan keys: %s" % ", ".join(unknown))

    findings = []
    for name in MANDATORY_SECTIONS:
        if name not in plan:
            findings.append(
                {
                    "code": "mandatory-section-absent",
                    "section": name,
                    "detail": "the data item requires a %s content area" % name,
                }
            )
        elif isinstance(plan[name], (list, tuple)) and len(plan[name]) == 0:
            findings.append(
                {
                    "code": "mandatory-section-empty",
                    "section": name,
                    "detail": "the %s area exists and holds nothing" % name,
                }
            )

    roster = validate_organisation(plan.get("organisation", []))
    tools = validate_tooling(plan.get("tooling", []))
    milestones = validate_schedule(plan.get("schedule", []))
    tasks = validate_tasks(plan.get("tasks", []))
    milestone_day = {m["milestone"]: m["day"] for m in milestones}

    for role, info in sorted(roster.items()):
        if not info["responsibilities"]:
            findings.append(
                {
                    "code": "role-without-responsibilities",
                    "role": role,
                    "detail": "role %s is declared with nothing assigned to it" % role,
                }
            )

    used_tools = set()
    owned_roles = set()
    for task in tasks:
        if not task["owner_role"]:
            findings.append(
                {
                    "code": "task-without-owner",
                    "task": task["id"],
                    "detail": "task %s names no owning role" % task["id"],
                }
            )
        elif task["owner_role"] not in roster:
            findings.append(
                {
                    "code": "task-owner-not-in-organisation",
                    "task": task["id"],
                    "owner_role": task["owner_role"],
                    "detail": "task %s is owned by %r, which the organisation does "
                    "not declare" % (task["id"], task["owner_role"]),
                }
            )
        else:
            owned_roles.add(task["owner_role"])
        for tool_id in task["tools"]:
            used_tools.add(tool_id)
            if tool_id not in tools:
                findings.append(
                    {
                        "code": "task-tool-not-declared",
                        "task": task["id"],
                        "tool": tool_id,
                        "detail": "task %s uses %r, which the tooling area does not "
                        "declare" % (task["id"], tool_id),
                    }
                )
            elif tools[tool_id]["qualification_status"] != QUALIFIED:
                findings.append(
                    {
                        "code": "task-uses-unqualified-tool",
                        "task": task["id"],
                        "tool": tool_id,
                        "qualification_status": tools[tool_id]["qualification_status"],
                        "detail": "task %s depends on %r, which is %s"
                        % (task["id"], tool_id, tools[tool_id]["qualification_status"]),
                    }
                )
        if not task["finish_day"] > task["start_day"]:
            findings.append(
                {
                    "code": "task-with-non-positive-duration",
                    "task": task["id"],
                    "start_day": task["start_day"],
                    "finish_day": task["finish_day"],
                    "detail": "task %s finishes on or before it starts" % task["id"],
                }
            )
        if not task["milestone"]:
            findings.append(
                {
                    "code": "task-without-milestone",
                    "task": task["id"],
                    "detail": "task %s belongs to no milestone" % task["id"],
                }
            )
        elif task["milestone"] not in milestone_day:
            findings.append(
                {
                    "code": "task-milestone-not-in-schedule",
                    "task": task["id"],
                    "milestone": task["milestone"],
                    "detail": "task %s points at milestone %r, which the schedule "
                    "does not declare" % (task["id"], task["milestone"]),
                }
            )
        elif not within_limit(task["finish_day"], milestone_day[task["milestone"]]):
            findings.append(
                {
                    "code": "task-overruns-its-milestone",
                    "task": task["id"],
                    "milestone": task["milestone"],
                    "finish_day": task["finish_day"],
                    "milestone_day": milestone_day[task["milestone"]],
                    "detail": "task %s finishes on day %g, after milestone %s on day "
                    "%g" % (
                        task["id"],
                        task["finish_day"],
                        task["milestone"],
                        milestone_day[task["milestone"]],
                    ),
                }
            )

    idle_roles = sorted(set(roster) - owned_roles)
    if idle_roles:
        findings.append(
            {
                "code": "role-without-task",
                "roles": idle_roles,
                "detail": "roles %s own no task in the plan" % ", ".join(idle_roles),
            }
        )
    unused_tools = sorted(set(tools) - used_tools)
    if unused_tools:
        findings.append(
            {
                "code": "tool-not-used-by-any-task",
                "tools": unused_tools,
                "detail": "tools %s are declared and never used"
                % ", ".join(unused_tools),
            }
        )
    for earlier, later in zip(milestones, milestones[1:]):
        if not later["day"] > earlier["day"]:
            findings.append(
                {
                    "code": "schedule-out-of-order",
                    "milestones": [earlier["milestone"], later["milestone"]],
                    "detail": "milestone %s on day %g does not follow %s on day %g"
                    % (
                        later["milestone"],
                        later["day"],
                        earlier["milestone"],
                        earlier["day"],
                    ),
                }
            )

    return {
        "role_count": len(roster),
        "task_count": len(tasks),
        "tool_count": len(tools),
        "milestone_count": len(milestones),
        "span_days": plan_span_days(tasks) if tasks else 0.0,
        "slack_days": (
            schedule_slack_days(tasks, milestones) if tasks and milestones else None
        ),
        "findings": findings,
        "complete": not findings,
    }
