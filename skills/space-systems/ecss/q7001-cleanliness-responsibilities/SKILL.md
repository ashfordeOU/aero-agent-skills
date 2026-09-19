---
name: q7001-cleanliness-responsibilities
description: "Define who holds each cleanliness activity on a project under ECSS-Q-ST-70-01C, covering the facility operators and the suppliers alongside the prime's own organisation. Use when a control plan needs its responsibility matrix built, or an existing one has to be shown to leave nothing unowned. Requires exactly one accountable party and at least one party carrying out each activity, a facility party in the loop wherever the facility decides the outcome, a supplier assigned to work done at a supplier with the requirement holder still accountable, and verification by somebody who did not do the cleaning. Trigger: ecss, q-st-70-01, cleanliness-responsibility-matrix, cleanliness-accountable-party, facility-operator-cleanliness-role, supplier-cleanliness-flow-down, cleanliness-verification-independence, cleanliness-activity-coverage."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-cleanliness-responsibilities, cleanliness-responsibility-matrix, cleanliness-accountable-party, facility-operator-cleanliness-role, supplier-cleanliness-flow-down, cleanliness-verification-independence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Responsibilities (space-systems/ecss/q7001-cleanliness-responsibilities)

Use when the task is the responsibility half of the ECSS-Q-ST-70-01C
programme clause — assigning every cleanliness activity to a named
party, including the facility operators and suppliers whose work
decides the result but who sit outside the prime's own organisation.

## Domain quick reference

- The rules turn on what kind of party an actor is, not on its name. A
  facility operator, a subsystem supplier and the prime's own product
  assurance carry different obligations for the same activity, so the
  matrix is grouped by party kind before it is graded.
- Exactly one party is accountable for an activity. None means the
  activity has no owner and will be discovered unowned at the first
  non-conformance; two means each can point at the other, which is the
  same state with more signatures.
- Accountability and execution are different columns. A party can be
  accountable for cleaning it does not perform, and the party that
  performs it is the one to name when the work has to be scheduled and
  resourced, so both have to be present.
- The facility decides the outcome of several activities outright.
  Environment monitoring, cleaning, witness samples and storage all
  happen in somebody else's building to somebody else's procedures, and
  a matrix naming only the prime for those describes an intention
  rather than an arrangement.
- Being informed is not being in the loop. A facility operator copied
  on the result has no say in how the activity is run, which is the
  distinction the check between consulted and informed exists to keep.
- Requirements flow down; accountability does not go with them. Work
  carried out at a supplier needs that supplier named as carrying it
  out, and the party holding the requirement still accountable for it.
  A matrix that moves both has transferred the requirement, not
  delegated the work.
- Verification is only verification when somebody other than the
  cleaner can sign it. A team grading its own work has no mechanism for
  reporting that the work fell short.

## Workflow

1. Validate the actors: each named once, each given one of the
   recognised party kinds. An unrecognised kind is refused rather than
   defaulted, because every later rule depends on it.
2. Validate the matrix: every activity a known one, every assignment
   naming a known actor and a recognised role.
3. List the activities the matrix leaves out entirely, and report the
   coverage share over the full activity set.
4. For each assigned activity, require exactly one accountable party
   and at least one party carrying it out; report zero and multiple
   accountability separately, because they are different failures.
5. For each activity the facility decides, require at least one
   facility party accountable, carrying it out, or consulted. A
   facility party merely informed does not satisfy this.
6. For each activity declared as carried out at a supplier, require a
   supplier carrying it out and an accountable party that may retain
   accountability for work done elsewhere.
7. Compare the parties verifying cleanliness with those that performed
   the cleaning, and report a verification set drawn entirely from the
   cleaners.
8. Summarise the roles each actor holds, report any actor named in the
   plan with no role at all, and call the assignment complete only when
   no finding stands.

## Pitfalls

- Assigning the matrix to organisations rather than to the activities.
  Coverage then looks complete because every organisation appears
  somewhere, while individual activities remain unowned.
- Naming two accountable parties to keep both organisations content. It
  reads as thoroughness in the review and resolves to nobody at the
  first disagreement.
- Leaving the facility out because it is on contract. The contract says
  what the facility is paid for; the matrix says who decides, and the
  cleanliness result is decided in the facility.
- Marking the facility or the supplier as informed and treating that as
  coverage. Informed parties receive outcomes and change none of them.
- Delegating accountability with the work. Once the supplier is
  accountable, the party that owes the requirement to the customer has
  no route to enforce it short of a contract change.
- Letting the cleaning team verify its own cleaning. Every reading is
  then produced by the party with the strongest reason for it to pass,
  and no independent evidence exists that it ever did.

## Behavior contract (gate 3)

The actor and matrix validation, activity coverage, single-point
accountability and execution checks, facility-party involvement,
supplier flow-down with retained accountability, verification
independence and the per-actor role summary are exercised by the gate 3
contract test: scripts/test_q7001_cleanliness_responsibilities.py
against scripts/q7001_cleanliness_responsibilities_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_cleanliness_responsibilities.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
