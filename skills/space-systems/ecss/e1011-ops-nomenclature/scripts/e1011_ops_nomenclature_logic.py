"""
ECSS-E-ST-10-11C §4.3.3 operations nomenclature consistency checker.

Validates crew role labels, mission phase terms, and command type
designators against canonical vocabularies. Detects synonym conflicts
where a single concept is referenced by multiple non-equivalent labels
within the same document.
"""

CANONICAL_CREW_ROLES = frozenset({
    "commander",
    "pilot",
    "mission specialist",
    "payload specialist",
    "flight engineer",
    "science officer",
    "ground controller",
    "flight director",
    "capcom",
    "systems engineer",
    "flight surgeon",
})

CANONICAL_MISSION_PHASES = frozenset({
    "launch",
    "ascent",
    "orbit insertion",
    "on-orbit operations",
    "rendezvous",
    "docking",
    "undocking",
    "de-orbit",
    "reentry",
    "landing",
    "recovery",
    "contingency",
    "abort",
})

CANONICAL_COMMAND_TYPES = frozenset({
    "nominal command",
    "emergency command",
    "time-tagged command",
    "delayed command",
    "immediate command",
    "verified command",
    "inhibit command",
    "enable command",
})

# Abbreviations and synonyms that resolve to a canonical crew role.
ROLE_SYNONYMS = {
    "cdm": "commander",
    "cdr": "commander",
    "plt": "pilot",
    "ms": "mission specialist",
    "ps": "payload specialist",
    "fe": "flight engineer",
    "so": "science officer",
    "fc": "flight director",
    "fltdir": "flight director",
    "gnd ctrl": "ground controller",
    "flt surg": "flight surgeon",
    "sys eng": "systems engineer",
}

# Non-standard phase terms that resolve to a canonical phase.
PHASE_SYNONYMS = {
    "liftoff": "launch",
    "launch phase": "launch",
    "orbital operations": "on-orbit operations",
    "on orbit": "on-orbit operations",
    "deorbit": "de-orbit",
    "de orbit": "de-orbit",
    "re-entry": "reentry",
    "entry": "reentry",
    "touchdown": "landing",
    "touch down": "landing",
    "dock": "docking",
    "undock": "undocking",
    "abort mode": "abort",
    "contingency mode": "contingency",
}


class NomenclatureViolation:
    """A single nomenclature inconsistency finding."""

    __slots__ = ("category", "term", "location", "detail")

    def __init__(self, category, term, location, detail):
        self.category = category  # "crew_role" | "mission_phase" | "command_type" | "synonym_conflict"
        self.term = term
        self.location = location
        self.detail = detail

    def __repr__(self):
        return (
            f"NomenclatureViolation("
            f"category={self.category!r}, term={self.term!r}, "
            f"location={self.location!r})"
        )

    def __eq__(self, other):
        if not isinstance(other, NomenclatureViolation):
            return NotImplemented
        return (
            self.category == other.category
            and self.term == other.term
            and self.location == other.location
        )


def check_crew_roles(roles_used):
    """
    Validate a list of crew role labels.

    roles_used: iterable of (term: str, location: str).
    Returns list of NomenclatureViolation.
    """
    violations = []
    for term, location in roles_used:
        normalized = term.strip().lower()
        if normalized in CANONICAL_CREW_ROLES:
            continue
        if normalized in ROLE_SYNONYMS:
            canonical = ROLE_SYNONYMS[normalized]
            violations.append(NomenclatureViolation(
                "crew_role", term, location,
                f"Non-standard label '{term}'; use canonical form '{canonical}'",
            ))
        else:
            violations.append(NomenclatureViolation(
                "crew_role", term, location,
                f"Unrecognized crew role '{term}'; not in canonical set",
            ))
    return violations


def check_mission_phases(phases_used):
    """
    Validate a list of mission phase terms.

    phases_used: iterable of (term: str, location: str).
    Returns list of NomenclatureViolation.
    """
    violations = []
    for term, location in phases_used:
        normalized = term.strip().lower()
        if normalized in CANONICAL_MISSION_PHASES:
            continue
        if normalized in PHASE_SYNONYMS:
            canonical = PHASE_SYNONYMS[normalized]
            violations.append(NomenclatureViolation(
                "mission_phase", term, location,
                f"Non-standard phase term '{term}'; use canonical form '{canonical}'",
            ))
        else:
            violations.append(NomenclatureViolation(
                "mission_phase", term, location,
                f"Unrecognized mission phase '{term}'; not in canonical set",
            ))
    return violations


def check_command_types(commands_used):
    """
    Validate a list of command type designators.

    commands_used: iterable of (term: str, location: str).
    Returns list of NomenclatureViolation.
    """
    violations = []
    for term, location in commands_used:
        normalized = term.strip().lower()
        if normalized in CANONICAL_COMMAND_TYPES:
            continue
        violations.append(NomenclatureViolation(
            "command_type", term, location,
            f"Unrecognized command type '{term}'; not in authorized taxonomy",
        ))
    return violations


def check_synonym_conflicts(term_locations):
    """
    Detect synonym conflicts within a document.

    A synonym conflict exists when two or more distinct labels that
    resolve to the same canonical concept both appear in the document.

    term_locations: dict mapping term (str) -> list of location strings.
    Returns list of NomenclatureViolation, one per conflicted canonical concept.
    """
    all_synonyms = {}
    all_synonyms.update(ROLE_SYNONYMS)
    all_synonyms.update(PHASE_SYNONYMS)

    canonical_to_forms = {}
    for term in term_locations:
        normalized = term.strip().lower()
        if normalized in CANONICAL_CREW_ROLES or normalized in CANONICAL_MISSION_PHASES or normalized in CANONICAL_COMMAND_TYPES:
            canonical = normalized
        elif normalized in all_synonyms:
            canonical = all_synonyms[normalized]
        else:
            continue

        if canonical not in canonical_to_forms:
            canonical_to_forms[canonical] = []
        canonical_to_forms[canonical].append(normalized)

    violations = []
    for canonical, forms in canonical_to_forms.items():
        unique_forms = list(dict.fromkeys(forms))
        if len(unique_forms) > 1:
            all_locs = []
            for t in term_locations:
                if t.strip().lower() in unique_forms:
                    all_locs.extend(term_locations[t])
            violations.append(NomenclatureViolation(
                "synonym_conflict", canonical, str(all_locs),
                f"Concept '{canonical}' appears under multiple labels: {unique_forms}; "
                f"resolve to the canonical form throughout",
            ))
    return violations


def assess_document(crew_roles, mission_phases, command_types, term_locations):
    """
    Full nomenclature assessment for a document.

    crew_roles: list of (term, location) for crew role references.
    mission_phases: list of (term, location) for phase references.
    command_types: list of (term, location) for command type references.
    term_locations: dict of term -> [location, ...] for conflict detection.

    Returns a result dict with per-category violations and overall compliance.
    """
    if term_locations is None:
        raise ValueError("term_locations must be a dict, not None")

    role_findings = check_crew_roles(crew_roles)
    phase_findings = check_mission_phases(mission_phases)
    cmd_findings = check_command_types(command_types)
    conflict_findings = check_synonym_conflicts(term_locations)

    all_findings = role_findings + phase_findings + cmd_findings + conflict_findings

    return {
        "crew_role_violations": role_findings,
        "mission_phase_violations": phase_findings,
        "command_type_violations": cmd_findings,
        "synonym_conflicts": conflict_findings,
        "total_violations": len(all_findings),
        "compliant": len(all_findings) == 0,
    }
