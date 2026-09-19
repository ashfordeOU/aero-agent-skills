"""Applicability screening of sterilization processes against a bill of materials.

Anchor: the framework clause of ECSS-Q-ST-70-53, which fixes the scope of a
materials and hardware sterilization compatibility campaign. Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate a register of candidate processes, each carrying the stressor
   levels it applies (temperature, cumulative dose, agent concentration,
   humidity, dwell) and the chemical agents it exposes hardware to.
2. Validate a bill of materials, each carrying declared capability per axis
   and the agents it is known to be attacked by.
3. Compare every material and process pairing axis by axis.
4. Categorize the pairing as excluded, test-required or admissible by
   analysis, keeping the driving axis and its margin.
5. Aggregate to the item: the admissible process set, the test matrix, and a
   finding when nothing survives.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "DEFAULT_ANALYSIS_MARGIN",
    "STATUS_ADMISSIBLE",
    "STATUS_TEST_REQUIRED",
    "STATUS_EXCLUDED",
    "validate_process",
    "validate_material",
    "axis_margin",
    "screen_pairing",
    "admissible_processes",
    "test_matrix",
    "assess_applicability",
]

# A margin comparison against a threshold can land a few ULP either side when
# both came out of a division. Absorb the representation error here.
MARGIN_TOLERANCE = 1e-9

# Unused fraction of capability below which a pairing is not settled by
# analysis and owes the campaign a test.
DEFAULT_ANALYSIS_MARGIN = 0.20

STATUS_ADMISSIBLE = "admissible-by-analysis"
STATUS_TEST_REQUIRED = "test-required"
STATUS_EXCLUDED = "excluded"


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _agent_set(value, label):
    if value is None:
        return frozenset()
    if isinstance(value, str) or not hasattr(value, "__iter__"):
        raise ValueError("%s must be a sequence of agent names" % label)
    agents = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("%s entries must be non-empty strings" % label)
        agents.append(item.strip().lower())
    return frozenset(agents)


def validate_process(process):
    """Return a validated process record.

    Keys: name, stressors (axis -> applied level), optional agents.
    """
    if not isinstance(process, dict):
        raise ValueError("process must be a mapping")
    name = process.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("process name must be a non-empty string")
    stressors = process.get("stressors")
    if not isinstance(stressors, dict) or not stressors:
        raise ValueError("process %s must declare a non-empty stressor mapping" % name)
    cleaned = {}
    for axis, level in stressors.items():
        if not isinstance(axis, str) or not axis.strip():
            raise ValueError("process %s has a non-string stressor axis" % name)
        cleaned[axis.strip().lower()] = _non_negative(
            level, "process %s axis %s" % (name, axis)
        )
    return {
        "name": name.strip(),
        "stressors": cleaned,
        "agents": _agent_set(process.get("agents"), "process %s agents" % name),
    }


def validate_material(material):
    """Return a validated material record.

    Keys: name, capabilities (axis -> declared capability), optional
    sensitive_to (agent names the material is attacked by).
    """
    if not isinstance(material, dict):
        raise ValueError("material must be a mapping")
    name = material.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("material name must be a non-empty string")
    capabilities = material.get("capabilities")
    if capabilities is None:
        capabilities = {}
    if not isinstance(capabilities, dict):
        raise ValueError("material %s capabilities must be a mapping" % name)
    cleaned = {}
    for axis, value in capabilities.items():
        if not isinstance(axis, str) or not axis.strip():
            raise ValueError("material %s has a non-string capability axis" % name)
        cleaned[axis.strip().lower()] = _positive(
            value, "material %s capability %s" % (name, axis)
        )
    return {
        "name": name.strip(),
        "capabilities": cleaned,
        "sensitive_to": _agent_set(
            material.get("sensitive_to"), "material %s sensitive_to" % name
        ),
    }


def axis_margin(capability, applied):
    """Return the unused fraction of capability on one axis.

    Positive is headroom, zero is exactly at capability, negative is a breach.
    """
    cap = _positive(capability, "capability")
    level = _non_negative(applied, "applied")
    return (cap - level) / cap


def screen_pairing(material, process, analysis_margin=DEFAULT_ANALYSIS_MARGIN):
    """Categorize one material and process pairing."""
    mat = validate_material(material)
    proc = validate_process(process)
    threshold = _non_negative(analysis_margin, "analysis_margin")
    attacked = sorted(mat["sensitive_to"] & proc["agents"])
    axes = {}
    undeclared = []
    breached = []
    least_margin = None
    driving_axis = None
    for axis in sorted(proc["stressors"]):
        applied = proc["stressors"][axis]
        if axis not in mat["capabilities"]:
            undeclared.append(axis)
            axes[axis] = {"applied": applied, "capability": None, "margin": None}
            continue
        capability = mat["capabilities"][axis]
        margin = axis_margin(capability, applied)
        axes[axis] = {"applied": applied, "capability": capability, "margin": margin}
        if margin < -MARGIN_TOLERANCE:
            breached.append(axis)
        if least_margin is None or margin < least_margin:
            least_margin = margin
            driving_axis = axis
    if attacked:
        status = STATUS_EXCLUDED
        reason = "attacked by %s" % ", ".join(attacked)
    elif breached:
        status = STATUS_EXCLUDED
        reason = "applied level above capability on %s" % ", ".join(breached)
    elif undeclared:
        status = STATUS_TEST_REQUIRED
        reason = "no declared capability on %s" % ", ".join(undeclared)
    elif least_margin is not None and least_margin < threshold - MARGIN_TOLERANCE:
        status = STATUS_TEST_REQUIRED
        reason = "least margin %.4f on %s is below the analysis threshold %.4f" % (
            least_margin,
            driving_axis,
            threshold,
        )
    else:
        status = STATUS_ADMISSIBLE
        reason = "every axis carries margin at or above the analysis threshold"
    return {
        "material": mat["name"],
        "process": proc["name"],
        "axes": axes,
        "undeclared_axes": undeclared,
        "breached_axes": breached,
        "attacked_by": attacked,
        "least_margin": least_margin,
        "driving_axis": driving_axis,
        "status": status,
        "reason": reason,
    }


def admissible_processes(pairings):
    """Return the process names no material excludes."""
    if not isinstance(pairings, (list, tuple)):
        raise ValueError("pairings must be a sequence of pairing records")
    seen = []
    excluded = set()
    for record in pairings:
        if not isinstance(record, dict) or "process" not in record or "status" not in record:
            raise ValueError("each pairing must carry 'process' and 'status'")
        if record["process"] not in seen:
            seen.append(record["process"])
        if record["status"] == STATUS_EXCLUDED:
            excluded.add(record["process"])
    return [name for name in seen if name not in excluded]


def test_matrix(pairings):
    """Return the (material, process) pairs that owe the campaign a test."""
    return [
        (record["material"], record["process"])
        for record in pairings
        if record["status"] == STATUS_TEST_REQUIRED
    ]


def assess_applicability(spec):
    """Scope a sterilization compatibility campaign for one item.

    spec keys: item, materials, processes; optional analysis_margin.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("item", "materials", "processes"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    materials = spec["materials"]
    processes = spec["processes"]
    if not isinstance(materials, (list, tuple)) or not materials:
        raise ValueError("materials must be a non-empty sequence")
    if not isinstance(processes, (list, tuple)) or not processes:
        raise ValueError("processes must be a non-empty sequence")
    threshold = spec.get("analysis_margin", DEFAULT_ANALYSIS_MARGIN)
    pairings = []
    for process in processes:
        for material in materials:
            pairings.append(screen_pairing(material, process, threshold))
    admissible = admissible_processes(pairings)
    matrix = [pair for pair in test_matrix(pairings) if pair[1] in admissible]
    findings = []
    if not admissible:
        findings.append(
            "no candidate process survives the bill of materials for item %s"
            % spec["item"]
        )
    for record in pairings:
        if record["status"] == STATUS_EXCLUDED:
            findings.append(
                "%s excludes process %s: %s"
                % (record["material"], record["process"], record["reason"])
            )
    return {
        "item": spec["item"],
        "analysis_margin": float(threshold),
        "pairings": pairings,
        "admissible_processes": admissible,
        "test_matrix": matrix,
        "scoped": bool(admissible),
        "findings": findings,
    }
