---
name: e20-electrical-power-engineering-overview
description: "Use when size and cross-check the spacecraft electrical power chain introduced by ECSS-E-ST-20C clause 5.1: place every power element into generation, storage, conditioning or distribution, derive the bus architecture from whether the bus is regulated in sunlight and in eclipse, compute the eclipse energy the storage must deliver through the distribution efficiency, the usable capacity that implies at the allowed depth of discharge, the sunlit generation needed to carry the load and recharge within the sunlit arc, and the resulting power margin, then flag any stage of the chain left unpopulated. Trigger: ecss, e-st-20-electrical-scope, electrical-power-engineering-overview, power-generation-chain, energy-storage-sizing, power-conditioning-bus, power-distribution-protection, eclipse-energy-balance."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electrical-power-engineering-overview, power-generation-chain, energy-storage-sizing, power-conditioning-bus, power-distribution-protection, eclipse-energy-balance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Power Engineering Overview (space-systems/ecss/e20-electrical-power-engineering-overview)

Use when the task is the introductory power-engineering description of
ECSS-E-ST-20C clause 5.1 -- laying out the four stages of the electrical
power chain, naming the bus architecture, and running the orbit-average
energy balance that sizes the storage and the generation.

## Domain quick reference

- Clause 5.1 describes the electrical power subsystem as a chain of
  four stages, each of which must be populated by at least one element
  before the architecture is describable. Generation converts an
  external source into electrical power (solar array, radioisotope
  generator, fuel cell). Storage carries the load when generation is
  unavailable (secondary battery, supercapacitor bank). Conditioning
  sets the bus and controls the energy flow (shunt regulator, battery
  charge regulator, peak-power tracker, converter). Distribution routes
  and protects the power to each user (distribution switch, latching
  current limiter, harness, fuse).
- The bus architecture follows from where regulation is applied, not
  from the element list. Regulated in both sunlight and eclipse is a
  fully regulated bus; regulated in sunlight only, with the battery
  setting the bus in eclipse, is a sun-regulated bus; regulated in
  neither, with the battery directly coupled, is an unregulated bus.
  Regulated in eclipse but not in sunlight is not an architecture -- it
  is a description error, and is rejected rather than interpreted.
- The energy balance runs over one orbit. The eclipse energy the
  storage must deliver is the eclipse load times the eclipse duration,
  divided by the distribution efficiency -- the loss is upstream of the
  load, so the storage delivers more than the load consumes. The usable
  capacity that implies is that energy divided by the allowed depth of
  discharge and the discharge efficiency; sizing to the raw energy
  ignores both the fraction of the battery that is off-limits and the
  round-trip loss.
- Generation must carry the sunlit load and recharge the storage within
  the sunlit arc. The recharge power is the eclipse energy divided by
  the sunlit duration and the charge efficiency; the total is that plus
  the sunlit load, divided by the conditioning efficiency. The power
  margin is the fractional headroom of the available generation over
  that requirement, and the house minimum is five percent at this stage
  of the design.

## Workflow

1. Inventory the power elements and place each one in exactly one of
   generation, storage, conditioning, distribution. Reject an
   unrecognized element type before the chain is assessed.
2. Check every stage is populated. An empty stage means the chain has a
   gap the overview cannot describe.
3. Name the bus architecture from the regulation state in sunlight and
   in eclipse; reject the inconsistent combination.
4. Compute the eclipse energy the storage must deliver, dividing the
   eclipse load-energy by the distribution efficiency.
5. Convert that into required usable capacity at the allowed depth of
   discharge and the discharge efficiency, and compare it with the
   installed capacity.
6. Compute the required sunlit generation as the sunlit load plus the
   recharge power, divided by the conditioning efficiency, and take the
   margin against the available generation.
7. The architecture is consistent only when the chain, storage and
   generation finding lists are all empty; the computed sizing figures
   are reported alongside them for the design report.

## Pitfalls

- Multiplying the load by the efficiency instead of dividing. The
  distribution and conditioning losses sit between source and load, so
  the source-side figure is always the larger one; multiplying
  understates both the battery and the array.
- Sizing the battery to the eclipse energy. The allowed depth of
  discharge and the discharge efficiency both inflate the capacity that
  must be installed, often by more than a factor of two.
- Forgetting the recharge term in the generation requirement. An array
  sized for the sunlit load alone never refills the battery, and the
  design fails on the second orbit rather than the first.
- Reading a populated element list as a complete chain. Four solar
  arrays and a harness still leave storage and conditioning empty; the
  check is one element per stage, not a count.
- Inferring the architecture from the presence of a battery. Every
  architecture has a battery; what distinguishes them is where the
  regulation is applied.

## Behavior contract (gate 3)

The element-stage placement, bus-architecture derivation, eclipse
energy, required capacity, required generation, power margin and
aggregate chain review logic is exercised by the gate 3 contract test:
scripts/test_e20_electrical_power_engineering_overview.py against
scripts/e20_electrical_power_engineering_overview_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_electrical_power_engineering_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
