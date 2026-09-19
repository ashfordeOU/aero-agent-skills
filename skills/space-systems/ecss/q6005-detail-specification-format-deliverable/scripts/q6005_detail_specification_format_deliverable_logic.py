"""Hybrid detailed product specification: prescribed layout of the deliverable.

Anchor: ECSS-Q-ST-60-05C Annex B -- the layout a hybrid circuit detailed
product specification is written to, and the entries each numbered clause of
that layout has to hold. Paraphrased into an implementable acceptance
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Parse every delivered heading number into a clause path, refusing a
   malformed, zero-component or duplicated number.
2. Rebuild the clause tree from those paths and report a heading whose parent
   clause was never written, a sibling numbering that skips or repeats, and a
   heading nested deeper than the layout allows.
3. Match the delivered headings onto the template sections, reporting the
   template sections absent from the draft and the headings that belong to no
   template section.
4. Check each mandated entry appears under the clause that owns it, and
   report an entry filed under the wrong clause separately from one that is
   missing altogether.
5. Combine the tree findings, the section coverage and the entry placement
   into a layout conformance ratio and an accept / accept-with-remarks / hold
   verdict.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "MAX_HEADING_DEPTH",
    "TEMPLATE_SECTIONS",
    "MANDATED_ENTRIES",
    "parse_clause_number",
    "format_clause_number",
    "parse_headings",
    "clause_tree_findings",
    "section_coverage",
    "entry_placement",
    "layout_conformance_ratio",
    "assess_detail_specification_format",
]

# A conformance ratio is a quotient of counts, so an exact 1.0 can land a few
# units in the last place low. Absorb that here, not by rounding the ratio.
RATIO_TOLERANCE = 1e-12

# The layout is a two-level clause tree: a numbered top clause and its
# numbered subclauses. A third level is a drafting habit, not the layout.
MAX_HEADING_DEPTH = 2

# Ordered template: clause number -> section key.
TEMPLATE_SECTIONS = (
    ("1", "scope"),
    ("2", "applicable_documents"),
    ("3", "requirements"),
    ("3.1", "requirements_general"),
    ("3.2", "design_and_construction"),
    ("3.3", "electrical_characteristics"),
    ("3.4", "mechanical_and_environmental"),
    ("3.5", "marking"),
    ("4", "quality_assurance"),
    ("4.1", "screening"),
    ("4.2", "lot_acceptance"),
    ("4.3", "qualification"),
    ("5", "delivery"),
    ("5.1", "packaging"),
    ("5.2", "documentation"),
)

# Section key -> entries the layout requires under that clause.
MANDATED_ENTRIES = {
    "scope": ("circuit_designation", "intended_application"),
    "applicable_documents": ("document_list",),
    "requirements": (),
    "requirements_general": ("specification_issue", "reference_drawing"),
    "design_and_construction": (
        "substrate_material",
        "interconnection_method",
        "sealing_method",
    ),
    "electrical_characteristics": ("limit_table", "test_conditions"),
    "mechanical_and_environmental": ("outline_drawing", "temperature_range"),
    "marking": ("marking_content", "marking_location"),
    "quality_assurance": ("quality_programme_reference",),
    "screening": ("screening_sequence",),
    "lot_acceptance": ("lot_acceptance_groups", "sample_sizes"),
    "qualification": ("qualification_reference",),
    "delivery": (),
    "packaging": ("packing_method",),
    "documentation": ("delivery_documents",),
}

_SECTION_OF_NUMBER = {number: key for number, key in TEMPLATE_SECTIONS}
_NUMBER_OF_SECTION = {key: number for number, key in TEMPLATE_SECTIONS}
_OWNER_OF_ENTRY = {
    entry: section
    for section, entries in MANDATED_ENTRIES.items()
    for entry in entries
}


def parse_clause_number(number):
    """Return a dotted heading number as a tuple of positive integers."""
    if not isinstance(number, str):
        raise ValueError("clause number must be a string, got %r" % (number,))
    text = number.strip().rstrip(".")
    if not text:
        raise ValueError("clause number must not be blank")
    parts = text.split(".")
    path = []
    for part in parts:
        if not part.isdigit():
            raise ValueError("clause number %r has a non-numeric component %r"
                             % (number, part))
        if len(part) > 1 and part.startswith("0"):
            raise ValueError("clause number %r has a padded component %r"
                             % (number, part))
        value = int(part)
        if value < 1:
            raise ValueError("clause number %r has a zero component" % (number,))
        path.append(value)
    return tuple(path)


def format_clause_number(path):
    """Return a clause path as its dotted heading number."""
    if not isinstance(path, (list, tuple)) or not path:
        raise ValueError("clause path must be a non-empty sequence")
    for value in path:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError("clause path components must be positive integers")
    return ".".join(str(value) for value in path)


def parse_headings(headings):
    """Return the delivered headings as ordered parsed records."""
    if not isinstance(headings, (list, tuple)) or not headings:
        raise ValueError("headings must be a non-empty sequence")
    records = []
    seen = set()
    for index, item in enumerate(headings):
        if not isinstance(item, dict):
            raise ValueError("headings[%d] must be a mapping" % index)
        if "number" not in item:
            raise ValueError("headings[%d] must carry a 'number'" % index)
        path = parse_clause_number(item["number"])
        number = format_clause_number(path)
        if number in seen:
            raise ValueError("heading number %s is written twice" % number)
        seen.add(number)
        title = item.get("title", "")
        if title is not None and not isinstance(title, str):
            raise ValueError("headings[%d] title must be text" % index)
        records.append(
            {
                "number": number,
                "path": path,
                "depth": len(path),
                "title": (title or "").strip(),
                "position": index,
                "section": _SECTION_OF_NUMBER.get(number),
            }
        )
    return records


def clause_tree_findings(records):
    """Report orphan headings, sibling numbering breaks and over-deep nesting."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of parsed headings")
    present = {record["path"] for record in records}
    orphans = []
    too_deep = []
    for record in records:
        path = record["path"]
        if record["depth"] > MAX_HEADING_DEPTH:
            too_deep.append(record["number"])
        if record["depth"] > 1 and path[:-1] not in present:
            orphans.append(record["number"])
    children = {}
    for path in present:
        parent = path[:-1]
        children.setdefault(parent, []).append(path[-1])
    breaks = []
    for parent in sorted(children):
        numbers = sorted(children[parent])
        for expected, actual in enumerate(numbers, start=1):
            if actual != expected:
                label = format_clause_number(parent + (actual,)) if parent else str(actual)
                breaks.append(label)
                break
    return {
        "orphan_headings": tuple(sorted(orphans)),
        "sibling_numbering_breaks": tuple(breaks),
        "over_deep_headings": tuple(sorted(too_deep)),
    }


def section_coverage(records):
    """Return the template sections absent and the headings outside the template."""
    delivered = {record["section"] for record in records if record["section"]}
    absent = tuple(key for _, key in TEMPLATE_SECTIONS if key not in delivered)
    outside = tuple(
        record["number"] for record in records if record["section"] is None
    )
    return {"absent_sections": absent, "headings_outside_template": outside}


def entry_placement(entries):
    """Report mandated entries that are missing or filed under the wrong clause."""
    if not isinstance(entries, dict):
        raise ValueError("entries must be a mapping of section key to entry list")
    filed = {}
    for section, listed in entries.items():
        if not isinstance(section, str) or not section.strip():
            raise ValueError("entry section keys must be non-empty strings")
        if not isinstance(listed, (list, tuple)):
            raise ValueError("entries['%s'] must be a sequence" % section)
        for entry in listed:
            if not isinstance(entry, str) or not entry.strip():
                raise ValueError("entry names under '%s' must be non-empty strings"
                                 % section)
            key = entry.strip()
            if key in filed:
                raise ValueError("entry '%s' is filed under two clauses" % key)
            filed[key] = section.strip()
    missing = []
    misfiled = []
    for entry, owner in sorted(_OWNER_OF_ENTRY.items()):
        where = filed.get(entry)
        if where is None:
            missing.append(entry)
        elif where != owner:
            misfiled.append(
                {
                    "entry": entry,
                    "filed_under": where,
                    "owning_clause": _NUMBER_OF_SECTION.get(owner, owner),
                }
            )
    unknown = tuple(sorted(key for key in filed if key not in _OWNER_OF_ENTRY))
    return {
        "missing_entries": tuple(missing),
        "misfiled_entries": tuple(misfiled),
        "unknown_entries": unknown,
    }


def layout_conformance_ratio(records, entries):
    """Return the fraction of layout obligations the draft meets."""
    coverage = section_coverage(records)
    placement = entry_placement(entries)
    tree = clause_tree_findings(records)
    section_total = len(TEMPLATE_SECTIONS)
    entry_total = len(_OWNER_OF_ENTRY)
    sections_met = section_total - len(coverage["absent_sections"])
    entries_met = entry_total - len(placement["missing_entries"]) - len(
        placement["misfiled_entries"]
    )
    tree_faults = (
        len(tree["orphan_headings"])
        + len(tree["sibling_numbering_breaks"])
        + len(tree["over_deep_headings"])
    )
    met = sections_met + entries_met - tree_faults
    if met < 0:
        met = 0
    return met / (section_total + entry_total)


def assess_detail_specification_format(draft):
    """Judge a delivered hybrid detail specification against the Annex B layout.

    draft keys: headings (sequence of {number, title}), entries (mapping of
    template section key to the entry names written under it).
    """
    if not isinstance(draft, dict):
        raise ValueError("draft must be a mapping")
    for key in ("headings", "entries"):
        if key not in draft:
            raise ValueError("draft missing required key '%s'" % key)
    records = parse_headings(draft["headings"])
    tree = clause_tree_findings(records)
    coverage = section_coverage(records)
    placement = entry_placement(draft["entries"])
    ratio = layout_conformance_ratio(records, draft["entries"])
    conformant = math.isclose(ratio, 1.0, rel_tol=0.0, abs_tol=RATIO_TOLERANCE)

    findings = []
    for number in tree["orphan_headings"]:
        findings.append("heading %s is written under a parent clause that is absent"
                        % number)
    for number in tree["sibling_numbering_breaks"]:
        findings.append("sibling numbering breaks at %s" % number)
    for number in tree["over_deep_headings"]:
        findings.append("heading %s is nested deeper than the layout allows" % number)
    for key in coverage["absent_sections"]:
        findings.append("template clause %s (%s) is absent from the draft"
                        % (_NUMBER_OF_SECTION[key], key))
    for number in coverage["headings_outside_template"]:
        findings.append("heading %s belongs to no template clause" % number)
    for entry in placement["missing_entries"]:
        findings.append("mandated entry '%s' is not written anywhere" % entry)
    for item in placement["misfiled_entries"]:
        findings.append(
            "entry '%s' is filed under '%s' but belongs to clause %s"
            % (item["entry"], item["filed_under"], item["owning_clause"])
        )

    blocking = bool(findings)
    if blocking:
        verdict = "hold"
    elif placement["unknown_entries"]:
        verdict = "accept-with-remarks"
    else:
        verdict = "accept"

    return {
        "headings": records,
        "tree": tree,
        "coverage": coverage,
        "placement": placement,
        "layout_conformance_ratio": ratio,
        "conformant": conformant,
        "findings": findings,
        "verdict": verdict,
    }
