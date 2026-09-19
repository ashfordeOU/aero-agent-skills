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
- every cross-reference resolves against the tree: skill-local
  scripts/ references/ assets/ paths, repo-root paths (skills/, docs/,
  packages/, research/, ...) and domain routes <domain>/<sub>/<leaf>
  (the router tables and the prose 'pairs with ...' form)
- license == Apache-2.0 (compliance flags, brief 06 s8.3.5)
- compliance in {none, ITAR-GATED, EAR-GATED, STANDARDS-REF}
- standards: non-empty list, every entry resolves in standards-map.yaml;
  a gated standard must be marked reference-only unless skill gated:true
- gated: boolean, consistent with standards-map gating
- metadata.version + metadata.author present

Exit 0 = conformant; 1 = violation (reasons on stdout).
"""

import os
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


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
STANDARDS_MAP = REPO_ROOT / "standards-map.yaml"
COMPLIANCE_VALUES = {"none", "ITAR-GATED", "EAR-GATED", "STANDARDS-REF"}

# ---------------------------------------------------------------------------
# Cross-reference resolution
# ---------------------------------------------------------------------------
# check_ref above only inspects the SHAPE of a reference (absolute vs relative,
# how deep it nests); it never asks the filesystem whether the target is there.
# Everything below does the lookup, so a route to a leaf that was renamed or
# removed is reported with its file, its line and the target that is missing.
#
# INCLUSION RULE (deliberately narrow: a gate that cries wolf gets turned off).
# A path-shaped string in a SKILL.md body counts as a reference ONLY when its
# first segment is one of these namespaces, every one of them read off the tree
# rather than invented:
#
#   scripts/ references/ assets/  the skill-local dirs of the agentskills.io
#                                 layout. Resolved against the SKILL.md's own
#                                 folder first, then the repo root (the corpus
#                                 also has a repo-level scripts/).
#   <repo top-level dir>/         skills/, docs/, packages/, research/, eval/,
#                                 tools/, ops/, context/, security/. Resolved
#                                 against the repo root. Two segments minimum.
#   <domain>/                     a pack directory under skills/. This is the
#                                 router-table "Path" column and the prose
#                                 "pairs with <domain>/<sub>/<leaf>" form.
#                                 Resolved against skills/. THREE segments
#                                 minimum: prose writes "the avionics/equipment
#                                 bay", which is not a path at all, so a
#                                 two-segment <domain>/<word> is left alone.
#
# Anything else is ignored, and the namespace anchor is what keeps the gate
# quiet. Measured on the corpus of 2026-09-19: 225 further tokens are shaped
# like a path (a file extension, or two or more slashes) and start with no
# namespace above -- unit strings (kg/m2/s, J/mol/K), enumerations
# (FHA/PSSA/SSA, MEO/GEO/GTO/HEO) and prose (events/device/day). A rule that
# went by shape alone would report every one of them. Also skipped: fenced
# code blocks, URLs, paths containing '..', and bare filenames with no
# separator.
#
# The corpus hard-wraps prose near column 72, which splits a long route across
# the break after '-', '_' or '/'. Those continuations are rejoined before
# resolution (and the absorbed prefix is not scanned a second time). Same day,
# same rule, rejoin disabled: 46 references read as unresolved instead of 4, so
# 42 of the 46 would have been wolf-cries about healthy paths.

SKILLS_ROOT = REPO_ROOT / "skills"
REF_CHARS = "A-Za-z0-9_./-"
_TRAILING_PUNCT = ".,;:!?'\"`)]}"
_DIR_CACHE = {}


def _dir_names(path):
    """Entry names of a directory, cached; empty frozenset when absent."""
    key = str(path)
    names = _DIR_CACHE.get(key)
    if names is None:
        try:
            names = frozenset(os.listdir(key))
        except OSError:
            names = frozenset()
        _DIR_CACHE[key] = names
    return names


def _subdir_names(root):
    return sorted(
        n
        for n in _dir_names(root)
        if not n.startswith(".") and (root / n).is_dir()
    )


DOMAIN_NS = frozenset(_subdir_names(SKILLS_ROOT))
REPO_NS = frozenset(n for n in _subdir_names(REPO_ROOT) if n not in LOCAL_DIRS)
_ALL_NS = sorted(set(LOCAL_DIRS) | DOMAIN_NS | REPO_NS, key=len, reverse=True)
REF_TOKEN_RE = (
    re.compile(
        r"(?<![%s])(?:%s)/[%s]+"
        % (REF_CHARS, "|".join(re.escape(n) for n in _ALL_NS), REF_CHARS)
    )
    if _ALL_NS
    else None
)
_LEAD_RUN_RE = re.compile(r"^[%s]+" % REF_CHARS)
_TAIL_RUN_RE = re.compile(r"[%s]+$" % REF_CHARS)


def _wraps_into_next_line(text):
    """True when the line ends in the middle of a hard-wrapped path token."""
    t = text.rstrip()
    if not t:
        return False
    if t.endswith("\\"):
        t = t[:-1]
        if not t or t[-1].isspace():
            return False  # a shell line-continuation, not a split path
    elif not t.endswith(("-", "_", "/")):
        return False
    m = _TAIL_RUN_RE.search(t)
    return m is not None and "/" in m.group(0)


def reference_lines(body):
    """Yield (text, first_lineno) per body line outside a ``` fence, with
    hard-wrapped path continuations folded in. Line numbers are relative to
    the body; main() adds the frontmatter offset."""
    lines = body.splitlines()
    n = len(lines)
    fenced = [False] * n
    in_fence = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fenced[i] = True  # the delimiter itself carries no reference
            in_fence = not in_fence
            continue
        fenced[i] = in_fence
    eaten = [0] * n  # chars already absorbed by a preceding joined line
    for i in range(n):
        if fenced[i]:
            continue
        text = lines[i][eaten[i]:]
        j = i
        while _wraps_into_next_line(text) and j + 1 < n and not fenced[j + 1]:
            nxt = lines[j + 1]
            indent = len(nxt) - len(nxt.lstrip())
            m = _LEAD_RUN_RE.match(nxt[indent:])
            if m is None:
                break
            head = text.rstrip()
            if head.endswith("\\"):
                head = head[:-1]
            text = head + m.group(0)
            eaten[j + 1] = indent + m.end()
            j += 1
        yield text, i + 1


def _exists_exact(root, segs):
    """Walk the segments against the real directory listings.

    pathlib exists() is case-insensitive on the macOS build host and
    case-sensitive on the Linux runner, so a mis-cased reference would pass
    the gate locally and fail in CI. Comparing spellings against os.listdir
    makes the verdict identical on both."""
    cur = root
    for part in segs:
        if part not in _dir_names(cur):
            return False
        cur = cur / part
    return True


def tree_root_for(skill_dir):
    """Return the checkout that CONTAINS this file, not the one holding this
    script.

    A lane is a full git worktree: the harvester lints lane files using main's
    scripts/, so a module-level REPO_ROOT resolves a lane leaf's own path
    against main, where it does not exist yet. Walk up from the file instead,
    and take the first ancestor that looks like a checkout of this repository.
    Falls back to REPO_ROOT, so behaviour inside the repo is unchanged.
    """
    try:
        p = skill_dir.resolve()
    except OSError:
        return REPO_ROOT
    for anc in [p] + list(p.parents):
        if (anc / "skills").is_dir() and (anc / "standards-map.yaml").is_file():
            return anc
    return REPO_ROOT


def resolve_ref(ref, skill_dir):
    """Resolve one candidate. Returns (checked, ok, missing_repo_rel_path)."""
    segs = [s for s in ref.split("/") if s not in ("", ".")]
    if not segs or ".." in segs:
        return False, True, None
    head = segs[0]
    tree = tree_root_for(skill_dir)          # the file's own checkout
    skills_root = tree / "skills"
    if head in LOCAL_DIRS:
        roots = [(skill_dir, False), (tree, False)]
    elif head in DOMAIN_NS:
        if len(segs) < 3:
            return False, True, None  # two-segment prose, see the rule above
        roots = [(skills_root, True)]
    elif head in REPO_NS:
        if len(segs) < 2:
            return False, True, None
        roots = [(tree, head == "skills")]
    else:
        return False, True, None
    rel = "/".join(segs)
    for root, route in roots:
        if not _exists_exact(root, segs):
            continue
        target = root / rel
        if route and target.is_dir() and _is_leaf_dir(target):
            if "SKILL.md" not in _dir_names(target):
                return True, False, "%s/SKILL.md" % rel
        return True, True, None
    if head in LOCAL_DIRS:
        try:
            shown = "%s/%s" % (skill_dir.resolve().relative_to(tree), rel)
        except (ValueError, OSError):
            shown = rel
    elif head in REPO_NS:
        shown = rel
    else:
        shown = "skills/%s" % rel
    return True, False, shown


def _is_leaf_dir(target):
    """True when target sits at <tree>/skills/<domain>/<subdomain>/<leaf>.

    Tree-relative for the same reason as tree_root_for: a lane's leaf must be
    recognised as a leaf even though the lane is not this script's checkout.
    """
    parts = target.parts
    if "skills" not in parts:
        return False
    i = len(parts) - 1 - parts[::-1].index("skills")
    return len(parts) - (i + 1) == 3


def check_references(body, body_offset, skill_dir, errs):
    """Resolve every cross-reference in the body. Returns how many were
    checked; appends 'line N: unresolved reference ...' per miss."""
    if REF_TOKEN_RE is None:
        return 0
    checked = 0
    for line, line_no in reference_lines(body):
        for m in REF_TOKEN_RE.finditer(line):
            ref = m.group(0).rstrip(_TRAILING_PUNCT)
            was_checked, ok, missing = resolve_ref(ref, skill_dir)
            if not was_checked:
                continue
            checked += 1
            if not ok:
                errs.append(
                    "line %d: unresolved reference '%s' (no such path: %s)"
                    % (line_no + body_offset, ref, missing)
                )
    return checked



def load_standards_index():
    """Map every searchable key (id, short name, full name) to its entry."""
    with open(STANDARDS_MAP, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    index = {}
    for entry in data.get("standards", []):
        keys = [entry.get("id", "")]
        name = entry.get("name", "")
        if name:
            keys.append(name.split(":")[0].strip())
            keys.append(name.strip())
        for key in keys:
            key = key.strip().lower()
            if key:
                index[key] = entry
    return index


def check_compliance_flags(fm, index, errs):
    """Enforce brief 06 s8.3.5 frontmatter flags: license/compliance/
    standards/gated/metadata. Violations append to errs (never raise)."""
    lic = fm.get("license")
    if lic != "Apache-2.0":
        errs.append("license must equal 'Apache-2.0' (got %r)" % (lic,))
    comp = fm.get("compliance")
    if comp not in COMPLIANCE_VALUES:
        errs.append(
            "compliance must be one of none|ITAR-GATED|EAR-GATED|STANDARDS-REF (got %r)"
            % (comp,)
        )
    raw = fm.get("standards")
    if raw is None:
        errs.append("frontmatter missing required 'standards' list")
        raw = []
    if not isinstance(raw, list):
        errs.append("standards must be a list")
        raw = []
    if len(raw) == 0:
        errs.append("standards must be a non-empty list")
    gated = fm.get("gated")
    if gated is None:
        errs.append("frontmatter missing required 'gated' (bool)")
    elif not isinstance(gated, bool):
        errs.append("gated must be a boolean (true/false), got %r" % (gated,))
    resolved = []
    for i, item in enumerate(raw):
        ref_only = False
        key = None
        if isinstance(item, str):
            key = item
        elif isinstance(item, dict):
            key = item.get("id") or item.get("name")
            ref_only = bool(item.get("reference-only", False))
            if key is None:
                errs.append("standards[%d]: mapping entry needs 'id' or 'name'" % i)
                continue
        else:
            errs.append("standards[%d]: entry must be a string or mapping" % i)
            continue
        entry = index.get(str(key).strip().lower())
        if entry is None:
            errs.append("standards[%d]: '%s' not in standards-map.yaml" % (i, key))
            continue
        resolved.append((entry, ref_only))
    if isinstance(gated, bool):
        for entry, ref_only in resolved:
            if entry.get("gated") and not ref_only and not gated:
                errs.append(
                    "standard '%s' is gated:true in standards-map.yaml; "
                    "skill must be gated:true or list it as reference-only" % entry["id"]
                )
    meta = fm.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
        errs.append("frontmatter missing required 'metadata' mapping")
    if not meta.get("version"):
        errs.append("metadata.version required")
    if not meta.get("author"):
        errs.append("metadata.author required")


def check_mcp_policy(fm, errs):
    """Optional MCP access policy (SEP-2640 delivery): skills may declare
    which MCP servers a host may consult to enrich the workflow. Absent =
    offline-only skill (the default: content + stdlib scripts). Present must
    be an allow list of '<server>:<read|write>' entries; mcp_blocked is a
    hard deny list that wins. This mirrors the roles repo role-lint rule so
    both libraries carry the same access grammar."""
    allowed = fm.get("mcp_allowed")
    blocked = fm.get("mcp_blocked")
    if allowed is None and blocked is None:
        return  # offline-only by default
    if allowed is None:
        errs.append(
            "mcp_blocked without mcp_allowed is redundant (absent mcp_allowed "
            "already blocks all); remove it or add an allow list"
        )
        return
    if not isinstance(allowed, list) or not allowed:
        errs.append("mcp_allowed must be a non-empty list of '<server>:<read|write>' entries")
        return
    for item in allowed:
        if not isinstance(item, str) or re.fullmatch(
            r"[a-z0-9][a-z0-9\-_]*:(read|write)", item
        ) is None:
            errs.append("mcp_allowed entry %r must be '<server>:<read|write>' (e.g. 'aero-agent-roles:read')" % (item,))
    allow_names = {item.split(":", 1)[0] for item in allowed if isinstance(item, str)}
    if isinstance(blocked, list):
        for item in blocked:
            if not isinstance(item, str) or re.fullmatch(
                r"[a-z0-9][a-z0-9\-_]*", item
            ) is None:
                errs.append("mcp_blocked entry %r must be a server name" % (item,))
            elif item in allow_names:
                errs.append("mcp_blocked contradicts mcp_allowed for '%s'" % item)
    elif blocked is not None:
        errs.append("mcp_blocked must be a list of server names")


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
    try:
        index = load_standards_index()
    except OSError as exc:
        errs.append("cannot load standards-map.yaml: %s" % exc)
        index = {}
    check_compliance_flags(fm, index, errs)
    check_mcp_policy(fm, errs)
    body = parts[2] if len(parts) >= 3 else text
    body_offset = text.count("\n", 0, len(text) - len(body))
    n_body = len(body.splitlines())
    if n_body >= MAX_BODY_LINES:
        errs.append("body is %d lines, must be < %d" % (n_body, MAX_BODY_LINES))
    for ref, line_no in ref_targets(body):
        check_ref(ref, line_no + body_offset, errs)
    n_refs = check_references(body, body_offset, p.parent, errs)
    if errs:
        for e in errs:
            print("FAIL gate1-spec-lint: %s: %s" % (p, e))
        sys.exit(1)
    print(
        "PASS gate1-spec-lint: %s name=%s desc=%dch body=%dL "
        "refs-resolved=%d compliance-flags-ok"
        % (p, name, len(desc), n_body, n_refs)
    )


if __name__ == "__main__":
    main()
