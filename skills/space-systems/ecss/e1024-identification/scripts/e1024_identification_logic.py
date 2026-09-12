"""
Interface identification logic — ECSS-E-ST-10-24C §5.2.

Paraphrased from ECSS-E-ST-10-24C; no verbatim standard text reproduced.
Encodes the §5.2 interface-category taxonomy, identifier-generation scheme,
interface-record construction, list validation, and interface-tree building.
All functions are deterministic and offline.
"""

# ---------------------------------------------------------------------------
# §5.2  Interface-category taxonomy
# ---------------------------------------------------------------------------

INTERFACE_CATEGORIES = {
    "mechanical": {
        "code": "MEC",
        "description": "Structural, kinematic, and acoustic connections between elements",
        "examples": ["bolt_pattern", "separation_mechanism", "acoustic_coupling"],
    },
    "electrical": {
        "code": "ELC",
        "description": "Power, grounding, and harness connections",
        "examples": ["power_bus", "grounding_strap", "harness_connector"],
    },
    "data": {
        "code": "DAT",
        "description": "Software, protocol, and signal path interfaces",
        "examples": ["mil_std_1553", "spacewire", "rs422", "can_bus"],
    },
    "thermal": {
        "code": "THM",
        "description": "Thermal conduction and radiation coupling interfaces",
        "examples": ["thermal_strap", "heat_pipe_coupling", "radiative_coupling"],
    },
    "fluid": {
        "code": "FLD",
        "description": "Propellant, pressurant, and coolant flow connections",
        "examples": ["propellant_line", "pressurant_feed", "coolant_loop"],
    },
    "rf": {
        "code": "RF_",
        "description": "Radio-frequency and antenna interfaces",
        "examples": ["s_band_antenna", "uhf_link", "ka_band_feeder"],
    },
    "optical": {
        "code": "OPT",
        "description": "Light-path and optical alignment interfaces",
        "examples": ["telescope_focal_plane", "star_tracker_boresight"],
    },
}

# Aliases that map alternate spellings to the canonical category key
_CATEGORY_ALIASES = {
    "mech": "mechanical",
    "mec": "mechanical",
    "elec": "electrical",
    "elc": "electrical",
    "sw": "data",
    "software": "data",
    "signal": "data",
    "therm": "thermal",
    "thm": "thermal",
    "prop": "fluid",
    "fld": "fluid",
    "rf_": "rf",
    "radio": "rf",
    "opt": "optical",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_categories() -> list:
    """Return the list of canonical interface-category keys (§5.2 taxonomy)."""
    return list(INTERFACE_CATEGORIES.keys())


def normalize_category(raw: str) -> str:
    """
    Return the canonical category key for *raw*.

    Accepts both canonical keys (e.g. 'electrical') and known aliases
    (e.g. 'elec', 'elc').  Input is matched case-insensitively.

    Parameters
    ----------
    raw : str
        Raw category label from the interface record.

    Returns
    -------
    str
        Canonical category key.

    Raises
    ------
    ValueError
        When *raw* does not map to any known category or alias.
    """
    key = raw.strip().lower()
    if key in INTERFACE_CATEGORIES:
        return key
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    raise ValueError(
        f"Unrecognized interface category '{raw}'. "
        f"Expected one of: {list(INTERFACE_CATEGORIES)} or a known alias."
    )


def get_category_info(category: str) -> dict:
    """
    Return the info dict for *category*.

    Parameters
    ----------
    category : str
        Canonical category key (case-insensitive) or alias.

    Returns
    -------
    dict
        Copy of the category entry (code, description, examples).

    Raises
    ------
    ValueError
        When *category* is not recognized.
    """
    canon = normalize_category(category)
    return dict(INTERFACE_CATEGORIES[canon])


def generate_identifier(side_a: str, side_b: str, category: str, seq: int) -> str:
    """
    Generate a unique interface identifier.

    Format: ``{SIDE_A}-{SIDE_B}-{CAT_CODE}-{SEQ:03d}``

    Parameters
    ----------
    side_a : str
        Name of the first (owning/primary) entity.
    side_b : str
        Name of the second entity.
    category : str
        Interface category key or alias.
    seq : int
        Sequence number (>= 1) within this entity-pair / category group.

    Returns
    -------
    str
        Formatted identifier, e.g. ``SC-AOCS-ELC-001``.

    Raises
    ------
    ValueError
        When *side_a* or *side_b* is empty, *category* is unrecognized,
        or *seq* is less than 1.
    """
    if not side_a or not side_a.strip():
        raise ValueError("side_a must be a non-empty string.")
    if not side_b or not side_b.strip():
        raise ValueError("side_b must be a non-empty string.")
    if seq < 1:
        raise ValueError(f"seq must be >= 1, got {seq}.")
    canon = normalize_category(category)
    code = INTERFACE_CATEGORIES[canon]["code"]
    a = side_a.strip().upper()
    b = side_b.strip().upper()
    return f"{a}-{b}-{code}-{seq:03d}"


def build_interface_record(
    side_a: str,
    side_b: str,
    category: str,
    seq: int,
    description: str = "",
) -> dict:
    """
    Build and return a complete interface record.

    Parameters
    ----------
    side_a : str
        Primary owning entity name.
    side_b : str
        Second entity name.
    category : str
        Interface category key or alias.
    seq : int
        Sequence number within the entity-pair / category group (>= 1).
    description : str, optional
        Human-readable description of what crosses this boundary.

    Returns
    -------
    dict with keys:
        identifier   : generated unique identifier string
        side_a       : normalized upper-case entity name
        side_b       : normalized upper-case entity name
        category     : canonical category key
        category_code: two-to-three-character category code
        seq          : sequence number (int)
        description  : description string (may be empty)
        complete     : bool — True when identifier, both sides, and category
                       are all non-empty

    Raises
    ------
    ValueError
        When any mandatory input is invalid (delegated to generate_identifier
        and normalize_category).
    """
    if side_a.strip().upper() == side_b.strip().upper():
        raise ValueError(
            f"Self-interface detected: side_a and side_b are both "
            f"'{side_a.strip().upper()}'. An interface must connect two "
            f"distinct entities."
        )
    canon = normalize_category(category)
    ident = generate_identifier(side_a, side_b, canon, seq)
    record = {
        "identifier": ident,
        "side_a": side_a.strip().upper(),
        "side_b": side_b.strip().upper(),
        "category": canon,
        "category_code": INTERFACE_CATEGORIES[canon]["code"],
        "seq": seq,
        "description": description,
        "complete": bool(ident and side_a.strip() and side_b.strip() and canon),
    }
    return record


def check_identifier_unique(interfaces: list) -> list:
    """
    Return a list of identifiers that appear more than once in *interfaces*.

    Parameters
    ----------
    interfaces : list of dict
        Interface records as returned by build_interface_record.

    Returns
    -------
    list of str
        Duplicate identifier strings (empty list when all are unique).
    """
    seen = {}
    for rec in interfaces:
        ident = rec.get("identifier", "")
        seen[ident] = seen.get(ident, 0) + 1
    return [ident for ident, count in seen.items() if count > 1]


def validate_interface_list(interfaces: list) -> dict:
    """
    Validate a list of interface records and return a result dict.

    Checks performed:
    - No self-interfaces (side_a == side_b).
    - All category values are recognized.
    - All identifiers are unique.
    - All mandatory fields (identifier, side_a, side_b, category) are non-empty.
    - Sequence numbers are >= 1.

    Parameters
    ----------
    interfaces : list of dict
        Interface records (from build_interface_record or equivalent).

    Returns
    -------
    dict with keys:
        valid  : bool — True when no issues found
        issues : list of str — human-readable problem descriptions
    """
    issues = []

    for i, rec in enumerate(interfaces):
        ident = rec.get("identifier", "")
        side_a = rec.get("side_a", "")
        side_b = rec.get("side_b", "")
        category = rec.get("category", "")
        seq = rec.get("seq", 0)
        label = ident if ident else f"record[{i}]"

        if not ident:
            issues.append(f"{label}: missing identifier.")
        if not side_a:
            issues.append(f"{label}: side_a is empty.")
        if not side_b:
            issues.append(f"{label}: side_b is empty.")
        if side_a and side_b and side_a.upper() == side_b.upper():
            issues.append(
                f"{label}: self-interface — side_a and side_b are both '{side_a}'."
            )
        if not category:
            issues.append(f"{label}: category is empty.")
        else:
            try:
                normalize_category(category)
            except ValueError:
                issues.append(
                    f"{label}: category '{category}' is not in the §5.2 taxonomy."
                )
        if not isinstance(seq, int) or seq < 1:
            issues.append(f"{label}: seq must be an integer >= 1, got '{seq}'.")

    duplicates = check_identifier_unique(interfaces)
    for dup in duplicates:
        issues.append(f"Duplicate identifier '{dup}' found in the interface list.")

    return {"valid": len(issues) == 0, "issues": issues}


def build_interface_tree(interfaces: list) -> dict:
    """
    Build an interface tree grouped by the primary owning entity (side_a).

    Parameters
    ----------
    interfaces : list of dict
        Interface records.

    Returns
    -------
    dict
        Keys are side_a entity names; values are lists of interface records
        belonging to that entity.  Records are included as-is (shallow copy
        of each dict).
    """
    tree = {}
    for rec in interfaces:
        owner = rec.get("side_a", "UNKNOWN")
        if owner not in tree:
            tree[owner] = []
        tree[owner].append(dict(rec))
    return tree
