---
name: q7026-harness-interface
description: "Coordinate the crimping requirements of ECSS-Q-ST-70-26C with the harness manufacturing rules of ECSS-Q-ST-20-30C so the shop works to one instruction per topic. Use when both documents reach the same harness bench and somebody has to say which governs: allocate every shared topic to one owning document, take the stricter limit where both state one in the same direction, let a declared subordination outrank the arithmetic, keep a floor and a ceiling as a band unless that band is empty, escalate two differing rules instead of quietly picking one, and report the topics neither document owns. Trigger: ecss, q-st-70-26, q-st-20-30, crimp-harness-interface, crimp-harness-topic-allocation, crimp-harness-requirement-conflict, crimp-harness-stricter-limit."
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
  tags: [ecss, q-st-70-26-crimping-scope, q-st-20-30-harness-scope, q7026-harness-interface, crimp-harness-topic-allocation, crimp-harness-requirement-conflict, crimp-harness-stricter-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Interface to the Harness Manufacturing Rules (space-systems/ecss/q7026-harness-interface)

Use when the task is the interface between ECSS-Q-ST-70-26C and
ECSS-Q-ST-20-30C — both documents reach the same harness bench, so
each shared topic needs one owning document and the shop needs one
instruction it can actually follow.

## Domain quick reference

- Every shared topic is allocated to exactly one governing document.
  A topic only one document reaches is governed by that one, and the
  interesting cases are the handful both of them reach.
- Where both state a limit in the same direction, the stricter limit
  governs and the looser one is recorded as superseded rather than
  deleted. Stricter means the larger value for a floor and the
  smaller for a ceiling, which is why the direction travels with the
  value instead of being inferred from the topic name.
- A declared subordination outranks the arithmetic. Where an
  applicability matrix makes one document senior for a topic, that
  decision governs even when the other document is stricter, because
  a project is allowed to make that call and the shop is not.
- A floor from one document and a ceiling from the other are not a
  strictness question. Together they describe a band, and the band is
  the instruction — unless the floor sits above the ceiling, in which
  case nothing can be built and the topic is a conflict.
- Two differing non-numeric rules with no subordination declared are
  an unresolved conflict. Silently preferring the crimping document
  because it is the one in hand is how a harness gets built to an
  instruction nobody approved.
- A required topic neither document reaches is a gap, not a free
  choice for the bench. It is reported so the project writes the
  instruction down somewhere before the harness is built.
- Two limits that are numerically equal agree. The comparison absorbs
  representation error from a unit conversion rather than raising a
  conflict over the last bit of a converted figure.
- A stated requirement on a topic outside the agreed list is an input
  error. The topic list is the scope of the interface, and quietly
  admitting extra topics widens it without anyone deciding to.

## Workflow

1. Validate the interface: two different document identifiers, a
   non-empty required-topic list, and a subordination map naming only
   those two documents as senior.
2. Validate each stated requirement: a document inside the interface,
   a topic, and either a limit with a direction and a numeric value
   or a rule with an identifier.
3. Reject a requirement stated on a topic outside the required list
   rather than silently widening the interface.
4. For each required topic, gather what each document says about it.
   None at all is a gap; one document only is a single-document
   allocation.
5. Where both speak, apply a declared subordination first and record
   the senior document as governing.
6. Otherwise compare: same-direction limits resolve to the stricter
   one with an exact equality recorded as agreement; opposite
   directions resolve to a band, or to a conflict when the band is
   empty; identical rules are agreement; anything else is a conflict.
7. Roll the allocations up: escalate the whole interface when any
   topic conflicts, report it reconciled with gaps when topics are
   unowned, and group the reconciled topics by governing document so
   the shop can be told where each instruction came from.

## Pitfalls

- Assuming the crimping document wins because it is the one being
  worked to. The harness document is often the stricter of the two
  on shared topics and the project may have made it senior anyway.
- Inferring strictness without the direction. The larger number is
  stricter for a floor and looser for a ceiling, and guessing from
  the topic name gets bend radius exactly backwards.
- Collapsing a floor and a ceiling into a single limit. They are a
  band, and reducing them loses half the requirement.
- Reading an empty band as merely a tight one. If the floor is above
  the ceiling nothing conforming can be built, and that is an
  escalation rather than a difficult tolerance.
- Picking one of two differing rules to keep the shop moving. That is
  the decision the project has to make and record.
- Leaving an unowned topic to the bench. Someone will decide it
  anyway, differently on each shift.

## Behavior contract (gate 3)

Interface and requirement validation, out-of-scope topic rejection,
single-document allocation, gaps, same-direction strictness in both
directions with the equality case, subordination overriding the
arithmetic, the band and empty-band cases, rule agreement and rule
conflict, and the reconciled, gapped and escalated verdicts are
exercised by the gate 3 contract test:
scripts/test_q7026_harness_interface.py against
scripts/q7026_harness_interface_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7026_harness_interface.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
