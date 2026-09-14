---
name: q6013-class-1-parts-control-board
description: "Evaluate the board that approves commercial EEE part selection and usage at the highest assurance class under ECSS-Q-ST-60-13C clause 4.1.3: refuse a board missing a required voting role, take each part decision in turn, compute the attendance share against the declared quorum and the approval share against its floor, refuse a vote cast by members who were not present, require a submitted data package, customer concurrence and a record raised before the procurement commitment, name every incomplete decision rather than the first, and flag an approval carried on a bare quorum. Use when board minutes have to become an approval verdict. Trigger: ecss, q-st-60-13c-clause-4-1-3, class-one-parts-control-board, parts-control-board-quorum-share, commercial-part-usage-approval-vote, parts-board-customer-concurrence, part-approval-data-package-record, bare-quorum-approval-advisory."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-1-parts-control-board, class-one-parts-control-board, parts-control-board-quorum-share, commercial-part-usage-approval-vote, parts-board-customer-concurrence, part-approval-data-package-record, bare-quorum-approval-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 1 Parts Control Board (space-systems/ecss/q6013-class-1-parts-control-board)

Use when the task is the clause 4.1.3 board question of
ECSS-Q-ST-60-13C at the highest assurance class: commercial EEE parts
are being put forward for selection and for a specific usage, and the
body that may approve them has to be constituted and its decisions have
to be recorded so that each one can be reconstructed.

## Domain quick reference

- The board is a constitution before it is a meeting. A required voting
  role that is absent does not make the board smaller; it makes every
  decision it takes unattributable to the discipline that was missing,
  and that is a constitution finding rather than a decision finding.
- Attendance and quorum are computed against the voting membership, not
  against whoever appeared. A meeting with eleven people in the room and
  two voting members present has not reached a quorum, and a decision
  taken there approves nothing.
- Votes cast cannot exceed the members present. That sounds obvious and
  it is the commonest defect in a reconstructed minute, because a
  written-procedure concurrence collected afterwards gets folded into
  the count of the meeting that did not hear it.
- Approval is decided on a share of the votes cast against a declared
  floor, and a decision landing exactly on the floor is approved, the
  comparison tolerance being there to absorb representation error rather
  than to widen the floor.
- The decision is about a part in a usage, not about a part. The same
  device approved for a benign bay is a different decision from the same
  device in a hot, radiation-exposed one, so a decision without a usage
  reference has approved nothing that can be checked later.
- A decision with no submitted data package behind it is a preference. At
  this class the package is what the board weighed, and a record that
  does not name it cannot be reconstructed by anyone who was not there.
- Customer concurrence belongs to the record at this class, because the
  customer carries the residual risk of a commercial part; and the
  record has to be raised before the procurement commitment, since an
  approval minuted after the order describes a decision that had already
  been taken by the purchase.
- A decision approved on exactly the quorum and exactly the floor is
  approved and fragile. Reporting the two shares beside the verdict is
  what lets the next board see which approvals would not survive one
  absence.

## Workflow

1. Validate the board policy first: the quorum share, the approval share
   floor, the marginal band inside which an approval is advised on, and
   whether customer concurrence is required. A share above one, or a
   marginal band above its floor, is refused rather than used.
2. Validate the board membership: non-blank member identifiers, no
   duplicates, a recognised role on each member, and boolean voting
   rights. An empty board, or one with no voting member, is refused.
3. Check the constitution: every required voting role present at least
   once. A missing role closes the assessment on board not constituted,
   and every missing role is named, not only the first.
4. Validate every decision record: a non-blank decision identifier, no
   duplicates, a part reference and a usage reference, a present-member
   list drawn only from the declared membership, and non-negative vote
   counts whose sum does not exceed the voting members present.
5. Compute the attendance share as present voting members over voting
   members, and compare it against the quorum with a tolerance that
   absorbs representation error. A decision below quorum is reported and
   does not reach the approval arithmetic.
6. Compute the approval share as votes in favour over votes cast, and
   compare it against the floor. Then check the record itself: a
   non-blank data package reference, customer concurrence when the
   policy requires it, and the record raised before the procurement
   commitment.
7. Report the quorate share and approval share of every decision, the
   record completeness across the board, the weakest approved decision,
   and an advisory for every approval inside the marginal band. Close on
   one verdict: board not constituted, decision not quorate, decision
   record incomplete, or board approvals sound.

## Pitfalls

- Counting heads instead of voting members. Observers and specialists
  are useful and they do not make a quorum, so an attendance share taken
  over everyone in the room hides exactly the meetings that should be
  re-run.
- Folding a later written concurrence into the vote of the meeting. The
  meeting either reached its quorum or it did not; a concurrence
  collected afterwards is a separate record and inflating the count
  makes an inquorate decision look sound.
- Approving a part rather than a part in a usage. The usage reference is
  what the derating, the radiation case and the screening decision were
  argued against, and without it the approval cannot be checked against
  the board it will next be quoted to.
- Minuting the approval after the order is placed. The purchase then
  made the decision and the board recorded it, which is the shape this
  clause exists to prevent.
- Reporting a bare approval. The quorum share and the approval share are
  what show which approvals survive one absence, and the verdict word
  carries neither.

## Behavior contract (gate 3)

The policy validation, membership validation, the constitution check
against the required voting roles, decision validation including votes
against members present, the attendance share against the quorum, the
approval share against its floor, the data package, concurrence and
timing checks, the record completeness, the weakest approved decision,
the bare-quorum advisories and the board verdict are exercised by the
gate 3 contract test:
scripts/test_q6013_class_1_parts_control_board.py against
scripts/q6013_class_1_parts_control_board_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_parts_control_board.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
