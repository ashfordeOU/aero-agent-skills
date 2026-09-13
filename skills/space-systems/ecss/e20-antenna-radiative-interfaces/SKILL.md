---
name: e20-antenna-radiative-interfaces
description: "Use when evaluate the radiative interaction between an antenna and its surrounding spacecraft-structure under ECSS-E-ST-20C clause 7.2.3.2, from phase B onward: place each appendage (solar-array-wing, thermal-radiator, deployable-boom, neighbouring radiating-port) in the reactive-near-field, radiating-near-field or far-field zone, categorize its interaction-path as main-beam-blockage, near-field-coupling, side-lobe-scattering or port-to-port-coupling, convert the item radar-cross-section and the antenna-gain toward it into a re-radiated level, turn that level into peak pattern-ripple and a boresight-pointing-perturbation, and compare every figure against the declared allowable. Trigger: ecss, e-st-20-electrical-scope, antenna-structure-interaction, main-beam-blockage, near-field-coupling, side-lobe-scattering, port-to-port-isolation, pattern-ripple, radar-cross-section, appendage-scattering."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-radiative-interfaces, antenna-structure-interaction, main-beam-blockage, near-field-coupling, side-lobe-scattering, port-to-port-isolation, pattern-ripple, appendage-scattering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical and Optical Engineering — Antenna Radiative Interfaces (space-systems/ecss/e20-antenna-radiative-interfaces)

Use when the task is the radiative-interface assessment of ECSS-E-ST-20C
clause 7.2.3.2 -- quantifying, from phase B onward, how the spacecraft
structure and its appendages disturb an antenna pattern and how much
energy the antenna couples into a neighbouring radiating port.

## Domain quick reference

- The assessment is anchored to phase B and later. Before that the
  configuration is not stable enough to place anything, so the correct
  outcome is a deferred assessment rather than a pass: not demonstrated
  is not compliant.
- Geometry first. An aperture of diameter D at wavelength L has a
  reactive near field out to 0.62*sqrt(D^3/L), a radiating near field out
  to 2*D^2/L, and its pattern is only fully formed beyond that. On a
  compact spacecraft most appendages sit inside one of the two near-field
  zones, and that is a result, not an inconvenience: a closed-form
  re-radiation estimate does not apply there and the item has to be
  carried into a full-wave model instead.
- Angular placement decides the mechanism. An item within half the
  half-power-beamwidth of boresight blocks the main beam. Out to roughly
  2.39 times that half-angle the item sits on the main-lobe skirt, where
  it is still strongly illuminated. Beyond it the item is in the
  side-lobe region and scatters at a level set by the antenna-gain
  pointing at it.
- Re-radiation level. An item of radar-cross-section S at distance d,
  illuminated by antenna-gain Gi while the peak is Gp, re-radiates at
  (Gi - Gp) + 10*log10(S/(4*pi*d^2)) relative to the main-beam peak. That
  single number drives both pattern effects: a coherent scattered field
  at voltage ratio r produces a peak-to-peak pattern-ripple of
  20*log10((1+r)/(1-r)) and shifts the apparent boresight by about half a
  beamwidth times r.
- A neighbouring radiating port is a different problem: the figure of
  merit is port-to-port-isolation, the free-space spreading loss
  20*log10(4*pi*d/L) less the gain each port presents to the other, and
  it is compared against a required isolation rather than against a
  ripple allowable.
- An allowable that is absent from the record is a finding in its own
  right; a configuration with no declared pattern-ripple allowable has
  not been specified and cannot be declared compliant.

## Workflow

1. Confirm the project has reached phase B. Earlier than that, return the
   assessment as deferred rather than as a pass.
2. Inventory the surrounding hardware with a unique id each: solar-array
   wings, thermal radiators, deployable booms, star-tracker baffles,
   propulsion tanks, MLI-covered panels and every other antenna port on
   the spacecraft. Record for each its distance from the antenna, its
   angular offset from boresight, the antenna-gain in its direction, its
   radar-cross-section, whether it is itself a radiating port, and
   whether it is illuminated at all.
3. Place each item in its field region from the distance and the aperture
   zone radii, and in its beam sector from the angular offset and the
   half-power-beamwidth.
4. Categorize the interaction-path from those two plus the hardware type:
   port-to-port-coupling for a radiating neighbour, no-interaction-path
   for a shadowed item, main-beam-blockage on boresight,
   near-field-coupling for anything still inside the far-field boundary,
   and main-lobe or side-lobe scattering otherwise. Drop the
   no-interaction-path items instead of carrying them as a worst case.
5. For a scattering item compute the re-radiated level, the resulting
   pattern-ripple and the boresight-pointing-perturbation, and judge both
   against their allowables. For a radiating neighbour compute the
   port-to-port-isolation and judge it against the required value; flag
   it additionally when the neighbour sits inside the far-field boundary,
   where the spreading formula no longer holds.
6. Aggregate: report the worst pattern-ripple, the minimum
   port-to-port-isolation and every item carrying a finding. The
   radiative interface is demonstrated only when no item carries one.

## Pitfalls

- Applying the closed-form re-radiation or spreading formulas to an item
  inside the far-field boundary -- on a compact spacecraft that is most
  of them, and the number produced is not merely imprecise, it is the
  wrong model. The correct output is a finding that routes the item to a
  full-wave model.
- Charging a shadowed item "to be conservative" -- it inflates the worst
  pattern-ripple and hides the appendage that actually drives the budget.
- Reporting the re-radiated level and stopping there -- the level is an
  intermediate quantity; the specification is written in pattern-ripple
  and boresight-pointing-perturbation, and a level that looks small can
  still break a tight pointing allowable on a wide beam.
- Judging a neighbouring radiating port against the pattern-ripple
  allowable -- port-to-port-coupling is governed by a required isolation,
  and the two requirements come from different budgets.
- Treating a phase-A configuration as compliant because no item breached
  an allowable -- the geometry was not yet stable, so nothing was
  demonstrated.
- Assuming the antenna-gain toward an appendage equals the peak gain --
  it is the gain in that direction, which is what makes the side-lobe
  level of the antenna part of the structural-interaction budget.

## Behavior contract (gate 3)

The field-region and beam-sector placement, interaction-path
categorisation, re-radiation level, pattern-ripple and
boresight-pointing-perturbation, port-to-port-isolation, phase gate and
aggregation logic are exercised by the gate 3 contract test:
scripts/test_e20_antenna_radiative_interfaces.py against
scripts/e20_antenna_radiative_interfaces_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_antenna_radiative_interfaces.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
