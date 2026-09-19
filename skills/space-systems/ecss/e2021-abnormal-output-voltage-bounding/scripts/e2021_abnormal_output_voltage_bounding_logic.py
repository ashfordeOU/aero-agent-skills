#!/usr/bin/env python3
"""Abnormal output voltage bounding for actuator electronics under
ECSS-E-ST-20-21C clause 5.5.2.

Paraphrased, implementable procedure (no verbatim standard text):

* Whatever the actuator electronics does when it misbehaves, the voltage
  it can present at its output has to stay bounded by the voltage coming
  into it. The unit is allowed to fail; it is not allowed to invent
  potential the supply never gave it.
* The bound is a single number and it is the top of the input supply
  envelope, not the nominal bus and not the output rating. Comparing a
  fault peak against the nominal bus understates the bound and fails
  cases that comply; comparing it against the output rating is a
  different requirement entirely.
* An output that exceeds the bound has an internal path that lifted it.
  Stored energy in the actuator or harness inductance flying back, a
  boost stage, a charge pump, a transformer-coupled winding -- each is a
  design feature that has to be named, because an exceedance with no
  named path means the case was measured but not understood.
* A bounding statement is only as good as the fault set behind it. A case
  list that never covered a required fault category has not bounded the
  output; it has bounded the cases someone thought of, which is a
  coverage finding rather than a pass.
* Cases are grouped by the path that produced them, so a repeated
  inductive flyback across several lines reads as one design issue
  instead of as several unrelated exceedances.

Stdlib only, offline, deterministic. Arithmetic is restricted to the four
basic operations, and the bound comparison runs through a named tolerance
so a peak landing exactly on the supply bound does not turn on the last
bit of a subtraction.
"""

import math

# Named tolerance absorbing representation error in a voltage comparison.
# It is NOT a design allowance: the supply bound is never lifted.
VOLTAGE_EPS = 1e-9

NO_PATH = "none"
INDUCTIVE_KICK = "inductive-kick"
BOOST_CONVERSION = "boost-conversion"
CHARGE_PUMP = "charge-pump"
TRANSFORMER_COUPLED = "transformer-coupled"

EXCEEDANCE_PATHS = (
    NO_PATH,
    INDUCTIVE_KICK,
    BOOST_CONVERSION,
    CHARGE_PUMP,
    TRANSFORMER_COUPLED,
)

DRIVE_STAGE_SHORT = "drive-stage-short"
DRIVE_STAGE_OPEN = "drive-stage-open"
COMMAND_LOSS = "command-loss"
SUPPLY_TRANSIENT = "supply-transient"
ACTUATOR_DISCONNECT = "actuator-disconnect"
CONTROL_LOGIC_UPSET = "control-logic-upset"

FAULT_CATEGORIES = (
    DRIVE_STAGE_SHORT,
    DRIVE_STAGE_OPEN,
    COMMAND_LOSS,
    SUPPLY_TRANSIENT,
    ACTUATOR_DISCONNECT,
    CONTROL_LOGIC_UPSET,
)

REQUIRED_FAULT_CATEGORIES = (
    DRIVE_STAGE_SHORT,
    DRIVE_STAGE_OPEN,
    COMMAND_LOSS,
    SUPPLY_TRANSIENT,
)


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _at_most(value, ceiling_value):
    """True when value stays under ceiling_value, absorbing representation error."""
    return value <= ceiling_value or math.isclose(
        value, ceiling_value, rel_tol=0.0, abs_tol=VOLTAGE_EPS
    )


def supply_bound_v(supply):
    """The bound an abnormal output has to stay under: the supply ceiling."""
    if not isinstance(supply, dict):
        raise ValueError("supply must be a mapping, got %r" % (supply,))
    low = _require_number(supply.get("min_v"), "supply 'min_v'")
    high = _require_number(supply.get("max_v"), "supply 'max_v'")
    if low <= 0.0:
        raise ValueError("supply minimum must be positive, got %r" % (low,))
    if high < low:
        raise ValueError("supply maximum %r is below its minimum %r" % (high, low))
    return high


def bound_ratio(peak_v, bound_v):
    """Fault peak expressed as a fraction of the supply bound."""
    peak_v = _require_number(peak_v, "peak output voltage")
    bound_v = _require_number(bound_v, "supply bound")
    if bound_v <= 0.0:
        raise ValueError("supply bound must be positive, got %r" % (bound_v,))
    return peak_v / bound_v


def require_fault_category(category):
    """Validate that a fault case names a recognized category."""
    if category not in FAULT_CATEGORIES:
        raise ValueError(
            "unrecognized fault category %r (expected one of %s)"
            % (category, ", ".join(FAULT_CATEGORIES))
        )
    return category


def categorize_exceedance(case, bound_v):
    """Name the internal path that lifted an output above the supply bound."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    peak = _require_number(case.get("peak_output_voltage_v"), "case peak voltage")
    path = case.get("path", NO_PATH)
    if path not in EXCEEDANCE_PATHS:
        raise ValueError(
            "unrecognized exceedance path %r (expected one of %s)"
            % (path, ", ".join(EXCEEDANCE_PATHS))
        )
    if _at_most(peak, bound_v):
        return NO_PATH
    return path


def evaluate_case(case, bound_v):
    """Bounding verdict for one abnormal-output fault case."""
    bound_v = _require_number(bound_v, "supply bound")
    if bound_v <= 0.0:
        raise ValueError("supply bound must be positive, got %r" % (bound_v,))
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    name = _require_text(case.get("name"), "case 'name'")
    category = require_fault_category(case.get("category"))
    peak = _require_number(
        case.get("peak_output_voltage_v"), "case %r peak output voltage" % name
    )
    if peak < 0.0:
        raise ValueError(
            "case %r peak output voltage must not be negative, got %r" % (name, peak)
        )
    bounded = _at_most(peak, bound_v)
    path = categorize_exceedance(case, bound_v)
    return {
        "name": name,
        "category": category,
        "peak_output_voltage_v": peak,
        "supply_bound_v": bound_v,
        "exceedance_v": max(0.0, peak - bound_v),
        "bound_ratio": bound_ratio(peak, bound_v),
        "path": path,
        "path_named": bounded or path != NO_PATH,
        "bounded": bounded,
    }


def coverage_gaps(results, required=REQUIRED_FAULT_CATEGORIES):
    """Required fault categories the case list never covered."""
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a sequence, got %r" % (results,))
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required categories must be a non-empty sequence")
    for category in required:
        require_fault_category(category)
    covered = {result["category"] for result in results}
    return [category for category in required if category not in covered]


def group_by_path(results):
    """Exceeding cases grouped under the internal path that produced them."""
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a sequence, got %r" % (results,))
    grouped = {}
    for result in results:
        if result["bounded"]:
            continue
        grouped.setdefault(result["path"], []).append(result["name"])
    return grouped


def worst_case(results):
    """The case sitting highest relative to the supply bound."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    worst = results[0]
    for result in results[1:]:
        if result["bound_ratio"] > worst["bound_ratio"]:
            worst = result
    return worst


def bounding_status(findings):
    """Gate token for the finding list of one bounding assessment."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "output-bounded-by-supply" if not findings else "hold-output-bounding"


def evaluate_bounding(config):
    """End-to-end clause 5.5.2 bounding assessment over a fault case list."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    for key in ("supply", "cases"):
        if key not in config:
            raise ValueError("config missing required key %r" % (key,))
    cases = config["cases"]
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence")
    bound = supply_bound_v(config["supply"])
    results = [evaluate_case(case, bound) for case in cases]
    names = [result["name"] for result in results]
    if len(set(names)) != len(names):
        raise ValueError("case names must be unique, got %r" % (names,))
    required = config.get("required_categories", REQUIRED_FAULT_CATEGORIES)

    findings = []
    for result in results:
        if not result["bounded"]:
            findings.append(
                "%s presents %.6f V, exceeding the supply bound by %.6f V"
                % (result["name"], result["peak_output_voltage_v"], result["exceedance_v"])
            )
        if not result["path_named"]:
            findings.append(
                "%s exceeds the supply bound with no internal path named"
                % (result["name"],)
            )
    for category in coverage_gaps(results, required):
        findings.append("no fault case covers the required category %s" % (category,))

    worst = worst_case(results)
    return {
        "supply_bound_v": bound,
        "cases": results,
        "worst_case": worst,
        "worst_case_bound_ratio": worst["bound_ratio"],
        "paths": group_by_path(results),
        "coverage_gaps": coverage_gaps(results, required),
        "findings": findings,
        "status": bounding_status(findings),
        "bounded": not findings,
    }
