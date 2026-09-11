"""
ECSS-E-ST-10-11C §4.3.7 — HFE Requirement Identification logic.

Deterministic, offline, stdlib-only. No third-party dependencies.
"""

import re
from typing import List, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------

VALID_PHASES: Dict[str, str] = {
    "launch":       "LCH",
    "ascent":       "ASC",
    "orbit":        "ORB",
    "re-entry":     "REE",
    "landing":      "LND",
    "maintenance":  "MNT",
    "contingency":  "CON",
}

VALID_ROLES: Dict[str, str] = {
    "crew":          "CRW",
    "commander":     "CMD",
    "ground_control": "GND",
    "maintainer":    "MNT",
}

VALID_DRIVERS: Dict[str, str] = {
    "workload":      "WKL",
    "habitability":  "HAB",
    "anthropometry": "ANT",
    "visibility":    "VIS",
    "reachability":  "RCH",
    "cognitive":     "COG",
    "communication": "COM",
    "safety":        "SAF",
}

# Drivers that must appear in every phase (ECSS-E-ST-10-11C §4.3.7)
MANDATORY_DRIVERS = {"safety", "workload"}

# Requirement ID pattern: HFE-<3-letter phase>-<3-letter role>-<3-letter driver>-<3-digit seq>
_REQ_ID_PATTERN = re.compile(r"^HFE-[A-Z]{3}-[A-Z]{3}-[A-Z]{3}-\d{3}$")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

class ValidationError(ValueError):
    """Raised when a token or structure violates the controlled vocabulary."""


def validate_phase(phase: str) -> str:
    """Return the phase code for *phase* or raise ValidationError."""
    code = VALID_PHASES.get(phase)
    if code is None:
        raise ValidationError(
            f"Unknown phase '{phase}'. Valid phases: {sorted(VALID_PHASES)}"
        )
    return code


def validate_role(role: str) -> str:
    """Return the role code for *role* or raise ValidationError."""
    code = VALID_ROLES.get(role)
    if code is None:
        raise ValidationError(
            f"Unknown role '{role}'. Valid roles: {sorted(VALID_ROLES)}"
        )
    return code


def validate_driver(driver: str) -> str:
    """Return the driver code for *driver* or raise ValidationError."""
    code = VALID_DRIVERS.get(driver)
    if code is None:
        raise ValidationError(
            f"Unknown HFE driver '{driver}'. Valid drivers: {sorted(VALID_DRIVERS)}"
        )
    return code


def validate_req_id_format(req_id: str) -> bool:
    """Return True if *req_id* matches the structured ID format, else False."""
    return bool(_REQ_ID_PATTERN.match(req_id))


# ---------------------------------------------------------------------------
# Requirement ID generation
# ---------------------------------------------------------------------------

def generate_req_id(phase: str, role: str, driver: str, seq: int) -> str:
    """
    Generate a structured HFE requirement ID.

    Format: HFE-<PHASE_CODE>-<ROLE_CODE>-<DRIVER_CODE>-<SEQ>

    All three tokens are validated against the controlled vocabulary.
    *seq* must be in [1, 999].
    """
    if not (1 <= seq <= 999):
        raise ValidationError(f"seq must be in [1, 999], got {seq}")
    phase_code = validate_phase(phase)
    role_code = validate_role(role)
    driver_code = validate_driver(driver)
    return f"HFE-{phase_code}-{role_code}-{driver_code}-{seq:03d}"


# ---------------------------------------------------------------------------
# Core requirement identification
# ---------------------------------------------------------------------------

def identify_requirements(
    mission_phases: List[str],
    roles_per_phase: Dict[str, List[str]],
    drivers_per_phase_role: Dict[Tuple[str, str], List[str]],
) -> List[str]:
    """
    Generate the full set of structured HFE requirement IDs.

    Parameters
    ----------
    mission_phases:
        Ordered list of mission phase tokens (from the controlled vocabulary).
    roles_per_phase:
        Mapping of phase token → list of active role tokens.
    drivers_per_phase_role:
        Mapping of (phase, role) tuple → list of applicable HFE driver tokens.
        The mandatory drivers (safety, workload) are automatically added to
        every pair if not already present.

    Returns
    -------
    List of requirement ID strings in generation order.

    Raises
    ------
    ValidationError
        If any phase, role, or driver token is outside the controlled vocabulary,
        or if a phase has no assigned roles.
    """
    # Validate all phases first
    for phase in mission_phases:
        validate_phase(phase)  # raises on unknown token

    requirements: List[str] = []

    for phase in mission_phases:
        roles = roles_per_phase.get(phase, [])
        if not roles:
            raise ValidationError(
                f"Phase '{phase}' has no assigned operator roles. "
                "At least one role must be active in every phase."
            )
        for role in roles:
            validate_role(role)  # raises on unknown token

            raw_drivers = list(drivers_per_phase_role.get((phase, role), []))
            # Enforce mandatory drivers
            for mandatory in MANDATORY_DRIVERS:
                if mandatory not in raw_drivers:
                    raw_drivers.append(mandatory)

            # Validate and deduplicate while preserving order
            seen_drivers: Dict[str, None] = {}
            for driver in raw_drivers:
                validate_driver(driver)
                seen_drivers[driver] = None
            deduped = list(seen_drivers)

            seq = 1
            for driver in deduped:
                req_id = generate_req_id(phase, role, driver, seq)
                requirements.append(req_id)
                seq += 1

    return requirements


# ---------------------------------------------------------------------------
# Post-generation checks
# ---------------------------------------------------------------------------

def check_completeness(
    requirements: List[str],
    mission_phases: List[str],
) -> List[str]:
    """
    Return a list of gap descriptions for phases missing mandatory drivers.

    A gap exists when no requirement ID for a phase encodes a mandatory driver
    code (SAF or WKL). Returns an empty list when all mandatory drivers are
    present for every phase.
    """
    gaps: List[str] = []
    mandatory_codes = {
        driver: VALID_DRIVERS[driver] for driver in MANDATORY_DRIVERS
    }

    for phase in mission_phases:
        phase_code = VALID_PHASES.get(phase)
        if phase_code is None:
            gaps.append(f"Unknown phase '{phase}' — cannot assess completeness.")
            continue
        for driver_name, driver_code in mandatory_codes.items():
            prefix = f"HFE-{phase_code}-"
            suffix_fragment = f"-{driver_code}-"
            has_match = any(
                r.startswith(prefix) and suffix_fragment in r
                for r in requirements
            )
            if not has_match:
                gaps.append(
                    f"Phase '{phase}' is missing a mandatory HFE requirement "
                    f"for driver '{driver_name}' (code {driver_code})."
                )
    return gaps


def check_uniqueness(requirements: List[str]) -> List[str]:
    """
    Return a list of duplicate requirement IDs.

    Returns an empty list when all IDs are unique.
    """
    seen: Dict[str, int] = {}
    duplicates: List[str] = []
    for req_id in requirements:
        seen[req_id] = seen.get(req_id, 0) + 1
    for req_id, count in seen.items():
        if count > 1:
            duplicates.append(f"Duplicate ID '{req_id}' appears {count} times.")
    return duplicates


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_identification(
    mission_phases: List[str],
    roles_per_phase: Dict[str, List[str]],
    drivers_per_phase_role: Dict[Tuple[str, str], List[str]],
) -> Dict:
    """
    Execute the full HFE requirement identification pipeline.

    Returns a dict with keys:
    - 'requirements': List[str] — generated requirement IDs
    - 'gaps': List[str] — completeness gap descriptions
    - 'duplicates': List[str] — duplicate ID descriptions
    - 'ready': bool — True iff gaps and duplicates are both empty
    """
    requirements = identify_requirements(
        mission_phases, roles_per_phase, drivers_per_phase_role
    )
    gaps = check_completeness(requirements, mission_phases)
    duplicates = check_uniqueness(requirements)
    return {
        "requirements": requirements,
        "gaps": gaps,
        "duplicates": duplicates,
        "ready": len(gaps) == 0 and len(duplicates) == 0,
    }
