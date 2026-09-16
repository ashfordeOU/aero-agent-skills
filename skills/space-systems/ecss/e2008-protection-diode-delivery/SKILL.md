---
name: e2008-protection-diode-delivery
description: "Use when a protection diode shipment is offered and its release has to be decided. Evaluate whether a dispatch of ordered protection diodes may leave under ECSS-E-ST-20-08C clause 9.9, where the hardware and the document set travelling with it must close together: hold every diode from a lot short one released document, read each document for its release state rather than its presence, refuse a bypass-for-blocking swap outright because diode function is categorical, fill each line from its own reverse-voltage band before any upgrade the order permits, reconcile short and surplus lines, and apply the declared partial-delivery floor. Trigger: ecss, e-st-20-08c, clause-9-9, protection-diode-dispatch-release, protection-diode-lot-document-set, protection-diode-function-substitution-rule, protection-diode-rating-band-allocation, protection-diode-partial-delivery-floor."
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
  tags: [ecss, e-st-20-08-protection-diode-scope, e2008-protection-diode-delivery, e-st-20-08c-clause-9-9, protection-diode-dispatch-release, protection-diode-lot-document-set, protection-diode-function-substitution-rule, protection-diode-rating-band-allocation, protection-diode-partial-delivery-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Protection Diodes -- Delivery (space-systems/ecss/e2008-protection-diode-delivery)

Use when the task is clause 9.9 of ECSS-E-ST-20-08C: the ordered
protection diodes are ready to leave, and whether they may go has to be
settled against both the order they answer and the documentation the
preceding clauses ask to travel with them.

## Domain quick reference

- Two arms have to close, not one. A shipment is not releasable because
  the diodes are counted and present; every diode also has to come from a
  lot whose documentation is released. A diode whose lot is short a
  document is not a diode with late paperwork, it is a diode nobody
  downstream can trace back to a qualified process.
- The documentation arm is a SET, not a flag. A lot owes its data
  package, its screening test data and a declaration of conformance, and
  each carries its own release state. Two of the three released is not a
  released lot, and a check that reads one document and stops will pass a
  lot that never released the screening results.
- Release state is a state, not an entry. A document listed in the
  register as draft or withdrawn is a document that is not released, and
  reading the register for presence rather than for state is the quiet
  way this arm goes green.
- That is why a count is the weakest possible check. An ordered quantity
  can be met in full by diodes drawn entirely from a lot that never
  released a document, and a pure counting sweep passes it without a word.
- Protection diodes carry two different substitution questions, and they
  do not have the same answer. Function is categorical: a bypass diode
  and a blocking diode answer different faults in different places, so
  one never stands in for the other and no order permission unlocks it.
- Rating is a ladder. A line asking for a lower reverse-voltage band may
  be filled from a higher band when the order permits the upgrade -- the
  customer receives more standoff margin than was bought. It may never be
  filled from a lower band, which is a downgrade of the part dressed up
  as a substitution.
- Allocation order therefore matters as much as the rule. The exact band
  is spent first and only then is a permitted upgrade drawn on, or a high
  line goes short because its diodes were consumed by a low line that had
  its own stock available.
- A diode under an open nonconformance is not shippable because somebody
  wrote a concession; it is shippable when that concession is accepted,
  and those diodes are named in the dispatch rather than folded into the
  clean count. A concession never completes a document set.
- What is left over is not slack. A shippable diode that no order line
  asks for is surplus the shipment was never asked to carry, and it is
  reported rather than quietly loaded. A function mismatch shows up here
  twice: the line goes short and the stock it could not use goes surplus.
- A partial dispatch is a decision. The order declares the fraction of a
  line below which a partial delivery is refused outright; a line that
  clears that floor without being complete still goes, and is still named
  as partial. A line sitting exactly on its floor clears it -- the
  comparison absorbs representation error rather than moving the floor.

## Workflow

1. Validate the order: every line carries an identifier, a diode
   function, a reverse-voltage rating band, a positive ordered count and
   an explicit rating-upgrade permission, and the partial-delivery floor
   is a stated fraction between nought and one.
2. Grade each lot's document set, reading each required document for its
   release state and separating a document that is absent from one that
   is present but not released.
3. Disposition every offered diode: held when its lot's document set is
   short anything, held when the lot has no register entry at all, held
   when an open nonconformance carries no accepted concession, shippable
   on an accepted concession when it does, and shippable otherwise.
4. Fill each order line from the shippable diodes, matching the function
   exactly, taking the exact rating band first and only then the nearest
   permitted upgrade; never take a lower band and never cross functions.
5. Reconcile each line: shipped against ordered, the short count, the
   fill fraction, and which allocated diodes were upgrades.
6. Compare each fill fraction with the declared floor under a named
   tolerance, marking the line complete, partial within the floor, or
   refused below it.
7. Report the surplus shippable diodes no line asked for, the held diodes
   with their reasons, the concession diodes by name, the incomplete lots,
   and release only when the finding list is empty.

## Pitfalls

- Counting to the ordered quantity and stopping. The count says nothing
  about which lots the diodes came from, and the documentation arm is
  where a traceability break actually shows.
- Treating the documentation arm as one flag. The lot owes a set; reading
  the data package and calling the lot documented ships diodes whose
  screening data was never released.
- Reading the document register for presence. An entry whose state is
  draft or withdrawn is still an entry, and treating it as coverage puts
  untraceable diodes on the shipment.
- Letting an accepted concession stand in for documentation. A concession
  disposes of a nonconformance; it does not release a lot's documents,
  and a diode can fail both arms at once.
- Treating function like a grade. A bypass diode is not a weaker blocking
  diode, it is a different part doing a different job, so no upgrade
  permission and no engineering judgement makes the swap legitimate.
- Allowing a downgrade as a substitution. Filling a higher-band line from
  a lower band delivers a part with less standoff margin than the order
  bought, whatever the count says.
- Taking upgrades before exact stock. A permitted upgrade spent on a low
  line can starve the high line the diode was the only candidate for, so
  the same pool produces a short line purely through allocation order.
- Loading the surplus. A shippable diode no line wants is not a free
  extra; it leaves the shipment and the order disagreeing.
- Moving the floor to pass a line that sits exactly on it. An equality at
  the limit is a representation question, handled by the tolerance inside
  the comparison; the declared fraction stays as declared.
- Reporting a bare rejection. One refused line, one held diode or one
  surplus diode each block the dispatch for a different reason, and the
  report names which.

## Behavior contract (gate 3)

The categorical diode function set, the reverse-voltage rating ladder and
its rank order, the order and line validation with the explicit
rating-upgrade permission and the bounded partial-delivery floor, the
per-lot required-document set graded on release state with absent and
unreleased documents reported apart, the three-way diode disposition with
its concession states, the function-exact and exact-band-before-upgrade
allocation with downgrades and cross-function fills refused, the per-line
short and surplus reconciliation, the floor comparison under a named
tolerance and the aggregated dispatch verdict are exercised by the gate 3
contract test: scripts/test_e2008_protection_diode_delivery.py against
scripts/e2008_protection_diode_delivery_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_protection_diode_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
