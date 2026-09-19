---
name: e7041-storage-control-processing-logic
description: "Determine what each packet store does with a generated telemetry report under ECSS-E-ST-70-41C clause 6.15.4.3. Use when the task is tracing why a report is or is not on board: gating on the storage control of its application process, finding every packet store whose definitions select it, holding one copy where a store selects it twice, discarding at a full bounded store, evicting the oldest records at a circular one, separating a report larger than a whole store from a fullness discard, and returning a named disposition per store. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, storage-control-routing-decision, packet-store-report-disposition, circular-store-eviction-count, application-process-storage-gate, oversized-report-sizing-error."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-storage-control-processing-logic, storage-control-routing-decision, packet-store-report-disposition, circular-store-eviction-count, application-process-storage-gate, oversized-report-sizing-error]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Storage Control Processing Logic (space-systems/ecss/e7041-storage-control-processing-logic)

Use when the task is the storage control processing logic of
ECSS-E-ST-70-41C clause 6.15.4.3 -- what the on-board storage and
retrieval service actually does with each generated report once the
storage-control definitions have said which packet stores want it.

## Domain quick reference

- Four gates decide a copy, in this order: the storage control of the
  generating application process, the definitions of the store, the
  storage state of the store, and whether the report fits. Each gate
  has its own named disposition, because each calls for a different
  response on the ground.
- The application-process gate is one switch that silences a whole
  process without touching a single definition. A report refused
  there is refused at every store at once, and the configuration is
  unchanged when the switch goes back on.
- Selected twice, stored once. A store whose definitions cover a
  report through both a wildcard and a specific entry holds one copy.
  Counting the definitions instead of the stores doubles the octets
  the budget thinks it is spending.
- Store type only matters at the moment the store is full. A bounded
  store discards the arriving report and keeps its history; a
  circular store evicts its oldest records until there is room. The
  eviction count is worth reporting -- it is how much history the
  current picture cost.
- A report larger than the store's whole capacity is a sizing error,
  not a fullness discard. Eviction can never make room for it, so a
  circular store that reports it as an overwrite hides the fault and
  empties itself trying.
- "Nothing was stored" is four different situations and one of them
  is normal. A report nobody selected, a silenced process, a store
  switched off and a store that filled up each need their own reason
  in the disposition.
- One store failing never stops another copy. The stores are
  independent, and a disabled long-term store must not suppress the
  copy the circular anomaly store took.

## Workflow

1. Validate the report -- application process, report type, message
   subtype, a positive size in octets -- and the packet store working
   states, refusing a state that already holds more than its capacity.
2. Check the generating application process against the storage
   control enable set once, for the whole report.
3. Collect the packet stores whose definitions select the report,
   naming each store once however many of its definitions match.
4. Refuse a store the definitions name but the table does not hold;
   that is a configuration mismatch, not a routing outcome.
5. Offer the report to each selecting store in turn: name the sizing
   error first, then the disabled storage state, then fit it against
   the free octets.
6. On a full bounded store discard and keep the content; on a full
   circular store evict oldest-first until the report fits, counting
   the records evicted.
7. Return the per-store dispositions, the copy count and, when no
   store selected the report at all, the report-level reason.
8. Over a stream, carry the store states forward and report record
   counts, occupancy, fill fraction, copies stored and evictions.

## Pitfalls

- Counting matching definitions instead of selecting stores. The
  wildcard and the specific entry in one store become two copies that
  never existed.
- Reporting an oversized report as a fullness discard. A circular
  store then evicts its whole content, one record at a time, for a
  report that was never going to fit.
- Collapsing every empty outcome into "not stored". The operator
  cannot tell a silenced process from a store somebody left switched
  off, and re-enabling the wrong one changes nothing.
- Letting a disabled store abort the routing of the report. The copy
  in the other store is the one the anomaly investigation needs.
- Evicting on a bounded store because the arithmetic is the same. It
  is the same arithmetic and the opposite intention: the bounded
  store exists to keep the beginning of the record.
- Applying the application-process gate per store. It is one decision
  for the report, and testing it per store invites a partial result
  that no configuration can produce.

## Behavior contract (gate 3)

The report and store-state validation, the application-process gate,
the select-once rule, the bounded discard, the circular eviction
count, the oversized-report separation, the per-store dispositions
and the stream summary are exercised by the gate 3 contract test:
scripts/test_e7041_storage_control_processing_logic.py
against
scripts/e7041_storage_control_processing_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_storage_control_processing_logic.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
