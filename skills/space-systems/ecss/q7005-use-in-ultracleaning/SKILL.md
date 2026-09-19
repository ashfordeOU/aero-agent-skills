---
name: q7005-use-in-ultracleaning
description: "Verify the result of an ECSS-Q-ST-70-54C ultracleaning process with the infrared measurement of ECSS-Q-ST-70-05C. Use when a part has been through one or more cleaning cycles and the question is whether the surface actually reached its target rather than whether the procedure was followed: take each cycle's removal against the level the cycle before it left, read successive dead cycles as a process that will not improve, report a level that rose as recontamination between measurements, treat a residual sitting in the verification blank as a bound, and project whether another cycle could reach the target at all. Trigger: ecss, q-st-70-54, q-st-70-05-ir-contamination-scope, ultracleaning-verification-measurement, cleaning-cycle-removal-efficiency, cleaning-efficiency-plateau, verification-blank-limited-residual."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-use-in-ultracleaning, ultracleaning-verification-measurement, cleaning-cycle-removal-efficiency, cleaning-efficiency-plateau, verification-blank-limited-residual, recontamination-between-cleaning-cycles]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Use in Ultracleaning (space-systems/ecss/q7005-use-in-ultracleaning)

Use when the task is carrying an ECSS-Q-ST-70-05C infrared measurement
into the verification of an ultracleaning process run under
ECSS-Q-ST-70-54C — deciding from the levels measured whether the surface
reached the target, needs another cycle, or needs a different process.

## Domain quick reference

- Cleaning is verified by measurement. Executing the process as written
  is a precondition and not evidence, because the same process meets a
  different soil on every part. The areal organic level left on the
  surface is what the verification rests on.
- Removal is a per-cycle quantity, measured against the level the
  previous cycle left, not against the level the part started at. A
  campaign average looks healthy while the last three cycles did
  nothing, and the average is exactly the number that gets quoted.
- The plateau is the finding worth having. A process that has stopped
  removing does not start again, and repeated cycles then spend
  schedule and solvent while the surface stays where it is. Successive
  cycles under the efficiency floor while still above the target mean a
  different process, not another pass.
- A level that rises across a cycle is not a bad clean. It is
  recontamination between the two measurements, and it points at
  handling, packaging or the bench rather than at the cleaning step —
  the reintroduction control of the cleaning standard, not its process
  parameters.
- The verification measurement has a blank of its own: the solvent, the
  wipe and the cell used to take it. A residual sitting inside that
  blank is a bound, and a bound demonstrates cleanliness only when the
  bound itself is under the target. A clean-looking number from a dirty
  blank is the classic false pass.
- Whether another cycle can even reach the target is answerable before
  it is run. Projecting the last efficiency forward gives a cycle count,
  and a target unreachable inside the permitted count is a finding about
  the process, not about the part.

## Workflow

1. Resolve the policy: the per-cycle efficiency floor, how many trailing
   cycles constitute a plateau, the blank margin factor and the largest
   number of further cycles worth projecting.
2. Validate the campaign: a named item, the ultracleaning process
   reference being verified, a positive starting level, a positive
   target and a non-empty cycle list with non-negative levels.
3. Compute each cycle's removal efficiency against the level the
   previous cycle left, numbering the cycles as given.
4. Record a rise across any cycle as suspected recontamination, naming
   the cycle.
5. Compare the final residual with the verification blank scaled by the
   margin factor; when it sits inside, report the scaled blank as a
   bound and mark the result blank-limited.
6. Compare the reported level, value or bound, with the target,
   absorbing representation error at the boundary rather than relaxing
   the target.
7. Detect a plateau over the trailing cycles, and project how many
   further cycles the last efficiency would need.
8. Outcome: accepted when the target is met; not demonstrated when a
   blank-limited bound cannot reach it; process change required on a
   plateau or an unreachable target; another cycle otherwise. Then group
   a set of campaigns by outcome.

## Pitfalls

- Verifying the procedure instead of the surface. A perfectly executed
  process on an unexpected soil leaves an unacceptable part.
- Quoting a campaign-average removal. It hides the plateau, which is the
  only pattern that changes the decision.
- Answering a plateau with more cycles. The schedule goes, the solvent
  goes, and the level does not.
- Reading a rise as a cleaning failure. The cleaning step is the one
  part of that interval least likely to have added contamination.
- Accepting a residual that is really the blank. Without the blank
  beside it the cleanest-looking number in the campaign is meaningless.
- Relaxing the target so a residual sitting on it passes. Equality is a
  representation question, handled by the tolerance inside the
  comparison.

## Behavior contract (gate 3)

The policy merge, the campaign validation, the per-cycle efficiencies,
the recontamination finding, the blank-limited bound, the plateau
detection, the projected cycle count and the accepted, further-cycle,
process-change and not-demonstrated outcomes are exercised by the gate 3
contract test: scripts/test_q7005_use_in_ultracleaning.py against
scripts/q7005_use_in_ultracleaning_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7005_use_in_ultracleaning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
