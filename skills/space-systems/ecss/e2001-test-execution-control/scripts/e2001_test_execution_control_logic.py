#!/usr/bin/env python3
"""Multipactor test execution control (ECSS-E-ST-20-01C clause 8.1).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
Execution of a multipactor test is controlled by a written detailed
procedure, and the evidence of control has two independent halves:

* the procedure as written -- does it carry the content the clause
  expects, is its declared step order consistent with the precedence the
  setup imposes, and is its power staircase sound;
* the execution log against that procedure -- was every step run, in
  order, and is every departure covered by an authorised deviation.

Either half can fail on its own. A complete procedure executed loosely
and a loose procedure executed exactly are both uncontrolled runs.
"""

import math

# Content elements a clause 8.1 procedure is expected to carry.
EXPECTED_PROCEDURE_ELEMENTS = (
    "item-identification",
    "test-configuration",
    "vacuum-conditions",
    "path-calibration-method",
    "detection-method-and-sensitivity",
    "power-profile",
    "abort-criteria",
    "data-recording",
    "pass-fail-criteria",
    "nonconformance-handling",
    "roles-and-authorisations",
)

# Canonical step identifiers a procedure may sequence.
KNOWN_STEPS = (
    "item-identity-check",
    "chamber-pumpdown",
    "vacuum-stabilisation",
    "path-calibration",
    "detection-baseline-check",
    "power-ramp",
    "hold-at-level",
    "power-down",
    "chamber-vent",
    "data-archive",
)

# Ordering the setup imposes: (earlier, later).
PRECEDENCE_PAIRS = (
    ("item-identity-check", "chamber-pumpdown"),
    ("chamber-pumpdown", "vacuum-stabilisation"),
    ("vacuum-stabilisation", "power-ramp"),
    ("path-calibration", "power-ramp"),
    ("detection-baseline-check", "power-ramp"),
    ("power-ramp", "hold-at-level"),
    ("hold-at-level", "power-down"),
    ("power-down", "chamber-vent"),
    ("chamber-vent", "data-archive"),
)

# Default floor on how long a level is held before it is believed.
DEFAULT_MIN_DWELL_S = 60.0
# Comparisons absorb representation error only; limits stay where they are.
REL_TOL = 1e-12
ABS_TOL = 1e-12

_DEVIATION_KEYS = ("step", "reason", "authorised_by")
_SCHEDULE_KEYS = ("level_w", "dwell_s")


def _as_float(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _positive(name, value):
    out = _as_float(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, out))
    return out


def _non_negative(name, value):
    out = _as_float(name, value)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %g" % (name, out))
    return out


def at_or_above(value, limit):
    """True when ``value`` reaches ``limit``, absorbing representation error."""
    value = _as_float("value", value)
    limit = _as_float("limit", limit)
    return value > limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def missing_procedure_elements(procedure_elements):
    """Expected content elements the written procedure does not carry."""
    if not isinstance(procedure_elements, (list, tuple, set, frozenset)):
        raise ValueError("procedure_elements must be a list, tuple or set of names")
    declared = set()
    for element in procedure_elements:
        if not isinstance(element, str) or not element:
            raise ValueError("procedure element %r must be a non-empty string" % (element,))
        declared.add(element)
    unknown = declared - set(EXPECTED_PROCEDURE_ELEMENTS)
    if unknown:
        raise ValueError(
            "unrecognised procedure elements: %s" % ", ".join(sorted(unknown))
        )
    return [name for name in EXPECTED_PROCEDURE_ELEMENTS if name not in declared]


def normalise_step_order(step_ids):
    """Validate a declared step order and return it as a list."""
    if not isinstance(step_ids, (list, tuple)):
        raise ValueError("step_ids must be a list or tuple of step identifiers")
    if len(step_ids) == 0:
        raise ValueError("step_ids must hold at least one step")
    order = []
    for step in step_ids:
        if step not in KNOWN_STEPS:
            raise ValueError(
                "unknown step identifier %r (expected one of %s)"
                % (step, ", ".join(KNOWN_STEPS))
            )
        if step in order:
            raise ValueError("step %r appears more than once in the declared order" % step)
        order.append(step)
    return order


def precedence_violations(step_ids):
    """Precedence pairs the declared order breaks, in canonical pair order."""
    order = normalise_step_order(step_ids)
    position = {step: index for index, step in enumerate(order)}
    violations = []
    for earlier, later in PRECEDENCE_PAIRS:
        if earlier in position and later in position:
            if position[earlier] > position[later]:
                violations.append(
                    {
                        "code": "step-precedence-broken",
                        "earlier": earlier,
                        "later": later,
                        "detail": "%s is declared after %s" % (earlier, later),
                    }
                )
    return violations


def required_test_level_w(nominal_power_w, margin_db):
    """Power level the test-margin puts above the nominal level."""
    nominal = _positive("nominal_power_w", nominal_power_w)
    margin = _non_negative("margin_db", margin_db)
    return nominal * 10.0 ** (margin / 10.0)


def validate_power_schedule(
    steps, required_level_w, min_dwell_s=DEFAULT_MIN_DWELL_S
):
    """Grade the power staircase for monotonicity, dwell and top level."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list or tuple of schedule entries")
    if len(steps) == 0:
        raise ValueError("steps must hold at least one power level")
    required = _positive("required_level_w", required_level_w)
    floor_dwell = _positive("min_dwell_s", min_dwell_s)
    levels, dwells = [], []
    for index, entry in enumerate(steps):
        if not isinstance(entry, dict):
            raise ValueError("steps[%d] must be a mapping with %s" % (index, ", ".join(_SCHEDULE_KEYS)))
        unknown = set(entry) - set(_SCHEDULE_KEYS)
        if unknown:
            raise ValueError(
                "steps[%d] carries unknown keys: %s" % (index, ", ".join(sorted(unknown)))
            )
        missing = [key for key in _SCHEDULE_KEYS if key not in entry]
        if missing:
            raise ValueError("steps[%d] missing %s" % (index, ", ".join(missing)))
        levels.append(_positive("steps[%d].level_w" % index, entry["level_w"]))
        dwells.append(_positive("steps[%d].dwell_s" % index, entry["dwell_s"]))
    findings = []
    for index in range(1, len(levels)):
        if levels[index] < levels[index - 1] and not math.isclose(
            levels[index], levels[index - 1], rel_tol=REL_TOL, abs_tol=ABS_TOL
        ):
            findings.append(
                {
                    "code": "power-step-not-monotonic",
                    "index": index,
                    "level_w": levels[index],
                    "previous_level_w": levels[index - 1],
                    "detail": "level %d drops from %.6g W to %.6g W"
                    % (index, levels[index - 1], levels[index]),
                }
            )
    for index, dwell in enumerate(dwells):
        if not at_or_above(dwell, floor_dwell):
            findings.append(
                {
                    "code": "dwell-too-short",
                    "index": index,
                    "dwell_s": dwell,
                    "min_dwell_s": floor_dwell,
                    "detail": "level %d held %.6g s, under the %.6g s floor"
                    % (index, dwell, floor_dwell),
                }
            )
    peak = max(levels)
    if not at_or_above(peak, required):
        findings.append(
            {
                "code": "test-level-not-reached",
                "peak_level_w": peak,
                "required_level_w": required,
                "detail": "staircase topped out at %.6g W, under the %.6g W the "
                "test-margin demands" % (peak, required),
            }
        )
    return findings


def categorize_deviation(record):
    """Name the control state of one departure record."""
    if not isinstance(record, dict):
        raise ValueError("deviation record must be a mapping")
    unknown = set(record) - set(_DEVIATION_KEYS)
    if unknown:
        raise ValueError(
            "deviation record carries unknown keys: %s" % ", ".join(sorted(unknown))
        )
    step = record.get("step")
    if step not in KNOWN_STEPS:
        raise ValueError("deviation record names unknown step %r" % (step,))
    reason = record.get("reason")
    authoriser = record.get("authorised_by")
    if not reason or not str(reason).strip():
        return "uncontrolled"
    if not authoriser or not str(authoriser).strip():
        return "unauthorised"
    return "authorised-deviation"


def deviation_index(deviation_records):
    """Map each step named in the records to its control state."""
    if deviation_records is None:
        return {}
    if not isinstance(deviation_records, (list, tuple)):
        raise ValueError("deviation_records must be a list or tuple of records")
    index = {}
    for record in deviation_records:
        state = categorize_deviation(record)
        step = record["step"]
        if step in index and index[step] != state:
            raise ValueError(
                "step %r carries contradictory deviation records" % step
            )
        index[step] = state
    return index


def evaluate_execution_log(declared_order, executed_steps, deviation_records=None):
    """Grade an execution log against the declared procedure order."""
    order = normalise_step_order(declared_order)
    executed = normalise_step_order(executed_steps)
    unexpected = [step for step in executed if step not in order]
    if unexpected:
        raise ValueError(
            "executed steps absent from the declared procedure: %s"
            % ", ".join(unexpected)
        )
    states = deviation_index(deviation_records)
    findings = []
    for step, state in states.items():
        if state == "uncontrolled":
            findings.append(
                {
                    "code": "deviation-without-reason",
                    "step": step,
                    "detail": "departure on %s recorded with no reason" % step,
                }
            )
        elif state == "unauthorised":
            findings.append(
                {
                    "code": "deviation-not-authorised",
                    "step": step,
                    "detail": "departure on %s has no named authoriser" % step,
                }
            )
    for step in order:
        if step not in executed and states.get(step) != "authorised-deviation":
            findings.append(
                {
                    "code": "step-not-executed-uncontrolled",
                    "step": step,
                    "detail": "%s was never executed and carries no authorised "
                    "deviation" % step,
                }
            )
    expected_sequence = [step for step in order if step in executed]
    if executed != expected_sequence:
        out_of_order = [
            step
            for step, expected in zip(executed, expected_sequence)
            if step != expected
        ]
        for step in out_of_order:
            if states.get(step) == "authorised-deviation":
                continue
            findings.append(
                {
                    "code": "step-order-violation",
                    "step": step,
                    "detail": "%s was executed out of the declared order" % step,
                }
            )
    return findings


def assess_test_execution_control(procedure, execution):
    """Full clause 8.1 assessment of one procedure and the run it drove."""
    if not isinstance(procedure, dict) or not isinstance(execution, dict):
        raise ValueError("procedure and execution must both be mappings")
    procedure_keys = {"elements", "step_order", "power_steps", "nominal_power_w",
                      "margin_db", "min_dwell_s"}
    execution_keys = {"executed_steps", "deviations"}
    unknown = (set(procedure) - procedure_keys) | (set(execution) - execution_keys)
    if unknown:
        raise ValueError("unknown keys: %s" % ", ".join(sorted(unknown)))
    for key in ("elements", "step_order", "power_steps", "nominal_power_w", "margin_db"):
        if key not in procedure:
            raise ValueError("procedure missing required key '%s'" % key)
    if "executed_steps" not in execution:
        raise ValueError("execution missing required key 'executed_steps'")

    findings = []
    missing_elements = missing_procedure_elements(procedure["elements"])
    for element in missing_elements:
        findings.append(
            {
                "code": "procedure-element-missing",
                "element": element,
                "detail": "procedure does not carry %s" % element,
            }
        )
    findings.extend(precedence_violations(procedure["step_order"]))
    required = required_test_level_w(
        procedure["nominal_power_w"], procedure["margin_db"]
    )
    findings.extend(
        validate_power_schedule(
            procedure["power_steps"],
            required,
            procedure.get("min_dwell_s", DEFAULT_MIN_DWELL_S),
        )
    )
    findings.extend(
        evaluate_execution_log(
            procedure["step_order"],
            execution["executed_steps"],
            execution.get("deviations"),
        )
    )
    return {
        "required_test_level_w": required,
        "missing_procedure_elements": missing_elements,
        "findings": findings,
        "controlled": not findings,
    }
