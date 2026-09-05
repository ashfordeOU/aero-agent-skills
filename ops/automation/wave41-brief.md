# WAVE-41 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-05 ~14:12 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-40 close
baseline.
Baseline (wave-40 close, CEO gate PASSED 9.68/10 2026-09-05 ~14:10 UTC — fresh
CEO replay at 8300e7ea: make validate 5/5 1118/1118 + make attest 3/3 + make
completeness ALL REQUIRED PASS, 0 tracked findings; private remote == 8300e7ea
== HEAD; public ashfordeOU main == 92eef9ca sync verified with CI attest +
release-on-milestone SUCCESS):
**551 leaves · 85 packs · 12 families · 1118 router tasks · 30 standards**
(563 SKILL.md tracked = 551 leaves + 12 routers). Ratings ledger 551 rows.
Corpus eval/hit1-corpus.yaml = 1118.
Per-family leaf counts (wave-40 close, docs/metrics.json verified 2026-09-05):
**aerodynamics 40 (smallest — wave-40 landed rough-wall-skin-friction in
boundary-layer; the AERO dense receipt has now yielded FOUR straight waves
(boundary-layer-separation w38, flat-plate-skin-friction-heating w38,
bow-shock-standoff w39, rough-wall-skin-friction w40); wave-40 probe receipts:
SWBLI DECLINED (free-interaction plateau scatter + empirical heat-flux
augmentation), real-gas DECLINED (multi-regime piecewise curve fits /
chart-only effective gamma), hypersonic-viscous-interaction + tangent-wedge
DECLINED at 0.45 conf (thin vein after 3 waves) — probe FRESH only clean
closed-form gaps; do NOT re-open turbulent-boundary-layer-integral /
whirl-flutter / LFC / NLF)** · **flight-test-operations 41 (0 slots wave-40 —
saturated receipt reaffirmed with function scan; re-probe only genuine
gaps)** · **gnc-autonomy 42 (wave-40 landed ins-gnss-integrated-filter in
navigation; saturated receipts reaffirmed waves 38-40 — re-probe only genuine
gaps)** · **propulsion 42 (wave-40 +0: scramjet-cycle DROPPED at spec time on
cycle-convention fidelity — Rayleigh-combustor mirroring produced
non-physical Isp ~37500 s at M0 = 5; direct energy-bookkeeping with full
Rayleigh total-pressure relations beyond wave fidelity bar — do NOT re-open
scramjet-cycle without a verified anchor; wave-39 declines stood: drag loss,
PPT, resistojet, pressurant, ablative, turboshaft/engine-matching/axial-stage;
assess remaining rocket/gas-turbine deterministic sizing)** ·
**systems-engineering-safety 42 (wave-40 +3: fmes-coverage-analysis,
fault-tree-uncertainty-analysis, ssa-closure — the arp4761a seam has now
yielded FOUR straight waves (fault-tree-importance w38, beta-factor +
failure-mode-criticality w39, fmes-coverage + fault-tree-uncertainty +
ssa-closure w40); probe the WHOLE family FRESH with zero-owner greps +
sibling fence reads — candidates: remaining safety-assessment functions
beyond what wave-40 landed — ONLY clean deterministic gaps; receipts govern,
CEO-named lists may be stale)** · **flight-mechanics 45 (wave-40 +2:
balanced-field-length, rotorcraft-range-endurance; assess remaining
performance/mechanics gaps)** · **avionics 46 (saturated reaffirmed wave-40
with function-level proof; re-probe only genuine gaps)** ·
**manufacturing-quality 48 (saturated reaffirmed wave-40; probe only clean
determinism)** · **structures 49 (wave-40 +3: multiaxial-yield-criteria,
diagonal-tension-field-webs, peel-stress-bonded-joints; stringer-crippling
DECLINED twice on model fidelity — do not re-open; diagonal-tension general
variable-angle Kuhn solution NOT implemented (chart-heavy) — do not re-open
unless a clean closed form is verified)** · **space-systems 50 (wave-40 +2:
ground-station-pass-planning, magnetometer-calibration; assess remaining
ADCS/mission-design gaps)** · **vehicle-design 52 (wave-40 +3:
window-aperture-sizing, cargo-compartment-sizing,
emergency-exit-configuration; still not largest — CC 54 is largest)** ·
**cross-cutting 54 (LARGEST — probe LAST, only if every smaller family is
provably exhausted)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **aerodynamics 40 first** (probe FRESH per wave-40 receipts —
  boundary-layer/high-speed/aeroheating veins; ONLY clean closed-form gaps;
  wave-40 declined SWBLI/real-gas/hypersonic-viscous-interaction/tangent-wedge
  on fidelity — verify each with real receipts before spec'ing; read the
  sibling fence tables first). **Then flight-test-operations 41** (re-probe
  only genuine gaps — 0 slots wave-40 with function-scan proof). **Then the
  42-count — gnc-autonomy 42 + propulsion 42 + systems-engineering-safety 42**
  (SES: probe the WHOLE family per wave-38 lesson #1 — the arp4761a seam has
  yielded 4 straight waves; candidates to assess FRESH against the live tree:
  remaining arp4761a functions + safety-assessment beyond wave-40 — ONLY clean
  non-overlapping deterministic gaps; PROP: scramjet-cycle CLOSED until a
  verified Rayleigh energy-bookkeeping anchor exists — probe other
  rocket/gas-turbine sizing only). **Then flight-mechanics 45 + avionics 46 +
  manufacturing-quality 48.** **Then structures 49 + space-systems 50 +
  vehicle-design 52.** **Then cross-cutting 54 largest last** (only if every
  smaller family is provably exhausted). Probe only genuine non-overlapping
  gaps; never open a duplicate.
- **PROBE RULE (standing, wave-37 lesson #2):** "0 owners" is necessary but
  not sufficient — a zero-owner grep can still collide with a sibling that
  CLAIMS the function. Read the sibling fence/claim table before accepting any
  zero-owner grep as a genuine gap.
- **RECEIPTS OVER LISTS (wave-39 lesson #1, held wave-40):** probe briefs must
  be executed against the LIVE tree — wave-39's CEO-named SES candidates were
  stale (three already existed at HEAD); wave-40's probes again followed
  receipts. The wave plan follows the probe receipts, not the candidate list.
  Verify each named candidate EXISTS or DOES NOT at HEAD before spec'ing it.
- **SPEC-ENGINEER PROMPTS (wave-40 lesson #1):** long-context spec-engineer
  prompts on this model stall with in-flight model-response hangs (476+ s
  waits observed wave-40, two stopped). A COMPACT spec prompt with a hard
  write-NOW ordering beats an exhaustive one. When an anchor script is left
  behind by a stopped engineer, REUSE it (wave-40 recovered peel,
  diagonal-tension, ground-station anchors and spec'd directly from real
  outputs).
- **EM-DASH HYGIENE (standing):** em dashes in skills/ = 0 at wave-40 close
  (REAL count). THIS WAVE: write ALL new leaves em-dash-free (hyphens /
  restructured prose). At prep and at close run `git grep -l "—" -- 'skills/'`;
  if nonzero, add ONE mechanical cleanup commit; ALWAYS report the REAL em-dash
  count in wave41-state.md — never copy a receipt that is not true at the HEAD
  you are on.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave41-state.md and spend the slot on the next family.
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
REAL module outputs) + eval fragment eval/hit1-wave41-<leaf>.yaml
(2 corpus tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json
value-delta record + ratings ledger row appended IN-TURN at ≥9.5 (rows 552+,
header 551→551+N at close). references/ + assets/ only when the body inlines
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
   ~14:12 UTC — you have ~5.8h of build daylight to 20:00 UTC. Target: core
   close-out well before 20:00 UTC (prior waves' full cycle ~1.5-2.5h). **If
   close-out is not reached by ~19:30 UTC: STOP CLEANLY — commit what landed
   (≥10 landed = PASS), push PRIVATE + sync if a full close chain exists, queue
   the remainder for 08:00 UTC 2026-09-06.** Pre-quiet guard: no new subagents
   after ~19:30 UTC.
4. **Anti-hang protocol (wave-25..40 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies. If a `terminal`
   tool call exceeds ~7 min it may time out; treat as timed out, verify state,
   continue — do not sit silent. **STEER TIMING (wave-38 lesson #4): expect one
   builder stall per ~4 builders; a single steer resolves it — check quiet
   transcripts at ~8-10 minutes, not 15+. SPEC-ENGINEER PROMPTS (wave-40
   lesson #1): keep spec prompts compact with hard write-NOW ordering; stopped
   engineers leave anchors — reuse them.**
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 552+). No backfilling at close. Keep the
   re-read-max+1 rule. Final rows must be contiguous 552-551+N. **LEDGER RACE
   (wave-39 lesson #3, PERSISTED wave-40): concurrent appends scramble physical
   row order even when numbers stay contiguous — wave-40 lost ground-station's
   row to a RMW race and ops re-added it in 0d9837ca. Normalize the physical
   row order to ascending at close before the header update AND verify every
   leaf's row on the HEAD chain after each batch (re-add lost rows
   immediately).**
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31..40 class): after any commit, verify
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
   the PRE-MERGE routing simulation (state/wave41-sim-merge.py on corpus +
   on-disk fragments BEFORE the real merge) so no rewording is needed.
8. **Corpus:** 1118 → 1118+2N (merge via state/wave41-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one
   table row + one routing-guidance bullet per family touched), router
   descriptions ≤1024 chars. Router parity check (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (1118+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
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
    local-only commits mid-wave (wave-30..40 class) — fast-forward below the
    wave commits, do not fight them; regenerate manifests at close. **NOTE:
    run the wave push as a background process with notify-on-complete — the
    pre-push hook battery can exceed a 180s foreground timeout (observed
    wave-40).**
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160`
    → verify SEND_EXIT=0.
12. **wave41-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons, REAL em-dash count) + commit + push PRIVATE. Then
    give the final close-out report (text-only allowed NOW).
