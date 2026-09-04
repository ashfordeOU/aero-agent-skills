# WAVE-35 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-04 ~14:35 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-34 close
baseline.
Baseline (wave-34 close, CEO gate PASSED 9.68/10 2026-09-04 ~14:30 UTC — fresh
CEO replay at 7b213b1b: validate 5/5 · 958/958 Hit@1 · attest 3/3 ·
completeness ALL REQUIRED · value-delta 10/10 · visuals fresh · em dashes 0 ·
tree clean; private remote == 7b213b1b == HEAD at gate; public ashfordeOU main
== f98c69d9 sync verified):
**472 leaves · 85 packs · 12 families · 958 router tasks · 30 standards**
(484 SKILL.md tracked = 472 leaves + 12 routers). Ratings ledger 472 rows.
Corpus eval/hit1-corpus.yaml = 958.
Per-family leaf counts (wave-34 close, docs/metrics.json verified):
**systems-engineering-safety 33 (smallest — re-probed waves 30-34 and
documented dense/saturated all five times; FRESH receipt required this wave —
re-probe only for a genuine gap, else document + shift)** · **vehicle-design 35
(second-smallest — wave-34 probe OPENED the aircraft-subsystem sizing class and
landed ECS + hydraulic; NOT saturated: probe further genuine subsystem sizing
gaps — landing-gear, fuel-system, electrical-load, avionics-cooling,
bleed/ECS-adjacent — only deterministic non-overlapping)** · **propulsion 36 ·
aerodynamics 36 (36-count — PROP +2 wave-34 (injector-design,
thrust-chamber-cooling), AERO 36 dense wave-34 (26-topic receipt, delta-wing
landed wave-33); assess density)** · **avionics 40 · flight-test-operations 40
(40-count — AV +1 wave-34 (previously-developed-software), FTO +1 wave-34
(control-force-flight-test); assess)** · **gnc-autonomy 41 · manufacturing-
quality 41 (41-count — GNC dense wave-34 (LQG/information-filter declined w/
composition receipts); MQ +2 wave-34 (cusum-ewma-monitoring,
solid-rivet-installation-quality); assess)** · **cross-cutting 42 ·
flight-mechanics 42 (42-count — CC +2 wave-34 (singular-value-decomposition,
rank-based-hypothesis-testing); FM saturated wave-34 (fixed-wing spot-probe all
owned; rotorcraft: ground-resonance declined lead-lag owns coincidence,
Pitt-Peters declined convention-sensitivity — FRESH receipt required)** ·
**structures 43 · space-systems 43 largest last (STRUCT +1 wave-34
(lug-joint-analysis); SPACE +3 wave-34 (kepler-orbit-propagation,
gyro-allan-variance, pointing-error-budget — assess remaining ADCS/orbit
depth)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **SES 33 + VD 35 first** — SES documented dense/saturated waves
  30-34 (33 leaves; packs arp4754a 8, arp4761a 11, certification 4,
  continued-airworthiness 2, mbse 6, requirements 1, safety-case 1). Fresh
  receipt required THIS wave (grep sibling fences; if provably still saturated,
  say so in wave35-state.md and spend slots on next-smallest). **VD is the
  wave-35 probe candidate** — wave-34 proved the aircraft-subsystem sizing
  class was a real zero-owner gap (ECS + hydraulic); probe for further genuine
  gaps in that class with deterministic stdlib worked examples (landing-gear
  kinematics/loads, fuel-system sizing, electrical load analysis, cabin/avionics
  cooling) — only clean non-overlapping gaps. **Then propulsion 36 +
  aerodynamics 36** (PROP FRESH re-probe post-injector/cooling — remaining
  rocket subsystem sizing? nozzle? AERO dense receipt wave-34 holds — assess
  density). **Then the 40/41-count — avionics 40, flight-test-operations 40,
  gnc-autonomy 41, manufacturing-quality 41** (AV/FTO/MQ post-wave-34 density
  assess; GNC dense wave-34 — re-probe only for a genuine gap, else document +
  shift). **Then cross-cutting 42 + flight-mechanics 42.** **Then structures 43
  + space-systems 43 largest last** (STRUCT re-probed dense waves 31-34 — spend
  only on a clean gap; SPACE assess remaining orbit-mechanics/ADCS/subsystems
  depth beyond wave-34's three). Probe only genuine non-overlapping gaps; never
  open a duplicate.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave35-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter, "Use when you must …" gate-2 clause style) +
scripts/<leaf>_logic.py (stdlib only, portable imports — sibling
os.path.dirname(os.path.abspath(__file__)) pattern, NO machine-local absolute
paths; wave-27 lesson a440e453, publish leak sweep aborts on it) + scripts/test_<leaf>.py
(offline unittest, asserts REAL module outputs) + eval fragment eval/hit1-wave35-<leaf>.yaml
(2 corpus tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json
value-delta record + ratings ledger row appended IN-TURN at ≥9.5 (rows 473+,
header 472→472+N at close). references/ + assets/ only when the body inlines long
external content.

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
   ~14:35 UTC; the window opens 20:00 UTC — you have ~5.4h of build daylight;
   normal full-speed cadence, but STILL gate-check per batch and STOP cleanly at
   20:00 UTC if close-out is not reached (queue, resume 08:00 UTC next daylight
   per doctrine). Target: close-out comfortably this session (~1-2h per wave
   history); a partial wave with ≥10 landed = PASS, <10 = queue resume.
4. **Anti-hang protocol (wave-25..34 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 473+). No backfilling at close.
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31/32/33/34 class, wave-16 precedent): concurrent
   builders' explicit-path adds can collide in the shared git index AND the
   shared ledger — after any commit, verify `git ls-tree`/status that YOUR
   leaf's six artifacts AND your ledger row are on the HEAD chain; a swept
   file/row is not lost if you re-commit your own paths.
7. **Hit@1 no-task-stealing check BEFORE close-out** (wave-24R gate-fix lesson,
   wave-31 pn1 reword precedent): after corpus merge, re-run make validate;
   ZERO pre-existing tasks may be stolen by a new leaf description; fence
   descriptions against siblings (distinctive hyphenated tokens). Reword a
   pre-existing task ONLY on the wave-31 precedent and disclose it. Run the
   PRE-MERGE routing simulation (state/wave35-sim-merge.py on corpus + on-disk
   fragments BEFORE the real merge) so no rewording is needed.
8. **Corpus:** 958 → 958+2N (merge via state/wave35-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one table
   row + one routing-guidance bullet per family touched), router descriptions
   ≤1024 chars (state/wave16-router-desc-len.py PASS). Router parity check
   (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (958+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
   ALL REQUIRED PASS · make value-delta 10/10 ≥0.2 · visuals-check PASS
   (numbers only via make visuals) · router descs ≤1024 · em dashes 0 in
   skills/ · tree clean.
10. **Push PRIVATE only** (arjun-0077/aero-agent-skills, GITHUB_TOKEN_ARJUN,
    fast-forward, NO force) + ls-remote verify remote == HEAD. NO Ashforde, NO
    visibility flip. Then **publish-public.sh sync** (sanctioned path) + verify
    public HEAD + GitHub CI attest SUCCESS. Keep publish-public.sh fixes from
    2da34f0e (leaf-count regression guard) and eec11e34 (About refresh from the
    MIRROR post-push); do not revert. Concurrent release/docs automation may
    land local-only commits mid-wave (wave-30 class) — fast-forward below the
    wave commits, do not fight them; regenerate manifests at close.
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160`
    → verify SEND_EXIT=0.
12. **wave35-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons) + commit + push PRIVATE. Then proc exit → CEO P5.2
    WAVE-35 audit ≥9.5 → WAVE-36.

## Sequence
Prep (builder kit + 12-16 specs at ops/automation/state/wave35-specs/, commit) →
batches of 3-4 → ≥10 landed → corpus merge + routers → ratings header → gates
FRESH → push PRIVATE + verify → publish-public sync + CI verify → GROUP 160
post → wave35-state.md → exit. If the window approaches before close-out: stop
cleanly, commit what landed, queue resume 08:00 UTC (per doctrine). No founder
contact (routine progress).
