"""Means of compliance (MOC) selection for certification items.

Pure stdlib, deterministic. For each certification item (an applicable
regulation paragraph in an airworthiness certification program) this
module recommends the acceptable means of compliance from the
six-class MOC scheme (MOC 1 engineering/analysis, MOC 2 ground test,
MOC 3 flight test, MOC 4 simulation/analysis tool, MOC 5 certification
by similarity, MOC 6 safety assessment), gates the assigned set for
catastrophic failure severity and novelty, builds the per-item
compliance matrix, scores matrix coverage per item kind, and returns a
certification plan readiness verdict.

The suitability table below is a deterministic summary derived from
public certification guidance (EASA/FAA style MOC categories and
DO-178C / DO-254 / DO-160 style evidence expectations); it is a
routing summary at reference level, not verbatim regulatory text.

Scope: per-certification-item MOC assignment and coverage. It does NOT
determine the certification basis (see certification-basis leaf), the
program-level airworthiness sequencing, or ARP4754A verification
method assignment.
"""

ITEM_KINDS = (
    "structure",
    "systems",
    "powerplant",
    "equipment",
    "software",
    "hardware",
    "performance",
    "handling",
)

SEVERITIES = ("none", "minor", "major", "hazardous", "catastrophic", "n/a")

DALS = ("A", "B", "C", "D", "E", "n/a")

MOC_NAMES = {
    1: "engineering/analysis",
    2: "ground test",
    3: "flight test",
    4: "simulation/analysis tool",
    5: "certification by similarity",
    6: "safety assessment",
}

MOC_IDS = tuple(sorted(MOC_NAMES))

# Deterministic MOC suitability summary per item kind, derived from
# public certification guidance at reference level (never verbatim).
# "systems" and "structure" carry rule-based handling for severity,
# development assurance level (DAL) and novelty.
# Ordered primary-first. "n/a" marks inputs not applicable to the kind.
# MOC 5 (similarity) is never auto-recommended: guidance limits it to
# minor changes, which this item model cannot confirm; accept_item
# rejects MOC 5 for any novel item.
_STRUCTURE_MOCS = {False: [1, 2], True: [1, 2, 3]}

# Static rule tables for the fixed kinds (novelty has no extra effect
# on kinds that never rely on similarity or test-evidence upgrades).
_FIXED_KIND_MOCS = {
    "powerplant": [2, 3, 1],
    "equipment": [2, 1],
    "software": [1, 4],
    "hardware": [1, 2],
    "performance": [3, 1, 4],
    "handling": [3, 1, 4],
}


def _validate_inputs(item_kind, severity, dal):
    """Raise ValueError for unknown item_kind, severity or DAL strings."""
    if item_kind not in ITEM_KINDS:
        raise ValueError(
            "unknown item_kind %r; expected one of %s"
            % (item_kind, ", ".join(ITEM_KINDS))
        )
    if severity not in SEVERITIES:
        raise ValueError(
            "unknown severity %r; expected one of %s"
            % (severity, ", ".join(SEVERITIES))
        )
    if dal not in DALS:
        raise ValueError(
            "unknown development_assurance_level %r; expected one of %s"
            % (dal, ", ".join(DALS))
        )


def _dedupe(seq):
    """Return a copy of seq preserving order and removing duplicates."""
    seen = []
    for entry in seq:
        if entry not in seen:
            seen.append(entry)
    return seen


def _systems_mocs(severity, dal, novel):
    """Recommended MOCs for an electronic systems item.

    Catastrophic and hazardous failure severities carry MOC 1 analysis
    plus MOC 6 safety assessment; DAL C-E items may lean on MOC 4
    simulation; a novel system adds ground test (MOC 2) so a test MOC
    is always present.
    """
    rec = [1]
    if severity in ("catastrophic", "hazardous"):
        rec.append(6)
    elif dal in ("C", "D", "E"):
        rec.append(4)
    if novel:
        rec.append(2)
    return _dedupe(rec)


def moc_suitability(item_kind, severity="n/a", dal="n/a", novel=False):
    """Recommended MOC id list (ordered, primary first) for an item.

    item_kind: one of ITEM_KINDS; severity: one of SEVERITIES;
    dal: one of DALS; novel: bool novelty screen flag.
    Raises ValueError on unknown kind, severity or DAL strings.
    """
    _validate_inputs(item_kind, severity, dal)
    if item_kind == "structure":
        return list(_STRUCTURE_MOCS[bool(novel)])
    if item_kind == "systems":
        return _systems_mocs(severity, dal, bool(novel))
    return list(_FIXED_KIND_MOCS[item_kind])


def _item_fields(item):
    """Validate an item dict and return (kind, severity, dal, novel)."""
    if not isinstance(item, dict):
        raise ValueError("each certification item must be a dict")
    if "item_id" not in item or "item_kind" not in item:
        raise ValueError("each certification item needs item_id and item_kind")
    kind = item["item_kind"]
    severity = item.get("severity", "n/a")
    dal = item.get("dal", "n/a")
    novel = bool(item.get("novel", False))
    _validate_inputs(kind, severity, dal)
    return kind, severity, dal, novel


def accept_item(item, recommended):
    """Gate an assigned MOC set for a certification item.

    Returns (accepted_bool, reason). Rules:
    - A catastrophic systems item must include MOC 6 (safety
      assessment); without it the item is non-compliant.
    - A novel structure or systems item must include a test MOC (2 or
      3) in addition to analysis.
    - MOC 5 (similarity) is rejected for any novel item.
    - An empty assigned set is never accepted.
    """
    if not recommended:
        return False, "no means of compliance assigned to the item"
    kind, severity, dal, novel = _item_fields(item)
    if kind == "systems" and severity == "catastrophic" and 6 not in recommended:
        return (
            False,
            "%s catastrophic systems item requires MOC 6 safety assessment "
            "in the compliance set" % item["item_id"],
        )
    if novel and 5 in recommended:
        return (
            False,
            "MOC 5 certification by similarity is rejected for novel item %s"
            % item["item_id"],
        )
    if novel and kind in ("structure", "systems"):
        if 2 not in recommended and 3 not in recommended:
            return (
                False,
                "novel %s item %s requires a test MOC (2 ground test or 3 "
                "flight test) in addition to analysis" % (kind, item["item_id"]),
            )
    return (
        True,
        "accepted: MOC set %s is suitable for %s item %s"
        % (", ".join(str(m) for m in recommended), kind, item["item_id"]),
    )


def build_compliance_matrix(items):
    """Build the per-item compliance matrix from a list of items.

    Each item dict: item_id, regulation_paragraph, item_kind, severity
    (optional, default n/a), dal (optional, default n/a), novel
    (optional, default False) and optional assigned_mocs overriding the
    recommended set for acceptance gating.

    Returns a dict with "items" (row dicts) and "issues" (list of
    (item_id, reason) tuples for rejected items). Raises ValueError on
    an empty item list or unknown kind/severity/DAL strings.
    """
    if not items:
        raise ValueError("certification item list must not be empty")
    rows = []
    issues = []
    for item in items:
        kind, severity, dal, novel = _item_fields(item)
        recommended = moc_suitability(kind, severity, dal, novel)
        assigned = item.get("assigned_mocs")
        mocs = list(assigned) if assigned is not None else list(recommended)
        accepted, reason = accept_item(item, mocs)
        rows.append(
            {
                "item_id": item["item_id"],
                "regulation_paragraph": item.get("regulation_paragraph", ""),
                "item_kind": kind,
                "severity": severity,
                "dal": dal,
                "novel": novel,
                "recommended_mocs": recommended,
                "mocs": mocs,
                "primary_moc": mocs[0] if mocs else None,
                "accepted": accepted,
                "reason": reason,
            }
        )
        if not accepted:
            issues.append((item["item_id"], reason))
    return {"items": rows, "issues": issues}


def coverage_score(matrix):
    """Score compliance matrix coverage.

    Overall coverage = (items with at least one accepted MOC) / (all
    items). Returns (overall, per_kind) where per_kind maps each item
    kind present in the matrix to its own covered/total ratio.
    """
    rows = matrix["items"]
    total = len(rows)
    covered = sum(1 for row in rows if row["accepted"])
    per_kind = {}
    for row in rows:
        kind = row["item_kind"]
        bucket = per_kind.setdefault(kind, [0, 0])
        bucket[1] += 1
        if row["accepted"]:
            bucket[0] += 1
    per_kind_score = {
        kind: (float(bucket[0]) / bucket[1]) for kind, bucket in per_kind.items()
    }
    return float(covered) / total, per_kind_score


def compliance_verdict(matrix):
    """Certification plan readiness verdict for the matrix.

    Returns (PASS/FAIL, reasons list). PASS requires overall coverage
    1.0 and every catastrophic systems item carrying MOC 6 in its
    compliance set; each rejection produces an explicit reason.
    """
    reasons = []
    rows = matrix["items"]
    for row in rows:
        if not row["accepted"]:
            reasons.append("%s: %s" % (row["item_id"], row["reason"]))
        if (
            row["item_kind"] == "systems"
            and row["severity"] == "catastrophic"
            and 6 not in row["mocs"]
        ):
            reasons.append(
                "%s: catastrophic systems item requires MOC 6 (safety "
                "assessment) in the compliance set" % row["item_id"]
            )
    overall, _ = coverage_score(matrix)
    if overall < 1.0:
        reasons.append(
            "compliance matrix coverage %.3f below 1.0: every certification "
            "item needs at least one accepted MOC" % overall
        )
    if reasons:
        return "FAIL", reasons
    return "PASS", ["all certification items covered with acceptable MOCs"]


