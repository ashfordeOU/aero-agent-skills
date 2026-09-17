---
name: q60-class-2-parts-control-board
description: "Evaluate whether the approval route an electronic part actually took is the route that part needed at reliability Class 2 under ECSS-Q-ST-60C clause 5.1.3: refuse a submission with no part reference, category, outcome or dates, route each category to its lowest permitted decision level, refuse a level below it, test the seated quorum and the chair behind the level taken, require the evaluation evidence, customer agreement and minute the level rests on, and flag every part committed before its decision. Use when a board record has to become a part usage verdict. Trigger: ecss, q-st-60c-clause-5-1-3, reliability-class-2-parts-control-board, parts-board-approval-route-level, parts-board-standing-delegation-limit, parts-board-submission-package-readiness, parts-board-decision-turnaround."
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
  tags: [ecss, q-st-60-eee-component-selection-scope, q60-class-2-parts-control-board, reliability-class-2-parts-control-board, parts-board-approval-route-level, parts-board-standing-delegation-limit, parts-board-submission-package-readiness, parts-board-decision-turnaround]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components -- Class 2 Parts Control Board Route (space-systems/ecss/q60-class-2-parts-control-board)

Use when the task is the clause 5.1.3 approval-route question of
ECSS-Q-ST-60C at reliability Class 2: a part has been selected and put
into use, and the question is whether the route that cleared it is the
route its category needed, rather than whether a board exists.

## Domain quick reference

- The board is a route, not a meeting. What the clause turns on is the
  level at which a given category of part may be cleared, so every
  submission is routed to its lowest permitted level and the level it
  actually took is compared against that.
- Not every part needs the full board. A part already on the approved
  range can be cleared by a delegated chair decision, which is what
  keeps the board usable; the standing limit on that delegation is the
  category list, and a part off the range cleared that way is the
  failure this route exists to prevent.
- A level above the one needed is never a defect. Taking a routine part
  to the full board wastes an agenda slot and nothing else, so the
  comparison is one-sided: at or above what the category needs.
- A board level rests on the board having been there. The mandatory
  functions carry the quorum, an accepted proxy counts as a seat because
  the function was represented, and a delegated decision rests instead
  on the chair having sat at all.
- The evidence a level rests on is part of the level. A category that
  depends on an evaluation programme and cites no evaluation result was
  not decided, it was assumed; a level reaching as far as customer
  agreement needs that agreement recorded, not intended.
- A decision with no minute is not a decision. It is one person's
  recollection of a room, and it is what an audit finds two years later
  when the part is already flying.
- Commitment order matters as much as the decision. A part ordered
  before the board met was decided by the schedule, and the board record
  is then a formality written around a purchase.
- Turnaround is a real control at this class. A route that is correct
  and takes four months pushes projects into committing early, so the
  days from submission to decision are aged against a declared limit.

## Workflow

1. Read the board as it sat: validate every seat against the known
   functions, refuse a function seated twice, count a seat as taken when
   its holder attended or an accepted proxy stood in, and derive the
   quorum over the mandatory functions alone.
2. Validate and dispose of every submission. A record missing its
   reference, category, outcome, route or dates cannot be routed and
   stops there.
3. Refuse an unrecognised category, outcome or route, a repeat of a
   reference already decided, and a decision dated before the submission
   it answers.
4. Close a rejected or deferred submission as a decision taken. It is
   not an approval and it is not a finding; only a usable outcome
   carries on into the route tests.
5. Refuse an approval taken on an incomplete data package, then compare
   the route taken with the level the category needs and refuse
   anything below it.
6. Test what the level rests on: quorum and a minute reference for a
   board route, the chair having sat for a delegated one, an evaluation
   reference where the category depends on one, and a recorded customer
   agreement where the level reaches that far.
7. Flag a part committed to procurement before its decision day, age the
   decision against the declared turnaround, and report the approved
   parts, the approval share and the findings ranked most severe first,
   closing on one verdict: board route sound, or board route not
   established.

## Pitfalls

- Grading attendance instead of the route. A full board that cleared an
  off-range part without the customer agreement its level needs is a
  well-attended defect.
- Reading a chair delegation as a shortcut available to any part. The
  delegation has a standing limit written into the category list, and
  the whole value of the route is that the limit is checked rather than
  assumed.
- Counting a rejection as a failure of the board. A refused part is the
  route working; what is graded is whether the decision was taken at the
  right level on a complete package.
- Accepting an approval with the evaluation still to come. The category
  needing evaluation is exactly the one where an assumed result is worth
  a flight failure, so the reference is required before the approval
  stands.
- Reporting the verdict without the approval share and the turnaround. A
  board approving everything in ninety days and one approving most
  things in a week read identically in the verdict word.

## Behavior contract (gate 3)

The seat and chair validation, the quorum derivation, the submission
completeness and disposition, the category-to-level routing, the
one-sided level comparison, the quorum, minute, evaluation and customer
agreement tests, the commitment-order and turnaround checks, the
approval share and the board verdict are exercised by the gate 3
contract test: scripts/test_q60_class_2_parts_control_board.py against
scripts/q60_class_2_parts_control_board_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_parts_control_board.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
