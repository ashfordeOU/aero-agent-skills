---
name: q60-class-3-parts-control-board
description: "Determine whether a class 3 part usage needed a parts control board approval at all and whether the approval it holds stands, under ECSS-Q-ST-60C clause 6.1.3: count only the recognised customer triggers that are active and carry a reference, refuse an approval taken after the procurement commitment, one naming no board chair, one with the customer unrepresented, one covering the selection but not the usage or one identifying no part, then take docket readiness across the usages against its floor under a named tolerance. Use when a class 3 part approval file has to become a board verdict. Trigger: ecss, q-st-60c-clause-6-1-3, class-3-customer-triggered-board, board-trigger-evidence-reference, selection-and-usage-approval-scope, board-approval-commitment-lead, class-3-board-docket-readiness."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q60-class-3-parts-control-board, q-st-60c-clause-6-1-3, class-3-customer-triggered-board, board-trigger-evidence-reference, selection-and-usage-approval-scope, board-approval-commitment-lead, class-3-board-docket-readiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 3 — Customer-Triggered Parts Control Board (space-systems/ecss/q60-class-3-parts-control-board)

Use when the task is clause 6.1.3 of ECSS-Q-ST-60C: the board approval of part
selection and usage that a customer calls for on class 3 equipment. This leaf
decides whether the board was owed an appearance at all, and then whether the
approval on file actually stands.

## Domain quick reference

- On class 3 the board is convened because the customer asked, not by default.
  Running every usage past a board nobody called for costs schedule and teaches
  the project to treat the board as paperwork.
- A trigger is a fact with a reference behind it. A contract clause, a written
  request, a function the customer flagged, a reserved part family or a
  response to a deviation each name a document, and a trigger nobody can point
  at convenes nothing.
- An inactive trigger is still worth reading. It records that the condition was
  looked at and did not apply, which is what the reviewer wants to see when the
  board never met.
- Selection and usage are two approvals. The board can be satisfied that the
  part is a sound choice and still not have looked at where this equipment puts
  it, and an approval covering one has not covered the other.
- An approval dated after the procurement commitment is a ratification. The
  money was spent, the lot was cut, and the board reviewed a decision it could
  no longer change.
- The customer triggered the board, so the customer sits on it. An approval
  taken with no customer representative answers a question the customer asked
  without the customer in the room.
- The docket carries no allowance. One usage short of an approval is one part
  in the equipment with nothing behind it, so readiness is judged against a
  floor of every usage cleared.

## Workflow

1. Read the triggers declared against the usage and keep the recognised ones,
   reporting any name the programme does not know.
2. Keep as active only the triggers marked active that carry a reference, and
   report an active trigger with no reference as a defect in its own right.
3. Decide whether a board approval is required: it is required when at least
   one trigger survives step 2, and not otherwise.
4. Where it is required, test the approval record: raised on or before the
   procurement commitment day, a board chair named, a customer representative
   present, both the selection and the usage inside its scope, and the part
   identified.
5. Report the lead between the approval and the commitment in days, negative
   when the project committed first.
6. Return one disposition per usage: board-approval-not-required,
   board-approval-valid, board-approval-deficient, or board-approval-missing
   when no approval record exists at all.
7. Take docket readiness as the share of usages cleared and judge it against
   the floor under the stated tolerance.

## Pitfalls

- Convening the board by default because a higher class would have. The class 3
  board answers a customer call, and a standing board that meets on everything
  stops reading what it approves.
- Counting a trigger nobody can reference. A remembered conversation puts a
  usage on the docket and gives the board nothing to bound the decision with.
- Reading an approval of the part as an approval of the usage. The same part is
  sound in one position and outside its rating in the next.
- Accepting an approval dated after the commitment. It reads identically in the
  file and had no power to change anything.
- Holding the board without the customer. The trigger was the customer's, and
  the answer goes back to them unseen.
- Treating a missing approval and a flawed one as the same finding. One is a
  meeting that never happened and the other is a meeting to repair, and the
  recovery is different.
- Averaging the docket. A readiness of nine in ten is one part in the equipment
  with no approval behind it, which is why the floor is every usage cleared.

## Behavior contract (gate 3)

The trigger recognition, the active-trigger test, the requirement decision, the
approval record defects, the selection and usage scope coverage, the
commitment lead in days, the per-usage disposition, the ordered docket and the
readiness floor are exercised by the gate 3 contract test:
scripts/test_q60_class_3_parts_control_board.py against
scripts/q60_class_3_parts_control_board_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_3_parts_control_board.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
