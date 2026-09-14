---
name: e2008-deliverable-protection-diode-components
description: "Evaluate whether the integral protection diodes built into a photovoltaic assembly are carried as deliverable items under ECSS-E-ST-20-08C clause 9.2.2: decide from the mounting whether a diode belongs on the assembly item list or on a delivery line of its own, catch the two ways an item is misfiled between them, hold the protection each string architecture requires against the diodes actually fitted and the fitted count against the count the paperwork declares, bracket what the string really delivers, and weight the release by diodes. Use when a PVA delivery item list, protection diode item reconciliation or string protection count has to be reviewed. Trigger: ecss, e-st-20-08c, pva-deliverable-protection-diode-items, protection-diode-mounting-category, pva-diode-item-line-placement, string-bypass-diode-count, pva-diode-inventory-reconciliation, pva-diode-release-bracket."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-deliverable-protection-diode-components, pva-deliverable-protection-diode-items, protection-diode-mounting-category, pva-diode-item-line-placement, string-bypass-diode-count, pva-diode-inventory-reconciliation, pva-diode-release-bracket]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Deliverable Protection Diode Components (space-systems/ecss/e2008-deliverable-protection-diode-components)

Use when the task is clause 9.2.2 of ECSS-E-ST-20-08C -- the protection diodes
built into a photovoltaic assembly are items on the delivery list, and somebody
has to decide which line each one belongs on and how many of them the assembly
actually hands over.

## Domain quick reference

- A protection diode is not a fitting, it is a deliverable item, and the line
  it is booked against is decided by how it is mounted rather than by who
  supplied it. A diode bonded onto the cell assembly or mounted on the
  substrate arrives welded to the article and can only be received with it. A
  diode in the spacecraft wiring arrives on its own and is received on its own.
- The two misfilings fail in opposite directions and neither is cosmetic.
  Booking an integral diode as a separate item asks receiving inspection to
  find a part that is already bonded down. Booking an external diode on the
  assembly line counts it twice at incoming and leaves the harness kit short
  when integration comes to fit it.
- An item nobody booked is worse than either. The hardware is on the assembly
  and no line carries it, so there is no reference to inspect against, no
  reference to raise a nonconformance against, and nothing to reconcile.
- Three counts have to agree per string and they come from three different
  places: what the architecture requires, what the build fitted, and what the
  delivery paperwork declares. Requirement against fitted is a protection
  question, answered by the circuit. Fitted against declared is a traceability
  question, answered by the paperwork. They fail separately, they are repaired
  separately, and collapsing them into one number hides whichever is worse.
- The requirement is derived, not quoted. A string carries bypass protection
  per section and blocking protection per string, so a twenty-section string
  and a one-section string do not need the same diode count and a single figure
  copied across both under-protects one of them.
- Bypass and blocking shortfalls are different failures. A missing bypass diode
  leaves a shadowed section to be driven in reverse by the sections still lit;
  a missing blocking diode leaves the string open to being back-fed from the
  bus. Naming which one is short is the whole content of the finding.
- Counts alone do not settle what the string delivers. The diodes both fitted
  and declared are the ceiling, and a string short of the protection it needs
  cannot deliver against its own count, so the figure is reported as a bracket
  and released against the lower bound.
- Roll-up is weighted by diodes, never by strings. A twenty-section string and
  a one-section string are not half an assembly each, and averaging their
  dispositions reports a delivery neither of them describes.

## Workflow

1. Take the assembly as a list of strings, each carrying its identifier, its
   section count, the bypass and blocking diodes fitted, the diode count the
   delivery paperwork declares, the mounting, and the delivery line the items
   are booked against.
2. Categorize each mounting as integral or external and read off the delivery
   line it is owed.
3. Compare the line the items are actually booked against with that one, and
   name the misfiling in the direction it fails -- integral booked separately,
   external booked on the assembly, or booked nowhere at all.
4. Derive the protection the architecture requires from the section count and
   the per-section and per-string policy, then compare bypass and blocking
   separately against what was fitted.
5. Reconcile fitted against declared and split the difference into diodes
   fitted that nothing declares and diodes declared that nothing carries.
6. Bracket the diodes the string delivers between the accounted count and that
   count less the protection shortfall, and release against the lower bound.
7. Disposition each string: a protection shortfall, a phantom item or a
   misfiled line withholds it; undeclared fitted hardware releases it under
   concession; anything else releases it.
8. Roll the assembly up on diodes: required, fitted, released, the share
   against its floor, the strings withheld, the strings under concession, the
   weakest string and one disposition.

## Pitfalls

- Deciding the delivery line from the supplier rather than from the mounting.
  Who built the diode says nothing about whether it can be received on its own.
- Treating a double-booked external diode as a paperwork tidy-up. It is a
  missing harness part at integration, found on the day nobody has a spare.
- Letting fitted hardware ship against no delivery line because it is obviously
  there. Obvious hardware with no line has nothing to inspect against.
- Quoting one diode count per string from a drawing note. The requirement
  scales with sections, and one figure copied across strings of different
  lengths under-protects the long ones.
- Reporting a total shortfall without saying whether it is bypass or blocking.
  One leaves a section reverse-biased, the other leaves the string back-fed,
  and the repairs are not the same part.
- Collapsing the requirement-against-fitted and fitted-against-declared checks
  into a single reconciliation. A string can be fully protected and completely
  untracked, and that case reads as clean if the two are merged.
- Quoting the accounted count as what the string delivers. A string missing
  protection cannot deliver against its own item count, and the optimistic
  figure over-releases it.
- Averaging string dispositions instead of weighting them by diodes. A short
  string in trouble and a long clean one are not an average.
- Comparing a release share with its floor by bare arithmetic. Both are
  quotients of counts and a delivery exactly on the floor can evaluate a few
  units in the last place under it; the comparison absorbs that while the floor
  stays as written.

## Behavior contract (gate 3)

The mounting categorization, the delivery-line placement check with both
misfiling directions and the unbooked item, the derived bypass and blocking
requirement, the separate bypass and blocking shortfall findings, the fitted
against declared reconciliation, the deliverable diode bracket, the per-string
disposition and the diode-weighted assembly roll-up are exercised by the gate 3
contract test:
scripts/test_e2008_deliverable_protection_diode_components.py against
scripts/e2008_deliverable_protection_diode_components_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_deliverable_protection_diode_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
