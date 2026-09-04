# WAVE-31 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-04 ~08:05 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-30 close
baseline.
Baseline (wave-30 close, CEO gate PASSED 9.68/10 2026-09-03 — fresh CEO
replay at 932b726f: validate 5/5 · 846/846 Hit@1 · attest 3/3 · em dashes 0
· tree clean; private remote == 932b726f == HEAD at gate; current HEAD
eedec744 == remote main (jetbrains plugin version fix, no leaf change
since gate)):
**416 leaves · 85 packs · 12 families · 846 router tasks · 30 standards**
(428 SKILL.md tracked = 416 leaves + 12 routers). Ratings ledger 416 rows.
Corpus eval/hit1-corpus.yaml = 846.
Per-family leaf counts (live-tree verified at dispatch, docs/metrics.json):
**systems-engineering-safety 33 (smallest) · vehicle-design 33 (smallest —
SES/VD both re-probed wave-30 and documented dense/saturated; FRESH receipt
required this wave — re-probe only for a genuine gap, else document +
shift)** · **cross-cutting 34 · flight-mechanics 34 · flight-test-operations
34 · propulsion 34 (four 34-count — CC/FTO/PROP documented dense wave-30;
FM +2 last wave was the rotorcraft gap start — fixed-wing saturation
receipt holds, but the rotorcraft domain is NEW and only partially built:
re-probe for genuine rotorcraft/other non-duplicate FM gaps)** · **aerodynamics
35 · avionics 35 · manufacturing-quality 35 (three 35-count; AERO/AV/MQ +2/+1/+1
wave-30)** · **gnc-autonomy 36 · space-systems 36 (36-count, +1 each wave-30)**
· **structures 37 (largest — last; +3 wave-30, assess density)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **SES 33 + VD 33 first** — wave-30 documented both as dense/
  saturated after re-probe (no clean non-duplicate gap found then). Fresh
  receipt required THIS wave (grep the sibling fences; if provably still
  saturated, say so in wave31-state.md and spend those slots on the next
  smallest families). **Then the four 34-count — cross-cutting,
  flight-mechanics, flight-test-operations, propulsion:** FM fixed-wing is
  saturated (wave-29/30 receipts hold: V-n = FTO load-factor-envelope,
  dutch-roll = lateral-directional-stability, maneuver-point =
  longitudinal-stability, time-to-climb = climb-performance, accelerate-stop
  = FTO accelerate-stop-distance) but rotorcraft is a fresh, partially-built
  domain (only hover + forward-flight landed in wave-30) — probe genuine
  rotorcraft gaps (e.g. autorotation, vertical flight/climb, ground effect,
  figure of merit, rotor torque/power) plus any other FM family-appropriate
  non-duplicate gaps before declaring FM dense. FTO/PROP documented dense
  wave-30 — re-probe with fresh receipts. **Then the three 35-count:
  aerodynamics, avionics, manufacturing-quality** (each +1/+2 wave-30 —
  assess density, probe only genuine gaps). **GNC/SPACE 36 = next; STRUCT 37
  largest = last.** Probe only genuine non-overlapping gaps; never open a
  duplicate.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave31-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter, "Use when you must …" gate-2 clause style) +
scripts/<leaf>_logic.py (stdlib only, portable imports — sibling
os.path.dirname(os.path.abspath(__file__)) pattern, NO machine-local absolute
paths; wave-27 lesson a440e453, publish leak sweep aborts on it) + scripts/test_<leaf>.py
(offline unittest, asserts REAL module outputs) + eval fragment eval/hit1-wave31-<leaf>.yaml
(2 corpus tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json
value-delta record + ratings ledger row appended IN-TURN at ≥9.5 (rows 417+,
header 416→416+N at close). references/ + assets/ only when the body inlines long
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
   ~08:05 UTC; the window closed 08:00 UTC and opens again 20:00 UTC — you have
   ~12h of build daylight; normal full-speed cadence, but STILL gate-check per
   batch and STOP cleanly at 20:00 UTC if close-out is not reached (queue,
   resume 08:00 UTC next daylight per doctrine). Target: close-out comfortably
   this session (~2h per wave history); a partial wave with ≥10 landed = PASS,
   <10 = queue resume.
4. **Anti-hang protocol (wave-25/26/27/28/29/30 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 417+). No backfilling at close.
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
7. **Hit@1 no-task-stealing check BEFORE close-out** (wave-24R gate-fix lesson,
   wave-26 p1 reword precedent): after corpus merge, re-run make validate; ZERO
   pre-existing tasks may be stolen by a new leaf description; fence descriptions
   against siblings (distinctive hyphenated tokens).
8. **Corpus:** 846 → 846+2N (merge via state/wave31-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one table
   row + one routing-guidance bullet per family touched), router descriptions
   ≤1024 chars (state/wave16-router-desc-len.py PASS). Router parity check
   (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (846+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
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
12. **wave31-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons) + commit + push PRIVATE. Then proc exit → CEO P5.2
    WAVE-31 audit ≥9.5 → WAVE-32.

## Sequence
Prep (builder kit + 12-16 specs at ops/automation/state/wave31-specs/, commit) →
batches of 3-4 → ≥10 landed → corpus merge + routers → ratings header → gates
FRESH → push PRIVATE + verify → publish-public sync + CI verify → GROUP 160
post → wave31-state.md → exit. If the window approaches before close-out: stop
cleanly, commit what landed, queue resume 08:00 UTC (per doctrine). No founder
contact (routine progress).
