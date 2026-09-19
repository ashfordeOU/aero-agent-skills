"""Release and locking device design assessment for spacecraft mechanisms.

Anchor: ECSS-E-ST-33-01C clauses 4.7.5.4.12 and 4.7.6 (release devices,
including pyrotechnic ones, and the locking devices that hold a mechanism
until release). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate each release device: actuation means, initiator count, the number
   of electrically independent firing paths, and the declared release
   confirmation.
2. Grade the redundancy arrangement. A release function that an appendage
   depends on may not rest on one initiator or one firing path, whatever the
   actuation means is.
3. Grade shock compatibility: convert the separation event into an induced
   level at each neighbouring unit and compare it with that unit's qualified
   level, expressed as a margin in dB.
4. Grade the locking device: the preload it holds has to cover the worst-case
   launch load with margin, and the lock has to be positive rather than a
   friction grip that a vibration environment can walk loose.
5. Allocate the particulate and gaseous release of the devices against the
   contamination budget of the sensitive surfaces they sit near.
"""

import math

__all__ = [
    "ACTUATION_MEANS",
    "PYROTECHNIC_MEANS",
    "MARGIN_TOLERANCE_DB",
    "PRELOAD_TOLERANCE",
    "CONTAMINATION_TOLERANCE",
    "MIN_INITIATORS",
    "MIN_FIRING_PATHS",
    "validate_device",
    "redundancy_findings",
    "shock_margin_db",
    "induced_shock_g",
    "shock_findings",
    "preload_margin",
    "locking_findings",
    "contamination_total",
    "contamination_findings",
    "assess_release_locking_design",
]

# Actuation means recognised for a release device. A means outside this set is
# an input error: its failure modes are not the ones graded below.
ACTUATION_MEANS = (
    "pyrotechnic",
    "thermal-knife",
    "shape-memory-alloy",
    "paraffin-thermal",
    "split-spool",
    "motorised-nut",
)

# Means whose release is a one-shot energetic event and therefore carries the
# separation-shock and contamination questions by construction.
PYROTECHNIC_MEANS = ("pyrotechnic",)

# A margin comparison in dB is a difference of logarithms; an exact physical
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here rather than relaxing the engineering limit.
MARGIN_TOLERANCE_DB = 1e-9
PRELOAD_TOLERANCE = 1e-9
CONTAMINATION_TOLERANCE = 1e-12

# A release that an appendage depends on is redundant in both the energetic
# element and the circuit that reaches it.
MIN_INITIATORS = 2
MIN_FIRING_PATHS = 2


def _positive(label, value):
    """Return value as a positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def _count(label, value):
    """Return value as a non-negative integer count or raise ValueError."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count" % label)
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def validate_device(device):
    """Return a normalised release-device record.

    Required keys: id, actuation, initiators, firing_paths, preload_n,
    worst_case_load_n. Optional keys: positive_lock (bool), release_confirmed
    (bool), particulate_mg, outgassed_mg, source_level_g, mission_critical.
    """
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping")
    for key in ("id", "actuation", "initiators", "firing_paths",
                "preload_n", "worst_case_load_n"):
        if key not in device:
            raise ValueError("device missing required key '%s'" % key)
    identifier = device["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("device id must be a non-empty string")
    actuation = device["actuation"]
    if not isinstance(actuation, str):
        raise ValueError("actuation must be a string")
    actuation = actuation.strip().lower()
    if actuation not in ACTUATION_MEANS:
        raise ValueError(
            "actuation %r is not one of %s" % (device["actuation"], ", ".join(ACTUATION_MEANS))
        )
    record = {
        "id": identifier.strip(),
        "actuation": actuation,
        "initiators": _count("initiators", device["initiators"]),
        "firing_paths": _count("firing_paths", device["firing_paths"]),
        "preload_n": _positive("preload_n", device["preload_n"]),
        "worst_case_load_n": _positive("worst_case_load_n", device["worst_case_load_n"]),
        "positive_lock": bool(device.get("positive_lock", False)),
        "release_confirmed": bool(device.get("release_confirmed", False)),
        "mission_critical": bool(device.get("mission_critical", True)),
        "particulate_mg": _non_negative("particulate_mg", device.get("particulate_mg", 0.0)),
        "outgassed_mg": _non_negative("outgassed_mg", device.get("outgassed_mg", 0.0)),
        "source_level_g": _positive("source_level_g", device.get("source_level_g", 1.0)),
    }
    if record["initiators"] < 1:
        raise ValueError("a release device needs at least one initiator")
    if record["firing_paths"] < 1:
        raise ValueError("a release device needs at least one firing path")
    return record


def redundancy_findings(device):
    """Return the single-point-failure findings for one validated device."""
    record = validate_device(device)
    findings = []
    if not record["mission_critical"]:
        return findings
    if record["initiators"] < MIN_INITIATORS:
        findings.append(
            "%s: %d initiator(s); a mission-critical release needs at least %d "
            "independently capable of releasing on their own"
            % (record["id"], record["initiators"], MIN_INITIATORS)
        )
    if record["firing_paths"] < MIN_FIRING_PATHS:
        findings.append(
            "%s: %d firing path(s); the initiators share a circuit, so the circuit "
            "is a single-point failure" % (record["id"], record["firing_paths"])
        )
    if not record["release_confirmed"]:
        findings.append(
            "%s: no declared release confirmation; a failed release cannot be "
            "distinguished from a late one" % record["id"]
        )
    return findings


def induced_shock_g(source_level_g, distance_m, joints=0, decay_per_m=0.5,
                    joint_attenuation=0.7):
    """Return the shock level in g reaching a unit from a release event."""
    source = _positive("source_level_g", source_level_g)
    distance = _non_negative("distance_m", distance_m)
    count = _count("joints", joints)
    decay = _positive("decay_per_m", decay_per_m)
    attenuation = _positive("joint_attenuation", joint_attenuation)
    if attenuation > 1.0:
        raise ValueError("joint_attenuation must not exceed unity, got %r" % (joint_attenuation,))
    level = source * math.exp(-decay * distance)
    for _ in range(count):
        level *= attenuation
    return level


def shock_margin_db(qualified_g, induced_g):
    """Return the shock margin in dB of a qualified level over an induced one."""
    qualified = _positive("qualified_g", qualified_g)
    induced = _positive("induced_g", induced_g)
    return 20.0 * math.log10(qualified / induced)


def shock_findings(device, neighbours, required_margin_db):
    """Return the shock-compatibility findings for the units near a device."""
    record = validate_device(device)
    required = _non_negative("required_margin_db", required_margin_db)
    if not isinstance(neighbours, (list, tuple)):
        raise ValueError("neighbours must be a sequence of unit mappings")
    findings = []
    records = []
    for index, unit in enumerate(neighbours):
        if not isinstance(unit, dict):
            raise ValueError("neighbours[%d] must be a mapping" % index)
        for key in ("id", "distance_m", "qualified_g"):
            if key not in unit:
                raise ValueError("neighbours[%d] missing key '%s'" % (index, key))
        induced = induced_shock_g(
            record["source_level_g"],
            unit["distance_m"],
            unit.get("joints", 0),
            unit.get("decay_per_m", 0.5),
            unit.get("joint_attenuation", 0.7),
        )
        margin = shock_margin_db(unit["qualified_g"], induced)
        compliant = margin > required or math.isclose(
            margin, required, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_DB
        )
        records.append({
            "unit": unit["id"],
            "induced_g": induced,
            "qualified_g": float(unit["qualified_g"]),
            "margin_db": margin,
            "compliant": compliant,
        })
        if not compliant:
            findings.append(
                "%s -> %s: separation shock leaves %.3f dB against the required %.3f dB"
                % (record["id"], unit["id"], margin, required)
            )
    return {"records": records, "findings": findings}


def preload_margin(preload_n, worst_case_load_n):
    """Return the fractional margin of a locking preload over the load it holds."""
    preload = _positive("preload_n", preload_n)
    load = _positive("worst_case_load_n", worst_case_load_n)
    return preload / load - 1.0


def locking_findings(device, required_preload_margin):
    """Return the locking-device findings for one validated device."""
    record = validate_device(device)
    required = _non_negative("required_preload_margin", required_preload_margin)
    margin = preload_margin(record["preload_n"], record["worst_case_load_n"])
    findings = []
    compliant = margin > required or math.isclose(
        margin, required, rel_tol=0.0, abs_tol=PRELOAD_TOLERANCE
    )
    if not compliant:
        findings.append(
            "%s: locking preload margin %.4f is below the required %.4f"
            % (record["id"], margin, required)
        )
    if not record["positive_lock"]:
        findings.append(
            "%s: lock is not declared positive; a friction-only grip can walk loose "
            "under the launch vibration environment" % record["id"]
        )
    return {"margin": margin, "compliant": compliant and record["positive_lock"],
            "findings": findings}


def contamination_total(devices):
    """Return the summed particulate and outgassed release of the devices."""
    if not isinstance(devices, (list, tuple)) or not devices:
        raise ValueError("devices must be a non-empty sequence")
    particulate = 0.0
    outgassed = 0.0
    for device in devices:
        record = validate_device(device)
        particulate += record["particulate_mg"]
        outgassed += record["outgassed_mg"]
    return {"particulate_mg": particulate, "outgassed_mg": outgassed,
            "total_mg": particulate + outgassed}


def contamination_findings(devices, budget_mg):
    """Return the contamination findings of a device set against its budget."""
    totals = contamination_total(devices)
    budget = _positive("budget_mg", budget_mg)
    findings = []
    within = totals["total_mg"] < budget or math.isclose(
        totals["total_mg"], budget, rel_tol=0.0, abs_tol=CONTAMINATION_TOLERANCE
    )
    if not within:
        findings.append(
            "release devices put %.4f mg against a %.4f mg sensitive-surface budget"
            % (totals["total_mg"], budget)
        )
    return {"totals": totals, "within_budget": within, "findings": findings}


def assess_release_locking_design(spec):
    """Run the full clause 4.7.5.4.12 / 4.7.6 release and locking assessment.

    spec keys: devices (non-empty sequence), neighbours (sequence, may be
    empty), required_shock_margin_db, required_preload_margin,
    contamination_budget_mg.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("devices", "required_shock_margin_db", "required_preload_margin",
                "contamination_budget_mg"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    devices = spec["devices"]
    if not isinstance(devices, (list, tuple)) or not devices:
        raise ValueError("spec['devices'] must be a non-empty sequence")
    neighbours = spec.get("neighbours", [])
    findings = []
    per_device = []
    for device in devices:
        record = validate_device(device)
        redundancy = redundancy_findings(device)
        shock = shock_findings(device, neighbours, spec["required_shock_margin_db"])
        locking = locking_findings(device, spec["required_preload_margin"])
        device_findings = list(redundancy) + list(shock["findings"]) + list(locking["findings"])
        per_device.append({
            "id": record["id"],
            "actuation": record["actuation"],
            "energetic": record["actuation"] in PYROTECHNIC_MEANS,
            "redundancy_findings": redundancy,
            "shock_records": shock["records"],
            "preload_margin": locking["margin"],
            "findings": device_findings,
            "compliant": not device_findings,
        })
        findings.extend(device_findings)
    contamination = contamination_findings(devices, spec["contamination_budget_mg"])
    findings.extend(contamination["findings"])
    return {
        "devices": per_device,
        "contamination": contamination["totals"],
        "within_contamination_budget": contamination["within_budget"],
        "findings": findings,
        "compliant": not findings,
    }
