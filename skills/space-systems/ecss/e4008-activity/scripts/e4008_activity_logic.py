#!/usr/bin/env python3
"""Activities inside an SMP schedule task.

Anchor: ECSS-E-ST-40-08C clause 5.4.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An activity is the smallest thing a schedule does. A task is an
ordered list of them, and each one reaches into the assembled model:
it calls an entry point, writes a field, or emits an event. Because
an activity is resolved against the model rather than against the
schedule, most of what can be wrong with it is only visible when the
two artefacts are read together.

The clause's normative items reduce to fourteen implementable checks:

     1  the activity declares a kind
     2  the kind is one of the defined kinds
     3  the activity carries the payload of its own kind and nothing
        belonging to another kind
     4  the activity is named
     5  names are unique within the enclosing task
     6  the instance path it reaches into resolves in the assembly
     7  an entry-point activity names an entry point the instance's
        type declares
     8  an entry point takes no arguments, so an activity supplying
        them is refused rather than truncated
     9  a field activity names a field the instance's type declares
    10  that field is writable
    11  the assigned value matches the field's declared type
    12  the assigned value lies inside the field's declared range
    13  an event activity names an event the instance's type declares
    14  no activity advances simulated time or blocks, and two
        activities writing the same field in one sequence are
        order-dependent and reported as such

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

KIND_ENTRY_POINT = "entry-point"
KIND_FIELD_SET = "field-set"
KIND_EVENT_EMIT = "event-emit"
ACTIVITY_KINDS = (KIND_ENTRY_POINT, KIND_FIELD_SET, KIND_EVENT_EMIT)

KIND_PAYLOAD_KEYS = {
    KIND_ENTRY_POINT: ("entry_point",),
    KIND_FIELD_SET: ("field", "value"),
    KIND_EVENT_EMIT: ("event",),
}
ALL_PAYLOAD_KEYS = ("entry_point", "field", "value", "event")

VERDICT_ADMISSIBLE = "activity-admissible"
VERDICT_REJECTED = "activity-rejected"

FINDING_KIND_MISSING = "activity-kind-missing"
FINDING_KIND_UNKNOWN = "activity-kind-unknown"
FINDING_PAYLOAD_FOREIGN = "payload-belongs-to-another-kind"
FINDING_PAYLOAD_MISSING = "payload-missing-for-kind"
FINDING_NAME_MISSING = "activity-name-missing"
FINDING_NAME_DUPLICATE = "activity-name-duplicate-in-task"
FINDING_INSTANCE_UNRESOLVED = "instance-path-unresolved"
FINDING_ENTRY_POINT_UNKNOWN = "entry-point-not-on-type"
FINDING_ENTRY_POINT_ARGUMENTS = "entry-point-given-arguments"
FINDING_FIELD_UNKNOWN = "field-not-on-type"
FINDING_FIELD_READ_ONLY = "field-not-writable"
FINDING_VALUE_TYPE = "value-type-mismatch"
FINDING_VALUE_RANGE = "value-outside-declared-range"
FINDING_EVENT_UNKNOWN = "event-not-on-type"
FINDING_ADVANCES_TIME = "activity-advances-simulated-time"
FINDING_BLOCKING = "activity-blocks-the-scheduler"
FINDING_WRITE_ORDER = "same-field-written-twice-in-sequence"

INTEGER_TYPES = {
    "Int8": (-128, 127),
    "Int16": (-32768, 32767),
    "Int32": (-2147483648, 2147483647),
    "Int64": (-9223372036854775808, 9223372036854775807),
    "UInt8": (0, 255),
    "UInt16": (0, 65535),
    "UInt32": (0, 4294967295),
    "UInt64": (0, 18446744073709551615),
    "Duration": (-9223372036854775808, 9223372036854775807),
}
FLOAT_TYPES = ("Float32", "Float64")
FIELD_TYPES = tuple(sorted(INTEGER_TYPES)) + FLOAT_TYPES + ("Bool", "String8")

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list, got %r" % (name, value))
    return list(value)


def _text_or_none(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _finding(code, detail):
    return {"code": code, "detail": detail}


def _at_least(value, limit):
    """value >= limit, absorbing float representation error at the bound."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _not_above(value, limit):
    """value <= limit, absorbing float representation error at the bound."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_model(model):
    """Check the assembled model an activity is resolved against."""
    _require_mapping("model", model)
    instances = _require_mapping("model instances", model.get("instances", {}))
    types = _require_mapping("model types", model.get("types", {}))
    if not instances:
        raise ValueError("an activity cannot be resolved against an empty model")
    for path, entry in instances.items():
        if _text_or_none(path) is None:
            raise ValueError("instance path must be a non-empty string")
        _require_mapping("instance %s" % path, entry)
        type_name = _text_or_none(entry.get("type"))
        if type_name is None:
            raise ValueError("instance %s declares no type" % path)
        if type_name not in types:
            raise ValueError(
                "instance %s names a type %r the model does not declare"
                % (path, type_name)
            )
    for type_name, spec in types.items():
        _require_mapping("type %s" % type_name, spec)
        _require_sequence("type %s entry_points" % type_name, spec.get("entry_points", []))
        _require_sequence("type %s events" % type_name, spec.get("events", []))
        fields = _require_mapping("type %s fields" % type_name, spec.get("fields", {}))
        for field_name, field in fields.items():
            _require_mapping("field %s.%s" % (type_name, field_name), field)
            if field.get("type") not in FIELD_TYPES:
                raise ValueError(
                    "field %s.%s declares an unknown type %r"
                    % (type_name, field_name, field.get("type"))
                )
            low = field.get("min")
            high = field.get("max")
            if low is not None and high is not None and high < low:
                raise ValueError(
                    "field %s.%s declares a max below its min" % (type_name, field_name)
                )
    return model


def type_of(instance_path, model):
    """Type specification behind an instance path, or None."""
    entry = model.get("instances", {}).get(instance_path)
    if not isinstance(entry, dict):
        return None
    spec = model.get("types", {}).get(entry.get("type"))
    return spec if isinstance(spec, dict) else None


def value_matches_type(type_name, value):
    """Whether a value is of the declared field type at all."""
    if type_name not in FIELD_TYPES:
        raise ValueError("unknown field type %r" % (type_name,))
    if type_name == "Bool":
        return isinstance(value, bool)
    if type_name == "String8":
        return isinstance(value, str)
    if type_name in INTEGER_TYPES:
        return isinstance(value, int) and not isinstance(value, bool)
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def value_in_range(field, value):
    """Whether a typed value sits inside the field's admissible range.

    The width of the declared integer type is a range in its own
    right, and an explicit min or max narrows it further. Float bounds
    are compared with the representation error absorbed, so a value
    meant to sit exactly on a bound is not rejected for landing a few
    units in the last place outside it.
    """
    _require_mapping("field", field)
    type_name = field.get("type")
    if type_name in INTEGER_TYPES:
        low, high = INTEGER_TYPES[type_name]
        if value < low or value > high:
            return False
    if type_name in ("Bool", "String8"):
        return True
    declared_low = field.get("min")
    declared_high = field.get("max")
    number = float(value)
    if declared_low is not None and not _at_least(number, float(declared_low)):
        return False
    if declared_high is not None and not _not_above(number, float(declared_high)):
        return False
    return True


def evaluate_activity(activity, model):
    """Check one activity against the assembled model it reaches into."""
    _require_mapping("activity", activity)
    validate_model(model)
    findings = []

    name = _text_or_none(activity.get("name"))
    if name is None:
        findings.append(_finding(FINDING_NAME_MISSING, repr(activity.get("name"))))
    label = name or "unnamed activity"

    kind = activity.get("kind")
    if kind is None:
        findings.append(_finding(FINDING_KIND_MISSING, label))
    elif kind not in ACTIVITY_KINDS:
        findings.append(_finding(FINDING_KIND_UNKNOWN, "%s -> %r" % (label, kind)))

    if kind in ACTIVITY_KINDS:
        own = KIND_PAYLOAD_KEYS[kind]
        for key in ALL_PAYLOAD_KEYS:
            if key in own:
                continue
            if key in activity:
                findings.append(_finding(FINDING_PAYLOAD_FOREIGN, "%s -> %s" % (label, key)))
        for key in own:
            if key not in activity:
                findings.append(_finding(FINDING_PAYLOAD_MISSING, "%s -> %s" % (label, key)))

    duration = activity.get("duration_ns", 0)
    if isinstance(duration, bool) or not isinstance(duration, int):
        raise ValueError("%s duration_ns must be an integer" % label)
    if duration != 0:
        findings.append(_finding(FINDING_ADVANCES_TIME, "%s by %d ns" % (label, duration)))
    if activity.get("blocking", False):
        findings.append(_finding(FINDING_BLOCKING, label))

    path = _text_or_none(activity.get("instance"))
    spec = None if path is None else type_of(path, model)
    if spec is None:
        findings.append(_finding(FINDING_INSTANCE_UNRESOLVED, "%s -> %s" % (label, path)))
        return _result(label, kind, None, findings)

    target = None
    if kind == KIND_ENTRY_POINT:
        entry_point = _text_or_none(activity.get("entry_point"))
        if entry_point is not None:
            target = "%s.%s" % (path, entry_point)
            if entry_point not in spec.get("entry_points", []):
                findings.append(_finding(FINDING_ENTRY_POINT_UNKNOWN, target))
            arguments = activity.get("arguments")
            if arguments:
                findings.append(_finding(FINDING_ENTRY_POINT_ARGUMENTS, target))
    elif kind == KIND_FIELD_SET:
        field_name = _text_or_none(activity.get("field"))
        if field_name is not None:
            target = "%s.%s" % (path, field_name)
            field = spec.get("fields", {}).get(field_name)
            if field is None:
                findings.append(_finding(FINDING_FIELD_UNKNOWN, target))
            elif not field.get("writable", True):
                findings.append(_finding(FINDING_FIELD_READ_ONLY, target))
            elif "value" in activity:
                value = activity["value"]
                if not value_matches_type(field["type"], value):
                    findings.append(_finding(FINDING_VALUE_TYPE, target))
                elif not value_in_range(field, value):
                    findings.append(_finding(FINDING_VALUE_RANGE, target))
    elif kind == KIND_EVENT_EMIT:
        event = _text_or_none(activity.get("event"))
        if event is not None:
            target = "%s.%s" % (path, event)
            if event not in spec.get("events", []):
                findings.append(_finding(FINDING_EVENT_UNKNOWN, target))

    return _result(label, kind, target, findings)


def _result(label, kind, target, findings):
    return {
        "name": label,
        "kind": kind,
        "target": target,
        "admissible": not findings,
        "verdict": VERDICT_ADMISSIBLE if not findings else VERDICT_REJECTED,
        "findings": findings,
        "finding_codes": sorted({item["code"] for item in findings}),
    }


def evaluate_activity_sequence(activities, model, task_name="task"):
    """Check an ordered activity sequence, including its order hazards."""
    entries = _require_sequence("activities", activities)
    if not entries:
        raise ValueError("a task with no activities does nothing when it is triggered")
    validate_model(model)

    results = []
    findings = []
    seen_names = set()
    writes = {}

    for position, activity in enumerate(entries):
        result = evaluate_activity(activity, model)
        results.append(result)
        findings.extend(result["findings"])
        name = result["name"]
        if name != "unnamed activity":
            if name in seen_names:
                findings.append(
                    _finding(FINDING_NAME_DUPLICATE, "%s/%s" % (task_name, name))
                )
            seen_names.add(name)
        if result["kind"] == KIND_FIELD_SET and result["target"] is not None:
            writes.setdefault(result["target"], []).append(position)

    for target in sorted(writes):
        positions = writes[target]
        if len(positions) > 1:
            findings.append(
                _finding(
                    FINDING_WRITE_ORDER,
                    "%s written at positions %s; the last one wins"
                    % (target, ", ".join(str(item) for item in positions)),
                )
            )

    return {
        "task": task_name,
        "verdict": VERDICT_ADMISSIBLE if not findings else VERDICT_REJECTED,
        "admissible": not findings,
        "activities": results,
        "order": [item["name"] for item in results],
        "written_fields": sorted(writes),
        "findings": findings,
        "finding_codes": sorted({item["code"] for item in findings}),
    }
