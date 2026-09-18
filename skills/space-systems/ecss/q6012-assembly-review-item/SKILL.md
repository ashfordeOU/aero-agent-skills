---
name: q6012-assembly-review-item
description: "Assess the assembly review item of ECSS-Q-ST-60-12C clause 7.3.9 for a microwave die: confirm the declared die-attach medium is one the programme allows, size the die-to-carrier expansion mismatch across the qualification temperature swing against that medium's allowance, build the junction-to-case path from bondline thickness, conductivity and attached footprint, derive the junction temperature at the dissipated power and compare it against the derated rating, count the bond wires the derated current demands, then close, action or reject the item. Use when a microwave die design review reaches the mounting, bonding and host-module integration data. Trigger: ecss, q-st-60-12-microwave-die-scope, microwave-die-assembly-review, die-attach-method-review, die-carrier-expansion-mismatch, die-attach-bondline-thermal-path, bond-wire-interconnect-count, die-junction-temperature-margin, host-module-integration-readiness."
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
  tags: [ecss, q-st-60-12-microwave-die-scope, q6012-assembly-review-item, microwave-die-assembly-review, die-attach-method-review, die-carrier-expansion-mismatch, die-attach-bondline-thermal-path, bond-wire-interconnect-count, die-junction-temperature-margin, host-module-integration-readiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Assembly Review Item (space-systems/ecss/q6012-assembly-review-item)

Use when the task is the assembly review item of ECSS-Q-ST-60-12C
clause 7.3.9 -- examining how the microwave die will be mounted, bonded
and integrated into its host module, rather than how the circuit
carried on it performs.

## Domain quick reference

- The item is about the transition from a piece of semiconductor to a
  part of a module. Three physical chains carry that transition, and
  the review is only answered when all three are answered: the attach
  chain, the thermal chain and the interconnect chain.
- The attach chain starts with the medium. Eutectic, solder, conductive
  epoxy and adhesive film are not interchangeable: they differ by an
  order of magnitude in how much differential expansion they absorb
  before the joint owes a stress case of its own.
- Die and carrier expand at different rates, so the load on the joint
  is the difference of the two expansion coefficients times the
  temperature swing the qualification programme imposes. Only the
  magnitude of that difference matters -- a carrier that expands less
  than the die loads the joint exactly as a carrier that expands more.
- The thermal chain runs through the same medium. Bondline thickness
  over the product of conductivity and attached footprint gives the
  attach contribution, the carrier spreading resistance adds to it, and
  the dissipated power turns the total into a junction temperature.
  That temperature is graded against the rating less the programme
  derating, never against the bare rating.
- The interconnect chain is a counting problem. Each bond wire carries
  a derated share of its rated current, so the bias and radio-frequency
  demand fixes a minimum wire count. A layout that sits exactly on that
  count has no redundant wire, so a single lifted bond takes the
  interface out of specification.
- Host module integration is the precondition, not a detail. Where the
  module interface is undefined there is nothing to review the assembly
  data against, and the item cannot be opened let alone closed.

## Workflow

1. Confirm the host module integration state first. An undefined
   integration makes the rest of the item unreviewable, and a partial
   one is carried as an action rather than being quietly assumed.
2. Take the declared attach medium and reject an uncategorized one.
   Look up the differential expansion it is credited with absorbing
   from the programme table rather than from the vendor sheet.
3. Size the mismatch from the two expansion coefficients and the
   qualification temperature swing. Where it exceeds the allowance,
   demand a referenced joint stress case; without one the item fails.
4. Build the junction-to-case path from the bondline geometry and add
   the carrier spreading contribution. Derive the junction temperature
   at the dissipated power and compare it against the derated rating,
   flagging a thin margin separately from a breach.
5. Count the bond wires the derated current demands and compare that
   against the layout. Separate an under-provisioned interface, which
   blocks, from an interface with no redundant wire, which actions.
6. Close, action or reject the item, and report which chain drove the
   verdict so the action lands on the right drawing.

## Pitfalls

- Grading the junction temperature against the bare rating. The rating
  is where the die is guaranteed, not where the programme allows it to
  run; dropping the derating step turns a thin margin into an apparent
  pass on every hot case.
- Treating the attach medium as a thermal detail only. It is
  simultaneously the heat path and the compliant layer, and the choice
  that improves one usually worsens the other -- a thin eutectic joint
  spreads heat well and absorbs almost no differential expansion.
- Taking the drawing footprint as the attached area. Voiding, fillet
  and partial wetting reduce the area that actually conducts, so a
  resistance computed on the drawing value is optimistic by whatever
  the process leaves unattached.
- Signing off an interface whose wire count exactly matches the demand.
  The count is a minimum, not a design; with no redundant wire the
  first lifted bond moves the current into the survivors and the
  interface is out of specification from that moment.
- Comparing a mismatch or a margin against its bound by bare
  arithmetic. Both are products and differences of floating-point
  quantities, so a case that sits exactly on the bound can land a few
  units in the last place on the wrong side of it; the comparison
  absorbs that representation error while the bound stays untouched.

## Behavior contract (gate 3)

The attach medium categorization, expansion mismatch sizing, bondline
thermal path, derated junction comparison, bond wire count and closure
verdict are exercised by the gate 3 contract test:
scripts/test_q6012_assembly_review_item.py against
scripts/q6012_assembly_review_item_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_assembly_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
