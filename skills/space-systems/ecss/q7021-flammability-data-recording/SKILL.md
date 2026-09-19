---
name: q7021-flammability-data-recording
description: "Document upward flame propagation screening outcomes as materials data set entries under ECSS-Q-ST-70-21C, feeding the declared-materials practice of ECSS-Q-ST-70-71C and ECSS-Q-ST-70C. Use when finished flammability runs must become reusable records and a use environment has to be checked against the atmosphere actually tested. Keys the entry on material, thickness band and tested oxygen partial pressure rather than trade name, categorizes the specimen set into a rating, carries a drip restriction into the declared list, refuses an unreportable run, and separates a duplicate from a confirmation, a superseding later run and a stale earlier one. Trigger: ecss, q-st-70-21, flammability-data-set-entry, flammability-entry-key, tested-oxygen-partial-pressure, flammability-rating-record, superseding-flammability-run, flammability-drip-restriction."
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
  tags: [ecss, q-st-70-21-flammability-scope, q7021-flammability-data-recording, flammability-data-set-entry, flammability-entry-key, tested-oxygen-partial-pressure, flammability-rating-record, flammability-drip-restriction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Flammability Screening — Materials Data Set Recording (space-systems/ecss/q7021-flammability-data-recording)

Use when the task is the data step that follows an ECSS-Q-ST-70-21C
upward flame propagation run — turning observed specimens into entries a
declared-materials list under ECSS-Q-ST-70-71C and ECSS-Q-ST-70C can be
built from, and reconciling a new run with what is already held.

## Domain quick reference

- A flammability entry is identified by what was tested and by the
  atmosphere it was tested in. Designation, manufacturer, product form
  and processing state name the material; thickness band and the oxygen
  partial pressure of the test atmosphere name the condition. The same
  film at 0.5 mm in a reduced-pressure enriched atmosphere and at 2.0 mm
  in sea-level air are two entries, because neither result says anything
  about the other.
- Oxygen partial pressure, not oxygen percentage, is what the entry
  records. Thirty percent oxygen at 70 kPa is a milder atmosphere than
  sea-level air, and an entry that stores only the percentage will be
  read as the more severe of the two for the rest of its life.
- The rating comes from the specimen set. A run below the minimum
  specimen count is not a run; the worst specimen governs; a specimen
  that never self-extinguished, or that burned past the observation
  limit, makes the whole run propagating however well the others behaved.
- Dripping that ignites the indicator below the specimen does not make
  the material propagating, but it restricts where it may be installed.
  That restriction belongs in the entry, travelling into the declared
  list, not in the memory of whoever watched the run.
- Every entry points at the run it came from, and an entry whose run was
  not reportable never goes in. A gap gets tested; an entry gets trusted.
- Coverage runs one way. A test atmosphere at least as severe as the use
  atmosphere covers it; a milder test is not evidence.

## Workflow

1. Build the key from the four material fields, the thickness band and
   the atmosphere, folding case and spacing so one material submitted
   twice lands on one key and refusing a blank field.
2. Compute the oxygen partial pressure from volume fraction and total
   pressure, and round geometry and atmosphere to the data-set
   resolution before anything is compared or stored.
3. Validate the specimen set: minimum count, non-negative burn lengths,
   boolean extinction and drip observations.
4. Categorize the run into not-propagating, not-propagating with a drip
   restriction, or propagating, recording the worst burn length.
5. Drop a candidate whose run was not reportable, recording why rather
   than silently skipping it.
6. Look the key up. With nothing recorded, the candidate is a new entry;
   otherwise compare rating and worst burn length, then the dates:
   duplicate, independent confirmation, superseding, stale, or conflict.
7. Apply only the outcomes that should change the data set — new and
   superseding — and leave a stale or conflicting run out with a finding.
8. Emit the declared-list cross-reference for every recorded entry,
   carrying the rating, the tested atmosphere and any restriction.

## Pitfalls

- Keying on the trade name or on the material alone. It merges
  thicknesses and atmospheres into one entry whose rating belongs to
  whichever run arrived last.
- Storing oxygen percentage instead of partial pressure. A 30 percent
  result at reduced pressure then looks like it bounds sea-level air,
  which it does not.
- Letting one good specimen soften a run. The specimen that kept burning
  is the result; averaging it away is how a propagating material enters
  a declared list.
- Treating drip ignition as a pass with no consequence. The installation
  restriction is the only thing standing between that entry and a use
  with something ignitable underneath.
- Letting an older run overwrite a newer entry because it arrived later.
  Arrival order is not test order.
- Resolving a same-date disagreement by keeping one rating. The
  disagreement is the finding.

## Behavior contract (gate 3)

Key construction, partial-pressure computation, thickness rounding,
specimen validation, run categorization, atmosphere coverage,
declared-list linking, reconciliation outcomes and data-set folding are
exercised by the gate 3 contract test:
scripts/test_q7021_flammability_data_recording.py against
scripts/q7021_flammability_data_recording_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7021_flammability_data_recording.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
