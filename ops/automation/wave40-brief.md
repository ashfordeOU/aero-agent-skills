# WAVE-40 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-05 ~12:15 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-39 close
baseline.
Baseline (wave-39 close, CEO gate PASSED 9.68/10 2026-09-05 ~12:13 UTC — fresh
CEO replay at fb09a644: make validate 5/5 1088/1088 + make attest 3/3 + make
completeness ALL REQUIRED PASS, 0 tracked findings; private remote == fb09a644
== HEAD; public ashfordeOU main == 699904861 sync verified with CI attest +
release-on-milestone SUCCESS):
**536 leaves · 85 packs · 12 families · 1088 router tasks · 30 standards**
(548 SKILL.md tracked = 536 leaves + 12 routers). Ratings ledger 536 rows.
Corpus eval/hit1-corpus.yaml = 1088.
Per-family leaf counts (wave-39 close, docs/metrics.json verified 2026-09-05):
**systems-engineering-safety 39 (smallest, tied with AERO — wave-39 landed TWO
genuine arp4761a leaves: beta-factor-analysis (CCF quantification) +
failure-mode-criticality (rate-based C_m = beta·alpha·lambda·t; the RPN S·O·D
rating is fenced to manufacturing-quality/risk-management); the CEO-named
zonal/common-cause/particular-risk candidates ALREADY EXISTED at HEAD — the
arp4761a seam has now yielded 3 waves running (fault-tree-importance wave-38,
beta-factor + failure-mode-criticality wave-39); probe the WHOLE family again
with FRESH zero-owner greps + sibling fence reads — remaining safety-assessment
functions: zonal-safety-analysis reads as OWNED (verify), FMECA beyond
rate-based criticality (e.g. CA/FMES extension), uncertainty/sensitivity of FTA
results, maintenance-task analysis, operational-safety-assessment — ONLY clean
deterministic gaps)** · **aerodynamics 39 (wave-39 landed bow-shock-standoff in
high-speed; wave-38 broke the dense receipt twice (boundary-layer-separation,
flat-plate-skin-friction-heating) — probe boundary-layer/high-speed/aeroheating
veins for REMAINING clean gaps: e.g. turbulent flat-plate heating, shock
interactions, real-gas effects — do NOT re-litigate whirl-flutter / LFC / NLF /
turbulent-boundary-layer-integral (Head-entrainment closure constants
discontinuous — wave-39 fidelity decline, do not re-open without a clean
continuous closed form))** · **flight-test-operations 41 · gnc-autonomy 41
(41-count — saturated receipts reaffirmed waves 38-39 with proof; re-probe only
genuine gaps)** · **propulsion 42 (wave-39 +2: turbojet-cycle,
rocket-gravity-loss; assess remaining rocket/gas-turbine deterministic
sizing)** · **flight-mechanics 43 (wave-39 +1: propeller-range — breguet
propeller branch now owned; assess remaining performance/mechanics gaps)** ·
**structures 46 (wave-39 +1: laminate-plate-buckling; stringer-crippling
DECLINED twice on model fidelity — do not re-open)** · **avionics 46 (saturated
reaffirmed wave-39 with function-level proof; re-probe only genuine gaps)** ·
**space-systems 48 (wave-39 +2: gravity-gradient-stabilization,
synodic-launch-window; assess remaining ADCS/mission-design gaps)** ·
**manufacturing-quality 48 (effectively saturated wave-39 — Nelson-control-
chart-rules candidate NOT taken; probe only clean determinism)** ·
**vehicle-design 49 (untouched waves 37-39; NOT largest anymore — cross-cutting
54 is largest now; VD may be probed when all smaller families exhausted)** ·
**cross-cutting 54 (now the LARGEST family — grew +6 wave-39; probe LAST, only
if every smaller family is provably exhausted)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **SES 39 + AERO 39 first** (SES: probe the WHOLE family per
  wave-38 lesson #1 and wave-39 receipt — the arp4761a seam has yielded 3
  straight waves; candidates to assess FRESH against the live tree: remaining
  arp4761a functions + safety-assessment beyond what wave-39 landed — ONLY
  clean non-overlapping deterministic gaps; read the sibling fence tables
  first; the CEO-named list may again be STALE — probe receipts govern.
  AERO: boundary-layer/high-speed/aeroheating veins — ONLY clean genuine
  gaps). **Then the 41-count — flight-test-operations 41 + gnc-autonomy 41**
  (re-probe only genuine gaps). **Then propulsion 42 + flight-mechanics 43.**
  **Then structures 46 + avionics 46 + space-systems 48 +
  manufacturing-quality 48.** **Then vehicle-design 49** (permitted now that
  VD is no longer largest — cross-cutting 54 superseded it; probe ONLY genuine
  gaps). **Then cross-cutting 54 largest last** (only if every smaller family
  is provably exhausted). Probe only genuine non-overlapping gaps; never open
  a duplicate.
- **PROBE RULE (standing, wave-37 lesson #2):** "0 owners" is necessary but
  not sufficient — a zero-owner grep can still collide with a sibling that
  CLAIMS the function. Read the sibling fence/claim table before accepting any
  zero-owner grep as a genuine gap.
- **RECEIPTS OVER LISTS (wave-39 lesson #1):** probe briefs must be executed
  against the LIVE tree — wave-39's CEO-named SES candidates were stale (three
  already existed at HEAD). The wave plan follows the probe receipts, not the
  candidate list. Verify each named candidate EXISTS or DOES NOT at HEAD before
  spec'ing it.
- **EM-DASH HYGIENE (standing):** em dashes in skills/ = 0 at wave-39 close
  (REAL count). THIS WAVE: write ALL new leaves em-dash-free (hyphens /
  restructured prose). At prep and at close run `git grep -l "—" -- 'skills/'`;
  if nonzero, add ONE mechanical cleanup commit; ALWAYS report the REAL em-dash
  count in wave40-state.md — never copy a receipt that is not true at the HEAD
  you are on.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave40-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter, "Use when you must …" gate-2 clause
style) + **FULL HOUSE BODY: Workflow → Worked example → Pitfalls (3-6
leaf-specific bullets derived from the leaf's own content/tests — NEVER
invent) → Behavior contract (gate 3) → Compliance.** Never use "classified"
as a verb in prose (content-policy sweep trips CLASSIFIED; use "categorized").
+ scripts/<leaf>_logic.py (stdlib only, portable imports — sibling
os.path.dirname(os.path.abspath(__file__)) pattern, NO machine-local absolute
paths; logic files NEVER start with test_; **UNDERSCORE script filenames —
standing kit lesson**) + scripts/test_<leaf>.py (offline unittest, asserts
REAL module outputs) + eval fragment eval/hit1-wave40-<leaf>.yaml
(2 corpus tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json
value-delta record + ratings ledger row appended IN-TURN at ≥9.5 (rows 537+,
header 536→536+N at close). references/ + assets/ only when the body inlines
long external content.

**VALUE-DELTA SAMPLER RULE (wave-38 lesson #3):** the value-delta sampler
recomputes eval records from TEST FILE term presence, NOT the committed JSON.
Pure-math contract tests that do not reference the SKILL.md workflow can
compute delta 0.0 and FAIL the gate even when the committed record says 0.5.
Reference the SKILL.md workflow steps NATURALLY in the test docstring (name
the workflow steps the test exercises) so the sampler sees the terms.

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
   ~12:15 UTC — you have ~7.7h of build daylight to 20:00 UTC. Target: core
   close-out well before 20:00 UTC (prior waves' full cycle ~1.5-2h). **If
   close-out is not reached by ~19:30 UTC: STOP CLEANLY — commit what landed
   (≥10 landed = PASS), push PRIVATE + sync if a full close chain exists, queue
   the remainder for 08:00 UTC 2026-09-06.** Pre-quiet guard: no new subagents
   after ~19:30 UTC.
4. **Anti-hang protocol (wave-25..39 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies. If a `terminal`
   tool call exceeds ~7 min it may time out; treat as timed out, verify state,
   continue — do not sit silent. **STEER TIMING (wave-38 lesson #4): expect one
   builder stall per ~4 builders; a single steer resolves it — check quiet
   transcripts at ~8-10 minutes, not 15+.**
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 537+). No backfilling at close. Keep the
   re-read-max+1 rule. Final rows must be contiguous 537-536+N. **LEDGER RACE
   (wave-39 lesson #3): concurrent appends scramble physical row order even
   when numbers stay contiguous — normalize the physical row order to ascending
   at close before the header update.**
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31..39 class): after any commit, verify
   `git ls-tree`/status that YOUR leaf's six artifacts AND your ledger row are
   on the HEAD chain; a swept file/row is not lost if you re-commit your own
   paths. **Concurrent mid-wave automation (desc frontload + visuals regen +
   its own publish-public sync) is now an EXPECTED wave class (wave-38 lesson
   #2): recover cleanly with remainder commits, never fight it; re-run make
   visuals at close regardless.**
7. **Hit@1 no-task-stealing check BEFORE close-out:** after corpus merge,
   re-run make validate; ZERO pre-existing tasks may be stolen by a new leaf
   description; fence descriptions against siblings (distinctive hyphenated
   tokens — standing lesson: embed 1-2 of the leaf's own hyphenated tag tokens
   in corpus queries where a sibling holds a generic single-word fragment). Run
   the PRE-MERGE routing simulation (state/wave40-sim-merge.py on corpus +
   on-disk fragments BEFORE the real merge) so no rewording is needed.
8. **Corpus:** 1088 → 1088+2N (merge via state/wave40-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one
   table row + one routing-guidance bullet per family touched), router
   descriptions ≤1024 chars. Router parity check (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (1088+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
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
    local-only commits mid-wave (wave-30..39 class) — fast-forward below the
    wave commits, do not fight them; regenerate manifests at close.
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160`
    → verify SEND_EXIT=0.
12. **wave40-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons, REAL em-dash count) + commit + push PRIVATE. Then
    give the final close-out report (text-only allowed NOW).
