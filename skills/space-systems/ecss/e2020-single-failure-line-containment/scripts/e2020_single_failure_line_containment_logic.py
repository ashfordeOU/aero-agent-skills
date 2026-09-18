#!/usr/bin/env python3
"""Deciding whether one failure can take down more than one protected
distribution line.

Anchor: ECSS-E-ST-20-20C clause 5.2.15.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause bounds the reach of a single failure: one failure disables at
most one protected distribution line. The bound is on the failure, not on
the line, so the analysis is read failure point by failure point:

    line        a distribution output. Only a protected line is counted
                against the bound; an unprotected one is a separate
                finding and must not be allowed to dilute this one
    failure     a place where something can fail. A line-local point
                reaches only its own line by construction, so it is
                refused outright if it names another. A shared drive,
                command path, return or source stage is where the fan-out
                actually comes from
    fan-out     how many protected lines one failure point takes with it.
                One is the bound; two is the clause's own failure
    exposure    how much of the distribution leans on shared hardware at
                all. A shared drive reaching one protected line today
                still has that line on common hardware, so it is counted
                apart from the fan-out rather than folded into it

A protected line no declared failure point ever mentions has not passed.
It is the part of the analysis where no one looked, and it is reported
ahead of a line that was traced and found exposed, because the two need
different work.

The bound, the exposure ceiling and the tracing requirement below are a
declared policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LINE_LOCAL = "line-local"
SHARED_DRIVE = "shared-drive"
SHARED_COMMAND_PATH = "shared-command-path"
SHARED_RETURN = "shared-return"
SHARED_SOURCE_STAGE = "shared-source-stage"
SHARED_HOUSEKEEPING_SUPPLY = "shared-housekeeping-supply"

FAILURE_POINT_KINDS = (
    LINE_LOCAL,
    SHARED_DRIVE,
    SHARED_COMMAND_PATH,
    SHARED_RETURN,
    SHARED_SOURCE_STAGE,
    SHARED_HOUSEKEEPING_SUPPLY,
)

SHARED_KINDS = (
    SHARED_DRIVE,
    SHARED_COMMAND_PATH,
    SHARED_RETURN,
    SHARED_SOURCE_STAGE,
    SHARED_HOUSEKEEPING_SUPPLY,
)

CONTAINMENT_NOT_EVALUATED = "line-containment-not-evaluated"
CONTAINMENT_MULTI_LINE_FAILURE = "single-failure-disables-multiple-lines"
CONTAINMENT_EXPOSURE_OVER_CEILING = "exposed-line-fraction-over-ceiling"
CONTAINMENT_UNPROTECTED_LINE = "distribution-line-not-protected"
CONTAINMENT_SATISFIED = "single-failure-line-containment-satisfied"

DESIGN_VERDICTS = (
    CONTAINMENT_NOT_EVALUATED,
    CONTAINMENT_MULTI_LINE_FAILURE,
    CONTAINMENT_EXPOSURE_OVER_CEILING,
    CONTAINMENT_UNPROTECTED_LINE,
    CONTAINMENT_SATISFIED,
)

DEFAULT_LINE_POLICY = {
    "max_lines_per_failure": 1,
    "max_exposed_line_fraction": 0.34,
    "require_every_line_traced": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def validate_line_policy(policy):
    """Check a containment policy is usable before any line is traced."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    bound = policy.get("max_lines_per_failure")
    if not isinstance(bound, int) or isinstance(bound, bool) or bound < 1:
        raise ValueError(
            "max_lines_per_failure must be an integer of at least one, got %r"
            % (bound,)
        )
    fraction = policy.get("max_exposed_line_fraction")
    if not _is_finite_number(fraction) or not 0.0 <= float(fraction) <= 1.0:
        raise ValueError(
            "max_exposed_line_fraction must sit between zero and one, got %r"
            % (fraction,)
        )
    traced = policy.get("require_every_line_traced")
    if not isinstance(traced, bool):
        raise ValueError(
            "require_every_line_traced must be a boolean, got %r" % (traced,)
        )
    return policy


def validate_line_inventory(lines):
    """Check the line list before anything is counted against it."""
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("lines must be a non-empty sequence, got %r" % (lines,))
    inventory = {}
    for line in lines:
        if not isinstance(line, dict):
            raise ValueError("line must be a mapping, got %r" % (line,))
        line_id = _require_identifier("line id", line.get("id"))
        if line_id in inventory:
            raise ValueError("line %r declared twice" % (line_id,))
        protected = line.get("protected")
        if not isinstance(protected, bool):
            raise ValueError(
                "line %r must say whether it is protected, got %r"
                % (line_id, protected)
            )
        inventory[line_id] = {"id": line_id, "protected": protected}
    return inventory


def protected_line_ids(inventory):
    """The lines the clause bound is actually counted against."""
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("inventory must be a non-empty mapping, got %r" % (inventory,))
    return tuple(
        sorted(line_id for line_id, line in inventory.items() if line["protected"])
    )


def unprotected_line_ids(inventory):
    """Lines carrying no protection at all -- a separate finding."""
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("inventory must be a non-empty mapping, got %r" % (inventory,))
    return tuple(
        sorted(line_id for line_id, line in inventory.items() if not line["protected"])
    )


def categorize_failure_point_kind(kind):
    """Name a failure point kind, refusing anything unrecognised."""
    name = _require_identifier("failure point kind", kind)
    if name not in FAILURE_POINT_KINDS:
        raise ValueError(
            "unrecognised failure point kind %r; known kinds are %s"
            % (name, ", ".join(FAILURE_POINT_KINDS))
        )
    return name


def lines_disabled_by(point, inventory):
    """Which declared lines this one failure point takes down."""
    if not isinstance(point, dict):
        raise ValueError("failure point must be a mapping, got %r" % (point,))
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("inventory must be a non-empty mapping, got %r" % (inventory,))
    point_id = _require_identifier("failure point id", point.get("id"))
    kind = categorize_failure_point_kind(point.get("kind"))

    disables = point.get("disables")
    if not isinstance(disables, (list, tuple)) or not disables:
        raise ValueError(
            "failure point %r must disable at least one line, got %r"
            % (point_id, disables)
        )
    named = []
    for line_id in disables:
        resolved = _require_identifier("disabled line id", line_id)
        if resolved not in inventory:
            raise ValueError(
                "failure point %r disables unknown line %r" % (point_id, resolved)
            )
        named.append(resolved)
    if len(set(named)) != len(named):
        raise ValueError("failure point %r names the same line twice" % (point_id,))

    if kind == LINE_LOCAL:
        own = _require_identifier("failure point line", point.get("line"))
        if own not in inventory:
            raise ValueError(
                "failure point %r sits on unknown line %r" % (point_id, own)
            )
        if tuple(named) != (own,):
            raise ValueError(
                "line-local failure point %r reaches past its own line %r to %s, "
                "so it is not line-local" % (point_id, own, ", ".join(sorted(named)))
            )
    return tuple(sorted(named))


def failure_fan_out(point, inventory):
    """How many protected lines one failure point takes with it."""
    disabled = lines_disabled_by(point, inventory)
    return sum(1 for line_id in disabled if inventory[line_id]["protected"])


def validate_failure_points(points, inventory):
    """Check the failure point list, refusing duplicates and bad references."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("failure_points must be a non-empty sequence, got %r" % (points,))
    seen = set()
    records = []
    for point in points:
        if not isinstance(point, dict):
            raise ValueError("failure point must be a mapping, got %r" % (point,))
        point_id = _require_identifier("failure point id", point.get("id"))
        if point_id in seen:
            raise ValueError("failure point %r declared twice" % (point_id,))
        seen.add(point_id)
        records.append(
            {
                "id": point_id,
                "kind": categorize_failure_point_kind(point.get("kind")),
                "disables": lines_disabled_by(point, inventory),
                "fan_out": failure_fan_out(point, inventory),
            }
        )
    return records


def find_multi_line_failures(records, policy=DEFAULT_LINE_POLICY):
    """The failure points that reach past the bound, worst first."""
    validate_line_policy(policy)
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence, got %r" % (records,))
    bound = int(policy["max_lines_per_failure"])
    offenders = [
        record
        for record in records
        if int(record["fan_out"]) > bound
    ]
    return sorted(offenders, key=lambda record: (-record["fan_out"], record["id"]))


def shared_dependency_lines(records, inventory):
    """Protected lines that lean on a shared element at all, fan-out aside."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence, got %r" % (records,))
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("inventory must be a non-empty mapping, got %r" % (inventory,))
    exposed = set()
    for record in records:
        if record["kind"] not in SHARED_KINDS:
            continue
        for line_id in record["disables"]:
            if inventory[line_id]["protected"]:
                exposed.add(line_id)
    return tuple(sorted(exposed))


def exposed_line_fraction(records, inventory):
    """Share of the protected lines depending on shared hardware.

    A shared drive that happens to reach only one protected line today
    still puts that line on common hardware, so this is counted apart from
    the fan-out bound rather than folded into it.
    """
    protected = protected_line_ids(inventory)
    if not protected:
        raise ValueError("inventory declares no protected line to count against")
    return len(shared_dependency_lines(records, inventory)) / len(protected)


def untraced_protected_lines(records, inventory):
    """Protected lines no declared failure point ever mentions."""
    protected = set(protected_line_ids(inventory))
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence, got %r" % (records,))
    for record in records:
        for line_id in record["disables"]:
            protected.discard(line_id)
    return tuple(sorted(protected))


def assess_single_failure_containment(design, policy=DEFAULT_LINE_POLICY):
    """Full clause 5.2.15.1.1 judgement of one distribution design."""
    validate_line_policy(policy)
    if not isinstance(design, dict):
        raise ValueError("design must be a mapping, got %r" % (design,))

    inventory = validate_line_inventory(design.get("lines"))
    records = validate_failure_points(design.get("failure_points"), inventory)

    offenders = find_multi_line_failures(records, policy)
    untraced = untraced_protected_lines(records, inventory)
    unprotected = unprotected_line_ids(inventory)
    fraction = exposed_line_fraction(records, inventory)
    worst = max((record["fan_out"] for record in records), default=0)

    findings = []
    for record in offenders:
        findings.append(
            "%s (%s) disables %d protected lines -- %s -- against the bound of "
            "%d"
            % (
                record["id"],
                record["kind"],
                record["fan_out"],
                ", ".join(record["disables"]),
                int(policy["max_lines_per_failure"]),
            )
        )
    ceiling = float(policy["max_exposed_line_fraction"])
    if not _at_most(fraction, ceiling):
        findings.append(
            "%.4f of the protected lines depend on shared hardware against "
            "the %.4f the policy allows" % (fraction, ceiling)
        )
    for line_id in untraced:
        findings.append(
            "protected line %s is named by no failure point, so it is a line "
            "nobody traced rather than a line that passed" % (line_id,)
        )
    for line_id in unprotected:
        findings.append(
            "line %s carries no protection, so the bound on a single failure "
            "was never the thing standing between it and a fault" % (line_id,)
        )

    result = {
        "lines": inventory,
        "failure_points": records,
        "multi_line_failures": offenders,
        "worst_fan_out": worst,
        "exposed_line_fraction": fraction,
        "untraced_protected_lines": untraced,
        "unprotected_lines": unprotected,
        "findings": findings,
    }

    if untraced and bool(policy["require_every_line_traced"]):
        result["verdict"] = CONTAINMENT_NOT_EVALUATED
    elif offenders:
        result["verdict"] = CONTAINMENT_MULTI_LINE_FAILURE
    elif not _at_most(fraction, ceiling):
        result["verdict"] = CONTAINMENT_EXPOSURE_OVER_CEILING
    elif unprotected:
        result["verdict"] = CONTAINMENT_UNPROTECTED_LINE
    else:
        result["verdict"] = CONTAINMENT_SATISFIED
    return result
