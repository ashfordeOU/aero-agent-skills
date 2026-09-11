---
name: e1011-verif-sim
description: "Use when verify human factors engineering requirements for a space system by running crew-in-the-loop simulations under ECSS-E-ST-10-11C §4.11.4: define simulation scope and acceptance criteria, recruit representative and qualified crew participants, execute integrated system simulations, measure task completion, error rate, and workload against thresholds, compare results to acceptance criteria, and produce a simulation-based HFE verification report. Trigger: ecss, e-st-10-system-scope, hfe-verification, crew-in-the-loop, simulation, task-performance, workload-assessment, human-factors."
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
  tags: [ecss, e-st-10-system-scope, hfe-verification, crew-in-the-loop, simulation, task-performance, workload-assessment, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — Verification via System Simulation (space-systems/ecss/e1011-verif-sim)

Use when the task is to verify human factors engineering requirements for a
space system through crew-in-the-loop (CITL) simulations as required by
ECSS-E-ST-10-11C §4.11.4 — defining simulation scope, running representative
crew through integrated system scenarios, measuring human performance against
acceptance thresholds, and confirming each HFE requirement is met or flagging
it as an open finding.

## Domain quick reference

- §4.11.4 mandates simulation as a verification method for HFE requirements
  where direct on-orbit testing is impractical. The simulation must be
  integrated (full or representative system-level fidelity, not a component
  mock-up alone) and crew-in-the-loop (representative operators perform the
  actual tasks, not observers or surrogates).
- Each simulation scenario maps to one or more HFE requirements with explicit,
  pre-agreed acceptance criteria. Criteria cover three performance dimensions:
  task completion rate (proportion of task steps completed successfully),
  error rate (proportion of task steps containing operator errors), and
  workload rating (mean score on an accepted cognitive/physical load scale,
  e.g., a normalised 1–10 scale derived from NASA-TLX or equivalent).
- Participants must be representative of the target user population and must
  meet the qualification criteria specified in the verification plan before
  results from their runs are counted. Results from unqualified participants
  are recorded but excluded from the compliance evaluation.
- A scenario is considered covered only when at least the required number of
  qualified participants have completed it and a result record exists. Scenarios
  without results remain open verification items regardless of other passing
  scenarios.
- The overall simulation verification is complete only when every scenario
  passes its acceptance criteria, every scenario is covered, and no participant
  qualification gaps remain unresolved.

## Workflow

1. Assemble the scenario inventory: list every simulation scenario, assign each
   scenario a unique identifier, record the HFE requirements it addresses, and
   document the acceptance criteria (minimum task completion rate, maximum error
   rate, maximum mean workload rating) for that scenario.
2. Register participants: for each crew member assigned to run scenarios, record
   their identifier, role, and whether they meet the qualification criteria in
   the verification plan. Flag unqualified participants before execution begins.
3. Execute scenarios: run each scenario with the required number of qualified
   participants; capture task completion rate, error rate, and workload ratings
   per run; aggregate per scenario by computing the mean across participants.
4. Evaluate each scenario result against its acceptance criteria:
   - Task completion rate below the scenario minimum → finding.
   - Error rate above the scenario maximum → finding.
   - Mean workload above the scenario maximum → finding.
   - Fewer qualified participants than required → insufficient evidence finding.
5. Identify uncovered scenarios (scenarios with no result record) and list them
   as open verification items.
6. Aggregate all scenario findings and open items; the simulation verification
   is complete only when every scenario passes and no open items remain.

## Pitfalls

- Accepting results from unqualified participants as compliance evidence —
  §4.11.4 requires a representative user population; runs by observers or
  unqualified stand-ins do not count toward the required participant threshold.
- Setting acceptance criteria after seeing the data — thresholds must be
  documented in the verification plan before execution, not tuned to fit
  observed results; post-hoc adjustment invalidates the verification.
- Treating a scenario with partial runs as covered — if fewer qualified
  participants completed the scenario than the plan requires, the scenario
  remains insufficiently evidenced regardless of whether individual runs passed.
- Collapsing workload ratings without verifying scale consistency — if
  participants use different rating scales or interpretations, the mean workload
  figure is meaningless; confirm all participants used the same normalised scale
  before aggregating.
- Reading a scenario's individual passing runs as an overall pass — evaluation
  uses aggregated metrics across all required participants, not the best
  individual run.

## Behavior contract (gate 3)

The scenario-coverage, participant-qualification, performance-metric-evaluation,
and overall-verification logic is exercised by the gate 3 contract test:
scripts/test_e1011_verif_sim.py against scripts/e1011_verif_sim_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1011_verif_sim.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
