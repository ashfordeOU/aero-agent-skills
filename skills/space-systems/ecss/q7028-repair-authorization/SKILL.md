---
name: q7028-repair-authorization
description: "Validate the authorization behind a proposed board repair or modification before any iron reaches the hardware. Use when a repair request is being signed off, an approval chain is being assembled, or a repair file is audited after the fact: it derives the minimum approving authority from the work type, the hardware model, the criticality of the function and whether the method is a listed one, compares that against the signature actually obtained, lists the file entries still owed, and grades the retention the record has to survive. Trigger: ecss, q-st-70-28c-board-repair, pcb-repair-authorization, pcb-repair-approval-chain, pcb-repair-records, pcb-repair-design-authority, pcb-repair-file-retention."
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
  tags: [ecss, q-st-70-28c-board-repair, q-st-70-28c, q7028-repair-authorization, pcb-repair-authorization, pcb-repair-approval-chain, pcb-repair-records, pcb-repair-design-authority, pcb-repair-file-retention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Repair Authorization (space-systems/ecss/q7028-repair-authorization)

Use when the task is the authorization clause of ECSS-Q-ST-70-28C: a repair or
a modification has been proposed on a board that has already been accepted,
and the question is who has to approve it and what the file has to hold before
the work may start.

## Domain quick reference

- Approval runs on a ladder, not a list. Operator, inspector, quality
  assurance, design authority and customer are ordered, so "approved" is only
  meaningful next to the rung it was given at, and a signature one rung short
  of the requirement is a refusal rather than a formality.
- Several drivers set the floor at once and the highest of them wins. The work
  type, the hardware model, the criticality of the function the board carries
  and whether the method is a listed one each put a minimum under the approval;
  satisfying three of the four is still not authorized.
- A modification is owned by the design authority because it changes what the
  drawing says. Quality assurance can accept a board built to its design; it
  cannot decide that the design is now something else.
- A method outside the listed catalogue reaches the customer every time. The
  standard's assurance rests on methods whose behaviour is known, and an
  invented method has no such history, so the acceptance of the risk is the
  customer's to give.
- The file is the deliverable, not the repaired board. Request, damage,
  method, operator, inspection result and date are the base entries; a
  modification adds the drawing and as-built references, and a customer-level
  approval adds its own reference.
- A blank entry is a missing entry. A key present with an empty string reads as
  complete to a careless audit and holds no traceability at all, so it is
  counted with the absent ones.
- Retention outlives the hardware. The repair file has to answer questions
  asked years after flight, so a short declared retention is a finding at the
  moment of approval, not at the moment the file is destroyed.

## Workflow

1. Resolve the minimum approving authority from the work type, the hardware
   model and the criticality level, taking the highest of the three.
2. Raise that minimum to customer level where the proposed method is outside
   the listed catalogue.
3. Rank the authority actually obtained on the same ladder and report how many
   rungs short it falls, if any.
4. Build the expected record list — base entries, plus the modification
   entries and the customer reference where those apply — and name every entry
   that is absent or blank.
5. Grade the declared retention period against the programme minimum.
6. Return the verdict with required and obtained authority, the missing
   entries, and every finding; authorize only when there are none.

## Pitfalls

- Reading "approved" without reading the rung. An inspector's signature on a
  flight repair looks like an approval in the file and is not one, and the
  defect is only found when the chain is reconstructed.
- Letting one satisfied driver stand for all of them. The hardware model is
  right, so the criticality of the function is never brought in, and a level 1
  item ships on a quality-assurance signature.
- Sending a modification up the repair chain. The board is now different from
  its drawing and the only authority that could have said so was never asked.
- Treating an invented method as a repair like any other. It reaches the bench
  with a local approval, and the one body that would have priced the unknown
  risk never saw it.
- Accepting an empty field as a filled one. The audit counts keys rather than
  content, the file passes, and the operator who did the work cannot be named
  afterwards.
- Declaring a retention that ends before the questions do. The hardware is
  still flying and the evidence for its repair has already been destroyed.

## Behavior contract (gate 3)

The authority ladder, the highest-driver rule, the unlisted-method escalation,
the record list for repairs, modifications and customer approvals, blank-entry
handling and the retention minimum are exercised by the gate 3 contract test:
scripts/test_q7028_repair_authorization.py against
scripts/q7028_repair_authorization_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7028_repair_authorization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
