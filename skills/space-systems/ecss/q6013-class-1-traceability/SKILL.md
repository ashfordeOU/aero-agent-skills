---
name: q6013-class-1-traceability
description: "Use when a class 1 lot must be followed from goods-in through stores into an assembly, or a board serial traced back to its lot. Verify that the lot identity of a highest-assurance (class 1) commercial EEE procurement survives its whole custody chain under ECSS-Q-ST-60-13C clause 4.5.4: order the receipt, inspection, storage, kitting, installation and scrap events on one clock, find the events that drop the lot code or contradict the received date code, reconcile installed, scrapped and returned quantities against the quantity received, build the board-serial trace in both directions, and score identity completeness against the required level. Trigger: ecss, q-st-60-13c, commercial-eee-lot-traceability, class-1-commercial-part, receipt-to-assembly-chain, lot-quantity-reconciliation, board-serial-forward-trace, date-code-continuity."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-traceability, class-1-commercial-eee-part, commercial-eee-lot-traceability, receipt-to-assembly-chain, lot-quantity-reconciliation, board-serial-forward-trace]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Lot Traceability (space-systems/ecss/q6013-class-1-traceability)

Use when the task is the traceability step of ECSS-Q-ST-60-13C clause
4.5.4 for a commercial EEE part procured to the highest assurance class —
showing that one received lot keeps a single, unbroken identity from
goods-in, through storage and kitting, onto the board serials it was
built into.

## Domain quick reference

- The lot identity is the only thing that makes the rest of the class
  work. A nonconformance can only be contained across a lot, and an
  alert can only be screened against a date code, if every part in the
  build can still be attributed to the lot it arrived in. Traceability
  is therefore the load-bearing record, not the paperwork around it.
- A chain describes one lot and has exactly one receipt. Two receipts
  mean two lots that have been merged in the record, and an event timed
  before the receipt means the clock or the identity is wrong; either
  way the chain no longer answers the question it exists to answer.
- Identity travels on three fields: the lot code, the date code and the
  certificate reference from goods-in. An event that carries none of
  them is where the trail stops, and a downstream event carrying a
  different date code from the receipt is evidence that a second lot has
  entered the record.
- Re-marking and re-lotting are legitimate, but only against a
  cross-reference back to the original lot. A changed lot code with no
  cross-reference is indistinguishable from a mix-up, and is treated as
  one.
- Quantities have to close. The received quantity equals what was
  installed, plus what was scrapped, plus what went back to the
  supplier, plus what is still in stores. Movements in and out of stores
  shuffle parts around; they do not consume them, so they never enter
  that balance. Issuing more parts than were received is proof that a
  second lot is being drawn from under one identity.
- The trace runs both ways and both directions are used. Forward, from a
  lot to the board serials it reached, is what an alert or a
  nonconformance needs. Backward, from a board serial to its lot, is
  what a failure investigation needs, and a serial the chain never
  installed onto has to be refused rather than answered vaguely.

## Workflow

1. Validate every event: a known type, a non-empty event identity, a
   positive quantity and a finite non-negative clock reading. An
   installation must name the board serial it went onto; nothing else
   may carry one.
2. Validate the chain: reject a duplicated event identity, require
   exactly one receipt and refuse a chain whose earliest event is
   something other than that receipt. Order the rest by the clock,
   breaking ties on the event identity so the ordering is reproducible.
3. Walk the ordered chain for identity breaks: an event with no lot
   code, an event whose lot code differs from the lot under
   investigation with no cross-reference, and an event whose date code
   contradicts the one received.
4. Reconcile quantities from the receipt: sum installations, scraps and
   returns, subtract from the received quantity and report the remainder
   that should still be in stores. A negative remainder is an over-issue
   and is reported as a quantity, not as a boolean.
5. Build the forward trace by summing installed quantities per board
   serial, so a board built from the same lot twice shows one total.
6. Answer a backward trace by resolving the serial in that map and
   returning the lot identity, date code and certificate from the
   receipt; refuse a serial that is not in the map.
7. Score identity completeness as the fraction of events carrying all
   three identity fields, compare it with the required level under a
   named tolerance, and report the chain traceable only when there are
   no breaks, the quantities close and the score is met.

## Pitfalls

- Counting stores movements as consumption. A stores-out followed by a
  kitting event moves the same parts twice; adding them to the balance
  invents a shortage that sends people looking for parts that are on the
  shelf.
- Accepting a changed lot code because the part number still matches.
  The part number is not an identity; without a cross-reference the
  re-marked event is a mix-up until proven otherwise.
- Treating an absent date code as agreement with the receipt. A blank
  field is unknown, and it is exactly the field an alert screen will
  need later, so it is scored as incomplete rather than assumed good.
- Ordering the chain by the row order of the extract. Records arrive in
  whatever order the system exported them; the clock is the order, and
  a tie needs a deterministic second key or two runs disagree.
- Answering a backward trace for a board serial the lot never touched.
  Returning the lot anyway attributes a failure to the wrong
  procurement and sends the containment at the wrong population.
- Failing an exactly complete chain on its own threshold. The score is a
  ratio of counts turned into a float; the comparison absorbs that with
  a tolerance rather than by lowering the required level.

## Behavior contract (gate 3)

The event validation, chain ordering and single-receipt rule, identity
break detection, quantity reconciliation, forward and backward tracing
and completeness scoring are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_traceability.py against
scripts/q6013_class_1_traceability_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6013_class_1_traceability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
