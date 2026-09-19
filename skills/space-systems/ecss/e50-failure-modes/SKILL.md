---
name: e50-failure-modes
description: "Evaluate whether a communications link still meets its performance requirement in every failure mode the mission declares, per ECSS-E-ST-50C clause 5.6.11.4: sum each mode's concurrent decibel contributors, subtract them from the nominal margin, grade every mode against the required margin, name the mode that governs, and return any required mode the budget never covered as unassessed rather than as passing. Use when a link budget shows a healthy nominal column and the failure-mode columns are empty, optimistic, or graded one contributor at a time. Trigger: ecss, e-st-50c-communications-scope, link-performance-failure-modes, degraded-link-margin, governing-worst-case-link-mode, redundancy-recovered-link-failure, uncovered-failure-mode, concurrent-degradation-stack-up."
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
  tags: [ecss, e-st-50c-communications-scope, e50-failure-modes, link-performance-failure-modes, degraded-link-margin, governing-worst-case-link-mode, redundancy-recovered-link-failure, uncovered-failure-mode, concurrent-degradation-stack-up]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Failure Modes (space-systems/ecss/e50-failure-modes)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.6.11.4 —
that the communications link performance requirements are stated for, and hold
in, the failure modes declared for the mission — and the question is what a
link budget must show beyond its nominal column.

## Domain quick reference

- The nominal case is the easy case and it is not the requirement. The
  requirement is that performance survives the declared failure modes, so
  a budget that only proves the undegraded link has proved the wrong
  thing.
- A declared mode with no figure against it is unassessed, not passing.
  Absence of a number is absence of evidence; grading it green because
  nothing was written is how a missing analysis becomes a signed-off one.
- Degradation contributors inside one mode are concurrent and add. A mode
  built from three one-and-a-half decibel losses is worse than a mode
  built from one three decibel loss, which is why the largest single
  contributor is a poor guide to which mode governs.
- The governing mode is whichever applicable mode leaves the least
  margin. It has to be found by grading every mode, not guessed from the
  failure that sounds most severe.
- Direction matters. An uplink receiver failure does not degrade the
  downlink, and grading it against the downlink requirement both wastes
  margin and hides the mode that actually constrains that link.
- Recovery by redundancy changes how long a mode lasts, not whether the
  link works while it lasts. A redundancy-recovered mode still has to be
  graded, because the switchover is not instantaneous.
- Decibel margins add and subtract exactly on every host. Taking a power
  of ten or a logarithm to reach the same answer introduces host-dependent
  rounding for no benefit, so the arithmetic stays in decibels and the
  compliance comparison carries an explicit tolerance.

## Workflow

1. Normalise the declared modes, refusing a duplicate name and a negative
   degradation, and sort them so the grading order is deterministic.
2. Sum each mode's concurrent contributors in a fixed order and subtract
   the sum from the nominal margin to get that mode's margin.
3. Decide which modes apply to the link direction under assessment and
   grade only those against the requirement.
4. Compare each margin with the requirement inclusively, so a mode that
   lands exactly on the bound is met rather than a coin toss.
5. Name the applicable mode that leaves the least margin as the governing
   case.
6. Compare the declared modes with the modes the mission requires, and
   return any absentee as uncovered, which makes the whole assessment
   unassessed rather than compliant.

## Pitfalls

- Reporting compliance from the nominal margin alone. The clause exists
  precisely because that column always looks fine.
- Treating a required mode nobody analysed as a pass. An empty cell is an
  open action, and the verdict has to say so rather than round it up.
- Grading contributors one at a time inside a mode. They occur together,
  so the mode's real cost is their sum, and a per-contributor grade lets a
  stack-up through.
- Assuming the loudest failure governs. Three modest concurrent losses
  routinely beat one large loss, and only a full grading finds it.
- Applying a one-direction failure to both links. It overstates the
  downlink case, understates the uplink case, and moves the governing mode
  to the wrong place.
- Excusing a mode because redundancy recovers it. The link still has to
  work during the failure and through the switchover.
- Using a strict comparison on a margin that lands on the requirement.
  The answer then depends on the last bit of a floating-point sum, and
  two hosts disagree about a compliant design.

## Behavior contract (gate 3)

The decibel and direction validation, mode normalisation with duplicate
and negative-degradation rejection, concurrent contributor summation, the
per-mode margin, the inclusive margin comparison, direction filtering,
governing-mode selection, uncovered-mode detection and the three-way
met / not-met / unassessed verdict are exercised by the gate 3 contract
test: scripts/test_e50_failure_modes.py against
scripts/e50_failure_modes_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e50_failure_modes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
