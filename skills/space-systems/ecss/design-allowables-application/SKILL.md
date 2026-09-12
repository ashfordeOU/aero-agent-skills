---
name: design-allowables-application
description: "Use when determine the correct design allowable basis (A-basis or B-basis) and verify structural margins for spacecraft structural members under ECSS-E-ST-32C clause 4.5.8: assign A-basis to single load-path members and B-basis to redundant (multiple load-path) members, retrieve the allowable stress value from the applicable material database (MMPDS for metals, CMH-17 for composites, supplier data for non-metals and adhesives), compute the margin of safety as (allowable / applied_stress) − 1, and flag any negative margin or basis mismatch before the analysis package is accepted. Trigger: ecss, e-st-32-structures-scope, design-allowables, a-basis, b-basis, mmpds, cmh-17, margin-of-safety, metals, composites, adhesives."
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
  tags: [ecss, e-st-32-structures-scope, design-allowables, a-basis, b-basis, mmpds, cmh-17, margin-of-safety, metals, composites]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Design Allowables Application (space-systems/ecss/design-allowables-application)

Use when the task is selecting the correct A-basis or B-basis design allowable
for a structural member under ECSS-E-ST-32C clause 4.5.8, identifying the
applicable material database, computing the margin of safety, and confirming
no member has a negative margin before the structural analysis package is
accepted.

## Domain quick reference

- **A-basis vs B-basis**: A-basis is the lower one-sided tolerance bound
  exceeded by 99 % of the material population at 95 % statistical confidence.
  B-basis is the corresponding bound for 90 % of the population at 95 %
  confidence. A-basis is required wherever a single member's failure causes
  overall structural failure (single load path). B-basis is permitted when the
  structure is redundant (multiple load paths) so that failure of one element
  does not cause overall failure.
- **Material source by class**: metals use MMPDS (Metallic Materials Properties
  Development and Standardization); composites use CMH-17 (Composite Materials
  Handbook); non-metals and adhesives use supplier data sheets that must be
  substantiated by test.
- **Margin of safety**: MoS = (allowable / applied_stress) − 1. A non-negative
  MoS is required. A negative MoS is a structural finding that must be resolved
  by redesign, load reduction, or a revised allowable with supporting test data.
- **Failure-mode and environment match**: the allowable must correspond to the
  governing failure mode (tension, compression, shear, bearing) and to the
  design temperature, moisture, and radiation environment; using a room-
  temperature allowable in a cryogenic service condition is a systematic error.

## Workflow

1. **Categorize each structural member by load-path type.** Label the member
   "single" (loss of this one element causes overall structural failure) or
   "multiple" (redundant structure; failure of this element alone does not cause
   overall failure). The load-path label determines the required basis.
2. **Assign the required basis.** Single load path → A-basis required. Multiple
   load path (redundant) → B-basis permitted. Record the required basis for
   every member before retrieving any allowable value.
3. **Identify the material class and source document.** Metal members: retrieve
   allowable from MMPDS for the applicable alloy, temper, product form, and
   failure mode. Composite members: retrieve from CMH-17 for the applicable
   laminate and environment. Non-metal and adhesive members: use the supplier
   data sheet value substantiated by lot-acceptance testing.
4. **Confirm the retrieved value matches the required basis.** Check that the
   MMPDS or CMH-17 entry is labeled with the correct basis column (A or B).
   A B-basis value on a single load-path member is a non-conformance; flag it
   and do not proceed to margin calculation until corrected.
5. **Compute the margin of safety.** MoS = (allowable / applied_stress) − 1,
   where applied_stress is derived from the design limit load (or design
   ultimate load where appropriate) divided by the governing section property.
   Verify that all load factors have been applied before this step so the factor
   of safety is not double-counted.
6. **Flag findings and aggregate.** Any member with MoS < 0 is a finding.
   Any member where the retrieved allowable basis does not match the required
   basis is also a finding. All findings must be resolved before the analysis
   package can be accepted as structurally compliant.

## Pitfalls

- **Using B-basis on a single load-path member.** If the member fails the
  structure fails; only A-basis is acceptable. Applying the less-conservative
  B-basis is a systematic non-conservatism that invalidates the analysis.
- **Ignoring the environment condition on the allowable.** MMPDS and CMH-17
  allowables are tabulated per temperature; using a room-temperature value in
  an elevated-temperature or cryogenic service condition gives a non-conservative
  result without an explicit knock-down factor.
- **Double-counting the factor of safety.** If the applied stress already
  reflects the design ultimate load (limit × 1.5 for most metallic structures),
  divide the ultimate allowable by that same factor. Using limit load with the
  ultimate allowable, or ultimate load with the limit allowable, produces either
  an overly conservative or a non-conservative margin.
- **Omitting a basis check on the source entry.** Both MMPDS and CMH-17 publish
  separate A- and B-basis columns for the same material and failure mode; pulling
  the wrong column while noting the correct basis label is an error that will not
  be caught by numerical range checks alone.
- **Treating a missing allowable as a pass.** If no allowable value exists in
  the approved database for the material, product form, or failure mode, the
  absence is a finding (allowable not established), not a pass with zero margin.

## Behavior contract (gate 3)

The basis-selection, source-lookup, margin-of-safety computation, and
batch-assessment logic is exercised by the gate 3 contract test:
scripts/test_design_allowables_application.py against
scripts/design_allowables_application_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_design_allowables_application.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
