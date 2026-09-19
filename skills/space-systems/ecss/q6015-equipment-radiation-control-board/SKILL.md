---
name: q6015-equipment-radiation-control-board
description: "Verify that an equipment radiation control board is constituted and its dossier complete. Use when ECSS-Q-ST-60-15C clause 5.4 has to be applied to a board sitting: confirm every mandatory role is represented by somebody present, that a chair is appointed and is not the design authority under review, that quorum is met, then reconcile the equipment parts list against the radiation analyses, insist each analysis carries a margin against a stated requirement with an evidence reference, require an owned and dated action behind every shortfall, and issue one clearance verdict. Trigger: ecss, q-st-60-15c-clause-5-4, equipment-radiation-control-board, board-chair-independence, radiation-analysis-coverage-reconciliation, radiation-margin-shortfall-action, board-clearance-verdict, board-quorum-roles."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-equipment-radiation-control-board, q-st-60-15c-clause-5-4, board-chair-independence, radiation-analysis-coverage-reconciliation, radiation-margin-shortfall-action, board-clearance-verdict, board-quorum-roles]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Equipment Radiation Control Board (space-systems/ecss/q6015-equipment-radiation-control-board)

Use when the task is the board of ECSS-Q-ST-60-15C clause 5.4 — who
has to be in the room for a radiation clearance to mean anything, and
what the board has to be handed before it is entitled to clear an
equipment at all.

## Domain quick reference

- The board is a composition requirement before it is a review. The
  radiation effects engineer who did the analyses, product assurance,
  the design authority whose design is under examination, the
  component engineer who owns the parts list, and the customer's
  representative each bring a veto the others cannot exercise, so a
  role unrepresented is a question nobody in the room can answer.
- Represented means present. A named member who did not attend covers
  nothing, which is why the composition check runs over attendance
  rather than over the distribution list.
- The chair is an independence requirement. A board chaired by the
  design authority is the design reviewing itself, and it is the one
  composition defect that survives a full attendance list.
- Completeness comes before judgement. The board's first job is to
  find out whether the dossier is whole: every part on the parts list
  carrying an analysis for every effect it is exposed to, and no
  analysis presented for a part that is not on the list. The second
  case is the more interesting one — it means the parts list and the
  analysis set have drifted apart, and one of them is stale.
- A margin without a stated requirement is not a margin, and a margin
  without an evidence reference cannot be re-derived after the
  meeting. Both are completeness defects, not judgement calls.
- A shortfall is not something a board absorbs. It leaves the room as
  an action with an owner and a date, and an action already past its
  date when the board sits is itself reportable — it says the previous
  board's decision was never carried out.
- The verdict is one of three. Cleared, cleared subject to actions, or
  not cleared; and nothing is cleared while any completeness defect
  stands, however comfortable the margins are.

## Workflow

1. Validate the member list: unique ids, known roles, boolean
   attendance and chair flags.
2. Run the composition check over the members actually present: every
   mandatory role represented, exactly one chair, that chair not the
   design authority, and enough members present for quorum.
3. Validate the parts list and the analyses, then reconcile them both
   ways: a part-effect with no analysis, and an analysis for a part
   the list does not contain.
4. Check each analysis for a margin, a stated required margin and an
   evidence reference; an analysis missing a margin is reported and
   not graded further, because there is nothing to grade.
5. Compare each margin with its requirement, letting an exact equality
   pass under a named relative tolerance, and require an action whose
   subject names that part and effect behind every shortfall.
6. Check the actions themselves: an owner on each, and no open action
   whose due date is already behind the board date.
7. Concatenate the four finding sets, list the open actions, and issue
   the verdict: not cleared if anything was found, cleared subject to
   actions if actions remain open, cleared otherwise.

## Pitfalls

- Checking the invitation list instead of the attendance. The roles
  are there to answer questions during the meeting.
- Letting the design authority chair because they know the design
  best. That is the reason they cannot chair.
- Reconciling the parts list against the analyses in one direction
  only. The missing analysis is the obvious defect; the orphan
  analysis is the one that reveals a stale parts list.
- Grading a margin that has no stated requirement. Without the
  requirement, the number is a ratio with no verdict attached to it.
- Accepting a shortfall because the board discussed it. A discussion
  that produced no owned, dated action leaves nothing behind.
- Clearing an equipment whose margins are all comfortable while a
  part-effect analysis is missing. The comfortable margins are the
  ones that were done.
- Failing a margin that lands exactly on its requirement. The equality
  is a representation question, settled inside the comparison.

## Behavior contract (gate 3)

The member validation, attendance-based composition and chair
independence checks, quorum rule, two-way parts-list reconciliation,
margin and evidence completeness checks, shortfall-to-action linking,
action owner and overdue checks and the three-way verdict are
exercised by the gate 3 contract test:
scripts/test_q6015_equipment_radiation_control_board.py against
scripts/q6015_equipment_radiation_control_board_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6015_equipment_radiation_control_board.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
