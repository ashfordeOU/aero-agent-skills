---
name: q60-class-1-parts-control-board
description: "Use when a board minute has to become a part use verdict. Determine whether the parts control board has actually approved an electronic part for use at the highest reliability class under ECSS-Q-ST-60C clause 4.1.3: refuse a board missing a seat or a reference, test the quorum as attendance plus the chair rather than a headcount alone, weight the votes cast so an abstention withholds support, route each part category to the concurrences it depends on, require a decision reference and a recorded dissent before the decision stands, and name every absent, dissenting and abstaining seat. Trigger: ecss, q-st-60c-clause-4-1-3, class-one-parts-control-board, parts-control-board-quorum, parts-control-board-weighted-vote, parts-control-board-concurrence-route, parts-control-board-decision-record."
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
  tags: [ecss, q-st-60-eee-component-selection-scope, q60-class-1-parts-control-board, class-one-parts-control-board, parts-control-board-quorum, parts-control-board-weighted-vote, parts-control-board-concurrence-route, parts-control-board-decision-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components -- Class 1 Parts Control Board (space-systems/ecss/q60-class-1-parts-control-board)

Use when the task is the clause 4.1.3 approval-route question of
ECSS-Q-ST-60C at the highest reliability class: a part has been put to
the parts control board, and the question is whether what the meeting
produced is an approval the part may be used under.

## Domain quick reference

- At this class a part is not selected by the engineer who wants it. It
  goes to a standing board whose seats represent the disciplines that
  carry the consequences -- product assurance in the chair, part
  engineering, the design authority, procurement quality, reliability
  and radiation, and the customer -- and it may be used once that board
  has said so on the record.
- A board is constituted or it is not. Every required seat carries a
  named member and a vote weight before the first meeting. A seat that
  exists only on the day it agrees with the proposer is not a seat, so a
  missing seat or a missing board reference closes the assessment before
  any vote is read.
- Quorum is attendance plus the chair, and the two are tested
  separately. A meeting that loses the chair loses the authority the
  chair carries however many members attended. An attendance share
  landing exactly on the declared minimum is quorate, the comparison
  tolerance being there to absorb representation error rather than to
  lower the minimum.
- The approval threshold is weighted and an abstention is not a vote in
  favour. The share is taken over the weight of every seat present, so
  abstaining lowers the share exactly as much as it withholds support,
  which is what stops a thin room from waving a part through on two
  votes and four shrugs.
- Depth of approval follows the part, not the meeting. A standard
  qualified part needs the board. An upgraded part needs part
  engineering and the reliability and radiation seat to concur with it.
  A part outside the standard route needs the customer to concur as
  well, because the customer carries what that part does in orbit, and a
  concurrence is support actually cast rather than an absence read as
  assent.
- The record is part of the decision. A minute with no decision
  reference approves nothing, and a minute that drops the dissent does
  not say what the board decided -- it says what the proposer heard.
- The carried share is worth as much as the verdict. A part carried on
  the threshold and one carried unanimously read the same in a status
  table, and the first will not carry again once a seat changes hands.

## Workflow

1. Validate the board policy first: the minimum attendance share, the
   weighted approval threshold, the marginal band inside which a carried
   part is still advised on, and whether the chair presence and the
   decision record are required. A threshold above one or at zero, an
   attendance share outside the unit interval, or a marginal band wider
   than the threshold is refused rather than used.
2. Validate every seat: a recognised role, no role seated twice, a
   non-blank member name and a positive vote weight. A board with an
   unseated required role, or with no board reference, closes the
   assessment on board not constituted.
3. Validate the part request: a named part, a recognised category, a
   decision reference that may be blank but is then read as no record, a
   boolean dissent flag and a votes mapping.
4. Test the quorum: the chair in the room when the policy requires it,
   and the attendance share at or above its minimum with a tolerance
   that absorbs representation error. Report the absent seats by name.
5. Validate the votes: one vote per seat present, no vote from an absent
   or unseated role, and every vote for, against or abstaining. A
   present seat that cast nothing makes the record incomplete rather
   than neutral.
6. Take the weighted share in favour over the weight present, then check
   the decision reference, the dissent record when any seat voted
   against, the concurrences the part category depends on, and finally
   the share against the approval threshold.
7. Report the attendance share, the carried share, the unseated, absent,
   dissenting and abstaining seats and the missing concurrences, and
   raise an advisory when the part carried inside the marginal band.
   Close on one verdict: board not constituted, quorum not met, decision
   not recorded, concurrence missing, part use refused, or part use
   approved.

## Pitfalls

- Counting heads for the quorum. Attendance and the chair are two
  conditions, and a quorate-looking room without its chair has no
  standing to release a part.
- Reading an abstention as assent. The denominator is the weight in the
  room, so a seat that will not support the part lowers the share; a
  concurrence is support actually cast, and an absent seat concurs with
  nothing.
- Approving a part outside the standard route without the customer. The
  category sets the concurrence depth, and the customer is the one
  carrying what that part does after launch.
- Minuting the outcome and dropping the dissent. A decision with no
  reference, or with unrecorded votes against, is not a decision the
  part can be used under whatever the share was.
- Reporting a bare approval. The carried share, the absent seats and the
  dissent are what the next board is compared against, and the verdict
  word carries none of them.

## Behavior contract (gate 3)

The policy validation, seat validation, the unseated and absent seat
lists, the attendance share, the chair and quorum tests, the vote
validation, the weighted carried share, the dissent and abstention
lists, the category concurrence route, the decision record check, the
marginal advisory and the board verdict are exercised by the gate 3
contract test:
scripts/test_q60_class_1_parts_control_board.py against
scripts/q60_class_1_parts_control_board_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_parts_control_board.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
