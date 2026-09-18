---
name: e2007-test-setup-photographic-records
description: "Document the photographic evidence set required for every setup, test point and calibration arrangement in an electromagnetic test report under ECSS-E-ST-20-07C clause 5.2.13. Use when the report is being closed: categorize every frame by its subject, confirm each subject holds enough distinct views, check resolution, caption, identification label and scale reference, reject a frame captured outside the validity window of the arrangement it shows, and hold the report while a subject is unphotographed or a captured frame stays outside it. Trigger: ecss, e-st-20-electrical-scope, emc-test-photographic-record, test-setup-photograph-coverage, calibration-arrangement-photograph, test-point-photograph-views, report-photograph-inclusion, photograph-caption-and-scale-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-test-setup-photographic-records, emc-test-photographic-record, test-setup-photograph-coverage, calibration-arrangement-photograph, test-point-photograph-views, report-photograph-inclusion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Test Reporting — Photographic Records of Setups, Test Points and Calibrations (space-systems/ecss/e2007-test-setup-photographic-records)

Use when the task is the ECSS-E-ST-20-07C clause 5.2.13 photographic evidence
set of an electromagnetic test report -- listing every subject that has to be
photographed, auditing each frame for resolution, caption, label, scale
reference and capture time, and holding the report while a subject is short of
views or a frame never reached the report.

## Domain quick reference

- Photographs are the only part of a report that lets a second laboratory
  rebuild the bench. Prose describes intent; the frame shows the routing,
  the separations and the instrument settings that were actually there.
- Three subject families are photographed, and each frame is categorized by
  which one it documents: the setup arrangements, the test points where
  signals were injected or monitored, and the calibration arrangements that
  set the reference levels. A frame documenting none of them is not evidence.
- A setup arrangement needs more than one distinct view. A single elevation
  hides the harness run behind the unit, so a second view is the requirement,
  and two frames of the same view add no coverage at all.
- Every frame carries usable metadata: resolution above a floor, a caption
  long enough to name what is shown, an identification label tying the frame
  to its subject, and -- where the evidence is geometric -- a dimensional
  reference in the frame.
- Capture time is part of the evidence. A frame taken hours after the bench
  was struck documents a different bench; the offset from the arrangement it
  claims to show is checked against a validity window.
- A photograph that exists on a camera card but was never placed in the
  report has not been delivered. Inclusion is a separate check from capture.

## Workflow

1. Catalogue the subjects: map every campaign subject to setup arrangement,
   test point or calibration arrangement. Reject an unrecognized subject
   kind, a duplicate subject name, an empty record, or a record holding no
   setup arrangement at all.
2. Audit each frame: resolve its subject on the catalogue, compute the frame
   resolution in megapixels, and check caption length, identification label
   and scale reference where the category demands one.
3. Check the capture offset of each frame against the validity window of the
   arrangement it documents, and confirm the frame was placed in the report.
4. Reduce the usable frames to distinct views per subject; a repeated view
   collapses to one, and an unusable frame contributes nothing.
5. Compare the distinct-view count of every subject against the requirement
   for its category and record each shortfall.
6. Aggregate the frame findings and the coverage findings and emit the gate
   token. Only an empty finding list releases the report.

## Pitfalls

- Counting frames instead of views. Six frames of the same elevation still
  leave the routing undocumented, so coverage is measured on distinct views.
- Letting an unusable frame count toward coverage. A frame rejected for a
  missing label is not evidence, and allowing it to fill a view quota hides
  the gap the audit exists to find.
- Photographing the setups and forgetting the calibration arrangements. The
  reference levels are as reproducible-or-not as the bench, and they are the
  first thing a reviewer asks to see.
- Treating capture time as bookkeeping. The frame that matters was taken
  while the arrangement stood; one taken after teardown documents a bench
  that no longer existed.
- Demanding a scale reference on every frame. A close-up of a test point is
  identification evidence, not geometric evidence, and a blanket rule there
  buries the real geometric findings in noise.
- Delivering a photograph folder alongside the report. Evidence that is not
  inside the report is not in the deliverable a reviewer receives.
- Letting a megapixel or minute sum land a few units in the last place below
  a floor and reading that as a non-conformance. The logic absorbs
  representation error with a named tolerance; the floors are never lowered.

## Behavior contract (gate 3)

The subject catalogue, frame audit, distinct-view coverage, capture-window,
report-inclusion and gate-token logic is exercised by the gate 3 contract
test: `scripts/test_e2007_test_setup_photographic_records.py` against
`scripts/e2007_test_setup_photographic_records_logic.py` (stdlib unittest,
offline).
Run: python3 scripts/test_e2007_test_setup_photographic_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
