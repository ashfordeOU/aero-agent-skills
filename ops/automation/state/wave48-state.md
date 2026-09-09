# WAVE-48 STATE NOTE (ops manager, honest close)

Wave-48 of the Aero Agent Skills P5.3 build. Dispatched by the RELAY
2026-09-09 ~08:05 UTC (daylight CEO gate 10:00 CEST; monitor fired the
relay at 08:01 UTC). Execution 08:05-11:25 UTC (daylight, quiet-window
clean; night model REVERSED holds - no night execution, executor stayed
PAUSED). Baseline: 645 leaves, 86 packs, 12 families, 1306 corpus tasks,
30 standards, ledger 645 rows (HEAD 92d84a48, wave-48 brief staged).

## Result

10 verified leaves landed (MUST >= 10 met):

- avionics/fsw/cyclic-executive-scheduling (50 -> 51)
- space-systems/subsystems/mmod-shielding-sizing (52 -> 53)
- propulsion/reciprocating/dual-cycle (53 -> 54)
- vehicle-design/sizing/landing-gear-weight-estimation (57 -> 58)
- vehicle-design/sizing/fuel-system-weight-estimation (58 -> 59)
- gnc-autonomy/control/h-infinity-synthesis (62 -> 63)
- gnc-autonomy/control/sliding-mode-control (63 -> 64)
- gnc-autonomy/control/feedback-linearization (64 -> 65)
- structures/composites/honeycomb-core-micromechanics (65 -> 66)
- structures/composites/laminate-bending-stiffness (66 -> 67)

Final counts: 655 leaves, 86 packs, 12 families, 1326 corpus tasks, 30
standards, ledger 655 rows contiguous (rows 646-655, renumbered once to
close a concurrent-rescue race gap at 647). SKILL.md tracked = 667 (655
leaves + 12 routers). No new packs this wave.

## Recon (9 whole-family FRESH probes, receipts task-0..9)

task-0 FM NO_CANDIDATES (saturated) · task-1 AV 1 GO
(cyclic-executive-scheduling) · task-2 PROP 1 GO (dual-cycle) · task-3
GNC 3 GO (h-infinity-synthesis, sliding-mode-control,
feedback-linearization) · task-4 VD 2 GO (landing-gear +
fuel-system-weight-estimation) · task-5 STRUCT 1 strong + 1 conditional
(honeycomb-core-micromechanics, laminate-bending-stiffness) · task-6 SES
NO_CANDIDATES · task-7 MQ NO_CANDIDATES · task-8 FTO NO_CANDIDATES ·
task-9 SPACE 1 GO (mmod-shielding-sizing - first space-systems GO since
wave-46; standing NO_CANDIDATES reopened on pool-drop rule and a
genuinely new seam). Saturated re-probe order honored (SES -> MQ -> FTO
-> SPACE). Pool 10 (9 strong + 1 conditional) >= 10 floor; CC/AERO not
re-probed (doctrine stop at pool >= 10). The wave-48 conditional landed
at build exactly as the spec pre-empted (B/D/ABD-only claim; wave-47
creep-stress precedent).

## Leaf commits (HEAD chain)

6cbd0e35 cyclic-executive-scheduling, 3b9bddfb dual-cycle, 5348fd77
landing-gear-weight-estimation, 5f8a3108 mmod-shielding-sizing,
394b5c19 fuel-system-weight-estimation, dc6eb304 sliding-mode-control,
2eef9669 feedback-linearization, 1d0ffed0 h-infinity-synthesis,
eca3da30 honeycomb-core-micromechanics, 79bd6c58
laminate-bending-stiffness. Close commit 97b98aca "ops: wave-48 close
(10 leaves, corpus 1306+20)".

## Builder model + rescue disclosure (honest)

All 10 leaf builds were dispatched through aero-delegate.sh (Claude
Code doer, skills skill_build, 40 turns / $10 budget). ALL 10 Claude
builders hit the 40-turn cap pre-commit (each ran ~4-12 minutes of
real work and produced most artifacts on disk - wave-47 lesson
confirmed: the turn cap is the norm, the rescue lane is the EXPECTED
completion path). The DeepSeek DAYLIGHT rescue lane (4+4+2 agents)
completed/verified each leaf: fixed missing fragments/JSON/ledger rows
(fuel-system missing none; feedback/sliding missing fragment+JSON;
h-infinity missing SKILL.md+fragment+JSON+test dedupe; honeycomb
duplicate logic file deduped to canonical hyphenated name; mmod missing
fragment+JSON), ran leaf-create-gate (exit 0 on every leaf), and
committed. Every leaf's contract test passes under BOTH interpreters
(/usr/bin/python3 3.9.6 and pyenv 3.13.12); no exact-float asserts;
portable imports; desc <= 1000 chars. Ratings ledger rows appended at
creation (646-655) and renumbered once for contiguity after a
concurrent-commit race (647 gap closed; disclosed).

## Gates FRESH at rest (post-close, real command output)

- make validate PASS 5/5 (1326/1326 Hit@1 incl. 20 new wave-48 tasks)
- make attest PASS 3/3 (number snapshot offline, brief audit, content
  policy 0 hits)
- make completeness ALL REQUIRED PASS (667 SKILL.md, no broken refs)
- make value-delta PASS 10/10 >= 0.2
- make visuals-check PASS (19 artifacts fresh: 655 leaves, 86 packs);
  manifest-check zero diff
- router parity PASS (all 12 families rows == leaves; wave43 parity
  script); router desc lengths <= 1024 PASS
- em dashes in skills/: 0
- stale-number-guard PASS
- git status clean at close

## Public sync

Private push: 97b98aca on chain 6cbd0e35..97b98aca (10 leaf commits +
rescue commits + close), pre-push ALL GATES GREEN (hook battery),
ls-remote == 97b98aca verified. publish-public.sh ran: export gates
green inside the export, leaf-count guard 655 >= 645 passed,
fast-forward no force; public ashfordeOU/aero-agent-skills updated and
verified at f6a3d8c1 (655 skills, 86 packs, 12 families); About
refreshed (public + private). At state-note time public CI attest +
release-on-milestone in progress on f6a3d8c1 (pushed 11:23 UTC).

## Spend

python3 ~/.hermes/scripts/run_budget.py record --job wave-build-48
--usd 0.40 --note "ESTIMATE: 9 recon probes + 10 spec engineers + 10
rescue agents at documented deepseek-v4-flash rates (receipts in
delegation logs, est ~$0.01-0.03 each); Claude Code doer runs on Max
subscription (~$0); oracle turn budget of this relay session excluded
(relay cap). Bounded by the $20 wave-build cap (checked exit 0 at
dispatch)."

## Lessons / disclosures

- Claude Code 40-turn cap is now a CERTAINTY for skill_build (10/10
  this wave). The delegate produces strong partial artifacts in its
  turns; budget the DS rescue lane as the standard completion path, not
  an exception. Rescue agents complete a leaf in ~2-4 min each at
  ~$0.01-0.03 - cheaper and faster than waiting on Claude session
  resets.
- Rescue agents running CONCURRENTLY on a shared ratings ledger race
  row numbers (round-1 produced a 647 gap). Fix applied: orchestrator
  pre-appends ratings rows before dispatching rescue batches (rounds
  2-3 had zero gaps); keep that practice.
- Concurrent leaf commits with shared eval/ + ratings files need the
  max+1/re-add protocol; every rescue agent followed it correctly
  (verified no lost rows, no clobbered leaves).
- mmod spec received a small factual correction from its builder
  ('mmod' substring false positive 'accommODate' in
  bleed-air-system-sizing) - orchestrator-accepted, committed with the
  renumber commit.
- One spec build-time suggestion (routing bullet in sandwich-panels /
  h-infinity-control / laminate-stiffness related-leaves fences) was
  deliberately skipped by rescue agents under commit-scope rules; the
  family-router guidance bullets added at close cover the routing
  intent. Future waves: spec authors should note such edits for the
  close-out router pass explicitly.
