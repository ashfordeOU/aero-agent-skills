"""Clause-by-clause compliance matrix against ECSS-Q-ST-80C Rev.2.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025). Section 8 of the software
product assurance plan (Annex B) carries a compliance matrix to the
standard, and Annex D fixes which requirements apply to each software
criticality category. This module joins a list of clauses to an evidence
index (clause -> document, section, status, justification) and returns the
matrix rows, a coverage summary and the gaps. Clause identifiers are used with topic labels of
our own wording; no requirement or heading text is reproduced.

The output is ALWAYS a draft. The module never marks a matrix as approved
by itself: only record_sign_off, called with a named human signatory, moves
it out of draft, and it refuses to do so silently over open gaps.

Procedure implemented here
--------------------------
1. Normalise the clause list (ids or dicts, item letters cut, duplicates
   refused) or take the default list for a category.
2. Parse and index the evidence (rows from CSV text or dicts), normalising
   the status vocabulary and keeping several evidence rows per clause.
3. Build one matrix row per clause: the combined status (the weakest of the
   rows), the justification, the evidence references (document and
   section), and the gaps that row raises.
4. Summarise coverage: counts per status, the compliant fraction of the
   applicable clauses, the fraction with an evidence reference.
5. Collect the gaps, including evidence for clauses that are not in the
   list at all.
6. Render the matrix as Markdown or CSV with the draft banner and the stop
   line; record a human sign-off only when a named person gives it.
"""

import csv
import io

__all__ = [
    "CATEGORIES",
    "STATUSES",
    "STATUS_ALIASES",
    "HEADINGS",
    "REQUIREMENT_IDS",
    "APPLICABILITY_EXCEPTIONS",
    "DRAFT_BANNER",
    "STOP_LINE",
    "normalise_category",
    "normalise_clause_id",
    "normalise_status",
    "heading_of",
    "tailored_status",
    "default_clauses",
    "parse_evidence_csv",
    "index_evidence",
    "build_matrix",
    "coverage_summary",
    "find_gaps",
    "render_markdown",
    "render_csv",
    "record_sign_off",
]

CATEGORIES = ("A", "B", "C", "D")

STATUSES = ("compliant", "partially-compliant", "not-compliant", "not-applicable")

STATUS_ALIASES = {
    "c": "compliant", "compliant": "compliant", "yes": "compliant", "y": "compliant",
    "full": "compliant", "fc": "compliant",
    "pc": "partially-compliant", "partial": "partially-compliant",
    "partially": "partially-compliant", "partially compliant": "partially-compliant",
    "partially-compliant": "partially-compliant",
    "nc": "not-compliant", "no": "not-compliant", "n": "not-compliant",
    "not compliant": "not-compliant", "not-compliant": "not-compliant",
    "non-compliant": "not-compliant", "noncompliant": "not-compliant",
    "na": "not-applicable", "n/a": "not-applicable", "not applicable": "not-applicable",
    "not-applicable": "not-applicable",
}

# Worst first: the combined status of several evidence rows is the weakest.
_SEVERITY = {"not-compliant": 0, "partially-compliant": 1, "compliant": 2}

DRAFT_BANNER = ("DRAFT - prepared by an agent for review. Not a statement of "
                "compliance until signed off by the responsible human.")
STOP_LINE = "STOP: human sign-off required before submission."

# Applicability data, derived from the clause structure of the standard.
# Codes per requirement, in category order A B C D: Y applicable, N not
# applicable, R reduced, S set by security sensitivity. Default YYYY.
HEADINGS = {
    '5': 'assurance programme',
    '5.1': 'organisation',
    '5.1.1': 'assurance organisation set-up',
    '5.1.2': 'who answers for what',
    '5.1.3': 'staff and means',
    '5.1.4': 'the assurance lead',
    '5.1.5': 'skills and training',
    '5.2': 'programme management',
    '5.2.1': 'planning and control of the programme',
    '5.2.2': 'assurance reporting',
    '5.2.3': 'audit programme',
    '5.2.4': 'alert handling',
    '5.2.5': 'problem reporting',
    '5.2.6': 'nonconformance handling',
    '5.2.7': 'quality model',
    '5.3': 'risks and critical items',
    '5.3.1': 'risk handling',
    '5.3.2': 'critical items',
    '5.4': 'suppliers',
    '5.4.1': 'choosing suppliers',
    '5.4.2': 'what suppliers are held to',
    '5.4.3': 'watching suppliers',
    '5.4.4': 'category flow-down to suppliers',
    '5.4.5': 'security flow-down to suppliers',
    '5.5': 'buying software',
    '5.5.1': 'purchase documents',
    '5.5.2': 'bought-in component list',
    '5.5.3': 'purchase data',
    '5.5.4': 'marking of bought items',
    '5.5.5': 'incoming checks',
    '5.5.6': 'export constraints',
    '5.6': 'tools and environment',
    '5.6.1': 'methods and tools chosen',
    '5.6.2': 'choice of development environment',
    '5.7': 'process capability',
    '5.7.1': 'capability assessment',
    '5.7.2': 'how assessments are run',
    '5.7.3': 'improving the process',
    '6': 'process assurance',
    '6.1': 'life cycle',
    '6.1.1': 'defining the life cycle',
    '6.1.2': 'process targets',
    '6.1.3': 'reviewing the life cycle',
    '6.1.4': 'means for the life cycle',
    '6.1.5': 'validation timing',
    '6.2': 'cross-process obligations',
    '6.2.1': 'process documentation',
    '6.2.2': 'dependability and safety of software',
    '6.2.3': 'critical software',
    '6.2.4': 'configuration management',
    '6.2.5': 'process measurement',
    '6.2.6': 'verification',
    '6.2.7': 'reusing existing software',
    '6.2.8': 'generated code',
    '6.2.9': 'security',
    '6.2.10': 'security-sensitive software',
    '6.3': 'per-process obligations',
    '6.3.1': 'system-level software requirements',
    '6.3.2': 'requirements analysis',
    '6.3.3': 'architecture and design',
    '6.3.4': 'coding',
    '6.3.5': 'testing and validation',
    '6.3.6': 'delivery and installation',
    '6.3.7': 'acceptance',
    '6.3.8': 'operations',
    '6.3.9': 'maintenance',
    '7': 'product quality assurance',
    '7.1': 'quality targets and measurement',
    '7.1.1': 'deriving quality requirements',
    '7.1.2': 'quality requirements as numbers',
    '7.1.3': 'checking quality requirements',
    '7.1.4': 'product measures',
    '7.1.5': 'basic measures',
    '7.1.6': 'reporting measures',
    '7.1.7': 'numerical accuracy',
    '7.1.8': 'maturity analysis',
    '7.2': 'product quality obligations',
    '7.2.1': 'requirement documents',
    '7.2.2': 'design documents',
    '7.2.3': 'test and validation documents',
    '7.3': 'software built for reuse',
    '7.3.1': 'what the customer asks for',
    '7.3.2': 'own documentation set',
    '7.3.3': 'standalone information',
    '7.3.4': 'reuse requirements',
    '7.3.5': 'configuration of reusable items',
    '7.3.6': 'multi-platform testing',
    '7.3.7': 'conformance certificate',
    '7.4': 'ground hardware and services',
    '7.4.1': 'buying ground hardware',
    '7.4.2': 'buying services',
    '7.4.3': 'limits',
    '7.4.4': 'choice',
    '7.4.5': 'upkeep',
    '7.5': 'programmable devices',
    '7.5.1': 'programming devices',
    '7.5.2': 'device marking',
    '7.5.3': 'device calibration',
}

REQUIREMENT_IDS = (
    '5.1.1', '5.1.2.1', '5.1.2.2', '5.1.2.3', '5.1.3.1', '5.1.3.2', '5.1.4.1', '5.1.4.2',
    '5.1.5.1', '5.1.5.2', '5.1.5.3', '5.1.5.4', '5.2.1.1', '5.2.1.2', '5.2.1.3', '5.2.1.4',
    '5.2.1.5', '5.2.2.1', '5.2.2.2', '5.2.2.3', '5.2.3', '5.2.4', '5.2.5.1', '5.2.5.2',
    '5.2.5.3', '5.2.5.4', '5.2.6.1', '5.2.6.2', '5.2.7.1', '5.2.7.2', '5.3.1', '5.3.2.1',
    '5.3.2.2', '5.4.1.1', '5.4.1.2', '5.4.2.1', '5.4.2.2', '5.4.3.1', '5.4.3.2', '5.4.3.3',
    '5.4.3.4', '5.4.4', '5.4.5', '5.5.1', '5.5.2', '5.5.3', '5.5.4', '5.5.5',
    '5.5.6', '5.6.1.1', '5.6.1.2', '5.6.1.3', '5.6.2.1', '5.6.2.2', '5.6.2.3', '5.7.1',
    '5.7.2.1', '5.7.2.2', '5.7.2.3', '5.7.2.4', '5.7.3.1', '5.7.3.2', '5.7.3.3', '6.1.1',
    '6.1.2', '6.1.3', '6.1.4', '6.1.5', '6.2.1.1', '6.2.1.2', '6.2.1.3', '6.2.1.4',
    '6.2.1.5', '6.2.1.6', '6.2.1.7', '6.2.1.8', '6.2.1.9', '6.2.2.1', '6.2.2.2', '6.2.2.3',
    '6.2.2.4', '6.2.2.5', '6.2.2.6', '6.2.2.7', '6.2.2.8', '6.2.2.9', '6.2.2.10', '6.2.3.2',
    '6.2.3.3', '6.2.3.4', '6.2.3.5', '6.2.3.6', '6.2.3.7', '6.2.3.8', '6.2.4.1', '6.2.4.2',
    '6.2.4.3', '6.2.4.4', '6.2.4.5', '6.2.4.6', '6.2.4.7', '6.2.4.8', '6.2.4.9', '6.2.4.10',
    '6.2.4.11', '6.2.4.12', '6.2.5.1', '6.2.5.2', '6.2.5.3', '6.2.5.4', '6.2.5.5', '6.2.6.1',
    '6.2.6.2', '6.2.6.3', '6.2.6.4', '6.2.6.5', '6.2.6.6', '6.2.6.7', '6.2.6.8', '6.2.6.9',
    '6.2.6.10', '6.2.6.11', '6.2.6.12', '6.2.6.13', '6.2.7.1', '6.2.7.2', '6.2.7.3', '6.2.7.4',
    '6.2.7.5', '6.2.7.6', '6.2.7.7', '6.2.7.8', '6.2.7.9', '6.2.7.10', '6.2.7.11', '6.2.8.1',
    '6.2.8.2', '6.2.8.3', '6.2.8.4', '6.2.8.5', '6.2.8.6', '6.2.8.7', '6.2.9.1', '6.2.9.2',
    '6.2.9.3', '6.2.9.4', '6.2.9.5', '6.2.9.6', '6.2.9.7', '6.2.10.1', '6.2.10.2', '6.2.10.3',
    '6.2.10.4', '6.3.1.1', '6.3.1.2', '6.3.1.3', '6.3.2.1', '6.3.2.2', '6.3.2.3', '6.3.2.4',
    '6.3.2.5', '6.3.3.1', '6.3.3.2', '6.3.3.3', '6.3.3.4', '6.3.3.5', '6.3.3.6', '6.3.3.7',
    '6.3.4.1', '6.3.4.2', '6.3.4.3', '6.3.4.4', '6.3.4.5', '6.3.4.6', '6.3.4.7', '6.3.4.8',
    '6.3.5.1', '6.3.5.2', '6.3.5.3', '6.3.5.4', '6.3.5.5', '6.3.5.6', '6.3.5.7', '6.3.5.8',
    '6.3.5.9', '6.3.5.10', '6.3.5.11', '6.3.5.12', '6.3.5.13', '6.3.5.14', '6.3.5.15', '6.3.5.16',
    '6.3.5.17', '6.3.5.18', '6.3.5.19', '6.3.5.20', '6.3.5.21', '6.3.5.22', '6.3.5.23', '6.3.5.24',
    '6.3.5.25', '6.3.5.26', '6.3.5.27', '6.3.5.28', '6.3.5.29', '6.3.5.30', '6.3.5.31', '6.3.5.32',
    '6.3.5.33', '6.3.6.1', '6.3.6.2', '6.3.6.3', '6.3.6.4', '6.3.7.1', '6.3.7.2', '6.3.7.3',
    '6.3.7.5', '6.3.7.6', '6.3.7.7', '6.3.8.1', '6.3.8.2', '6.3.8.3', '6.3.9.1', '6.3.9.2',
    '6.3.9.3', '6.3.9.4', '6.3.9.5', '6.3.9.6', '6.3.9.7', '7.1.1', '7.1.2', '7.1.3',
    '7.1.4', '7.1.5', '7.1.6', '7.1.7', '7.1.8', '7.2.1.1', '7.2.1.2', '7.2.1.3',
    '7.2.2.1', '7.2.2.2', '7.2.2.3', '7.2.3.1', '7.2.3.2', '7.2.3.3', '7.2.3.4', '7.2.3.5',
    '7.2.3.6', '7.3.1', '7.3.2', '7.3.3', '7.3.4', '7.3.5', '7.3.6', '7.3.7',
    '7.4.1', '7.4.2', '7.4.3', '7.4.4', '7.4.5', '7.5.1', '7.5.2', '7.5.3',
)

APPLICABILITY_EXCEPTIONS = {
    '5.1.3.2': 'YYYN',
    '5.1.5.1': 'YYYR',
    '5.1.5.2': 'YYYN',
    '5.2.3': 'YYYR',
    '5.2.7.2': 'YYYR',
    '5.4.1.1': 'YYYR',
    '5.4.2.2': 'YYYN',
    '5.4.3.4': 'YYYN',
    '5.6.1.1': 'YYYR',
    '5.6.1.2': 'YYYR',
    '5.6.1.3': 'YYYR',
    '5.6.2.1': 'YYYR',
    '5.6.2.2': 'YYYR',
    '5.7.1': 'YYYN',
    '5.7.2.1': 'YYYN',
    '5.7.2.2': 'YYYN',
    '5.7.2.3': 'YYYN',
    '5.7.2.4': 'YYYN',
    '5.7.3.1': 'YYYN',
    '5.7.3.2': 'YYYN',
    '5.7.3.3': 'YYYN',
    '6.2.1.9': 'YYYN',
    '6.2.2.2': 'YYYN',
    '6.2.2.3': 'YYYN',
    '6.2.2.4': 'YYYN',
    '6.2.2.5': 'YYYN',
    '6.2.2.6': 'YYYN',
    '6.2.2.7': 'YYYN',
    '6.2.3.2': 'YYYN',
    '6.2.3.3': 'YYYN',
    '6.2.3.4': 'YYYN',
    '6.2.3.5': 'YYYN',
    '6.2.3.6': 'YYYN',
    '6.2.3.7': 'YYNN',
    '6.2.3.8': 'YYYN',
    '6.2.5.4': 'YYYR',
    '6.2.6.5': 'YYYN',
    '6.2.6.6': 'YYYN',
    '6.2.6.13': 'YYNN',
    '6.2.7.4': 'YYYR',
    '6.2.7.7': 'YYYR',
    '6.2.7.8': 'YYYR',
    '6.2.9.1': 'SSSS',
    '6.2.9.2': 'SSSS',
    '6.2.9.3': 'SSSS',
    '6.2.9.4': 'SSSS',
    '6.2.9.5': 'SSSS',
    '6.2.9.6': 'SSSS',
    '6.2.9.7': 'SSSS',
    '6.2.10.1': 'SSSS',
    '6.2.10.2': 'SSSS',
    '6.2.10.3': 'SSSS',
    '6.2.10.4': 'SSSS',
    '6.3.3.1': 'YYYR',
    '6.3.3.2': 'YYYR',
    '6.3.3.3': 'YYYN',
    '6.3.3.4': 'YYYR',
    '6.3.3.5': 'YYYN',
    '6.3.3.6': 'YYYN',
    '6.3.4.3': 'YYYN',
    '6.3.4.4': 'YYYR',
    '6.3.4.8': 'YYYR',
    '6.3.5.1': 'YYYR',
    '6.3.5.2': 'YYYR',
    '6.3.5.3': 'YYYR',
    '6.3.5.4': 'YYYR',
    '6.3.5.9': 'YYYN',
    '6.3.5.10': 'YYYN',
    '6.3.5.14': 'YYYR',
    '6.3.5.19': 'YYYN',
    '6.3.5.28': 'YYNN',
    '6.3.5.30': 'YYYN',
    '6.3.5.31': 'YYYN',
    '6.3.8.2': 'YYRR',
    '6.3.9.7': 'YYYR',
    '7.1.4': 'YYYR',
    '7.1.5': 'YYYR',
    '7.1.8': 'YYYN',
}


def normalise_category(value):
    """Return the category letter A to D; raise ValueError otherwise."""
    if not isinstance(value, str) or value.strip().upper() not in CATEGORIES:
        raise ValueError("unknown software criticality category %r" % (value,))
    return value.strip().upper()


def normalise_clause_id(value):
    """Return a clause id like '6.2.3.4'; item letters and dots are cut."""
    if not isinstance(value, str):
        raise ValueError("clause id must be a string, got %r" % (value,))
    text = value.strip().rstrip(".")
    for prefix in ("clause", "cl.", "§"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
    while text and text[-1].isalpha():
        text = text[:-1].rstrip(".")
    parts = text.split(".")
    if not text or not all(p.isdigit() for p in parts):
        raise ValueError("not a clause identifier: %r" % (value,))
    return ".".join(str(int(p)) for p in parts)


def normalise_status(value):
    """Map a status spelling to one of STATUSES; raise on anything else."""
    key = str(value or "").strip().lower().replace("_", " ")
    if key in STATUS_ALIASES:
        return STATUS_ALIASES[key]
    key = key.replace(" ", "-")
    if key in STATUS_ALIASES:
        return STATUS_ALIASES[key]
    raise ValueError("unknown compliance status %r" % (value,))


def heading_of(clause):
    """Return the title of the heading a clause sits under, or ''."""
    parts = normalise_clause_id(clause).split(".")
    for depth in range(min(3, len(parts)), 0, -1):
        key = ".".join(parts[:depth])
        if key in HEADINGS:
            return HEADINGS[key]
    return ""


def tailored_status(clause, category, security_sensitive=False):
    """Return 'applicable', 'reduced', 'not-applicable' or 'unknown'.

    'unknown' means the clause is not in the applicability data (a heading,
    or an id from another revision); the matrix then treats it as applicable
    and says so.
    """
    cid = normalise_clause_id(clause)
    if cid not in _REQUIREMENT_SET:
        return "unknown"
    code = APPLICABILITY_EXCEPTIONS.get(cid, "YYYY")[CATEGORIES.index(normalise_category(category))]
    if code == "S":
        return "applicable" if security_sensitive else "not-applicable"
    return {"Y": "applicable", "R": "reduced", "N": "not-applicable"}[code]


def default_clauses(category=None):
    """Return the requirement ids of the standard as clause dicts.

    With a category, each clause carries its tailored status so the matrix
    can pre-fill not-applicable rows; without one, every id is returned.
    """
    out = []
    for rid in REQUIREMENT_IDS:
        row = {"id": rid, "title": heading_of(rid)}
        if category is not None:
            row["tailoring"] = tailored_status(rid, category)
        out.append(row)
    return out


_FIELD_ALIASES = {
    "clause": "clause", "clause_id": "clause", "requirement": "clause", "id": "clause",
    "document": "document", "doc": "document", "evidence": "document",
    "section": "section", "sect": "section", "paragraph": "section",
    "status": "status", "compliance": "status",
    "justification": "justification", "comment": "justification", "rationale": "justification",
}


def parse_evidence_csv(text):
    """Parse evidence rows from CSV text.

    The header must name at least a clause and a status column; document,
    section and justification are optional. Header spellings are matched
    loosely (clause/requirement/id, document/doc/evidence, ...). Blank lines
    are skipped. Returns a list of dicts with the canonical keys.
    """
    reader = csv.DictReader(io.StringIO(str(text)))
    if not reader.fieldnames:
        raise ValueError("evidence CSV has no header")
    mapping = {}
    for name in reader.fieldnames:
        key = _FIELD_ALIASES.get(str(name).strip().lower())
        if key and key not in mapping.values():
            mapping[name] = key
    if "clause" not in mapping.values() or "status" not in mapping.values():
        raise ValueError("evidence CSV needs a clause column and a status column")
    rows = []
    for raw in reader:
        row = {mapping[k]: (v or "").strip() for k, v in raw.items() if k in mapping}
        if not any(row.values()):
            continue
        rows.append(row)
    return rows


def index_evidence(rows):
    """Index evidence rows by clause id.

    rows: iterable of dicts with clause, status and optionally document,
        section, justification. Returns {clause id: [entries]} where each
        entry holds the normalised status and the stripped fields.
    """
    index = {}
    for n, row in enumerate(rows, 1):
        if "clause" not in row:
            raise ValueError("evidence row %d has no clause" % n)
        cid = normalise_clause_id(str(row["clause"]))
        entry = {
            "status": normalise_status(row.get("status")),
            "document": str(row.get("document") or "").strip(),
            "section": str(row.get("section") or "").strip(),
            "justification": str(row.get("justification") or "").strip(),
        }
        index.setdefault(cid, []).append(entry)
    return index


def _clause_list(clauses):
    out = []
    seen = set()
    for item in clauses:
        if isinstance(item, dict):
            cid = normalise_clause_id(str(item.get("id") or item.get("clause") or ""))
            title = str(item.get("title") or "") or heading_of(cid)
        else:
            cid = normalise_clause_id(str(item))
            title = heading_of(cid)
        if cid in seen:
            raise ValueError("clause %s listed twice" % cid)
        seen.add(cid)
        out.append((cid, title))
    return out


def _row(cid, title, entries, category, security_sensitive):
    gaps = []
    tailoring = tailored_status(cid, category, security_sensitive) if category else "unknown"
    refs = []
    for e in entries:
        if e["document"]:
            refs.append(e["document"] + (" " + e["section"] if e["section"] else ""))
    justification = "; ".join(e["justification"] for e in entries if e["justification"])
    if not entries:
        if tailoring == "not-applicable":
            status = "not-applicable"
            justification = "tailored out for software category %s" % category
        else:
            status = "not-compliant"
            gaps.append("no-evidence")
            justification = "no evidence mapped; open until assessed"
        return _pack(cid, title, status, justification, refs, gaps, tailoring)
    stated = [e["status"] for e in entries]
    graded = [s for s in stated if s != "not-applicable"]
    if graded:
        status = min(graded, key=_SEVERITY.get)
        if "not-applicable" in stated:
            gaps.append("conflicting-status")
    else:
        status = "not-applicable"
    if status == "not-applicable":
        if tailoring in ("applicable", "reduced"):
            gaps.append("na-conflicts-with-tailoring")
        if not justification:
            gaps.append("na-without-justification")
    else:
        if not refs:
            gaps.append("no-evidence-reference")
            if status == "compliant":
                status = "partially-compliant"
        elif any(e["document"] and not e["section"] for e in entries):
            gaps.append("reference-without-section")
        if status in ("partially-compliant", "not-compliant") and not justification:
            gaps.append("deviation-without-justification")
        if tailoring == "not-applicable":
            gaps.append("evidence-for-tailored-out-clause")
    return _pack(cid, title, status, justification, refs, gaps, tailoring)


def _pack(cid, title, status, justification, refs, gaps, tailoring):
    return {
        "clause": cid,
        "title": title,
        "status": status,
        "justification": justification,
        "evidence": refs,
        "tailoring": tailoring,
        "gaps": gaps,
    }


def build_matrix(clauses, evidence_index, category=None, security_sensitive=False):
    """Build the compliance matrix. The result is always a DRAFT.

    clauses: list of clause ids or dicts {id, title}. Pass
        default_clauses(category) for the whole standard.
    evidence_index: {clause id: [entries]} from index_evidence, or a list of
        evidence rows (then it is indexed here).
    category: optional software category A to D; with it, rows with no
        evidence for a tailored-out clause are pre-filled not-applicable,
        and contradictions with the tailoring are raised as gaps.

    Returns a dict: status 'DRAFT', requires_human_sign_off True, banner,
    rows, coverage, gaps, orphan_evidence, sign_off (unsigned) and the stop
    line.
    """
    cat = normalise_category(category) if category is not None else None
    if isinstance(evidence_index, dict):
        index = {normalise_clause_id(k): list(v) for k, v in evidence_index.items()}
    else:
        index = index_evidence(evidence_index)
    listed = _clause_list(clauses)
    rows = [_row(cid, title, index.get(cid, []), cat, security_sensitive)
            for cid, title in listed]
    listed_ids = {cid for cid, _ in listed}
    orphans = sorted((cid for cid in index if cid not in listed_ids),
                     key=lambda c: [int(p) for p in c.split(".")])
    matrix = {
        "standard": "ECSS-Q-ST-80C Rev.2 (30 April 2025)",
        "category": cat,
        "status": "DRAFT",
        "requires_human_sign_off": True,
        "banner": DRAFT_BANNER,
        "rows": rows,
        "orphan_evidence": orphans,
        "sign_off": {"signed": False, "signatory": None, "role": None,
                     "date": None, "decision": None, "accepted_gaps": []},
        "stop_line": STOP_LINE,
    }
    matrix["coverage"] = coverage_summary(rows)
    matrix["gaps"] = find_gaps(matrix)
    return matrix


def coverage_summary(rows):
    """Summarise a set of matrix rows.

    Returns counts per status, the number of clauses, the number applicable
    (everything not marked not-applicable), the compliant fraction of the
    applicable clauses, the fraction of applicable clauses carrying an
    evidence reference, and the number of rows with at least one gap.
    """
    counts = {s: 0 for s in STATUSES}
    with_ref = 0
    gapped = 0
    for row in rows:
        counts[row["status"]] += 1
        if row["status"] != "not-applicable" and row["evidence"]:
            with_ref += 1
        if row["gaps"]:
            gapped += 1
    applicable = len(rows) - counts["not-applicable"]
    return {
        "clauses": len(rows),
        "counts": counts,
        "applicable": applicable,
        "compliant_fraction": round(counts["compliant"] / applicable, 4) if applicable else 1.0,
        "evidenced_fraction": round(with_ref / applicable, 4) if applicable else 1.0,
        "rows_with_gaps": gapped,
    }


def find_gaps(matrix):
    """Return the gap list of a matrix: one entry per (clause, gap kind).

    Includes every row gap, every clause not fully compliant, and one entry
    per clause that has evidence but is not in the clause list.
    """
    out = []
    for row in matrix["rows"]:
        for kind in row["gaps"]:
            out.append({"clause": row["clause"], "kind": kind, "status": row["status"]})
        if row["status"] in ("partially-compliant", "not-compliant") and "no-evidence" not in row["gaps"]:
            out.append({"clause": row["clause"], "kind": row["status"], "status": row["status"]})
    for cid in matrix.get("orphan_evidence", []):
        out.append({"clause": cid, "kind": "evidence-for-unlisted-clause", "status": None})
    return out


def _cell(text):
    return str(text).replace("|", "/").replace("\n", " ")


def render_markdown(matrix):
    """Render the matrix as Markdown: banner, table, coverage, gaps, stop line."""
    cov = matrix["coverage"]
    lines = ["> " + matrix["banner"], ""]
    lines.append("Standard: %s. Software category: %s. Status: %s." % (
        matrix["standard"], matrix["category"] or "not stated", matrix["status"]))
    lines.append("")
    lines.append("| Clause | Topic | Status | Justification | Evidence | Gaps |")
    lines.append("|---|---|---|---|---|---|")
    for row in matrix["rows"]:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            row["clause"], _cell(row["title"]), row["status"], _cell(row["justification"]),
            _cell("; ".join(row["evidence"])), _cell(", ".join(row["gaps"]))))
    lines.append("")
    c = cov["counts"]
    lines.append("Coverage: %d clauses, %d applicable; compliant %d, partially %d, "
                 "not compliant %d, not applicable %d; compliant fraction %.4f; "
                 "evidenced fraction %.4f." % (
                     cov["clauses"], cov["applicable"], c["compliant"],
                     c["partially-compliant"], c["not-compliant"], c["not-applicable"],
                     cov["compliant_fraction"], cov["evidenced_fraction"]))
    lines.append("")
    lines.append("Open gaps: %d." % len(matrix["gaps"]))
    so = matrix["sign_off"]
    if so["signed"]:
        lines.append("Signed off by %s (%s) on %s: %s." % (
            so["signatory"], so["role"], so["date"], so["decision"]))
    else:
        lines.append("")
        lines.append(matrix["stop_line"])
    return "\n".join(lines) + "\n"


def render_csv(matrix):
    """Render the matrix rows as CSV text with a DRAFT marker column."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["clause", "topic", "status", "justification", "evidence",
                     "gaps", "matrix_status"])
    for row in matrix["rows"]:
        writer.writerow([row["clause"], row["title"], row["status"], row["justification"],
                         "; ".join(row["evidence"]), ", ".join(row["gaps"]),
                         matrix["status"]])
    return buf.getvalue()


def record_sign_off(matrix, signatory, role, date, decision, accept_open_gaps=False):
    """Record a human sign-off and return a NEW matrix; the input is untouched.

    signatory and role must be non-empty (a named person, not a tool), date
    an ISO date string, decision 'approved' or 'rejected'. Approving a
    matrix with open gaps requires accept_open_gaps=True, and the accepted
    gaps are recorded with the sign-off.
    """
    name = str(signatory or "").strip()
    who = str(role or "").strip()
    if not name or not who:
        raise ValueError("a sign-off needs a named signatory and a role")
    when = str(date or "").strip()
    parts = when.split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts) or len(parts[0]) != 4:
        raise ValueError("date must be an ISO date YYYY-MM-DD, got %r" % (date,))
    dec = str(decision or "").strip().lower()
    if dec not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")
    gaps = list(matrix.get("gaps", []))
    if dec == "approved" and gaps and not accept_open_gaps:
        raise ValueError("%d open gap(s): approve only with accept_open_gaps=True" % len(gaps))
    out = dict(matrix)
    out["rows"] = [dict(r) for r in matrix["rows"]]
    out["sign_off"] = {
        "signed": True, "signatory": name, "role": who, "date": when,
        "decision": dec, "accepted_gaps": gaps if dec == "approved" else [],
    }
    out["status"] = "SIGNED-%s" % dec.upper()
    out["requires_human_sign_off"] = False
    return out


_REQUIREMENT_SET = frozenset(REQUIREMENT_IDS)
