# WAVE-38 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-05 ~08:05 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-37 close
baseline.
Baseline (wave-37 close, CEO gate PASSED 9.68/10 2026-09-04 ~19:12 UTC — fresh
CEO replay at 4abfc55d: make validate 5/5 1028/1028 + make attest 3/3 replayed
by CEO at rest, 0 tracked findings; private remote == 4abfc55d == HEAD; public
ashfordeOU main == a514d587 sync verified with CI attest + release-on-milestone
SUCCESS):
**506 leaves · 85 packs · 12 families · 1028 router tasks · 30 standards**
(518 SKILL.md tracked = 506 leaves + 12 routers). Ratings ledger 506 rows.
Corpus eval/hit1-corpus.yaml = 1028.
Per-family leaf counts (wave-37 close, docs/metrics.json verified 2026-09-05):
**systems-engineering-safety 36 + aerodynamics 36 (tied smallest — SES vein
BROKE OPEN waves 36-37: ica-cmr-ali-classification (w36) → airworthiness-
directive-compliance + type-certificate-data-sheet (w37) all landed in
SES/continued-airworthiness — the airworthiness-management sub-area is a LIVE
seam, NOT saturated; wave-37 lesson #1 says probe that sub-area HARD before
re-declaring density) · AERO dense receipt wave-37 holds (whirl-flutter
declined on model-fidelity — do not re-litigate; assess only clean genuine
gaps)** · **propulsion 38 (PROP +1 wave-37 subsonic-inlet-recovery; assess
remaining rocket/gas-turbine deterministic sizing)** · **flight-test-operations
41 · gnc-autonomy 41 (41-count — re-probe only genuine gaps)** · **avionics 43
· flight-mechanics 42 · structures 43 (AV +1 wave-37 holding-pattern-entry; FM
saturated receipt wave-37; STRUCT assess)** · **cross-cutting 45 ·
space-systems 45 (CC +1 wave-37 grubbs-outlier-test; SPACE +1 wave-37
geostationary-station-keeping; assess)** · **manufacturing-quality 47 ·
vehicle-design 49 largest last (MQ +2 wave-37; VD +2 wave-37; probe ONLY if
smaller families provably exhausted; smallest-first doctrine)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **SES 36 + AERO 36 first** — SES/continued-airworthiness is
  the proven live seam (wave-37 lesson #1: when a wave breaks a saturation
  streak in a sub-area, probe that sub-area HARD next wave before re-declaring
  density — candidates to probe: MRB disposition logic, certification
  maintenance requirements, airworthiness limitations section (ALS), type
  certificate data upkeep, reliability-centered maintenance program logic —
  ONLY clean non-overlapping deterministic gaps; read the sibling fence tables
  first). **Then propulsion 38** (assess rocket/gas-turbine remaining
  deterministic sizing — subsonic-inlet landed wave-37, inlet/rocket veins
  productive). **Then the 41-count — flight-test-operations 41 +
  gnc-autonomy 41** (re-probe only genuine gaps). **Then avionics 43 +
  flight-mechanics 42 + structures 43.** **Then cross-cutting 45 +
  space-systems 45 + manufacturing-quality 47.** **Then vehicle-design 49
  largest last** (only if smaller families provably exhausted). Probe only
  genuine non-overlapping gaps; never open a duplicate.
- **PROBE RULE (wave-37 lesson #2):** "0 owners" is necessary but not
  sufficient — a zero-owner grep can still collide with a sibling that CLAIMS
  the function. Read the sibling fence/claim table before accepting any
  zero-owner grep as a genuine gap.
- **EM-DASH HYGIENE (standing):** em dashes in skills/ = 0 at wave-37 close
  (REAL count). THIS WAVE: write ALL new leaves em-dash-free (hyphens /
  restructured prose). At prep and at close run `git grep -l "—" -- 'skills/'`;
  if nonzero, add ONE mechanical cleanup commit; ALWAYS report the REAL em-dash
  count in wave38-state.md — never copy a receipt that is not true at the HEAD
  you are on.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave38-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter, "Use when you must …" gate-2 clause style) +
**FULL HOUSE BODY: Workflow → Worked example → Pitfalls (3-6 leaf-specific
bullets derived from the leaf's own content/tests — NEVER invent) → Behavior
contract (gate 3) → Compliance.** Never use "classified" as a verb in prose
(content-policy sweep trips CLASSIFIED; use "categorized"). +
scripts/<leaf>_logic.py (stdlib only, portable imports — sibling
os.path.dirname(os.path.abspath(__file__)) pattern, NO machine-local absolute
paths; logic files NEVER start with test_; **UNDERSCORE script filenames —
wave-38 kit lesson: wave-37 saw 3 of 10 builders default to hyphenated logic
filenames; gate-valid but inconsistent with the 500-leaf convention — use
underscores in script filenames**) + scripts/test_<leaf>.py (offline
unittest, asserts REAL module outputs) + eval fragment
eval/hit1-wave38-<leaf>.yaml (2 corpus tasks with distinctive hyphenated
tokens) + eval/skill-eval/<leaf>.json value-delta record + ratings ledger row
appended IN-TURN at ≥9.5 (rows 507+, header 506→506+N at close). references/ +
assets/ only when the body inlines long external content.

**CREATION GATE (run BEFORE every leaf commit, exit 0 required — founder
2026-09-04):** `bash scripts/leaf-create-gate.sh <leaf-path>` — checks
structure, naming, test pass, pycache, content policy, corpus, eval. FAIL →
fix in-turn, re-run, then commit. Full builder checklist:
MAINTENANCE_AND_HANDOVER.md section 5a.

## Operational rules (ALL prior-wave lessons — non-negotiable)
1. **TURN-ALIVE (wave-24R rule, operational):** NEVER emit a text-only response
   while delegations are live or work remains. Every turn continues with real
   tool calls (poll transcripts/state/prep/gates) until close-out. The ONLY
   permitted text-only response is the final close-out report.
2. **API health first:** check DeepSeek API before fan-out; CAP 3-4 concurrent
   builders per batch (one agent per leaf — PARALLEL-AGENT doctrine).
3. **Quiet-hours gate-check before EACH batch:**
   `python3 ~/.hermes/scripts/quiet-hours-gate.py --check` (exit 0 = go; exit 2/3
   = stop/queue). Window 20:00-08:00 UTC — no work in the window. Dispatch is
   ~08:05 UTC — you have ~12h of build daylight to 20:00 UTC. Target: core
   close-out well before 20:00 UTC (prior waves' full cycle ~1-2h; you have
   room for a full 12-16 leaf wave). **If close-out is not reached by ~19:30
   UTC: STOP CLEANLY — commit what landed (≥10 landed = PASS), push PRIVATE +
   sync if a full close chain exists, queue the remainder for 08:00 UTC
   2026-09-06.** Pre-quiet guard: no new subagents after ~19:30 UTC.
4. **Anti-hang protocol (wave-25..37 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies. If a `terminal`
   tool call exceeds ~7 min it may time out (wave-35 tail: 420s timeout at
   close, session recovered); treat as timed out, verify state, continue — do
   not sit silent.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 507+). No backfilling at close. Keep the
   re-read-max+1 rule. Final rows must be contiguous 507-506+N.
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31..37 class): after any commit, verify
   `git ls-tree`/status that YOUR leaf's six artifacts AND your ledger row are
   on the HEAD chain; a swept file/row is not lost if you re-commit your own
   paths.
7. **Hit@1 no-task-stealing check BEFORE close-out:** after corpus merge,
   re-run make validate; ZERO pre-existing tasks may be stolen by a new leaf
   description; fence descriptions against siblings (distinctive hyphenated
   tokens — wave-36/37 lesson: embed 1-2 of the leaf's own hyphenated tag
   tokens in corpus queries where a sibling holds a generic single-word
   fragment). Run the PRE-MERGE routing simulation
   (state/wave38-sim-merge.py on corpus + on-disk fragments BEFORE the real
   merge) so no rewording is needed.
8. **Corpus:** 1028 → 1028+2N (merge via state/wave38-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one
   table row + one routing-guidance bullet per family touched), router
   descriptions ≤1024 chars. Router parity check (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (1028+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
   ALL REQUIRED PASS · make value-delta 10/10 ≥0.2 · visuals-check PASS
   (numbers only via make visuals) · router descs ≤1024 · REPORT the real em
   dash count in skills/ (grep; 0 preferred — write em-dash-free, cleanup
   commit at prep/close if nonzero) · tree clean.
10. **Push PRIVATE only** (arjun-0077/aero-agent-skills, GITHUB_TOKEN_ARJUN,
    fast-forward, NO force) + ls-remote verify remote == HEAD. NO Ashforde, NO
    visibility flip. Then **publish-public.sh sync** (sanctioned path) + verify
    public HEAD + GitHub CI attest SUCCESS. Keep publish-public.sh fixes from
    2da34f0e (leaf-count regression guard) and eec11e34 (About refresh from the
    MIRROR post-push); do not revert. Concurrent automation may land
    local-only commits mid-wave (wave-30..37 class) — fast-forward below the
    wave commits, do not fight them; regenerate manifests at close.
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160`
    → verify SEND_EXIT=0.
12. **wave38-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons, REAL em-dash count) + commit + push PRIVATE. Then
    proc exit → CEO P5.2 WAVE-38 audit ≥9.5 → WAVE-39.

## Sequence
Prep (builder kit + 12-16 specs at ops/automation/state/wave38-specs/, commit)
→ batches of 3-4 → ≥10 landed → corpus merge + routers → ratings header →
gates FRESH → push PRIVATE + verify → publish-public sync + CI verify → GROUP
160 post → wave38-state.md → exit. If the window approaches before close-out:
stop cleanly, commit what landed, queue resume 08:00 UTC (per doctrine). No
founder contact (routine progress).
