---
name: q1009-causes-consequences
description: "Analyze the cause and the consequences of a nonconformance under ECSS-Q-ST-10-09 clause 5.2.2.3, so that the board disposes of it on evidence and the corrective-action call rests on something. Use when a departure has been raised and its review package still needs a cause chain and an impact scope. Walks the chain from the observed departure to a root the organisation actually controls, refuses a root naming the person present rather than the control that failed, scores every consequence dimension explicitly, combines the worst severity with recurrence and detectability into one integral priority number, and widens the suspect population to every unit built under the same condition when the root is systemic. Trigger: ecss, q-st-10-09, nonconformance-root-cause-chain, nonconformance-consequence-scope, systemic-root-reach, suspect-unit-population, nonconformance-priority-number, corrective-action-trigger."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-causes-consequences, nonconformance-root-cause-chain, nonconformance-consequence-scope, systemic-root-reach, suspect-unit-population, nonconformance-priority-number]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Causes and Consequences (space-systems/ecss/q1009-causes-consequences)

Use when the task is the analysis step of ECSS-Q-ST-10-09 clause 5.2.2.3
— establishing why a departure happened and how far it reaches, before
anybody proposes what to do about the item.

## Domain quick reference

- Cause and consequence are two different questions and both feed two
  different decisions. The cause decides whether corrective action is
  owed and how wide it has to be swept; the consequence decides what
  disposition the item can carry. An analysis that answers only one of
  them leaves the board deciding half blind.
- A cause chain runs from the observed departure to a root, and a root
  is a control the organisation can change. Three levels is the floor:
  what was found, the condition that produced it, and the control that
  allowed the condition. A chain stopping at the first level has named a
  mechanism and called it a cause.
- The taxonomy deliberately has no entry for the person standing there.
  A root recorded as operator error names who was present, not what let
  the error reach the item, and nothing can be swept from it. The
  refusal is the point of the taxonomy, not a gap in it.
- Each level is either evidenced or it is an assertion, and the two are
  reported separately. A chain of plausible assertions reads exactly
  like an analysis and supports nothing.
- Consequence is assessed across every dimension explicitly — function
  or performance, safety, interfaces, schedule, cost, the validity of
  qualification, and other units. A dimension left out is not a zero; it
  is the dimension nobody looked at, which is usually the one that
  matters.
- The priority number is deliberately integral: the worst dimension
  severity times the recurrence likelihood times the detection
  difficulty. Integers mean the same inputs give the same number on
  every machine, and the threshold comparison is exact rather than a
  floating-point near miss.
- Reach follows the root. A systemic root — design, material, process
  control, procedure, tooling, supplier, inspection — puts every unit
  built under the same condition in question. An item-specific root does
  not, and inflating the suspect population is as wrong as missing it.

## Workflow

1. Validate the cause chain: ordered levels, each with a statement and
   an explicit evidenced flag; the root additionally carries a taxonomy
   category and a declaration of whether the organisation controls it.
   A chain shorter than the floor is an input error.
2. Report the chain findings: a root outside the organisation's control
   cannot be acted on, and unevidenced levels are named by index rather
   than accepted.
3. Validate the consequence assessment: an integral severity for every
   dimension. A missing dimension, an unknown dimension or a severity
   off the scale is an input error.
4. Take the worst dimension severity and combine it with the recurrence
   and detection ratings into the priority number, and express it as a
   share of the worst attainable priority for reporting.
5. Derive the suspect population from the root's reach: every sharing
   unit for a systemic root, the raising unit alone otherwise. The
   raising unit is always suspect whatever the reach.
6. Decide whether corrective action is owed — any safety consequence, a
   priority at or above the threshold, or a systemic root that has
   already touched other units — and name every reason, because each one
   is swept differently.
7. Report the analysis as complete only when the root is controllable
   and every level carries its evidence.

## Pitfalls

- Stopping the chain at the condition. "The jig was on the wrong datum"
  is what happened, not why it was allowed to; corrective action against
  it fixes one jig.
- Recording a root the organisation cannot change and then raising a
  corrective action against it. The action has no owner who can close
  it, and it sits open until somebody quietly cancels it.
- Leaving a consequence dimension unassessed and reading the blank as
  nil. Interfaces and qualification validity are the two most often
  skipped and the two most expensive to discover later.
- Scoring severity on a floating-point scale. The threshold comparison
  then turns on rounding, and the same departure can earn corrective
  action on one machine and not on another.
- Sweeping every unit ever built because the root sounded systemic. The
  population is the units that shared the condition; a wider sweep costs
  the credibility of the next one.
- Sweeping only the raising unit because that is the one with the
  report. A systemic root has already produced the same departure
  elsewhere, undetected.

## Behavior contract (gate 3)

The cause-chain validation and findings, the root taxonomy refusal, the
consequence-dimension validation, the integral priority number, the
suspect-population derivation and the corrective-action decision are
exercised by the gate 3 contract test:
scripts/test_q1009_causes_consequences.py against
scripts/q1009_causes_consequences_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q1009_causes_consequences.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
