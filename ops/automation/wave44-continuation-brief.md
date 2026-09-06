# WAVE-44 CONTINUATION RESCUE BRIEF — Aero Agent Skills P5.2 (relay dispatch 2026-09-06 ~14:40 UTC)

Your wave-44 builder session (20260906_162202_622165, proc 94232) closed at
16:34:36 CEST after emitting a text-only yield while the 9 delegated probe
results were still pending delivery — the TURN-ALIVE violation class that
killed wave-42 mid-close-out. The session is CLOSED (cli_close verified in
the profile state DB); the process is GONE (ps-verified). The relay is
dispatching YOU as the continuation builder to carry wave-44 from the
durable probe state to close-out.

You are the ONLY wave-44 builder. Do not re-dispatch a duplicate of
yourself; if you see another wave-44 chat process, stop and report.

## Verified state (relay-verified fresh 14:36-14:40 UTC — trust, do not re-litigate)
- AeroSkills HEAD == **e8e03308** "ops: wave-44 prep (kit, runbook, merge/sim helpers)" — LOCAL ONLY.
  Remote main == **ea778bbe** == wave-44 brief (ls-remote verified). No leaf commits exist.
- git status: 12 untracked items — ops/automation/state/wave44-recon/{dump-probes.py,
  extract-probes.py, find-receipts.py, task-0..8-receipt.md, wave44-prelight-counts.py}.
  These are the builder's recon helpers + SHORT receipt extracts. Do not delete them.
- ops/automation/state/wave44-specs/ is EMPTY. NO leaf plan written yet. 0 leaf dirs.
- Baseline (unchanged from wave-44 brief): 597 leaves · 85 packs · 12 families ·
  1210 router tasks · 30 standards. Ledger 597 rows. Corpus eval/hit1-corpus.yaml = 1210.
- QH gate exit 0 at dispatch (14:40 UTC). Build daylight to 20:00 UTC ≈ 5h20m.
- Budget: wave-build-44-rescue est $18 <= $20 cap (recorded). Spend wisely; no founder contact.

## Probe phase: COMPLETE (9/9, deleg_2ff07eac, all completed 16:32:21 CEST)
The FULL probe receipts are the subagent summaries — READ THESE, they are the
real receipts (the task-*-receipt.md files in wave44-recon/ are short extracts):
- ~/.hermes/profiles/opsmanager/cache/delegation/subagent-summary-{0..8}-20260906_163221_*.txt
  (task index → family: 0=avionics, 1=propulsion, 2=flight-mechanics,
   3=flight-test-operations, 4=systems-engineering-safety, 5=manufacturing-quality,
   6=aerodynamics, 7=gnc-autonomy, 8=space-systems)
- Task logs (same detail): ~/.hermes/profiles/opsmanager/cache/delegation/live/deleg_2ff07eac/task-{0..8}.log

### Candidate set from the probes (11 GO total)
- **avionics (1):** aperiodic-server-scheduling (avionics/fsw) — sporadic/deferrable/
  polling server analysis; 0 owners; real-time-scheduling fence leaves it open.
- **propulsion (2):** mixed-flow-exhaust (turbofan — two-stream mixer, wave-43 reserve,
  strong GO) · nozzle-area-ratio-selection (rocket — THIN, MED-overlap flagged; spec-time
  verify against nozzle siblings, decline if genuine overlap).
- **flight-test-operations (1):** vmcg-determination (borderline GO; vmcg<=V1 pairs with
  vmu's V1 gating; do NOT also build Vmcl; extend-existing-into-vmc is the fallback).
- **aerodynamics (4):** ackeret-linearized-supersonic (high-speed, GO) ·
  hypersonic-piston-theory (high-speed, GO) · added-mass-coefficients-potential-flow
  (aeroelasticity, GO) · stokes-creeping-flow-drag (boundary-layer, GO-lean lowest confidence).
- **gnc-autonomy (3):** ilqr-ddp (optimal-control, GO) · terrain-referenced-navigation
  (navigation, GO) · gnss-rtk-positioning (navigation, GO; rtca-do-229 ref).
- **NO_CANDIDATES (receipts on file):** flight-mechanics · systems-engineering-safety ·
  manufacturing-quality · space-systems.

### Plan decision rule (brief mandate: land >=10, plan 12-16)
11 GO candidates leaves thin margin against spec-time declines (nozzle-area-ratio thin,
stokes-creeping GO-lean, vmcg borderline). Build the leaf plan from the 11 FIRST. If
spec-time triage drops the viable set below ~12, EXTEND probes to the unprobed largest
families per the wave-44 brief's own sequencing (vehicle-design 55 → structures 57 →
cross-cutting 54 — probe with the same probe method, read sibling fences, receipts over
lists) to restore buffer. NEVER open a duplicate; every leaf gets the standard 6-artifact
completeness + leaf-create-gate + rate-at-creation >=9.5 in-turn.

## Your tasks (in order)
1. Read the wave-44 brief IN FULL: ~/AeroSkills/ops/automation/wave44-brief.md (mandate,
   per-family rules, all wave-43 lessons — EXACT-FLOAT, DESC-TRIM, compact spec prompts,
   PUBLIC-SYNC-RACED-AHEAD, ROUTER ROW REGEX, LEAF-BATCH CADENCE). Then the builder kit
   (state/wave44-builder-kit.md), close runbook (state/wave44-close-runbook.md), and the
   9 probe summaries above.
2. Write the leaf plan: ops/automation/state/wave44-leaf-plan.md (families/packs/leaves,
   anchors, ordering — smallest-first per brief; plan 12-16, >=10 floor).
3. Commit the recon + leaf plan + any extended probes as ONE prep commit (explicit paths,
   message "ops: wave-44 rescue prep (leaf plan, probe receipts)"). Push PRIVATE only when
   the pre-push battery passes (CI-first) — or defer the push until the close commit if you
   prefer (previous waves pushed prep separately; either is fine, never push red).
4. Spec phase: CAP <=4 concurrent spec-engineers, COMPACT write-NOW prompts (~1-1.5KB, ONE
   exemplar, anchor script FIRST then spec — wave-43 16/16 zero stalls). Specs land in
   ops/automation/state/wave44-specs/.
5. Build phase: leaf-build rounds of 3-4 concurrent builders (one subagent per leaf —
   PARALLEL-AGENT doctrine). Every leaf: SKILL.md + logic + contract test + eval fragment +
   value-delta record + ledger row IN-TURN >=9.5 (rows 598+). Run the leaf-create-gate
   before every leaf commit. Explicit-path commits only.
6. Close-out chain (per runbook): corpus merge (1210 + 2N) → routers → make visuals →
   gates FRESH at rest: make validate 5/5 · attest 3/3 · completeness · value-delta ·
   visuals-check · em-dash 0 · ledger contiguous (598-597+N) → push PRIVATE + ls-remote
   verify → publish-public.sh sync (sanctioned; record ACTUAL public commit — hourly
   automation may race ahead) + CI attest → GROUP 160 close-out post AS YOURSELF
   (env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160 "...")
   → wave44-state.md (honest receipts, ALL gates + counts real at YOUR HEAD) → commit +
   push → final close-out report (the ONLY text-only response allowed).
7. Final report: one concise block — leaves landed (families), final leaf count, corpus,
   ledger rows, gates results, private/public HEADs, CI run ids, GROUP message id.

## Hard rules
- TURN-ALIVE: NEVER emit a text-only response while delegations are live or work
  remains. The ONLY permitted text-only response is the final close-out report.
  (This is what killed your predecessor — do not repeat it.)
- Quiet-hours gate before EVERY batch: python3 ~/.hermes/scripts/quiet-hours-gate.py
  --check. Exit 0 = go. If close-out is not reached by ~19:30 UTC: STOP CLEANLY —
  commit what landed (>=10 landed = PASS), push PRIVATE if a close chain exists,
  queue the remainder for 08:00 UTC 2026-09-07.
- Budget: wave-build cap $20. No new spend beyond the wave.
- Publish law: NO direct push to ashfordeOU. Public sync ONLY via publish-public.sh.
- No founder contact. Routine progress.
