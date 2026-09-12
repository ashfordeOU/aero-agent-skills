---
name: interface-verification-test
description: "Use when verify interface compliance between spacecraft structural
  subsystems or components per ECSS E-ST-32C clause 4.6.3.22: categorize each
  interface as mechanical, electrical, thermal, fluid, or optical; select the
  verification method (inspection, analysis, or test) appropriate to the interface
  type; perform dimensional fit checks against the tolerance stack in the Interface
  Control Document; confirm every interface carries a valid ICD reference; and
  aggregate per-interface findings to determine overall compliance. Trigger: ecss,
  e-st-32-structures-scope, interface-verification, icd, dimensional-fit,
  structural-interface, inspection, test-verification, fit-check."
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
  tags: [ecss, e-st-32-structures-scope, interface-verification, icd, dimensional-fit, structural-interface, inspection, test-verification, fit-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Interface Verification by Test or Inspection (space-systems/ecss/interface-verification-test)

Use when the task is verifying that structural interfaces between spacecraft
subsystems or components meet their Interface Control Document (ICD) requirements,
following the procedure outlined in ECSS E-ST-32C clause 4.6.3.22. The procedure
covers categorizing each interface by type, selecting the appropriate verification
method, checking dimensional fit against the ICD tolerance stack, and confirming
every interface carries a valid ICD reference before declaring compliance.

## Domain quick reference

- Clause 4.6.3.22 requires that each interface between structural assemblies be
  formally verified either by physical inspection, by supporting analysis, or by
  dedicated test, depending on the nature and criticality of the interface. The
  method selected must be traceable to the ICD.
- Interfaces are grouped into five categories: mechanical (bolted, bonded,
  riveted, welded joints and mating structural surfaces), electrical (connector
  and harness pass-throughs that impose structural loads), thermal (conductive
  and radiative contact surfaces that carry thermo-elastic loads), fluid
  (pressure lines and fittings that transmit fluid-induced structural loads), and
  optical (alignment-critical interfaces for sensors and instruments).
  Each interface is placed in exactly one category before its verification
  method is selected.
- Verification method selection follows the interface category and available
  facility: electrical and optical interfaces require functional test; any
  interface category where a dedicated test facility exists defaults to test;
  otherwise inspection is the baseline method. Analysis alone is not a
  standalone verification for dimensional fit — it supplements inspection or test.
- A dimensional fit check confirms that the measured gap or clearance at the
  mating surface falls within the tolerance band specified in the ICD. The check
  computes the deviation from the ICD nominal dimension and compares it against
  the ±tolerance. A surface outside the band is a non-compliant finding.
- Every interface must carry a valid ICD reference. An interface with no ICD
  reference is a non-compliant finding regardless of the dimensional result,
  because traceability to a controlled requirement document cannot be established.

## Workflow

1. Collect the full interface inventory from the structural ICD set. For each
   interface record the interface identifier, category (mechanical / electrical /
   thermal / fluid / optical), the ICD nominal dimension and its ±tolerance, the
   measured actual dimension, the ICD reference identifier, and the proposed
   verification method.
2. Validate every interface record for completeness before proceeding. Reject
   any record that is missing a required field and flag it as an input error
   rather than a compliance finding.
3. Categorize each interface into exactly one of the five categories. Reject any
   interface with an unrecognized category — do not silently assign a default.
4. Confirm the proposed verification method is one of: inspection, analysis, or
   test. Reject unrecognized methods with an explicit error.
5. Perform the dimensional fit check for each interface: compute the deviation
   of the actual dimension from the ICD nominal, check that it lies within the
   ±tolerance band, and record the result. Flag any interface outside the band
   as a dimensional non-conformance finding.
6. Check that every interface record carries a non-empty ICD reference string.
   Flag any interface with a missing or blank ICD reference as a traceability
   non-conformance finding.
7. Aggregate the findings per interface: an interface is compliant only when
   both the dimensional fit check passes and a valid ICD reference is present.
   An interface with any finding is non-compliant.
8. Summarize the assessment: report total interface count, compliant count,
   non-compliant count, and the list of findings per interface. The structural
   interface set is fully verified only when the non-compliant count is zero.

## Pitfalls

- Skipping the ICD reference check and treating a clean dimensional result as
  full compliance — an interface with no traceable ICD reference is not verified
  regardless of its measured dimension.
- Applying the same verification method to all interfaces irrespective of
  category — electrical and optical interfaces require functional test to confirm
  their interface loads and alignment; inspection alone is insufficient.
- Treating analysis as a standalone verification method for dimensional fit —
  analysis supports the verification but dimensional compliance must ultimately
  be confirmed by a physical measurement (inspection) or by a dedicated test.
- Counting an interface as compliant when its tolerance band is unset or zero
  because "no violation was found" — an unset tolerance means the ICD requirement
  was never captured, which is itself a traceability finding, not a pass.
- Assigning interfaces to multiple categories to hedge against method
  requirements — each interface belongs to exactly one category, and the
  verification method follows from that single assignment.

## Behavior contract (gate 3)

The interface categorization, verification method selection, dimensional fit
check, ICD reference validation, per-interface compliance determination, and
set-level aggregation logic are exercised by the gate 3 contract test:
scripts/test_interface_verification_test.py against
scripts/interface_verification_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_interface_verification_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
