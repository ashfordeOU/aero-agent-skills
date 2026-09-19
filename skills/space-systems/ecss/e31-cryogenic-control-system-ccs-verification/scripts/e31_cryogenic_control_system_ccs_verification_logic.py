"""Cryogenic control system (CCS) verification at instrument and subsystem level.

Anchor: ECSS-E-ST-31C clause 4.5.2.2 (verification of the cryogenic control
system against the agreed verification objectives and the agreed test setups).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the agreed verification objectives: each one names the level it is
   agreed at, the method agreed to close it, and the quantity it grades.
2. Grade the agreed test setup actually achieved during the run -- sink
   temperature, chamber pressure and the presence of the agreed boundary
   simulator -- because a result taken outside the agreed setup grades the
   setup, not the cryogenic chain.
3. Compute the four engineering quantities the clause turns on: heat-lift
   margin at the operating temperature, peak-to-peak temperature stability
   across the observation window, cooldown slack against the agreed duration,
   and the parasitic heat-load roll-up against its allocation.
4. Check the level at which every objective was closed. A level agreed as
   instrument level is not closed by a subsystem run, and an objective agreed
   to be closed by test is not closed by analysis alone.
5. Roll the campaign up: per-objective records, setup findings, uncovered
   objectives and the overall verification status.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "STABILITY_TOLERANCE_K",
    "LEVELS",
    "METHODS",
    "level_rank",
    "validate_temperature_k",
    "validate_level",
    "validate_method",
    "heat_lift_margin",
    "temperature_stability_pp_k",
    "stability_compliant",
    "cooldown_slack_h",
    "parasitic_load_rollup",
    "grade_setup",
    "evaluate_objective",
    "objective_coverage",
    "assess_ccs_verification",
]

# Margins and stability limits come out of divisions and subtractions of
# measured floats. A quantity that should sit exactly on its limit can land a
# few ULPs either side, so absorb the representation error here rather than
# loosening the engineering limit.
MARGIN_TOLERANCE = 1e-9
STABILITY_TOLERANCE_K = 1e-9

# Verification levels, most detailed first. A more detailed level may close a
# coarser objective; the reverse hides the interface the objective was written
# to exercise.
LEVELS = ("instrument", "subsystem")

# Closure methods, in decreasing evidential strength.
METHODS = ("test", "analysis", "review-of-design")

_METHOD_RANK = {name: index for index, name in enumerate(METHODS)}


def level_rank(level):
    """Return the detail rank of a verification level (0 is the most detailed)."""
    return LEVELS.index(validate_level(level))


def validate_temperature_k(value, label):
    """Return a validated absolute temperature in kelvin."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    temperature = float(value)
    if not math.isfinite(temperature):
        raise ValueError("%s must be finite" % label)
    if temperature <= 0.0:
        raise ValueError("%s must be above absolute zero, got %r" % (label, value))
    return temperature


def _validate_positive(value, label, allow_zero=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_level(level):
    """Return a validated verification level name."""
    if not isinstance(level, str):
        raise ValueError("verification level must be a string")
    name = level.strip().lower()
    if name not in LEVELS:
        raise ValueError("unknown verification level %r; expected one of %s" % (level, LEVELS))
    return name


def validate_method(method):
    """Return a validated closure method name."""
    if not isinstance(method, str):
        raise ValueError("closure method must be a string")
    name = method.strip().lower()
    if name not in METHODS:
        raise ValueError("unknown closure method %r; expected one of %s" % (method, METHODS))
    return name


def heat_lift_margin(lift_available_w, lift_required_w):
    """Return the fractional heat-lift margin of a cooler at its operating point."""
    available = _validate_positive(lift_available_w, "lift_available_w", allow_zero=True)
    required = _validate_positive(lift_required_w, "lift_required_w")
    return (available - required) / required


def temperature_stability_pp_k(samples_k):
    """Return the peak-to-peak temperature excursion of an observation window."""
    if not isinstance(samples_k, (list, tuple)) or len(samples_k) < 2:
        raise ValueError("samples_k needs at least two readings to form an excursion")
    values = [validate_temperature_k(s, "sample") for s in samples_k]
    return max(values) - min(values)


def stability_compliant(peak_to_peak_k, allowed_k):
    """Return True when a peak-to-peak excursion sits within its allowance."""
    measured = _validate_positive(peak_to_peak_k, "peak_to_peak_k", allow_zero=True)
    allowed = _validate_positive(allowed_k, "allowed_k", allow_zero=True)
    if measured < allowed:
        return True
    return math.isclose(measured, allowed, rel_tol=0.0, abs_tol=STABILITY_TOLERANCE_K)


def cooldown_slack_h(measured_h, agreed_h):
    """Return the cooldown slack in hours (positive means the run beat the agreed time)."""
    measured = _validate_positive(measured_h, "measured_h", allow_zero=True)
    agreed = _validate_positive(agreed_h, "agreed_h")
    return agreed - measured


def parasitic_load_rollup(loads_w, allocation_w):
    """Sum the declared parasitic heat loads and grade them against their allocation."""
    if not isinstance(loads_w, dict) or not loads_w:
        raise ValueError("loads_w must be a non-empty mapping of path name to watts")
    allocation = _validate_positive(allocation_w, "allocation_w")
    total = 0.0
    contributions = {}
    for name, watts in loads_w.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("every parasitic path needs a non-empty name")
        value = _validate_positive(watts, "parasitic load %r" % name, allow_zero=True)
        contributions[name.strip()] = value
        total += value
    if len(contributions) != len(loads_w):
        raise ValueError("duplicate parasitic path name after trimming")
    within = total < allocation or math.isclose(
        total, allocation, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    dominant = max(contributions.items(), key=lambda item: (item[1], item[0]))[0]
    return {
        "contributions": contributions,
        "total_w": total,
        "allocation_w": allocation,
        "within_allocation": within,
        "dominant_path": dominant,
    }


def grade_setup(achieved, agreed):
    """Grade the achieved test setup against the agreed cryogenic setup."""
    for label, mapping in (("achieved", achieved), ("agreed", agreed)):
        if not isinstance(mapping, dict):
            raise ValueError("%s setup must be a mapping" % label)
    for key in ("sink_temperature_k", "chamber_pressure_pa"):
        if key not in achieved or key not in agreed:
            raise ValueError("both setups must carry '%s'" % key)
    sink_achieved = validate_temperature_k(achieved["sink_temperature_k"], "achieved sink")
    sink_agreed = validate_temperature_k(agreed["sink_temperature_k"], "agreed sink")
    pressure_achieved = _validate_positive(achieved["chamber_pressure_pa"], "achieved pressure")
    pressure_agreed = _validate_positive(agreed["chamber_pressure_pa"], "agreed pressure")
    findings = []
    sink_ok = sink_achieved < sink_agreed or math.isclose(
        sink_achieved, sink_agreed, rel_tol=0.0, abs_tol=STABILITY_TOLERANCE_K
    )
    if not sink_ok:
        findings.append(
            "sink temperature reached %.3f K against an agreed %.3f K"
            % (sink_achieved, sink_agreed)
        )
    pressure_ok = pressure_achieved < pressure_agreed or math.isclose(
        pressure_achieved, pressure_agreed, rel_tol=1e-12, abs_tol=0.0
    )
    if not pressure_ok:
        findings.append(
            "chamber pressure held %.3e Pa against an agreed %.3e Pa"
            % (pressure_achieved, pressure_agreed)
        )
    simulator_required = bool(agreed.get("boundary_simulator", False))
    simulator_present = bool(achieved.get("boundary_simulator", False))
    if simulator_required and not simulator_present:
        findings.append("agreed boundary simulator was not installed for the run")
    return {
        "sink_temperature_k": sink_achieved,
        "chamber_pressure_pa": pressure_achieved,
        "boundary_simulator": simulator_present,
        "setup_conforms": not findings,
        "findings": findings,
    }


def evaluate_objective(objective):
    """Evaluate one agreed CCS verification objective and return its record."""
    if not isinstance(objective, dict):
        raise ValueError("objective must be a mapping")
    for key in ("id", "quantity", "agreed_level", "agreed_method",
                "closed_level", "closed_method"):
        if key not in objective:
            raise ValueError("objective missing required key '%s'" % key)
    identifier = objective["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("objective id must be a non-empty string")
    quantity = objective["quantity"]
    if not isinstance(quantity, str) or not quantity.strip():
        raise ValueError("objective quantity must be a non-empty string")
    agreed_level = validate_level(objective["agreed_level"])
    closed_level = validate_level(objective["closed_level"])
    agreed_method = validate_method(objective["agreed_method"])
    closed_method = validate_method(objective["closed_method"])
    findings = []
    if level_rank(closed_level) > level_rank(agreed_level):
        findings.append(
            "%s was agreed at %s level and closed at %s level"
            % (identifier.strip(), agreed_level, closed_level)
        )
    if _METHOD_RANK[closed_method] > _METHOD_RANK[agreed_method]:
        findings.append(
            "%s was agreed to close by %s and closed by %s"
            % (identifier.strip(), agreed_method, closed_method)
        )
    return {
        "id": identifier.strip(),
        "quantity": quantity.strip(),
        "agreed_level": agreed_level,
        "closed_level": closed_level,
        "agreed_method": agreed_method,
        "closed_method": closed_method,
        "conforms": not findings,
        "findings": findings,
    }


def objective_coverage(objectives, required_quantities):
    """Return the agreed quantities that no conforming objective closes."""
    if not isinstance(objectives, (list, tuple)):
        raise ValueError("objectives must be a sequence")
    if not isinstance(required_quantities, (list, tuple)) or not required_quantities:
        raise ValueError("required_quantities must be a non-empty sequence")
    covered = set()
    for record in objectives:
        if not isinstance(record, dict) or "quantity" not in record:
            raise ValueError("each objective record must carry 'quantity'")
        if record.get("conforms"):
            covered.add(record["quantity"])
    missing = []
    for quantity in required_quantities:
        if not isinstance(quantity, str) or not quantity.strip():
            raise ValueError("required quantity names must be non-empty strings")
        if quantity.strip() not in covered:
            missing.append(quantity.strip())
    return missing


def assess_ccs_verification(spec):
    """Run the full clause 4.5.2.2 CCS verification assessment.

    spec keys: objectives, required_quantities, agreed_setup, achieved_setup,
    lift_available_w, lift_required_w, stability_samples_k, stability_allowed_k,
    cooldown_measured_h, cooldown_agreed_h, parasitic_loads_w,
    parasitic_allocation_w.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "objectives", "required_quantities", "agreed_setup", "achieved_setup",
        "lift_available_w", "lift_required_w", "stability_samples_k",
        "stability_allowed_k", "cooldown_measured_h", "cooldown_agreed_h",
        "parasitic_loads_w", "parasitic_allocation_w",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    raw_objectives = spec["objectives"]
    if not isinstance(raw_objectives, (list, tuple)) or not raw_objectives:
        raise ValueError("spec['objectives'] must be a non-empty sequence")
    records = [evaluate_objective(item) for item in raw_objectives]
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError("duplicate objective id %r" % record["id"])
        seen.add(record["id"])
    setup = grade_setup(spec["achieved_setup"], spec["agreed_setup"])
    margin = heat_lift_margin(spec["lift_available_w"], spec["lift_required_w"])
    peak_to_peak = temperature_stability_pp_k(spec["stability_samples_k"])
    stable = stability_compliant(peak_to_peak, spec["stability_allowed_k"])
    slack = cooldown_slack_h(spec["cooldown_measured_h"], spec["cooldown_agreed_h"])
    parasitics = parasitic_load_rollup(spec["parasitic_loads_w"], spec["parasitic_allocation_w"])
    missing = objective_coverage(records, spec["required_quantities"])
    findings = list(setup["findings"])
    for record in records:
        findings.extend(record["findings"])
    lift_ok = margin > 0.0 or math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE)
    if not lift_ok:
        findings.append("heat lift falls short of the required duty by %.4f of it" % -margin)
    if not stable:
        findings.append(
            "temperature stability window spans %.4f K against an allowance of %.4f K"
            % (peak_to_peak, float(spec["stability_allowed_k"]))
        )
    if slack < 0.0 and not math.isclose(slack, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE):
        findings.append("cooldown overran the agreed duration by %.3f h" % -slack)
    if not parasitics["within_allocation"]:
        findings.append(
            "parasitic heat load totals %.4f W against an allocation of %.4f W, %s dominating"
            % (parasitics["total_w"], parasitics["allocation_w"], parasitics["dominant_path"])
        )
    for quantity in missing:
        findings.append("no conforming objective closes the agreed quantity %r" % quantity)
    return {
        "objectives": records,
        "setup": setup,
        "heat_lift_margin": margin,
        "heat_lift_compliant": lift_ok,
        "stability_pp_k": peak_to_peak,
        "stability_compliant": stable,
        "cooldown_slack_h": slack,
        "parasitics": parasitics,
        "uncovered_quantities": missing,
        "verified": not findings,
        "findings": findings,
    }
