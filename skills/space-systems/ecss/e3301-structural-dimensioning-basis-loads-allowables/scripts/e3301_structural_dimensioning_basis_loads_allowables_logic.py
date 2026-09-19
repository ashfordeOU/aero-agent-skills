"""Load and allowable basis for spacecraft mechanism structural dimensioning.

Anchor: ECSS-E-ST-33-01 clauses 4.7.5.2.1 to 4.7.5.2.4 (paraphrased into
an implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Collect the limit loads. Each load case names the mission event it
   comes from and the basis it was obtained on (a measurement, a
   coupled-loads analysis, a specification envelope or an engineering
   estimate). The basis is what fixes the model factor, so an
   uncategorized basis is rejected rather than defaulted.
2. Raise each limit load into a design limit load by the model factor
   its basis carries and by the declared project factor. The two are
   applied to the load, never folded into the allowable, so a later
   margin computation cannot apply either of them twice.
3. Envelope the design limit loads. The case that sizes the part is the
   largest one, and it is named, because a part dimensioned on a mean
   or a root-sum-square of the cases is dimensioned on no case at all.
4. Pair the load with an allowable whose statistical basis matches the
   redundancy of the load path. A single load path has no alternative
   route for the load, so it carries a basis that bounds the material
   population; a redundant path admits a less severe basis. A typical
   or average value is a description of a population, not a bound on
   it, and is never admissible for dimensioning.
5. Reduce the room-temperature allowable by the retention the material
   actually keeps at the design temperature, and require that the
   allowable was stated at a temperature that covers the part.

Stdlib only, offline, deterministic.
"""

# Mission events a mechanism load case can be drawn from.
VALID_EVENTS = (
    "ground-handling",
    "launch-quasi-static",
    "launch-random-equivalent",
    "launch-shock",
    "thermoelastic",
    "actuation-induced",
    "deployment-shock",
    "on-orbit-operational",
)

# A mechanism that flies has to be dimensioned for at least the launch
# ride and the operational life; a schedule missing either is incomplete
# whatever the other cases say.
MANDATORY_EVENTS = ("launch-quasi-static", "on-orbit-operational")

# How the limit load was obtained, and the model factor that knowledge
# basis carries. A measured load needs no uplift; an estimate needs the
# most.
MODEL_FACTOR_BY_BASIS = {
    "measured-test": 1.00,
    "coupled-loads-analysis": 1.10,
    "specification-envelope": 1.20,
    "engineering-estimate": 1.50,
}
VALID_LOAD_BASES = tuple(sorted(MODEL_FACTOR_BY_BASIS))

# Statistical basis of a material allowable.
BASIS_TYPICAL = "typical-average"
VALID_ALLOWABLE_BASES = ("a-basis", "b-basis", "s-basis", BASIS_TYPICAL)

# Redundancy of the load path, and the allowable bases it admits.
VALID_LOAD_PATHS = ("single", "redundant")
ADMISSIBLE_BASES_BY_LOAD_PATH = {
    "single": ("a-basis", "s-basis"),
    "redundant": ("a-basis", "b-basis", "s-basis"),
}

# Material properties a dimensioning basis has to carry.
REQUIRED_PROPERTIES = ("yield", "ultimate")
VALID_PROPERTIES = REQUIRED_PROPERTIES

# A design load is a product of floats, so a case sitting exactly on the
# envelope can land a few units in the last place away from it. This
# tolerance absorbs that representation error without relaxing anything.
LOAD_TOLERANCE = 1.0e-12

# Temperature band a room-temperature allowable is taken to cover.
ROOM_TEMPERATURE_BAND_C = (15.0, 30.0)


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return value


def _identifier(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def model_factor(load_basis):
    """Model factor carried by the knowledge basis of a limit load."""
    if load_basis not in MODEL_FACTOR_BY_BASIS:
        raise ValueError(
            "unknown load basis %r (expected one of %s)"
            % (load_basis, ", ".join(VALID_LOAD_BASES))
        )
    return MODEL_FACTOR_BY_BASIS[load_basis]


def validate_load_case(case):
    """Validate one mechanism load case and return a normalized copy."""
    if not isinstance(case, dict):
        raise ValueError("load case must be a mapping")
    case_id = _identifier("load case id", case.get("id"))
    event = case.get("event")
    if event not in VALID_EVENTS:
        raise ValueError(
            "load case %s has unknown event %r (expected one of %s)"
            % (case_id, event, ", ".join(VALID_EVENTS))
        )
    basis = case.get("load_basis")
    if basis not in MODEL_FACTOR_BY_BASIS:
        raise ValueError(
            "load case %s has unknown load_basis %r (expected one of %s)"
            % (case_id, basis, ", ".join(VALID_LOAD_BASES))
        )
    limit_load = _numeric("load case %s limit_load" % case_id, case.get("limit_load"), 0.0)
    project_factor = _numeric(
        "load case %s project_factor" % case_id, case.get("project_factor", 1.0), 1.0
    )
    return {
        "id": case_id,
        "event": event,
        "load_basis": basis,
        "limit_load": limit_load,
        "project_factor": project_factor,
    }


def design_limit_load(case):
    """Limit load raised by the model factor and the project factor."""
    norm = validate_load_case(case)
    return norm["limit_load"] * norm["project_factor"] * model_factor(norm["load_basis"])


def envelope_design_limit_load(cases):
    """Largest design limit load in a schedule, and the case that drives it."""
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must be a non-empty list")
    per_case = []
    seen = set()
    for case in cases:
        norm = validate_load_case(case)
        if norm["id"] in seen:
            raise ValueError("duplicate load case id %r" % (norm["id"],))
        seen.add(norm["id"])
        per_case.append(
            {
                "id": norm["id"],
                "event": norm["event"],
                "design_limit_load": design_limit_load(norm),
            }
        )
    driving = per_case[0]
    for entry in per_case[1:]:
        if entry["design_limit_load"] > driving["design_limit_load"] + LOAD_TOLERANCE:
            driving = entry
    return {
        "design_limit_load": driving["design_limit_load"],
        "driving_case_id": driving["id"],
        "driving_event": driving["event"],
        "per_case": per_case,
    }


def uncovered_mandatory_events(cases):
    """Mandatory mission events with no load case in the schedule."""
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must be a non-empty list")
    present = set(validate_load_case(case)["event"] for case in cases)
    return [event for event in MANDATORY_EVENTS if event not in present]


def validate_allowable(allowable):
    """Validate one material allowable record and return a normalized copy."""
    if not isinstance(allowable, dict):
        raise ValueError("allowable must be a mapping")
    material = _identifier("allowable material", allowable.get("material"))
    prop = allowable.get("property")
    if prop not in VALID_PROPERTIES:
        raise ValueError(
            "allowable for %s has unknown property %r (expected one of %s)"
            % (material, prop, ", ".join(VALID_PROPERTIES))
        )
    basis = allowable.get("basis")
    if basis not in VALID_ALLOWABLE_BASES:
        raise ValueError(
            "allowable for %s has unknown basis %r (expected one of %s)"
            % (material, basis, ", ".join(VALID_ALLOWABLE_BASES))
        )
    room_value = _numeric(
        "allowable for %s room_value" % material, allowable.get("room_value"), 0.0
    )
    if room_value <= 0.0:
        raise ValueError("allowable for %s room_value must be positive" % material)
    retention = _numeric(
        "allowable for %s retention_factor" % material,
        allowable.get("retention_factor", 1.0),
        0.0,
        1.0,
    )
    if retention <= 0.0:
        raise ValueError(
            "allowable for %s retention_factor must be positive" % material
        )
    stated_c = allowable.get("stated_temperature_c")
    if stated_c is not None:
        stated_c = _numeric("allowable for %s stated_temperature_c" % material, stated_c)
    return {
        "material": material,
        "property": prop,
        "basis": basis,
        "room_value": room_value,
        "retention_factor": retention,
        "stated_temperature_c": stated_c,
    }


def allowable_basis_admissible(basis, load_path):
    """Return (admissible, reason) for a basis against a load-path redundancy."""
    if basis not in VALID_ALLOWABLE_BASES:
        raise ValueError(
            "unknown allowable basis %r (expected one of %s)"
            % (basis, ", ".join(VALID_ALLOWABLE_BASES))
        )
    if load_path not in VALID_LOAD_PATHS:
        raise ValueError(
            "unknown load_path %r (expected one of %s)"
            % (load_path, ", ".join(VALID_LOAD_PATHS))
        )
    if basis == BASIS_TYPICAL:
        return False, "typical-average-is-not-a-bound-on-the-population"
    if basis in ADMISSIBLE_BASES_BY_LOAD_PATH[load_path]:
        return True, "basis-matches-load-path-redundancy"
    return False, "single-load-path-needs-a-population-bounding-basis"


def design_allowable(allowable):
    """Room allowable reduced by the retention kept at design temperature."""
    norm = validate_allowable(allowable)
    return norm["room_value"] * norm["retention_factor"]


def allowable_covers_temperature(allowable, design_temperature_c):
    """True when the allowable was stated at or beyond the design temperature."""
    norm = validate_allowable(allowable)
    design_c = _numeric("design_temperature_c", design_temperature_c)
    stated_c = norm["stated_temperature_c"]
    if stated_c is None:
        low, high = ROOM_TEMPERATURE_BAND_C
        return low <= design_c <= high
    if design_c >= 0.0:
        return stated_c >= design_c
    return stated_c <= design_c


def assess_dimensioning_basis(part):
    """Assess the load and allowable basis of one mechanism part."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    part_id = _identifier("part id", part.get("id"))
    load_path = part.get("load_path")
    if load_path not in VALID_LOAD_PATHS:
        raise ValueError(
            "part %s has unknown load_path %r (expected one of %s)"
            % (part_id, load_path, ", ".join(VALID_LOAD_PATHS))
        )
    design_c = _numeric(
        "part %s design_temperature_c" % part_id, part.get("design_temperature_c", 20.0)
    )
    cases = part.get("load_cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("part %s needs a non-empty load_cases list" % part_id)
    allowables = part.get("allowables")
    if not isinstance(allowables, list) or not allowables:
        raise ValueError("part %s needs a non-empty allowables list" % part_id)

    envelope = envelope_design_limit_load(cases)
    findings = []
    for event in uncovered_mandatory_events(cases):
        findings.append("mandatory-event-not-covered:%s" % event)

    resolved = {}
    for allowable in allowables:
        norm = validate_allowable(allowable)
        prop = norm["property"]
        if prop in resolved:
            raise ValueError(
                "part %s declares the %s allowable twice" % (part_id, prop)
            )
        admissible, reason = allowable_basis_admissible(norm["basis"], load_path)
        entry = {
            "property": prop,
            "material": norm["material"],
            "basis": norm["basis"],
            "basis_admissible": admissible,
            "basis_reason": reason,
            "design_allowable": design_allowable(norm),
            "covers_design_temperature": allowable_covers_temperature(norm, design_c),
        }
        if not admissible:
            findings.append("allowable-basis-not-admissible:%s" % prop)
        if not entry["covers_design_temperature"]:
            findings.append("allowable-not-stated-at-design-temperature:%s" % prop)
        resolved[prop] = entry

    for prop in REQUIRED_PROPERTIES:
        if prop not in resolved:
            findings.append("allowable-missing:%s" % prop)

    return {
        "part_id": part_id,
        "load_path": load_path,
        "design_temperature_c": design_c,
        "design_limit_load": envelope["design_limit_load"],
        "driving_case_id": envelope["driving_case_id"],
        "driving_event": envelope["driving_event"],
        "per_case": envelope["per_case"],
        "allowables": [resolved[p] for p in sorted(resolved)],
        "findings": findings,
        "basis_complete": not findings,
    }
