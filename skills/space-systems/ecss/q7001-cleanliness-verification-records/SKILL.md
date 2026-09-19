---
name: q7001-cleanliness-verification-records
description: "Document cleanliness verification results so every figure traces back to the hardware it came from and the level it was graded against. Use when a verification dossier is being closed out and each record has to name its hardware item, surface, sampled area, method, instrument and day before the achieved level can be believed. Grades the level ladder in the right direction, refuses a record whose instrument calibration had lapsed on the measurement day, marks a record superseded by later handling of the same surface, finds the inventory surfaces no record covers, and returns per-record findings with the traceable coverage fraction. Trigger: ecss, q-st-70-01, cleanliness-verification-record, product-cleanliness-level-ladder, nvr-level-verification, verification-instrument-calibration, superseded-cleanliness-record, cleanliness-traceability-coverage."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-control, q7001-cleanliness-verification-records, cleanliness-verification-record, product-cleanliness-level-ladder, nvr-level-verification, verification-instrument-calibration, superseded-cleanliness-record, cleanliness-traceability-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Contamination Control — Cleanliness Verification Records (space-systems/ecss/q7001-cleanliness-verification-records)

Use when the task is the verification-record step of ECSS-Q-ST-70-01 — turning
a pile of cleanliness measurements into evidence that a named hardware surface
was delivered at a named cleanliness level. This leaf decides whether the
records are traceable; the post-cleaning verification leaf decides whether a
single measurement passes.

## Domain quick reference

- A cleanliness figure is not evidence on its own. It becomes evidence when it
  carries the hardware item, the surface, the area that was sampled, the
  method, the instrument, the day and the operator. Any of those missing and
  the figure describes nothing in particular.
- Levels live on two separate ladders. A surface particulate level bounds the
  largest particle tolerated on the witnessed area; a non-volatile residue
  level bounds the molecular loading on it. Both are ordered cleanest first,
  and a result is graded against a requirement on its own ladder only — a
  particulate count cannot answer a residue limit.
- A measurement taken with an instrument whose calibration had already lapsed
  is not a weak result, it is not a result. The comparison is made against the
  measurement day, not against the day the dossier is reviewed, and a
  calibration that expires on the measurement day is still valid on it.
- Cleanliness is a state, not a property. A record describes the surface at the
  moment of measurement, so any handling, opening or rework of that same
  surface afterwards supersedes it, and the surface is uncovered again until it
  is re-verified.
- Coverage is counted over inventory surfaces, not over records. Ten records on
  one surface leave the other two uncovered, and a record pointing at a surface
  the inventory never declared is an orphan: it neither covers anything nor
  quietly proves the inventory wrong.

## Workflow

1. Flatten the hardware inventory into the set of hardware-surface pairs the
   dossier has to cover, rejecting an item that declares the same surface twice.
2. Validate each record against the required key set, with a positive sampled
   area and integer day indices; a record missing its operator or instrument is
   an input error, not a record with gaps.
3. Grade the verified level against the required level on their shared ladder,
   and refuse the pair outright when the two sit on different ladders.
4. Test the instrument calibration against the measurement day and raise a
   finding when it had already lapsed.
5. Mark every record superseded by a later handling event on the same hardware
   surface, and drop it from the usable set.
6. Take the usable records, subtract the orphans, and report the surfaces still
   uncovered plus the traceable coverage fraction, comparing that fraction with
   completeness through a named tolerance rather than an exact float equality.
7. Return the per-record findings and the dossier disposition.

## Pitfalls

- Counting records instead of surfaces. A dossier can hold more records than
  surfaces and still leave a surface unverified; coverage is only meaningful
  over the declared inventory.
- Grading a residue result against a particulate limit because both were called
  the cleanliness level. The two ladders answer different hazards and a
  cross-ladder comparison is refused, not coerced.
- Accepting a lapsed-calibration measurement because the number looks
  reasonable. The figure has no traceable instrument behind it, so it cannot
  close a surface, however plausible it reads.
- Treating the newest record as authoritative without checking what happened to
  the surface afterwards. A re-work or an access opening after the measurement
  voids it regardless of how recent it is.
- Letting an orphan record close a gap by matching on hardware id alone. The
  surface has to match too, or a baffle measurement silently certifies a mirror.
- Comparing the coverage fraction to 1.0 with a bare equality. It is a ratio of
  integers reached through floating point; the completeness test carries a named
  tolerance instead.

## Behavior contract (gate 3)

The level ladders, record validation, calibration and level findings,
supersession by handling, orphan detection, coverage accounting and the dossier
disposition are exercised by the gate 3 contract test:
scripts/test_q7001_cleanliness_verification_records.py against
scripts/q7001_cleanliness_verification_records_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_cleanliness_verification_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
