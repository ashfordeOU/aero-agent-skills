"""
e1009_documentation_logic.py

CSD maintenance logic for ECSS-E-ST-10C §5.2.2.

Validates coordinate system entries, enforces lifecycle state transitions,
checks identifier uniqueness and phase coverage, and computes a readiness score
for the Coordinate Systems Document (CSD).
"""

REQUIRED_CS_ENTRY_FIELDS = frozenset({
    "cs_id", "name", "origin", "axes", "reference_frame",
    "applicable_phases", "status",
})

REQUIRED_AXES = frozenset({"x", "y", "z"})

VALID_ENTRY_STATUSES = frozenset({"draft", "review", "approved", "superseded"})

VALID_DOC_STATES = frozenset({"draft", "review", "approved", "superseded"})

VALID_TRANSITIONS = frozenset({
    ("draft", "review"),
    ("review", "approved"),
    ("review", "draft"),
    ("approved", "superseded"),
    ("draft", "superseded"),
})

REQUIRED_DOC_FIELDS = frozenset({"doc_id", "revision", "lifecycle_state", "entries"})


def validate_cs_entry(entry):
    """
    Validate a single coordinate system entry dict.
    Returns a list of issue strings; an empty list means the entry is valid.
    """
    if not isinstance(entry, dict):
        return ["entry must be a dict"]

    issues = []

    missing = REQUIRED_CS_ENTRY_FIELDS - set(entry.keys())
    for field in sorted(missing):
        issues.append(f"missing required field: {field}")

    if "cs_id" in entry:
        cs_id = entry["cs_id"]
        if not isinstance(cs_id, str) or not cs_id.strip():
            issues.append("cs_id must be a non-empty string")

    if "axes" in entry:
        issues.extend(check_axis_completeness(entry["axes"]))

    if "status" in entry and entry["status"] not in VALID_ENTRY_STATUSES:
        issues.append(
            f"invalid status '{entry['status']}'; "
            f"must be one of {sorted(VALID_ENTRY_STATUSES)}"
        )

    if "applicable_phases" in entry:
        phases = entry["applicable_phases"]
        if not isinstance(phases, list) or len(phases) == 0:
            issues.append("applicable_phases must be a non-empty list")

    return issues


def check_axis_completeness(axes):
    """
    Verify that axes contains non-empty string definitions for x, y, and z.
    Returns a list of issue strings; empty means axes are complete.
    """
    if not isinstance(axes, dict):
        return ["axes must be a dict"]

    issues = []

    missing = REQUIRED_AXES - set(axes.keys())
    for ax in sorted(missing):
        issues.append(f"missing axis definition: {ax}")

    for ax in sorted(REQUIRED_AXES):
        if ax in axes:
            defn = axes[ax]
            if not isinstance(defn, str) or not defn.strip():
                issues.append(f"axis '{ax}' must have a non-empty string definition")

    return issues


def check_cs_id_uniqueness(entries):
    """
    Return a list of cs_id values that appear more than once across entries.
    Duplicate identifiers are a documentation non-conformance.
    """
    seen = {}
    for entry in entries:
        cs_id = entry.get("cs_id")
        if cs_id is not None:
            seen[cs_id] = seen.get(cs_id, 0) + 1
    return [cs_id for cs_id, count in sorted(seen.items()) if count > 1]


def check_lifecycle_transition(from_state, to_state):
    """
    Return True if the transition from_state -> to_state is permitted.
    Raises ValueError if either state is not a recognized document state.
    """
    if from_state not in VALID_DOC_STATES:
        raise ValueError(f"unrecognized state: {from_state!r}")
    if to_state not in VALID_DOC_STATES:
        raise ValueError(f"unrecognized state: {to_state!r}")
    return (from_state, to_state) in VALID_TRANSITIONS


def check_phase_coverage(entries, required_phases):
    """
    Return the set of phases from required_phases that no entry covers.
    An entry covers a phase when the phase appears in its applicable_phases list.
    """
    covered = set()
    for entry in entries:
        phases = entry.get("applicable_phases", [])
        if isinstance(phases, list):
            covered.update(phases)
    return set(required_phases) - covered


def validate_csd(csd_doc):
    """
    Validate a full CSD document dict.

    Returns:
        dict with keys:
            valid        bool   True only when doc_issues and entry_issues are both empty.
            doc_issues   list   Document-level finding strings.
            entry_issues dict   {cs_id: [issue strings]} for each invalid entry.
            duplicate_ids list  cs_id values that appear more than once.
    """
    if not isinstance(csd_doc, dict):
        return {
            "valid": False,
            "doc_issues": ["csd_doc must be a dict"],
            "entry_issues": {},
            "duplicate_ids": [],
        }

    doc_issues = []
    entry_issues = {}
    duplicate_ids = []

    missing_doc = REQUIRED_DOC_FIELDS - set(csd_doc.keys())
    for field in sorted(missing_doc):
        doc_issues.append(f"missing required doc field: {field}")

    if "lifecycle_state" in csd_doc:
        state = csd_doc["lifecycle_state"]
        if state not in VALID_DOC_STATES:
            doc_issues.append(
                f"invalid lifecycle_state '{state}'; "
                f"must be one of {sorted(VALID_DOC_STATES)}"
            )

    if "entries" in csd_doc:
        entries = csd_doc["entries"]
        if not isinstance(entries, list):
            doc_issues.append("entries must be a list")
        else:
            duplicate_ids = check_cs_id_uniqueness(entries)
            if duplicate_ids:
                doc_issues.append(f"duplicate cs_id values: {duplicate_ids}")
            for entry in entries:
                cs_id = entry.get("cs_id", "<unknown>") if isinstance(entry, dict) else "<unknown>"
                issues = validate_cs_entry(entry)
                if issues:
                    entry_issues[cs_id] = issues

    valid = not doc_issues and not entry_issues
    return {
        "valid": valid,
        "doc_issues": doc_issues,
        "entry_issues": entry_issues,
        "duplicate_ids": duplicate_ids,
    }


def compute_csd_readiness_score(csd_doc):
    """
    Compute a readiness score 0-100 for a CSD document dict.

    Score components:
      - Document field completeness  30 pts  (fraction of required doc fields present)
      - Lifecycle state maturity     20 pts  (draft=5, review=10, approved=20, superseded=15)
      - Entry quality                50 pts  (fraction of entries that individually pass validation)

    Returns int 0-100.
    """
    if not isinstance(csd_doc, dict):
        return 0

    present = set(csd_doc.keys()) & REQUIRED_DOC_FIELDS
    doc_score = int(30 * len(present) / len(REQUIRED_DOC_FIELDS))

    state_maturity = {"draft": 5, "review": 10, "approved": 20, "superseded": 15}
    state_score = state_maturity.get(csd_doc.get("lifecycle_state", ""), 0)

    entries = csd_doc.get("entries", [])
    if isinstance(entries, list) and len(entries) > 0:
        valid_count = sum(1 for e in entries if not validate_cs_entry(e))
        entry_score = int(50 * valid_count / len(entries))
    else:
        entry_score = 0

    return min(doc_score + state_score + entry_score, 100)
