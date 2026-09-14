---
name: q6013-class-3-traceability
description: "Determine how deeply a lowest assurance class commercial EEE delivery can still be followed into the assembly it was fitted to, under ECSS-Q-ST-60-13C clause 6.5.4: resolve each installation back through kitting and re-batching records to its goods-in entry, cap the depth a pooled batch may claim, take the achieved depth as the weakest link on that chain, name every chain that never reaches goods-in, catch a record dated after the installation it supplied, and compare record coverage with the floor in exact integer arithmetic. Use when a light traceability folder has to become a depth verdict. Trigger: ecss, q-st-60-13c-clause-6-5-4, class-three-commercial-part-traceability, installation-to-goods-in-chain, pooled-batch-depth-cap, weakest-link-trace-depth, unresolved-trace-chain, record-installation-date-order."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-traceability, class-three-commercial-part-traceability, installation-to-goods-in-chain, pooled-batch-depth-cap, weakest-link-trace-depth, unresolved-trace-chain, record-installation-date-order]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Traceability (space-systems/ecss/q6013-class-3-traceability)

Use when the task is the clause 6.5.4 traceability duty of
ECSS-Q-ST-60-13C at the lowest assurance class: commercial parts bought
against a catalogue reference have been booked in, kitted, pooled and
fitted, and the question is not whether a folder exists but how far back
each fitted part can actually be followed and whether that reach is the
one the programme declared.

## Domain quick reference

- Traceability at this class is a depth, not a yes or no. A record can
  carry a unit serial, a manufacturing lot code, a delivery batch
  reference, or nothing beyond the ordered part number, and those four
  are ranked. The verdict is which rank each fitted part reaches, not
  whether paper was produced.
- The reach of a fitted part is the weakest link on its chain. A part
  kitted from a batch that carried a lot code, out of a goods-in entry
  that recorded only the order line, is traceable to the order line.
  Taking the best record on the chain instead of the worst reports a
  reach the programme does not have.
- Pooling is the commercial reality this class admits and the price it
  charges. Where several deliveries are drawn into one working batch,
  the individual manufacturing identity is gone, so a pooled record
  cannot claim a depth above the batch it became however specific its
  own label looks.
- A chain that runs out before it reaches a goods-in entry has not
  reached the supply boundary. It is not a shallow chain to be scored
  low; it is an unresolved chain, and the reference it dies on is the
  useful output.
- Dates order the chain and also test it. A record dated after the
  installation it is said to have supplied describes a different event,
  and that contradiction survives any depth the record claims.
- Coverage is a count of fitted parts reaching the declared depth,
  compared with the floor by cross-multiplying integers. A fraction held
  in floating point puts a population sitting exactly on the floor on
  either side of it depending on the machine.

## Workflow

1. Validate the records: a non-empty reference, a ranked depth token, an
   integer day, an optional parent reference, and no reference used
   twice. Validate each installation: a part identifier, an assembly, a
   record reference and an integer day.
2. Resolve each installation back along parent references. Stop on a
   record with no parent, refuse a chain that loops, and mark a chain
   that names a reference no record supplies as unresolved.
3. Reduce each record on the chain to its effective depth, applying the
   pooled-batch cap before anything is compared.
4. Take the achieved depth of the installation as the minimum effective
   depth on the resolved chain, and record which link set it.
5. Compare every record date on the chain with the installation day and
   raise a finding for any record dated later.
6. Flag a chain longer than the declared hop limit and a chain that
   never reaches a goods-in root.
7. Count the installations reaching the declared depth, compare that
   count with the coverage floor by integer cross-multiplication, and
   return one verdict in precedence order: unresolved chain, date order
   contradicted, coverage below the floor, coverage met with named
   shortfalls, otherwise traceable to the declared depth.

## Pitfalls

- Scoring a chain by its best record. The lot code on a kitting slip
  says nothing once the goods-in entry behind it recorded only a
  catalogue reference; the part is traceable to the catalogue reference.
- Letting a pooled batch keep the depth printed on its own label. A
  pooled batch is the merge point where several deliveries stopped being
  distinguishable, so its label is a name, not a reach.
- Treating an unresolved chain as a low score. A low score is a measured
  reach; an unresolved chain is a measurement that never terminated, and
  averaging it into a coverage figure hides the gap.
- Accepting a record dated after the installation because the depth
  looks right. The date contradiction says the record belongs to another
  event, and a depth taken from the wrong event is not a depth.
- Holding the coverage ratio as a float. A population sitting exactly on
  the declared floor is the case reviewers compare between two sites,
  and it is the case a float decides differently on each of them.
- Reporting a single depth for the delivery. Fitted parts out of one
  delivery take different routes through kitting, so the reach is a
  distribution over installations and the shortfalls are what get fixed.

## Behavior contract (gate 3)

The record and installation validation, chain resolution with loop
refusal, pooled-batch depth capping, weakest-link depth, date-order
checking, integer coverage comparison and verdict precedence are
exercised by the gate 3 contract test:
scripts/test_q6013_class_3_traceability.py against
scripts/q6013_class_3_traceability_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_traceability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
