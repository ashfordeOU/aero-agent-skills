# WAVE-42 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-06 ~08:05 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-41 close
baseline.
Baseline (wave-41 close, CEO gate PASSED 9.68/10 2026-09-05 ~17:36 UTC — fresh
CEO replay at a9fa0d63: make validate 5/5 1150/1150 + make attest 3/3 + make
completeness ALL REQUIRED PASS, 0 tracked findings; private remote == a9fa0d63
== HEAD at close, then infra/docs commits landed to ba8b8906 == remote main
(hourly-publish + context why-files — non-leaf, baseline intact); public
ashfordeOU main == 60fa4c4 sync verified with CI attest + release-on-milestone
SUCCESS):
**567 leaves · 85 packs · 12 families · 1150 router tasks · 30 standards**
(579 SKILL.md tracked = 567 leaves + 12 routers). Ratings ledger 567 rows.
Corpus eval/hit1-corpus.yaml = 1150.
Per-family leaf counts (wave-41 close, docs/metrics.json verified 2026-09-06):
**gnc-autonomy 42 (SMALLEST — wave-41 landed 0 slots: saturated reaffirmed with
candidates resolving to space-systems/adcs + orbit-mechanics owners; probe the
WHOLE family FRESH with zero-owner greps + sibling fence reads — wave-40 landed
ins-gnss-integrated-filter; only clean deterministic non-overlapping gaps)** ·
**aerodynamics 43 (wave-41 +3: isentropic-flow-relations,
regular-shock-reflection, stagnation-flow-boundary-layer — the AERO dense
receipt has now yielded FIVE straight waves; wave-41 declines stood: SWBLI,
real-gas, hypersonic-viscous-interaction, tangent-wedge,
supersonic-linearized-theory/Ackeret (purpose collides with
shock-expansion-airfoil); do NOT re-open turbulent-boundary-layer-integral /
whirl-flutter / LFC / NLF — probe FRESH only clean closed-form gaps)** ·
**flight-test-operations 43 (wave-41 +2: fuel-jettison-flight-test,
in-flight-engine-relight-test; 13/14 functions saturated with fresh evidence
wave-41 — re-probe only genuine gaps)** · **propulsion 43 (wave-41 +1:
polytropic-efficiency; scramjet-cycle CLOSED until a verified Rayleigh
energy-bookkeeping anchor exists — do NOT re-open; wave-39 declines stood: drag
loss, PPT, resistojet, pressurant, ablative, turboshaft/engine-matching/
axial-stage)** · **systems-engineering-safety 45 (wave-41 +3: event-tree-analysis,
reliability-growth-analysis, maintainability-prediction — the arp4761a seam has
now yielded FIVE straight waves; reliability-prediction-parts-count LEFT IN
RESERVE wave-41 (med conf, MIL-HDBK-217-style subset scoping) — assess whether
that reserve slot is now defensible with fresh receipts; probe the WHOLE family
FRESH per wave-38 lesson #1; receipts govern, CEO-named lists may be stale)** ·
**avionics 46 (saturated reaffirmed wave-41; probe only clean determinism)** ·
**flight-mechanics 46 (wave-41 +1: rotorcraft-turn-performance; assess remaining
performance/mechanics gaps)** · **manufacturing-quality 48 (saturated reaffirmed
wave-41; probe only clean determinism)** · **structures 51 (wave-41 +2:
beam-column-analysis, curved-beam-analysis; stringer-crippling + variable-angle
Kuhn CLOSED on fidelity — do not re-open)** · **space-systems 52 (wave-41 +2:
environmental-disturbance-torque-budget, reaction-jet-limit-cycle; assess
remaining ADCS/mission-design gaps)** · **vehicle-design 54 (wave-41 +2:
air-cycle-machine-sizing, v-tail-sizing)** · **cross-cutting 54 (Tied LARGEST
with vehicle-design — probe LAST, only if every smaller family is provably
exhausted)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **gnc-autonomy 42 first** (probe the WHOLE family FRESH per
  wave-38 lesson #1 — wave-41 saturated receipts reaffirmed with
  space-systems/adcs + orbit-mechanics resolution; re-probe only genuine
  deterministic gaps; receipts govern). **Then the 43-count — aerodynamics 43 +
  flight-test-operations 43 + propulsion 43** (AERO: probe boundary-layer/
  high-speed/aeroheating veins FRESH — wave-41 declines stood
  (SWBLI/real-gas/hypersonic-viscous-interaction/tangent-wedge/
  supersonic-linearized-theory); ONLY clean closed-form gaps; read the sibling
  fence tables first. FTO: 13/14 functions saturated wave-41 — re-probe only
  genuine gaps. PROP: scramjet-cycle CLOSED — probe other rocket/gas-turbine
  sizing only). **Then systems-engineering-safety 45** (arp4761a seam has
  yielded 5 straight waves; assess the reliability-prediction-parts-count
  reserve slot + remaining safety-assessment functions with FRESH receipts).
  **Then avionics 46 + flight-mechanics 46.** **Then manufacturing-quality 48.**
  **Then structures 51 + space-systems 52.** **Then vehicle-design 54 +
  cross-cutting 54 largest last** (only if every smaller family is provably
  exhausted). Probe only genuine non-overlapping gaps; never open a duplicate.
- **PROBE RULE (standing, wave-37 lesson #2):** "0 owners" is necessary but
  not sufficient — a zero-owner grep can still collide with a sibling that
  CLAIMS the function. Read the sibling fence/claim table before accepting any
  zero-owner grep as a genuine gap.
- **RECEIPTS OVER LISTS (wave-39 lesson #1, held waves 40-41):** probe briefs
  must be executed against the LIVE tree — wave-39's CEO-named SES candidates
  were stale; waves 40-41 probes again followed receipts. The wave plan follows
  the probe receipts, not the candidate list. Verify each named candidate
  EXISTS or DOES NOT at HEAD before spec'ing it.
- **SPEC-ENGINEER PROMPTS (wave-40 lesson #1, held wave-41):** long-context
  spec-engineer prompts on this model stall with in-flight model-response hangs
  (476+ s waits observed waves 40-41, three stopped total). A COMPACT spec
  prompt with a hard write-NOW ordering beats an exhaustive one. When an anchor
  script is left behind by a stopped engineer, REUSE it (wave-40 recovered
  peel/diagonal-tension/ground-station anchors; wave-41 recovered the relight
  anchor at /tmp/w41spec/anchor_relight.py in 86 s).
- **STEER TIMING (wave-38 lesson #4, held):** expect one builder stall per ~4
  builders; a single steer resolves it — check quiet transcripts at ~8-10
  minutes, not 15+. If a terminal tool call exceeds ~7 min it may time out —
  treat as timed out, verify state, continue.
- **EXACT-FLOAT ASSERT LESSON (wave-41, NEW):** event-tree-analysis's contract
  test asserted an exact-float equality on a sum-of-products of probabilities
  (3.0000000000000004e-05 != 3e-05) that failed ONLY under the git-hook
  environment — order-sensitive summation. Root-caused with a deterministic
  4x `make validate` loop, fixed with an order-safe assertAlmostEqual delta
  1e-15 (5e6a1c51) + full __pycache__ purge. THIS WAVE: write ALL new contract
  test numeric asserts order-safe/tolerant from the start (assertAlmostEqual/
  math.isclose), never exact-float equality on computed sums. If a push is
  blocked by a hook gate that passes standalone, treat it as a REAL latent test
  defect until root-caused — loop validate standalone, grep the failing file,
  fix structurally, THEN retry the push.
- **DESC-TRIM LESSON (wave-41, NEW):** 9 of 16 wave-41 leaf descriptions
  exceeded gate limits (1038-1216 chars). A first mechanical trim corrupted 9
  frontmatters (greedy regex swallowed following fields) — caught by gate1,
  restored from HEAD~1, re-applied with a YAML-SAFE frontmatter rewrite,
  amended in place (802a0766). THIS WAVE: draft leaf descriptions ≤1000 chars /
  ≤148 words from the start; if a trim is needed, edit the YAML frontmatter
  line itself (never a line-blob regex); re-run gate1 before commit.
- **EM-DASH HYGIENE (standing):** em dashes in skills/ = 0 at wave-41 close
  (REAL count, git grep U+2014 zero). THIS WAVE: write ALL new leaves
  em-dash-free (hyphens / restructured prose). At prep and at close run
  `git grep -l "—" -- 'skills/'`; if nonzero, add ONE mechanical cleanup
  commit; ALWAYS report the REAL em-dash count in wave42-state.md — never copy
  a receipt that is not true at the HEAD you are on.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave42-state.md and spend the slot on the next family.
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
REAL module outputs) + eval fragment eval/hit1-wave42-<leaf>.yaml
(2 corpus tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json
value-delta record + ratings ledger row appended IN-TURN at ≥9.5 (rows 568+,
header 567→567+N at close). references/ + assets/ only when the body inlines
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
   ~08:05 UTC — you have ~12h of build daylight to 20:00 UTC. Target: core
   close-out well before 20:00 UTC (prior waves' full cycle ~1.5-2.5h). **If
   close-out is not reached by ~19:30 UTC: STOP CLEANLY — commit what landed
   (≥10 landed = PASS), push PRIVATE + sync if a full close chain exists, queue
   the remainder for 08:00 UTC 2026-09-07.** Pre-quiet guard: no new subagents
   after ~19:30 UTC.
4. **Anti-hang protocol (wave-25..41 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies. If a `terminal`
   tool call exceeds ~7 min it may time out; treat as timed out, verify state,
   continue — do not sit silent.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 568+). No backfilling at close. Keep the
   re-read-max+1 rule. Final rows must be contiguous 568-567+N. **LEDGER RACE
   (wave-39 lesson #3, PERSISTED waves 40-41): concurrent appends scramble
   physical row order even when numbers stay contiguous — wave-40 lost
   ground-station's row to a RMW race and ops re-added it in 0d9837ca; wave-41
   found a pre-existing scramble at rows ~347-348 and normalized physical order
   at close. Normalize the physical row order to ascending at close before the
   header update AND verify every leaf's row on the HEAD chain after each batch
   (re-add lost rows immediately).**
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31..41 class — wave-41 swept
   environmental-disturbance-torque-budget's six artifacts inside the
   air-cycle-machine-sizing commit a7219686, verified on the HEAD chain, no
   revert fought): after any commit, verify `git ls-tree`/status that YOUR
   leaf's six artifacts AND your ledger row are on the HEAD chain; a swept
   file/row is not lost if you re-commit your own paths. **Concurrent mid-wave
   automation (desc frontload + visuals regen + its own publish-public sync) is
   now an EXPECTED wave class (wave-38 lesson #2): recover cleanly with
   remainder commits, never fight it; re-run make visuals at close
   regardless.**
7. **Hit@1 no-task-stealing check BEFORE close-out:** after corpus merge,
   re-run make validate; ZERO pre-existing tasks may be stolen by a new leaf
   description; fence descriptions against siblings (distinctive hyphenated
   tokens — standing lesson: embed 1-2 of the leaf's own hyphenated tag tokens
   in corpus queries where a sibling holds a generic single-word fragment; a
   pre-merge routing sim caught wave-41's only theft — tbm2 reworded to carry
   cfd-turbulence-modeling's y-plus/wall-treatment tokens per the wave-31 pn1
   precedent). Run the PRE-MERGE routing simulation (state/wave42-sim-merge.py
   on corpus + on-disk fragments BEFORE the real merge) so no rewording is
   needed.
8. **Corpus:** 1150 → 1150+2N (merge via state/wave42-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one
   table row + one routing-guidance bullet per family touched), router
   descriptions ≤1024 chars. Router parity check (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (1150+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
   ALL REQUIRED PASS · make value-delta 10/10 ≥0.2 · visuals-check PASS
   (numbers only via make visuals) · router descs ≤1024 · REPORT the real em
   dash count in skills/ (grep; 0 preferred — write em-dash-free, cleanup
   commit at prep/close if nonzero) · tree clean. **PRE-PUSH MANIFEST
   FRESHNESS (wave-40 lesson #2): the pre-push hook re-runs manifest freshness
   from scratch — ANY leaf edit after the last `make visuals` (even a gate-fix
   word change) must be followed by `make visuals` before the push, or the hook
   fails on manifest staleness.**
10. **Push PRIVATE only** (arjun-0077/aero-agent-skills, GITHUB_TOKEN_ARJUN,
    fast-forward, NO force) + ls-remote verify remote == HEAD. NO Ashforde, NO
    visibility flip. Then **publish-public.sh sync** (sanctioned path) + verify
    public HEAD + GitHub CI attest SUCCESS. Keep publish-public.sh fixes from
    2da34f0e (leaf-count regression guard) and eec11e34 (About refresh from the
    MIRROR post-push); do not revert. Concurrent automation may land
    local-only commits mid-wave (wave-30..41 class) — fast-forward below the
    wave commits, do not fight them; regenerate manifests at close. **NOTE:
    run the wave push as a background process with notify-on-complete — the
    pre-push hook battery can exceed a 180s foreground timeout (observed waves
    40-41); if a push is blocked, root-cause the failing gate FIRST (loop
    standalone validate, grep the failing test file), fix structurally, purge
    __pycache__, THEN retry — never blind-retry.**
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:<CHAT_ID>`
    → verify SEND_EXIT=0.
12. **wave42-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons, REAL em-dash count) + commit + push PRIVATE. Then
    give the final close-out report (text-only allowed NOW).
