"""Part approval document data item: required content and per-part sheet fields.

Anchor: ECSS-Q-ST-60C Annex D (part approval document DRD). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the document-level content blocks, weighted by how much of the
   approval rests on each, so a missing approval summary is not scored the
   same as a missing scope paragraph.
2. Select the parts the deliverable actually owes a sheet for. A part outside
   the flight EEE set owes nothing here and must not be counted either as
   covered or as a shortfall.
3. Grade every sheet on the fields a reader needs to act on the decision it
   carries: what the part is, what it was bought against, what evidence was
   evaluated, who decided, and when.
4. Separate a decision that approves from one that approves subject to stated
   limitations, from one that refuses, from one that has been deferred. Each
   sends a different correction, and a single approved-or-not column loses
   three of the four.
5. Insist an approval granted with limitations records those limitations. An
   approval whose limitations are blank is a full approval in practice.
6. Treat a second sheet for a part already carrying a decision as a duplicate
   sheet, not as a second part.
7. Weight the approved share by how many of each part type the build installs,
   compare it with the required level, and return one submission verdict with
   ranked findings.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "DECISION_VALUES",
    "DOCUMENT_BLOCKS",
    "OBLIGED_CATEGORY",
    "SHEET_FIELDS",
    "validate_part_type",
    "document_block_coverage",
    "decision_facts",
    "sheet_completeness",
    "obliged_parts",
    "evaluate_sheet",
    "approved_installation_fraction",
    "assess_part_approval_document_drd",
]

# The approved share is a ratio of summed installation counts. An exactly-met
# requirement can land a few ULPs low; absorb the representation error here
# rather than lowering the level the project agreed.
COVERAGE_TOLERANCE = 1e-9

# Document-level content block -> weight. The weights say how much of the
# approval rests on the block, which is why coverage is not a heading count.
DOCUMENT_BLOCKS = {
    "identification": 2,
    "scope-and-applicability": 1,
    "approval-summary": 3,
    "part-sheets": 3,
    "limitations-and-conditions": 2,
    "signature-and-date": 2,
}

# Fields one part sheet cannot carry an actionable decision without.
SHEET_FIELDS = (
    "sheet_id",
    "part_type",
    "manufacturer",
    "part_number",
    "procurement_reference",
    "evaluation_evidence",
    "decision",
    "decision_authority",
    "decision_date",
)

# Decision -> whether it is settled, and whether it lets the part stay on the
# build. Deferred is not settled; a refusal is settled and removes the part.
DECISION_VALUES = {
    "approved": {"settled": True, "permits_use": True},
    "approved-with-limitations": {"settled": True, "permits_use": True},
    "not-approved": {"settled": True, "permits_use": False},
    "deferred": {"settled": False, "permits_use": False},
}

# The decision that is meaningless without recorded limitations.
_LIMITED_DECISION = "approved-with-limitations"

# The part category this deliverable raises a sheet obligation for.
OBLIGED_CATEGORY = "eee-flight"

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "document-block-absent": 0,
    "sheet-incomplete": 0,
    "unknown-part-type": 1,
    "unknown-decision": 2,
    "duplicate-sheet": 3,
    "limitation-not-recorded": 4,
    "decision-deferred": 5,
    "part-not-approved": 6,
    "sheet-absent": 7,
    "outside-obligation": 8,
    "accepted": 9,
}

_ACCEPTED = "accepted"


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def validate_part_type(value):
    """Return the validated designation of one part type."""
    return _require_text(value, "part_type")


def document_block_coverage(blocks):
    """Return (absent_blocks, weighted_coverage) for the document content."""
    if not isinstance(blocks, dict):
        raise ValueError("blocks must be a mapping of block name -> content")
    absent = []
    present_weight = 0
    total_weight = 0
    for name, weight in DOCUMENT_BLOCKS.items():
        total_weight += weight
        body = blocks.get(name)
        if body is None or (isinstance(body, str) and not body.strip()):
            absent.append(name)
            continue
        if not isinstance(body, str):
            raise ValueError("block %s must hold text, got %r" % (name, body))
        present_weight += weight
    if total_weight <= 0:
        raise ValueError("the document block table carries no weight")
    return (tuple(sorted(absent)), present_weight / total_weight)


def decision_facts(decision):
    """Return whether a decision is settled and whether it permits use."""
    name = _require_text(decision, "decision").lower()
    if name not in DECISION_VALUES:
        raise ValueError(
            "unknown decision %r; known: %s"
            % (decision, ", ".join(sorted(DECISION_VALUES)))
        )
    facts = dict(DECISION_VALUES[name])
    facts["decision"] = name
    return facts


def sheet_completeness(sheet):
    """Return (missing_fields, completeness_fraction) for one part sheet."""
    if not isinstance(sheet, dict):
        raise ValueError(
            "each sheet must be a mapping, got %r" % (type(sheet).__name__,)
        )
    missing = []
    for field in SHEET_FIELDS:
        if field not in sheet:
            missing.append(field)
            continue
        value = sheet[field]
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    total = len(SHEET_FIELDS)
    return (tuple(missing), (total - len(missing)) / total)


def obliged_parts(parts):
    """Return the part types this deliverable owes an approval sheet for."""
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("parts must be a non-empty sequence of part mappings")
    obliged = []
    seen = set()
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError("each part must be a mapping")
        part_type = validate_part_type(part.get("part_type")).lower()
        if part_type in seen:
            raise ValueError("part type %s appears twice in the build" % part_type)
        seen.add(part_type)
        category = _require_text(part.get("approval_category"), "approval_category").lower()
        _require_positive_int(part.get("installed_count"), "installed_count")
        if category == OBLIGED_CATEGORY:
            obliged.append(part_type)
    if not obliged:
        raise ValueError("the build carries no %s part type" % OBLIGED_CATEGORY)
    return tuple(obliged)


def evaluate_sheet(sheet, part_index, already_decided=()):
    """Return the disposition record of one part approval sheet."""
    if not isinstance(part_index, dict) or not part_index:
        raise ValueError("part_index must be a non-empty mapping of part_type -> part")
    missing, completeness = sheet_completeness(sheet)
    raw_label = sheet.get("sheet_id")
    label = (
        raw_label.strip()
        if isinstance(raw_label, str) and raw_label.strip()
        else "<unnumbered>"
    )
    record = {
        "sheet_id": label,
        "part_type": None,
        "missing_fields": missing,
        "completeness": completeness,
        "decision": None,
        "settled": False,
        "permits_use": False,
        "installed_count": 0,
        "disposition": "sheet-incomplete",
        "accepted": False,
    }
    if missing:
        return record

    part_type = validate_part_type(sheet["part_type"]).lower()
    record["part_type"] = part_type
    if part_type not in part_index:
        record["disposition"] = "unknown-part-type"
        return record

    part = part_index[part_type]
    category = _require_text(part.get("approval_category"), "approval_category").lower()
    installed = _require_positive_int(part.get("installed_count"), "installed_count")
    record["installed_count"] = installed

    if category != OBLIGED_CATEGORY:
        record["disposition"] = "outside-obligation"
        return record

    try:
        facts = decision_facts(sheet["decision"])
    except ValueError:
        record["disposition"] = "unknown-decision"
        return record
    record["decision"] = facts["decision"]
    record["settled"] = facts["settled"]
    record["permits_use"] = facts["permits_use"]

    if part_type in already_decided:
        record["disposition"] = "duplicate-sheet"
        return record

    if facts["decision"] == _LIMITED_DECISION:
        limitations = sheet.get("limitations")
        if not isinstance(limitations, str) or not limitations.strip():
            record["disposition"] = "limitation-not-recorded"
            return record

    if not facts["settled"]:
        record["disposition"] = "decision-deferred"
        return record
    if not facts["permits_use"]:
        record["disposition"] = "part-not-approved"
        return record

    record["disposition"] = _ACCEPTED
    record["accepted"] = True
    return record


def approved_installation_fraction(records, part_index, obliged):
    """Return the obliged installation count sitting behind an approved sheet."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of sheet records")
    if not isinstance(obliged, (list, tuple)) or not obliged:
        raise ValueError("obliged must be a non-empty sequence of part types")
    total = 0
    for part_type in obliged:
        total += _require_positive_int(
            part_index[part_type].get("installed_count"), "installed_count"
        )
    covered = 0
    approved_types = set()
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        if record["disposition"] != _ACCEPTED:
            continue
        part_type = record.get("part_type")
        if part_type in approved_types or part_type not in obliged:
            continue
        approved_types.add(part_type)
        covered += part_index[part_type]["installed_count"]
    if total <= 0:
        raise ValueError("no obliged part type carries a usable installation count")
    return covered / total


def assess_part_approval_document_drd(spec):
    """Run the full Annex D part approval document data item assessment.

    spec keys: blocks (mapping of document block -> text), parts (sequence of
    part mappings), sheets (sequence of sheet mappings), optional
    required_approved_fraction (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("blocks", "parts", "sheets"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    parts = spec["parts"]
    obliged = obliged_parts(parts)
    part_index = {
        validate_part_type(part["part_type"]).lower(): part for part in parts
    }

    sheets = spec["sheets"]
    if not isinstance(sheets, (list, tuple)):
        raise ValueError("spec['sheets'] must be a sequence")

    required = spec.get("required_approved_fraction", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_approved_fraction must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_approved_fraction must lie in [0, 1], got %r"
            % (spec["required_approved_fraction"],)
        )

    absent_blocks, block_coverage = document_block_coverage(spec["blocks"])

    records = []
    decided_types = set()
    for sheet in sheets:
        record = evaluate_sheet(sheet, part_index, already_decided=decided_types)
        # Only an accepted sheet closes a part type. A corrected resubmission
        # after a refusal is the fix, not a duplicate.
        if record["disposition"] == _ACCEPTED and record["part_type"] is not None:
            decided_types.add(record["part_type"])
        records.append(record)

    addressed = {r["part_type"] for r in records if r["part_type"] is not None}
    without_sheet = tuple(
        sorted(part_type for part_type in obliged if part_type not in addressed)
    )

    approved = approved_installation_fraction(records, part_index, obliged)

    findings = [
        {
            "severity": _SEVERITY["document-block-absent"],
            "reference": name,
            "disposition": "document-block-absent",
            "detail": "the deliverable carries no content for this required block",
        }
        for name in absent_blocks
    ]
    for record in records:
        disposition = record["disposition"]
        if disposition in (_ACCEPTED, "outside-obligation"):
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(disposition, 8),
                "reference": record["sheet_id"],
                "disposition": disposition,
                "detail": _finding_detail(record),
            }
        )
    for part_type in without_sheet:
        findings.append(
            {
                "severity": _SEVERITY["sheet-absent"],
                "reference": part_type,
                "disposition": "sheet-absent",
                "detail": "no approval sheet was raised for this part type",
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    meets = approved > required or math.isclose(
        approved, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    submittable = meets and not findings
    return {
        "obliged_parts": obliged,
        "records": records,
        "document_block_coverage": block_coverage,
        "absent_document_blocks": absent_blocks,
        "parts_without_a_sheet": without_sheet,
        "approved_installation_fraction": approved,
        "required_approved_fraction": required,
        "findings": findings,
        "submittable": submittable,
        "verdict": "submit" if submittable else "hold",
    }


def _finding_detail(record):
    """Return the human-readable reason one sheet blocks the submission."""
    disposition = record["disposition"]
    if disposition == "sheet-incomplete":
        return "sheet lacks %s; the decision on it cannot be acted on" % ", ".join(
            record["missing_fields"]
        )
    if disposition == "unknown-part-type":
        return "the sheet names a part type that is not in the build"
    if disposition == "unknown-decision":
        return "the sheet carries a decision the data item does not define"
    if disposition == "duplicate-sheet":
        return "a second sheet was raised for a part type already approved"
    if disposition == "limitation-not-recorded":
        return "an approval with limitations was granted without recording them"
    if disposition == "decision-deferred":
        return "the decision on this part type has been deferred, not taken"
    if disposition == "part-not-approved":
        return "the part type was refused and cannot stay on the build as sheeted"
    return "the sheet is outside the obligation this deliverable raises"
