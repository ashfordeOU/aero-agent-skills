---
name: static-test
description: "Use when assess static structural test compliance for a spacecraft or launch vehicle structural assembly under ECSS-E-ST-32C clause 4.6.3.7: determine the required test load from the design limit load and the applicable load factor (qualification ultimate, qualification yield, or acceptance proof), generate the incremental load-application sequence with hold steps, compute margin of safety for each critical load case, and evaluate the success criteria covering no fracture at the test load level, residual deformation within the post-test allowable, and structural stiffness within the model-correlation tolerance band. Trigger: ecss, e-st-32-structures-scope, static-test, structural-test, load-factor, margin-of-safety, qualification, acceptance, load-application."
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
  tags: [ecss, e-st-32-structures-scope, static-test, structural-test, load-factor, margin-of-safety, qualification, acceptance, load-application]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Static Structural Test (space-systems/ecss/static-test)

Use when the task is planning or evaluating a static structural test
under ECSS-E-ST-32C clause 4.6.3.7 -- computing the required test
load from the design limit load and an applicable factor, building
the incremental load-application sequence, computing margin of safety
for each load case, and checking all three success criteria: no
fracture at the test load, residual deformation within the post-test
allowable, and measured stiffness within the model-correlation band.

## Domain quick reference

- ECSS-E-ST-32C clause 4.6.3.7 governs static structural tests
  whose purpose is to demonstrate that a structural assembly can
  sustain specified load levels without failure, permanent
  deformation beyond tolerance, or a stiffness departure that would
  invalidate the structural model. Two test types apply: a
  qualification test (demonstrating structural integrity to
  qualification-ultimate or qualification-yield levels, which exceed
  the design limit load) and an acceptance test (proofing the
  flight-deliverable hardware to a lower proof-load level to screen
  for workmanship deficiencies without consuming fatigue life
  excessively).
- Test load levels are computed by multiplying the design limit load
  by a load factor that depends on the test type and the check
  level. Qualification-ultimate factor: 1.5 (applied over the design
  limit load). Qualification-yield factor: 1.1. Acceptance proof
  factor: 1.1. These factors reflect the common-knowledge margins
  codified in ECSS-E-ST-32C Table 4-2; the precise contractual
  values are always taken from the project-specific tailoring
  document.
- Load application proceeds in incremental steps from zero to the
  target test load. Typically a minimum of three steps is required
  so that the structure's response (strain gauge readings, deflection
  measurements) can be compared with the analysis model prediction at
  each sub-level. A hold period is maintained at every step for
  measurement and visual inspection. The sequence does not include a
  0 N baseline step -- the pre-load baseline state is recorded
  before the sequence begins.
- Three success criteria must all be satisfied: (1) no structural
  fracture or collapse at the target test load, assessed by margin
  of safety (allowable / applied − 1 ≥ 0) for every load case;
  (2) residual deformation after load removal not exceeding the
  specified post-test allowable (confirming that no unacceptable
  permanent set occurred); and (3) measured structural stiffness
  within a tolerance band (default ±10 %) of the model-predicted
  stiffness, providing model-correlation evidence.
- Load cases are drawn from the structural load-cases matrix and
  cover the primary loading modes relevant to the assembly: tension,
  compression, shear, bending, torsion, combined, pressure, and
  thermal-mechanical. Each load case is handled independently in the
  margin-of-safety and residual-deformation checks.

## Workflow

1. Identify the test type (qualification or acceptance) from the
   verification plan and confirm the governing load factor from the
   project tailoring document. Reject an unrecognized test type
   before it enters the test-load calculation.
2. Compute the target test load: design limit load × the applicable
   factor (qualification-ultimate 1.5, qualification-yield 1.1, or
   acceptance proof 1.1). A negative or zero design limit load is
   rejected before computation.
3. Retrieve the load cases from the structural load-cases matrix.
   Validate each load case type against the recognized set (tension,
   compression, shear, bending, torsion, combined, pressure,
   thermal-mechanical). Reject unrecognized types with an explicit
   error rather than silently skipping them.
4. Generate the load-application sequence: divide the target test
   load into a minimum of three evenly-spaced steps. Record the
   planned load at each step so the test conductor can compare
   measured versus commanded load in real time.
5. For each load case, compute the margin of safety (allowable /
   applied − 1). Flag any load case where the margin is negative
   as a structural violation. A zero margin is acceptable (exactly
   at the allowable).
6. If post-test residual deformation data are available, compare the
   measured deformation against the specified allowable. Flag an
   exceedance as a deformation violation even if the margin of
   safety at the test load was non-negative.
7. If structural stiffness measurements are available, compute the
   percentage deviation from the model-predicted stiffness. Flag a
   deviation outside the tolerance band (default ±10 %) as a
   model-correlation finding requiring an analysis update or a
   re-test.
8. Aggregate all violations across all load cases. The static test
   is compliant only when the violation list is empty.

## Pitfalls

- Applying the load factor to the test load rather than the design
  limit load -- the factor is always a multiplier on the design
  limit load, not on a previous test load or analysis load.
- Treating a zero margin of safety (allowable exactly equals
  applied) as a violation -- a zero margin is the boundary
  condition of compliance, not a failure. Negatives are failures.
- Skipping the residual-deformation check on the grounds that the
  structure did not fracture -- permanent set beyond the allowable
  is itself a test failure, independent of whether the structure
  survived the test load.
- Using fewer than three load steps -- an insufficient step count
  prevents meaningful comparison of the measured response against
  the model prediction at intermediate load levels, which defeats
  the model-validation purpose of the test.
- Omitting the stiffness-correlation check when stiffness data are
  available -- a stiffness deviation that falls outside the
  tolerance band indicates that the structural model used for margin
  calculations may be unconservative, and the finding must be
  resolved before the analysis results can be considered verified.

## Behavior contract (gate 3)

The load-case categorization, test-load computation, margin-of-
safety calculation, load-step generation, residual-deformation check,
stiffness-correlation check, and full assessment logic are exercised
by the gate 3 contract test: scripts/test_static_test.py against
scripts/static_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_static_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
