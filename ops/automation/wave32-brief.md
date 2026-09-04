# WAVE-32 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-04 ~09:25 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-31 close
baseline.
Baseline (wave-31 close, CEO gate PASSED 9.68/10 2026-09-04 09:20 UTC — fresh
CEO replay at 751dfb5d: validate 5/5 · 868/868 Hit@1 · attest 3/3 · em dashes
0 · tree clean; private remote == 751dfb5d == HEAD at gate; public
ashfordeOU main == d32e1ff3 sync verified):
**427 leaves · 85 packs · 12 families · 868 router tasks · 30 standards**
(439 SKILL.md tracked = 427 leaves + 12 routers). Ratings ledger 427 rows.
Corpus eval/hit1-corpus.yaml = 868.
Per-family leaf counts (live-tree verified at dispatch, docs/metrics.json):
**systems-engineering-safety 33 (smallest) · vehicle-design 33 (smallest —
SES/VD both re-probed waves 30 AND 31 and documented dense/saturated both
times; FRESH receipt required this wave — re-probe only for a genuine gap,
else document + shift)** · **propulsion 34 (re-probed wave-31, documented
dense; scramjet declined with Rayleigh/thermal-choke receipt — ramjet-cycle +
ramjet-inlet still cover the ramjet family; FRESH receipt required)** ·
**aerodynamics 35 · cross-cutting 35 · flight-test-operations 35 (three
35-count — AERO re-probed dense wave-31; CC +1 wave-31 (fir-filter-design),
FTO +1 wave-31 (rotorcraft-performance-flight-test); assess density, probe
genuine gaps only)** · **avionics 36 · manufacturing-quality 36 (36-count —
AV +1 wave-31 (airborne-weather-radar), MQ +1 wave-31 (internal-quality-audit);
assess density)** · **flight-mechanics 37 · structures 37 (37-count — FM +3
wave-31 rotorcraft: vertical-climb, HIGE, tail-rotor-sizing landed; STRUCT
re-probed wave-31 dense (continuous-turbulence + stiffener-crippling declined
on empirical/spectral grounds). FM rotorcraft subdomain still the youngest —
probe further genuine rotorcraft gaps (e.g. figure-of-merit content,
autorotation empirical models, ground-resonance/dynamic-stability) with
receipts; STRUCT only if a clean gap)** · **gnc-autonomy 38 · space-systems
38 (largest — last; +2 each wave-31)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority
  per doctrine: **SES 33 + VD 33 first** — waves 30/31 both documented dense/
  saturated with inventory-dump receipts (33 leaves each; SES packs arp4754a 8,
  arp4761a 11, certification 4, continued-airworthiness 2, mbse 6,
  requirements 1, safety-case 1; VD packs conceptual 5, cost-estimation 3,
  mass-properties 3, mdo 3, sizing 17, structures-integration 2). Fresh
  receipt required THIS wave (grep the sibling fences; if provably still
  saturated, say so in wave32-state.md and spend those slots on the next
  smallest families). **Then propulsion 34** (wave-31 dense receipt holds —
  FRESH re-probe, spend only on a genuine non-overlapping gap). **Then the
  three 35-count — aerodynamics, cross-cutting, flight-test-operations** (CC/
  FTO +1 wave-31; AERO dense wave-31 — assess). **Then avionics 36 +
  manufacturing-quality 36** (assess density). **Then flight-mechanics 37 +
  structures 37:** FM rotorcraft is the youngest subdomain (hover, forward
  flight, vertical climb, HIGE, tail-rotor sized in waves 30-31) — probe
  genuine rotorcraft engineering gaps (rotor figure of merit / torque-power
  breakdown content beyond what the hover leaf owns, autorotation empirical
  models, rotor dynamics if a deterministic stdlib contract test is
  defensible) and any FM fixed-wing gap with a fresh saturation receipt;
  STRUCT re-probed dense wave-31 — spend only on a clean gap. **GNC/SPACE 38
  = largest last.** Probe only genuine non-overlapping gaps; never open a
  duplicate.
- Never duplicate an existing leaf. Distinct trigger + description + purpose
  per leaf (audit-team standard). Read the sibling fence tables before
  writing any spec. If a candidate family is provably saturated, say so in
  wave32-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter, "Use when you must …" gate-2 clause style) +
scripts/<leaf>_logic.py (stdlib only, portable imports — sibling
os.path.dirname(os.path.abspath(__file__)) pattern, NO machine-local absolute
paths; wave-27 lesson a440e453, publish leak sweep aborts on it) + scripts/test_<leaf>.py
(offline unittest, asserts REAL module outputs) + eval fragment eval/hit1-wave32-<leaf>.yaml
(2 corpus tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json
value-delta record + ratings ledger row appended IN-TURN at ≥9.5 (rows 428+,
header 427→427+N at close). references/ + assets/ only when the body inlines long
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
   ~09:25 UTC; the window opens 20:00 UTC — you have ~10.5h of build daylight;
   normal full-speed cadence, but STILL gate-check per batch and STOP cleanly at
   20:00 UTC if close-out is not reached (queue, resume 08:00 UTC next daylight
   per doctrine). Target: close-out comfortably this session (~1h-1.5h per wave
   history); a partial wave with ≥10 landed = PASS, <10 = queue resume.
4. **Anti-hang protocol (wave-25..31 held):** write logic files in small
   pieces, compact unittests, early test runs. Watch live transcripts; steer
   quiet builders once — no re-dispatch unless a child dies.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 428+). No backfilling at close.
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
   Shared-index commit race (wave-31 class, wave-16 precedent): concurrent
   builders' explicit-path adds can collide in the shared git index — after any
   commit, verify `git ls-tree`/status that YOUR leaf's six artifacts are on the
   HEAD chain; a swept file is not lost if you re-commit your own paths.
7. **Hit@1 no-task-stealing check BEFORE close-out** (wave-24R gate-fix lesson,
   wave-26 p1 + wave-31 pn1 reword precedents): after corpus merge, re-run make
   validate; ZERO pre-existing tasks may be stolen by a new leaf description;
   fence descriptions against siblings (distinctive hyphenated tokens). Reword a
   pre-existing task ONLY on the wave-31 precedent (carry the incumbent leaf's
   distinctive hyphenated tags) and disclose it.
8. **Corpus:** 868 → 868+2N (merge via state/wave32-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one table
   row + one routing-guidance bullet per family touched), router descriptions
   ≤1024 chars (state/wave16-router-desc-len.py PASS). Router parity check
   (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (868+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
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
12. **wave32-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons) + commit + push PRIVATE. Then proc exit → CEO P5.2
    WAVE-32 audit ≥9.5 → WAVE-33.

## Sequence
Prep (builder kit + 12-16 specs at ops/automation/state/wave32-specs/, commit) →
batches of 3-4 → ≥10 landed → corpus merge + routers → ratings header → gates
FRESH → push PRIVATE + verify → publish-public sync + CI verify → GROUP 160
post → wave32-state.md → exit. If the window approaches before close-out: stop
cleanly, commit what landed, queue resume 08:00 UTC (per doctrine). No founder
contact (routine progress).
