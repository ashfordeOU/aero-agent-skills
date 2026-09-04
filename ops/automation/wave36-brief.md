# WAVE-36 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-04 ~17:05 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-35 close
baseline.
Baseline (wave-35 close, CEO gate PASSED 9.60/10 2026-09-04 ~17:00 UTC — fresh
CEO replay at 99097454: validate 5/5 · 986/986 Hit@1 · attest 3/3 ·
completeness ALL REQUIRED · value-delta 10/10 · visuals fresh · contract tests
spot-checked 34/35/31 PASS · tree clean; private remote == 99097454 == HEAD at
gate; public ashfordeOU main sync verified at wave-35 close):
**485 leaves · 85 packs · 12 families · 986 router tasks · 30 standards**
(497 SKILL.md tracked = 485 leaves + 12 routers). Ratings ledger 485 rows.
Corpus eval/hit1-corpus.yaml = 986.
Per-family leaf counts (wave-35 close, docs/metrics.json verified):
**systems-engineering-safety 33 (smallest — re-probed waves 30-35 and
documented dense/saturated SIX consecutive times; FRESH receipt required this
wave — re-probe only for a genuine gap, else document + shift)** ·
**vehicle-design 42 (richest remaining vein — wave-35 probe landed SEVEN
genuine aircraft-subsystem sizing gaps (retraction, electrical load, fuel
feed, avionics-bay cooling, oxygen, fire protection, fuel jettison), extending
wave-34's ECS + hydraulic; wave-35 disclosure: wave-36 should re-probe for
bleed/APU-adjacent and RAT/inerting candidates that were examined and parked
this wave — only deterministic non-overlapping, else document + shift)** ·
**propulsion 36 · aerodynamics 36 (36-count — PROP 36 post wave-34 +2, AERO 36
dense receipt wave-35 holds; assess)** · **avionics 41 · flight-test-operations
41 (41-count — AV +1 wave-35 (arinc429-bus-loading), FTO +1 wave-35
(pcm-telemetry-decommutation); assess)** · **gnc-autonomy 41 (41-count — GNC
dense receipt wave-35 holds; re-probe only genuine gaps)** ·
**cross-cutting 43 · flight-mechanics 42 (CC +1 wave-35 (information-entropy);
FM saturated receipt wave-35; FRESH re-probe)** · **structures 43 ·
space-systems 43 · manufacturing-quality 44 largest last (STRUCT saturated
receipt wave-35; SPACE no-genuine-gap receipt wave-35; MQ +3 wave-35
(attribute-control-charts, attribute-agreement-analysis,
individuals-and-moving-range-chart); assess density)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **SES 33 + VD 42 first** — SES documented dense/saturated
  waves 30-35 (sixth consecutive receipt at wave-35); fresh receipt required
  THIS wave (grep sibling fences; if provably still saturated, say so in
  wave36-state.md and spend slots on next-smallest). **VD is the wave-36
  probe candidate** — wave-35 disclosure names the parked candidates: bleed
  air / APU-adjacent (APU sizing itself declined wave-35 as duplicating the
  ELA load rollup + bleed fragmentation — probe ONLY clean non-overlapping
  sub-pieces), RAT (ram air turbine) / fuel-tank inerting (both declined
  wave-35 as thin/empirics — re-examine only if a deterministic stdlib
  worked example exists), plus any further aircraft-subsystem sizing gaps in
  the SAME deterministic class (wave-34/35 precedent). **Then propulsion 36
  + aerodynamics 36** (PROP 36: post-injector/cooling wave-34, nozzle?
  remaining rocket subsystem sizing? FRESH probe; AERO 36 dense receipt
  wave-35 holds — assess). **Then the 41-count — avionics 41,
  flight-test-operations 41, gnc-autonomy 41** (AV/FTO post-wave-35 density
  assess; GNC dense — re-probe only for a genuine gap, else document +
  shift). **Then cross-cutting 43 + flight-mechanics 42.** **Then structures
  43 + space-systems 43 + manufacturing-quality 44 largest last** (STRUCT/
  SPACE saturated/no-gap receipts wave-35 — spend only on a clean gap; MQ
  assess post-+3 density). Probe only genuine non-overlapping gaps; never
  open a duplicate.
- **EM-DASH HYGIENE FINDING (CEO audit 2026-09-04, wave-35 close):** the
  wave-35 post-close enrichment pass (de93b243, 192 lean leaves to full
  house) added prose containing em dashes; at HEAD 99097454, 68 skill files
  contain "—" and the wave35-state.md close receipt "em dashes 0 in skills/"
  is INACCURATE. Em dashes are NOT a gated failure (no em-dash gate in the
  make validate/attest/completeness/value-delta battery — verified in
  Makefile), but the team hygiene standard tracks 0 and the receipt must be
  truthful. THIS WAVE: at prep, run `git grep -l "—" -- 'skills/'`; if
  nonzero, add ONE mechanical cleanup commit (strip em dashes to hyphen/
  restructure in the enriched Pitfalls prose — scripts only, no semantic
  edits) at prep or close; ALWAYS report the REAL em-dash count in
  wave36-state.md — never copy a receipt that is not true at the HEAD you
  are on.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave36-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter, "Use when you must …" gate-2 clause style) +
scripts/<leaf>_logic.py (stdlib only, portable imports — sibling
os.path.dirname(os.path.abspath(__file__)) pattern, NO machine-local absolute
paths; wave-27 lesson a440e453, publish leak sweep aborts on it) + scripts/test_<leaf>.py
(offline unittest, asserts REAL module outputs) + eval fragment eval/hit1-wave36-<leaf>.yaml
(2 corpus tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json
value-delta record + ratings ledger row appended IN-TURN at ≥9.5 (rows 486+,
header 485→485+N at close). references/ + assets/ only when the body inlines long
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
   ~17:05 UTC; the window opens 20:00 UTC — you have ~2h55m of build daylight;
   normal full-speed cadence, but STILL gate-check per batch and STOP cleanly at
   20:00 UTC if close-out is not reached (queue, resume 08:00 UTC next daylight
   per doctrine). Target: core close-out within ~1.5h (per wave history);
   post-close extensions are OPTIONAL this wave — if the wave closes after
   ~19:15 UTC, do NOT start a long post-close enrichment extension; stop clean
   (the wave-30-class post-close work can queue for a future wave). A partial
   wave with ≥10 landed = PASS, <10 = queue resume.
4. **Anti-hang protocol (wave-25..35 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies. NOTE wave-35 tail:
   a `terminal` tool call timed out after 420s at close (gate battery replay)
   and the session recovered; if a long gate command exceeds ~7 min, treat it
   as timed out, verify state, and continue — do not sit silent.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 486+). No backfilling at close. Known concurrent-append
   race (wave-35 batch-1, rows landed out of order): renumber to contiguous at
   the batch boundary and disclose; final rows must be contiguous 486-485+N.
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31..35 class, wave-16 precedent): concurrent
   builders' explicit-path adds can collide in the shared git index AND the
   shared ledger — after any commit, verify `git ls-tree`/status that YOUR
   leaf's six artifacts AND your ledger row are on the HEAD chain; a swept
   file/row is not lost if you re-commit your own paths.
7. **Hit@1 no-task-stealing check BEFORE close-out** (wave-24R gate-fix lesson,
   wave-31 pn1 reword precedent): after corpus merge, re-run make validate;
   ZERO pre-existing tasks may be stolen by a new leaf description; fence
   descriptions against siblings (distinctive hyphenated tokens). Run the
   PRE-MERGE routing simulation (state/wave36-sim-merge.py on corpus + on-disk
   fragments BEFORE the real merge) so no rewording is needed.
8. **Corpus:** 986 → 986+2N (merge via state/wave36-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one table
   row + one routing-guidance bullet per family touched), router descriptions
   ≤1024 chars (state/wave16-router-desc-len.py PASS). Router parity check
   (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (986+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
   ALL REQUIRED PASS · make value-delta 10/10 ≥0.2 · visuals-check PASS
   (numbers only via make visuals) · router descs ≤1024 · REPORT the real em
   dash count in skills/ (grep; 0 preferred, cleanup commit at prep if
   nonzero per the finding above) · tree clean.
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
12. **wave36-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons, REAL em-dash count) + commit + push PRIVATE. Then
    proc exit → CEO P5.2 WAVE-36 audit ≥9.5 → WAVE-37.

## Sequence
Prep (builder kit + 12-16 specs at ops/automation/state/wave36-specs/, em-dash
cleanup commit if needed, commit) → batches of 3-4 → ≥10 landed → corpus merge
+ routers → ratings header → gates FRESH → push PRIVATE + verify → publish-public
sync + CI verify → GROUP 160 post → wave36-state.md → exit. If the window
approaches before close-out: stop cleanly, commit what landed, queue resume
08:00 UTC (per doctrine). No founder contact (routine progress).
