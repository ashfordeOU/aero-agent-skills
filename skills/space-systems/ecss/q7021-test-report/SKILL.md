---
name: q7021-test-report
description: "Audit a flammability test report for the conditions, results and observations ECSS-Q-ST-70-21C expects it to carry, and assemble the list of what is missing. Use when a report has come back from a laboratory and somebody has to decide whether it can be filed as screening evidence or has to go back. Checks the identification, specimen, condition, result and observation fields, separates a blocking omission from an advisory one, cross-checks the report against itself so a burn longer than its specimen or a quoted worst case that is not the worst is caught, and returns the section order a compliant report follows. Trigger: ecss, q-st-70-21, flammability-test-report-completeness, flammability-test-condition-record, specimen-identification-fields, report-internal-consistency, blocking-versus-advisory-omission, worst-case-result-cross-check."
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
  tags: [ecss, q-st-70-21-flammability-screening-scope, q7021-test-report, flammability-test-report-completeness, flammability-test-condition-record, specimen-identification-fields, report-internal-consistency, blocking-versus-advisory-omission]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Flammability Screening — Test Report (space-systems/ecss/q7021-test-report)

Use when the task is the reporting step of the ECSS-Q-ST-70-21C
flammability screening test — establishing that a report records the
conditions the run was carried out under, the results it produced and
the observations made while producing them, in a form a later reader
can act on without calling the laboratory.

## Domain quick reference

- A flammability result is meaningless without its conditions. The same
  material clears and fails depending on the oxygen concentration, the
  pressure, the ignition source and how long the specimens were
  conditioned, so a report carrying results and no conditions records a
  number with no standing.
- Specimen identity is part of the result. Thickness, orientation and
  batch decide how a material burns, and a report that names only the
  material describes a class of specimens rather than the ones that
  were tested, which makes the run unrepeatable.
- The observations are evidence in their own right. Whether the
  specimen dripped and whether it self-extinguished are the inputs the
  acceptance decision needs; recorded as prose in a covering note they
  are lost the moment the report is filed.
- Omissions are not equal. A missing ignition source stops the report
  being usable; a missing ambient temperature is worth saying and does
  not. Grading them together either blocks usable reports or files
  unusable ones, so the completeness figure is taken over the blocking
  fields alone.
- A complete report can still be wrong. A burn length longer than the
  specimen it was measured on, a result count that disagrees with the
  specimen count, a run dated before the conditioning that preceded it,
  and a quoted worst case that is not the worst of the rows are all
  contradictions no field-presence check can see.
- A report that has to go back should be rebuilt against the section
  order, not patched. Patching preserves whatever produced the
  contradiction in the first place.

## Workflow

1. Check the outer shape: a mapping of known sections, each carrying a
   mapping. Refuse a section outside the reporting structure rather
   than ignoring it.
2. Walk the blocking fields in reporting order and list every absence,
   counting an empty string and an empty list as absent while keeping a
   legitimate false observation as present.
3. Walk the advisory fields the same way and keep the two lists apart.
4. Cross-check the results against the specimens: the row count against
   the declared specimen count, each burn length against the specimen
   it was measured on, and the quoted worst case against the longest
   row, absorbing floating-point representation error in that last
   comparison rather than raising a phantom contradiction.
5. Cross-check the conditions for physicality, and the test date
   against the conditioning end date, counting a run on the
   conditioning end date as in order.
6. Compute completeness over the blocking fields only.
7. Assign the verdict in precedence order: return for completion while
   blocking fields are absent, return for correction when the report is
   complete but contradicts itself, fileable with advisories when only
   advisory fields are absent, fileable otherwise — and return the
   section skeleton with it.

## Pitfalls

- Filing results without the conditions that produced them. The number
  survives; what it means does not.
- Naming the material and not the specimen. Thickness and orientation
  change the answer, and without them nobody can repeat the run.
- Letting advisory omissions into the completeness figure. The figure
  then falls for things that never blocked anything, and a genuinely
  incomplete report is indistinguishable from a tidy one.
- Accepting a quoted worst case without checking it against the rows.
  It is the number the acceptance decision uses, and it is the one most
  often carried over from a previous report.
- Treating an internally contradictory report as merely untidy. A burn
  length longer than its specimen means something in the chain is
  mislabelled, and the results cannot be trusted until it is found.
- Recording the observations in a covering note. They are inputs to the
  acceptance decision, and they have to travel with the results.

## Behavior contract (gate 3)

The report shape validation, blocking and advisory omission lists,
result-to-specimen cross-checks, worst-case comparison with tolerance,
condition physicality checks, conditioning-date ordering, completeness
ratio and verdict precedence are exercised by the gate 3 contract test:
scripts/test_q7021_test_report.py against
scripts/q7021_test_report_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7021_test_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
