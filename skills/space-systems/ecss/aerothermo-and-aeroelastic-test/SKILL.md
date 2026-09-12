---
name: aerothermo-and-aeroelastic-test
description: "Use when plan or verify aerodynamic, aerothermodynamic, and aeroelastic
  structural tests under ECSS-E-ST-32C clauses 4.6.3.23–4.6.3.24: determine the
  applicable test category (aerothermodynamic or aeroelastic), define heat-flux and
  temperature acceptance limits for aerothermodynamic specimens, compute flutter speed
  and aeroelastic stability margins against design flight envelope limits, confirm
  damping-ratio compliance, and verify combined thermal-structural load margins are
  met. Trigger: ecss, e-st-32-structures-scope, aerothermodynamic-test,
  aeroelastic-test, flutter-margin, heat-flux, thermal-structural, wind-tunnel."
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
  tags: [ecss, e-st-32-structures-scope, aerothermodynamic-test, aeroelastic-test, flutter-margin, heat-flux, thermal-structural, wind-tunnel]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Aerothermodynamic and Aeroelastic Tests (space-systems/ecss/aerothermo-and-aeroelastic-test)

Use when the task requires planning or verifying aerodynamic, aerothermodynamic,
and aeroelastic structural tests per ECSS-E-ST-32C clauses 4.6.3.23–4.6.3.24.
These two test types share the atmospheric-flight environment but address different
failure modes: aerothermodynamic tests confirm structural integrity under combined
aero-heating and pressure loads, while aeroelastic tests confirm freedom from
flutter, divergence, and control reversal within the certified flight envelope.

## Domain quick reference

- **Aerothermodynamic tests (clause 4.6.3.23)**: Applied to structural elements
  and assemblies exposed to significant aerodynamic heating during ascent or
  atmospheric re-entry. The test reproduces the combined heat-flux profile and
  simultaneous mechanical load, verifying that the structure meets both the thermal
  allowable (peak temperature ≤ material limit) and the structural margin (applied
  load ≤ allowable strength under elevated temperature). Heat-flux acceptance is
  expressed as a margin factor: (allowable flux / applied flux) − 1. A margin of
  zero or negative is a finding. Tests are categorized as either aerothermodynamic
  (heat-flux + load combined) or thermal-only (heat-flux without simultaneous
  structural load); the combined category is the more demanding case.

- **Aeroelastic tests (clause 4.6.3.24)**: Address the coupling between structural
  deformation and aerodynamic forces. The primary deliverable is a demonstrated
  flutter-free envelope: the flutter onset speed must exceed the design limit speed
  by at least the required margin factor (typically 1.15 of the limit speed at the
  design altitude and Mach). Damping ratio at each tracked mode must remain above
  the structural damping floor across the flight envelope. Dynamic-pressure margin
  (critical dynamic pressure / design dynamic pressure) must meet the program's
  stability requirement. Tests are categorized as flutter-clearance, divergence-
  check, or control-reversal, each with its own acceptance criterion.

- **Categorization before testing**: Each candidate test is categorized into one
  of these two families before test planning begins. An uncategorized test item
  must be resolved before it enters the matrix; mixing aerothermodynamic and
  aeroelastic acceptance criteria on the same test run without explicit joint-
  coverage justification is a procedural finding.

## Workflow

1. **Identify and categorize each test item**: For every structural element or
   assembly in the test scope, assign a primary test category — aerothermodynamic
   or aeroelastic. An item requiring both is entered twice (once in each category).
   Reject uncategorized items before proceeding.

2. **Aerothermodynamic test planning**: For each aerothermodynamic test item,
   define the applied heat-flux profile (peak flux, duration, spatial distribution),
   the simultaneous mechanical load case (limit or ultimate, per the test objective),
   and the material temperature limit. Record the heat-flux margin factor and the
   combined thermal-structural utilization. A margin factor ≤ 0 or a combined
   utilization > 1.0 is a disqualifying finding before test execution.

3. **Aeroelastic test planning**: For each aeroelastic test item, document the
   design limit speed, the required flutter-speed margin factor, the minimum
   damping ratio floor, and the critical dynamic pressure. Compute the flutter-
   speed margin and the dynamic-pressure stability factor. Flag any mode with
   damping below the floor or a flutter-speed margin below the required factor.

4. **Execute test and record measurements**: Conduct each test in the defined
   environment. For aerothermodynamic tests record peak temperature and structure
   response. For aeroelastic tests record measured flutter onset speed (or
   subcritical extrapolated value) and damping ratios at each tracked frequency.

5. **Post-test acceptance check**: Compare measured values against limits. For
   aerothermodynamic tests: peak temperature ≤ allowable, no structural failure.
   For aeroelastic tests: flutter onset speed ≥ design limit speed × margin factor,
   all damping ratios ≥ floor, dynamic-pressure stability factor ≥ required value.
   Document each finding with the clause reference and measured vs. required value.

6. **Aggregate and close**: Produce a per-item acceptance record. An item is
   accepted only when both temperature/flux and stability criteria are clear of
   findings. Open findings must be dispositioned before test closure.

## Pitfalls

- **Conflating aerothermodynamic and thermal-only tests**: A thermal-only test
  (heat-flux soak without simultaneous structural load) does not satisfy the
  combined aerothermodynamic requirement of clause 4.6.3.23. Verify that the
  mechanical load application is concurrent with the peak heat-flux phase.

- **Applying sea-level flutter margins at altitude**: The flutter onset speed is
  a function of dynamic pressure, which varies with altitude and Mach. A margin
  demonstrated at sea level does not transfer to all altitudes; verify the margin
  at the critical altitude-Mach combination.

- **Reading zero damping as marginal rather than unstable**: A zero or negative
  measured damping ratio indicates onset or post-onset aeroelastic instability —
  it is a failure, not a finding to disposition. The aeroelastic test must be
  halted and the structural model updated before re-test.

- **Skipping categorization for mixed-environment items**: An item exposed to both
  aerodynamic heating and significant aeroelastic coupling (e.g. a control surface
  at high angle of attack during ascent) must satisfy both sets of acceptance
  criteria independently. Satisfying only one does not constitute test closure.

## Behavior contract (gate 3)

The categorization, heat-flux margin, temperature-limit, flutter-speed margin,
damping-ratio, dynamic-pressure stability, and combined thermal-structural logic
is exercised by the gate 3 contract test: scripts/test_aerothermo_and_aeroelastic_test.py
against scripts/aerothermo_and_aeroelastic_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_aerothermo_and_aeroelastic_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Anchor clauses: ECSS-E-ST-32C §4.6.3.23 (aerodynamic/aerothermodynamic tests),
  §4.6.3.24 (aeroelastic tests).
