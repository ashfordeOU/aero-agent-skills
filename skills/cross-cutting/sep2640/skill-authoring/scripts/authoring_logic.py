#!/usr/bin/env python3
"""SEP-2640 skill authoring logic: frontmatter template and conformance check.

Implements the authoring discipline for a NEW conformant SKILL.md per
SEP-2640 / agentskills.io (paraphrase of the spec, which is emerging and
not yet stable): the required frontmatter fields, the kebab-case name
rule, the description discipline (the description is the router), and
the pre-publish conformance check an author runs before publishing a
leaf. Stdlib only (re, no external deps), deterministic, offline.

Frontmatter parsing is deliberately lightweight (regex over the block
between the leading --- markers): the check targets field presence and
shape, not full YAML semantics. That is enough for a pre-publish gate.

Required fields (agentskills.io SKILL.md, paraphrased):
- name: kebab-case (lowercase letters, digits, single hyphens), equal
  to the leaf folder name
- description: present, action clause plus use-when clause plus
  trigger keywords, within the word and char budgets
- license: Apache-2.0
- compliance: one of none, ITAR-GATED, EAR-GATED, STANDARDS-REF
- standards: a non-empty list whose entries resolve to the pack
  standards map
- gated: a boolean, consistent with the standards list
- metadata: a mapping carrying version and author
"""

import re

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REQUIRED_TOP_LEVEL = (
    "name",
    "description",
    "license",
    "compliance",
    "standards",
    "gated",
    "metadata",
)
COMPLIANCE_VALUES = ("none", "ITAR-GATED", "EAR-GATED", "STANDARDS-REF")
MAX_DESC_CHARS = 1024
DESC_WORD_MIN = 50
DESC_WORD_MAX = 150
MIN_TRIGGER_KEYWORDS = 2

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):\s*(.*)$")
LIST_ITEM_RE = re.compile(r"^-\s+(.*)$")
STANDARDS_LINE_RE = re.compile(r"(?m)^standards:\s*$")
LIST_ITEM_LINE_RE = re.compile(r"(?m)^\s+- ")


def is_kebab_case(name):
    """True when name is kebab-case: lowercase letters, digits, and
    single hyphens only (e.g. skill-authoring, sep2640-leaf-2)."""
    return bool(NAME_RE.fullmatch(str(name)))


def _scalar(raw):
    """Coerce one frontmatter value: strip quotes, parse booleans and
    inline lists, otherwise keep the raw string."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part.strip()) for part in inner.split(",") if part.strip()]
    low = raw.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    return raw


def _parse_fields(block):
    """Parse a flat-ish frontmatter block into nested dict/list values.

    Handles the field shapes used in agentskills.io SKILL.md frontmatter:
    scalars, quoted strings, booleans, inline lists, block lists under a
    key, and one level of nested mappings (metadata). Comment and blank
    lines are ignored. Block list items are recorded for presence checks
    but not deeply parsed.
    """
    fields = {}
    mapping_stack = []  # (dict, indent) of open mapping blocks
    list_owner = None   # (dict, key) when a block list may follow
    for raw in block.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        while mapping_stack and mapping_stack[-1][1] >= indent:
            mapping_stack.pop()
        parent = fields
        for container, _ in mapping_stack:
            parent = container
        if LIST_ITEM_RE.match(stripped):
            if list_owner is not None:
                owner, key = list_owner
                owner.setdefault(key, []).append(stripped[2:].strip())
            continue
        m = KEY_RE.match(stripped)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if value == "":
            node = {}
            parent[key] = node
            mapping_stack.append((node, indent))
            list_owner = None
        else:
            parent[key] = _scalar(value)
            list_owner = (parent, key)
    return fields


def parse_frontmatter(text):
    """Split SKILL.md text into (fields dict, body text).

    Raises ValueError when the leading delimiter is missing or the
    frontmatter block is not closed by a second --- line.
    """
    if not text.startswith("---"):
        raise ValueError("missing leading --- frontmatter delimiter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("frontmatter not closed")
    return _parse_fields(parts[1]), parts[2]


def missing_required_fields(fields):
    """List of required top-level fields absent from the fields dict."""
    return [key for key in REQUIRED_TOP_LEVEL if key not in fields or fields[key] is None]


def check_name(fields, folder_name=None):
    """Name problems: kebab-case shape and folder match, in that order."""
    problems = []
    name = fields.get("name")
    if name is None:
        return problems
    name = str(name)
    if not is_kebab_case(name):
        problems.append("name '%s' is not kebab-case" % name)
    if folder_name is not None and name != folder_name:
        problems.append("name '%s' does not match folder name '%s'" % (name, folder_name))
    return problems


def check_description(fields):
    """Description discipline problems: presence, budgets, use-when
    clause, and trigger keywords (the description is the router)."""
    problems = []
    desc = fields.get("description")
    if desc is None or str(desc).strip() == "":
        problems.append("description missing")
        return problems
    desc = str(desc)
    if len(desc) > MAX_DESC_CHARS:
        problems.append("description is %d chars, max %d" % (len(desc), MAX_DESC_CHARS))
    words = desc.split()
    if not (DESC_WORD_MIN <= len(words) <= DESC_WORD_MAX):
        problems.append(
            "description is %d words, want %d-%d" % (len(words), DESC_WORD_MIN, DESC_WORD_MAX)
        )
    if "use when" not in desc.lower():
        problems.append("description lacks a 'Use when' clause")
    m = re.search(r"trigger", desc, re.IGNORECASE)
    if not m:
        problems.append("description lacks a 'Trigger' keyword clause")
    else:
        after = desc[m.end():]
        keywords = [k.strip(" :,;.") for k in re.split(r"[,;:]", after)]
        keywords = [k for k in keywords if k]
        if len(keywords) < MIN_TRIGGER_KEYWORDS:
            problems.append(
                "fewer than %d trigger keywords after 'Trigger'" % MIN_TRIGGER_KEYWORDS
            )
    return problems


def check_license(fields):
    if fields.get("license") != "Apache-2.0":
        return ["license must equal Apache-2.0"]
    return []


def check_compliance(fields):
    value = fields.get("compliance")
    if value not in COMPLIANCE_VALUES:
        return ["compliance must be one of none|ITAR-GATED|EAR-GATED|STANDARDS-REF"]
    return []


def check_standards(fields, block):
    """standards must be present and non-empty (block-list or inline)."""
    problems = []
    raw = fields.get("standards")
    if raw is None:
        problems.append("standards missing")
        return problems
    if isinstance(raw, list) and not raw:
        problems.append("standards list is empty")
    if isinstance(raw, dict):
        m = STANDARDS_LINE_RE.search(block)
        if not m or not LIST_ITEM_LINE_RE.search(block[m.end():]):
            problems.append("standards block has no entries")
    return problems


def check_gated(fields):
    value = fields.get("gated")
    if not isinstance(value, bool):
        return ["gated must be a boolean (true/false)"]
    return []


def check_metadata(fields):
    """metadata mapping must carry version and author."""
    problems = []
    meta = fields.get("metadata")
    if not isinstance(meta, dict):
        problems.append("metadata mapping missing")
        return problems
    if not meta.get("version"):
        problems.append("metadata.version required")
    if not meta.get("author"):
        problems.append("metadata.author required")
    return problems


def validate_skill_candidate(text, folder_name=None):
    """Pre-publish conformance check for one candidate SKILL.md.

    Returns (problems, valid): problems is the list of missing or
    invalid required-field findings (empty when the candidate is
    conformant), valid is the boolean verdict. Never raises on malformed
    input; a malformed frontmatter becomes a problem with valid False.
    """
    try:
        fields, _body = parse_frontmatter(text)
    except ValueError as exc:
        return [str(exc)], False
    # check_standards scans the raw frontmatter block (parts[1]) for the
    # 'standards:' block-list shape; parse_frontmatter returns the body,
    # so re-split here to hand the check the block it expects.
    frontmatter_block = text.split("---", 2)[1]
    problems = []
    problems += missing_required_fields(fields)
    problems += check_name(fields, folder_name)
    problems += check_description(fields)
    problems += check_license(fields)
    problems += check_compliance(fields)
    problems += check_standards(fields, frontmatter_block)
    problems += check_gated(fields)
    problems += check_metadata(fields)
    return problems, len(problems) == 0


def _emit_scalar(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    text = str(value)
    if text == "" or ":" in text or "#" in text or text[0] in "\"'":
        return '"%s"' % text.replace('"', "'")
    return text


def _render_frontmatter(fields):
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, dict):
            lines.append("%s:" % key)
            for sub, subval in value.items():
                lines.append("  %s: %s" % (sub, _emit_scalar(subval)))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            lines.append("%s:" % key)
            for item in value:
                for i, (sub, subval) in enumerate(item.items()):
                    prefix = "  - " if i == 0 else "    "
                    lines.append("%s%s: %s" % (prefix, sub, _emit_scalar(subval)))
        else:
            lines.append("%s: %s" % (key, _emit_scalar(value)))
    lines.append("---")
    return "\n".join(lines) + "\n"


def build_frontmatter_template(name, description):
    """Build a minimal conformant frontmatter block for a new leaf.

    Fills the required fields from the arguments plus the pack defaults
    (license, compliance, standards, gated, metadata). The caller owns
    the description discipline: pass a description with an action clause,
    a 'Use when' clause, and trigger keywords so the block round-trips
    through validate_skill_candidate with no findings.
    """
    fields = {
        "name": name,
        "description": description,
        "license": "Apache-2.0",
        "compliance": "STANDARDS-REF",
        "standards": [{"id": "sep-2640", "reference-only": True}],
        "gated": False,
        "domain": "cross-cutting",
        "pack": "cross-cutting",
        "compatibility": "agentskills.io SKILL.md; any SKILL.md host",
        "metadata": {
            "domain": "cross-cutting",
            "subdomain": "sep2640",
            "tags": ["sep-2640", "skill-authoring", "frontmatter", "kebab-case"],
            "version": "0.1.0",
            "author": "AeroSkills",
        },
    }
    return _render_frontmatter(fields)


def main(argv=None):
    """CLI: python3 authoring_logic.py <SKILL.md path> [folder name].

    Prints each finding and the verdict; exit 0 when the candidate is
    conformant, 1 otherwise.
    """
    import sys

    args = list(argv) if argv is not None else sys.argv[1:]
    if len(args) < 1 or len(args) > 2:
        print("usage: authoring_logic.py <SKILL.md path> [folder name]", file=sys.stderr)
        return 2
    path = args[0]
    folder_name = args[1] if len(args) == 2 else None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print("cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 2
    problems, valid = validate_skill_candidate(text, folder_name)
    for problem in problems:
        print("finding: %s" % problem)
    print("verdict: %s (%d finding(s))" % ("pass" if valid else "fail", len(problems)))
    return 0 if valid else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
