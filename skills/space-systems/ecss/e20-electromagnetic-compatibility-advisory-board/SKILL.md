---
name: e20-electromagnetic-compatibility-advisory-board
description: "Use when structure and run the electromagnetic compatibility advisory board that ECSS-E-ST-20C clause 6.2.3 places over a project's electromagnetic compatibility decisions: categorize each nominated member as a core, contributing or observer seat, check the mandatory chairperson, system-engineering, customer, product-assurance and grounding-authority roles are filled, confirm every emitting or susceptible subsystem holds a representative, compute the voting membership and the quorum a sitting requires, and dispose each agenda item as endorsed, rejected, deferred or escalated for customer approval. Trigger: ecss, e-st-20-electrical-scope, electromagnetic-compatibility-advisory-board, emc-board-composition, emc-board-quorum, emc-board-remit, grounding-authority-representation, emc-decision-escalation."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electromagnetic-compatibility-advisory-board, electromagnetic-compatibility-advisory-board, emc-board-composition, emc-board-quorum, emc-board-remit, emc-decision-escalation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Electromagnetic Compatibility Advisory Board (space-systems/ecss/e20-electromagnetic-compatibility-advisory-board)

Use when the task is the clause 6.2.3 advisory body of ECSS-E-ST-20C --
constituting the board that oversees the electromagnetic compatibility
decisions taken across the electrical architecture, writing down its
role and composition rather than leaving them to custom, and running a
sitting so that each decision has a traceable disposition.

## Domain quick reference

- The board is a standing advisory body, not a design authority and
  not the project configuration control board. It forms a single
  technical opinion on electromagnetic compatibility and hands that
  opinion to the authority that owns the change. The consequence is
  procedural: the board can endorse inside its own remit, but an item
  that moves the agreed baseline leaves the room as a recommendation
  awaiting customer approval, never as a closed action.
- Every nominated seat falls into exactly one of three categories.
  Core seats are the ones the board cannot sit without: the chair, the
  system-engineering representative, the customer representative, the
  product-assurance representative and the grounding and bonding
  authority. Contributing seats are the technical voices that speak
  for a scope: a subsystem electromagnetic representative, the payload
  representative, the harness designer, the launch authority.
  Observers attend and do not vote. An unfilled core seat is a finding
  against the board itself, independent of head count.
- Representation is checked against the project's list of
  electromagnetically relevant subsystems, meaning every subsystem
  that emits into or is susceptible to the shared electrical
  environment. A subsystem on that list with nobody speaking for it
  means the board's opinion was formed without one of the parties it
  binds, which is a composition defect and not a scheduling detail.
- A sitting is quorate on two conditions at once: the number of voting
  members in the room reaches the stated fraction of the voting
  membership, rounded up and never below one, and the chair is
  present. Un-appointed nominees and observers are outside the head
  count on both sides of that comparison, so a well-attended room of
  observers is still inquorate.
- An agenda topic is admitted only if it belongs to the board. A
  requirement tailoring, a grounding or bonding architecture change, a
  margin deviation, a nonconformance disposition and a verification
  endorsement all belong; a propellant or thermal budget does not, and
  is rejected before it can absorb a vote. The decision class that
  comes back from that admission step is what selects endorsement
  against escalation.
- Majorities are counted on votes cast, in whole numbers, with
  abstentions excluded from both the numerator and the denominator. A
  tie does not carry. An item with no vote cast at all is deferred
  rather than rejected, because silence is not a decision.

## Workflow

1. Normalize the membership: reject a record with no member
   identifier, no role, a non-boolean appointment flag or a malformed
   subsystem list, and reject a repeated member identifier before any
   count is taken.
2. Categorize every seat as core, contributing or observer, and list
   the core roles no appointed member fills. Flag a second appointed
   chair and any nominee left un-appointed.
3. Take the voting membership: appointed core and contributing seats
   only.
4. Check representation: for each electromagnetically relevant
   subsystem, confirm at least one appointed member speaks for it.
5. Compute the quorum requirement from the stated fraction of the
   voting membership, then take the sitting's quorum state from the
   voting members present and the chair's presence. An attendee who is
   not on the board is an input error, not a guest.
6. Admit each agenda item by decision class, rejecting an out-of-remit
   or unrecognized topic. Dispose the item: deferred if the sitting is
   inquorate or no vote was cast, escalated for customer approval if a
   carried item moves the baseline, endorsed if a carried item stays
   inside the board's authority, otherwise rejected.
7. Aggregate. The board is constituted when composition and
   representation findings are both empty; the sitting is compliant
   only when the board is constituted, the sitting was quorate and
   nothing was left deferred.

## Pitfalls

- Counting heads instead of seats and declaring a crowded room
  quorate. Observers and un-appointed nominees do not vote, so the
  quorum has to be taken against the voting membership, not against
  attendance.
- Treating the chair as one voter among many. The board issues one
  opinion; without the chair there is nobody to issue it, so an
  otherwise well-attended sitting is still inquorate.
- Letting the board close an item that tailors a requirement or
  accepts a margin deviation. Those move the agreed baseline and the
  board only recommends; recording them as closed loses the customer
  approval the project still owes.
- Computing the quorum as a fraction times a head count and taking a
  bare ceiling of the result. A product such as fifty-six percent of
  twenty-five seats lands a few units in the last place above
  fourteen, and a bare ceiling then demands a fifteenth seat the
  requirement never asked for. Absorb the representation error at the
  rounding step; never move the stated fraction.
- Reading an item with no votes cast as rejected. An all-abstention
  item is unresolved and stays on the agenda, and folding it into the
  rejected pile hides an open decision.
- Accepting an out-of-remit topic because it was raised by a senior
  attendee. A topic outside the electromagnetic scope has no
  disposition this board can give it, and voting on it produces a
  record no authority can act on.
- Counting abstentions in the denominator of the majority. Doing so
  turns a clear technical consensus into a failed vote and pushes
  sound recommendations back onto the agenda.

## Behavior contract (gate 3)

The seat categorization, membership validation, core-role, voting
membership, quorum, subsystem-representation, agenda-admission,
disposition and aggregate-review logic is exercised by the gate 3
contract test:
scripts/test_e20_electromagnetic_compatibility_advisory_board.py
against
scripts/e20_electromagnetic_compatibility_advisory_board_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e20_electromagnetic_compatibility_advisory_board.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
