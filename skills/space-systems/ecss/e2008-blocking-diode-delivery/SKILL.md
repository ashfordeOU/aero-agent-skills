---
name: e2008-blocking-diode-delivery
description: "Evaluate whether a dispatch of ordered blocking diodes may leave, per ECSS-E-ST-20-08C clause 12.9: hold every diode from a batch whose data package is not released, hold a serial missing from its batch delivered list, hold a batch past its storage life with no revalidation, fill each ordered line from its own blocking voltage class before any permitted upgrade and never from a lower class or another part number, and apply the declared partial-delivery floor. Use when blocking diode hardware is offered for dispatch with its delivery documentation. Trigger: ecss, e-st-20-08c, clause-12-9, blocking-diode-dispatch-release, blocking-diode-batch-documentation-coverage, blocking-diode-serial-traceability, blocking-diode-voltage-class-upgrade, blocking-diode-storage-life-revalidation."
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
  tags: [ecss, e-st-20-08-blocking-diode-scope, e2008-blocking-diode-delivery, e-st-20-08c-clause-12-9, blocking-diode-dispatch-release, blocking-diode-batch-documentation-coverage, blocking-diode-serial-traceability, blocking-diode-voltage-class-upgrade, blocking-diode-storage-life-revalidation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Delivery (space-systems/ecss/e2008-blocking-diode-delivery)

Use when the task is clause 12.9 of ECSS-E-ST-20-08C: the ordered blocking
diodes are ready to leave, and whether they may go has to be settled
against the order they answer and against the documentation the preceding
clause asks for at delivery.

## Domain quick reference

- The count is the cheapest arm of the check and the only one a picking
  list can answer on its own. An ordered quantity can be met in full by
  diodes drawn entirely from a batch whose package was never released, and
  a pure counting sweep passes it without a word.
- Release state is a state, not an entry. A batch listed in the package
  register with the release still pending is a batch without a released
  package, and reading the register for presence rather than for state is
  the quiet way the documentation arm goes green.
- Blocking diodes ship serialized, so traceability is a second arm and not
  a restatement of the first. A serial that is not on the delivered-serial
  list of the batch it claims is not a labelling slip: the part and the
  batch record disagree about what was built, and neither can be trusted
  until that is settled. A batch can be fully released and still contain
  no record of the diode in the box.
- A released package does not stop the clock. A batch dispatched past its
  storage life is held unless a revalidation was performed after the life
  ran out and on or before the day the shipment left. A revalidation
  predating the expiry revalidated a batch that had not yet expired, and
  one dated after the shipment left was not available to release it.
- Diodes are ordered by part number and by blocking voltage class, which
  raises a substitution question a single-attribute article never has to
  answer. A line may be filled from a higher class when the order permits
  the upgrade -- the customer receives a part that blocks more than was
  bought. It may never be filled from a lower class, which is a downgrade
  of the article dressed up as a substitution, and never from another part
  number at all, which is not a substitution of any kind.
- Allocation order therefore matters as much as the rule. Exact class is
  spent first and only then is a permitted upgrade drawn on, or a
  high-class line goes short because its parts were consumed by a low line
  that had its own stock available.
- What is left over is not slack. A shippable diode that no order line
  asks for is surplus the shipment was never asked to carry, and it is
  reported rather than quietly loaded.
- A partial dispatch is a decision. The order declares the fraction of a
  line below which a partial delivery is refused outright; a line that
  clears that floor without being complete still goes, and is still named
  as partial. A line sitting exactly on its floor clears it -- the
  comparison absorbs representation error rather than moving the floor.

## Workflow

1. Validate the order: every line carries an identifier, a part number, a
   blocking voltage class, a positive ordered count and an explicit
   upgrade permission, and the partial-delivery floor is a stated fraction
   between nought and one.
2. Build the batch register, reading the release state rather than the
   presence of an entry, and parsing each batch's storage life expiry and
   any revalidation.
3. Disposition every offered diode against all three hold arms at once:
   an unreleased package, a serial absent from its batch's delivered list,
   and a batch past its storage life without a qualifying revalidation. A
   part can fail more than one, and each reason is named.
4. Fill each order line from the shippable diodes of the matching part
   number, taking the exact class first and only then the nearest
   permitted upgrade; never take a lower class or another part number.
5. Reconcile each line: shipped against ordered, the short count, the fill
   fraction, and which allocated serials were upgrades.
6. Compare each fill fraction with the declared floor under a named
   tolerance, marking the line complete, partial within the floor, or
   refused below it.
7. Report the surplus diodes no line asked for, the held diodes with their
   hold codes, and release only when the finding list is empty.

## Pitfalls

- Counting to the ordered quantity and stopping. The count says nothing
  about which batches the diodes came from, and the documentation arm is
  where a traceability break actually shows.
- Reading the batch package register for presence. An entry whose release
  is still pending is an entry, and treating it as coverage puts
  untraceable hardware on the pallet.
- Folding traceability into the documentation arm. A released batch record
  that does not list the serial in the box is a released record of a
  different set of parts, and only a serial-level check sees it.
- Letting a released package stand in for shelf life. Release says the
  paperwork is done; it says nothing about how long the part has sat, and
  the two arms fail independently.
- Accepting any revalidation that exists. One dated before the expiry
  revalidated nothing, and one dated after the shipment left was not
  available to release it.
- Allowing a downgrade as a substitution. Filling a higher-class line from
  a lower class delivers a part that blocks less than the order bought,
  whatever the count says.
- Treating another part number as near enough. It is not a substitution of
  any kind, and it leaves the line short and the surplus list long.
- Taking upgrades before exact stock. A permitted upgrade spent on a low
  line can starve the high line the part was the only candidate for, so
  the same pool produces a short line purely through allocation order.
- Loading the surplus. A shippable diode no line wants is not a free
  extra; it leaves the shipment and the order disagreeing.
- Moving the floor to pass a line that sits exactly on it. An equality at
  the limit is a representation question, handled by the tolerance inside
  the comparison; the declared fraction stays as declared.
- Reporting a bare rejection. One refused line, one held diode and one
  surplus part each block the dispatch for a different reason, and the
  report names which.

## Behavior contract (gate 3)

The blocking voltage class ladder and its rank order, the order and line
validation with the explicit upgrade permission and the bounded
partial-delivery floor, the release-state reading of the batch register
with its serial lists and storage-life dates, the revalidation window
rule, the three-arm diode disposition with hold codes reported together,
the part-number match with exact class spent before a permitted upgrade
and downgrades refused, the per-line short and surplus reconciliation, the
floor comparison under a named tolerance and the aggregated dispatch
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_delivery.py against
scripts/e2008_blocking_diode_delivery_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_blocking_diode_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
