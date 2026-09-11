"""
Organisational environment assessment logic for ECSS-E-ST-10-11C §4.2.1.5.

Paraphrased procedure — no verbatim ECSS text. Cite: ECSS-E-ST-10-11C §4.2.1.5.
stdlib only; offline; deterministic.
"""

VALID_AUTHORITY_LEVELS = frozenset({"commander", "crew-member", "specialist", "observer"})
VALID_INTERFACE_TYPES = frozenset({"direct-voice", "data-link", "video", "text", "indirect"})
VALID_PROC_TYPES = frozenset({"nominal", "contingency", "emergency", "maintenance", "handover"})
MANDATORY_GROUND_FUNCTIONS = frozenset({"flight-control", "systems-monitoring", "crew-support"})


def validate_crew_role(role):
    """
    Validate a single crew role entry.

    Returns a list of error strings; empty when the entry is valid.
    A valid entry has non-empty title, responsibility, and authority_level,
    where authority_level is one of VALID_AUTHORITY_LEVELS.
    """
    errors = []
    for field in ("title", "responsibility", "authority_level"):
        if not role.get(field):
            errors.append(f"crew_role missing field '{field}'")
    authority = role.get("authority_level")
    if authority and authority not in VALID_AUTHORITY_LEVELS:
        errors.append(
            f"crew_role authority_level '{authority}' not in "
            f"{sorted(VALID_AUTHORITY_LEVELS)}"
        )
    return errors


def check_commander_present(crew_roles):
    """
    Return True if at least one crew role has authority_level == 'commander'.

    A missing commander leaves the authority chain undefined;
    the org-env record is non-compliant without one.
    """
    return any(r.get("authority_level") == "commander" for r in crew_roles)


def check_duplicate_titles(crew_roles):
    """
    Return a sorted list of role titles that appear more than once.

    Duplicate titles suggest a data entry error or an unresolved role split.
    """
    seen = set()
    duplicates = set()
    for role in crew_roles:
        title = role.get("title", "")
        if title in seen:
            duplicates.add(title)
        else:
            seen.add(title)
    return sorted(duplicates)


def validate_ground_unit(unit):
    """
    Validate a single ground support unit entry.

    Returns a list of error strings; empty when the entry is valid.
    A valid entry has non-empty unit_name, function, and interface_type,
    where interface_type is one of VALID_INTERFACE_TYPES.
    """
    errors = []
    for field in ("unit_name", "function", "interface_type"):
        if not unit.get(field):
            errors.append(f"ground_unit missing field '{field}'")
    itype = unit.get("interface_type")
    if itype and itype not in VALID_INTERFACE_TYPES:
        errors.append(
            f"ground_unit interface_type '{itype}' not in "
            f"{sorted(VALID_INTERFACE_TYPES)}"
        )
    return errors


def check_mandatory_ground_functions(ground_units):
    """
    Return a sorted list of mandatory ground functions not covered by any unit.

    Mandatory functions: flight-control, systems-monitoring, crew-support.
    A unit covers a function when its 'function' field matches exactly.
    """
    covered = {u.get("function") for u in ground_units if u.get("function")}
    return sorted(MANDATORY_GROUND_FUNCTIONS - covered)


def validate_procedure_entry(proc):
    """
    Validate a single procedure entry.

    Returns a list of error strings; empty when the entry is valid.
    Required fields: proc_type (from VALID_PROC_TYPES), approval_authority.
    Optional: review_cycle_days — when present must be a positive number.
    """
    errors = []
    for field in ("proc_type", "approval_authority"):
        if not proc.get(field):
            errors.append(f"procedure missing field '{field}'")
    ptype = proc.get("proc_type")
    if ptype and ptype not in VALID_PROC_TYPES:
        errors.append(
            f"procedure proc_type '{ptype}' not in "
            f"{sorted(VALID_PROC_TYPES)}"
        )
    review_days = proc.get("review_cycle_days")
    if review_days is not None:
        if not isinstance(review_days, (int, float)) or isinstance(review_days, bool) or review_days <= 0:
            errors.append(
                f"procedure review_cycle_days must be a positive number, got '{review_days}'"
            )
    return errors


def assess_org_env(org_env):
    """
    Top-level assessment of an organisational environment record.

    Expected input structure::

        {
          "crew_roles":    [{"title": str, "responsibility": str, "authority_level": str}, ...],
          "ground_units":  [{"unit_name": str, "function": str, "interface_type": str}, ...],
          "procedures":    [{"proc_type": str, "approval_authority": str,
                             "review_cycle_days": int|float}, ...]
        }

    Returns::

        {
          "compliant": bool,   # True only when findings is empty
          "findings":  [str]   # ordered list of finding strings
        }

    The record is compliant only when every crew role is valid, a commander
    is present, no duplicate titles exist, every ground unit is valid, all
    three mandatory ground functions are covered, at least one ground unit is
    present, and every procedure entry is valid.
    """
    findings = []

    crew_roles = org_env.get("crew_roles", [])
    ground_units = org_env.get("ground_units", [])
    procedures = org_env.get("procedures", [])

    for i, role in enumerate(crew_roles):
        for err in validate_crew_role(role):
            findings.append(f"crew_role[{i}]: {err}")

    if not check_commander_present(crew_roles):
        findings.append("no crew role with authority_level 'commander' found")

    for dup in check_duplicate_titles(crew_roles):
        findings.append(f"duplicate crew role title: '{dup}'")

    for i, unit in enumerate(ground_units):
        for err in validate_ground_unit(unit):
            findings.append(f"ground_unit[{i}]: {err}")

    if not ground_units:
        findings.append("no ground support units recorded")

    for fn in check_mandatory_ground_functions(ground_units):
        findings.append(f"mandatory ground function not covered: '{fn}'")

    for i, proc in enumerate(procedures):
        for err in validate_procedure_entry(proc):
            findings.append(f"procedure[{i}]: {err}")

    return {"compliant": len(findings) == 0, "findings": findings}
