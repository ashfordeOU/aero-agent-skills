# WAVE-43 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-06 ~11:10 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-42 close
baseline.

Baseline (wave-42 close, CEO gate PASSED 9.6/10 2026-09-06 ~11:00 UTC — fresh
CEO replay at HEAD 71e83fda: 581 leaves / 581 ledger rows 0 gap / corpus 1178 /
tree clean / em dashes 0 / attest 3/3 PASS; private remote == 71e83fda == HEAD
ls-remote verified; public ashfordeOU main == 358c5824 with CI attest +
release-on-milestone SUCCESS — sync carried f42208e9+4819dc97 via the hourly
automation):
**581 leaves · 85 packs · 12 families · 1178 router tasks · 30 standards**
(593 SKILL.md tracked = 581 leaves + 12 routers). Ratings ledger 581 rows.
Corpus eval/hit1-corpus.yaml = 1178.
Per-family leaf counts (wave-42 close, verified this dispatch):
**flight-test-operations 44 (TIED SMALLEST — wave-42 +1
rotorcraft-autorotation-flight-test; 13/14 functions were saturated at 43 with
the measurement side as the ONE genuine gap, which LANDED; whole-family fresh
probe required — re-probe only clean deterministic measurement/planning gaps,
expect heavy saturation)** · **propulsion 44 (TIED SMALLEST — wave-42 +1
brayton-optimum-pressure-ratio; scramjet-cycle CLOSED DEFINITIVELY (do NOT
re-open); wave-39 declines stood (drag loss, PPT, resistojet, pressurant,
ablative, turboshaft/engine-matching/axial-stage); rocket-nozzle-divergence-loss
flagged MARGINAL wave-42 and NOT planned — probe rocket/gas-turbine sizing
FRESH with receipts)** · **gnc-autonomy 45 (wave-42 +3: gnss-carrier-smoothing,
lqg-design, bearing-only-localization — the whole-family fresh probe found
clean deterministic gaps in navigation + optimal-control; tdoa-positioning
declined (fence-adjacent to manufacturing-quality acoustic-emission planar
hyperbolic location), kept in reserve; NOT saturated — probe navigation/
optimal-control/estimation veins FRESH)** · **aerodynamics 46 (wave-42 +3:
shock-tube, thin-airfoil-section-theory, compressible-couette-flow — the dense
receipt has yielded SIX straight waves; wave-42 declines stood: aileron-reversal
OWNED by flight-mechanics, van-Driest/Chapman-Rubesin dup, Fay-Riddell dup,
Falkner-Skan ODE, law-of-the-wall fenced, Taylor-Maccoll ODE, MOC marching;
probe FRESH only clean closed-form gaps)** · **avionics 46 (saturated reaffirmed
wave-42; probe only clean determinism)** · **flight-mechanics 47 (wave-42 +1:
rotorcraft-main-rotor-sizing; assess remaining rotorcraft/fixed-wing
performance-mechanics gaps FRESH)** · **systems-engineering-safety 47 (wave-42
+2: fault-tree-quantification, reliability-allocation — arp4761a seam has now
yielded SIX straight waves; reliability-prediction-parts-count DECLINED
DEFINITIVELY wave-42 (no MIL-HDBK-217/Telcordia id in standards-map.yaml, a
fabricated generic base-rate table violates verified-anchor discipline, residual
series-sum logic owned by reliability-block-diagram +
maintainability-prediction) — reopen ONLY if MIL-HDBK-217F is added to
standards-map.yaml; probe remaining safety-assessment/arp4761a functions
FRESH)** · **manufacturing-quality 48 (saturated reaffirmed wave-42; probe only
clean determinism)** · **space-systems 52 (saturated reaffirmed wave-42; probe
only clean determinism)** · **structures 53 (wave-42 +2: shear-center-analysis,
shrink-fit-analysis; probe remaining solid-mechanics/instability gaps FRESH)** ·
**cross-cutting 54 (saturated/default-CLOSED reaffirmed wave-42; probe LAST)** ·
**vehicle-design 55 (LARGEST — wave-42 +1 landing-gear-layout; probe LAST, only
if every smaller family is provably exhausted)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority per
  doctrine: **flight-test-operations 44 + propulsion 44 first** (TIED smallest —
  FTO: whole-family FRESH probe per wave-38 lesson #1; expect saturation after
  wave-42's 13/14 reaffirm + measurement-side land; only genuine gaps. PROP:
  scramjet CLOSED — probe other rocket/gas-turbine sizing only). **Then
  gnc-autonomy 45** (probe navigation/optimal-control/estimation veins FRESH —
  wave-42 proved the family NOT saturated with 3 clean lands). **Then the
  46-count — aerodynamics 46 + avionics 46** (AERO: probe boundary-layer/
  high-speed/aeroheating veins FRESH per wave-41/42 receipts — ONLY clean
  closed-form gaps; read sibling fence tables first. AV: saturated — probe only
  clean determinism). **Then flight-mechanics 47 + systems-engineering-safety
  47** (FM: rotorcraft/fixed-wing performance-mechanics gaps FRESH. SES: probe
  arp4761a seam + remaining safety-assessment functions FRESH — receipts
  govern, CEO-named lists may be stale). **Then manufacturing-quality 48.**
  **Then space-systems 52 + structures 53.** **Then cross-cutting 54 +
  vehicle-design 55 largest last** (only if every smaller family is provably
  exhausted). Probe only genuine non-overlapping gaps; never open a duplicate.
- **PROBE RULE (standing, wave-37 lesson #2):** "0 owners" is necessary but
  not sufficient — a zero-owner grep can still collide with a sibling that
  CLAIMS the function. Read the sibling fence/claim table before accepting any
  zero-owner grep as a genuine gap.
- **RECEIPTS OVER LISTS (wave-39 lesson #1, held waves 40-42):** probe briefs
  must be executed against the LIVE tree. The wave plan follows the probe
  receipts, not the candidate list. Verify each named candidate EXISTS or DOES
  NOT at HEAD before spec'ing it.
- **SPEC-ENGINEER PROMPTS (wave-40 lesson #1 + wave-42 lesson, HELD):**
  long-context spec-engineer prompts on this model stall with in-flight
  model-response hangs. A COMPACT spec prompt with a hard write-NOW ordering
  beats an exhaustive one. **WAVE-42 NEW: two consecutive spec-engineer stalls
  on shear-center-analysis (11 + 10 min silent); Ops wrote the anchor + spec
  directly in 12 min. Lesson: after ONE re-dispatch still stalls, write the
  anchor + spec DIRECTLY (ops pattern).** When an anchor script is left behind
  by a stopped engineer, REUSE it.
- **STEER TIMING (wave-38 lesson #4, held):** expect one builder stall per ~4
  builders; a single steer resolves it — check quiet transcripts at ~8-10
  minutes, not 15+. If a terminal tool call exceeds ~7 min it may time out —
  treat as timed out, verify state, continue.
- **EXACT-FLOAT ASSERT LESSON (wave-41 + wave-42, HELD — wave-42 recurrence
  ROOT-CAUSED DEEPER):** wave-42's reliability-allocation contract test asserted
  an exact float-noise relative error (1.3552527156068805e-16, delta=1e-18)
  that failed ONLY under the git-hook env. **Root cause: the pre-push hook env
  resolves python3 to pyenv 3.13.12 (login shell sources .zshrc -> pyenv shims
  first; Neumaier-accurate sum() since 3.12 -> relative_error 0.0) while
  foreground shells use /usr/bin/python3 3.9.6 (naive sum() -> 1.355e-16).**
  Fix applied structurally: exact-noise asserts replaced with algorithm-safe
  bounds (abs < 1e-15), verified on BOTH interpreters, __pycache__ purged.
  THIS WAVE: write ALL contract-test numeric asserts order-safe/tolerant from
  the start (assertAlmostEqual/math.isclose or abs < 1e-15 bounds — NEVER
  exact-float equality or exact-noise delta on computed sums). If a push is
  blocked by a hook gate that passes standalone, root-cause the failing test
  FIRST (loop standalone validate, grep the failing file), fix structurally +
  purge __pycache__ + verify on both interpreters, THEN retry — never
  blind-retry.
- **DESC-TRIM LESSON (wave-41 + wave-42, HELD):** wave-42's
  bearing-only-localization desc-lint fail at close (missing 'Trigger' keyword —
  committed text ended at the Does-NOT-do sentence). Draft leaf descriptions
  ≤1000 chars / ≤148 words from the start WITH the Trigger tail included; if a
  trim is needed, edit the YAML frontmatter line itself (never a line-blob
  regex); re-run gate1 + `make visuals` after ANY leaf edit (wave-40 lesson #2:
  any leaf edit after the last make visuals must be followed by make visuals
  before push).
- **PUBLIC-SYNC RACED AHEAD (wave-42 NEW, PERSISTED):** the hourly
  publish-public automation picked up local dev commits (state note f42208e9 +
  publish fix 4819dc97) BEFORE the private push landed — public advanced to
  358c5824 at ~10:41 UTC with its own green CI. EXPECT this class mid-wave;
  do not fight it; verify public HEAD at close and record the ACTUAL public
  commit (may be ahead of your sync point).
- **VALUE-DELTA SAMPLER RULE (wave-38 lesson #3 + wave-42 close):** the
  value-delta sampler recomputes eval records from TEST FILE term presence,
  NOT the committed JSON. Reference the SKILL.md workflow steps NATURALLY in
  the test docstring (name the workflow steps the test exercises). Wave-42
  close recomputed thin-airfoil-section-theory's record from test-file terms
  (delta 0.333, still ≥0.2 PASS).
- **EM-DASH HYGIENE (standing):** em dashes in skills/ = 0 at wave-42 close.
  Write ALL new leaves em-dash-free. At prep and at close run
  `git grep -l "—" -- 'skills/'`; if nonzero, add ONE mechanical cleanup
  commit. ALWAYS report the REAL em-dash count in wave43-state.md — never copy
  a receipt that is not true at the HEAD you are on.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf. Read the sibling fence tables before writing any spec. If a
  candidate family is provably saturated, say so in wave43-state.md and spend
  the slot on the next family.
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
REAL module outputs, order-safe numeric asserts) + eval fragment
eval/hit1-wave43-<leaf>.yaml (2 corpus tasks with distinctive hyphenated
tokens) + eval/skill-eval/<leaf>.json value-delta record + ratings ledger row
appended IN-TURN at ≥9.5 (rows 582+, header 581→581+N at close). references/ +
assets/ only when the body inlines long external content.

**CREATION GATE (run BEFORE every leaf commit, exit 0 required — founder
2026-09-04):** `bash scripts/leaf-create-gate.sh <leaf-path>` — checks
structure, naming, test pass, pycache, content policy, corpus, eval. FAIL →
fix in-turn, re-run, then commit. Full builder checklist:
MAINTENANCE_AND_HANDOVER.md section 5a.

## Operational rules (ALL prior-wave lessons — non-negotiable)
1. **TURN-ALIVE (wave-24R rule, operational):** NEVER emit a text-only response
   while delegations are live or work remains. Every turn continues with real
   tool calls until close-out. The ONLY permitted text-only response is the
   final close-out report.
2. **API health first:** check DeepSeek API before fan-out; CAP 3-4 concurrent
   builders per batch (one agent per leaf — PARALLEL-AGENT doctrine).
3. **Quiet-hours gate-check before EACH batch:**
   `python3 ~/.hermes/scripts/quiet-hours-gate.py --check` (exit 0 = go; exit 2/3
   = stop/queue). Window 20:00-08:00 UTC — no work in the window. Dispatch is
   ~11:10 UTC — you have ~8.5h of build daylight to 20:00 UTC. Target: core
   close-out well before 20:00 UTC. **If close-out is not reached by ~19:30
   UTC: STOP CLEANLY — commit what landed (≥10 landed = PASS), push PRIVATE +
   sync if a full close chain exists, queue the remainder for 08:00 UTC
   2026-09-07.** Pre-quiet guard: no new subagents after ~19:30 UTC.
4. **Anti-hang protocol (wave-25..42 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies. If a `terminal`
   tool call exceeds ~7 min it may time out; treat as timed out, verify state,
   continue — do not sit silent.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 582+). No backfilling at close. Keep the
   re-read-max+1 rule. Final rows must be contiguous 582-581+N. **LEDGER RACE
   (wave-39 lesson #3, PERSISTED waves 40-42): concurrent appends scramble
   physical row order even when numbers stay contiguous. Normalize the physical
   row order to ascending at close before the header update AND verify every
   leaf's row on the HEAD chain after each batch (re-add lost rows
   immediately).**
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31..42 class): after any commit, verify
   `git ls-tree`/status that YOUR leaf's six artifacts AND your ledger row are
   on the HEAD chain; a swept file/row is not lost if you re-commit your own
   paths. **Concurrent mid-wave automation (desc frontload + visuals regen +
   hourly publish-public sync) is now an EXPECTED wave class (wave-38 lesson #2
   + wave-42 public-sync-raced-ahead): recover cleanly with remainder commits,
   never fight it; re-run make visuals at close regardless.**
7. **Hit@1 no-task-stealing check BEFORE close-out:** after corpus merge,
   re-run make validate; ZERO pre-existing tasks may be stolen by a new leaf
   description; fence descriptions against siblings (distinctive hyphenated
   tokens). Run the PRE-MERGE routing simulation (state/wave43-sim-merge.py on
   corpus + on-disk fragments BEFORE the real merge) so no rewording is needed.
8. **Corpus:** 1178 → 1178+2N (merge via state/wave43-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one
   table row + one routing-guidance bullet per family touched), router
   descriptions ≤1024 chars. Router parity check (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (1178+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
   ALL REQUIRED PASS · make value-delta 10/10 ≥0.2 · visuals-check PASS
   (numbers only via make visuals) · router descs ≤1024 · REPORT the real em
   dash count in skills/ (grep; 0 preferred) · tree clean. **PRE-PUSH MANIFEST
   FRESHNESS (wave-40 lesson #2): ANY leaf edit after the last `make visuals`
   must be followed by `make visuals` before the push.**
10. **Push PRIVATE only** (arjun-0077/aero-agent-skills, GITHUB_TOKEN_ARJUN,
    fast-forward, NO force) + ls-remote verify remote == HEAD. NO Ashforde, NO
    visibility flip. Then **publish-public.sh sync** (sanctioned path) + verify
    public HEAD (may have advanced via hourly automation — record the ACTUAL
    commit) + GitHub CI attest SUCCESS. Keep publish-public.sh fixes from
    2da34f0e (leaf-count regression guard) and eec11e34 (About refresh from the
    MIRROR post-push); do not revert. **NOTE: run the wave push as a background
    process with notify-on-complete — the pre-push hook battery can exceed a
    180s foreground timeout; if a push is blocked, root-cause the failing gate
    FIRST (loop standalone validate, grep the failing test file), fix
    structurally, purge __pycache__, verify on both interpreters, THEN retry —
    never blind-retry.**
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160`
    → verify SEND_EXIT=0.
12. **wave43-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons, REAL em-dash count) + commit + push PRIVATE. Then
    give the final close-out report (text-only allowed NOW).
