---
name: e20-battery-clause-applicability
description: "Use when determine whether the ECSS-E-ST-20C clause 5.6.1 battery provisions reach a given on-board energy store: categorize every item as a secondary rechargeable electrochemical battery, a primary non-rechargeable electrochemical battery, an electrochemical converter that holds no internal reactants, or a non-electrochemical store; resolve the declared cell assembly into nominal voltage, ampere-hour capacity and stored energy; select the provision groups that follow from the category; and reconcile the derived reach against the scope the electrical architecture declared. Trigger: ecss, e-st-20-electrical-scope, e20-battery-clause-applicability, battery-provision-applicability, electrochemical-energy-store, secondary-battery-chemistry, primary-battery-chemistry, cell-assembly-topology, battery-scope-boundary."
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
  tags: [ecss, e-st-20-electrical-scope, e20-battery-clause-applicability, battery-provision-applicability, electrochemical-energy-store, secondary-battery-chemistry, primary-battery-chemistry, cell-assembly-topology]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Battery Clause Applicability (space-systems/ecss/e20-battery-clause-applicability)

Use when the task is deciding which entries of a spacecraft energy-storage
inventory are batteries in the sense of ECSS-E-ST-20C clause 5.6.1 -- an
electrochemical source that holds its own reactants and delivers electrical
energy through an assembly of cells -- and which provision groups therefore
reach each entry.

## Domain quick reference

- Clause 5.6.1 fixes two things at once: what counts as a battery, and how
  far the battery provisions extend. The definition is electrochemical and
  self-contained: reactants stored inside the cell, energy released by a
  reversible or irreversible chemical reaction at the electrodes. A store
  that converts rather than holds (a fuel cell fed from external tanks) and
  a store that is not electrochemical at all (capacitor bank, flywheel,
  array, radioisotope source) sit outside the clause even though both
  deliver electrical energy.
- The categories that matter downstream are four. A secondary battery is
  rechargeable, so charge management, cycling and energy-balance sizing all
  reach it. A primary battery is single-discharge, so charge management does
  not reach it while cell rating limits, safety management, storage and
  handling, and telemetry still do. An electrochemical converter and a
  non-electrochemical store take neither set and are governed elsewhere.
- A battery is an assembly, never a bare cell: the series count sets the
  nominal terminal voltage from the per-cell nominal voltage of the
  chemistry, the parallel count sets the ampere-hour capacity from the cell
  capacity, and the product of the two gives the stored energy that the
  power budget and the energy-balance case both consume. An in-scope item
  whose assembly is not declared cannot be sized or rated and is therefore
  an open item, not a pass.
- The reach decision is auditable in both directions. The architecture
  declares which items it treats as batteries; the categorization derives
  the same answer from chemistry. A disagreement is a finding: either a
  rechargeable store escaped the battery provisions, or a non-battery store
  is carrying requirements it cannot satisfy.

## Workflow

1. Take the energy-storage inventory and require a unique identifier and a
   named chemistry on every entry. Reject a duplicate identifier and reject
   a chemistry that is not on the recognized list before any reach decision
   is made -- an unrecognized chemistry is an input defect, not a category.
2. Categorize each entry from its chemistry into exactly one of secondary
   battery, primary battery, electrochemical converter, or non-electrochemical
   store. Only the first two are in the reach of clause 5.6.1.
3. For each in-scope entry, resolve the declared assembly: series count,
   parallel count and per-cell capacity together give nominal voltage,
   ampere-hour capacity and stored energy. Treat a partially declared
   assembly as an input defect and a wholly undeclared one as an open item
   recorded against the entry.
4. Select the provision groups that follow from the category: charge
   management, cell rating limits, energy-balance sizing, safety management,
   storage and handling, and telemetry for a secondary battery; the same set
   less charge management and energy-balance cycling for a primary battery;
   none for the two out-of-scope categories.
5. Reconcile the derived reach against the declared reach on each entry and
   record a finding wherever the two disagree. Record a further finding for
   a secondary battery with no charge control identified, since the group
   that most distinguishes it has no owner.
6. Aggregate per inventory: the applicability assessment is settled only
   when every entry has a category, every in-scope entry has an assembly,
   and the finding list is empty.

## Pitfalls

- Reading "delivers electrical energy from a chemical reaction" as enough
  and pulling a fuel cell into the battery provisions -- the clause scopes a
  store with internal reactants, and a converter fed from external tanks is
  sized, rated and operated by a different set of requirements entirely.
- Applying the rechargeable provisions to a primary battery because both are
  electrochemical -- charge current limits, charge temperature windows and
  cycle-life energy balance have no meaning on a single-discharge store, and
  imposing them produces requirements that can never be verified.
- Categorizing a battery and stopping there, leaving the series and parallel
  counts undeclared -- without the assembly there is no nominal voltage and
  no capacity, so every later clause that consumes those numbers inherits an
  undeclared input.
- Trusting the architecture's own scope flag instead of deriving the
  category -- the flag is the item under audit, so accepting it as the answer
  makes the check circular and lets a mis-scoped store pass unexamined.

## Behavior contract (gate 3)

The categorization, assembly-resolution, provision-selection and declared-
versus-derived reconciliation logic is exercised by the gate 3 contract test:
scripts/test_e20_battery_clause_applicability.py against
scripts/e20_battery_clause_applicability_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e20_battery_clause_applicability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
