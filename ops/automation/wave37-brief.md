# WAVE-37 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-04 ~18:00 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-36 close
baseline.
Baseline (wave-36 close, CEO gate PASSED 9.65/10 2026-09-04 ~18:00 UTC — fresh
CEO replay at 3c887595: contract tests spot-checked fuel-tank-inerting 31 PASS
+ propelling-nozzle 34 PASS + 11/11 skill-eval records with=1.0 delta=0.5
failed=0 · corpus 1008 · ratings header 496 · em dashes in skills/ = 0 REAL
count · tree clean; private remote == 3c887595 == HEAD at gate; public
ashfordeOU main == da80539f sync verified with CI attest + release-on-milestone
SUCCESS):
**496 leaves · 85 packs · 12 families · 1008 router tasks · 30 standards**
(508 SKILL.md tracked = 496 leaves + 12 routers). Ratings ledger 496 rows.
Corpus eval/hit1-corpus.yaml = 1008.
Per-family leaf counts (wave-36 close, docs/metrics.json verified):
**systems-engineering-safety 34 (smallest — re-probed waves 30-36 and documented
dense/saturated SIX consecutive times BUT wave-36 broke the streak: landed
ica-cmr-ali-classification in SES/continued-airworthiness — the
airworthiness-management/continued-airworthiness/MRB-adjacent area is NOT
saturated; FRESH receipt required this wave — re-probe that area for the NEXT
genuine gap, else document + shift)** ·
**aerodynamics 36 (36-count — AERO dense receipt wave-35 holds; assess)** ·
**propulsion 37 (37-count — PROP +1 wave-36 propelling-nozzle; assess rocket
subsystem sizing / remaining gaps)** · **flight-test-operations 41 ·
gnc-autonomy 41 (41-count — FTO +1 wave-35 pcm-telemetry-decommutation, GNC
dense receipt wave-35; re-probe only genuine gaps)** · **avionics 42 ·
flight-mechanics 42 (AV +1 wave-36 mil-std-1553-bus-loading; FM saturated
receipt wave-35; FRESH re-probe)** · **structures 43 · cross-cutting 44 ·
space-systems 44 (STRUCT saturated receipt wave-35; CC +1 wave-36 runs-test;
SPACE +1 wave-36 walker-delta-constellation; assess)** · **manufacturing-quality
45 · vehicle-design 47 largest last (MQ +1 wave-36 gage-linearity-bias-study;
VD +5 wave-36 = the richest built family now — wave-36 close disclosed the VD
sizing class still NOT saturated, but VD is LARGEST — probe ONLY if smaller
families are provably exhausted; smallest-first doctrine)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **SES 34 first** — the wave-36 ica-cmr-ali-classification
  landing (SES/continued-airworthiness) PROVES a live vein: probe
  airworthiness-management sub-area (e.g. type-certificate-data-sheet,
  airworthiness-directive-compliance, MRB disposition logic — ONLY clean
  non-overlapping deterministic gaps; read the sibling fence tables first).
  **Then aerodynamics 36 + propulsion 37** (AERO dense receipt wave-35 holds —
  assess for a genuine gap; PROP 37 assess rocket/gas-turbine remaining
  deterministic sizing). **Then the 41-count — flight-test-operations 41 +
  gnc-autonomy 41** (re-probe only genuine gaps; FTO rotorcraft/flight-test
  remaining candidates per wave-30..36 receipts). **Then avionics 42 +
  flight-mechanics 42 + structures 43.** **Then cross-cutting 44 +
  space-systems 44 + manufacturing-quality 45.** **Then vehicle-design 47
  largest last** (only if smaller families provably exhausted). Probe only
  genuine non-overlapping gaps; never open a duplicate.
- **EM-DASH HYGIENE (standing, wave-35 finding → wave-36 remediated):** em
  dashes in skills/ = 0 at wave-36 close (REAL count). THIS WAVE: write ALL
  new leaves em-dash-free (hyphens / restructured prose). At prep and at
  close run `git grep -l "—" -- 'skills/'`; if nonzero, add ONE mechanical
  cleanup commit; ALWAYS report the REAL em-dash count in wave37-state.md —
  never copy a receipt that is not true at the HEAD you are on.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave37-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter, "Use when you must …" gate-2 clause style) +
**FULL HOUSE BODY: Workflow → Worked example → Pitfalls (3-6 leaf-specific
bullets derived from the leaf's own content/tests — NEVER invent) → Behavior
contract (gate 3) → Compliance.** Never use "classified" as a verb in prose
(content-policy sweep trips CLASSIFIED; use "categorized"). +
scripts/<leaf>_logic.py (stdlib only, portable imports — sibling
os.path.dirname(os.path.abspath(__file__)) pattern, NO machine-local absolute
paths; logic files NEVER start with test_) + scripts/test_<leaf>.py (offline
unittest, asserts REAL module outputs) + eval fragment eval/hit1-wave37-<leaf>.yaml
(2 corpus tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json
value-delta record + ratings ledger row appended IN-TURN at ≥9.5 (rows 497+,
header 496→496+N at close). references/ + assets/ only when the body inlines
long external content.

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
   ~18:00 UTC; the window opens 20:00 UTC — you have ~2h of build daylight.
   Target: core close-out by ~19:15 UTC at the latest (wave-36 full cycle was
   ~55 min). **If close-out is not reached by ~19:30 UTC: STOP CLEANLY — commit
   what landed (≥10 landed = PASS), push PRIVATE + sync if a full close chain
   exists, queue the remainder for 08:00 UTC. Do NOT start a long post-close
   extension this wave.** Pre-quiet guard: no new subagents after ~19:30 UTC.
4. **Anti-hang protocol (wave-25..36 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies. If a `terminal`
   tool call exceeds ~7 min it may time out (wave-35 tail: 420s timeout at
   close, session recovered); treat as timed out, verify state, continue — do
   not sit silent.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 497+). No backfilling at close. Keep the
   re-read-max+1 rule (wave-36 contiguous; the wave-35 concurrent-append race
   did NOT recur — keep the rule). Final rows must be contiguous 497-496+N.
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31..36 class): after any commit, verify
   `git ls-tree`/status that YOUR leaf's six artifacts AND your ledger row are
   on the HEAD chain; a swept file/row is not lost if you re-commit your own
   paths.
7. **Hit@1 no-task-stealing check BEFORE close-out:** after corpus merge,
   re-run make validate; ZERO pre-existing tasks may be stolen by a new leaf
   description; fence descriptions against siblings (distinctive hyphenated
   tokens — wave-36 lesson: a leaf whose name/tag contains a generic
   single-word fragment owned by a sibling LOSE queries that don't carry the
   leaf's full hyphenated tag tokens, so spec corpus queries should embed 1-2
   of the leaf's own hyphenated tag tokens where a sibling holds the generic
   fragment). Run the PRE-MERGE routing simulation (state/wave37-sim-merge.py
   on corpus + on-disk fragments BEFORE the real merge) so no rewording is
   needed.
8. **Corpus:** 1008 → 1008+2N (merge via state/wave37-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one
   table row + one routing-guidance bullet per family touched), router
   descriptions ≤1024 chars. Router parity check (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (1008+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
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
    local-only commits mid-wave (wave-30..36 class) — fast-forward below the
    wave commits, do not fight them; regenerate manifests at close.
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160`
    → verify SEND_EXIT=0.
12. **wave37-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons, REAL em-dash count) + commit + push PRIVATE. Then
    proc exit → CEO P5.2 WAVE-37 audit ≥9.5 → WAVE-38.

## Sequence
Prep (builder kit + 12-16 specs at ops/automation/state/wave37-specs/, commit)
→ batches of 3-4 → ≥10 landed → corpus merge + routers → ratings header →
gates FRESH → push PRIVATE + verify → publish-public sync + CI verify → GROUP
160 post → wave37-state.md → exit. If the window approaches before close-out:
stop cleanly, commit what landed, queue resume 08:00 UTC (per doctrine). No
founder contact (routine progress).
