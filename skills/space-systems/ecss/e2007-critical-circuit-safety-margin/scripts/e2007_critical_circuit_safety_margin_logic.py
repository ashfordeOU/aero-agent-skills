#!/usr/bin/env python3
"""Safety margin demonstration for critical circuits and electro-explosive
device firing lines under ECSS-E-ST-20-07C clause 5.3.2.

Paraphrased, implementable procedure (no verbatim standard text):

* A circuit whose malfunction endangers the mission or the launch team is
  not verified by showing that it survived the test. It is verified by
  showing, in decibels, how far the level induced on it sits below the
  level at which it would respond.
* The margin is a ratio expressed logarithmically. For an amplitude
  quantity -- a current or a voltage -- the ratio is taken twenty times its
  base-ten logarithm; for a power quantity, ten times. Using the amplitude
  form on a power reading doubles the claimed margin, which is the classic
  way a firing line is reported safe when it is not.
* An electro-explosive device firing line is compared not with the no-fire
  level itself but with a derated no-fire level, so the bridgewire
  population spread and the measurement uncertainty are inside the
  demonstration rather than argued around it.
* The required margin depends on what the circuit does. A firing line and a
  safety-critical circuit carry the largest requirement; a mission-critical
  circuit less; a non-critical circuit least. Each is a specification
  value, not a constant of nature, so each is overridable.
* The demonstration is graded on the worst circuit, not on the average.
  One line short of its requirement holds the verification, and the report
  names that line.

Stdlib only, offline, deterministic. Every logarithmic comparison is made
through a named tolerance, because a base-ten logarithm is not correctly
rounded and a boundary case must not depend on which side of the last bit a
particular library lands.

* A vehicle that carries initiators must show a firing line on the record.
  A demonstration listing only signal circuits has not covered the lines
  that fire something, and the record says so rather than staying silent.
"""

import math

# Named tolerance absorbing representation error in decibel sums and
# differences. It is NOT an engineering allowance: the required margins
# themselves are never reduced.
MARGIN_EPS = 1e-9

AMPLITUDE = "amplitude"
POWER = "power"
QUANTITY_KINDS = (AMPLITUDE, POWER)

# Decibel multiplier per quantity kind.
_KIND_MULTIPLIER = {AMPLITUDE: 20.0, POWER: 10.0}

EED_FIRING_LINE = "eed-firing-line"
SAFETY_CRITICAL_CIRCUIT = "safety-critical-circuit"
MISSION_CRITICAL_CIRCUIT = "mission-critical-circuit"
NON_CRITICAL_CIRCUIT = "non-critical-circuit"

CIRCUIT_CATEGORIES = (
    EED_FIRING_LINE,
    SAFETY_CRITICAL_CIRCUIT,
    MISSION_CRITICAL_CIRCUIT,
    NON_CRITICAL_CIRCUIT,
)

# Categories whose threshold is derated before the comparison.
DERATED_CATEGORIES = (EED_FIRING_LINE,)

_CATEGORY_SPEC_KEY = {
    EED_FIRING_LINE: "required_margin_db_eed_firing_line",
    SAFETY_CRITICAL_CIRCUIT: "required_margin_db_safety_critical_circuit",
    MISSION_CRITICAL_CIRCUIT: "required_margin_db_mission_critical_circuit",
    NON_CRITICAL_CIRCUIT: "required_margin_db_non_critical_circuit",
}

DEFAULT_MARGIN_SPEC = {
    "required_margin_db_eed_firing_line": 20.0,
    "required_margin_db_safety_critical_circuit": 20.0,
    "required_margin_db_mission_critical_circuit": 12.0,
    "required_margin_db_non_critical_circuit": 6.0,
    "eed_no_fire_derating_factor": 0.5,
}


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


def _at_least(value, floor_value):
    """True when value reaches floor_value, absorbing representation error."""
    return value >= floor_value or math.isclose(
        value, floor_value, rel_tol=0.0, abs_tol=MARGIN_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the standard margin specification."""
    spec = dict(DEFAULT_MARGIN_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_MARGIN_SPEC:
            raise ValueError("unrecognized margin specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if key == "eed_no_fire_derating_factor":
            if not (0.0 < number <= 1.0):
                raise ValueError(
                    "eed_no_fire_derating_factor must lie in (0, 1], got %r" % (value,)
                )
        elif number < 0.0:
            raise ValueError("spec %r must not be negative, got %r" % (key, value))
        spec[key] = number
    return spec


def quantity_multiplier(kind):
    """Decibel multiplier for an amplitude or a power quantity."""
    if kind not in _KIND_MULTIPLIER:
        raise ValueError(
            "unrecognized quantity kind %r (expected one of %s)"
            % (kind, ", ".join(QUANTITY_KINDS))
        )
    return _KIND_MULTIPLIER[kind]


def margin_db(threshold, induced, kind=AMPLITUDE):
    """Margin in decibels between a response threshold and an induced level."""
    multiplier = quantity_multiplier(kind)
    threshold = _require_number(threshold, "threshold")
    induced = _require_number(induced, "induced")
    if threshold <= 0.0:
        raise ValueError("threshold must be positive, got %r" % (threshold,))
    if induced <= 0.0:
        raise ValueError("induced level must be positive, got %r" % (induced,))
    return multiplier * math.log10(threshold / induced)


def derated_threshold(threshold, factor):
    """Threshold after the derating that precedes a firing-line comparison."""
    threshold = _require_number(threshold, "threshold")
    factor = _require_number(factor, "derating factor")
    if threshold <= 0.0:
        raise ValueError("threshold must be positive, got %r" % (threshold,))
    if not (0.0 < factor <= 1.0):
        raise ValueError("derating factor must lie in (0, 1], got %r" % (factor,))
    return threshold * factor


def required_margin_db(category, spec=None):
    """Margin a circuit of this category has to demonstrate."""
    if category not in _CATEGORY_SPEC_KEY:
        raise ValueError(
            "unrecognized circuit category %r (expected one of %s)"
            % (category, ", ".join(CIRCUIT_CATEGORIES))
        )
    spec = resolve_spec(spec)
    return spec[_CATEGORY_SPEC_KEY[category]]


def evaluate_circuit(circuit, spec=None):
    """Margin demonstration for one critical circuit or firing line."""
    resolved = resolve_spec(spec)
    if not isinstance(circuit, dict):
        raise ValueError("circuit must be a mapping, got %r" % (circuit,))
    name = _require_text(circuit.get("name"), "circuit 'name'")
    category = circuit.get("category")
    if category not in CIRCUIT_CATEGORIES:
        raise ValueError(
            "circuit %r has unrecognized category %r (expected one of %s)"
            % (name, category, ", ".join(CIRCUIT_CATEGORIES))
        )
    kind = circuit.get("quantity_kind", AMPLITUDE)
    multiplier = quantity_multiplier(kind)
    threshold = _require_number(
        circuit.get("threshold"), "circuit %r threshold" % name
    )
    induced = _require_number(circuit.get("induced"), "circuit %r induced" % name)
    if threshold <= 0.0:
        raise ValueError("circuit %r threshold must be positive, got %r" % (name, threshold))
    if induced <= 0.0:
        raise ValueError("circuit %r induced must be positive, got %r" % (name, induced))

    if category in DERATED_CATEGORIES:
        factor = resolved["eed_no_fire_derating_factor"]
        applied = derated_threshold(threshold, factor)
    else:
        factor = 1.0
        applied = threshold

    demonstrated = margin_db(applied, induced, kind)
    required = required_margin_db(category, spec)
    compliant = _at_least(demonstrated, required)
    return {
        "name": name,
        "category": category,
        "quantity_kind": kind,
        "multiplier": multiplier,
        "threshold": threshold,
        "derating_factor": factor,
        "applied_threshold": applied,
        "induced": induced,
        "margin_db": demonstrated,
        "required_margin_db": required,
        "shortfall_db": max(0.0, required - demonstrated),
        "compliant": compliant,
    }


def remaining_margin_db(result):
    """Decibels a circuit holds above its own requirement."""
    if not isinstance(result, dict):
        raise ValueError("result must be a mapping, got %r" % (result,))
    for key in ("margin_db", "required_margin_db"):
        if key not in result:
            raise ValueError("result missing required key %r" % (key,))
    return result["margin_db"] - result["required_margin_db"]


def worst_case_circuit(results):
    """The circuit holding the least margin above its own requirement."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    worst = results[0]
    worst_remaining = remaining_margin_db(worst)
    for result in results[1:]:
        remaining = remaining_margin_db(result)
        if remaining < worst_remaining:
            worst, worst_remaining = result, remaining
    return worst


def verification_status(findings):
    """Gate token for the finding list of one margin demonstration."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "margin-demonstrated" if not findings else "hold-margin-verification"


def evaluate_campaign(config):
    """End-to-end clause 5.3.2 margin demonstration for a set of circuits."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    if "circuits" not in config:
        raise ValueError("config missing required key 'circuits'")
    circuits = config["circuits"]
    if not isinstance(circuits, (list, tuple)) or not circuits:
        raise ValueError("circuits must be a non-empty sequence")
    spec = resolve_spec(config.get("spec"))
    results = [evaluate_circuit(circuit, config.get("spec")) for circuit in circuits]
    names = [result["name"] for result in results]
    if len(set(names)) != len(names):
        raise ValueError("circuit names must be unique, got %r" % (names,))

    findings = []
    for result in results:
        if not result["compliant"]:
            findings.append(
                "%s demonstrates %.3f dB against a requirement of %.3f dB"
                % (result["name"], result["margin_db"], result["required_margin_db"])
            )
    eed_installed = config.get("eed_installed", True)
    if not isinstance(eed_installed, bool):
        raise ValueError("eed_installed must be a boolean, got %r" % (eed_installed,))
    if eed_installed and not any(r["category"] == EED_FIRING_LINE for r in results):
        findings.append("no electro-explosive device firing line on the demonstration record")

    worst = worst_case_circuit(results)
    return {
        "spec": spec,
        "circuits": results,
        "worst_case": worst,
        "worst_case_remaining_db": remaining_margin_db(worst),
        "findings": findings,
        "status": verification_status(findings),
        "demonstrated": not findings,
    }
