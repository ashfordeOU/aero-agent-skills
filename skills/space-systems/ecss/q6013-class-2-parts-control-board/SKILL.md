---
name: q6013-class-2-parts-control-board
description: "Use when board minutes have to become an approval verdict. Assess the board reviewing and approving commercial EEE part choices at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.1.3: refuse a board missing a required voting role, take each decision in turn, apply the session quorum or the written-procedure response floor according to how it was taken, refuse a response from a member the circulation never reached, refuse votes cast beyond the members who took part, compute the approval share against its floor, require a data package, a part in a named usage and a record raised before the procurement commitment, and inform the customer above a declared usage criticality. Trigger: ecss, q-st-60-13c-clause-5-1-3, class-two-parts-control-board, written-procedure-part-approval, parts-board-circulation-completeness, commercial-part-usage-criticality-notification, part-approval-data-package-record, bare-quorum-approval-advisory."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-parts-control-board, class-two-parts-control-board, written-procedure-part-approval, parts-board-circulation-completeness, commercial-part-usage-criticality-notification, part-approval-data-package-record, bare-quorum-approval-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Parts Control Board (space-systems/ecss/q6013-class-2-parts-control-board)

Use when the task is the clause 5.1.3 board question of
ECSS-Q-ST-60-13C at the intermediate assurance class: commercial EEE
parts are being put forward for a specific usage, and the body that
reviews and approves the choice has to be constituted and its decisions
recorded so that each one can be reconstructed.

## Domain quick reference

- The board is a constitution before it is a meeting. A required voting
  role that is absent does not make the board smaller; it makes every
  decision unattributable to the discipline that was missing, and that
  is a constitution finding rather than a decision finding.
- This class permits a decision to be taken by written procedure as well
  as in session, which is the substantive difference from the class
  above. A circulated decision carries its own floor, higher than the
  quorum a session needs, because nobody in a circulation hears the
  argument the others make.
- A circulation that missed a voting member is a defect even when enough
  people answered. The member who never received it did not decline to
  take part; they were not asked, and a response share taken over the
  people who happened to reply is a share of nothing.
- Participation is computed against the voting membership either way.
  Observers and invited specialists are useful and they do not make a
  quorum, so a share taken over everyone in the room or on the
  distribution list hides exactly the decisions that should be re-run.
- Votes cast cannot exceed the members who took part. That sounds
  obvious and it is the commonest defect in a reconstructed minute,
  because a concurrence collected later gets folded into the count of a
  session that did not hear it.
- The decision is about a part in a usage, not about a part. The same
  device approved for a benign bay is a different decision from that
  device in a hot, radiation-exposed one, so a decision with no usage
  reference has approved nothing anyone can check later.
- Customer concurrence is not the condition at this class; informing the
  customer above a declared usage criticality is. That threshold is
  where the residual risk the customer carries stops being theoretical,
  and a critical usage they were never told about is a record defect
  rather than a courtesy lapse.
- A decision carried on exactly the floor is approved and fragile.
  Reporting the participation and approval shares beside the verdict is
  what lets the next board see which approvals would not survive one
  absence.

## Workflow

1. Validate the board policy first: the session quorum, the written
   response floor, the approval floor, the two marginal bands and the
   usage criticality threshold. A written floor below the quorum, a zero
   floor, or a band wider than the floor it sits above is refused rather
   than used.
2. Validate the membership: non-blank identifiers, no duplicates, a
   recognised role on each member, boolean voting rights and no voting
   observer. An empty board, or one with no voting member, is refused.
3. Check the constitution: every required voting role carried by a
   voting member. A missing role closes the assessment on board not
   constituted, and every missing role is named, not only the first.
4. Validate every decision: a non-blank identifier, no duplicates, a
   part reference and a usage reference, a recognised mode, participants
   drawn only from the declared membership, a circulation that every
   responder was on, and vote counts whose sum is at least one and no
   more than the voting members who took part. A session record carrying
   a circulation, or a circulated record carrying a list of members
   present, is refused as ambiguous.
5. Compute the participation share over the voting membership and
   compare it against the floor its mode attracts, with a tolerance that
   absorbs representation error. A decision below its floor is reported
   and does not reach the approval arithmetic.
6. Compute the approval share over the votes cast and compare it against
   its floor, then read the record itself: a non-blank data package
   reference, the customer informed where the usage criticality reaches
   the threshold, a circulation that reached every voting member, and
   the record raised before the procurement commitment.
7. Report every decision with its shares and the full list of its
   defects rather than the first, name the weakest sound decision, and
   raise an advisory for a bare participation or a bare majority. Close
   on one verdict: board not constituted, decision not quorate, decision
   record incomplete, or board approvals sound.

## Pitfalls

- Counting heads instead of voting members. Observers and specialists
  are useful and they do not make a quorum, so a participation share
  taken over everyone present hides the decisions that should be re-run.
- Treating a written procedure as a session with a longer deadline. It
  carries a higher response floor precisely because nobody hears the
  argument, and a circulation answered by a bare majority of those who
  replied is not the same decision at all.
- Reading a circulation as complete because enough people answered. A
  voting member who never received it did not abstain, and their absence
  from the list is the defect, not their silence.
- Approving a part rather than a part in a usage. The usage reference is
  what the derating, the radiation case and the screening decision were
  argued against, and without it the approval cannot be checked against
  the board it will next be quoted to.
- Minuting the approval after the order is placed. The purchase then
  made the decision and the board recorded it, which is the shape this
  clause exists to prevent.

## Behavior contract (gate 3)

The policy validation, membership validation, the constitution check
against the required voting roles, decision validation including the
circulation and the votes against the members who took part, the
participation share against the floor its mode attracts, the approval
share against its floor, the data package, usage criticality
notification and timing checks, the weakest sound decision, the bare
participation and bare majority advisories and the board verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_2_parts_control_board.py against
scripts/q6013_class_2_parts_control_board_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_parts_control_board.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
