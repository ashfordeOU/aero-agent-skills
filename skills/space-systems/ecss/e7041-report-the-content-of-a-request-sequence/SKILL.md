---
name: e7041-report-the-content-of-a-request-sequence
description: "Generate the content report of an on-board request sequence under ECSS-E-ST-70-41C clause 6.21.8: check the requested identifier against the request sequence store, order the entries by release offset, and pack them into the fewest content reports the telemetry data field can carry. Use when a request sequence content report, a report split across several packets, or the refusal of a report against an unknown or still-loading sequence is being specified or reviewed for a service 21 subservice. Refuses an unknown sequence identifier and an entry no single report could carry. Trigger: ecss, e-st-70-41c, pus-service-21, request-sequence-content-report, request-sequence-store, sequence-entry-release-offset, sequence-report-packing, under-construction-request-sequence."
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
  tags: [ecss, e-st-70-41c, pus-service-21, e7041-report-the-content-of-a-request-sequence, request-sequence-content-report, request-sequence-store, sequence-entry-release-offset, sequence-report-packing, under-construction-request-sequence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Request Sequencing — Report the Content of a Request Sequence (space-systems/ecss/e7041-report-the-content-of-a-request-sequence)

Use when the task is the content reporting step of the request sequencing
service of ECSS-E-ST-70-41C clause 6.21.8 — answering a request for the
content of one named sequence with a report that lists its entries in the
order the sequence will release them, and showing how many telemetry packets
that listing actually costs.

## Domain quick reference

- The report answers for one sequence, not for the store. The identifier the
  request carries either names a sequence the store holds or it does not, and
  an identifier that names nothing is a refusal with a reason, never an empty
  report that reads as an empty sequence.
- A sequence that is still being loaded has no settled content. Reporting it
  describes a state that changes before the packet reaches the ground, so the
  loading status is part of the answer and not an implementation detail.
- The order of the report is the release order, not the load order. Entries
  are presented by their offset from the start of the sequence, and entries
  sharing an offset keep the order they were loaded in so the listing is
  reproducible across two runs of the same request.
- The listing is bounded by the telemetry data field, not by the sequence.
  Each entry costs its own header plus its request, so a long sequence spills
  into successive content reports and the split has to be planned rather than
  discovered when the first packet overflows.
- An entry larger than one whole content report is unreportable at any split.
  No packing of the sequence rescues it, so it is a finding against the
  sequence and the report size together, not a packing failure.
- An empty sequence is a legitimate answer. It is a report with a header and
  no entries, and it is worth flagging because it usually means a load that
  never completed rather than a sequence deliberately left bare.

## Workflow

1. Validate the store, the requested identifier, the content report data
   field and the per-entry overhead; an overhead that fills the data field is
   an input error, not a zero-entry report.
2. Look the identifier up. If the store does not hold it, answer with the
   unknown status and stop; there is no content to order.
3. Validate every entry of the sequence: a whole non-negative release offset,
   a whole positive request size and a name that is unique inside the
   sequence.
4. Order the entries by release offset, breaking ties by load order, and
   record that ordering as the listing the report presents.
5. Cost each entry as its overhead plus its request, name any entry that
   exceeds a whole report, and otherwise pack the ordered entries greedily
   into successive reports.
6. Report the entry count, the ordering, the report split, the total octets
   and every finding: an unknown identifier, a sequence still being built, an
   empty sequence, or an entry no report can carry.

## Pitfalls

- Reporting an unknown identifier as an empty sequence. The ground then reads
  a sequence that was never loaded as a sequence that was loaded and left
  bare, and the load failure is lost.
- Listing the entries in load order. A sequence built out of order then
  reports in an order it will never execute in, and the review of the
  sequence checks the wrong release schedule.
- Sizing the split from the sum of the request sizes. The per-entry overhead
  is charged once per entry, so a sequence of many small requests needs far
  more packets than its payload total suggests.
- Splitting an oversized entry across two reports. The entry is reported in
  full or not at all; a half entry in each of two packets is not a content
  report, it is a corrupted one.
- Treating the loading status as advisory and reporting anyway. The content
  reported is a snapshot of a sequence still being written, and nothing in
  the packet tells the ground that.

## Behavior contract (gate 3)

The entry validation, release ordering, per-entry costing, oversize
detection, greedy packing and the assembled content report assessment are
exercised by the gate 3 contract test:
scripts/test_e7041_report_the_content_of_a_request_sequence.py against
scripts/e7041_report_the_content_of_a_request_sequence_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_report_the_content_of_a_request_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
