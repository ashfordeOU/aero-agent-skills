# WAVE-26 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-03 ~14:05 CEST)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the PUBLIC v1.0.0+ baseline.
Baseline (wave-25 close, HEAD 6415c91, CEO gate PASSED 9.66/10):
**353 leaves · 81 packs · 12 families · 720 router tasks** (365 SKILL.md tracked = 353
leaves + 12 routers). Ratings ledger 353 rows. Corpus eval/hit1-corpus.yaml = 720.
Per-family leaf counts: vehicle-design 29 · avionics 30 · cross-cutting 29 ·
flight-mechanics 29 · flight-test-operations 29 · manufacturing-quality 29 ·
gnc-autonomy 30 · propulsion 30 · space-systems 30 · structures 30 ·
aerodynamics 30 · **systems-engineering-safety 28 (smallest — priority start)**.

## Mandate and sequencing
- Land ≥10 leaves this wave (12-16 planned). Smallest-first family priority per
  doctrine: **systems-engineering-safety (28) FIRST** — wave25-state.md records it
  as saturated at method level (arp4754a 8 · arp4761a 11 · mbse 6 · certification 2 ·
  requirements 1); find the NEXT genuine non-overlapping engineering gaps there
  (e.g. new pack coverage, tool/artifact-level leaves, deeper standards leaves) or
  document why a family is truly full and move to the next smallest
  (cross-cutting 29 / flight-mechanics 29 / flight-test-operations 29 /
  manufacturing-quality 29 / vehicle-design 29 → 30-count families last).
- Never open a duplicate of an existing leaf. Distinct trigger + description +
  purpose per leaf (audit-team standard). If a candidate family is provably
  saturated, say so in wave26-state.md and spend the slot on the next family.
- Baseline counts referenced above must stay truthful at every commit.

## Per-leaf completeness standard (mandatory, from builder kit)
SKILL.md (agentskills.io frontmatter) + scripts/<leaf>_logic.py (stdlib only) +
scripts/test_<leaf>.py (offline unittest, asserts REAL module outputs) +
eval fragment eval/hit1-wave26-<leaf>.yaml (2 corpus tasks with distinctive
hyphenated tokens) + eval/skill-eval/<leaf>.json value-delta record + ratings
ledger row appended IN-TURN at ≥9.5 (rows 354+, header 353→353+N at close).
references/ + assets/ only when the body inlines long external content.

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
4. **Anti-hang protocol (wave-25 held):** write logic files in small pieces,
   compact unittests, early test runs. No stalls, no re-dispatches.
5. **Rate-at-creation ≥9.5 IN-TURN:** each builder appends its own ledger row at
   creation time (rows 354+). No backfilling at close.
6. **Explicit-path commits ONLY** (no `git add -A`); commit identity ashfordeOU;
   every commit a complete unit; message subject ≤50 chars, WHAT and WHY.
7. **Hit@1 no-task-stealing check BEFORE close-out** (wave-24R gate-fix lesson):
   after corpus merge, re-run make validate; ZERO pre-existing tasks may be stolen
   by a new leaf description; fence descriptions against siblings.
8. **Corpus:** 720 → 720+2N (merge via state/wave26-merge-corpus.py, delete
   fragments — 0 on disk at close). Update family routers parent-side (one table
   row + one routing-guidance bullet per family touched), router descriptions
   ≤1024 chars (state/wave16-router-desc-len.py PASS).
9. **Close-out gates FRESH at rest** (re-run, not claimed): make validate 5/5
   (720+2N Hit@1 deterministic offline) · make attest 3/3 · make completeness
   ALL REQUIRED PASS · make value-delta 10/10 ≥0.2 · visuals-check PASS
   (19 artifacts fresh; design LOCKED — numbers only via make visuals) ·
   router descs ≤1024 · em dashes 0 in skills/ · tree clean.
10. **Push PRIVATE only** (arjun-0077/aero-agent-skills, GITHUB_TOKEN_ARJUN,
    fast-forward, NO force) + ls-remote verify remote == HEAD. NO Ashforde, NO
    visibility flip. Then **publish-public.sh sync** (sanctioned path) + verify
    public HEAD + GitHub CI attest SUCCESS.
11. **GROUP 160 close-out post** as Ops Manager via
    `env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160`
    → verify SEND_EXIT=0.
12. **wave26-state.md honest** at close (leaves, family spread, deviations,
    disclosures, lessons) + commit + push PRIVATE. Then proc exit → CEO P5.2
    WAVE-26 audit ≥9.5 → WAVE-27.

## Sequence
Prep (builder kit + specs at ops/automation/state/wave26-specs/, commit) →
batches of 4 → ≥10 landed → corpus merge + routers → ratings header → gates
FRESH → push PRIVATE + verify → publish-public sync + CI verify → GROUP 160 post
→ wave26-state.md → exit. No founder contact (routine progress).
