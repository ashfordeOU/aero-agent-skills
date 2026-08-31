# Attestation Gate Scripts + Number Hygiene — Design (2026-08-31)

Status: design settled; implementation via TDD (see plans/2026-08-31-attestation-gates.md).
Owner: Ops Manager. Milestone: 09-07 part 1 (attestation scripts + number hygiene; legal stack is a separate turn).

## Problem

Every published number must be replayable same-day (command + timestamped output + exit code),
and every quoted number in repo docs must agree with a canonical register. Today:
- K-Dense stars are quoted as 31.9k (brief 09), 38.0k/37,955 (brief 01) while live is 39,111
  (task baseline 2026-08-31; live API this run: 39,171).
- No canonical number register exists; no audit gate; no star snapshot; no content-policy sweep.
- Joint/CEO phase-1 reports (development/builds) are already reconciled (39,111 / 31,700 / 22).

## Design

### 1. ops/automation/numbers.yaml — canonical register (single source of truth)
Sections:
- `tracked:` repos verified LIVE by number-snapshot.sh. Expected value + tolerance
  (pct for large repos, abs for small). Canonical baseline 2026-08-31:
  - K-Dense-AI/scientific-agent-skills stars 39111 (tol 1%)
  - mukul975/Anthropic-Cybersecurity-Skills stars 31700 (tol 1%)
  - devideamax/aerospace-team stars 21 (abs 1)
  - ajhcs/mbse-agents stars 22 (abs 1)
- `derived:` whitespace claims:
  - largest_aerospace_repo = 22 (derived from live max(ajhcs, devideamax))
  - total_aerospace_stars = 228 (register claim, source brief 09; not re-derivable from
    the 4 tracked repos alone — informational, gated by tolerance 10%)
- `repos:` every other quoted repo (stars/forks/skills, value = live 2026-08-31 where the
  repo exists; `verified: false` + source for the 404s: christophacham/agent-skills-library,
  IO-Aerospace-software-engineering/mcp-server, FrontierAgent, halofy).
- `scope:` documented in TEST.md — audit gates star/fork/skill-count figures that are
  marked (★/k★/stars/forks/skills) or headline numbers on a repo line; ranges (N–M) are
  self-consistent and excluded; attributed historical measurements ("measured …") are
  cited-source quotes and excluded; internal targets (500–2,000★, €10K MRR) excluded.

### 2. ops/automation/number-snapshot.sh — live GitHub stars snapshot
- Reads `tracked` + `derived.largest_aerospace_repo` from numbers.yaml.
- Calls `gh api repos/{repo} --jq .stargazers_count` for each tracked repo (gh authed as
  arjun-0077). No silent fallback: API failure → non-zero exit with clear message.
- Writes timestamped snapshot JSON to ops/automation/state/stars-snapshot-*.json
  (evidence, committed per attestation doctrine).
- Derives largest_aerospace_repo = max(live ajhcs, live devideamax); checks vs 22.
- Exit 0 iff all tracked live values within expected range AND largest matches; else
  exit 1 with per-repo diff (expected vs found).
- `--offline`: uses newest committed snapshot instead of the network; validates snapshot
  values against the register; exit 1 with clear message if no snapshot exists.
  Documented — never silent drift.

### 3. ops/automation/brief-audit.sh — doc-vs-register audit
- Engine: ops/automation/number_audit.py (python3 + PyYAML, deterministic, no LLM).
- Scans research/, marketing/, development/, docs/, README.md (per task scope).
- For each line, when a register repo alias is present, every star/fork/skill figure on the
  line (marked tokens ★/k★/stars/forks/skills, plus the first bare number ≥1000 after the
  alias = headline star cell, excluding 4-digit years) must resolve to that repo's register
  value within tolerance. Derived phrases (total/largest) resolve via derived section.
- Token that resolves to nothing → FAIL unresolved; value mismatch → FAIL with diff
  (file, line, expected, found). Exit 1 with all diffs; exit 0 clean.
- This FORCES the K-Dense split fix in briefs 01, 09, 00-CEO-REPORT (md+html), joint/CEO
  reports, visual report, marketing content note, briefs 04/10/11.

### 4. ops/automation/content-policy-sweep.sh — red-flag terms
- Patterns from research/briefs/06-legal-export-control.md §8.3.6/§8.3.9 + task:
  ITAR-compliant/ITAR compliant/ITAR-certified/ITAR certified, EAR-compliant,
  export-compliant, certified-for-flight / FAA-certified / EASA-certified /
  DO-178C-certified (unapproved certification claims), CLASSIFIED/SECRET//NOFORN/
  CONTROLLED UNCLASSIFIED/CUI markings, P/N+digits / NSN / CAGE part-number patterns,
  military-platform-parameter phrases. README compliance banner (06 §8.4) is allowed
  (negated "does not contain ITAR/EAR-controlled" — the pattern list targets claims,
  not the banner's disclaimer).
- Scans publishable content (README.md, marketing/, docs/, development/builds/, skills/,
  support/); research/ briefs are internal evidence and exempt (the policy doc itself
  legitimately discusses the terms).
- Exit 0 clean; exit 1 listing file:line for each hit. Wired into CI.

### 5. Makefile `make attest`
`attest: number-snapshot brief-audit content-policy-sweep` where number-snapshot runs
`--offline` (deterministic at rest; the live snapshot is a separate cron/manual step and
runs before the committed evidence). CI: .github/workflows/attest.yml runs
`make validate && make attest` on push/PR (private repo; never public).

### 6. TDD
- Negative fixtures first (ops/automation/test/): a brief with "38.0k★" must exit 1;
  a policy file with "ITAR-compliant" must exit 1; snapshot with expected=100 vs live
  must exit 1; --offline with no snapshot must exit 1. Document commands + observed
  outputs in ops/automation/TEST.md. Then green at rest: make validate + make attest exit 0.

## Decisions / gates
- Tracked tolerance 1% (K-Dense/cyber) and abs 1 (devideamax/ajhcs): catches 31.9k, 38.0k,
  31.2k, 31k, 37,955, 16★, 13★, 19★; allows 39.1k/31.7k and live drift (39,171 vs 39,111).
- Non-tracked repos: tolerance 5% (or abs 2 small) — dated measurements resolve;
  hashicorp 804 vs live 855 and LunCoSim 97 vs 105 exceed tolerance → docs fixed to live.
- Repo 404s are registered with verified:false + source; docs keep the documented value.
- "Never prosa away a number": stale figures are FIXED (reconciled to canonical with a
  "live as of 2026-08-31" note), never deleted without replacement.
