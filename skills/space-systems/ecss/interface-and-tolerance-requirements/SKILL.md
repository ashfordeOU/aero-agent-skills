---
name: interface-and-tolerance-requirements
description: "Use when define structural interface requirements and check dimensional
  tolerance stack-ups between structural items under ECSS-E-ST-32 clauses 4.3.9 and
  4.4: categorize each interface by type (mechanical-fastened, adhesive-bonded,
  bearing-contact, alignment-critical), assign dimensional and angular tolerances to
  each interface feature, compute tolerance stack-up by worst-case or RSS method,
  compare the resulting alignment envelope against the overall alignment budget, and
  verify every interface has a defined coordinate reference frame and an interface
  control document on record. Trigger: ecss, e-st-32-structures-scope,
  interface-requirements, tolerance-analysis, structural-interface,
  dimensional-tolerance, alignment-budget, tolerance-stack-up."
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
  tags: [ecss, e-st-32-structures-scope, interface-requirements, tolerance-analysis, structural-interface, dimensional-tolerance, alignment-budget, tolerance-stack-up]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Interface and Tolerance Requirements (space-systems/ecss/interface-and-tolerance-requirements)

Use when the task is to define structural interface requirements and verify dimensional
tolerance stack-ups between structural items per ECSS-E-ST-32 clauses 4.3.9 and 4.4 —
categorizing each interface, assigning tolerances, computing the stack-up, and checking
the result against the overall alignment budget.

## Domain quick reference

- Clause 4.3.9 requires every structural interface to be formally defined: the interface
  type (mechanical-fastened, adhesive-bonded, bearing-contact, or alignment-critical),
  the relevant coordinate reference frame, and an Interface Control Document (ICD)
  reference that records the geometric and load-path constraints between the mating
  items. An interface without a coordinate frame or ICD is incomplete regardless of
  whether tolerances have been assigned.
- Clause 4.4 requires dimensional and angular tolerances to be set for each interface
  feature. Two computation methods are permitted: worst-case (WC) — the arithmetic
  sum of all individual tolerances, conservative and used when the number of
  contributors is small or the assembly is non-replaceable — and root-sum-of-squares
  (RSS) — the square root of the sum of squared individual tolerances, used for larger
  contributor chains where statistical confidence is justified. The selected method must
  be stated explicitly; mixing methods without justification is not permitted.
- The alignment budget is the top-level requirement (derived from payload or system
  pointing/clearance needs) that the combined tolerance stack-up must not exceed.
  If the stack-up equals or is below the budget, the interface is alignment-compliant
  for that check; if it exceeds the budget, a redesign or tolerance reallocation is
  required.
- Every interface with a bearing-contact or alignment-critical type must be confirmed
  to carry an ICD; for mechanical-fastened and adhesive-bonded interfaces the ICD
  is still required but a missing reference is flagged as an administrative finding
  rather than a blocking one until the ICD is issued.

## Workflow

1. Inventory all structural interfaces in the assembly tree. For each interface record,
   capture: a unique identifier, the interface type, the coordinate reference frame
   that locates the interface, the ICD reference, and the list of tolerance features
   (each with a tolerance type, value, and unit).
2. Categorize each interface into one of the four recognized types
   (mechanical-fastened, adhesive-bonded, bearing-contact, alignment-critical).
   Reject any interface whose type is not recognized before it enters the analysis.
3. Validate each interface record for completeness: confirm a coordinate reference
   frame is on record, confirm an ICD reference exists, and confirm at least one
   tolerance feature is defined. Record each gap as a finding.
4. For each complete interface record, select the stack-up method (worst-case or RSS)
   consistent with the assembly's classification rationale. Compute the combined
   tolerance from the individual feature tolerances using the selected method.
5. Compare the computed stack-up against the system alignment budget. Flag any
   interface whose stack-up exceeds the budget; record the margin (budget minus
   stack-up) for all interfaces whether compliant or not.
6. Aggregate all findings: interface-definition findings (missing frame, missing ICD,
   unrecognized type), budget-exceedance findings, and ICD-absence findings.
   The interface set is not compliant until all finding lists are empty.

## Pitfalls

- Applying a tolerance value to an interface without first confirming a coordinate
  reference frame — a tolerance is meaningless unless it is anchored to a defined
  datum; the frame must be on record before the tolerance check runs.
- Using RSS without documenting the statistical basis — RSS reduces the combined
  tolerance relative to worst-case and is only valid when the individual contributors
  are independent and their distributions are characterized; applying RSS as a default
  to avoid redesign without justification is a compliance gap.
- Reading zero budget exceedances as compliant when some interface records are
  incomplete — an interface with no tolerances defined cannot be checked and must
  be counted as an open finding, not a pass.
- Counting an ICD reference string present as proof the ICD exists and is current —
  the ICD reference is a pointer; confirming currency and approval status is a separate
  configuration-management check outside this tolerance analysis.

## Behavior contract (gate 3)

The interface-categorization, record-validation, tolerance-stack-up, and
alignment-budget-check logic is exercised by the gate 3 contract test:
scripts/test_interface_and_tolerance_requirements.py against
scripts/interface_and_tolerance_requirements_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_interface_and_tolerance_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
