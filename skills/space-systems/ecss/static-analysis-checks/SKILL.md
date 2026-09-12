---
name: static-analysis-checks
description: "Use when you need to verify static-analysis output from a CalculiX
  linear finite-element model against ECSS-E-ST-32C section 5.5 criteria. Check
  that reaction forces balance applied loads within tolerance, confirm that external
  work equals strain energy within tolerance, and validate solver residual convergence.
  Each criterion is evaluated independently and returns PASS or FAIL with a quantified
  margin. Apply after every linear static run before results are accepted for structural
  sizing or qualification. Trigger: ecss, e-st-32-structures-scope, static-analysis,
  reaction-equilibrium, energy-balance, convergence-check, fem, calculix-linear."
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
  tags: [ecss, e-st-32-structures-scope, static-analysis, reaction-equilibrium, energy-balance, convergence-check, fem, calculix-linear]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Structures — Static Analysis Checks (space-systems/ecss/static-analysis-checks)

Use when the task is to verify the output of a CalculiX linear static
finite-element run against the three acceptance criteria defined in
ECSS-E-ST-32C section 5.5: reaction equilibrium, energy balance, and
solver convergence. All three criteria must pass before static results
are used for structural sizing, margin-of-safety calculation, or
qualification reporting.

## Domain quick reference

- Section 5.5 mandates three independent acceptance criteria for every
  linear static FEM solution:
  1. **Reaction equilibrium**: the vector sum of all applied external
     loads and all support reaction forces must be near zero in every
     degree of freedom. A non-zero residual indicates that the model
     does not correctly transmit load to its supports — typically caused
     by missing constraints, duplicate nodes, or disconnected mesh
     regions.
  2. **Energy balance**: the external work done by applied loads (one
     half of force dot displacement, summed over all loaded nodes) must
     equal the internal strain energy stored across all elements within
     a prescribed relative tolerance. A discrepancy indicates numerical
     error, element formulation issues, or an incorrectly assembled
     stiffness matrix.
  3. **Solver convergence**: the dimensionless residual norm
     ||K u − F|| / ||F|| must fall below a prescribed threshold. For a
     direct solver this is effectively machine precision; for iterative
     solvers the threshold is set in the solver control parameters. A
     result above threshold means the linear system was not solved to
     adequate accuracy and displacements cannot be trusted.
- Default tolerances (ECSS-E-ST-32C §5.5 guidance, paraphrased): 1 %
  of the maximum force component for reaction equilibrium; 1 % relative
  for energy balance; 1 × 10⁻⁶ dimensionless for solver convergence.
  Project-specific requirements may tighten these values.
- Each criterion is evaluated independently. A failure in any one
  criterion invalidates the run regardless of the other two.

## Workflow

1. Extract from the solver output file the applied force vector
   (one component per loaded node and degree of freedom) and the
   reaction force vector at every constrained degree of freedom.
2. Compute the per-component residual: F_applied[i] + F_reaction[i].
   Determine the scale as the maximum absolute value across all
   applied and reaction components; compute the maximum relative
   residual as max(|residual[i]|) / scale. Compare to the reaction
   tolerance threshold. Record PASS or FAIL with the quantified margin.
3. Extract the external work W and the total strain energy U from the
   solver summary. Compute the relative energy error:
   |W − U| / |U|. Compare to the energy balance tolerance. Record
   PASS or FAIL with the quantified margin.
4. Extract the solver residual norm R from the solver log or summary
   output. Compare R to the convergence threshold. Record PASS or FAIL.
5. Aggregate the three results. The run is accepted only when all three
   criteria return PASS. Report each criterion result and its margin to
   the structural analysis record.
6. If any criterion fails, identify the failure mode (equilibrium gap,
   energy discrepancy, or convergence shortfall) and trace it to a
   likely cause before re-running: recheck boundary conditions and
   constraint completeness for equilibrium failures; check element
   formulations and mesh connectivity for energy failures; tighten
   solver iteration limits or adjust preconditioning for convergence
   failures.

## Pitfalls

- Checking only the global resultant (scalar sum of all force
  components) instead of the per-component residual — a balanced
  global sum can hide large opposing errors in individual axes.
- Skipping the energy balance check because the reaction check passed
  — the two criteria detect different classes of error; element
  formulation defects may not show up in global equilibrium.
- Treating a missing convergence residual in the solver log as a pass
  — absent output means the run terminated abnormally or the metric
  was not requested; the criterion must be explicitly confirmed.
- Applying the project reaction tolerance (which may be several
  percent) to the energy balance check — each criterion carries its
  own tolerance derived from its physical basis; mixing them produces
  incorrect margin assessments.

## Behavior contract (gate 3)

The reaction-equilibrium, energy-balance, and solver-convergence logic
is exercised by the gate 3 contract test:
scripts/test_static_analysis_checks.py against
scripts/static_analysis_checks_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_static_analysis_checks.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
