---
name: q7005-record-in-cleanliness-database
description: "Maintain the cleanliness verification history a programme keeps from its ECSS-Q-ST-70-05C infrared contamination results. Use when finished analyses have to become entries a later query can find and a new submission meets records already held: key an entry on the hardware item, the surface zone and the method rather than on a description, hold every value at the resolution the history is written at, store a non-detect as its bound instead of a zero, separate a duplicate from an independent confirmation, a back-dated entry and a same-date conflict, and report the trend across the last two verifications. Trigger: ecss, q-st-70-05-ir-contamination-scope, cleanliness-verification-history, surface-zone-entry-key, non-detect-stored-as-bound, same-date-verification-conflict, cleanliness-degradation-trend."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-record-in-cleanliness-database, cleanliness-verification-history, surface-zone-entry-key, non-detect-stored-as-bound, same-date-verification-conflict, cleanliness-degradation-trend]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Cleanliness Verification History (space-systems/ecss/q7005-record-in-cleanliness-database)

Use when the task is the data-recording step that follows an
ECSS-Q-ST-70-05C infrared contamination analysis — turning finished
results into entries in the cleanliness verification history a
programme keeps for its hardware, and reconciling a new submission with
what is already held.

## Domain quick reference

- An entry is identified by what was verified. The hardware item, the
  surface zone and the measurement method together form the key. A
  description names nothing a later query can find, and a part number
  alone folds the optical face and the mounting flange into one
  history that answers every question with the wrong number.
- The history is a history. A newer result becomes the current level;
  it does not replace the older entry, because the trend across
  verifications is the reason the record is kept at all. Overwriting
  gives a database that always looks clean and can never show a drift.
- Values are held at the resolution the history is written at. Two
  analyses of one surface differ in the sixth decimal of a quotient
  neither of them published, and comparing raw values makes every
  resubmission look like a new result and every duplicate look like a
  conflict.
- A second reading on a different day with the same value is a
  confirmation and is worth recording as one. A second reading on the
  same day with a different value is a conflict: both cannot be the
  verification of that day, and holding it unresolved is better than
  letting whichever arrived last win.
- A back-dated entry belongs in the history but not at the front of it.
  It is accepted, marked, and does not displace the current level.
- A non-detect is stored as its quantitation bound. A zero claims a
  measurement nobody made, and an empty field loses a verification that
  did happen and did demonstrate something.
- An entry points at the analysis it came from, and an entry whose
  source analysis was never reportable has nothing behind it. Recording
  it makes a defective analysis permanent and quotable.
- A trend taken across a bound is indicative. A bound and a value are
  different kinds of number, and a fall from a value to a bound may be
  a cleaner surface or merely a less sensitive method.

## Workflow

1. Resolve the policy: the resolution the history stores levels at, and
   the rise between verifications that counts as degradation.
2. Build the key from the item, the surface zone and the method,
   refusing a record that cannot supply all three.
3. Validate the result: a detection with a level, or a non-detect with a
   quantitation limit, never both and never neither; quantize whichever
   applies onto the history resolution.
4. Refuse an entry whose source analysis was not reportable, and one
   that points at no analysis report.
5. Compare with the entries already held under that key. Same date and
   same value is a duplicate; same date and a different value is a
   conflict held for resolution.
6. Otherwise append: mark the entry current when it is the newest,
   mark it back-dated when it is not, and call it a confirmation when
   it repeats the value of the entry immediately before it.
7. Report the trend over the last two entries for a key — improving,
   stable or degrading — flagging a rise beyond the permitted fraction
   and marking a trend taken across a bound as indicative.
8. Post a sequence of records in order and return every disposition,
   keeping refusals and conflicts in their own groups.

## Pitfalls

- Keying on the part number alone. One history then mixes surfaces with
  different allocations and different exposure, and no query can
  separate them again.
- Overwriting the previous verification. The record loses the only
  thing it was kept for, and a degrading surface looks clean at every
  single point in time.
- Comparing raw values instead of stored ones. Every resubmission then
  reads as a fresh result and every genuine repeat reads as a conflict.
- Resolving a same-date disagreement by keeping the later arrival.
  Arrival order is not evidence; the conflict is the finding.
- Letting a back-dated entry become the current level. The most
  recently typed entry is not the most recent verification.
- Recording a non-detect as zero, and recording an entry from an
  analysis that was never reportable. Both make a number permanent that
  nothing supports.

## Behavior contract (gate 3)

The entry key, the resolution quantization, the detection and
non-detect storage rules, the refusal of an unsupported entry, the
duplicate, conflict, confirmation and back-dated dispositions, the
current-entry lookup, the trend with its degradation and bound findings
and the ordered posting of a sequence are exercised by the gate 3
contract test: scripts/test_q7005_record_in_cleanliness_database.py
against scripts/q7005_record_in_cleanliness_database_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7005_record_in_cleanliness_database.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
