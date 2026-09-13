---
name: e2006-plasma-power-loss-validation
description: "Use when compute the parasitic leakage-current that exposed conductors drain out of the ambient-plasma and confirm the resulting power-loss is acceptable, under ECSS-E-ST-20-06C clause 8.3: validate the plasma-environment, categorize each exposed element as electron-collecting, ion-collecting or non-collecting from its bias relative to plasma potential, scale the thermal-current-density by the orbit-limited-motion sheath enhancement for its geometry, apply the snapover multiplier where an element biases past the snapover-onset against a dielectric, then sum the parasitic-power-loss and judge it against the allowable fraction of generated output. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c-clause-8-3, plasma-leakage-current, parasitic-power-loss, snapover-onset, orbit-limited-motion, thermal-current-density, ambient-plasma-environment, sheath-collection-area."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-plasma-power-loss-validation, plasma-leakage-current, parasitic-power-loss, snapover-onset, orbit-limited-motion, thermal-current-density]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Plasma Leakage Power-Loss Validation (space-systems/ecss/e2006-plasma-power-loss-validation)

Use when the task is the ECSS-E-ST-20-06C clause 8.3 analysis of the current
that leaks out of exposed conductors into the surrounding plasma, and the
demonstration that the generated output lost that way stays acceptable.

## Domain quick reference

- Clause 8.3 is a loss-accounting question, not a breakdown question. Any
  conductor exposed to the ambient-plasma and held away from the local
  plasma potential sits at the bottom of a sheath and drains a steady
  current out of it. That current times the bias is generated output
  converted to nothing — it never reaches a load, and it never appears in a
  harness loss term either.
- Which species is drained follows the sign of the bias. An element
  positive with respect to the plasma collects electrons; a negative one
  collects ions. Because the electron is roughly four orders of magnitude
  lighter than an oxygen ion at the same temperature, the electron-collecting
  branch dominates the loss by a wide margin, and a negatively-biased
  element is rarely the driver.
- The current is not simply area times the thermal-current-density. The
  sheath grows with bias, and how fast depends on the shape: a flat
  conductor collects through roughly its own area, a thin cylindrical
  interconnect follows the orbit-limited-motion square-root law, a compact
  node follows the linear law. At a few hundred volts the sheath of a thin
  interconnect can carry two orders of magnitude more current than its
  geometric area suggests.
- Snapover is the discontinuity. Above a bias threshold, secondary electrons
  knocked off an adjacent dielectric let the sheath spread across the
  insulator surface and recruit its area into the collector. An element that
  is compliant just below the snapover-onset can jump by a large factor a
  few volts higher, so the onset must be located, not interpolated across.
- The acceptance criterion is a budget: the summed parasitic-power-loss
  against an allowable fraction of the generated output. A single element
  carrying most of that sum is a design finding in its own right, even
  inside budget, because it means one item governs the whole result.

## Workflow

1. Validate the ambient-plasma environment for the worst-case orbit
   position: electron density, electron temperature, ion temperature and
   the dominant ion mass. Reject a non-physical density or temperature
   before any current is computed.
2. Inventory every exposed element — interconnect, cell edge, connector
   shell, exposed standoff, instrument boom — with its exposed area,
   geometry, bias relative to plasma potential, whether it is encapsulated,
   and whether it sits against a dielectric. Categorize each as
   electron-collecting, ion-collecting or non-collecting.
3. Compute the thermal-current-density for the collected species from the
   validated environment, using the ion mass for the ion branch.
4. Apply the sheath enhancement for the element's geometry at its bias, and
   then the snapover multiplier where the element is biased at or past the
   snapover-onset against a dielectric. Multiply by the exposed area to get
   the leakage-current.
5. Convert each leakage-current to a parasitic-power-loss with the bias
   magnitude, sum over all elements, and compare against the allowable
   fraction of generated output. Rank the contributors and flag any single
   element carrying more than half the total.
6. Report margin, loss fraction, ranked contributors and every snapover
   element. The clause is met only when the summed loss sits inside the
   allowance.

## Pitfalls

- Multiplying area by thermal-current-density and stopping there. That is
  the zero-bias answer; at operating bias the sheath enhancement is the
  dominant term for anything that is not flat, and ignoring it understates
  the loss by orders of magnitude.
- Sampling the bias sweep coarsely across the snapover-onset. The collected
  current steps rather than ramps there, so a grid that steps over the onset
  reports a benign curve for hardware that actually jumps.
- Budgeting against the ion branch because it is easier to bound. Ion
  collection is the small term; a loss analysis dominated by ions almost
  always means the electron-collecting elements were missed.
- Treating an inside-budget total as the end of the analysis when one
  element carries most of it. That result has no robustness: a small change
  in that one item's area or bias moves the whole budget.
- Letting a floating-point boundary decide a compliant budget. A summed
  loss compared against a fraction of the generated output can land a few
  units in the last place above an allowance it mathematically equals; the
  comparison absorbs that representation error rather than the allowance
  being widened.

## Behavior contract (gate 3)

The environment validation, species categorization, thermal-current-density,
sheath-enhancement, snapover, ranking and budget logic is exercised by the
gate 3 contract test:
scripts/test_e2006_plasma_power_loss_validation.py against
scripts/e2006_plasma_power_loss_validation_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_plasma_power_loss_validation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
