"""Generic-hazard library and hazard-register seeding.

Anchor: ECSS-Q-ST-40-02C informative annexes A and B (paraphrased into an
implementable library and register grader; no standard text is
reproduced).

Procedure implemented here:

1. Hold a library of generic hazard groups, each keyed to the system
   characteristics that call it. The library is the starting point an
   identification session works from, so that step 2 begins with
   candidates rather than an empty page.
2. Seed a candidate hazard list from the characteristics a system
   declares. A candidate is raised when any keying characteristic is
   present, and its call strength is the fraction of that group's
   keying characteristics the system actually has -- a group called by
   three of its three characteristics deserves attention before one
   called by one of three.
3. Report the library groups nothing in the system called, so a
   reviewer can see what the seeding deliberately left out instead of
   inferring it from an absence.
4. Grade each register record against the example field set of the
   annex B register: a record missing its cause, its effect, its
   control or its verification reference is incomplete regardless of
   how much prose it carries.
5. Report which seeded candidates never became register records, which
   is the gap between a seeding session and a register.

Stdlib only, offline, deterministic.
"""

# Generic hazard groups and the system characteristics that call each.
# Paraphrased groupings, not a reproduction of any annex table.
GENERIC_HAZARD_LIBRARY = {
    "stored-pressure-energy-release": (
        "pressurized-vessel",
        "pressurized-feed-line",
        "high-pressure-gas-storage",
    ),
    "propellant-leakage-and-toxicity": (
        "liquid-propellant",
        "hypergolic-propellant",
        "propellant-loading-operation",
    ),
    "pyrotechnic-initiation": (
        "pyrotechnic-device",
        "separation-mechanism",
        "ordnance-firing-circuit",
    ),
    "electrical-shock-and-arcing": (
        "high-voltage-subsystem",
        "exposed-conductor",
        "high-energy-battery",
    ),
    "battery-thermal-runaway": (
        "high-energy-battery",
        "lithium-cell-chemistry",
    ),
    "ionizing-radiation-exposure": (
        "radioactive-source",
        "radioisotope-heater",
        "x-ray-inspection-equipment",
    ),
    "non-ionizing-radiation-exposure": (
        "high-power-radiofrequency-transmitter",
        "laser-payload",
    ),
    "cryogenic-contact-and-embrittlement": (
        "cryogenic-fluid",
        "cryogenic-feed-line",
    ),
    "kinetic-energy-and-moving-mass": (
        "deployable-appendage",
        "rotating-machinery",
        "lifting-operation",
    ),
    "structural-collapse-and-fragment-release": (
        "primary-load-path-structure",
        "rotating-machinery",
        "high-pressure-gas-storage",
    ),
    "thermal-burn-and-fire": (
        "hot-surface",
        "flammable-material",
        "high-energy-battery",
    ),
    "contamination-and-material-outgassing": (
        "cleanroom-sensitive-payload",
        "outgassing-material",
    ),
    "crew-injury-and-habitability-loss": (
        "crew-compartment",
        "life-support-system",
        "crew-egress-path",
    ),
    "electromagnetic-interference-with-safety-function": (
        "safety-critical-command-path",
        "high-power-radiofrequency-transmitter",
    ),
    "software-commanded-unsafe-state": (
        "safety-critical-command-path",
        "autonomous-control-function",
    ),
    "ground-handling-and-personnel-access": (
        "lifting-operation",
        "confined-access-area",
        "propellant-loading-operation",
    ),
}

# Fields the annex B register example carries per record.
REGISTER_RECORD_FIELDS = (
    "hazard_id",
    "hazard_group",
    "cause",
    "effect",
    "control",
    "verification_reference",
)

# Call strength is a quotient of two small counts, so a fully called
# group can land a few units in the last place under 1.0.
STRENGTH_TOLERANCE = 1.0e-12


def _string(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _sequence(label, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (label, value))
    return list(value)


def known_characteristics():
    """Every system characteristic the library keys on, sorted."""
    out = set()
    for keys in GENERIC_HAZARD_LIBRARY.values():
        out.update(keys)
    return sorted(out)


def hazard_groups():
    """Every generic hazard group in the library, sorted."""
    return sorted(GENERIC_HAZARD_LIBRARY)


def validate_characteristics(characteristics):
    """Validate a system characteristic list and return a sorted copy."""
    items = _sequence("characteristics", characteristics)
    if not items:
        raise ValueError("characteristics must not be empty")
    known = set(known_characteristics())
    out = []
    for item in items:
        name = _string("characteristic", item)
        if name not in known:
            raise ValueError(
                "unknown system characteristic %r (the library keys on %d known "
                "characteristics)" % (name, len(known))
            )
        out.append(name)
    return sorted(set(out))


def call_strength(group, characteristics):
    """Fraction of a group's keying characteristics the system has."""
    if group not in GENERIC_HAZARD_LIBRARY:
        raise ValueError("unknown hazard group %r" % (group,))
    keys = GENERIC_HAZARD_LIBRARY[group]
    present = set(validate_characteristics(characteristics))
    matched = [k for k in keys if k in present]
    return float(len(matched)) / float(len(keys))


def seed_candidates(characteristics):
    """Candidate hazard groups a system's characteristics call, ranked."""
    present = validate_characteristics(characteristics)
    present_set = set(present)
    candidates = []
    for group in hazard_groups():
        keys = GENERIC_HAZARD_LIBRARY[group]
        matched = [k for k in keys if k in present_set]
        if not matched:
            continue
        candidates.append(
            {
                "hazard_group": group,
                "matched_characteristics": matched,
                "call_strength": float(len(matched)) / float(len(keys)),
            }
        )
    candidates.sort(key=lambda c: (-c["call_strength"], c["hazard_group"]))
    return candidates


def uncalled_groups(characteristics):
    """Library groups nothing in the system called, sorted."""
    called = {c["hazard_group"] for c in seed_candidates(characteristics)}
    return [g for g in hazard_groups() if g not in called]


def validate_register_record(record):
    """Validate one register record and return it with its findings."""
    if not isinstance(record, dict):
        raise ValueError("register record must be a mapping")
    findings = []
    for field in REGISTER_RECORD_FIELDS:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            findings.append("register-record-missing:%s" % field)
    group = record.get("hazard_group")
    if isinstance(group, str) and group.strip() and group not in GENERIC_HAZARD_LIBRARY:
        findings.append("register-record-group-outside-library:%s" % group.strip())
    return {
        "hazard_id": record.get("hazard_id"),
        "hazard_group": group,
        "findings": findings,
        "complete": not findings,
    }


def grade_register(records):
    """Grade a hazard register against the annex B example field set."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = validate_register_record(record)
        rid = result["hazard_id"]
        if isinstance(rid, str) and rid.strip():
            if rid in seen:
                raise ValueError("duplicate register record id %r" % (rid,))
            seen.add(rid)
        results.append(result)
    incomplete = [r["hazard_id"] for r in results if not r["complete"]]
    return {
        "records": results,
        "incomplete_ids": incomplete,
        "complete": not incomplete,
    }


def seed_and_grade(characteristics, records):
    """Seed from the library and grade the register the seeding produced."""
    candidates = seed_candidates(characteristics)
    graded = grade_register(records)
    covered = set()
    for result in graded["records"]:
        group = result["hazard_group"]
        if isinstance(group, str) and group.strip():
            covered.add(group.strip())
    unregistered = [
        c["hazard_group"] for c in candidates if c["hazard_group"] not in covered
    ]
    findings = list(
        "seeded-candidate-not-in-register:%s" % g for g in unregistered
    )
    for result in graded["records"]:
        for finding in result["findings"]:
            findings.append("%s:%s" % (finding, result["hazard_id"]))
    return {
        "candidates": candidates,
        "uncalled_groups": uncalled_groups(characteristics),
        "register": graded,
        "unregistered_candidates": unregistered,
        "findings": findings,
        "seeded": not findings,
    }
