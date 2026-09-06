# WAVE-44 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-06 ~14:12 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-43 close
baseline.

Baseline (wave-43 close, CEO gate PASSED ~9.66/10 2026-09-06 ~14:10 UTC — fresh
CEO replay at HEAD 550cb0be: 597 leaves / 597 ledger rows 0 gap / corpus 1210 /
tree clean / em dashes 0 / attest 3/3 PASS; private remote == 550cb0be == HEAD
ls-remote verified; public ashfordeOU main == 3ba3821e with CI attest
34037152326 SUCCESS + release-on-milestone 34037152315 SUCCESS — the hourly
automation raced ahead and synced the wave-43 tree BYTE-IDENTICAL, recorded as
the ACTUAL public commit; wave-43 build +16 leaves in 4 rounds of 4 with ZERO
spec-engineer stalls):
**597 leaves · 85 packs · 12 families · 1210 router tasks · 30 standards**
(609 SKILL.md tracked = 597 leaves + 12 routers). Ratings ledger 597 rows.
Corpus eval/hit1-corpus.yaml = 1210.
Per-family leaf counts (wave-43 close, verified this dispatch):
**avionics 46 (TIED SMALLEST — SATURATED reaffirmed FRESH wave-43: whole-family
probe NO_CANDIDATES; TAWS/GPWS + Mode-S stay closed (wave-32 decline, RTCA-
gated, no standards-map id); probe only clean determinism, expect 0)** ·
**propulsion 46 (TIED SMALLEST — wave-43 +2 rocket-nozzle-divergence-loss +
turbofan-design-point; scramjet CLOSED DEFINITIVELY (do NOT re-open); wave-39
declines stood (drag loss, PPT, resistojet, pressurant, ablative,
turboshaft/engine-matching/axial-stage); wave-43 probe found unsat veins in
rocket + gas-turbine sizing — probe FRESH with receipts, only clean
closed-form/station-level producers)** · **flight-mechanics 47 (wave-43 probe
found 2 candidates, BOTH declined: rotorcraft-height-velocity-diagram ANALYSIS
conflicted with the FTO measurement slot (now filled — FTO owns H-V
demonstration), rotorcraft-forward-flight-envelope-limits carries fabricated-
table risk without a published closed-form anchor (parts-count decline
precedent); NOT saturated — revisit FRESH: fixed-wing + rotorcraft
performance-mechanics gaps, clean closed-form only)** · **flight-test-operations
47 (wave-43 +3 measurement-side: vmu-determination, rotorcraft-forward-flight-
climb-test, rotorcraft-height-velocity-diagram-test — the measurement side was
the ONE genuine seam after the wave-42 13/14 saturation reaffirm; whole-family
FRESH probe required, re-probe only clean deterministic measurement/planning
gaps, expect heavy saturation)** · **systems-engineering-safety 47 (SATURATED
reaffirmed FRESH wave-43: all six ARP4761A process functions exist;
reliability-prediction-parts-count NOT reopened (no MIL-HDBK-217/Telcordia id
in standards-map.yaml); probe only clean determinism, expect 0)** ·
**manufacturing-quality 48 (SATURATED reaffirmed FRESH wave-43: CMM seam
standards-map-blocked, no ISO 15530/ASME B89.4.x; probe only clean determinism,
expect 0)** · **aerodynamics 49 (wave-43 +3 fanno/rayleigh/unsteady-stokes —
the dense receipt has yielded SEVEN straight waves; wave-43 declines stood:
reflected-shock-tube-wall (HIGH overlap with shock-tube — extend-existing
adjudication), asymptotic-suction (LFC/NLF adjacency); probe FRESH only clean
closed-form gaps)** · **gnc-autonomy 49 (wave-43 +4: gnss-doppler-velocity-
positioning, process-noise-discretization, imu-static-calibration,
tightly-coupled-ins-gnss — NOT saturated; wave-43 reserve kept: tdoa-positioning
(fence-adjacent to manufacturing-quality acoustic-emission — re-check the fence
before opening), ilqr-ddp, terrain-referenced-navigation; probe navigation/
optimal-control/estimation veins FRESH)** · **space-systems 52 (SATURATED
reaffirmed FRESH wave-43: CCSDS 131.0-B seam map-blocked; slew owned by
bang-bang + attitude-control-sizing; probe only clean determinism, expect 0)** ·
**cross-cutting 54 (default CLOSED; probe LAST)** · **vehicle-design 55 (wave-43
NOT reached — largest-last doctrine; probe only if every smaller family is
provably exhausted)** · **structures 57 (LARGEST — wave-43 +4 crippling/
hertzian/metallic-fastener/plastic-collapse; wave-43 reserve kept:
statically-indeterminate, restrained-warping; probe LAST, clean
solid-mechanics/instability gaps only if smaller families exhaust)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority per
  doctrine: **avionics 46 + propulsion 46 first** (TIED smallest — AV: FRESH
  whole-family probe per wave-43 NO_CANDIDATES reaffirm; expect 0, say it with
  receipts if saturated. PROP: scramjet CLOSED — probe rocket/gas-turbine
  sizing FRESH, receipts over lists). **Then flight-mechanics 47 +
  flight-test-operations 47 + systems-engineering-safety 47** (FM: NOT
  saturated — revisit clean fixed-wing/rotorcraft performance-mechanics gaps,
  only published-anchor-backed; FTO: whole-family FRESH probe — measurement
  side now filled, expect saturation, only genuine deterministic gaps; SES:
  arp4761a seam FRESH probe, expect NO_CANDIDATES per wave-43). **Then
  manufacturing-quality 48** (saturated — clean determinism only). **Then
  aerodynamics 49 + gnc-autonomy 49** (AERO: clean closed-form only; GNC: probe
  navigation/optimal-control/estimation FRESH — tdoa-positioning/ilqr-ddp/
  terrain-referenced-navigation reserve candidates, re-verify fences at HEAD).
  **Then space-systems 52** (saturated). **Then cross-cutting 54 + vehicle-
  design 55 + structures 57 largest last** (only if every smaller family is
  provably exhausted). Probe only genuine non-overlapping gaps; never open a
  duplicate.
- **PROBE RULE (standing, wave-37 lesson #2):** "0 owners" is necessary but
  not sufficient — a zero-owner grep can still collide with a sibling that
  CLAIMS the function. Read the sibling fence/claim table before accepting any
  zero-owner grep as a genuine gap.
- **RECEIPTS OVER LISTS (wave-39 lesson #1, held waves 40-43):** probe briefs
  must be executed against the LIVE tree. The wave plan follows the probe
  receipts, not the candidate list. Verify each named candidate EXISTS or DOES
  NOT at HEAD before spec'ing it.
- **SPEC-ENGINEER PROMPTS (wave-40 lesson #1 + wave-42 lesson + wave-43 POSITIVE
  DATA POINT, HELD):** long-context spec-engineer prompts on this model stall
  with in-flight model-response hangs. A COMPACT spec prompt (~1-1.5KB) with a
  hard write-NOW ordering (write anchor script FIRST, run it, THEN write spec)
  and ONE format exemplar beats an exhaustive one — wave-43 ran 16/16 spec
  runs with ZERO stalls on this pattern. If one stalls anyway, steer ONCE; if
  still stalled after one re-dispatch, write the anchor + spec DIRECTLY (ops
  pattern). When an anchor script is left behind by a stopped engineer, REUSE
  it.
- **STEER TIMING (wave-38 lesson #4, held):** expect one builder stall per ~4
  builders; a single steer resolves it — check quiet transcripts at ~8-10
  minutes, not 15+. If a terminal tool call exceeds ~7 min it may time out —
  treat as timed out, verify state, continue.
- **EXACT-FLOAT ASSERT LESSON (wave-41 + wave-42 ROOT-CAUSED, HELD):** the
  pre-push hook env resolves python3 to pyenv 3.13.12 (login shell sources
  .zshrc -> pyenv shims first; Neumaier-accurate sum() since 3.12 ->
  relative_error 0.0) while foreground shells use /usr/bin/python3 3.9.6
  (naive sum() -> 1.355e-16). Write ALL contract-test numeric asserts
  order-safe/tolerant from the start (assertAlmostEqual/math.isclose or
  abs < 1e-15 bounds — NEVER exact-float equality or exact-noise delta on
  computed sums). If a push is blocked by a hook gate that passes standalone,
  root-cause the failing test FIRST, fix structurally + purge __pycache__ +
  verify on BOTH interpreters, THEN retry — never blind-retry.
- **DESC-TRIM LESSON (wave-41..43, HELD):** draft leaf descriptions ≤1000 chars
  / ≤148 words from the start WITH the Trigger tail included; if a trim is
  needed, edit the YAML frontmatter line itself (never a line-blob regex);
  re-run gate1 + `make visuals` after ANY leaf edit.
- **PUBLIC-SYNC RACED AHEAD (wave-42..43 NEW, PERSISTED):** the hourly
  publish-public automation picks up local dev commits BEFORE the private push
  lands. EXPECT this class mid-wave; do not fight it; verify public HEAD at
  close and record the ACTUAL public commit (may be ahead of your sync point).
- **VALUE-DELTA SAMPLER RULE (wave-38 lesson #3 + wave-42/43 close):** the
  value-delta sampler recomputes eval records from TEST FILE term presence,
  NOT the committed JSON. Reference the SKILL.md workflow steps NATURALLY in
  the test docstring.
- **EM-DASH HYGIENE (standing):** em dashes in skills/ = 0 at wave-43 close.
  Write ALL new leaves em-dash-free. At prep and at close run
  `git grep -l "—" -- 'skills/'`; if nonzero, add ONE mechanical cleanup
  commit. ALWAYS report the REAL em-dash count in wave44-state.md — never copy
  a receipt that is not true at the HEAD you are on.
- **ROUTER ROW REGEX PITFALL (wave-43 NEW):** router table rows start with
  `| <family>/...` (NO `skills/` prefix); a parity check regex that expects
  `^| skills/` returns 0 rows. Match `^\| <family>/`.
- **LEAF-BATCH CADENCE (wave-43 NEW):** 16 leaves built in 4 rounds of 4
  concurrent builders at ~6-30 min/leaf each; a shared-index sweep (one leaf's
  artifacts riding in a sibling's commit) is the EXPECTED once-per-wave event —
  verify byte-identical on HEAD, no remainder commit needed (kit rule).
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf. Read the sibling fence tables before writing any spec. If a
  candidate family is provably saturated, say so in wave44-state.md and spend
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
eval/hit1-wave44-<leaf>.yaml (2 corpus tasks with distinctive hyphenated
tokens) + eval/skill-eval/<leaf>.json value-delta record + ratings ledger row
appended IN-TURN at ≥9.5 (rows 598+, header 597→597+N at close). references/ +
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
   ~14:12 UTC — you have ~5h48m of build daylight to 20:00 UTC. Target: core
   close-out well before 19:30 UTC. **If close-out is not reached by ~19:30
   UTC: STOP CLEANLY — commit what landed (≥10 landed = PASS), push PRIVATE +
   sync if a full close chain exists, queue the remainder for 08:00 UTC
   2026-09-07.** Pre-quiet guard: no new subagents after ~19:30 UTC.
4. **Anti-hang protocol (wave-25..43 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies. If a `terminal`
   tool call exceeds ~7 min it may time out; treat as timed out, verify state,
   continue — do not sit silent.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 598+). No backfilling at close. Keep the
   re-read-max+1 rule. Final rows must be contiguous 598-597+N. **LEDGER RACE
   (wave-39 lesson #3, PERSISTED waves 40-43): concurrent appends scramble
   physical row order even when numbers stay contiguous. Normalize the physical
   row order to ascending at close before the header update AND verify every
   leaf's row on the HEAD chain after each batch (re-add lost rows
   immediately).**
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31..43 class): after any commit, verify
   `git ls-tree`/status that YOUR leaf's six artifacts AND your ledger row are
   on the HEAD chain; a swept file/row is not lost if you re-commit your own
   paths. **Concurrent mid-wave automation (desc frontload + visuals regen +
   hourly publish-public sync) is now an EXPECTED wave class: recover cleanly
   with remainder commits, never fight it; re-run make visuals at close
   regardless.**
7. **Hit@1 no-task-stealing check BEFORE close-out:** after corpus merge,
   re-run make validate; ZERO pre-existing tasks may be stolen by a new leaf
   description; fence descriptions against siblings (distinctive hyphenated
   tokens). Run the PRE-MERGE routing simulation (state/wave44-sim-merge.py on
   corpus + on-disk fragments BEFORE the real merge) so no rewording is needed.
8. **Corpus:** 1210 → 1210+2N (merge via state/wave44-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one
   table row + one routing-guidance bullet per family touched), router
   descriptions ≤1024 chars. Router parity check (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (1210+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
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
12. **wave44-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons, REAL em-dash count) + commit + push PRIVATE. Then
    give the final close-out report (text-only allowed NOW).
