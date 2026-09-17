---
name: q60-class-3-selection-general-requirements
description: "Audit whether a candidate Class 3 EEE part is ready to be taken to a procurement decision under clause 6.2.1 of ECSS-Q-ST-60C: declare every selection prerequisite as closed, open or not applicable, treat an undeclared one and an unjustified not-applicable as open, refuse a waiver raised against a blocking prerequisite, weight the prerequisites that still apply, compute the readiness index over them, list the blockers left standing and name the one prerequisite worth closing next. Use when a project has to show the ground a Class 3 part choice stands on before the purchase order goes out. Trigger: ecss, q-st-60c, q60-class-3-selection-general-requirements, q60-c3-selection-prerequisite-ledger, q60-c3-selection-readiness-index, q60-c3-blocking-prerequisite, q60-c3-selection-waiver-refusal, q60-c3-procurement-release."
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
  tags: [ecss, q-st-60c-eee-selection-scope, q-st-60c, q60-class-3-selection-general-requirements, q60-c3-selection-prerequisite-ledger, q60-c3-selection-readiness-index, q60-c3-blocking-prerequisite, q60-c3-selection-waiver-refusal, q60-c3-procurement-release]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Part Selection Before Procurement (space-systems/ecss/q60-class-3-selection-general-requirements)

Use when the task is clause 6.2.1 of ECSS-Q-ST-60C: the overarching
expectations a Class 3 part selection has to satisfy before anybody commits to
buying it. The leaf turns a scattered set of "we are looking into it" answers
into one ledger, one number and one next action.

## Domain quick reference

- The prerequisites are not equal, in two independent ways. They differ in
  weight, which is how much of the selection case rests on them, and they
  differ in whether they block: a blocking prerequisite stops the purchase
  order outright, a non-blocking one only costs the project later. Collapsing
  those two axes into a single tick-list is what lets a heavy blocker hide
  behind nine light greens.
- An undeclared prerequisite is open, not absent. A ledger silently missing an
  entry reads as clean precisely where nobody looked, which is the reverse of
  what a readiness reading is for.
- Not applicable is a claim, and a claim needs a justification on record.
  Without one it stays inside the denominator and stays open; a blank string in
  the justification field is the same as no field at all.
- A waiver on a blocking prerequisite is refused. Blocking is what the word
  means: the decision cannot be argued around, and a granted waiver on one is a
  worse finding than the open item it was meant to clear. On a non-blocking
  prerequisite a waiver with a recorded rationale does close the item, but it
  closes it under waiver and is carried as a residual, never printed as
  evidence.
- The readiness index reads only what still applies. A justified
  not-applicable leaves the denominator entirely, so a part legitimately
  exempt from a check is not penalised for it.
- A number without a next action is half an answer. The prerequisite worth
  closing next is the blocking one first, then the heaviest, then ledger order,
  so the answer is stable between runs.

## Workflow

1. Validate the candidate: a part identifier, and a prerequisite ledger whose
   every name is one the standard's selection expectations actually raise. An
   unrecognised name is an input error, not a bonus check.
2. Resolve every prerequisite in the fixed ledger, not only the ones the
   project declared, so an omission surfaces as an open item.
3. Read each declaration: closed is satisfied; not applicable with a recorded
   justification leaves the denominator; not applicable without one stays open
   and is reported.
4. Handle waivers before anything else is concluded. Refuse one on a blocking
   prerequisite, ignore one that was never granted, and refuse one carrying no
   rationale.
5. Weight the prerequisites that still apply, and compute the readiness index
   as the satisfied share of that weight rather than a count of ticks.
6. List the blocking prerequisites still open, then name the single one worth
   closing next under the blocking-then-heaviest-then-ledger-order rule.
7. Release to procurement only when no blocker stands and the index meets the
   agreed level, absorbing floating-point representation error at the boundary
   with a named tolerance rather than by lowering the level. Rank the findings
   worst first.

## Pitfalls

- Counting prerequisites instead of weighting them. Nine light items closed
  against one heavy item open reads as ninety percent ready and is not.
- Reading a missing ledger entry as a closed one. The entry is missing because
  nobody did the work, which is the case the ledger exists to catch.
- Accepting a bare not-applicable. Exemption is a claim about this part in this
  application, and an unrecorded claim cannot be reviewed later.
- Letting a waiver clear a blocking prerequisite. That is the one thing a
  waiver cannot do, and a granted one is itself the finding to report.
- Printing an item closed under waiver as evidence. It closed on a decision,
  not on a result, and the distinction is what a later review needs.
- Widening the required readiness so an exactly-met candidate passes. An
  equality at the boundary is a representation question handled by the
  tolerance inside the comparison; the agreed level stays where it was agreed.

## Behavior contract (gate 3)

The candidate validation, fixed prerequisite ledger, declaration resolution,
not-applicable justification rule, waiver refusal on blocking items,
weighted readiness index, blocker listing, next-to-close selection and ranked
findings are exercised by the gate 3 contract test:
`scripts/test_q60_class_3_selection_general_requirements.py` against
`scripts/q60_class_3_selection_general_requirements_logic.py` (stdlib
unittest, offline). Run:
`python3 scripts/test_q60_class_3_selection_general_requirements.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
