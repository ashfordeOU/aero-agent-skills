# WAVE-30 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-03 ~20:30 CEST)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-29 close
baseline.
Baseline (wave-29 close, HEAD 237ab58d, CEO gate PASSED — fresh CEO
replay at 8f1fa670/237ab58d: validate 5/5 · 822/822 Hit@1 · attest 3/3 ·
em dashes 0 · tree clean; private remote == 237ab58d == HEAD, public remote
== 037e53c8 sync commit, CI attest run 33789668500 + release 33789668506
SUCCESS):
**404 leaves · 85 packs · 12 families · 822 router tasks** (416 SKILL.md
tracked = 404 leaves + 12 routers). Ratings ledger 404 rows. Corpus
eval/hit1-corpus.yaml = 822.
Per-family leaf counts (live-tree verified at dispatch): **flight-mechanics
32 (smallest; FRESH wave-29 saturation receipt — re-probe only for a
genuine gap, else document + shift)** · **aerodynamics 33 · cross-cutting
33 · systems-engineering-safety 33 · vehicle-design 33 (four 33-count
families — priority start; AERO untouched by wave-29, CC/SES/VD were +1
each 32→33)** · **avionics 34 · flight-test-operations 34 ·
manufacturing-quality 34 · propulsion 34 · structures 34 (five 34-count;
FTO/MQ/STRUCT untouched by wave-29 — re-probe these as priority-2
targets)** · **gnc-autonomy 35 · space-systems 35 (largest — last;
GNC +3 and SPACE +2 last wave, assess density, document saturation if
proven)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **flight-mechanics 32 first** (wave-29 documented provable
  saturation with specific receipts — V-n = FTO load-factor-envelope,
  dutch-roll = lateral-directional-stability, maneuver-point =
  longitudinal-stability, time-to-climb = climb-performance,
  balanced-field/accelerate-stop = FTO accelerate-stop-distance + takeoff
  performance, stick-free neutral point = overlap risk on
  longitudinal-stability). If FM is still provably saturated (fresh
  receipt this wave in wave30-state.md), spend those slots on the next
  smallest families: **the four 33-count — aerodynamics (untouched since
  wave-28's +2), cross-cutting, systems-engineering-safety,
  vehicle-design — then the five 34-count: avionics, flight-test-operations,
  manufacturing-quality, structures (all untouched by wave-29) + propulsion
  (34, +2 last wave, assess)**. Largest (GNC/SPACE 35) = last; GNC +3 and
  SPACE +2 in wave-29 — probe only genuine non-overlapping gaps.
- Never open a duplicate of an existing leaf. Distinct trigger + description +
  purpose per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave30-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter, "Use when you must …" gate-2 clause style) +
scripts/<leaf>_logic.py (stdlib only, portable imports — sibling
os.path.dirname(os.path.abspath(__file__)) pattern, NO machine-local absolute
paths; wave-27 lesson a440e453, publish leak sweep aborts on it) + scripts/test_<leaf>.py
(offline unittest, asserts REAL module outputs) + eval fragment eval/hit1-wave30-<leaf>.yaml
(2 corpus tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json
value-delta record + ratings ledger row appended IN-TURN at ≥9.5 (rows 405+,
header 404→404+N at close). references/ + assets/ only when the body inlines long
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
   ~18:29 UTC; the window opens 20:00 UTC — you have ~1h30m of build daylight;
   gate-check per batch, keep batches tight (2-3 batches max), and STOP cleanly at
   the window if close-out is not reached (queue, resume 08:00 UTC per doctrine).
   Target: close-out ~19:45 UTC at latest; if the first batch is slow, cut planned
   scope (fewer leaves is acceptable — mandate is ≥10, plan 12 for margin).
4. **Anti-hang protocol (wave-25/26/27/28/29 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 405+). No backfilling at close.
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
7. **Hit@1 no-task-stealing check BEFORE close-out** (wave-24R gate-fix lesson,
   wave-26 p1 reword precedent): after corpus merge, re-run make validate; ZERO
   pre-existing tasks may be stolen by a new leaf description; fence descriptions
   against siblings (distinctive hyphenated tokens).
8. **Corpus:** 822 → 822+2N (merge via state/wave30-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one table
   row + one routing-guidance bullet per family touched), router descriptions
   ≤1024 chars (state/wave16-router-desc-len.py PASS). Router parity check
   (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (822+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
   ALL REQUIRED PASS · make value-delta 10/10 ≥0.2 · visuals-check PASS
   (numbers only via make visuals) · router descs ≤1024 · em dashes 0 in
   skills/ · tree clean.
10. **Push PRIVATE only** (arjun-0077/aero-agent-skills, GITHUB_TOKEN_ARJUN,
    fast-forward, NO force) + ls-remote verify remote == HEAD. NO Ashforde, NO
    visibility flip. Then **publish-public.sh sync** (sanctioned path) + verify
    public HEAD + GitHub CI attest SUCCESS. Keep publish-public.sh fixes from
    2da34f0e (leaf-count regression guard) and eec11e34 (About refresh from the
    MIRROR post-push); do not revert.
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160`
    → verify SEND_EXIT=0.
12. **wave30-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons) + commit + push PRIVATE. Then proc exit → CEO P5.2
    WAVE-30 audit ≥9.5 → WAVE-31.

## Sequence
Prep (builder kit + 12-16 specs at ops/automation/state/wave30-specs/, commit) →
batches of 3-4 (tight: daylight ~1h30m) → ≥10 landed → corpus merge + routers →
ratings header → gates FRESH → push PRIVATE + verify → publish-public sync + CI
verify → GROUP 160 post → wave30-state.md → exit. If the window approaches before
close-out: stop cleanly, commit what landed, queue resume 08:00 UTC (per
doctrine). No founder contact (routine progress).
