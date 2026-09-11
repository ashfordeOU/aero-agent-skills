"""
CSD responsibility-assignment logic for ECSS-E-ST-10C §5.2.1.

Every entry in a Coordinate System Document (CSD) must carry exactly one
identified owner. This module validates ownership completeness and produces
a structured compliance report.

No third-party dependencies — stdlib only.
"""

VALID_ENTRY_TYPES = frozenset({"coordinate_system", "transformation"})


class CSDEntryError(ValueError):
    """Raised when a CSD entry fails structural validation."""


def validate_csd_entry(entry):
    """
    Validate the structure of a single CSD entry dict.

    Required keys: name (non-empty str), entry_type (str in VALID_ENTRY_TYPES),
    owner (str or None).

    Raises CSDEntryError on any structural violation.
    Returns the entry unchanged on success.
    """
    if not isinstance(entry, dict):
        raise CSDEntryError(
            f"CSD entry must be a dict, got {type(entry).__name__!r}"
        )

    for required_key in ("name", "entry_type", "owner"):
        if required_key not in entry:
            raise CSDEntryError(
                f"CSD entry missing required key: {required_key!r}"
            )

    name = entry["name"]
    if not isinstance(name, str) or not name.strip():
        raise CSDEntryError(
            f"CSD entry 'name' must be a non-empty string, got {name!r}"
        )

    entry_type = entry["entry_type"]
    if entry_type not in VALID_ENTRY_TYPES:
        raise CSDEntryError(
            f"CSD entry 'entry_type' must be one of {sorted(VALID_ENTRY_TYPES)}, "
            f"got {entry_type!r}"
        )

    owner = entry["owner"]
    if owner is not None and not isinstance(owner, str):
        raise CSDEntryError(
            f"CSD entry 'owner' must be a str or None, got {type(owner).__name__!r}"
        )

    return entry


def is_owner_assigned(entry):
    """Return True if the entry has a non-empty, non-whitespace owner string."""
    owner = entry.get("owner")
    return isinstance(owner, str) and bool(owner.strip())


def check_responsibility(entries):
    """
    Check that every CSD entry has exactly one assigned owner.

    Scans for two failure modes:
      1. Duplicate entry names — structural conflict preventing unambiguous ownership.
      2. Unassigned owner — owner field is None, empty, or whitespace-only.

    Parameters
    ----------
    entries : list[dict]
        List of CSD entry dicts. Each is validated before inspection.

    Returns
    -------
    issues : list[dict]
        Each issue dict has keys 'entry_name' (str) and 'issue' (str).
        An empty list means the CSD is ownership-compliant.
    """
    issues = []
    seen_names = {}

    for idx, entry in enumerate(entries):
        try:
            validate_csd_entry(entry)
        except CSDEntryError as exc:
            issues.append({
                "entry_name": entry.get("name", f"<entry[{idx}]>"),
                "issue": f"structural validation failure: {exc}",
            })
            continue

        name = entry["name"]

        if name in seen_names:
            issues.append({
                "entry_name": name,
                "issue": (
                    "duplicate name — each CSD entry must have a unique "
                    "identifier; resolve the conflict before verifying ownership"
                ),
            })
            continue
        seen_names[name] = True

        if not is_owner_assigned(entry):
            issues.append({
                "entry_name": name,
                "issue": (
                    "no owner assigned — entry is unassigned and cannot be "
                    "included in a baselined CSD"
                ),
            })

    return issues


def find_unassigned_entries(entries):
    """Return a new list containing only entries that have no owner assigned."""
    return [e for e in entries if not is_owner_assigned(e)]


def find_entries_by_owner(entries, owner):
    """
    Return a new list of all entries whose owner matches the given string.

    Comparison is strip-normalised (leading/trailing whitespace ignored).

    Raises ValueError if owner is not a non-empty string.
    """
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("owner must be a non-empty string")
    target = owner.strip()
    return [e for e in entries if isinstance(e.get("owner"), str) and e["owner"].strip() == target]


def assign_owner(entry, owner):
    """
    Return a new entry dict with the owner field set to owner.

    Does NOT mutate the original entry (immutable update).
    Validates the resulting entry before returning.

    Raises CSDEntryError if the resulting entry is structurally invalid.
    """
    if not isinstance(owner, str) or not owner.strip():
        raise CSDEntryError("owner must be a non-empty string")
    updated = {**entry, "owner": owner}
    validate_csd_entry(updated)
    return updated


def generate_responsibility_report(entries):
    """
    Produce a summary dict describing the responsibility state of a CSD.

    Returns
    -------
    dict with keys:
        total      : int  — total number of entries
        assigned   : int  — entries with a valid owner
        unassigned : int  — entries without a valid owner
        issues     : list[dict]  — from check_responsibility
        compliant  : bool — True only when issues is empty
        owners     : dict[str, list[str]]  — maps owner → list of entry names
    """
    issues = check_responsibility(entries)

    assigned_entries = [e for e in entries if is_owner_assigned(e)]
    unassigned_entries = find_unassigned_entries(entries)

    owners = {}
    for e in assigned_entries:
        owner_key = e["owner"].strip()
        owners.setdefault(owner_key, []).append(e["name"])

    return {
        "total": len(entries),
        "assigned": len(assigned_entries),
        "unassigned": len(unassigned_entries),
        "issues": issues,
        "compliant": len(issues) == 0,
        "owners": owners,
    }
