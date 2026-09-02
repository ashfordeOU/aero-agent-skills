---
name: dymos-trajectory
description: "Use when setting up and assessing pseudospectral trajectory optimization with Dymos: plan optimal-control problems as phases with collocation nodes, check that phase setup includes initial-state and final bounds plus an objective, and verify convergence, state continuity across segments, and total delta-v against expected budgets for ascent or orbit-transfer trajectories. Flags under-resolved phases (fewer than 5 nodes), unconverged runs, and discontinuities at segment boundaries. Trigger: trajectory optimization, optimal control, dymos, pseudospectral, phase, convergence, collocation, launch ascent, bounds."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: optimal-control
  tags: [trajectory-optimization, optimal-control, dymos, pseudospectral, phase, convergence, collocation, launch-ascent, bounds]
  version: 0.1.0
  author: Aero Agent Skills
---

# Dymos Trajectory Optimization (gnc-autonomy/optimal-control/dymos-trajectory)

Use when the task is pseudospectral trajectory optimization with
Dymos: phase setup, convergence checks, and trajectory validation.

## Domain quick reference

- Dymos transcribes optimal-control problems into phases solved
  with pseudospectral collocation; each phase needs a node count,
  state bounds, and an objective.
- Minimum usable collocation node count in this contract: 5.
- A solved trajectory must converge within the iteration and
  tolerance limits (default max_iter 50, tol_limit 1e-4).
- State values must be continuous across segment boundaries.
- Total delta-v should match the expected budget within a
  tolerance (default 10%).

## Workflow

1. Define the phases: node count, initial- and final-state bounds,
   objective.
2. Check phase setup completeness with scripts/dymos_logic.py
   before solving.
3. Solve and check convergence (iterations, tolerance).
4. Verify state continuity at segment boundaries.
5. Compare total delta-v against the expected budget.

## Pitfalls

- Solving with under-resolved phases (fewer than 5 nodes) and
  trusting the result.
- Missing initial/final bounds or objective in the phase
  definition.
- Accepting a run that hit the iteration cap without tightening
  the mesh or scaling.
- Treating segment-boundary discontinuities as converged.

## Behavior contract (gate 3)

The phase-setup, convergence, continuity, and delta-v logic is
exercised by the gate 3 contract test: scripts/test_dymos.py against
scripts/dymos_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_dymos.py

## Compliance

- ARP4754A is proprietary (SAE); name + paraphrase only per
  standards-map.yaml and brief 06 (revision note: ARP4754B
  supersedes; this skill keys to A, the certification-baseline
  revision).
- compliance: STANDARDS-REF, gated: false.
