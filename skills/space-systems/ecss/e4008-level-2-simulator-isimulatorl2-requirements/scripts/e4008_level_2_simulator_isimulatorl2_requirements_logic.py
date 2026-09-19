"""Level 2 simulator interface conformance.

Anchor: ECSS-E-ST-40-08C clause 5.5.4.2 (level 2 Simulator, ISimulatorL2,
requirements). Paraphrased into an implementable procedure; no standard
text is reproduced. The clause carries seven normative items.

Model implemented here
----------------------
A level 1 simulator can be built, run and stopped. A level 2 simulator
adds the operations an operator-facing or test-harness-facing simulator
needs: holding and resuming a run, saving and reloading the whole tree,
stepping by a bounded amount, and changing the wall-clock-to-simulated
time ratio. Each added operation is only meaningful from some of the
simulator states, so the interface is graded on three axes at once:

* completeness  -- every level 2 operation is offered, and the level 1
  set it extends is offered too (a level 2 interface that dropped a
  level 1 operation is not a superset, it is a different interface);
* state guarding -- each operation declares the states it is callable
  from, and those states are a subset of the ones the model permits;
* idempotence and bounds -- hold from hold, resume from run, a
  non-positive step and a non-positive time scale all have a defined
  answer rather than undefined behaviour.
"""

__all__ = [
    "NORMATIVE_ITEM_COUNT",
    "NORMATIVE_ITEMS",
    "LEVEL1_OPERATIONS",
    "LEVEL2_OPERATIONS",
    "SIMULATOR_STATES",
    "PERMITTED_STATES",
    "MAX_STEP_TICKS",
    "validate_operation_name",
    "missing_operations",
    "unexpected_operations",
    "validate_state_set",
    "check_state_guard",
    "validate_step_request",
    "validate_time_scale",
    "assess_level2_interface",
]

NORMATIVE_ITEM_COUNT = 7

NORMATIVE_ITEMS = (
    ("L2-01", "the level 1 operation set is offered unchanged"),
    ("L2-02", "every level 2 operation is offered"),
    ("L2-03", "no operation outside the two sets is presented as level 2"),
    ("L2-04", "each operation is callable only from the states that permit it"),
    ("L2-05", "hold and resume are idempotent rather than undefined"),
    ("L2-06", "a step request carries a positive bounded duration"),
    ("L2-07", "the time scale is positive and finite"),
)

LEVEL1_OPERATIONS = ("publish", "configure", "connect", "initialise", "run", "exit")

LEVEL2_OPERATIONS = ("hold", "resume", "store", "restore", "step", "set_time_scale", "abort")

SIMULATOR_STATES = (
    "building",
    "connecting",
    "initialising",
    "standby",
    "executing",
    "storing",
    "restoring",
    "reconnecting",
    "exiting",
    "aborting",
)

# The states each operation is meaningful from. An implementation may
# declare a narrower set; declaring a wider one is a state-guard defect.
PERMITTED_STATES = {
    "publish": ("building",),
    "configure": ("building",),
    "connect": ("connecting",),
    "initialise": ("initialising",),
    "run": ("standby",),
    "exit": ("standby", "executing"),
    "hold": ("executing",),
    "resume": ("standby",),
    "store": ("standby",),
    "restore": ("standby",),
    "step": ("standby",),
    "set_time_scale": ("standby", "executing"),
    "abort": ("standby", "executing", "storing", "restoring", "reconnecting"),
}

# A step longer than this is a run, not a step; the bound keeps a
# harness from hanging on a mistyped duration.
MAX_STEP_TICKS = 10 ** 12


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def validate_operation_name(name):
    """Return the canonical form of an interface operation name."""
    text = _require_text(name, "operation name").lower().replace("-", "_").replace(" ", "_")
    if text not in PERMITTED_STATES:
        raise ValueError(
            "operation %r belongs to neither the level 1 nor the level 2 set" % (name,)
        )
    return text


def _canonical_set(operations, label):
    if not isinstance(operations, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a sequence of operation names" % label)
    out = []
    for item in operations:
        text = _require_text(item, "%s entry" % label).lower().replace("-", "_").replace(" ", "_")
        if text not in out:
            out.append(text)
    return out


def missing_operations(offered, required):
    """Return the required operations the interface does not offer."""
    have = _canonical_set(offered, "offered operations")
    want = _canonical_set(required, "required operations")
    return [name for name in want if name not in have]


def unexpected_operations(offered):
    """Return the offered operations that belong to neither declared set."""
    have = _canonical_set(offered, "offered operations")
    known = set(LEVEL1_OPERATIONS) | set(LEVEL2_OPERATIONS)
    return [name for name in have if name not in known]


def validate_state_set(states, label="states"):
    """Return the canonical state set, refusing an unknown state."""
    if not isinstance(states, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a sequence of state names" % label)
    out = []
    for item in states:
        text = _require_text(item, "%s entry" % label).lower()
        if text not in SIMULATOR_STATES:
            raise ValueError("%s names an unknown simulator state %r" % (label, item))
        if text not in out:
            out.append(text)
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def check_state_guard(operation, declared_states):
    """Return the verdict on the states an operation declares itself callable from."""
    name = validate_operation_name(operation)
    declared = validate_state_set(declared_states, "declared states for %r" % name)
    permitted = PERMITTED_STATES[name]
    widened = [s for s in declared if s not in permitted]
    findings = []
    if widened:
        findings.append(
            "operation %r declares itself callable from %s, outside the permitted set %s"
            % (name, ", ".join(widened), ", ".join(permitted))
        )
    return {
        "operation": name,
        "declared": declared,
        "permitted": list(permitted),
        "widened": widened,
        "narrowed": [s for s in permitted if s not in declared],
        "compliant": not findings,
        "findings": findings,
    }


def validate_step_request(ticks):
    """Return the validated step duration in infrastructure ticks."""
    if not isinstance(ticks, int) or isinstance(ticks, bool):
        raise ValueError("step duration must be an integer tick count, got %r" % (ticks,))
    if ticks <= 0:
        raise ValueError("step duration must be positive, got %d" % ticks)
    if ticks > MAX_STEP_TICKS:
        raise ValueError(
            "step duration %d exceeds the bound %d; that is a run, not a step"
            % (ticks, MAX_STEP_TICKS)
        )
    return ticks


def validate_time_scale(scale):
    """Return the validated simulated-to-wall-clock time scale."""
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        raise ValueError("time scale must be a real number, got %r" % (scale,))
    value = float(scale)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("time scale must be finite, got %r" % (scale,))
    if value <= 0.0:
        raise ValueError("time scale must be positive, got %g" % value)
    return value


def assess_level2_interface(spec):
    """Grade a level 2 simulator interface against the seven normative items.

    spec keys: operations (required sequence of offered operation names),
    state_guards (mapping operation -> declared states), hold_idempotent,
    resume_idempotent, step_ticks, time_scale.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "operations" not in spec:
        raise ValueError("spec missing required key 'operations'")
    offered = _canonical_set(spec["operations"], "spec['operations']")
    if not offered:
        raise ValueError("spec['operations'] must not be empty")

    detail = dict((item_id, []) for item_id, _ in NORMATIVE_ITEMS)

    missing_l1 = [n for n in LEVEL1_OPERATIONS if n not in offered]
    if missing_l1:
        detail["L2-01"].append(
            "level 1 operation(s) absent from the level 2 interface: %s" % ", ".join(missing_l1)
        )
    missing_l2 = [n for n in LEVEL2_OPERATIONS if n not in offered]
    if missing_l2:
        detail["L2-02"].append(
            "level 2 operation(s) absent: %s" % ", ".join(missing_l2)
        )
    extras = unexpected_operations(offered)
    if extras:
        detail["L2-03"].append(
            "operation(s) outside both declared sets: %s" % ", ".join(extras)
        )

    guards = spec.get("state_guards", {})
    if not isinstance(guards, dict):
        raise ValueError("spec['state_guards'] must be a mapping when given")
    guard_results = {}
    for operation in sorted(guards):
        result = check_state_guard(operation, guards[operation])
        guard_results[result["operation"]] = result
        detail["L2-04"].extend(result["findings"])

    for key, item_id in (("hold_idempotent", "L2-05"), ("resume_idempotent", "L2-05")):
        if key in spec:
            value = spec[key]
            if not isinstance(value, bool):
                raise ValueError("%s must be a boolean when given" % key)
            if not value:
                detail[item_id].append(
                    "%s is undefined rather than idempotent" % key.replace("_idempotent", "")
                )

    if "step_ticks" in spec:
        try:
            validate_step_request(spec["step_ticks"])
        except ValueError as exc:
            detail["L2-06"].append(str(exc))

    if "time_scale" in spec:
        try:
            validate_time_scale(spec["time_scale"])
        except ValueError as exc:
            detail["L2-07"].append(str(exc))

    items = []
    findings = []
    for item_id, title in NORMATIVE_ITEMS:
        entries = detail[item_id]
        items.append({
            "id": item_id,
            "title": title,
            "status": "satisfied" if not entries else "violated",
            "findings": list(entries),
        })
        findings.extend(entries)
    return {
        "items": items,
        "item_count": len(items),
        "offered": offered,
        "missing_level1": missing_l1,
        "missing_level2": missing_l2,
        "unexpected": extras,
        "state_guards": guard_results,
        "violations": [i["id"] for i in items if i["status"] == "violated"],
        "findings": findings,
        "compliant": not findings,
    }
