# ops/automation — attestation gates (TEST.md)

Three deterministic scripts gate every quoted number and every publishable
claim before it ships (milestone 2026-08-31; design:
docs/superpowers/specs/2026-08-31-attestation-gates-design.md).

## Scripts

| Script | Job | Exit codes |
|---|---|---|
| `number-snapshot.sh [--live\|--offline]` | Live-verify `tracked` repos against GitHub API via `gh` (authed arjun-0077); offline re-checks newest snapshot against the register | 0 ok · 1 drift · 2 API failure (no silent fallback) |
| `brief-audit.sh [path...]` | Resolve every quoted number in repo docs against `numbers.yaml` (canonical register) | 0 clean · 1 drift/unresolved/ambiguous |
| `content-policy-sweep.sh [path...]` | Scan publishable content for ITAR/EAR compliance CLAIMS, certification claims, classified markings, part numbers (brief 06 §8.3.6/8.3.9) | 0 clean · 1 hit |

`make attest` runs all three at rest (snapshot offline); `make snapshot-live`
refreshes the evidence snapshot before committing. CI (`.github/workflows/attest.yml`)
runs `make validate && make attest` on push/PR.

## Audit scope (brief-audit.sh)

Scanned: `research/`, `marketing/`, `development/`, `docs/`, `README.md`.
Excluded (EXCLUDED_DIRS in number_audit.py):
- `development/builds/` — dated build snapshots of reports; renumbering them
  would falsify history (AGENTS.md supersede-not-delete). Living briefs carry
  the canonical values.
- `docs/superpowers/` — planning/meta docs whose stale values (38.0k★, 31.9k,
  16★ ...) are intentional examples of what the audit catches (the audit's own
  spec + fixture descriptions), not market claims.
- `research/peer-skill-repo-audit-2026-08-31.md` — dated snapshot of peer repo
  states measured earlier on 2026-08-31 (e.g. K-Dense 39,855★ at audit time);
  renumbering it would falsify the recorded measurement. Same class as
  `development/builds/` (supersede-not-delete).

Checked patterns: `N★` / `Nk★` / `N stars` / `Nk stars`, `N forks` / `Nk forks`,
`N skills` (with a repo alias on the line), the first pure-numeric cell after a
repo alias in a pipe-table row, and derived claims (total/largest phrases) —
position-aware: the number must sit NEAR the phrase (≤40 chars before, ≤60
after), so a `Total ≈ 228★ (31 repos)` summary line is never read as a
largest-repo claim. Excluded: ranges (`N–M`), floors (`N+`), 4-digit years,
dates, identifier-embedded numbers (SEP-2640), bare prose numbers without a
market marker, internal AeroSkills design figures (no repo alias), attributed
historical quotes (`measured N`, `brief says N`, `same week`) which resolve
against the register's `measurements` section.

Resolution: nearest preceding repo alias on the line wins; no alias → derived
phrase near the number → unique register match (multiple matches = FAIL
ambiguous, forcing the doc to name the repo).

## TDD evidence (observed exit codes, 2026-08-31)

`bash ops/automation/test/run-tests.sh` → **exit 0, ALL TESTS PASS (41/41)**

| Test | Assertion | Expected | Observed |
|---|---|---|---|
| N1 | snapshot live, fixture expected 100 vs live ~39k | exit 1 | 1 |
| N2 | snapshot offline without snapshot (never silent drift) | exit 1 | 1 |
| N3 | brief-audit flags stale K-Dense 38.0k (fixture) | exit 1 | 1 |
| N5 | brief-audit still flags largest-repo drift 19 vs 22 (fixture, post-tuning) | exit 1 | 1 |
| N4 | content-policy-sweep flags "ITAR-compliant" (fixture) | exit 1 | 1 |
| S.no-license | spec-lint flags missing license (fixture) | exit 1 | 1 |
| S.bad-license | spec-lint flags license != Apache-2.0 (fixture) | exit 1 | 1 |
| S.bad-compliance | spec-lint flags compliance not in enum (fixture) | exit 1 | 1 |
| S.standards-unknown | spec-lint flags standard not in standards-map (fixture) | exit 1 | 1 |
| S.gated-mismatch | spec-lint flags gated:false with unmarked gated standard (fixture) | exit 1 | 1 |
| S.gated-nonbool | spec-lint flags non-boolean gated (fixture) | exit 1 | 1 |
| S.no-metadata | spec-lint flags missing metadata.version (fixture) | exit 1 | 1 |
| S.empty-standards | spec-lint flags empty standards list (fixture) | exit 1 | 1 |
| G1 | snapshot live on real register | exit 0 | 0 |
| G2 | snapshot offline with snapshot present | exit 0 | 0 |
| G3 | brief-audit full repo (19 scanned files) | exit 0 | 0 |
| G4 | content-policy-sweep full repo | exit 0 | 0 |
| G5 | brief-audit summary line ("total ≈ 228 / 31 repos") is NOT a largest-repo false positive (fixture) | exit 0 | 0 |
| G6 | spec-lint gate on real skills tree (compliance flags enforced) | exit 0 | 0 |
| P1–P9 | pack_inventory: real-repo reports 'packs=9 skills=43' (9 family routers / 43 leaf skills), per-pack/per-domain counts, missing frontmatter + router + taxonomy negatives | 0/1 | 0/1 |
| N8 | stale-number guard flags stale counts in live marketing/ + docs/ (fixture; R3 adds 'five packs' + '3/3 corpus') | exit 1 | 1 |
| N9 | stale-number guard exempts dated plans/ (supersede-not-delete) | exit 0 | 0 |
| N12 | stale-number guard flags planted 68/1,360 in README.md + development/ (R4 root extension) | exit 1 | 1 |
| N13 | stale-number guard exempts qualified README planning-target line ('planning target, not a shipped count') | exit 0 | 0 |
| N14 | stale-number guard exempts dated development/builds/ reports | exit 0 | 0 |
| N15 | stale-number guard flags planted 27/9/36-class counts ('27 skills' ... '36 SKILL.md', R3 re-grade patterns) | exit 1 | 1 |
| N16 | stale-number guard exempts legit live vocabulary ('27 live sub-domain packs', '9 families', '43 leaf skills', '52 SKILL.md') | exit 0 | 0 |
| N17 | stale-number guard flags bare '9 packs' family mislabel | exit 1 | 1 |
| N10 | gated-set check flags stale gated-set/map-coverage count claims (fixture: 9 vs map 16, 5 gated vs 10) | exit 1 | 1 |
| N11 | gated-set check passes clean enumerations (fixture: 16 map, 10 gated) | exit 0 | 0 |
| G7 | stale-number guard on real repo (R4 patterns + R3 re-grade 27/9/36 class; roots: marketing/ + docs/ + development/ + README.md; harness-contract milestone records exempt) | exit 0 | 0 |
| G8 | gated-set check on real repo (no numeric count claims contradict standards-map.yaml) | exit 0 | 0 |

Fixtures: `test/fixture-tracked-wrong.yaml`, `test/fixture-brief-stale.md`,
`test/fixture-derived-stale.md`, `test/fixture-derived-summary.md`,
`test/fixture-policy-bad.md`, `test/fixture-spec-{no-license,bad-license,
bad-compliance,standards-unknown,gated-mismatch,gated-nonbool,no-metadata,
empty-standards}.md`, `test/fixture-stale-numbers/`,
`test/fixture-stale-plans-only/`, `test/fixture-stale-roots/` (README +
development plants), `test/fixture-stale-roots-qualified/` (README
planning-target qualifier), `test/fixture-stale-builds-only/` (dated
build report), `test/fixture-stale-27-9-36/` (marketing plants of the
27/9/36-class stale counts), `test/fixture-legit-27-9/` (live one-way
vocabulary: 27 live sub-domain packs, 9 families, 43 leaf skills,
52 SKILL.md), `test/fixture-stale-9packs/` (bare '9 packs' family
mislabel). Fixture comments keep numbers marker-free so only
the content line is scanned. The suite preserves and restores the
committed `state/` dir around its own live runs, so running it never
dirties the tree.

The suite covers the attestation scripts plus gate 1 spec-lint compliance
flags (S-series) and the at-rest gate (G6) — the extended frontmatter
enforcement of docs/harness-contract.md gate 1.

## At-rest green

```
make validate   → exit 0 (5/5 harness gates)
make attest     → exit 0 (snapshot offline + brief audit + content sweep)
git status      → clean (state/stars-latest.json committed as replayable evidence)
```
