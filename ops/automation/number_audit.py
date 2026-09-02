#!/usr/bin/env python3
"""Aero Agent Skills brief-audit engine (deterministic, no LLM).

Scans repo docs (research/, marketing/, development/, docs/, README.md — or
explicit paths given as args; development/builds/ and docs/superpowers/ are
excluded as dated build artifacts and audit meta-docs, see EXCLUDED_DIRS) for
quoted market numbers and resolves each against ops/automation/numbers.yaml
(the canonical register). Exit 1 on any drift/unresolved/ambiguous figure,
printing a diff (file, line, expected, found). Exit 0 clean.

Scope (documented in ops/automation/TEST.md):
- Checked: star counts (N★ / Nk★ / "N stars" / "Nk stars"), fork counts
  ("N forks" / "Nk forks"), skill counts ("N skills" — only when a repo alias
  is on the line, value >= 10), the first numeric cell after a repo alias in a
  pipe-table row (star column, pure-number cell only; alias must be
  cell-dominant: cell is owner/repo or alias == cell after markdown
  stripping, so comma-separated skill-name lists are never repo cells),
  and derived claims
  (total/largest phrases with the number following the phrase).
- Excluded: ranges (N–M / N→M, self-consistent), floors (N+), 4-digit years,
  dates, identifier-embedded numbers (SEP-2640, v1.1.0), bare prose numbers
  without a market marker, internal Aero Agent Skills target/design figures (no repo
  alias, no external truth to verify), attributed historical quotes
  ("measured N", "brief says N", "same week") which resolve against the
  register's `measurements` section.
- Resolution: nearest preceding repo alias on the line wins; no alias ->
  derived phrase (number after phrase) -> unique register match (multiple
  matches = FAIL ambiguous, forcing the doc to name the repo).
"""
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_YAML = os.path.join(REPO_ROOT, "ops", "automation", "numbers.yaml")
DEFAULT_ROOTS = ["research", "marketing", "development", "docs", "README.md"]

# Dated/planning artifacts excluded from the market-number audit (documented
# in ops/automation/TEST.md):
# - development/builds/: dated build snapshots of reports; renumbering them
#   would falsify history (AGENTS.md supersede-not-delete). Living briefs carry
#   the canonical values.
# - docs/superpowers/: planning/meta docs whose stale values (38.0k★, 31.9k,
#   16★ ...) are intentional examples of what the audit catches — the audit's
#   own spec and TDD fixture descriptions, not market claims.
# - research/peer-skill-repo-audit-2026-08-31.md: dated snapshot of peer repo
#   states measured earlier on 2026-08-31 (K-Dense 39,855 etc.); renumbering
#   it would falsify the recorded measurement. Same class as development/builds/.
EXCLUDED_DIRS = ("development/builds", "docs/superpowers", "research/peer-skill-repo-audit")

RANGE_RE = re.compile(r"\d[\d,.]*[kK]?\s*[–—\-→]\s*\d[\d,.]*[kK]?")
FLOOR_RE = re.compile(r"\d[\d,.]*[kK]?\s*\+")
# negative lookbehind: number must not be embedded in an identifier (SEP-2640)
NUM_PREFIX = r"(?<![A-Za-z0-9-])"
STAR_MARKED_RE = re.compile(NUM_PREFIX + r"([0-9][0-9,]*\.?[0-9]*)\s*([kK])?\s*★")
STAR_WORD_RE = re.compile(NUM_PREFIX + r"([0-9][0-9,]*\.?[0-9]*)\s*([kK])?\s*stars\b")
FORK_WORD_RE = re.compile(NUM_PREFIX + r"([0-9][0-9,]*\.?[0-9]*)\s*([kK])?\s*forks\b")
SKILL_WORD_RE = re.compile(NUM_PREFIX + r"([0-9][0-9,]*\.?[0-9]*)\s*([kK])?\s*skills\b")
ATTR_RE = re.compile(r"(measured|brief says|said|reported|task brief|at race week|at race time|same[- ]?week)", re.I)
YEAR_RE = re.compile(r"^(19|20)\d{2}$")


def load_register(path):
    import yaml
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_index(reg):
    aliases = []
    for entry in reg.get("tracked", []) + reg.get("repos", []):
        rid = entry["id"]
        for a in entry.get("aliases", []) + [entry.get("repo", "")]:
            a = (a or "").strip().lower()
            if a:
                aliases.append((a, rid))
    aliases.sort(key=lambda t: -len(t[0]))  # longest first
    measurements = {}
    for m in reg.get("measurements", []):
        measurements.setdefault(m.get("repo"), []).append(m["value"])
    return aliases, measurements


def norm(value_str, k):
    v = value_str.replace(",", "").replace("~", "").replace("≈", "").strip()
    try:
        f = float(v)
    except ValueError:
        return None
    if k:
        f *= 1000.0
    if not k and YEAR_RE.match(v):
        return None
    return int(round(f))


def within(expected, found, entry):
    if entry.get("tolerance_abs") is not None:
        return abs(found - expected) <= entry["tolerance_abs"]
    pct = entry.get("tolerance_pct", 5)
    return abs(found - expected) <= max(1, expected * pct / 100.0)


def strip_ranges_floors(text):
    return FLOOR_RE.sub("", RANGE_RE.sub("", text))


def find_aliases(line_lower, aliases):
    hits = []
    for alias, rid in aliases:
        idx = line_lower.find(alias)
        if idx != -1:
            hits.append((idx, alias, rid))
    # drop aliases whose span is covered by a longer matching alias
    # (e.g. "asd-ste100-skill" inside "hakimzulkufli/asd-ste100-skills")
    kept = []
    for h in sorted(hits, key=lambda t: (-len(t[1]), t[0])):
        idx, alias, rid = h
        span = (idx, idx + len(alias))
        covered = any(
            a_idx <= idx and idx + len(alias) <= a_idx + len(a_alias)
            for a_idx, a_alias, _ in kept
        )
        if not covered:
            kept.append(h)
    kept.sort(key=lambda t: t[0])
    return kept


def nearest_repo(hits, token_idx):
    """Nearest alias strictly BEFORE the token; no fallback to aliases after
    (a number after an unrelated repo name must resolve via derived/unique)."""
    before = [h for h in hits if h[0] <= token_idx]
    if before:
        # dedupe by start index, keep the longest alias (asd-ste100-skills
        # must win over asd-ste100-skill)
        by_idx = {}
        for h in before:
            idx, alias, rid = h
            if idx not in by_idx or len(alias) > len(by_idx[idx][1]):
                by_idx[idx] = h
        last_idx = max(by_idx)
        return by_idx[last_idx][2]
    return None


def resolve_entry(reg, rid):
    for e in reg.get("tracked", []) + reg.get("repos", []):
        if e["id"] == rid:
            return e
    return None


def derived_values(reg):
    return {d["id"]: d for d in reg.get("derived", [])}


DERIVED_WINDOW_BEFORE = 40  # chars before the phrase the claim number may sit
DERIVED_WINDOW_AFTER = 60   # chars after the phrase the claim number may sit


def derived_match(reg, line_lower, found, field, out, filepath, lineno, token_idx):
    """Position-aware derived-claim check.

    A numeric token counts as a derived claim only when it sits NEAR the claim
    phrase on the line (within DERIVED_WINDOW_BEFORE/AFTER). Summary lines such
    as "Total ≈ 228★ across all attempts (31 repos)" are therefore NOT read as
    largest-repo claims, while real ones ("largest active repo has 21★") still
    are. When several phrases' windows contain the token, any matching value
    passes; only if no near phrase matches does the token fail (reported as
    derived drift with the actual found value). Tokens near no phrase fall
    through to unique-match / unresolved — bare roundings ("31k★") cannot hide
    behind an unrelated phrase on the same line.
    """
    plain = line_lower.replace("*", "")
    token_plain = len(line_lower[:token_idx].replace("*", ""))
    near = []  # (phrase, entry, phrase_idx) whose window contains the token
    for d in reg.get("derived", []):
        for ph in d.get("phrases", []):
            ph_idx = plain.find(ph)
            if ph_idx == -1:
                continue
            if ph_idx - DERIVED_WINDOW_BEFORE <= token_plain <= ph_idx + len(ph) + DERIVED_WINDOW_AFTER:
                near.append((ph, d, ph_idx))
    if not near:
        return False
    for _ph, d, _idx in near:
        if within(d["value"], found, d):
            return True
    ph, d, ph_idx = min(near, key=lambda t: abs(t[2] - token_plain))
    out.append(f"FAIL {filepath}:{lineno} derived {d['id']} (line has {ph}) {found}: expected ~{d['value']}")
    return True


def check_token(reg, measurements, line_lower, hits, found, field, attributed,
                token_idx, filepath, lineno, out):
    rid = nearest_repo(hits, token_idx)
    if attributed:
        # historical quote: resolve against ANY measurement first, then normal
        for vals in measurements.values():
            if found in vals:
                return
    entry = resolve_entry(reg, rid) if rid else None
    if field == "skills" and entry is not None and "skills" not in entry:
        return  # internal/design count (e.g. "~60 skills" with a tool alias) — out of scope
    if entry is not None and field in entry and entry.get(field) is not None:
        if not within(entry[field], found, entry):
            out.append(f"FAIL {filepath}:{lineno} {field} {found} -> repo {entry['id']}: expected {entry[field]}")
        return
    # no usable alias: derived claim?
    if derived_match(reg, line_lower, found, field, out, filepath, lineno, token_idx):
        return
    # unique match fallback
    matches = unique_match(reg, found, field)
    if len(matches) == 1:
        return
    if len(matches) > 1:
        out.append(f"FAIL {filepath}:{lineno} {field} {found}: ambiguous ({', '.join(matches)}) — name the repo")
        return
    out.append(f"FAIL {filepath}:{lineno} {field} {found}: unresolved (not in numbers.yaml)")


def unique_match(reg, found, field="stars"):
    matches = []
    for e in reg.get("tracked", []) + reg.get("repos", []):
        if field in e and e.get(field) is not None and within(e[field], found, e):
            matches.append(e["id"])
    return matches


def alias_dominates_cell(alias, cell_lower):
    """True when the alias is cell-dominant: it equals the cell's whole content
    (after markdown stripping) or is the repo-name part of an owner/repo path.
    A comma-separated list (e.g. docs/DOMAINS.md backtick-quoted skill names) is
    never a repo cell even when an alias appears inside one of its items."""
    if "," in cell_lower:
        return False
    plain = cell_lower.strip().strip("`*~≈ ").strip()
    if plain == alias:
        return True
    if "/" in plain:
        return plain.rsplit("/", 1)[-1] == alias
    return False


def scan_file(reg, aliases, measurements, filepath, out):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as exc:
        out.append(f"FAIL {filepath}: cannot read ({exc})")
        return
    rel = os.path.relpath(filepath, REPO_ROOT)
    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        stripped = strip_ranges_floors(raw)
        line_lower = stripped.lower()
        hits = find_aliases(line_lower, aliases)
        is_table = line.lstrip().startswith("|")

        # table rows: first PURE-numeric cell after a cell-dominant alias cell
        # = star column (alias must BE the cell, not a substring of a list item)
        if is_table and hits:
            cells = [c.strip() for c in line.split("|")]
            for idx, cell in enumerate(cells):
                cell_lower = cell.lower()
                hit_here = [h for h in hits if h[1] in cell_lower]
                if not hit_here:
                    continue
                # cell-dominant only: alias must BE the cell (owner/repo path or
                # alias == cell after markdown stripping). An alias substring
                # inside a comma-separated skill-name list (docs/DOMAINS.md
                # inventory rows) is not a repo cell; see N49/N50 fixtures.
                hit_here = [h for h in hit_here if alias_dominates_cell(h[1], cell_lower)]
                if not hit_here:
                    continue
                # most specific alias in this cell wins (e.g. ai4space over LunCoSim)
                hit_here.sort(key=lambda h: -len(h[1]))
                nxt = None
                for j in range(idx + 1, len(cells)):
                    c = cells[j].strip().strip("*~≈ ,")
                    if c and not re.fullmatch(r"[-–—]+", c):
                        nxt = c
                        break
                if nxt is None:
                    continue
                m = re.match(r"([0-9][0-9,]*\.?[0-9]*)\s*([kK])?\s*(★)?$", nxt)
                if not m:
                    continue  # cell has words (e.g. "818 skills, 34 domains") -> not the star column
                found = norm(m.group(1), m.group(2))
                if found is None:
                    continue
                rid = hit_here[0][2]
                entry = resolve_entry(reg, rid)
                if entry is not None and "stars" in entry and entry["stars"] is not None:
                    if not within(entry["stars"], found, entry):
                        out.append(f"FAIL {rel}:{lineno} stars {found} -> repo {entry['id']} (table row): expected {entry['stars']}")
                else:
                    out.append(f"FAIL {rel}:{lineno} stars {found}: repo {rid} not in register")
                break

        # marked tokens (position-aware)
        for pattern, field in ((STAR_MARKED_RE, "stars"), (STAR_WORD_RE, "stars"),
                               (FORK_WORD_RE, "forks"), (SKILL_WORD_RE, "skills")):
            for m in pattern.finditer(stripped):
                found = norm(m.group(1), m.group(2))
                if found is None:
                    continue
                if field == "skills" and (found < 10 or not hits):
                    continue  # internal/context-sensitive counts without a repo
                if field == "skills" and nearest_repo(hits, m.start()) is None:
                    continue  # internal target count, no repo attribution
                # aggregate noise descriptor ("noise, ~0★") and internal targets
                # ("≥500★") are out of scope
                if found < 5 and "noise" in line_lower:
                    continue
                pre = raw[max(0, m.start() - 40):m.start()]
                if "≥" in pre or "target" in line_lower:
                    continue
                token_idx = m.start()
                pre120 = raw[max(0, m.start() - 120):m.start()]
                post60 = raw[m.end():m.end() + 60]
                attributed = bool(ATTR_RE.search(pre120) or ATTR_RE.search(post60))
                check_token(reg, measurements, line_lower, hits, found, field,
                            attributed, token_idx, rel, lineno, out)


def iter_files(roots):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            if any(ex in dirpath for ex in EXCLUDED_DIRS):
                continue
            for fn in sorted(filenames):
                if fn.endswith((".md", ".html", ".txt")):
                    full = os.path.join(dirpath, fn)
                    if any(ex in full for ex in EXCLUDED_DIRS):
                        continue
                    yield full


def main():
    reg = load_register(os.environ.get("NUMBERS_YAML", DEFAULT_YAML))
    aliases, measurements = build_index(reg)
    roots = sys.argv[1:] or [os.path.join(REPO_ROOT, r) for r in DEFAULT_ROOTS]
    out = []
    scanned = 0
    for fp in iter_files(roots):
        scan_file(reg, aliases, measurements, fp, out)
        scanned += 1
    for line in out:
        print(line)
    if out:
        print(f"FAIL brief-audit: {len(out)} drift(s) in {scanned} file(s) — reconcile or register in numbers.yaml")
        return 1
    print(f"PASS brief-audit: all quoted numbers resolve against numbers.yaml ({scanned} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
