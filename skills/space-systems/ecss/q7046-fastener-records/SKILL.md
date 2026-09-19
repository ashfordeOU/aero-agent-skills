---
name: q7046-fastener-records
description: "Audit the paper trail a procured threaded fastener lot owes before acceptance may be signed. Use when certificates and test results have arrived with a delivery and someone must decide whether the file actually closes: take the record set from the criticality so a critical lot owes its heat-treatment and embrittlement relief results rather than a conformity certificate alone, name the gaps in the order the set requires them, then walk the delivered lot upwards through coating, manufacturing, bar and heat and report whether it reaches exactly one heat, stops at a parent nobody filed, returns to itself, or resolves to two heats mixed into one delivery. Trigger: ecss, q-st-70-46-fasteners, fastener-certificate-of-conformity, fastener-lot-traceability-chain, fastener-heat-number-resolution, fastener-record-retention-period."
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
  tags: [ecss, q-st-70-46-fasteners, q7046-fastener-records, fastener-certificate-of-conformity, fastener-lot-traceability-chain, fastener-heat-number-resolution, fastener-record-retention-period]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Records and Traceability (space-systems/ecss/q7046-fastener-records)

Use when the task is the records clause of ECSS-Q-ST-70-46: deciding
whether the certificates and test results delivered with a fastener lot
are the ones that lot owes, and whether the lot identity on the label
actually resolves back to a single heat.

## Domain quick reference

- The required record set comes from the criticality. A minor lot owes
  conformity, dimensions and a lot identity; a major one adds the
  material certificate and the mechanical results behind them; a
  critical one adds the heat-treatment record, the embrittlement relief
  test and the coating process record.
- The records a critical lot adds are exactly the properties nobody can
  re-measure on a finished part. That is why they are required in
  writing rather than re-verified on receipt.
- Traceability is a walk, not a field. The delivered lot is declared out
  of a coating lot, out of a manufacturing lot, out of a bar lot, out of
  a heat, and the question is what that declaration reaches when it is
  followed.
- A walk that stops at a parent nobody filed is a broken chain. The
  identifier printed on the paperwork is not evidence that the record
  behind it exists.
- A walk that returns to a node it has already passed is a corrupted
  record, not a deep one. It usually means two lots were renumbered into
  each other during a system migration.
- A walk that reaches two heats means two heats were mixed into one
  delivery. The mechanical results of neither heat cover the parts of
  the other, so the delivery has no test evidence at all despite having
  two sets of it.
- A missing record and a failed record are different findings. Only one
  of them can be closed by asking the supplier to send the file again.
- Retention runs from delivery, not from manufacture. Delivery is the
  date the receiving organisation can evidence, and a lot can sit in a
  supplier's store for years before it is one.

## Workflow

1. Take the criticality and build the required record set from it
   rather than from the delivery note's list of enclosures.
2. Compare the file against that set and report the gaps in the order
   the set requires them, so the chase list reads in the order the
   supplier will work through it.
3. Take the traceability declaration and normalise it: every node has an
   identifier and a kind, a heat is declared out of nothing, and no
   identifier appears twice.
4. Walk upwards from the delivered lot. Record every parent that is not
   in the file, every node the walk re-enters, and every heat reached.
5. Read the walk: one heat resolves; a missing parent or a node with no
   parent that is not a heat breaks; a re-entry is corrupted; more than
   one heat is a mixed delivery.
6. Sign acceptance only when the record set is complete and the walk
   resolves to exactly one heat. Report the retention deadline from the
   delivery date alongside the verdict.

## Pitfalls

- Accepting a conformity certificate as the whole file. It certifies
  that the supplier believes the lot conforms; the test results are what
  make that belief checkable.
- Treating a heat number printed on the certificate as traceability. The
  number is a claim; traceability is whether the records behind the
  number resolve when they are followed.
- Reading a deep chain as a good chain. A chain that loops through a
  renumbered node can be walked a long way and still reach no heat at
  all.
- Letting a delivery carry two heats because both have certificates.
  Two sets of mechanical results are not coverage of the mixed lot;
  each set covers only the parts from its own heat and nobody can tell
  them apart afterwards.
- Counting retention from the manufacture date on the part marking. The
  lot may have sat in the supplier's store for years, and the shorter
  retention it produces is the one that runs out first.
- Closing a gap by re-asking for the certificate that already failed. A
  missing record and a failing record look identical on a checklist and
  are answered by completely different actions.

## Behavior contract (gate 3)

The required record set by criticality, the ordered gap list, the
retention deadline with its leap-day clamp, the chain normalisation
rules, the upward walk with its broken, circular, mixed and resolved
outcomes and the acceptance verdict are exercised by the gate 3
contract test:
scripts/test_q7046_fastener_records.py against
scripts/q7046_fastener_records_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7046_fastener_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
