---
name: q7002-data-entry-to-materials-data
description: "Maintain a materials data set from thermal-vacuum outgassing screening results under ECSS-Q-ST-70-02C, feeding the declared-materials practice of ECSS-Q-ST-70C and ECSS-Q-ST-70-71C. Use when finished screening reports have to become reusable entries and a submission meets records already held. Builds the entry key from designation, manufacturer, product form and processing state rather than the trade name, records values at the data-set resolution, refuses an entry whose source report was never reportable, and separates a duplicate from an independent confirmation, a superseding later report, a stale earlier one and a same-date conflict. Trigger: ecss, q-st-70-02, materials-data-set-entry, declared-materials-list-record, outgassing-entry-key, superseding-outgassing-report, stale-outgassing-entry, outgassing-entry-conflict."
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
  tags: [ecss, q-st-70-materials-outgassing-scope, q7002-data-entry-to-materials-data, materials-data-set-entry, declared-materials-list-record, outgassing-entry-key, superseding-outgassing-report, outgassing-entry-conflict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening — Materials Data Set Entry (space-systems/ecss/q7002-data-entry-to-materials-data)

Use when the task is the data-recording step that follows an
ECSS-Q-ST-70-02C screening run — turning finished reports into entries a
declared-materials list under ECSS-Q-ST-70C and ECSS-Q-ST-70-71C can be
built from, and reconciling a new submission with what is already held.

## Domain quick reference

- The entry is identified by what was tested. Designation, manufacturer,
  product form and processing state together form the key; the trade
  name alone names a family. Two cure schedules of one adhesive are two
  entries, because the volatile fraction of an under-cured specimen has
  nothing to do with a post-baked one, and a data set that folds them
  together answers every later question with the wrong number.
- Values are recorded at the resolution the data set is written at. Two
  reports of the same material differ in the sixth decimal of a
  quotient neither of them published, and comparing the raw numbers
  makes every resubmission look like a new result.
- Every entry points at the report it came from, and an entry whose
  source report was not reportable never goes in. A data set is a
  pointer to evidence, so an entry with nothing usable behind it is
  worse than a gap: a gap gets tested, an entry gets trusted.
- Meeting an existing entry under the same key is where the judgement
  is. The same values from the same report is a resubmission; the same
  values from a different report is independent confirmation and worth
  recording as such; different values from a later report supersede;
  different values from an earlier report are stale and must not
  overwrite; different values from the same date are a conflict, and
  picking one silently destroys the only signal that something is
  wrong.
- Optional figures are part of the comparison. An entry that carries a
  recovered-mass-loss figure and one that does not are not the same
  entry, even when their other values agree.

## Workflow

1. Build the key from the four identifying fields, folding case and
   spacing so the same material submitted twice lands on one key, and
   refusing a blank field rather than keying on an empty string.
2. Validate the candidate: report reference, test date as an ISO
   calendar date, non-negative values, a condensable figure no larger
   than the total mass loss, and a recovered figure no larger than the
   total.
3. Normalize every value to the data-set resolution before anything is
   compared or stored.
4. Drop a candidate whose source report was not reportable, recording
   why rather than silently skipping it.
5. Look the key up. With nothing recorded, the candidate is a new entry.
6. With something recorded, compare values at the data-set resolution
   and then the dates: duplicate, independent confirmation, superseding,
   stale, or same-date conflict.
7. Apply only the outcomes that should change the data set — new and
   superseding — and leave a stale or conflicting submission out while
   raising its finding.
8. Report the resulting data set, the action taken for every candidate,
   and every finding.

## Pitfalls

- Keying on the trade name. It merges cure states, product forms and
  manufacturers into one entry whose value belongs to whichever report
  arrived last.
- Comparing unrounded values. Every resubmission then reads as a new
  result and the data set grows a history of digits nobody measured.
- Letting an older report overwrite a newer entry because it arrived
  later. Arrival order is not test order, and the data set has the test
  date precisely so it does not have to guess.
- Resolving a same-date conflict by keeping one value. The disagreement
  is the finding; silently choosing removes the only evidence that two
  runs of the same material disagreed.
- Recording an entry from a report that failed its own reporting
  checks. It looks identical to a good entry in the list and will be
  selected against for years.

## Behavior contract (gate 3)

The key construction, entry validation, value normalization, date
parsing, value comparison, reconciliation outcomes and data-set folding
are exercised by the gate 3 contract test:
scripts/test_q7002_data_entry_to_materials_data.py against
scripts/q7002_data_entry_to_materials_data_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7002_data_entry_to_materials_data.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
