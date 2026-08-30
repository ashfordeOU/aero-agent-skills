#!/usr/bin/env python3
"""Gate 1: agentskills.io SKILL.md conformance lint for one file.

Contract: docs/harness-contract.md gate 1. Checks:
- frontmatter parses as YAML mapping
- name: required, <=64 chars, kebab-case (lowercase/numbers/hyphens), equals
  parent directory name
- description: required, <=1024 chars
- compatibility: <=500 chars when present
- body <500 lines
- references one level deep from SKILL.md; relative paths only

Exit 0 = conformant; 1 = violation (reasons on stdout).
"""

import pathlib
import re
import sys

import yaml

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESC = 1024
MAX_COMPAT = 500
MAX_BODY_LINES = 500

# Skill-local dirs; references into these must sit one level below SKILL.md.
LOCAL_DIRS = {"references", "scripts", "assets"}

URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def ref_targets(body):
    """Yield (target, lineno) for markdown link targets and code-span tokens."""
    for i, line in enumerate(body.splitlines(), 1):
        for m in re.finditer(r"\]\(([^)\s]+)\)", line):
            yield m.group(1), i
        for m in re.finditer(r"`([^`]+)`", line):
            yield m.group(1), i


def check_ref(ref, line_no, errs):
    if not ref or ref.startswith("#"):
        return
    if URL_RE.match(ref):
        return  # web links are fine; the rule is about local references
    if ref.startswith("/"):
        errs.append("line %d: absolute path ref '%s' (relative paths only)" % (line_no, ref))
        return
    if ref.startswith(".."):
        return  # upward navigation is not a skill reference
    parts = ref.split("/")
    if parts[0] not in LOCAL_DIRS:
        return  # organizational/path mention, not a skill reference
    dirs_below = [c for c in parts[:-1] if c not in ("", ".")]
    if len(dirs_below) > 1:
        errs.append(
            "line %d: ref '%s' nests deeper than one level from SKILL.md" % (line_no, ref)
        )


def main():
    p = pathlib.Path(sys.argv[1])
    text = p.read_text(encoding="utf-8")
    errs = []
    if not text.startswith("---"):
        errs.append("missing frontmatter delimiter")
    parts = text.split("---", 2)
    fm = None
    if len(parts) < 3:
        errs.append("frontmatter not closed")
    else:
        try:
            fm = yaml.safe_load(parts[1])
        except Exception as e:  # noqa: BLE001
            errs.append("frontmatter yaml error: %s" % e)
    if not isinstance(fm, dict):
        errs.append("frontmatter is not a YAML mapping")
        fm = {}
    name = fm.get("name")
    if not name:
        errs.append("frontmatter missing required 'name'")
    else:
        if len(name) > MAX_NAME:
            errs.append("name is %d chars, max %d" % (len(name), MAX_NAME))
        if not NAME_RE.fullmatch(name):
            errs.append("name '%s' is not kebab-case (lowercase/numbers/hyphens)" % name)
        if name != p.parent.name:
            errs.append("name '%s' != parent dir name '%s'" % (name, p.parent.name))
    desc = fm.get("description")
    if not desc:
        errs.append("frontmatter missing required 'description'")
        desc = ""
    if len(desc) > MAX_DESC:
        errs.append("description is %d chars, max %d" % (len(desc), MAX_DESC))
    compat = fm.get("compatibility")
    if compat is not None and len(compat) > MAX_COMPAT:
        errs.append("compatibility is %d chars, max %d" % (len(compat), MAX_COMPAT))
    body = parts[2] if len(parts) >= 3 else text
    n_body = len(body.splitlines())
    if n_body >= MAX_BODY_LINES:
        errs.append("body is %d lines, must be < %d" % (n_body, MAX_BODY_LINES))
    for ref, line_no in ref_targets(body):
        check_ref(ref, line_no, errs)
    if errs:
        for e in errs:
            print("FAIL gate1-spec-lint: %s: %s" % (p, e))
        sys.exit(1)
    print(
        "PASS gate1-spec-lint: %s name=%s desc=%dch body=%dL refs-ok"
        % (p, name, len(desc), n_body)
    )


if __name__ == "__main__":
    main()
