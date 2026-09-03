# WAVE-28 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-03 ~16:10 CEST)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the PUBLIC v1.0.0+ baseline.
Baseline (wave-27 close, HEAD 48c6738d, CEO gate PASSED 9.68/10 — fresh replay:
validate 5/5 · 772/772 Hit@1 · attest 3/3 · em dashes 0 · tree clean; private
remote == 48c6738d, public remote == 890c786c, CI attest runs 33774817699 +
33774817700 SUCCESS):
**379 leaves · 83 packs · 12 families · 772 router tasks** (391 SKILL.md tracked = 379
leaves + 12 routers). Ratings ledger 379 rows. Corpus eval/hit1-corpus.yaml = 772.
Per-family leaf counts (live-tree verified at dispatch): **cross-cutting 31 ·
flight-test-operations 31 · manufacturing-quality 31 · vehicle-design 31 ·
aerodynamics 31 (smallest — priority start; CC/FTO/MQ/VD untouched by wave-27)** ·
avionics 32 · flight-mechanics 32 · gnc-autonomy 32 · propulsion 32 · space-systems
32 · structures 32 · **systems-engineering-safety 32 (largest — last)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority per
  doctrine: **the five 31-count families FIRST** — cross-cutting,
  flight-test-operations, manufacturing-quality, and vehicle-design were untouched
  by wave-27 (wave27-state.md: "the 31-count families ... were untouched by design
  per smallest-first doctrine"); aerodynamics was +1 last wave (30→31) and joins
  the smallest group. Find the NEXT genuine non-overlapping engineering gaps there
  (tool/artifact-level leaves, deeper standards leaves, subtopics not yet claimed)
  or document why a family is truly full and move to the next (32-count families:
  avionics / flight-mechanics / gnc-autonomy / propulsion / space-systems /
  structures; systems-engineering-safety LARGEST = last).
- Never open a duplicate of an existing leaf. Distinct trigger + description +
  purpose per leaf (audit-team standard). If a candidate family is provably
  saturated, say so in wave28-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter, "Use when you must …" gate-2 clause style) +
scripts/<leaf>_logic.py (stdlib only, portable imports — sibling
os.path.dirname(os.path.abspath(__file__)) pattern, NO machine-local absolute
paths; wave-27 lesson a440e453) + scripts/test_<leaf>.py (offline unittest,
asserts REAL module outputs) + eval fragment eval/hit1-wave28-<leaf>.yaml (2 corpus
tasks with distinctive hyphenated tokens) + eval/skill-eval/<leaf>.json value-delta
record + ratings ledger row appended IN-TURN at ≥9.5 (rows 380+, header
379→379+N at close). references/ + assets/ only when the body inlines long external
content.

## Operational rules (ALL prior-wave lessons — non-negotiable)
1. **TURN-ALIVE (wave-24R rule, operational):** NEVER emit a text-only response
   while delegations are live or work remains. Every turn continues with real
   tool calls (poll transcripts/state/prep/gates) until close-out. The ONLY
   permitted text-only response is the final close-out report.
2. **API health first:** check DeepSeek API before fan-out; CAP 3-4 concurrent
   builders per batch (one agent per leaf — PARALLEL-AGENT doctrine).
3. **Quiet-hours gate-check before EACH batch:**
   `python3 ~/.hermes/scripts/quiet-hours-gate.py --check` (exit 0 = go; exit 2/3
   = stop/queue). Window 20:00-08:00 UTC — no work in the window.
4. **Anti-hang protocol (wave-25/26/27 held):** write logic files in small pieces,
   compact unittests, early test runs. Watch live transcripts; steer quiet
   builders once — no re-dispatch unless a child dies.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 380+). No backfilling at close.
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
7. **Hit@1 no-task-stealing check BEFORE close-out** (wave-24R gate-fix lesson,
   wave-26 p1 reword precedent): after corpus merge, re-run make validate; ZERO
   pre-existing tasks may be stolen by a new leaf description; fence descriptions
   against siblings (distinctive hyphenated tokens).
8. **Corpus:** 772 → 772+2N (merge via state/wave28-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one table
   row + one routing-guidance bullet per family touched), router descriptions
   ≤1024 chars (state/wave16-router-desc-len.py PASS). Router parity check
   (rows == leaves per family).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (772+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
   ALL REQUIRED PASS · make value-delta 10/10 ≥0.2 · visuals-check PASS
   (19 artifacts fresh; design LOCKED — numbers only via make visuals) ·
   router descs ≤1024 · em dashes 0 in skills/ · tree clean.
10. **Push PRIVATE only** (arjun-0077/aero-agent-skills, GITHUB_TOKEN_ARJUN,
    fast-forward, NO force) + ls-remote verify remote == HEAD. NO Ashforde, NO
    visibility flip. Then **publish-public.sh sync** (sanctioned path) + verify
    public HEAD + GitHub CI attest SUCCESS. NOTE: publish-public.sh was hardened
    at 2da34f0e (leaf-count regression guard — refuse stale exports that would
    DELETE skills on public) and eec11e34 (refresh About from the MIRROR
    post-push); keep those fixes, do not revert.
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160`
    → verify SEND_EXIT=0.
12. **wave28-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons) + commit + push PRIVATE. Then proc exit → CEO P5.2
    WAVE-28 audit ≥9.5 → WAVE-29.

## Sequence
Prep (builder kit + specs at ops/automation/state/wave28-specs/, commit) →
batches of 4 → ≥10 landed → corpus merge + routers → ratings header → gates
FRESH → push PRIVATE + verify → publish-public sync + CI verify → GROUP 160 post
→ wave28-state.md → exit. No founder contact (routine progress).
