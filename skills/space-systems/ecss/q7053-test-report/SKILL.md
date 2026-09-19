---
name: q7053-test-report
description: "Document the cycles, degradation data and conclusion of an ECSS-Q-ST-70-53C sterilization-compatibility test, or grade a report already issued. Use when an exposure campaign is finished and the record has to stand on its own for a reviewer who was not there. Checks identification down to batch and process, matches the logged cycles against the planned count, catches a gap or a repeat in the cycle numbering, grades each achieved parameter against its window, pairs an out-of-window value with a recorded deviation, flags a deviation recorded against nothing, requires a pre and a post value for every declared property, and tests the stated conclusion against the data behind it. Trigger: ecss, q-st-70-53-sterilization-compatibility-scope, sterilization-compatibility-test-report, exposure-cycle-log-completeness, achieved-cycle-parameter-window, out-of-window-cycle-deviation, report-conclusion-consistency."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-test-report, sterilization-compatibility-test-report, exposure-cycle-log-completeness, achieved-cycle-parameter-window, out-of-window-cycle-deviation, report-conclusion-consistency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Test Report (space-systems/ecss/q7053-test-report)

Use when the task is the reporting step of an ECSS-Q-ST-70-53C
materials-and-hardware compatibility test — writing, or grading, the
record of what was exposed, how many cycles it actually saw, what the
exposure did to it, and what the test concluded.

## Domain quick reference

- A compatibility report is read by someone deciding whether to reuse
  the result on a different programme, so the identification has to
  reach the batch and the processing state of the item and the
  sterilization process it was run through. A generic material name
  makes the whole report unusable as evidence.
- The cycle log is the spine of the report. The number of cycles
  actually run, not the number planned, is what the degradation data
  belongs to, so a gap or a repeat in the cycle numbering is a defect
  in the record even when the totals happen to agree.
- Each cycle carries achieved parameters, and each of those is graded
  against its own window. An achieved value outside its window is not
  automatically a failed test; it is a failed record unless a deviation
  is written against it.
- A deviation recorded against a cycle whose parameters were all inside
  their windows is equally a defect. It means the deviation belongs to
  something else, and a reviewer cannot tell what.
- Degradation data is a pre and a post value per declared property. A
  property with only one of the two is unevidenced; it is not a
  zero-change property, and it cannot support a conclusion.
- The conclusion is graded against the data, not accepted as written. A
  statement of compatibility standing over a failed property or an
  incomplete cycle log is the single defect that makes a report
  actively misleading rather than merely thin.

## Workflow

1. Check the identification block for every required field and report
   the ones missing by name.
2. Validate each cycle record: a positive integer index, a mapping of
   achieved parameters, and an optional deviation reference.
3. Compare the logged cycle count with the planned count, and check the
   indices form a complete run with no gap and no repeat.
4. Grade each achieved parameter against its declared window, absorbing
   representation error at the bound with a named tolerance; report a
   parameter the windows declare but the cycle never recorded.
5. Pair each out-of-window value with the cycle's deviation reference;
   report an unpaired breach, and report a deviation reference on a
   cycle with nothing out of window.
6. Require a pre and a post value for every declared property, and
   carry each property's own acceptability verdict through.
7. Form the completeness score as the share of required record elements
   actually present, then test the stated conclusion against the
   property verdicts and the cycle findings and report any conflict.

## Pitfalls

- Reporting the planned cycle count. The degradation data belongs to
  the cycles that were actually run, and the two numbers diverge
  exactly when it matters.
- Accepting a cycle log whose totals agree but whose indices skip. A
  repeated index hides a cycle nobody recorded.
- Treating an out-of-window achieved value as a test failure. It is a
  record defect first; whether the test failed depends on the
  degradation data, and the deviation is what lets both be read.
- Filling a missing post-exposure value with the pre-exposure one. An
  unevidenced property is reported as unevidenced; it never becomes a
  zero-change property.
- Copying the conclusion the test engineer wrote. The conclusion is
  graded against the property verdicts and the cycle findings, and a
  compatibility statement over a failed property is reported as a
  conflict.

## Behavior contract (gate 3)

The identification check, cycle-record validation, sequence and count
checks, achieved-parameter window grading, deviation pairing,
degradation-table completeness, completeness scoring and conclusion
consistency are exercised by the gate 3 contract test:
scripts/test_q7053_test_report.py against
scripts/q7053_test_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7053_test_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
