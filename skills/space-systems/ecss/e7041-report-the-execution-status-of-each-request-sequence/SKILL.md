---
name: e7041-report-the-execution-status-of-each-request-sequence
description: "Generate the whole-store execution status report of ECSS-E-ST-70-41C clause 6.21.6, saying what every request sequence held is currently doing rather than what it contains. Use when the question is which sequences are running and what became of the rest: covering every sequence with no identifier list accepted, carrying an identifier and a status per entry, deriving each status from the engine's running set and the sequence's own released count instead of echoing a stored field, separating never-started from stopped part way from ran to the end, and carrying totals a receiver can check a transfer against. Trigger: ecss, e-st-70-41-packet-utilization-scope, request-sequence-execution-status-report, request-sequence-derived-execution-status, request-sequence-status-report-completeness, request-sequence-running-set."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-report-the-execution-status-of-each-request-sequence, request-sequence-execution-status-report, request-sequence-derived-execution-status, request-sequence-status-report-completeness, request-sequence-running-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Report the Execution Status of Each Request Sequence (space-systems/ecss/e7041-report-the-execution-status-of-each-request-sequence)

Use when the task is the status-reporting request of ECSS-E-ST-70-41C
clause 6.21.6 -- reporting, for every request sequence the on-board
store holds, what the engine is doing with it, with the four normative
items that clause places on the report.

## Domain quick reference

- The content reports answer what the store HOLDS. This one answers
  what it is DOING, and those two questions have different audiences
  and different failure modes.
- It covers the whole store by construction. There is no identifier
  list, because an operator asking what is running cannot be expected
  to name the sequence they have forgotten about.
- Status is derived, never stored. It is a function of the load state,
  the engine's running set and the released count, so a stored status
  field can only drift away from all three and be reported as fact.
- Four non-running outcomes look alike from the ground and are not
  alike at all: a slot holding no body, a body still arriving, a body
  loaded that never started, a body stopped part way, and a body that
  ran to its end. Each calls for a different next action.
- Stopped part way is the one worth isolating. It means requests went
  out and then stopped going out, so there is recovery work outstanding
  that no other status implies.
- The engine's running set outranks the progress counters. A sequence
  with every request released is still executing if the engine says so,
  because the last request may not have reported completion yet.
- The totals exist so a receiver can detect a truncated transfer
  without knowing what the report should have contained.

## Workflow

1. Refuse an identifier list before anything else; narrowing a
   whole-store sweep removes the only thing it offers.
2. Normalize the store and reject a duplicate identifier, a released
   count above the body length, an empty slot carrying requests, a
   loaded slot carrying none, or an unloaded slot claiming releases.
3. Normalize the engine's running set against that store, rejecting a
   repeated identifier, one the store does not hold, and one whose
   slot is not loaded.
4. Derive each status: empty and under-load first, then the engine's
   running set, then the released count against the body length to
   separate inactive, aborted and completed.
5. Assemble one entry per sequence in store order, each carrying the
   identifier, the status, the load state and the pending count.
6. Reconcile any declared status against the derived one, compute the
   totals from the assembled entries, verify the report against its own
   totals, and close with the verdict plus the sequences that drifted.

## Pitfalls

- Reporting a stored status field. It was written by whatever last
  touched the sequence, and the receiver reads it as the current state
  of the spacecraft.
- Collapsing inactive, aborted and completed into "not running". The
  one with outstanding recovery work becomes indistinguishable from
  the two with none.
- Letting the released counters outrank the engine. A sequence whose
  last request is still in flight reports completed, and the ground
  reuses the slot underneath it.
- Omitting empty and loading slots from the report. The sequence count
  then depends on what happens to be loaded, and a receiver cannot use
  it to detect truncation.
- Accepting an identifier list for this report. The sweep returns the
  sequences the requester already suspected, which is never the set
  that needed the sweep.
- Computing the totals from the store rather than from the assembled
  entries. They then agree with the intent instead of the content and
  a truncation passes its own check.
- Treating a declared-versus-derived disagreement as a reporting
  choice. It is a defect in the store, and reporting either value
  without the finding hides it.

## Behavior contract (gate 3)

The selector refusal, store normalization, engine running-set
validation against the store, status derivation across all six
outcomes, entry assembly in store order, declared-versus-derived
reconciliation, entry-derived totals and the report self-consistency
check are exercised by the gate 3 contract test:
scripts/test_e7041_report_the_execution_status_of_each_request_sequence.py
against
scripts/e7041_report_the_execution_status_of_each_request_sequence_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_report_the_execution_status_of_each_request_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
