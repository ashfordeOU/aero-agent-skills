---
name: q7003-process-records
description: "Audit the batch process record an anodizing run leaves behind. Use when parts have come off the line and the paperwork has to stand on its own as the only surviving evidence they ran inside the qualified window: check every traceability field is present and linked to the qualification it ran under, grade each recorded parameter against that window, treat a blank value as unknown rather than nominal, check the process steps are all there and in chronological order, measure the rinse-to-seal delay that decides whether an open coating was left to take up contamination, and derive the retention expiry from the record date. Trigger: ecss, q-st-70-03-anodizing, anodize-batch-process-record, anodize-parameter-traceability, anodize-rinse-to-seal-delay, anodize-record-retention-expiry."
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
  tags: [ecss, q-st-70-03-anodizing, q7003-process-records, anodize-batch-process-record, anodize-parameter-traceability, anodize-rinse-to-seal-delay, anodize-record-retention-expiry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Anodizing — Process Records (space-systems/ecss/q7003-process-records)

Use when the task is the records clause of ECSS-Q-ST-70-03: grading the
batch record an anodizing run leaves behind, which is the only thing
that still exists once the parts have shipped.

## Domain quick reference

- The record is the evidence, not a formality. After delivery nobody can
  re-measure the bath, so a claim that the batch ran inside the
  qualified window is worth exactly what the record says and nothing
  more.
- Traceability needs the link upward as well as the batch identity.
  Without the tank and the qualification it ran under, the record
  describes a batch that cannot be tied to the line that produced it or
  to the campaign that authorised that line.
- A blank parameter is unknown, not nominal. It is a different defect
  from an out-of-window value and is graded differently: an excursion
  says the batch left the window, a blank says nobody can tell. Folding
  the two together either condemns good batches or passes unknown ones.
- Sequence is graded by step order, not by the order lines were typed.
  A record is often entered out of sequence and still describes a
  correct run; what matters is that each step's timestamp does not
  precede the step before it.
- The rinse-to-seal delay is a real process limit. A freshly anodized
  coating is porous and open, so time spent waiting for the seal tank is
  time spent taking up whatever the rinse water and the air offer it,
  and a long wait shows up later as a corrosion result nobody can trace.
- Retention is derived, not assumed. The expiry comes from the record
  date and the declared period, and the leap-day case is handled rather
  than left to throw at the point of filing.
- Findings sort into two ranks. A gap in the record is a deficiency that
  can be closed by finding the missing entry. An excursion, an
  impossible chronology or an overrun seal delay is a statement about
  the batch that no amount of paperwork will close.

## Workflow

1. Check the traceability fields. Treat a blank string and an empty list
   as absent rather than present, because both are what a partly filled
   form actually produces.
2. Grade the recorded parameters against the window the line was
   qualified for. Report excursions and blanks as separate lists, and
   reject an inverted window rather than grading against it.
3. Check the process sequence: every step present, no step recorded
   twice, and each step's timestamp at or after the one before it in
   process order. Grade by step order so that a record entered
   backwards still reads correctly.
4. Where the sequence is complete and ordered, measure the rinse-to-seal
   delay in whole minutes and grade it against the declared maximum.
   Refuse to compute a delay across an out-of-order record, because the
   number would be meaningless.
5. Derive the retention expiry from the record date and the declared
   period, handling a leap-day record date rather than letting it fail.
6. Give the verdict in three ranks: rejected on an excursion, a broken
   chronology or an overrun seal delay; deficient on a missing field, a
   blank parameter or a missing step; complete only when nothing was
   raised.

## Pitfalls

- Reading a blank parameter as nominal. The operator who left it blank
  did not measure it, so filling it in downstream manufactures evidence
  that the batch ran in control.
- Grading the sequence by the order the lines appear. Records are
  routinely entered after the fact and out of order, so a check on list
  position condemns correct runs while missing the chronology error it
  was meant to catch.
- Recording a batch without the qualification it ran under. The record
  then survives the line it describes, and a later query about a batch
  cannot reach the campaign that authorised the process.
- Skipping the rinse-to-seal delay because both steps are present. Both
  being present is not both being timely, and the open coating is at its
  most absorbent in exactly that interval.
- Collapsing deficiencies and excursions into one verdict. A missing
  entry can still be found and filed; an out-of-window value cannot be
  unwound, and treating them alike loses the distinction that decides
  what happens to the parts.
- Comparing a parameter set on a window edge by bare arithmetic. A
  logged value carries the representation error of its conversion, so
  the comparison absorbs it while the window itself stays untouched.

## Behavior contract (gate 3)

The traceability field check, parameter grading, process sequence and
chronology check, rinse-to-seal delay, retention expiry and the
three-rank record verdict are exercised by the gate 3 contract test:
scripts/test_q7003_process_records.py against
scripts/q7003_process_records_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7003_process_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
