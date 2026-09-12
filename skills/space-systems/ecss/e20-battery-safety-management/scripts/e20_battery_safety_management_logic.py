#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.6.5.2 -- battery safety management.

Deterministic, offline, stdlib-only support logic for the battery safety
case: battery hazards are managed under the product assurance route for
space safety, which means every hazard carries a severity, a control
strategy sized by that severity, an inhibit chain whose members are
independent and verifiable, and a traceable link to the safety requirement
that owns it.

Implemented engineering:

* hazard categorization -- severity and likelihood are mapped onto ordered
  scales and refused when they are not on the scale at all;
* control sizing -- severity plus hazard family decide how many independent
  inhibits are demanded, whether a containment provision is demanded instead
  of an extra inhibit, and whether a cell-to-cell propagation barrier is
  demanded on top;
* inhibit-chain evaluation -- only inhibits that are both independent and
  verifiable count towards the achieved failure tolerance;
* propagation margin -- the thermal margin between the predicted cell
  surface temperature and the runaway onset temperature is computed and
  compared against the required margin;
* residual risk -- severity and likelihood combine into a risk index and an
  acceptance band, and an unacceptable band is itself a finding.

No verbatim standard text is reproduced; clause 5.6.5.2 and the product
assurance space-safety standard are cited as anchors only.
"""

SEVERITY_LEVELS = ("negligible", "marginal", "critical", "catastrophic")
LIKELIHOOD_LEVELS = ("improbable", "remote", "occasional", "probable", "frequent")

HAZARD_TYPES = (
    "thermal-runaway",
    "internal-short-circuit",
    "external-short-circuit",
    "overcharge",
    "overdischarge",
    "cell-venting",
    "electrolyte-leakage",
    "overpressure-rupture",
)

# Hazards controlled by containment rather than by an extra inhibit.
CONTAINMENT_HAZARDS = frozenset({"electrolyte-leakage", "overpressure-rupture"})
# Hazards that can propagate cell to cell once initiated.
PROPAGATION_HAZARDS = frozenset({"thermal-runaway", "internal-short-circuit"})

# Independent inhibits demanded by severity before any hazard-family tailoring.
BASE_INHIBIT_COUNT = {
    "catastrophic": 3,
    "critical": 2,
    "marginal": 1,
    "negligible": 0,
}

VERIFICATION_METHODS = frozenset(
    {"analysis", "similarity", "inspection", "test", "review-of-design"}
)

RISK_BANDS = (
    (12, "unacceptable"),
    (6, "undesirable"),
    (3, "acceptable-with-review"),
    (0, "acceptable"),
)

_REQUIRED_BATTERY_KEYS = (
    "battery_id",
    "cell_runaway_onset_c",
    "max_predicted_cell_temp_c",
    "required_thermal_margin_k",
    "cell_to_cell_barrier",
    "safety_standard_ref",
)

_REQUIRED_HAZARD_KEYS = (
    "hazard_id",
    "hazard_type",
    "severity",
    "likelihood",
    "inhibits",
    "verification_method",
    "containment_provision",
    "safety_requirement_ref",
)


def _as_float(value, field):
    """Coerce a numeric field, rejecting bools and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("field %r must be a real number, got %r" % (field, value))
    return float(value)


def _as_bool(value, field):
    if not isinstance(value, bool):
        raise ValueError("field %r must be a boolean, got %r" % (field, value))
    return value


def categorize_severity(severity):
    """Return the ordinal position of a severity on the ordered scale."""
    if severity not in SEVERITY_LEVELS:
        raise ValueError(
            "unknown severity %r; expected one of %s"
            % (severity, ", ".join(SEVERITY_LEVELS))
        )
    return SEVERITY_LEVELS.index(severity)


def categorize_likelihood(likelihood):
    """Return the ordinal position of a likelihood on the ordered scale."""
    if likelihood not in LIKELIHOOD_LEVELS:
        raise ValueError(
            "unknown likelihood %r; expected one of %s"
            % (likelihood, ", ".join(LIKELIHOOD_LEVELS))
        )
    return LIKELIHOOD_LEVELS.index(likelihood)


def validate_battery(battery):
    """Return a normalized battery record or raise ValueError."""
    if not isinstance(battery, dict):
        raise ValueError("battery must be a mapping, got %r" % type(battery).__name__)
    missing = [k for k in _REQUIRED_BATTERY_KEYS if k not in battery]
    if missing:
        raise ValueError(
            "battery missing required field(s): %s" % ", ".join(sorted(missing))
        )
    battery_id = battery["battery_id"]
    if not isinstance(battery_id, str) or not battery_id.strip():
        raise ValueError("battery_id must be a non-empty string")
    ref = battery["safety_standard_ref"]
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError(
            "safety_standard_ref must name the product assurance space-safety "
            "standard the battery safety case is managed under"
        )
    out = {"battery_id": battery_id.strip(), "safety_standard_ref": ref.strip()}
    for key in (
        "cell_runaway_onset_c",
        "max_predicted_cell_temp_c",
        "required_thermal_margin_k",
    ):
        out[key] = _as_float(battery[key], key)
    if out["required_thermal_margin_k"] < 0.0:
        raise ValueError("required_thermal_margin_k must be >= 0")
    out["cell_to_cell_barrier"] = _as_bool(
        battery["cell_to_cell_barrier"], "cell_to_cell_barrier"
    )
    return out


def validate_hazard(hazard):
    """Return a normalized hazard record or raise ValueError."""
    if not isinstance(hazard, dict):
        raise ValueError("hazard must be a mapping, got %r" % type(hazard).__name__)
    missing = [k for k in _REQUIRED_HAZARD_KEYS if k not in hazard]
    if missing:
        raise ValueError(
            "hazard missing required field(s): %s" % ", ".join(sorted(missing))
        )
    hazard_id = hazard["hazard_id"]
    if not isinstance(hazard_id, str) or not hazard_id.strip():
        raise ValueError("hazard_id must be a non-empty string")
    hazard_type = hazard["hazard_type"]
    if hazard_type not in HAZARD_TYPES:
        raise ValueError(
            "unknown hazard_type %r; expected one of %s"
            % (hazard_type, ", ".join(HAZARD_TYPES))
        )
    method = hazard["verification_method"]
    if method not in VERIFICATION_METHODS:
        raise ValueError(
            "unknown verification_method %r; expected one of %s"
            % (method, ", ".join(sorted(VERIFICATION_METHODS)))
        )
    categorize_severity(hazard["severity"])
    categorize_likelihood(hazard["likelihood"])
    ref = hazard["safety_requirement_ref"]
    if ref is not None and not isinstance(ref, str):
        raise ValueError("safety_requirement_ref must be a string or None")
    return {
        "hazard_id": hazard_id.strip(),
        "hazard_type": hazard_type,
        "severity": hazard["severity"],
        "likelihood": hazard["likelihood"],
        "inhibits": hazard["inhibits"],
        "verification_method": method,
        "containment_provision": _as_bool(
            hazard["containment_provision"], "containment_provision"
        ),
        "safety_requirement_ref": (ref or "").strip() or None,
    }


def required_controls(severity, hazard_type):
    """Size the control strategy for one hazard.

    Severity sets the baseline number of independent inhibits. A hazard
    family controlled by containment trades one inhibit for a containment
    provision. A propagation-capable hazard at critical severity or above
    additionally demands a cell-to-cell barrier.
    """
    sev_index = categorize_severity(severity)
    if hazard_type not in HAZARD_TYPES:
        raise ValueError("unknown hazard_type %r" % (hazard_type,))
    inhibits = BASE_INHIBIT_COUNT[severity]
    containment = hazard_type in CONTAINMENT_HAZARDS
    if containment:
        inhibits = max(0, inhibits - 1)
    barrier = hazard_type in PROPAGATION_HAZARDS and sev_index >= categorize_severity(
        "critical"
    )
    return {
        "inhibits": inhibits,
        "containment_required": containment,
        "propagation_barrier_required": barrier,
    }


def evaluate_inhibit_chain(inhibits):
    """Count the inhibits that actually carry failure tolerance."""
    if not isinstance(inhibits, (list, tuple)):
        raise ValueError("inhibits must be a list of inhibit records")
    seen = set()
    effective = 0
    findings = []
    for i, item in enumerate(inhibits):
        if not isinstance(item, dict):
            raise ValueError("inhibits[%d] must be a mapping" % i)
        for key in ("inhibit_id", "independent", "verifiable"):
            if key not in item:
                raise ValueError("inhibits[%d] missing %r" % (i, key))
        inhibit_id = item["inhibit_id"]
        if not isinstance(inhibit_id, str) or not inhibit_id.strip():
            raise ValueError("inhibits[%d] inhibit_id must be a non-empty string" % i)
        inhibit_id = inhibit_id.strip()
        if inhibit_id in seen:
            raise ValueError("duplicate inhibit_id %r" % inhibit_id)
        seen.add(inhibit_id)
        independent = _as_bool(item["independent"], "independent")
        verifiable = _as_bool(item["verifiable"], "verifiable")
        if not independent:
            findings.append("inhibit-not-independent:%s" % inhibit_id)
        if not verifiable:
            findings.append("inhibit-not-verifiable:%s" % inhibit_id)
        if independent and verifiable:
            effective += 1
    return {
        "declared": len(inhibits),
        "effective": effective,
        "fault_tolerance": max(0, effective - 1),
        "findings": findings,
    }


def compute_risk_index(severity, likelihood):
    """Return (index, acceptance band) for a severity/likelihood pair."""
    index = (categorize_severity(severity) + 1) * (categorize_likelihood(likelihood) + 1)
    for threshold, band in RISK_BANDS:
        if index >= threshold:
            return index, band
    raise ValueError("risk index %r fell outside every band" % (index,))


def propagation_barrier_margin(battery):
    """Thermal margin to runaway onset, and whether the barrier is adequate."""
    rec = validate_battery(battery)
    margin = rec["cell_runaway_onset_c"] - rec["max_predicted_cell_temp_c"]
    adequate = rec["cell_to_cell_barrier"] and margin >= rec["required_thermal_margin_k"]
    return {"margin_k": margin, "adequate": adequate}


def assess_hazard(hazard, battery):
    """Assess one battery hazard against its sized control strategy."""
    haz = validate_hazard(hazard)
    rec = validate_battery(battery)
    controls = required_controls(haz["severity"], haz["hazard_type"])
    chain = evaluate_inhibit_chain(haz["inhibits"])
    findings = list(chain["findings"])
    if chain["effective"] < controls["inhibits"]:
        findings.append(
            "insufficient-independent-inhibits:%d-of-%d"
            % (chain["effective"], controls["inhibits"])
        )
    if controls["containment_required"] and not haz["containment_provision"]:
        findings.append("containment-provision-missing")
    barrier = None
    if controls["propagation_barrier_required"]:
        barrier = propagation_barrier_margin(rec)
        if not barrier["adequate"]:
            findings.append("propagation-barrier-inadequate")
    if haz["safety_requirement_ref"] is None:
        findings.append("product-assurance-safety-link-missing")
    index, band = compute_risk_index(haz["severity"], haz["likelihood"])
    if band == "unacceptable":
        findings.append("residual-risk-unacceptable")
    return {
        "hazard_id": haz["hazard_id"],
        "hazard_type": haz["hazard_type"],
        "severity": haz["severity"],
        "required_inhibits": controls["inhibits"],
        "effective_inhibits": chain["effective"],
        "fault_tolerance": chain["fault_tolerance"],
        "containment_required": controls["containment_required"],
        "propagation_barrier_required": controls["propagation_barrier_required"],
        "propagation_margin": barrier,
        "risk_index": index,
        "risk_band": band,
        "findings": tuple(findings),
        "controlled": not findings,
    }


def assess_battery_safety(battery, hazards):
    """Aggregate the clause 5.6.5.2 safety case for one battery."""
    rec = validate_battery(battery)
    if not isinstance(hazards, (list, tuple)) or not hazards:
        raise ValueError("hazards must be a non-empty list of hazard records")
    results = []
    seen = set()
    worst = 0
    worst_band = "acceptable"
    for hazard in hazards:
        result = assess_hazard(hazard, rec)
        if result["hazard_id"] in seen:
            raise ValueError("duplicate hazard_id %r" % result["hazard_id"])
        seen.add(result["hazard_id"])
        if result["risk_index"] > worst:
            worst = result["risk_index"]
            worst_band = result["risk_band"]
        results.append(result)
    open_findings = tuple(
        "%s/%s" % (r["hazard_id"], f) for r in results for f in r["findings"]
    )
    return {
        "battery_id": rec["battery_id"],
        "safety_standard_ref": rec["safety_standard_ref"],
        "hazard_count": len(results),
        "hazards": tuple(results),
        "worst_risk_index": worst,
        "worst_risk_band": worst_band,
        "open_findings": open_findings,
        "safety_case_closed": not open_findings,
    }


if __name__ == "__main__":  # pragma: no cover - manual smoke run
    demo_battery = {
        "battery_id": "BAT-A",
        "cell_runaway_onset_c": 130.0,
        "max_predicted_cell_temp_c": 45.0,
        "required_thermal_margin_k": 40.0,
        "cell_to_cell_barrier": True,
        "safety_standard_ref": "product-assurance-space-safety",
    }
    demo_hazard = {
        "hazard_id": "HZ-01",
        "hazard_type": "overcharge",
        "severity": "catastrophic",
        "likelihood": "improbable",
        "inhibits": [
            {"inhibit_id": "I1", "independent": True, "verifiable": True},
            {"inhibit_id": "I2", "independent": True, "verifiable": True},
            {"inhibit_id": "I3", "independent": True, "verifiable": True},
        ],
        "verification_method": "test",
        "containment_provision": False,
        "safety_requirement_ref": "SAF-014",
    }
    out = assess_battery_safety(demo_battery, [demo_hazard])
    for key in sorted(out):
        if key != "hazards":
            print("%-24s %s" % (key, out[key]))
