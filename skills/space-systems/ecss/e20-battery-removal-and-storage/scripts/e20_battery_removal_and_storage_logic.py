#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.6.4 -- battery module removal, replacement, storage.

Deterministic, offline, stdlib-only support logic for the pre-launch battery
handling case: a battery module has to be removable or replaceable on the
integrated spacecraft without silently invalidating the acceptance status the
unit already holds, and a removed module has to be stored inside an envelope
that keeps its cells healthy until re-installation.

The module implements four checkable pieces of engineering:

* access-path categorization -- how the module is reached drives which
  qualified interfaces are broken and therefore which delta re-verification
  tasks the removal triggers;
* open-circuit storage projection -- self-discharge doubles roughly every
  10 K above the reference storage temperature, so the state of charge a
  module reaches after a storage interval is computed, not assumed;
* storage-envelope screening -- temperature band, deep-discharge floor,
  shelf-life and humidity are screened, and each breach adds its own
  re-verification task;
* acceptance-status resolution -- the required task set is compared with the
  delta re-verification allowance agreed for the programme.

No verbatim standard text is reproduced; clause 5.6.4 is the anchor only.
"""

REFERENCE_STORAGE_TEMP_C = 20.0
TEMP_DOUBLING_INTERVAL_K = 10.0
ABSOLUTE_MIN_STORAGE_TEMP_C = -40.0
ABSOLUTE_MAX_STORAGE_TEMP_C = 60.0
DAYS_PER_MONTH = 30.0

# Access path -> which qualified interfaces the removal breaks and the delta
# re-verification tasks that follow from breaking them.
ACCESS_PATHS = {
    "direct-hatch-access": {
        "breaks_qualified_interface": False,
        "removable": True,
        "tasks": ("visual-condition-check", "insulation-resistance-check"),
    },
    "panel-removal": {
        "breaks_qualified_interface": False,
        "removable": True,
        "tasks": (
            "visual-condition-check",
            "insulation-resistance-check",
            "fastener-torque-recheck",
        ),
    },
    "harness-demate": {
        "breaks_qualified_interface": True,
        "removable": True,
        "tasks": (
            "visual-condition-check",
            "insulation-resistance-check",
            "harness-continuity-check",
            "bonding-resistance-check",
        ),
    },
    "stack-teardown": {
        "breaks_qualified_interface": True,
        "removable": True,
        "tasks": (
            "visual-condition-check",
            "insulation-resistance-check",
            "harness-continuity-check",
            "bonding-resistance-check",
            "battery-capacity-retest",
            "workmanship-vibration-retest",
        ),
    },
    "non-removable": {
        "breaks_qualified_interface": True,
        "removable": False,
        "tasks": (),
    },
}

# Storage-envelope breach -> the extra re-verification task it forces.
BREACH_TASKS = {
    "storage-temperature-excursion": "battery-capacity-retest",
    "deep-discharge-below-floor": "cell-health-assessment",
    "shelf-life-exceeded": "battery-capacity-retest",
    "humidity-limit-exceeded": "insulation-resistance-check",
}

_REQUIRED_MODULE_KEYS = (
    "module_id",
    "access_path",
    "initial_soc_pct",
    "base_self_discharge_pct_per_month",
    "storage_temp_c",
    "storage_days",
    "min_storage_soc_pct",
    "min_storage_temp_c",
    "max_storage_temp_c",
    "max_storage_days",
    "storage_humidity_pct",
    "max_storage_humidity_pct",
)


def _as_float(value, field):
    """Coerce a numeric field, rejecting bools and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("field %r must be a real number, got %r" % (field, value))
    return float(value)


def validate_module(module):
    """Return a normalized module record or raise ValueError.

    Checks presence of every required key, numeric types, percentage ranges,
    a coherent storage temperature band and a known access path.
    """
    if not isinstance(module, dict):
        raise ValueError("module must be a mapping, got %r" % type(module).__name__)
    missing = [k for k in _REQUIRED_MODULE_KEYS if k not in module]
    if missing:
        raise ValueError(
            "module missing required field(s): %s" % ", ".join(sorted(missing))
        )
    module_id = module["module_id"]
    if not isinstance(module_id, str) or not module_id.strip():
        raise ValueError("module_id must be a non-empty string")
    access_path = module["access_path"]
    if access_path not in ACCESS_PATHS:
        raise ValueError(
            "unknown access_path %r; expected one of %s"
            % (access_path, ", ".join(sorted(ACCESS_PATHS)))
        )
    out = {"module_id": module_id.strip(), "access_path": access_path}
    for key in _REQUIRED_MODULE_KEYS[2:]:
        out[key] = _as_float(module[key], key)
    for key in (
        "initial_soc_pct",
        "min_storage_soc_pct",
        "storage_humidity_pct",
        "max_storage_humidity_pct",
    ):
        if not 0.0 <= out[key] <= 100.0:
            raise ValueError(
                "%s must be within 0..100 percent, got %g" % (key, out[key])
            )
    if out["base_self_discharge_pct_per_month"] <= 0.0:
        raise ValueError("base_self_discharge_pct_per_month must be > 0")
    if out["storage_days"] < 0.0 or out["max_storage_days"] <= 0.0:
        raise ValueError("storage_days must be >= 0 and max_storage_days must be > 0")
    if out["min_storage_temp_c"] >= out["max_storage_temp_c"]:
        raise ValueError("min_storage_temp_c must be below max_storage_temp_c")
    if out["initial_soc_pct"] <= out["min_storage_soc_pct"]:
        raise ValueError("initial_soc_pct must start above min_storage_soc_pct")
    return out


def categorize_access_path(access_path):
    """Return the access-path record (removability + triggered task set)."""
    record = ACCESS_PATHS.get(access_path)
    if record is None:
        raise ValueError(
            "unknown access_path %r; expected one of %s"
            % (access_path, ", ".join(sorted(ACCESS_PATHS)))
        )
    return dict(record)


def self_discharge_rate_pct_per_month(base_rate_pct_per_month, storage_temp_c):
    """Temperature-corrected self-discharge rate.

    The rate doubles for every 10 K above the 20 degC reference and halves
    for every 10 K below it.
    """
    base = _as_float(base_rate_pct_per_month, "base_rate_pct_per_month")
    temp = _as_float(storage_temp_c, "storage_temp_c")
    if base <= 0.0:
        raise ValueError("base self-discharge rate must be > 0, got %g" % base)
    if not ABSOLUTE_MIN_STORAGE_TEMP_C <= temp <= ABSOLUTE_MAX_STORAGE_TEMP_C:
        raise ValueError(
            "storage temperature %g degC outside the modelled band %g..%g"
            % (temp, ABSOLUTE_MIN_STORAGE_TEMP_C, ABSOLUTE_MAX_STORAGE_TEMP_C)
        )
    exponent = (temp - REFERENCE_STORAGE_TEMP_C) / TEMP_DOUBLING_INTERVAL_K
    return base * (2.0 ** exponent)


def project_storage_state_of_charge(initial_soc_pct, base_rate, storage_temp_c, days):
    """Open-circuit state of charge reached after `days` of storage."""
    soc = _as_float(initial_soc_pct, "initial_soc_pct")
    span = _as_float(days, "days")
    if not 0.0 <= soc <= 100.0:
        raise ValueError("initial_soc_pct must be within 0..100, got %g" % soc)
    if span < 0.0:
        raise ValueError("storage duration must be >= 0 days, got %g" % span)
    rate = self_discharge_rate_pct_per_month(base_rate, storage_temp_c)
    lost = rate * (span / DAYS_PER_MONTH)
    return max(0.0, soc - lost)


def maintenance_charge_interval_days(initial_soc_pct, floor_soc_pct, base_rate, temp_c):
    """Days of open-circuit storage before the module reaches its SoC floor."""
    soc = _as_float(initial_soc_pct, "initial_soc_pct")
    floor = _as_float(floor_soc_pct, "floor_soc_pct")
    if not 0.0 <= floor < soc <= 100.0:
        raise ValueError(
            "need 0 <= floor_soc_pct < initial_soc_pct <= 100, got floor=%g initial=%g"
            % (floor, soc)
        )
    rate = self_discharge_rate_pct_per_month(base_rate, temp_c)
    return (soc - floor) / rate * DAYS_PER_MONTH


def evaluate_storage_envelope(module):
    """Screen the storage plan and return (projected_soc_pct, breaches)."""
    rec = validate_module(module)
    breaches = []
    if (
        rec["storage_temp_c"] < rec["min_storage_temp_c"]
        or rec["storage_temp_c"] > rec["max_storage_temp_c"]
    ):
        breaches.append("storage-temperature-excursion")
    projected = project_storage_state_of_charge(
        rec["initial_soc_pct"],
        rec["base_self_discharge_pct_per_month"],
        rec["storage_temp_c"],
        rec["storage_days"],
    )
    if projected < rec["min_storage_soc_pct"]:
        breaches.append("deep-discharge-below-floor")
    if rec["storage_days"] > rec["max_storage_days"]:
        breaches.append("shelf-life-exceeded")
    if rec["storage_humidity_pct"] > rec["max_storage_humidity_pct"]:
        breaches.append("humidity-limit-exceeded")
    return projected, breaches


def required_reverification(access_path, breaches=()):
    """Ordered, de-duplicated delta re-verification task set."""
    record = categorize_access_path(access_path)
    tasks = list(record["tasks"])
    for breach in breaches:
        task = BREACH_TASKS.get(breach)
        if task is None:
            raise ValueError("unknown storage breach %r" % (breach,))
        if task not in tasks:
            tasks.append(task)
    return tuple(tasks)


def acceptance_status_after_removal(required_tasks, delta_allowance, removable):
    """Resolve the acceptance state the module holds after the operation."""
    if not isinstance(removable, bool):
        raise ValueError("removable must be a boolean, got %r" % (removable,))
    if not isinstance(delta_allowance, (list, tuple, set, frozenset)):
        raise ValueError("delta_allowance must be a collection of task names")
    if not removable:
        return "invalidated-module-not-removable", tuple(sorted(required_tasks))
    allowed = set(delta_allowance)
    uncovered = tuple(sorted(t for t in required_tasks if t not in allowed))
    if uncovered:
        return "invalidated-reverification-not-covered", uncovered
    return "preserved-with-delta-reverification", ()


def plan_removal_and_storage(module, delta_allowance):
    """Full clause 5.6.4 assessment for one battery module."""
    rec = validate_module(module)
    projected, breaches = evaluate_storage_envelope(rec)
    record = categorize_access_path(rec["access_path"])
    tasks = required_reverification(rec["access_path"], breaches)
    state, uncovered = acceptance_status_after_removal(
        tasks, delta_allowance, record["removable"]
    )
    interval = maintenance_charge_interval_days(
        rec["initial_soc_pct"],
        rec["min_storage_soc_pct"],
        rec["base_self_discharge_pct_per_month"],
        rec["storage_temp_c"],
    )
    return {
        "module_id": rec["module_id"],
        "access_path": rec["access_path"],
        "removable": record["removable"],
        "breaks_qualified_interface": record["breaks_qualified_interface"],
        "projected_soc_pct": projected,
        "maintenance_charge_interval_days": interval,
        "storage_breaches": tuple(breaches),
        "required_reverification": tasks,
        "uncovered_reverification": uncovered,
        "acceptance_state": state,
        "compliant": state == "preserved-with-delta-reverification" and not breaches,
    }


if __name__ == "__main__":  # pragma: no cover - manual smoke run
    demo = {
        "module_id": "BAT-M1",
        "access_path": "panel-removal",
        "initial_soc_pct": 60.0,
        "base_self_discharge_pct_per_month": 3.0,
        "storage_temp_c": 20.0,
        "storage_days": 90.0,
        "min_storage_soc_pct": 40.0,
        "min_storage_temp_c": 0.0,
        "max_storage_temp_c": 30.0,
        "max_storage_days": 180.0,
        "storage_humidity_pct": 45.0,
        "max_storage_humidity_pct": 60.0,
    }
    allowance = [
        "visual-condition-check",
        "insulation-resistance-check",
        "fastener-torque-recheck",
    ]
    for key, value in sorted(plan_removal_and_storage(demo, allowance).items()):
        print("%-32s %s" % (key, value))
