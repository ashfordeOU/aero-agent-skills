---
name: q6005-design-approval-general-provisions
description: "Assess the ECSS-Q-ST-60-05C clause 7.3.1 general provisions a hybrid circuit design approval owes whichever route it takes: an agreed procurement specification, an approved design baseline, a manufacturer capability approval, a named manufacturing line, approved materials and parts, and a documented process identification. Use when an approval package is being readied or re-checked and the question is whether the shared conditions hold before route-specific work starts. Grade every provision, refuse a waiver raised against a non-waivable provision or one missing its authority, reference or expiry, and test the approval validity window against the as-of date and any line move. Trigger: ecss, q-st-60-hybrid-scope, hybrid-design-approval-provisions, manufacturer-capability-approval, named-manufacturing-line, hybrid-approval-validity-window, non-waivable-provision, hybrid-provision-waiver."
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
  tags: [ecss, q-st-60-hybrid-scope, q6005-design-approval-general-provisions, hybrid-design-approval-provisions, manufacturer-capability-approval, named-manufacturing-line, hybrid-approval-validity-window, non-waivable-provision, hybrid-provision-waiver]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Design Approval General Provisions (space-systems/ecss/q6005-design-approval-general-provisions)

Use when the task is the route-independent half of ECSS-Q-ST-60-05C
clause 7.3 -- the clause 7.3.1 conditions a hybrid circuit design
approval rests on no matter which approval path was selected, and
whether those conditions are actually in place on a stated date.

## Domain quick reference

- Clause 7.3 branches into several approval routes. Clause 7.3.1 is the
  part that does not branch: a small set of shared conditions every
  route inherits. They look like housekeeping, and an approval granted
  with one of them open is an approval that names nothing definite.
- The provisions divide into hard gates and waivable ones. The agreed
  procurement specification, the approved design baseline, the
  manufacturer capability approval and the named manufacturing line are
  hard gates. The materials and parts list, the process identification
  document, the design data package and the change-control notification
  can be carried open against a recorded waiver.
- A waiver raised against a hard gate is not a waiver. It is an open
  provision with paperwork attached, and the assessment says so rather
  than letting the state word close the item.
- A waiver that does close an item has to carry three things: the
  authority that granted it, the reference it was recorded under, and
  the date it runs out. A waiver with no end date is an amendment to the
  requirement, not a waiver against it.
- An approval is bounded in time and bounded to a line. It expires on a
  calendar date derived from the grant date and the agreed validity
  window, and it does not follow the hardware when production moves to a
  different line. Either condition voids it whatever the provisions say.
- The validity question is evaluated against an explicit as-of date. A
  check that silently reads the day it happens to run cannot be
  reproduced, re-run against a past review date, or audited later.
- A provision marked not-applicable leaves the denominator rather than
  counting as done, so the readiness figure stays honest about what this
  particular approval actually owes.

## Workflow

1. Declare a state for every provision -- satisfied, open, waived or
   not-applicable. Reject an incomplete declaration: an undeclared
   provision is open, not absent, and defaulting it is how an approval
   package closes with a gate nobody looked at.
2. Fix the as-of date the whole assessment is made against, and use it
   for both the waiver expiries and the approval validity window.
3. Walk the provisions. An open one blocks. A waived one blocks unless
   the provision is waivable, a waiver is on file, and that waiver has
   not run out.
4. Validate each waiver structurally before trusting it: authority,
   reference and expiry, all present and non-empty.
5. Evaluate the approval validity window from the grant date and the
   agreed number of months, clamping a long grant day into a short
   month, and void the approval outright if production moved line.
6. Report the verdict in priority order -- a dead approval outranks a
   clean provision set -- together with the readiness share, the named
   blockers, and any hard gate standing open behind a waiver.

## Pitfalls

- Treating the word waived as a closed item. Half these provisions
  cannot be waived at all, and the state word is a claim about intent,
  not a verdict about the gate.
- Accepting a waiver with no expiry. It reads as a decision and behaves
  as a permanent change to the requirement, which is exactly what a
  waiver is not allowed to be.
- Reading readiness as approvability. A package can sit above ninety per
  cent ready with a hard gate open, because the weights report progress
  and say nothing about which items are permitted to stay open.
- Checking validity against today rather than a stated date. The answer
  then changes by itself between two runs of the same assessment and
  cannot be reproduced against the date a review actually took.
- Carrying an approval across a manufacturing line move. The approval
  names a line; the hardware built on the other line is outside it
  however complete the provisions look.
- Counting a not-applicable provision as satisfied. It inflates the
  readiness share and hides that the approval was scoped smaller than
  the one the numbers appear to describe.

## Behavior contract (gate 3)

The provision-state validation, weighting and readiness share, waiver
structure and expiry checks, blocking analysis, validity window and the
priority-ordered verdict are exercised by the gate 3 contract test:
scripts/test_q6005_design_approval_general_provisions.py against
scripts/q6005_design_approval_general_provisions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_design_approval_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
