#!/usr/bin/env python3
"""Aero Agent Skills figure audit — one corpus number, computed, everywhere.

WHY THIS EXISTS
---------------
The company pitch is that its numbers survive inspection. Today a reader can
falsify a headline by counting the tree: the leaf total is quoted as 3021 in
README/metrics, the npm manifest ships 3033 catalogue entries (it also carries
the 12 family router docs), the bundled JetBrains catalogue ships a third
number, and several living docs still carry counts from earlier waves. This
gate resolves every corpus figure in the publishable documents against ONE
register and ONE generator command per denominator.

It is the corpus half of the register that ops/automation/number_audit.py
(brief-audit) already owns for MARKET figures. Same file
(ops/automation/numbers.yaml), same "register or reconcile" contract, new
top-level sections — deliberately NOT a second competing register, because
four records that can disagree are worse than two that cannot.

WHAT IT CHECKS
--------------
1. ARTIFACT checks — the generated JSON that ships to users (docs/metrics.json,
   the npm manifest, the JetBrains plugin catalogue) must declare exactly what
   the tree computes.
2. PROSE checks — every numeric corpus claim in the publishable documents must
   (a) match a denominator registered in numbers.yaml,
   (b) agree with that denominator's generator command, and
   (c) if it is a growth rate, be registered WITH a stated measurement window.

NUMBER MATCHING — READ THIS BEFORE EDITING THE REGEXES
------------------------------------------------------
Never use a regex word boundary against a comma-grouped figure. `\\b` matches
INSIDE "4,472" (between the comma and the 4, and between 4 and 7...), and this
estate has a recorded incident where a figure-repair script built on `\\b`
rewrote every figure in a document. The matcher here uses explicit
character-class lookarounds so a comma-grouped figure is one indivisible
token: "4,472" yields exactly one number, 4472 — never 4, 472, 47 or 150.
`test_comma_group_*` in --selftest locks that behaviour down.

USAGE
-----
  python3 tools/figure_audit.py                # default publishable scope
  python3 tools/figure_audit.py docs README.md # explicit paths
  python3 tools/figure_audit.py --list         # print the register + live values
  python3 tools/figure_audit.py --selftest     # unit tests (stdlib unittest)

Exit 0 = every figure resolves. Exit 1 = at least one violation (each printed
as FAIL file:line). Exit 2 = the register or a generator is broken.

Stdlib only, offline, deterministic. No PyYAML: this file ships, so it carries
a strict mini-reader for the register sections it owns (and refuses anything
outside the shapes it knows, rather than guessing).
"""

import argparse
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTER = os.path.join("ops", "automation", "numbers.yaml")

# Publishable scope: the surfaces a reader/buyer actually reads. Deliberately
# NOT the whole tree:
#   skills/   domain content (failure rates, clause counts) — not corpus claims
#   eval/     corpus data, not prose
#   ops/      internal programme planning + dated wave briefs/state; these are
#             build PLANS ("776 leaves at 10-16 leaves/wave") and historical
#             records, the supersede-not-delete class that brief-audit and
#             stale-number-guard already exclude. Pass ops/ explicitly to scan it.
#   research/ dated research briefs (2026-08-30), same class.
DEFAULT_ROOTS = [
    "README.md",
    "MCP.md",
    "STANDARDS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "docs",
    "packages/aero-agent-skills/README.md",
    ".claude-plugin",
]

TEXT_EXT = (".md", ".txt", ".html")

# Dated snapshots inside the scanned roots (renumbering them would falsify a
# recorded measurement — AGENTS.md supersede-not-delete).
DATED_DOC_RE = re.compile(r"-\d{4}-\d{2}-\d{2}\.(md|txt|html)$")

# docs/harness-contract.md opens with dated milestone-record paragraphs
# (the block before the first '## ' heading). stale-number-guard already
# scans only the live sections below that heading; do the same here.
MILESTONE_PREAMBLE_FILES = ("docs/harness-contract.md",)


class RegisterError(Exception):
    """The register is malformed or uses a shape this reader refuses to guess at."""


class GeneratorError(Exception):
    """A generator command failed or did not print a single integer."""


# --------------------------------------------------------------------------
# strict mini-reader for the register sections this tool owns
# --------------------------------------------------------------------------

_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$")
_ITEM_RE = re.compile(r"^  - ([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$")
_FIELD_RE = re.compile(r"^    ([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$")
_BLOCK_SCALARS = ("|", ">", "|-", ">-", "|+", ">+")


def _strip_comment(text):
    """Drop a trailing '#' comment, respecting quoted strings."""
    out = []
    quote = None
    for ch in text:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _split_inline_list(body):
    parts, cur, quote = [], [], None
    for ch in body:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            cur.append(ch)
        elif ch == ",":
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return parts


def _scalar(token, where):
    token = token.strip()
    if token in _BLOCK_SCALARS:
        raise RegisterError(
            "%s: block scalars (| >) are not allowed in the corpus sections — "
            "use a single-line quoted string" % where
        )
    if token.startswith("[") and token.endswith("]"):
        inner = token[1:-1].strip()
        if not inner:
            return []
        return [_scalar(p, where) for p in _split_inline_list(inner)]
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    if token in ("true", "false"):
        return token == "true"
    if token == "":
        return ""
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if re.fullmatch(r"-?\d+\.\d+", token):
        return float(token)
    return token


def parse_register_sections(text, wanted):
    """Parse ONLY the named top-level keys. Every other top-level key (and its
    block, whatever shape it uses) is skipped without being interpreted, so the
    market half of numbers.yaml stays PyYAML's business."""
    lines = text.splitlines()
    result = {}
    i, n = 0, len(lines)
    while i < n:
        m = _TOP_KEY_RE.match(lines[i])
        if not m:
            i += 1
            continue
        key, rest = m.group(1), _strip_comment(m.group(2))
        if key in wanted and key in result:
            raise RegisterError("%s declared twice at top level" % key)
        block = []
        j = i + 1
        while j < n:
            if lines[j][:1] not in (" ", "\t", "", "#") and _TOP_KEY_RE.match(lines[j]):
                break
            block.append(lines[j])
            j += 1
        if key in wanted:
            result[key] = _parse_block(key, rest, block)
        i = j
    return result


def _parse_block(key, rest, block):
    if rest:
        return _scalar(rest, key)
    items = []
    current = None
    for raw in block:
        line = _strip_comment(raw)
        if not line.strip():
            continue
        m = _ITEM_RE.match(line)
        if m:
            current = {m.group(1): _scalar(m.group(2), key)}
            items.append(current)
            continue
        m = _FIELD_RE.match(line)
        if m:
            if not isinstance(current, dict):
                raise RegisterError("%s: field %r before any '- ' item" % (key, m.group(1)))
            current[m.group(1)] = _scalar(m.group(2), key)
            continue
        raise RegisterError("%s: unsupported line %r" % (key, raw))
    return items


REGISTER_KEYS = (
    "corpus_as_of",
    "corpus_units",
    "corpus_denominators",
    "corpus_ratio_phrases",
    "corpus_growth_rates",
    "corpus_artifacts",
    "corpus_line_exemptions",
    "corpus_subset_markers",
)


def load_register(path):
    with open(path, "r", encoding="utf-8") as fh:
        sections = parse_register_sections(fh.read(), REGISTER_KEYS)
    dens = sections.get("corpus_denominators") or []
    if not dens:
        raise RegisterError("%s: no corpus_denominators section" % path)
    seen = set()
    for d in dens:
        for field in ("id", "value", "generator", "definition"):
            if field not in d:
                raise RegisterError("denominator %r: missing %s" % (d.get("id"), field))
        if d["id"] in seen:
            raise RegisterError("duplicate denominator id %r" % d["id"])
        seen.add(d["id"])
        if not isinstance(d.get("phrases", []), list):
            raise RegisterError("denominator %r: phrases must be an inline list" % d["id"])
    for rate in sections.get("corpus_growth_rates") or []:
        for field in ("id", "value", "unit", "window", "source"):
            if field not in rate:
                raise RegisterError(
                    "growth rate %r: missing %s — a rate without a stated window "
                    "cannot be registered" % (rate.get("id"), field)
                )
        if not str(rate["window"]).strip():
            raise RegisterError("growth rate %r: window is empty" % rate["id"])
    return sections


# --------------------------------------------------------------------------
# generators
# --------------------------------------------------------------------------

_UNSAFE_SHELL = (";", "&&", "||", "`", "$(", ">", "<", "\n")


def run_generator(command, repo_root):
    """Run a register generator command and return the single integer it prints.

    Pipelines are allowed (the commands are find|wc shapes) but a pipe hides the
    exit code, so the pipeline runs under `bash -o pipefail`: a failing `find`
    can never be laundered into a green `wc -l 0`.
    """
    for token in _UNSAFE_SHELL:
        if token in command:
            raise RegisterError(
                "generator refuses %r (contains %r): generators must be a single "
                "pipeline of read-only commands" % (command, token)
            )
    if os.path.exists("/bin/bash"):
        argv = ["/bin/bash", "-o", "pipefail", "-c", command]
    else:  # pragma: no cover - every supported host ships bash
        argv = ["/bin/sh", "-c", command]
    proc = subprocess.run(argv, cwd=repo_root, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    if proc.returncode != 0:
        raise GeneratorError("generator exited %d: %s\n%s"
                             % (proc.returncode, command, proc.stderr.strip()))
    out = proc.stdout.strip()
    if not re.fullmatch(r"\d+", out):
        raise GeneratorError("generator did not print one integer: %s -> %r" % (command, out))
    return int(out)


def measure(register, repo_root):
    """denominator id -> live value computed by its registered generator."""
    return {d["id"]: run_generator(d["generator"], repo_root)
            for d in register["corpus_denominators"]}


# --------------------------------------------------------------------------
# number matching (comma-group safe)
# --------------------------------------------------------------------------

# A number token is indivisible. The lookbehind refuses a start inside a word,
# a comma group, a dotted version or a hyphenated identifier; the lookahead
# refuses an end inside one.
# "4,472" -> one token, 4472.  NOT 4, NOT 472, NOT 150 out of "4,150".
# The hyphen/dash in the lookbehind also drops identifier tails (SEP-2640,
# DO-178C) and the upper bound of a range ("301-400", "~344–353"), which is
# the same exclusion brief-audit makes for ranges and identifiers.
_NUM_BODY = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_NUM_LEFT = r"(?<![\w,.@\-‐‑‒–—])"
_RATIO_LEFT = r"(?<![\w,.@/\-‐‑‒–—])"
_INT_BODY = r"\d{1,3}(?:,\d{3})+|\d+"
NUMBER_RE = re.compile(_NUM_LEFT + r"(" + _NUM_BODY + r")(?![\d,.]*\d)")
RATIO_RE = re.compile(_RATIO_LEFT + r"(" + _INT_BODY + r")\s*/\s*("
                      + _INT_BODY + r")(?![\d,.]*\d)")

# Separator allowed between a number and the unit phrase that follows it.
# Two shapes only, and the distinction matters: a hyphen may JOIN the number
# to the unit with no spaces ("330-leaf", "1754-task"), or up to three
# whitespace/markdown characters may sit between them ("**3021** verified
# skills"). A spaced hyphen is NOT a separator — "Mechanism 2 - Skills" is a
# heading, not a claim of two skills.
SEP = r"(?:[-‐‑‒–—]|[\s_*`~·:()\[\]]{0,3})"

TIME_UNITS = r"(?:second|sec|minute|min|hour|hr|h|day|night|week|month|year)s?"


def parse_number(token):
    """'4,472' -> 4472 ; '19.4' -> 19.4 ; returns (value, is_integer)."""
    plain = token.replace(",", "")
    if "." in plain:
        return float(plain), False
    return int(plain), True


def find_numbers(text):
    """Every indivisible number token in text as (start, end, raw, value, is_int)."""
    out = []
    for m in NUMBER_RE.finditer(text):
        value, is_int = parse_number(m.group(1))
        out.append((m.start(1), m.end(1), m.group(1), value, is_int))
    return out


def _phrase_regex(phrase):
    """Case-insensitive, whitespace-flexible, literal-safe phrase matcher."""
    parts = [re.escape(p) for p in phrase.split()]
    body = r"\s+".join(parts)
    return re.compile(body, re.I)


class Vocabulary(object):
    """Unit phrases -> denominator id, longest phrase first (so 'verified
    skills' wins over 'skills' and 'sub-domain packs' over 'packs')."""

    def __init__(self, register):
        self.by_phrase = []
        claimed = set()
        for d in register["corpus_denominators"]:
            for phrase in d.get("phrases", []):
                p = phrase.strip().lower()
                if p:
                    self.by_phrase.append((p, _phrase_regex(p), d["id"]))
                    claimed.add(p)
        # Units the register names as corpus vocabulary but no denominator
        # claims -> rule (a): a corpus figure with no entry in numbers.yaml.
        self.unclaimed = []
        for unit in register.get("corpus_units") or []:
            u = str(unit).strip().lower()
            if u and u not in claimed:
                self.unclaimed.append((u, _phrase_regex(u), None))
        self.by_phrase.sort(key=lambda t: -len(t[0]))
        self.unclaimed.sort(key=lambda t: -len(t[0]))
        self.all = self.by_phrase + self.unclaimed

    def match_after(self, text, pos):
        """Longest unit phrase starting at pos (after an allowed separator)."""
        gap = re.match(SEP, text[pos:])
        start = pos + (gap.end() if gap else 0)
        for phrase, rx, den_id in self.all:
            m = rx.match(text, start)
            if m:
                return phrase, den_id, m.end()
        return None, None, None


# --------------------------------------------------------------------------
# document scanning
# --------------------------------------------------------------------------

def tree_scopes(repo_root):
    """Family and pack directory names, read from the tree (not hand-listed).
    A markdown section headed by one of these is a SUB-SCOPE: its counts are
    per-family/per-pack, not corpus denominators."""
    scopes = set()
    skills = os.path.join(repo_root, "skills")
    if not os.path.isdir(skills):
        return scopes
    for fam in sorted(os.listdir(skills)):
        fam_dir = os.path.join(skills, fam)
        if not os.path.isdir(fam_dir):
            continue
        scopes.add(_norm_scope(fam))
        for pack in sorted(os.listdir(fam_dir)):
            if os.path.isdir(os.path.join(fam_dir, pack)):
                scopes.add(_norm_scope(pack))
    return scopes


def _norm_scope(name):
    return re.sub(r"[^a-z0-9]+", "", name.lower())


HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")


def iter_files(roots, repo_root):
    for root in roots:
        full = root if os.path.isabs(root) else os.path.join(repo_root, root)
        if os.path.isfile(full):
            yield full
            continue
        if not os.path.isdir(full):
            continue
        for dirpath, dirnames, filenames in os.walk(full):
            dirnames.sort()
            for fn in sorted(filenames):
                if fn.endswith(TEXT_EXT):
                    yield os.path.join(dirpath, fn)


def scan_file(path, rel, register, vocab, live, scopes, findings):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        findings.append("FAIL %s: cannot read (%s)" % (rel, exc))
        return

    if DATED_DOC_RE.search(rel):
        return

    dens = {d["id"]: d for d in register["corpus_denominators"]}
    ratio_phrases = []
    for phrase in register.get("corpus_ratio_phrases") or []:
        pid = phrase.get("denominator")
        ratio_phrases.append((phrase["phrase"].lower(),
                              _phrase_regex(phrase["phrase"].lower()), pid))
    ratio_phrases.sort(key=lambda t: -len(t[0]))
    exemptions = [str(e["marker"]).lower()
                  for e in (register.get("corpus_line_exemptions") or [])]
    subset_markers = [str(m["marker"]).lower()
                      for m in (register.get("corpus_subset_markers") or [])]
    rates = register.get("corpus_growth_rates") or []

    skip_until_heading = rel in MILESTONE_PREAMBLE_FILES
    sub_scope = False

    for lineno, line in enumerate(lines, 1):
        head = HEADING_RE.match(line)
        if head:
            if skip_until_heading and len(head.group(1)) >= 2:
                skip_until_heading = False
            sub_scope = _norm_scope(head.group(2)) in scopes
        if skip_until_heading:
            continue
        low = line.lower()
        if any(mark in low for mark in exemptions):
            continue

        _scan_rates(line, rel, lineno, rates, vocab, findings)
        if sub_scope:
            continue
        _scan_counts(line, rel, lineno, vocab, dens, live, findings, subset_markers)
        _scan_ratios(line, rel, lineno, ratio_phrases, dens, live, findings)


def _verdict(den, found, live_value, rel, lineno, phrase, findings):
    tol = den.get("tolerance_abs", 0)
    if abs(found - live_value) > tol:
        findings.append(
            "FAIL %s:%d %s %s -> denominator %s: generator says %d (%s)"
            % (rel, lineno, phrase, _fmt(found), den["id"], live_value, den["generator"]))


def _fmt(value):
    if isinstance(value, float):
        return repr(value)
    return "{:,}".format(value)


def _scan_counts(line, rel, lineno, vocab, dens, live, findings, subset_markers=()):
    ratio_spans = [(m.start(), m.end()) for m in RATIO_RE.finditer(line)]
    low = line.lower()
    for start, end, raw, value, is_int in find_numbers(line):
        if any(s <= start and end <= e for s, e in ratio_spans):
            continue  # "8/8 gates" — graded once, by _scan_ratios
        phrase, den_id, _after = vocab.match_after(line, end)
        if phrase is None:
            continue
        # Sub-scope: "missing Pitfalls/BC sections (192 leaves)" counts a
        # subset of the corpus, not the corpus. The marker must precede the
        # number on the same line.
        if any(mark in low[:start] for mark in subset_markers):
            continue
        if not is_int:
            # "~4.7k tokens", "19.4 files" — a fractional count is never a
            # denominator; growth rates are handled by _scan_rates.
            continue
        if end < len(line) and line[end].isalpha():
            continue  # "4.7k", "12x" — a suffixed magnitude, not a plain count
        if den_id is None:
            findings.append(
                "FAIL %s:%d %s %s: corpus unit with no denominator in numbers.yaml"
                % (rel, lineno, phrase, _fmt(value)))
            continue
        _verdict(dens[den_id], value, live[den_id], rel, lineno, phrase, findings)


def _scan_ratios(line, rel, lineno, ratio_phrases, dens, live, findings):
    for m in RATIO_RE.finditer(line):
        total = int(m.group(2).replace(",", ""))
        best = None
        low = line.lower()
        for phrase, rx, den_id in ratio_phrases:
            for pm in rx.finditer(low):
                distance = (m.start() - pm.end()) if pm.end() <= m.start() else (pm.start() - m.end())
                if distance < 0 or distance > 40:
                    continue
                if best is None or distance < best[0]:
                    best = (distance, phrase, den_id)
        if best is None:
            continue
        _, phrase, den_id = best
        if den_id is None or den_id not in dens:
            findings.append("FAIL %s:%d %s ratio x/%d: no denominator in numbers.yaml"
                            % (rel, lineno, phrase, total))
            continue
        _verdict(dens[den_id], total, live[den_id], rel, lineno,
                 "%s (ratio x/%d)" % (phrase, total), findings)


def _scan_rates(line, rel, lineno, rates, vocab, findings):
    """A growth rate is <number> <corpus unit> per <time>. It must be registered
    in corpus_growth_rates WITH a window; a bare '84/hour' states a cadence but
    not the period it was measured over, so it cannot be checked by anyone."""
    for start, end, raw, value, _is_int in find_numbers(line):
        phrase, den_id, after = vocab.match_after(line, end)
        if phrase is None:
            continue
        tail = line[after:]
        # "/ ~40 min", "per hour", "an hour", "each 8 h" — the approximation
        # marker is part of the claim's shape, not a reason to miss it.
        m = re.match(r"\s*(?:/|per\b|an\b|a\b|each\b)\s*[~≈]?\s*(?:" + _NUM_BODY + r"\s*)?"
                     + TIME_UNITS, tail, re.I)
        if not m:
            continue
        claim = line[start:after + m.end()].strip()
        hit = None
        for rate in rates:
            for rp in rate.get("phrases", []) or []:
                if str(rp).lower() in line.lower():
                    hit = rate
                    break
            if hit:
                break
        if hit is None:
            findings.append(
                "FAIL %s:%d growth rate %r: not registered in numbers.yaml "
                "corpus_growth_rates — a rate needs a stated measurement window"
                % (rel, lineno, claim))
            continue
        if not str(hit.get("window", "")).strip():
            findings.append("FAIL %s:%d growth rate %r -> %s: registered with no window"
                            % (rel, lineno, claim, hit["id"]))
            continue
        tol = hit.get("tolerance_abs", 0)
        if abs(value - hit["value"]) > tol:
            findings.append("FAIL %s:%d growth rate %r -> %s: register says %s (%s)"
                            % (rel, lineno, claim, hit["id"], hit["value"], hit["window"]))


# --------------------------------------------------------------------------
# artifact checks
# --------------------------------------------------------------------------

def json_lookup(doc, path):
    if path.startswith("len:"):
        node = json_lookup(doc, path[4:])
        if not isinstance(node, (list, dict)):
            raise KeyError(path)
        return len(node)
    node = doc
    for seg in path.split("."):
        node = node[seg]
    return node


def check_artifacts(register, live, repo_root, findings):
    for art in register.get("corpus_artifacts") or []:
        rel = art["file"]
        full = os.path.join(repo_root, rel)
        den_id = art["denominator"]
        try:
            with open(full, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            findings.append("FAIL %s: cannot read artifact (%s)" % (rel, exc))
            continue
        try:
            found = json_lookup(doc, art["json_path"])
        except (KeyError, IndexError, TypeError):
            findings.append("FAIL %s: artifact key %s missing" % (rel, art["json_path"]))
            continue
        if not isinstance(found, int):
            findings.append("FAIL %s: artifact key %s is not an integer (%r)"
                            % (rel, art["json_path"], found))
            continue
        expected = live[den_id]
        if found != expected:
            findings.append(
                "FAIL %s [%s] %s -> denominator %s: generator says %s (%s)"
                % (rel, art["json_path"], _fmt(found), den_id, _fmt(expected),
                   art.get("why", "shipped artifact must equal the tree")))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def audit(repo_root, roots, register_path):
    register = load_register(register_path)
    live = measure(register, repo_root)
    vocab = Vocabulary(register)
    scopes = tree_scopes(repo_root)
    findings = []

    # The register's own stored values must match their generators, or every
    # document graded against the register inherits a stale truth.
    for den in register["corpus_denominators"]:
        stored, actual = den["value"], live[den["id"]]
        if stored != actual:
            findings.append(
                "FAIL %s [corpus_denominators/%s] value %s: generator says %s (%s)"
                % (register_path_rel(register_path, repo_root), den["id"],
                   _fmt(stored), _fmt(actual), den["generator"]))

    check_artifacts(register, live, repo_root, findings)

    scanned = 0
    for path in iter_files(roots, repo_root):
        rel = os.path.relpath(path, repo_root)
        scan_file(path, rel, register, vocab, live, scopes, findings)
        scanned += 1
    return register, live, findings, scanned


def refresh_register(register_path, repo_root, as_of):
    """Rewrite the stored `value:` of every corpus denominator from its own
    generator, and stamp corpus_as_of. No figure is ever typed by hand.

    Deliberately NOT a regex over numbers: a repair script can manufacture the
    defect it reports (a `\\b` inside a comma-grouped figure once rewrote every
    number in a document). This walks the corpus_denominators block line by
    line, tracks the current `- id:`, and replaces exactly the one
    `    value: ...` line that belongs to it.
    """
    register = load_register(register_path)
    live = measure(register, repo_root)
    with open(register_path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines(True)

    out, changed = [], []
    in_block = False
    current = None
    for raw in lines:
        stripped = raw.rstrip("\n")
        top = _TOP_KEY_RE.match(stripped)
        if top:
            if top.group(1) == "corpus_as_of":
                out.append('corpus_as_of: "%s"\n' % as_of)
                continue
            in_block = top.group(1) == "corpus_denominators"
            current = None
            out.append(raw)
            continue
        if in_block:
            item = _ITEM_RE.match(_strip_comment(stripped))
            if item and item.group(1) == "id":
                current = item.group(2).strip().strip("\"'")
            elif current is not None:
                field = _FIELD_RE.match(_strip_comment(stripped))
                if field and field.group(1) == "value":
                    old = int(field.group(2).strip())
                    new = live[current]
                    if old != new:
                        changed.append((current, old, new))
                    out.append("    value: %d\n" % new)
                    continue
        out.append(raw)

    with open(register_path, "w", encoding="utf-8") as fh:
        fh.write("".join(out))
    return changed, live


def register_path_rel(register_path, repo_root):
    try:
        return os.path.relpath(register_path, repo_root)
    except ValueError:  # pragma: no cover
        return register_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit corpus figures against numbers.yaml")
    ap.add_argument("paths", nargs="*", help="files/dirs to scan (default: publishable scope)")
    ap.add_argument("--register", default=None, help="path to numbers.yaml")
    ap.add_argument("--repo-root", default=REPO_ROOT)
    ap.add_argument("--list", action="store_true", help="print denominators + live values and exit")
    ap.add_argument("--refresh", metavar="YYYY-MM-DD", nargs="?", const="",
                    help="rewrite each denominator's stored value from its generator "
                         "and stamp corpus_as_of (never type a figure by hand)")
    ap.add_argument("--selftest", action="store_true", help="run the unit tests and exit")
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    repo_root = os.path.abspath(args.repo_root)
    register_path = args.register or os.path.join(repo_root, DEFAULT_REGISTER)

    try:
        if args.refresh is not None:
            import datetime
            as_of = args.refresh or datetime.date.today().isoformat()
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of):
                print("ERROR figure-audit: --refresh takes YYYY-MM-DD")
                return 2
            changed, _live = refresh_register(register_path, repo_root, as_of)
            for den_id, old, new in changed:
                print("refresh %s: %s -> %s" % (den_id, _fmt(old), _fmt(new)))
            print("PASS figure-audit --refresh: %d denominator(s) rewritten from their "
                  "generators, corpus_as_of=%s" % (len(changed), as_of))
            return 0
        if args.list:
            register = load_register(register_path)
            live = measure(register, repo_root)
            print("corpus_as_of: %s" % register.get("corpus_as_of"))
            width = max(len(d["id"]) for d in register["corpus_denominators"])
            for d in register["corpus_denominators"]:
                mark = "ok " if d["value"] == live[d["id"]] else "DRIFT"
                print("%-*s  registered=%-9s live=%-9s %s\n%s  %s\n%s  $ %s"
                      % (width, d["id"], _fmt(d["value"]), _fmt(live[d["id"]]), mark,
                         " " * width, d["definition"], " " * width, d["generator"]))
            rates = register.get("corpus_growth_rates") or []
            print("\ncorpus_growth_rates: %d registered" % len(rates))
            for r in rates:
                print("  %s = %s %s (window: %s)" % (r["id"], r["value"], r["unit"], r["window"]))
            return 0
        roots = args.paths or DEFAULT_ROOTS
        register, live, findings, scanned = audit(repo_root, roots, register_path)
    except (RegisterError, GeneratorError) as exc:
        print("ERROR figure-audit: %s" % exc)
        return 2

    for line in findings:
        print(line)
    if findings:
        print("FAIL figure-audit: %d violation(s) across %d document(s) + %d artifact(s) — "
              "reconcile the document or register the figure in %s"
              % (len(findings), scanned, len(register.get("corpus_artifacts") or []),
                 register_path_rel(register_path, repo_root)))
        return 1
    print("PASS figure-audit: every corpus figure resolves against %s "
          "(%d documents, %d artifacts, %d denominators)"
          % (register_path_rel(register_path, repo_root), scanned,
             len(register.get("corpus_artifacts") or []),
             len(register["corpus_denominators"])))
    return 0


# --------------------------------------------------------------------------
# unit tests (stdlib unittest; `--selftest`)
# --------------------------------------------------------------------------

SAMPLE_REGISTER = '''
unrelated_market_section:
  - id: kdense
    stars: 44256
    note: >
      a block scalar in someone else's section must not break this reader

corpus_as_of: "2026-09-19"

corpus_units: ["verified skills", "skills", "leaves", "packs", "families", "orphan skills"]

corpus_denominators:
  - id: leaves
    value: 7
    definition: "depth-4 SKILL.md files"
    generator: "printf 7"
    phrases: ["verified skills", "leaf skills", "leaves", "leaf", "skills"]
    tolerance_abs: 0
  - id: packs
    value: 3
    definition: "sub-domain pack directories"
    generator: "printf 3"
    phrases: ["sub-domain packs", "live packs", "packs"]
  - id: validate_gates
    value: 9
    definition: "prerequisites of the Makefile validate target"
    generator: "printf 9"
    phrases: ["gates"]

corpus_ratio_phrases:
  - phrase: "gates"
    denominator: validate_gates

corpus_growth_rates: []

corpus_artifacts: []

corpus_line_exemptions:
  - marker: "release every 100 skills"
    why: "founder cadence policy, not a corpus claim"
'''


def _build_selftest_case():
    import unittest

    class FigureAuditTests(unittest.TestCase):
        def setUp(self):
            self.register = parse_register_sections(SAMPLE_REGISTER, REGISTER_KEYS)
            self.vocab = Vocabulary(self.register)
            self.dens = {d["id"]: d for d in self.register["corpus_denominators"]}
            self.live = {"leaves": 7, "packs": 3, "validate_gates": 9}

        # ---- the recorded incident: \b matches INSIDE a comma-grouped figure
        def test_comma_group_is_one_indivisible_token(self):
            got = [(t[2], t[3]) for t in find_numbers("the registry holds 4,472 operations")]
            self.assertEqual(got, [("4,472", 4472)])

        def test_comma_group_never_yields_an_inner_number(self):
            values = [t[3] for t in find_numbers("4,472")]
            self.assertEqual(values, [4472])
            self.assertNotIn(4, values)
            self.assertNotIn(472, values)
            self.assertNotIn(47, values)

        def test_word_boundary_would_have_matched_inside_4150(self):
            # This is the defect, reproduced: \b150\b DOES match inside "4,150",
            # which is how a repair script rewrote "4,472" to "4,150".
            self.assertIsNotNone(re.search(r"\b150\b", "4,150"))
            self.assertIsNotNone(re.search(r"\b4\b", "4,150"))
            # Our matcher refuses both: one token, one value.
            self.assertEqual([t[3] for t in find_numbers("4,150")], [4150])

        def test_comma_group_inside_a_sentence_keeps_its_neighbours(self):
            text = "1,754 router tasks and 3,021 leaves"
            self.assertEqual([t[3] for t in find_numbers(text)], [1754, 3021])

        def test_comma_grouped_claim_is_graded_as_the_whole_figure(self):
            findings = []
            _scan_counts("the library ships 4,472 leaves", "d.md", 1,
                         self.vocab, self.dens, self.live, findings)
            self.assertEqual(len(findings), 1)
            self.assertIn("4,472", findings[0])
            self.assertIn("generator says 7", findings[0])

        # ---- number matching hygiene
        def test_versions_and_identifiers_are_not_numbers(self):
            self.assertEqual(find_numbers("aero-agent-skills 1.28.0"), [])
            self.assertEqual([t[3] for t in find_numbers("SEP-2640")], [])
            self.assertEqual([t[3] for t in find_numbers("DO-178C")], [])
            self.assertEqual([t[3] for t in find_numbers("Hit@1 corpus tasks")], [])

        def test_range_upper_bound_is_not_a_standalone_claim(self):
            self.assertEqual([t[3] for t in find_numbers("band v1.3.0 (301-400)")], [301])
            self.assertEqual([t[3] for t in find_numbers("~344–353 leaves")], [344])

        def test_number_hyphen_unit_still_matches(self):
            findings = []
            _scan_counts("a 1754-task corpus", "d.md", 1, self.vocab,
                         self.dens, self.live, findings)
            self.assertEqual([t[3] for t in find_numbers("330-leaf catalog")], [330])
            self.assertEqual(findings, [])  # 'task corpus' is not a phrase in the sample

        def test_decimals_are_matched_but_never_graded_as_a_count(self):
            self.assertEqual([t[3] for t in find_numbers("~4.7k tokens")], [4.7])
            findings = []
            _scan_counts("the plugin's skills (~4.7k tokens)", "d.md", 1,
                         self.vocab, self.dens, self.live, findings)
            self.assertEqual(findings, [])

        # ---- rule (b): disagrees with its generator
        def test_correct_count_passes(self):
            findings = []
            _scan_counts("7 verified skills in 3 packs", "d.md", 1,
                         self.vocab, self.dens, self.live, findings)
            self.assertEqual(findings, [])

        def test_stale_count_fails(self):
            findings = []
            _scan_counts("330-leaf catalog", "d.md", 9,
                         self.vocab, self.dens, self.live, findings)
            self.assertEqual(len(findings), 1)
            self.assertIn("d.md:9", findings[0])
            self.assertIn("denominator leaves", findings[0])

        def test_spaced_hyphen_is_not_a_separator(self):
            findings = []
            _scan_counts("Mechanism 2 - Skills (progressive disclosure)", "d.md", 1,
                         self.vocab, self.dens, self.live, findings)
            self.assertEqual(findings, [])

        def test_subset_marker_suppresses_a_partial_count(self):
            findings = []
            _scan_counts("missing Pitfalls sections (192 leaves)", "d.md", 1,
                         self.vocab, self.dens, self.live, findings, ["missing"])
            self.assertEqual(findings, [])
            _scan_counts("the library ships 192 leaves", "d.md", 1,
                         self.vocab, self.dens, self.live, findings, ["missing"])
            self.assertEqual(len(findings), 1)

        def test_ratio_is_graded_once_not_twice(self):
            findings = []
            _scan_counts("8/8 gates green", "README.md", 16,
                         self.vocab, self.dens, self.live, findings)
            self.assertEqual(findings, [])  # left to _scan_ratios

        def test_longest_phrase_wins(self):
            findings = []
            _scan_counts("4 sub-domain packs", "d.md", 1,
                         self.vocab, self.dens, self.live, findings)
            self.assertIn("sub-domain packs", findings[0])

        # ---- rule (a): no entry in numbers.yaml
        def test_corpus_unit_without_a_denominator_fails(self):
            findings = []
            _scan_counts("42 orphan skills shipped", "d.md", 3,
                         self.vocab, self.dens, self.live, findings)
            self.assertEqual(len(findings), 1)
            self.assertIn("no denominator in numbers.yaml", findings[0])

        # ---- rule (c): growth rate with no stated window
        def test_unregistered_growth_rate_fails(self):
            findings = []
            _scan_rates("we ship 84 skills/hour", "d.md", 4, [], self.vocab, findings)
            self.assertEqual(len(findings), 1)
            self.assertIn("growth rate", findings[0])
            self.assertIn("stated measurement window", findings[0])

        def test_decimal_growth_rate_is_caught(self):
            findings = []
            _scan_rates("sustained 19.4 files/hour", "d.md", 4, [],
                        Vocabulary({"corpus_denominators": [
                            {"id": "files", "value": 1, "definition": "x",
                             "generator": "printf 1", "phrases": ["files"]}]}),
                        findings)
            self.assertEqual(len(findings), 1)
            self.assertIn("19.4 files/hour", findings[0])

        def test_registered_growth_rate_with_window_passes(self):
            rates = [{"id": "night", "value": 84, "unit": "leaves/hour",
                      "window": "2026-09-13 21:00Z-05:00Z, 8 h",
                      "source": "harvest log", "phrases": ["leaves/hour"]}]
            findings = []
            _scan_rates("84 leaves/hour over the night run", "d.md", 4,
                        rates, self.vocab, findings)
            self.assertEqual(findings, [])

        def test_registered_growth_rate_value_drift_fails(self):
            rates = [{"id": "night", "value": 84, "unit": "leaves/hour",
                      "window": "2026-09-13, 8 h", "source": "log",
                      "phrases": ["leaves/hour"]}]
            findings = []
            _scan_rates("170 leaves/hour", "d.md", 4, rates, self.vocab, findings)
            self.assertEqual(len(findings), 1)
            self.assertIn("register says 84", findings[0])

        def test_register_refuses_a_rate_without_a_window(self):
            bad = SAMPLE_REGISTER.replace(
                "corpus_growth_rates: []",
                'corpus_growth_rates:\n'
                '  - id: night\n'
                '    value: 84\n'
                '    unit: "leaves/hour"\n'
                '    source: "log"\n')
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".yaml")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(bad)
                with self.assertRaises(RegisterError):
                    load_register(path)
            finally:
                os.unlink(path)

        def test_approximated_rate_is_still_a_rate(self):
            findings = []
            _scan_rates("10 leaves / ~40 min / lane", "p.md", 105, [],
                        self.vocab, findings)
            self.assertEqual(len(findings), 1)
            self.assertIn("10 leaves / ~40 min", findings[0])

        def test_refresh_rewrites_only_the_value_lines(self):
            import tempfile
            src = SAMPLE_REGISTER.replace("    value: 7\n", "    value: 1\n", 1)
            fd, path = tempfile.mkstemp(suffix=".yaml")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(src)
                changed, live = refresh_register(path, REPO_ROOT, "2026-09-19")
                self.assertEqual(changed, [("leaves", 1, 7)])
                after = open(path, encoding="utf-8").read()
                self.assertIn('corpus_as_of: "2026-09-19"', after)
                # the market half and every non-value line survive untouched
                self.assertIn("unrelated_market_section", after)
                self.assertIn("stars: 44256", after)
                self.assertIn('generator: "printf 7"', after)
                self.assertEqual(load_register(path)["corpus_denominators"][0]["value"], 7)
            finally:
                os.unlink(path)

        def test_domain_per_hour_rates_are_not_corpus_rates(self):
            findings = []
            _scan_rates("a 1e-6 per hour failure rate at 80 percent confidence",
                        "s.md", 1, [], self.vocab, findings)
            self.assertEqual(findings, [])

        # ---- ratios
        def test_gate_ratio_drift_fails(self):
            ratio = [("gates", _phrase_regex("gates"), "validate_gates")]
            findings = []
            _scan_ratios("8/8 gates green", "README.md", 16, ratio,
                         self.dens, self.live, findings)
            self.assertEqual(len(findings), 1)
            self.assertIn("generator says 9", findings[0])

        def test_correct_gate_ratio_passes(self):
            ratio = [("gates", _phrase_regex("gates"), "validate_gates")]
            findings = []
            _scan_ratios("9/9 REAL gates green", "README.md", 1, ratio,
                         self.dens, self.live, findings)
            self.assertEqual(findings, [])

        def test_distant_ratio_is_not_attributed_to_a_phrase(self):
            ratio = [("gates", _phrase_regex("gates"), "validate_gates")]
            findings = []
            line = "gates" + " " * 60 + "1/2 of the way"
            _scan_ratios(line, "d.md", 1, ratio, self.dens, self.live, findings)
            self.assertEqual(findings, [])

        # ---- register reader
        def test_reader_skips_other_sections_and_block_scalars(self):
            self.assertEqual(self.register["corpus_as_of"], "2026-09-19")
            self.assertNotIn("unrelated_market_section", self.register)
            self.assertEqual(len(self.register["corpus_denominators"]), 3)
            self.assertEqual(self.register["corpus_denominators"][0]["phrases"][0],
                             "verified skills")

        def test_reader_rejects_a_block_scalar_in_a_corpus_section(self):
            bad = SAMPLE_REGISTER.replace('    definition: "depth-4 SKILL.md files"',
                                          "    definition: >")
            with self.assertRaises(RegisterError):
                parse_register_sections(bad, REGISTER_KEYS)

        def test_reader_rejects_a_repeated_top_level_section(self):
            with self.assertRaises(RegisterError):
                parse_register_sections(
                    SAMPLE_REGISTER + "\ncorpus_growth_rates: []\n", REGISTER_KEYS)

        def test_reader_rejects_a_duplicate_denominator_id(self):
            import tempfile
            bad = SAMPLE_REGISTER.replace(
                "corpus_ratio_phrases:",
                "  - id: leaves\n"
                "    value: 7\n"
                '    definition: "dup"\n'
                '    generator: "printf 7"\n'
                "\ncorpus_ratio_phrases:")
            fd, path = tempfile.mkstemp(suffix=".yaml")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(bad)
                with self.assertRaises(RegisterError):
                    load_register(path)
            finally:
                os.unlink(path)

        # ---- generators
        def test_generator_returns_an_integer(self):
            self.assertEqual(run_generator("printf 3021", REPO_ROOT), 3021)

        def test_generator_refuses_command_chaining(self):
            with self.assertRaises(RegisterError):
                run_generator("printf 1; rm -rf /", REPO_ROOT)

        def test_generator_pipeline_failure_is_not_laundered_by_the_pipe(self):
            # `false | wc -l` prints 0 and exits 0 without pipefail.
            with self.assertRaises(GeneratorError):
                run_generator("false | wc -l", REPO_ROOT)

        def test_generator_must_print_exactly_one_integer(self):
            with self.assertRaises(GeneratorError):
                run_generator("printf 'a b'", REPO_ROOT)

        # ---- exemptions and scoping
        def test_line_exemption_is_honoured(self):
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".md")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("founder directive: release every 100 skills\n")
            findings = []
            try:
                scan_file(path, "docs/x.md", self.register, self.vocab,
                          self.live, set(), findings)
            finally:
                os.unlink(path)
            self.assertEqual(findings, [])

        def test_sub_scope_heading_suppresses_per_family_counts(self):
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".md")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("# Map\n\n2 leaves\n\n## aerodynamics\n\n57 skills\n")
            findings = []
            try:
                scan_file(path, "docs/y.md", self.register, self.vocab,
                          self.live, {"aerodynamics"}, findings)
            finally:
                os.unlink(path)
            self.assertEqual(len(findings), 1)
            self.assertIn("docs/y.md:3", findings[0])

        def test_dated_snapshot_documents_are_skipped(self):
            findings = []
            scan_file(__file__, "docs/audit-leaf-2026-09-04.md", self.register,
                      self.vocab, self.live, set(), findings)
            self.assertEqual(findings, [])

        # ---- artifacts
        def test_artifact_drift_is_reported(self):
            import tempfile
            d = tempfile.mkdtemp()
            with open(os.path.join(d, "catalog.json"), "w", encoding="utf-8") as fh:
                json.dump({"count": 2685, "skills": [1, 2]}, fh)
            reg = {"corpus_artifacts": [
                {"file": "catalog.json", "json_path": "count",
                 "denominator": "leaves", "why": "bundled IDE catalogue"},
                {"file": "catalog.json", "json_path": "len:skills",
                 "denominator": "leaves"}]}
            findings = []
            check_artifacts(reg, {"leaves": 7}, d, findings)
            self.assertEqual(len(findings), 2)
            self.assertIn("2,685", findings[0])
            self.assertIn("bundled IDE catalogue", findings[0])

    return FigureAuditTests


def run_selftest():
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(_build_selftest_case())
    # unittest writes its summary to STDERR; the caller must capture both
    # streams or a pass reads as a failure.
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stderr).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
