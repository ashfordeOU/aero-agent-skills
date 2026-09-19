---
name: q7053-applicability-and-processes
description: "Determine which sterilization processes a flight item may be exposed to and what compatibility evidence each one owes, before any test is written. Use when a bill of materials carrying declared temperature, dose, oxidiser and moisture capabilities meets a register of candidate processes - dry heat, ionising radiation, ethylene oxide, vapour-phase hydrogen peroxide - and the campaign scope has to be fixed. Compares every material against each process stressor, marks a pairing admissible by analysis, test-required or excluded, holds an undeclared capability to test-required rather than to zero, aggregates to the item, and reports when no process survives. Trigger: ecss, q-st-70-53, sterilization-compatibility-scope, dry-heat-sterilization, ionising-radiation-sterilization, ethylene-oxide-exposure, vapour-phase-hydrogen-peroxide, material-stressor-margin."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-applicability-and-processes, dry-heat-sterilization, ionising-radiation-sterilization, ethylene-oxide-exposure, vapour-phase-hydrogen-peroxide, material-stressor-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Applicability and Process Scope (space-systems/ecss/q7053-applicability-and-processes)

Use when the task is the framework step of a sterilization compatibility
campaign: fixing which processes are in scope for an item, which
material and process pairings can be settled on declared capability
alone, and which ones the campaign has to buy evidence for.

## Domain quick reference

- A sterilization process is not one stressor. Dry heat applies
  temperature and time; ionising radiation applies cumulative dose;
  ethylene oxide and vapour-phase hydrogen peroxide apply a chemical
  agent at a humidity and a concentration, and add a vacuum or pressure
  excursion. A material is compatible with a process only when it
  survives every axis that process applies, so the scoping question is
  per axis and not per process name.
- The axes are compared against declared material capability, and the
  interesting cases are the ones with a small margin. A pairing with
  ample margin on every axis is settled by analysis and buys nothing
  from a test; a pairing with a thin margin on any axis is exactly what
  the campaign exists to measure.
- An undeclared capability is not an infinite one and it is not zero.
  A material with no radiation datum against a radiation process is a
  test-required pairing, and recording it as a pass because no limit
  was breached is how an unqualified material reaches flight.
- Chemical sensitivity is categorical, not a margin. A polymer that the
  process agent attacks is excluded from that process whatever its
  temperature headroom, and no amount of margin elsewhere rehabilitates
  it.
- The item inherits the worst of its materials. A process is admissible
  for the item only when no material excludes it, so a single
  incompatible seal removes a process from the whole scope, and an item
  with no admissible process is a design finding rather than a test
  plan.

## Workflow

1. Validate the process register: each process carries a name and a
   mapping of stressor axis to applied level, plus the agents it
   exposes the hardware to. A negative applied level or an empty
   register is an input error.
2. Validate the bill of materials: each material carries a name, its
   declared capability per axis, and the agents it is known to be
   attacked by.
3. For every material and process pairing, walk the process axes. An
   axis the material declares a sensitivity agent for, or an applied
   level above the declared capability, excludes the pairing.
4. An axis with no declared capability makes the pairing test-required
   and records which axis is undeclared; it never passes by silence.
5. Compute the margin on each declared axis as the unused fraction of
   capability, and keep the driving axis, the one with the least
   margin.
6. Categorize the pairing: excluded, test-required when the least
   margin sits below the analysis threshold or an axis is undeclared,
   admissible by analysis otherwise.
7. Aggregate: a process is admissible for the item when no material
   excludes it; collect the test-required pairings into the campaign
   matrix, and raise a finding when the admissible set is empty.

## Pitfalls

- Scoping by process name instead of by stressor axis. Two facilities
  running the same named process at different dwell temperatures apply
  different stressors, and a scope that records only the name cannot
  tell which of them the item was screened against.
- Reading an undeclared capability as unlimited. Silence in a data
  sheet is missing data, and converting it into a pass is the single
  failure this step exists to prevent.
- Letting a generous margin on one axis offset a breach on another.
  The axes are not exchangeable; a seal with enormous thermal headroom
  still swells in the process agent.
- Declaring the campaign scope from the admissible-by-analysis set
  alone. The test matrix is the test-required set, and an item whose
  every pairing is settled by analysis should say so explicitly rather
  than leave an empty matrix to be read as an oversight.
- Keeping a process in scope because the programme prefers it. When
  every candidate is excluded the answer is a design or material
  change, not a relaxed threshold.

## Behavior contract (gate 3)

The process and material validation, per-axis margin computation,
undeclared-axis handling, sensitivity exclusion, pairing categorization
and item-level aggregation are exercised by the gate 3 contract test:
scripts/test_q7053_applicability_and_processes.py against
scripts/q7053_applicability_and_processes_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7053_applicability_and_processes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
