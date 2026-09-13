---
name: e2008-photovoltaic-assembly-purpose-and-objective
description: "Compute the design-limit margins and the responsibility split that clause 5.1.2 of ECSS-E-ST-20-08C expects a photovoltaic-assembly work scope to establish: normalize each declared limit into a not-to-exceed or not-to-fall-below margin fraction of the limit, compare it with the margin the project policy demands for its thermal, electrical, mechanical or optical category, name the required category that carries no declared limit at all, and check that every design, manufacturing and verification work item has one accountable party with an agreement reference wherever the work is shared. Use when a PVA statement of work, procurement specification or design-limit list has to be shown complete before build starts. Trigger: ecss, e-st-20-08c, photovoltaic-assembly-design-limit, photovoltaic-assembly-margin-policy, photovoltaic-assembly-work-responsibility, pva-customer-supplier-split, pva-design-limit-margin-shortfall, pva-work-scope-completeness."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-photovoltaic-assembly-purpose-and-objective, e-st-20-08c, photovoltaic-assembly-design-limit, photovoltaic-assembly-margin-policy, photovoltaic-assembly-work-responsibility, pva-customer-supplier-split, pva-design-limit-margin-shortfall, pva-work-scope-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Purpose and Objective (space-systems/ecss/e2008-photovoltaic-assembly-purpose-and-objective)

Use when the task is the opening obligation of ECSS-E-ST-20-08C clause
5.1.2: showing that a photovoltaic-assembly work scope actually
establishes what it is required to establish -- the design limits the
assembly may be operated against, the margin each limit is held with,
and who is accountable for each design, manufacturing and verification
activity. This leaf grades a declared scope and names what is still
open.

## Domain quick reference

- Clause 5.1.2 is a completeness obligation, not a design calculation.
  Three things have to be in place before hardware is built: the
  limits, the margins against them, and the ownership of the work. A
  scope that is strong on two of the three is not established.
- A declared limit is read in one of two senses. A not-to-exceed limit
  (cell junction temperature, string open-circuit voltage, coverglass
  solar absorptance) is satisfied by staying below it; a
  not-to-fall-below limit (interconnect pull strength, bond-line shear
  strength, end-of-life power) is satisfied by staying above it. The
  sense is declared with the limit, because the arithmetic reverses.
- The margin is normalized to a fraction of the limit magnitude so that
  a temperature in kelvin, a voltage in volt and a pull strength in
  newton can be ranked against one policy. A limit of zero has no scale
  to normalize against and is rejected rather than divided by.
- The required fraction is a declared project policy, not a physical
  constant. The default carries a larger fraction on mechanical limits
  than on thermal ones, because the mechanical population scatter of a
  bonded interconnect is wider than the spread of a thermal prediction.
  A project may substitute its own table.
- A category with no declared limit is a worse finding than a thin
  margin, because nothing measured it. The absent limit collides with
  nothing and produces no red number, so the category set is checked
  separately against the policy.
- Responsibility is the second half of the clause. Each work item is
  owned by the customer, by the supplier, or jointly; a jointly owned
  item is only established when it cites the agreement that splits it.
  An unowned item leaves the objective open however good the margins
  look, so it is reported rather than defaulted to the supplier.

## Workflow

1. Collect the declared design limits. Each one carries a name, a
   category, its sense, the limit value and the predicted value.
   Reject an uncategorized limit rather than guessing its sense,
   because the margin arithmetic reverses between the two senses.
2. Normalize each limit into a margin fraction of the limit magnitude
   and compare it with the fraction the policy demands for its
   category. Record the shortfall for every limit that falls under, and
   keep the requirement untouched -- the comparison, not the policy,
   absorbs the representation error at the boundary.
3. Check the declared categories against the categories the policy
   requires and name any that carry no limit at all.
4. Take the work breakdown and resolve one accountable party per item.
   Demand an agreement reference for a shared item and flag an item
   with no party at all instead of assigning one.
5. Check that each required activity -- design, manufacturing,
   verification -- is covered by at least one owned item, and report the
   coverage fraction with the open items named.
6. Close with a single verdict. The objective is established only when
   every limit holds its margin, every required category is covered,
   and every work item has an owner; otherwise report it as incomplete
   with the governing limit named.

## Pitfalls

- Grading the margins and calling the scope established. Ownership is
  half of clause 5.1.2, and a scope where nobody has accepted the
  manufacturing activity fails it with every margin green.
- Comparing limits in raw engineering units. A 50 K gap and a 30 V gap
  cannot be ranked against each other; only the normalized fraction
  can, which is why the margin is expressed against the limit magnitude
  rather than as a bare difference.
- Reading a not-to-fall-below limit with not-to-exceed arithmetic. The
  sign flips, so a healthy end-of-life power margin is reported as a
  violation and a genuine shortfall is reported as comfortable.
- Treating an absent category as a pass. A scope that declares no
  mechanical limit produces no non-compliant limit, so a check that
  only grades what was declared reports a clean sheet on the one gap
  that matters most.
- Defaulting an unowned work item to the supplier because the supplier
  owns the neighbouring items. The clause asks who is accountable, and
  an inferred owner has never accepted the work.
- Judging a margin that sits exactly on the policy fraction by bare
  arithmetic. A fraction is a quotient, so a case meant to land on the
  requirement can fall a few units in the last place below it; the
  comparison absorbs that while the policy stays as declared.

## Behavior contract (gate 3)

The margin normalization, category coverage, work-item ownership
resolution and the combined work-scope verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_photovoltaic_assembly_purpose_and_objective.py
against
scripts/e2008_photovoltaic_assembly_purpose_and_objective_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2008_photovoltaic_assembly_purpose_and_objective.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
