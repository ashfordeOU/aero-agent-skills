---
name: e2006-high-voltage-surface-description
description: "Use when compute the plasma-interaction behaviour of a high-voltage solar-array or other deliberately biased external surface in the dense low-orbit plasma of ECSS-E-ST-20-06C clause 8.1: validate the ambient electron-density and electron-temperature, derive the electron-thermal and ram-ion current densities, solve the two-area current-balance that fixes how much of the string-voltage floats positive of the plasma and where spacecraft-ground settles, categorize each biased surface as exposed-conductor, dielectric-covered or semi-exposed-junction, place its plasma-relative potential in the ion-collection, arc-inception, electron-collection or snapover regime, compute the parasitic collected current, and check the mitigations and the total against the parasitic-current budget. Trigger: ecss, e-st-20-06c, high-voltage-biased-surface, low-orbit-plasma-interaction, floating-potential-split, snapover-collection, arc-inception-threshold, parasitic-current-budget, ram-ion-flux."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-high-voltage-surface-description, e-st-20-06c, high-voltage-biased-surface, low-orbit-plasma-interaction, floating-potential-split, snapover-collection, arc-inception-threshold, parasitic-current-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — High-Voltage Surfaces in Low-Orbit Plasma (space-systems/ecss/e2006-high-voltage-surface-description)

Use when the task is the clause 8.1 introduction of ECSS-E-ST-20-06C: a
high-voltage solar-array, or any other deliberately biased external
surface, sits immersed in the dense ionospheric plasma of low orbit, and
the question is where the array drives spacecraft-ground, which surfaces
then collect or repel charge, and which of them fall into the regimes the
rest of clause 8 controls.

## Domain quick reference

- The ionospheric plasma of low orbit is conductive enough to close a
  circuit between a biased surface and the ambient medium. Below the dense
  regime the clause-8.1 concerns do not bite; at ionospheric densities they
  do, which is why the environment is validated and categorized before any
  surface is evaluated.
- Two current densities set the scale. Electrons arrive at their thermal
  speed, which for a fraction-of-an-eV ionosphere is several times the
  orbital speed, so the electron-thermal current density is much the larger.
  Ions arrive mainly by ram: the spacecraft overtakes them, so the ion
  current density is the density times the orbital velocity, not a thermal
  speed.
- Because electrons are collected so much more efficiently per unit area,
  the array floats until a small positive-side area balances a much larger
  negative-side one. The two-area current-balance fixes the fraction of the
  string-voltage that sits positive of the plasma; the remainder sits
  negative, and spacecraft-ground — tied to the negative end — is dragged
  well below plasma potential. On a high-voltage string that is where the
  arcing hazard comes from.
- Each biased surface is categorized before its current is computed:
  exposed-conductor (interconnect, bus-bar tab, biased electrode) collects
  on its full area; dielectric-covered (coverglass, blanket outer layer)
  collects only through pinholes and gaps, a small fraction of its area;
  semi-exposed-junction (cell edge, cell-gap triple junction) sits in
  between and is the site where arc inception actually starts.
- The plasma-relative potential of a surface then places it in exactly one
  regime. Negative and shallow: ion-collection, benign. Negative past the
  inception magnitude: arc-inception risk. Positive and modest:
  electron-collection. Positive past the snapover onset: snapover, where
  secondary-electron emission recruits the surrounding dielectric and the
  effective collecting area jumps by an order of magnitude. The arc-inception
  and snapover regimes demand mitigation on record; the collection regimes
  only consume parasitic current.
- The parasitic current the whole set draws from the plasma is a real
  budget item: it is current generated and never delivered to a load.

## Workflow

1. Validate the ambient environment (electron-density, electron-temperature,
   ram velocity) and decide whether it reaches the dense low-orbit regime.
2. Derive the electron-thermal and ram-ion current densities from it.
3. Solve the two-area current-balance for the fraction of the string that
   floats positive of the plasma, then split the string-voltage into its
   positive end, its negative end and the resulting spacecraft-ground
   potential.
4. Categorize each biased surface, add spacecraft-ground to its potential
   referred to ground to obtain its plasma-relative potential, and place
   that potential in its interaction regime.
5. Compute the parasitic current each surface exchanges with the plasma,
   applying the dielectric leak fraction, the semi-exposed halving and the
   snapover area multiplier.
6. Raise a finding for any surface in the arc-inception or snapover regime
   with no mitigation on record, sum the parasitic currents and compare the
   total against the budget. The set conforms only when both lists are empty.

## Pitfalls

- Treating spacecraft-ground as plasma potential. On a high-voltage array in
  low orbit ground floats strongly negative, and every surface potential has
  to be referred to the plasma before any regime is read off.
- Using a thermal ion flux in low orbit. The spacecraft overtakes the ions,
  so the ram flux governs the ion current; a thermal estimate understates it
  and skews the floating split.
- Computing collected current on geometric area. A dielectric-covered
  surface collects only through its defects, and a snapover surface collects
  far beyond its own conductor — both are area corrections, not potential
  corrections.
- Reading a positive surface as harmless. Past the snapover onset the
  effective collector grows by an order of magnitude, and the parasitic draw
  grows with it.
- Comparing an exactly-at-threshold potential or an exactly-on-budget total
  with a bare float comparison. Potentials are sums of offsets and the total
  is a sum of per-surface currents, so a compliant value can land a few ULPs
  on the wrong side; the logic absorbs that representation error without
  moving the threshold or the budget.

## Behavior contract (gate 3)

The environment validation, current-density derivation, floating-split,
surface categorization, regime placement, parasitic-current and budget logic
are exercised by the gate 3 contract test:
scripts/test_e2006_high_voltage_surface_description.py against
scripts/e2006_high_voltage_surface_description_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_high_voltage_surface_description.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
