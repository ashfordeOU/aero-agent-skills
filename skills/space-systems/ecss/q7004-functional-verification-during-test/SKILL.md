---
name: q7004-functional-verification-during-test
description: "Perform and grade the functional checks an assembly owes at the temperature extremes of an ECSS thermal test. Use when ECSS-Q-ST-70-04C asks for more than a before-and-after health check: build the set of check points the campaign owes at ambient and at both extremes of the first, last and any intermediate cycle, match what was actually performed against it, confirm each check was taken with the item inside the tolerance band of the condition it claims, judge every measured parameter against its limits, compare the two ambient references for relative drift, and return one verification verdict. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-functional-verification-during-test, at-temperature-functional-check, thermal-check-point-coverage, thermal-campaign-parameter-drift, assembly-hot-cold-extreme-check."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-functional-verification-during-test, thermal-functional-verification-during-test, at-temperature-functional-check, thermal-check-point-coverage, thermal-campaign-parameter-drift, assembly-hot-cold-extreme-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Functional Verification During Test (space-systems/ecss/q7004-functional-verification-during-test)

Use when the task is the at-temperature functional verification of an assembly
under ECSS-Q-ST-70-04C — deciding which functional checks the campaign owes,
whether the ones performed were taken under the conditions they claim, and
whether the item came back the same as it went in.

## Domain quick reference

- The point of an at-temperature check is that some failures only exist at
  temperature. A clearance that closes when cold, a reference that shifts when
  hot, a margin that vanishes at one end: a before-and-after check at ambient
  sees none of them, so the extremes are where the checks have to land.
- The owed set is structural, not a matter of taste. An ambient reference
  before, both extremes of the first cycle, both extremes of the last cycle,
  both extremes of any declared intermediate cycle, and an ambient reference
  after. The first cycle catches a workmanship failure, the last catches a
  wear-out, and the ambient pair is what drift is measured across.
- A check is only evidence about a condition if the item was at that
  condition. A functional run started on the way to the cold extreme
  documents the transit, not the extreme, so the recorded temperature is
  compared against the condition's target inside the tolerance band.
- Parameter limits and campaign drift answer different questions. Limits ask
  whether the item worked; drift asks whether the test changed it. A unit can
  sit inside its limits at both ambient references and still have moved
  across the campaign by more than the design allows.
- An unmeasured parameter is not a pass. A check that omits one of the
  parameters the campaign named has a hole in it, and that is reported as
  itself rather than folded into a limit verdict.
- A check that matches no required point is worth reporting too. It is either
  extra evidence or a sign the campaign ran a different profile than planned.

## Workflow

1. Build the owed check-point set from the cycle count and any declared
   intermediate interval, keeping the ambient references at the ends.
2. Index the performed checks by condition and cycle, refusing a duplicate
   rather than letting one silently replace another.
3. Compare the two sets and name both the omissions and the unscheduled
   checks.
4. For each performed check, compare its recorded temperature against the
   target for its condition inside the band, and report the deviation when it
   falls outside.
5. Judge every named parameter of every check against its limits, marking an
   omitted parameter as missing rather than as a pass.
6. Compare the ambient references parameter by parameter for relative drift
   against the campaign allowance, and only when both references exist.
7. Return the verdict with every finding that produced it.

## Pitfalls

- Treating ambient before and after as the whole functional verification.
  That is a continuity check on the assembly, not evidence it functions at the
  temperatures the mission will impose.
- Accepting a check because the chamber set point was right. The set point is
  the chamber's state; the item's recorded temperature is what says the check
  was taken at the condition.
- Checking only the first cycle. A failure that appears after repeated cycling
  is exactly what the cycle count exists to provoke, and only the last-cycle
  checks can see it.
- Reading drift off a single ambient reference. Drift is a difference between
  two references, and without the post-test one the campaign has no drift
  measurement at all, which is a different statement from zero drift.
- Folding a missing measurement into a limit pass because nothing was out of
  limits. Nothing was measured either, and the two are not the same result.
- Comparing a reading against its limit, or a drift against its allowance,
  with a bare strict inequality. Both are floats, so a value sitting on the
  bound is compared within a named tolerance while the bound itself stays as
  the campaign specified it.

## Behavior contract (gate 3)

The owed check-point construction, check indexing and coverage, at-condition
temperature placement, per-parameter limit verdicts, ambient-to-ambient
relative drift and the combined verification verdict are exercised by the gate
3 contract test: scripts/test_q7004_functional_verification_during_test.py
against scripts/q7004_functional_verification_during_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7004_functional_verification_during_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
