---
name: q7022-shelf-life-records
description: "Audit the per-lot record a limited-shelf-life material carries under ECSS-Q-ST-70-22C: score the mandatory header fields, order and read the event log for an issue with no receipt behind it or activity after disposal, require every deviation entry to carry a reference, a disposition and a closure, require every extension to sit on a re-test, balance received quantity against issued, returned, scrapped and remaining, and check the retention period. Use when auditing stores records, preparing a shelf-life register for review, or closing a lot out. Trigger: ecss, q-st-70-22c, shelf-life-lot-record-audit, shelf-life-deviation-entry, shelf-life-event-chronology, shelf-life-quantity-balance, shelf-life-record-retention."
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
  tags: [ecss, q-st-70-22c-limited-shelf-life-control, q-st-70-22c, q7022-shelf-life-records, shelf-life-lot-record-audit, shelf-life-deviation-entry, shelf-life-event-chronology, shelf-life-quantity-balance, shelf-life-record-retention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Per-Lot Records and Deviations (space-systems/ecss/q7022-shelf-life-records)

Use when the task is the records clause of ECSS-Q-ST-70-22C: what the record
for one limited-shelf-life lot has to contain from receipt through to disposal,
and whether a record in front of you actually supports the decisions taken
against the lot.

## Domain quick reference

- The record is the lot. Material in a drum is anonymous; everything that makes
  it usable — its identity, its dates, where it has been, how much is left — is
  carried by the record, and a lot whose record cannot identify it is
  indistinguishable from unqualified material.
- Header completeness and event completeness are different defects and need
  separate answers. A record with an empty batch field is unusable outright; a
  record with a full header and three events is usable but has stopped being
  written, and the audit reports both rather than one score.
- The event log has to order before it can be read. Entries arrive out of
  sequence, so the audit sorts by date and keeps input order within a day,
  because a receipt and a storage move on the same morning did happen in the
  order the storekeeper wrote them.
- Three chronology defects end a record's value as evidence: an event before
  the material existed, an issue with no receipt behind it, and activity after
  disposal. Each means the log is describing something other than this lot.
- A deviation entry is only an entry when it carries a reference, a disposition
  and a closure state. A dated line saying something went wrong records the
  event and loses the decision, which is the part an auditor came for.
- An extension is a claim that a re-validation justified more life. The record
  has to hold the re-test event on or before the extension date, otherwise the
  extension is an assertion rather than a result.
- Quantity is the arithmetic check the rest of the record cannot fake. What
  came in equals what went out net of returns, plus what was scrapped, plus
  what is on the shelf; an unexplained residual means material left the system
  without a line.

## Workflow

1. Score the header against the mandatory field set — lot identifier, material,
   manufacturer, batch, manufacture, expiry and receipt dates, location,
   quantity received — and report the completeness percentage with the fields
   that are absent or blank.
2. Validate every event: a known type, a parsable date, a non-negative
   quantity. Order the log by date and keep same-day entries in input order.
3. Read the ordered log for chronology defects: an event before the manufacture
   date, no receipt at all, an issue preceding the first receipt, or any
   further activity after a disposal.
4. Read every deviation entry for its reference, disposition and closure, and
   count the entries still open as a finding in their own right.
5. Require every extension event to sit on or after a re-test event.
6. Balance the quantity account with a named tolerance rather than exact float
   equality, and report the unexplained residual when it does not close.
7. On a retired record, check that the retention period has run from the
   disposal date, then close with the completeness percentage, open deviation
   count, findings and a compliant or deficient verdict.

## Pitfalls

- Collapsing the audit into one completeness number. A thin log and a broken
  header fail for different reasons and are fixed by different people; one
  percentage hides which one you have.
- Sorting the event log by date alone. Same-day entries then arrive in an
  arbitrary order, and a receipt can end up after the issue it supplied, which
  manufactures a chronology finding that is not there.
- Accepting a deviation line without a closure state. An entry with no closure
  is an open deviation that reads as history, which is exactly how a lot with
  an unresolved excursion reaches a kitting list.
- Taking an extension date at face value. Without the backing re-test event in
  the same record the extension cannot be reconstructed, and the next auditor
  has to take the previous one's word for it.
- Balancing quantities with exact equality. Decimal masses summed as floats
  will not close bit-exactly; the residual is compared against a named
  tolerance so that a real leak is distinguished from arithmetic noise.
- Retiring a record when the lot is disposed of. Disposal starts the retention
  period, it does not end the record; the record outlives the material it
  describes by years.

## Behavior contract (gate 3)

The header scoring, event validation and ordering, chronology reading,
deviation-entry checks, extension backing, quantity balance and retention
check are exercised by the gate 3 contract test:
scripts/test_q7022_shelf_life_records.py against
scripts/q7022_shelf_life_records_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7022_shelf_life_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
