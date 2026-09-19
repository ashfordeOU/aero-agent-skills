---
name: e3301-operational-constraints-thermo-mechanical-interfaces
description: "Evaluate the operational constraints and the mounting interface of a mechanism against ECSS-E-ST-33-01C clauses 4.5.3 and 4.6. Use when the task is showing that a mechanism stays inside the contamination, magnetic-cleanliness and grounding-continuity allowances its context imposes while its interface survives expansion mismatch: accumulating deposition from every declared source over life through the geometric view factor, summing static and moving-part dipole moments into the field seen at the declared separation, walking each bonding path and separating the ones that cross a rotating or sliding joint, and converting interface mismatch into displacement and induced load against their budgets. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-operational-constraints, mechanism-contamination-budget, mechanism-magnetic-dipole-allowance, mechanism-grounding-continuity, mechanism-thermo-mechanical-interface, interface-expansion-mismatch."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-operational-constraints-thermo-mechanical-interfaces, mechanism-operational-constraints, mechanism-contamination-budget, mechanism-magnetic-dipole-allowance, mechanism-grounding-continuity, mechanism-thermo-mechanical-interface, interface-expansion-mismatch]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Operational Constraints and Thermo-Mechanical Interfaces (space-systems/ecss/e3301-operational-constraints-thermo-mechanical-interfaces)

Use when the task is the clause 4.5.3 and 4.6 pair of ECSS-E-ST-33-01C
— honouring the constraints the rest of the spacecraft imposes on a
mechanism while it operates, and meeting the thermo-mechanical
requirements of the interface it is bolted through.

## Domain quick reference

- Operational constraints are not mechanism-internal requirements. They
  come from neighbours: an optical bench that cannot tolerate a
  molecular film, a magnetometer that cannot tolerate a dipole, an
  electrical architecture that needs a defined return path. The
  mechanism meets them while it is moving, which is the hard part.
- Contamination is accumulated, not instantaneous. A creeping lubricant
  and an outgassing harness both deposit for as long as the mission
  lasts, so the budget is a rate times a life times a view factor. A
  baffled source credited at its own view factor is the honest way to
  take geometry into account; crediting the whole assembly at the
  baffled value is not.
- A magnetic budget bites twice. The static residual dipole is the
  figure usually quoted, but a moving part carries its own moment and
  reorients it during travel, so the bounding case adds the magnitudes
  rather than a fixed vector sum. The field then falls as the inverse
  cube of separation, so a small increase in standoff buys a lot.
- Grounding across a mechanism is a wear question. A bearing race, a
  sliding contact or a harness loop can measure well on the bench and
  degrade over the cycle count; a path crossing a moving interface
  needs a dedicated bonding element whose job is only continuity.
- The mounting interface couples two answers. Expansion mismatch across
  a bolted joint produces a displacement when the joint is free and a
  load when it is restrained, and the same interface conducts heat. A
  stiffening change made to hold alignment moves the induced load and
  the conducted flux at the same time.

## Workflow

1. Validate every declared allowance and geometry; a zero life, a
   negative emission rate or a view factor above unity is an input
   error, not a conservative case.
2. Accumulate contamination: rate times life times view factor per
   source, per-source view factor overriding the assembly value, then
   compare the total with the deposition allowance.
3. Sum the static residual dipole with each moving-part moment as
   magnitudes, convert to the on-axis field at the declared separation,
   and compare with the magnetic-cleanliness allowance.
4. Walk each grounding path against the bonding resistance limit, and
   raise a separate finding for any path that crosses a rotating or
   sliding joint without a dedicated bonding element.
5. Compute the interface expansion mismatch over the declared
   temperature excursion, take its magnitude against the allowed
   displacement, drive it through the interface stiffness for the
   induced load, and grade the conducted heat when a conductance is
   declared.
6. Absorb floating-point representation error at every budget boundary
   with a named tolerance rather than by relaxing the allowance, and
   report all findings together so a fix can be traded across areas.

## Pitfalls

- Reporting an instantaneous contamination rate against an accumulated
  allowance. The allowance covers the mission; a rate that looks small
  per year can consume it several times over a fifteen-year life.
- Quoting only the static residual dipole. The moving part reorients,
  so a mechanism that passes a static magnetic check can still break
  the allowance in the middle of its travel.
- Taking a bench bonding measurement across a bearing as the grounding
  answer. That measurement is of a surface that wears; continuity has
  to be carried by an element designed for it.
- Grading interface displacement and induced load as alternatives. A
  free joint gives displacement, a restrained joint gives load, and a
  real joint gives some of both — both budgets are graded.
- Widening an allowance to make an exact-equality case pass. Equality
  at a budget boundary is a representation question, handled by the
  tolerance inside the comparison; the allowance stays as specified.

## Behavior contract (gate 3)

The contamination accumulation, dipole summation and field conversion,
grounding path walk, expansion mismatch, induced load, conducted heat
flux and the combined assessment are exercised by the gate 3 contract
test:
scripts/test_e3301_operational_constraints_thermo_mechanical_interfaces.py
against
scripts/e3301_operational_constraints_thermo_mechanical_interfaces_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_operational_constraints_thermo_mechanical_interfaces.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
