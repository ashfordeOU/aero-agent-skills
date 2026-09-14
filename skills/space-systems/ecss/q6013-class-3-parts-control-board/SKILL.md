---
name: q6013-class-3-parts-control-board
description: "Determine which approval route a commercial EEE part usage was entitled to at the lowest assurance class under ECSS-Q-ST-60-13C clause 6.1.3: test the usage against every board referral condition -- outside the approved catalogue, at or above the criticality floor, a single point of failure, needing a derating waiver, carrying an open alert, an untraceable lot, or past the delegation quantity threshold -- then weigh the route taken, the board quorum, the evidence behind the decision, the record raised before the commitment, and the cadence a delegated approval owes the board. Use when a part approval record has to become a route verdict. Trigger: ecss, q-st-60-13c-clause-6-1-3, class-three-parts-control-board, board-referral-condition-set, delegated-part-approval-authority, parts-board-quorum-share, delegated-approval-notification-cadence, bare-quorum-session-advisory."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-parts-control-board, class-three-parts-control-board, board-referral-condition-set, delegated-part-approval-authority, parts-board-quorum-share, delegated-approval-notification-cadence, bare-quorum-session-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Parts Control Board (space-systems/ecss/q6013-class-3-parts-control-board)

Use when the task is the clause 6.1.3 governance question of
ECSS-Q-ST-60-13C at the lowest assurance class: a commercial part usage
has been approved, and the question is whether the parts control board
owed that decision or whether the delegated authority was entitled to
take it.

## Domain quick reference

- At the higher classes every commercial part usage reaches the board.
  At the lowest class it does not, and that is the clause working as
  intended. The board governs the usages carrying the risk; the project
  parts engineer, working inside the approved catalogue, takes the rest,
  which is what keeps a board small enough to actually meet.
- The question is therefore not how the board voted. It is which route
  the usage was entitled to and whether the route taken was that one.
- Seven conditions oblige a board decision: the part sits outside the
  approved catalogue, its function is at or above the declared
  criticality floor, it is a single point of failure, it needs a
  derating or uprating waiver, it carries an open alert, its lot cannot
  be traced, or the installed quantity is past the delegation threshold.
  Any one is enough. They are not weighed against each other and a clean
  record on six does not cancel the seventh.
- A referral earned and not taken is what this clause exists to catch.
  The delegated route is not wrong, it is bounded, and a usage approved
  by the delegate when the board owed the decision leaves no record that
  anyone competent looked at the risk.
- The delegated route carries its own obligation. A part approved
  outside the board is reported to the board inside a declared cadence,
  so the board still sees the shape of what is being built where it did
  not decide. A report that never arrives turns delegation into a gap.
- Both routes need evidence behind the decision and a record raised
  before the procurement commitment. An approval written after the order
  is a description of a purchase, not a decision about a part.
- Quorum is a property of the session, not of the board. It is the
  attending share of the eligible members measured against a declared
  floor, and a session exactly on the floor is quorate, the comparison
  tolerance being there to absorb representation error rather than to
  lower the floor.
- The margin is worth as much as the verdict. A board sitting on a bare
  quorum and a usage installing one part below the delegation threshold
  both pass today and both change route on the next build standard.

## Workflow

1. Validate the route policy first: the quorum floor, the marginal band
   inside which a quorate session is still advised on, the criticality
   floor for referral, the delegation quantity threshold and its
   advisory margin, the notification cadence, and the evidence flag. A
   quorum floor of zero, a band wider than the floor, an unrecognised
   criticality, or a margin wider than the threshold is refused rather
   than used.
2. Validate the usage: a non-blank part reference, a recognised function
   criticality, boolean catalogue, single-point-failure, waiver, alert
   and traceability declarations, and a whole installed quantity. An
   absent usage closes the assessment on usage not declared.
3. Test the usage against all seven referral conditions and keep every
   one that fires, not the first. The list is the reason the verdict
   reads the way it does and it goes into the report.
4. Validate the approval record: a recognised route, an attendance that
   does not exceed the membership on the board route, an evidence
   reference that may be blank but is then read as none, a commitment
   flag and a notification delay. No record at all closes on approval
   not recorded.
5. Compare the obligation with the route taken. Any trigger firing
   against a delegated approval closes on board referral missed, and
   every firing condition is named.
6. On the board route take the attending share of the eligible members
   and compare it with the quorum floor under a tolerance that absorbs
   representation error.
7. Check the evidence reference, then the record before the commitment,
   then -- on the delegated route only -- the report to the board inside
   the cadence.
8. Report the part reference, the firing conditions, the route, the
   quorum share where one exists, and an advisory for a bare quorum or a
   quantity sitting just under the delegation threshold. Close on one
   verdict: usage not declared, approval not recorded, board referral
   missed, board quorum not met, approval evidence missing, approval
   recorded after commitment, delegated approval not notified, or
   approval route sound.

## Pitfalls

- Treating the delegated route as a lapse. At this class it is the
  designed route for a catalogue part in a non-critical function, and
  sending everything to the board is how a board stops meeting.
- Weighing the referral conditions against each other. They are grouped
  as a set of independent obligations; one firing condition sends the
  usage to the board whatever the other six say.
- Reading a quantity exactly on the delegation threshold as past it. The
  threshold is the last delegable quantity, not the first referred one,
  and the advisory rather than the verdict is what flags the margin.
- Checking the quorum on a delegated approval. There is no session to be
  quorate, and a quorum computed from an empty membership is a division
  nobody asked for.
- Forgetting the notification the delegated route owes the board. A part
  approved outside the board and never reported to it is invisible to
  the body answerable for the build.
- Accepting an approval recorded after the commitment because the
  reasoning is sound. The reasoning was not available when the order was
  placed, and the parts are in the build either way.

## Behavior contract (gate 3)

The policy validation, usage validation, the seven referral conditions,
the decision-record validation, the quorum share and its floor, the
evidence and commitment checks, the delegated notification cadence, the
bare-quorum and near-threshold advisories and the route verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_3_parts_control_board.py against
scripts/q6013_class_3_parts_control_board_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_parts_control_board.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
