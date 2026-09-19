---
name: e3301-material-selection-for-mechanisms
description: "Assess a candidate material list for a mechanism against the selection route of ECSS-E-ST-33-01C clause 4.5.2.1, which runs through ECSS-Q-ST-70 clause 5 and takes the allowables guidance of E-ST-32-08. Use when deciding which candidates may go into a moving assembly and what each one still owes: grouping them by selection route, grading vacuum mass loss and condensable volatiles, holding a susceptible stress-corrosion category to a written justification, turning a typical strength into a design allowable and refusing a basis that assumes load redistribution on a single-string fitting, and checking each service rating against the qualification envelope. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-material-selection-route, mechanism-outgassing-limits, mechanism-stress-corrosion-category, mechanism-design-allowable-basis, single-load-path-allowable, mechanism-service-temperature-rating."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-material-selection-for-mechanisms, mechanism-material-selection-route, mechanism-outgassing-limits, mechanism-stress-corrosion-category, mechanism-design-allowable-basis, single-load-path-allowable, mechanism-service-temperature-rating]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Material Selection (space-systems/ecss/e3301-material-selection-for-mechanisms)

Use when the task is the material selection of ECSS-E-ST-33-01C clause
4.5.2.1 -- taking a candidate list for a moving assembly through the
product-assurance route of ECSS-Q-ST-70 clause 5 and the design
allowables guidance of E-ST-32-08, and saying what each candidate still
owes.

## Domain quick reference

- Four questions are asked of every candidate and a material is only
  in once all four are answered: by what route it was selected, how
  clean it is in vacuum, how susceptible it is to stress corrosion, and
  what design allowable its strength data supports.
- The route decides what is owed rather than whether the material is
  good. A material already on the declared list carries its approval
  with it; one qualified by test carries its programme; a new material
  carries neither, and the honest outcome is acceptance with an
  approval still to obtain.
- Outgassing matters twice over in a mechanism. Total mass loss is a
  mass and stability question; the condensable fraction is a
  contamination one, and in a mechanism the condensate lands on the
  very surfaces that have to slide, so the condensable limit is
  tighter than the mass-loss limit by an order of magnitude.
- A susceptible stress-corrosion category is not automatically out; it
  is out unless there is a written justification. An alloy carried in a
  susceptible temper because it has always been carried is the failure
  this rule exists to catch.
- A design allowable is a statistical statement, not a typical value.
  A basis that leans on load redistribution between members is not
  available to a fitting that has nowhere to redistribute into, so a
  single load path admits only the bases that stand on their own, and a
  typical value belongs in a trade study rather than a stress report.
- Service temperature is graded against the qualification envelope,
  not the mission envelope, because the material has to survive the
  levels the hardware is proved at. A rating that lands exactly on
  either end meets it.

## Workflow

1. Take the qualification temperature envelope first; every candidate
   is graded against the same one, and a selection made against the
   mission envelope is short by the whole margin.
2. For each candidate, record its route, its outgassing figures, its
   stress-corrosion category with any justification, its strength data
   and basis, the load path it sits in, and its service rating.
3. Grade the outgassing figures against the limits, treating a value
   exactly on a limit as meeting it, and refuse a recovered mass loss
   larger than the total it is part of.
4. Grade the stress-corrosion category, demanding a justification of
   substance behind a susceptible one rather than a repeated label.
5. Turn the strength into a design allowable through the knockdown for
   its basis, and report a basis that is inadmissible for the load path
   as a finding against the candidate instead of stopping the run.
6. Check the service rating covers both ends of the qualification
   envelope, then close each candidate as accepted, accepted with an
   action, or rejected, and roll the three groups into one verdict.

## Pitfalls

- Reading the condensable limit as the same number as the mass-loss
  limit. They differ by an order of magnitude, and a material inside
  the mass-loss limit can be an order over on condensables while a
  single combined check calls it clean.
- Carrying a susceptible alloy on precedent. Precedent is not a
  justification, and the clause asks for a written argument tied to the
  temper, the stress state and the environment rather than to a
  previous programme.
- Quoting a typical strength as an allowable. Typical is the middle of
  a distribution, so half the material is weaker than the number the
  stress report used, and no knockdown was applied to say so.
- Using a redundancy-dependent basis on a single-string fitting. The
  basis is only meaningful where load can move to a neighbouring
  member; on a lug with nothing beside it the statistics do not apply.
- Grading service temperature against the mission envelope. The
  hardware is proved at the qualification levels, so a material rated
  to the mission hot case has no margin at the temperature it will
  actually see on the shaker or in the chamber.
- Reporting a new material as accepted because its numbers are good.
  The numbers are only three of the four questions; the approval is the
  fourth, and an action still owed is not the same as a clean
  selection.

## Behavior contract (gate 3)

Route grouping, outgassing screening, stress-corrosion grading, the
design-allowable knockdown and its load-path rule, service-temperature
coverage and the three-way candidate outcome are exercised by the gate
3 contract test:
scripts/test_e3301_material_selection_for_mechanisms.py against
scripts/e3301_material_selection_for_mechanisms_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_material_selection_for_mechanisms.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
