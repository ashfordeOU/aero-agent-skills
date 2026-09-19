---
name: q7040-brazing-records
description: "Audit the record a brazement owes and decide whether it closes on its own evidence. Use when a brazed joint has been made and the traveller has to prove how, because the joint cannot be re-opened to find out: build the required field set from the process and whether flux was used, name the gaps in the order the set requires them, test the operator against both the certificate expiry and the continuity interval that disuse runs out, read the furnace run for its ramp, soak, cooling and atmosphere channels and for enough load thermocouples to see a cold corner, and close only when nothing is outstanding. Trigger: ecss, q-st-70-40-brazing, brazement-record-set, braze-operator-continuity-interval, braze-furnace-thermal-profile-trace, braze-procedure-qualification-record, braze-load-thermocouple-coverage."
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
  tags: [ecss, q-st-70-40-brazing, q7040-brazing-records, brazement-record-set, braze-operator-continuity-interval, braze-furnace-thermal-profile-trace, braze-load-thermocouple-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — Brazement Records (space-systems/ecss/q7040-brazing-records)

Use when the task is the records clause of ECSS-Q-ST-70-40: deciding
whether the traveller behind a brazed joint actually evidences how the
joint was made, by whom, in which furnace run and with what result.

## Domain quick reference

- A brazed joint cannot be re-opened. The record is the only history the
  joint has, which is why a gap in it is a gap in the joint's evidence
  and not a paperwork inconvenience.
- The procedure reference and its qualification record are two different
  fields. The reference is a pointer; the qualification record is what
  says the pointer leads to a process that was proved on coupons.
- Brazing is a manual-skill process even inside a furnace, because the
  cleaning, the filler placement and the fixturing are done by hand.
  That is why the operator is named on the record at all.
- Operator qualification fails in two independent ways. A certificate
  expires on a date. Currency also lapses through disuse when the
  operator has not run the process inside the continuity interval. A
  certificate valid for another year says nothing about an operator who
  last brazed nine months ago.
- The thermal profile is the process. A furnace run identity with no
  trace behind it records that a furnace was switched on, and that is
  all it records.
- The trace owes the ramp rate, the soak temperature, the soak duration
  and the controlled cooling rate. Soak temperature alone hides a ramp
  that took the assembly through a sensitisation range on the way up.
- The atmosphere log owes the vacuum level or the dew point. An
  inert-gas cycle run wet is a different process from the qualified one
  and leaves oxide the filler will not wet.
- Load thermocouples are not redundancy with the control channel. The
  control channel reports the hot zone; the load channels are what say
  a corner of the load ever reached soak.
- The inspection result closes the record. Without it the brazement has
  a history and no verdict.

## Workflow

1. Take the process and the flux answer and build the required field set
   from them, not from the fields the traveller happens to carry.
2. Compare the record against that set and report the gaps in the order
   the set requires them, so the chase list reads in working order.
3. Test the operator twice: certificate expiry against the braze date,
   and the gap since the last run of the same process against the
   continuity interval. Refuse a record whose last-run date sits after
   the braze date rather than treating it as a small transposition.
4. For a furnace process, read the run record for its four profile
   channels and for the number of load thermocouples, and report each
   absent channel by name.
5. Report every finding, not only the deciding one, so one recovery
   round closes the record instead of three.
6. Close the record only when no field is missing, the operator was
   current on the day, and the furnace run carries its full trace.

## Pitfalls

- Accepting the procedure reference as the qualification. The number on
  the traveller is a claim that a qualified procedure exists; the
  qualification record is the evidence that it does.
- Reading a valid certificate as a current operator. The two failure
  modes are independent and the continuity one is the one nobody
  notices, because nothing on the certificate changes when it happens.
- Treating a furnace run identity as furnace data. The identity says
  which run; the trace says what the run did.
- Grading the soak and ignoring the ramp and the cooling rate. Both ends
  of the cycle set the metallurgy, and a compliant soak with an
  uncontrolled cool is a different joint.
- Counting the control thermocouple as load instrumentation. It reports
  the furnace, not the part, and a single channel cannot distinguish a
  cold corner from a uniform load.
- Closing the record on the first finding. A record chased one gap at a
  time takes as many rounds as it has gaps, and each round loses a day.

## Behavior contract (gate 3)

The process-driven required field set, the ordered gap list, the
two-way operator currency test with its inconsistent-date refusal, the
furnace profile channel and load-thermocouple checks and the overall
record verdict are exercised by the gate 3 contract test:
scripts/test_q7040_brazing_records.py against
scripts/q7040_brazing_records_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7040_brazing_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
