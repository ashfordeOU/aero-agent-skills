"""Content and layout of a hybrid microcircuit detail specification.

Anchor: ECSS-Q-ST-60-05 clause 7.2 (what the detailed product specification
of a hybrid must state, and the layout template it follows). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise and validate the declared sections of a draft specification.
2. Name the template sections it omits and the declared sections that carry
   no content, because an empty heading is not a stated requirement.
3. Place any section outside the template, so an addendum is visible rather
   than silently accepted as part of the mandated set.
4. Measure how far the written order departs from the template order by the
   longest run of sections that is already in template order; everything
   outside that run is the set that has to move.
5. Resolve every applicable-document citation made anywhere in the
   specification against the documents the specification itself lists.
6. Return a completeness ratio and one accept-or-hold verdict.
"""

__all__ = [
    "TEMPLATE_SECTIONS",
    "normalize_key",
    "validate_sections",
    "missing_sections",
    "empty_sections",
    "unexpected_sections",
    "longest_in_template_order",
    "ordering_displacements",
    "completeness_ratio",
    "declared_documents",
    "unresolved_references",
    "assess_detail_specification",
]

# The layout template a hybrid detail specification follows, in order.
TEMPLATE_SECTIONS = (
    "identification",
    "scope",
    "applicable-documents",
    "requirements",
    "verification-and-quality-assurance",
    "delivery-and-packaging",
    "notes",
)

_DOCUMENTS_SECTION = "applicable-documents"


def normalize_key(raw):
    """Return a section key in the canonical hyphenated lower-case form."""
    if not isinstance(raw, str):
        raise ValueError("section key must be a string, got %r" % (raw,))
    key = "-".join(raw.strip().lower().split())
    key = key.replace("_", "-")
    while "--" in key:
        key = key.replace("--", "-")
    key = key.strip("-")
    if not key:
        raise ValueError("section key must not be empty")
    return key


def _content_items(content, key):
    """Return the content of one section as a list of non-empty strings."""
    if content is None:
        return []
    if isinstance(content, str):
        return [content] if content.strip() else []
    if isinstance(content, (list, tuple)):
        items = []
        for i, item in enumerate(content):
            if not isinstance(item, str):
                raise ValueError("section '%s' content[%d] must be a string" % (key, i))
            if item.strip():
                items.append(item.strip())
        return items
    raise ValueError("section '%s' content must be a string or a sequence of strings" % key)


def validate_sections(sections):
    """Return the declared sections as an ordered list of validated records."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be an ordered sequence of section mappings")
    if not sections:
        raise ValueError("a detail specification must declare at least one section")
    records = []
    seen = set()
    for i, section in enumerate(sections):
        if not isinstance(section, dict):
            raise ValueError("sections[%d] must be a mapping" % i)
        if "key" not in section:
            raise ValueError("sections[%d] missing required key 'key'" % i)
        key = normalize_key(section["key"])
        if key in seen:
            raise ValueError("section '%s' declared twice" % key)
        seen.add(key)
        raw_refs = section.get("references", ())
        if raw_refs is None:
            raw_refs = ()
        if not isinstance(raw_refs, (list, tuple)):
            raise ValueError("section '%s' references must be a sequence" % key)
        refs = []
        for item in raw_refs:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("section '%s' has a non-string citation %r" % (key, item))
            token = item.strip()
            if token not in refs:
                refs.append(token)
        records.append(
            {
                "key": key,
                "position": i,
                "content": _content_items(section.get("content"), key),
                "references": tuple(refs),
            }
        )
    return records


def missing_sections(sections):
    """Return the template sections the draft never declares, in template order."""
    records = validate_sections(sections)
    declared = {r["key"] for r in records}
    return tuple(key for key in TEMPLATE_SECTIONS if key not in declared)


def empty_sections(sections):
    """Return the declared template sections that carry no content."""
    records = validate_sections(sections)
    return tuple(r["key"] for r in records if r["key"] in TEMPLATE_SECTIONS and not r["content"])


def unexpected_sections(sections):
    """Return the declared sections that sit outside the layout template."""
    records = validate_sections(sections)
    return tuple(r["key"] for r in records if r["key"] not in TEMPLATE_SECTIONS)


def longest_in_template_order(sections):
    """Return the longest run of declared sections already in template order."""
    records = validate_sections(sections)
    indexed = [
        (r["key"], TEMPLATE_SECTIONS.index(r["key"]))
        for r in records
        if r["key"] in TEMPLATE_SECTIONS
    ]
    if not indexed:
        return []
    n = len(indexed)
    best = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if indexed[j][1] < indexed[i][1] and best[j] + 1 > best[i]:
                best[i] = best[j] + 1
                prev[i] = j
    end = max(range(n), key=lambda i: (best[i], -i))
    chain = []
    while end != -1:
        chain.append(indexed[end][0])
        end = prev[end]
    chain.reverse()
    return chain


def ordering_displacements(sections):
    """Return the template sections that have to move to restore the layout."""
    records = validate_sections(sections)
    in_order = set(longest_in_template_order(sections))
    return tuple(
        r["key"] for r in records if r["key"] in TEMPLATE_SECTIONS and r["key"] not in in_order
    )


def completeness_ratio(sections):
    """Return the fraction of template sections that are declared and filled."""
    records = validate_sections(sections)
    filled = {r["key"] for r in records if r["key"] in TEMPLATE_SECTIONS and r["content"]}
    return len(filled) / float(len(TEMPLATE_SECTIONS))


def declared_documents(sections):
    """Return the document identifiers listed in the applicable-documents section."""
    records = validate_sections(sections)
    for record in records:
        if record["key"] == _DOCUMENTS_SECTION:
            return tuple(record["content"])
    return ()


def unresolved_references(sections):
    """Return (section, citation) pairs citing a document the draft never lists."""
    records = validate_sections(sections)
    listed = set(declared_documents(sections))
    out = []
    for record in records:
        for citation in record["references"]:
            if citation not in listed:
                out.append((record["key"], citation))
    return out


def assess_detail_specification(spec):
    """Run the full clause 7.2 detail-specification content assessment.

    spec keys: sections (ordered sequence of section mappings); optional
    allow_additional_sections (bool, default False).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "sections" not in spec:
        raise ValueError("spec missing required key 'sections'")
    allow_extra = spec.get("allow_additional_sections", False)
    if not isinstance(allow_extra, bool):
        raise ValueError("allow_additional_sections must be a boolean")

    sections = spec["sections"]
    absent = missing_sections(sections)
    blank = empty_sections(sections)
    extra = unexpected_sections(sections)
    displaced = ordering_displacements(sections)
    unresolved = unresolved_references(sections)
    ratio = completeness_ratio(sections)

    findings = []
    if absent:
        findings.append("template sections never declared: %s" % ", ".join(absent))
    if blank:
        findings.append("declared sections carrying no content: %s" % ", ".join(blank))
    if displaced:
        findings.append("sections out of template order: %s" % ", ".join(displaced))
    if extra and not allow_extra:
        findings.append("sections outside the layout template: %s" % ", ".join(extra))
    if unresolved:
        findings.append(
            "citations resolving to no listed applicable document: %s"
            % ", ".join("%s cites %s" % pair for pair in unresolved)
        )

    return {
        "missing_sections": absent,
        "empty_sections": blank,
        "unexpected_sections": extra,
        "displaced_sections": displaced,
        "in_template_order": longest_in_template_order(sections),
        "unresolved_references": unresolved,
        "completeness_ratio": ratio,
        "findings": findings,
        "acceptable": not findings,
    }
