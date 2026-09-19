---
name: q2007-test-sequence
description: "Structure a test campaign plan against the typical test process sequence offered by ECSS-Q-ST-20-07C Annex B: lay the planned phases on the reference flow, report a mandatory phase that is neither planned nor omitted against a recorded tailoring rationale, name every adjacent pair that runs the flow backwards, flag a rationale left behind for a phase that is planned anyway, and lay the durations into contiguous day windows so the plan carries a schedule. Use when a campaign plan is being drafted or an offered sequence is being compared with the reference. Trigger: ecss, q-st-20-07c, typical-test-process-sequence, test-campaign-phase-ordering, test-phase-precedence-conformance, test-sequence-tailoring-rationale, campaign-phase-day-windows."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-test-sequence, typical-test-process-sequence, test-campaign-phase-ordering, test-phase-precedence-conformance, test-sequence-tailoring-rationale, campaign-phase-day-windows]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres -- Reference Test Process Sequence (space-systems/ecss/q2007-test-sequence)

Use when the task is laying a test campaign plan against the Annex B
reference flow of ECSS-Q-ST-20-07C: a sequence of phases has been
proposed and the question is whether it covers the typical process, runs
in the right direction, and adds up to a schedule.

## Domain quick reference

- The reference flow is informative, so conformance is a comparison and
  not a pass mark. What it fixes is the direction: request, specify,
  prepare, configure, review, run, package, report. A plan is graded on
  coverage and order against that flow, not on matching it phase for
  phase.
- Mandatory and optional are different failures. An optional phase left
  out -- a facility feasibility study, an incoming inspection, an item
  return leg -- is a campaign choice. A mandatory phase left out is a
  gap unless somebody wrote down why, and the rationale is what turns an
  omission into tailoring.
- Order violations are local. A single phase dropped into the wrong slot
  produces one inversion against its neighbour, and reporting the pair is
  what makes it fixable; reporting only that the plan is unordered sends
  the planner back through the whole list.
- A stale tailoring rationale is worth reporting. A rationale recorded
  for a phase that is planned anyway usually means the plan changed and
  the justification file did not, and the next reviewer will read the
  rationale as still applying.
- The durations are what turn the flow into a campaign. Contiguous day
  windows from the campaign start give each phase a slot and the campaign
  a total, which is the number the facility booking is made against.

## Workflow

1. Normalise the proposed plan: phase, duration in whole days, in the
   planner's own order. Reject an unknown phase, a phase planned twice,
   and a non-positive or fractional duration.
2. Normalise the tailoring rationales and refuse one that names a phase
   outside the reference flow or carries no text.
3. Grade coverage phase by phase over the mandatory set: planned,
   tailored against a rationale, or an omission that blocks.
4. Report any rationale recorded for a phase that is in fact planned.
5. Walk the plan and name every adjacent pair whose reference positions
   run backwards.
6. Lay the durations into contiguous windows from the campaign start day
   and take the campaign total from the first and last window.
7. Return the mandatory coverage fraction, the order verdict and the
   decision: conforms, conforms with tailoring, or non-conforming.

## Pitfalls

- Reading full coverage as conformance. A plan can contain every
  mandatory phase and still run the review after the test; coverage and
  order are graded separately and both appear in the decision.
- Treating an omission as tailoring because somebody mentioned it. The
  rationale has to be recorded against the phase, otherwise the next
  reviewer cannot tell a decision from an oversight.
- Reporting a single unordered verdict. Every inversion is a pair, and
  the pair is what the planner moves.
- Grading optional phases as gaps. They are in the flow because a
  campaign often needs them, not because every campaign does, and
  raising them as findings buries the mandatory omission that matters.
- Summing durations without laying out the windows. The total is the same
  number, but the window is what shows the facility when each phase
  actually occupies it.

## Behavior contract (gate 3)

The reference flow, the plan and tailoring normalisation, the mandatory
coverage grading, the stale-rationale report, the adjacent-pair order
check, the contiguous day windows and the conformance decision are
exercised by the gate 3 contract test:
scripts/test_q2007_test_sequence.py against
scripts/q2007_test_sequence_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_test_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
