---
name: q7001-cleanliness-history-database
description: "Maintain the contamination history a flight item carries under ECSS-Q-ST-70-01C, held per serial number rather than per programme. Use when cleaning operations, exposure events and cleanliness measurements have to be kept as one ordered ledger, when the exposure a unit has accumulated since its last cleaning is in question, or when a review asks whether the record has gaps: validate every entry against its unit and date, order the ledger, refuse a duplicate or an unordered reading, accumulate molecular and particulate exposure since the last cleaning, flag any monitoring interval longer than the declared maximum, and report what the unit still owes for traceability. Trigger: ecss, q-st-70-01c-cleanliness-scope, contamination-history-ledger, per-unit-cleanliness-record, cleanliness-monitoring-interval-gap, cumulative-contamination-exposure, contamination-event-traceability, post-cleaning-verification-record."
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
  tags: [ecss, q-st-70-01c-cleanliness-scope, q7001-cleanliness-history-database, contamination-history-ledger, per-unit-cleanliness-record, cleanliness-monitoring-interval-gap, cumulative-contamination-exposure, contamination-event-traceability, post-cleaning-verification-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Contamination History Database (space-systems/ecss/q7001-cleanliness-history-database)

Use when the task is the cleanliness record duty of ECSS-Q-ST-70-01C —
keeping, for each item by serial number, the cleaning operations, the
exposure events and the measurements that together say how clean that
item is and how it got there.

## Domain quick reference

- The history belongs to the item, not to the facility. Two units built
  in the same cleanroom on the same day can have different histories
  the moment one of them is unbagged for a fit check, so the ledger
  keys on serial number.
- Three entry kinds carry the whole history. A cleaning resets the
  accumulation, an exposure event adds to it, and a measurement states
  what was actually found. Anything that cannot be placed in one of the
  three is not a history entry and is refused rather than filed.
- Order is data. The same three entries in a different order describe a
  different unit, so the ledger is built in date order and an entry
  that arrives with an unreadable date is rejected rather than pushed
  to the end.
- Accumulation runs from the last cleaning, not from delivery. The
  useful figure is what has landed on the surface since it was last
  known clean; carrying it from the start of the programme double
  counts everything a cleaning already removed.
- A cleaning without a verification measurement after it is an
  assertion. The unit is only known clean at the level the measurement
  read, so the ledger tracks whether each cleaning was closed by a
  reading.
- Gaps matter more than values. A ledger with no measurement across a
  long interval says nothing about that interval, and a unit that sat
  unmonitored through a facility move has an unbounded exposure, not a
  zero one.
- Duplicates corrupt the accumulation silently. The same reading filed
  twice inflates the exposure and moves the unit towards a
  nonconformance it never had, so identical entries are refused at
  entry rather than reconciled later.

## Workflow

1. Take the unit identifier and the raw entries, and reject a case that
   cannot name the unit rather than filing orphan records.
2. Validate each entry: a known kind, a readable calendar date, a
   non-negative value where the kind carries one, and a contaminant
   ledger named where the kind measures one.
3. Refuse an entry identical to one already held, and keep only entries
   belonging to the unit under examination.
4. Order the ledger by date, then by the order entries were supplied so
   that two events on one day stay stable.
5. Find the last cleaning, and accumulate molecular and particulate
   exposure over the exposure events and measurements that follow it.
6. Walk the measurement dates and report every interval longer than the
   declared maximum monitoring interval, naming its length.
7. Report the traceability state: whether the unit has a cleaning, a
   verification reading after it, and an unbroken monitoring record;
   name what is absent rather than returning a score.

## Pitfalls

- Keying the history on the programme or the facility. The exposure a
  unit carries is a property of that unit, and a shared record cannot
  answer which serial number was out of its bag.
- Accumulating from the first entry rather than the last cleaning. The
  cleaning removed what came before it, so an accumulation that reaches
  past it reports contamination that is no longer on the item.
- Filing a cleaning as evidence of cleanliness. Only the measurement
  after it says what level was reached, and a cleaning with no reading
  behind it leaves the unit at an unknown level.
- Reading an unmonitored interval as a clean one. No data is not a zero
  reading, and treating a gap as nominal is how a storage period with a
  failed air handler disappears from the record.
- Reconciling duplicate readings after the fact. By then the
  accumulation has already moved, so the refusal has to happen when the
  entry is offered.
- Comparing an accumulated exposure against a limit by bare arithmetic.
  Summed floating-point increments landing exactly on a limit can miss
  it by a few units in the last place, so the comparison absorbs that
  representation error.

## Behavior contract (gate 3)

Entry validation, duplicate refusal, chronological ordering,
accumulation since the last cleaning, monitoring-gap detection and the
traceability state are exercised by the gate 3 contract test:
scripts/test_q7001_cleanliness_history_database.py against
scripts/q7001_cleanliness_history_database_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_cleanliness_history_database.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
