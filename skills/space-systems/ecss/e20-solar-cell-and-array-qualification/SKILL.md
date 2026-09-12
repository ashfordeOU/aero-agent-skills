---
name: e20-solar-cell-and-array-qualification
description: "Use when derive the qualification route for a spacecraft photovoltaic assembly under ECSS-E-ST-20C clause 5.5.1: categorize each item as bare cell, coverglass, interconnect, protection diode, cell-coverglass assembly or panel, select full, delta or similarity qualification from its heritage and the environment envelope already covered, list the qualification tests that category owes and flag the ones absent from the programme, size the thermal-cycle count against mission eclipse cycles and the qualification fluence against the end-of-life particle dose, and roll the degradation factors into an end-of-life power check. Trigger: ecss, e-st-20c-clause-5-5-1, photovoltaic-assembly-qualification, solar-cell-qualification, coverglass-qualification, bypass-diode-qualification, thermal-cycling-qualification, radiation-fluence-margin, end-of-life-power-degradation."
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
  tags: [ecss, e-st-20-electrical-scope, e20-solar-cell-and-array-qualification, photovoltaic-assembly-qualification, solar-cell-qualification, coverglass-qualification, bypass-diode-qualification, thermal-cycling-qualification, radiation-fluence-margin, end-of-life-power-degradation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Solar Cell and Array Qualification (space-systems/ecss/e20-solar-cell-and-array-qualification)

Use when the task is the clause 5.5.1 qualification route of
ECSS-E-ST-20C for a photovoltaic assembly -- deciding what has to be
qualified at cell, coverglass, interconnect, diode, cell-assembly and
panel level, how much of that route the item's heritage can replace,
and whether the qualification environment actually envelopes the
mission the array has to survive.

## Domain quick reference

- The photovoltaic chain is qualified item by item, and each item is
  categorized once: bare solar cell, coverglass (with its adhesive and
  coating), interconnect, protection diode (bypass or blocking),
  cell-coverglass assembly and panel or wing assembly. The category
  decides what the qualification programme owes -- a coverglass owes
  optical transmittance and ultraviolet exposure but not a reverse-bias
  characterisation; a protection diode owes forward and reverse
  characterisation but not an optical measurement.
- The route is one of three. Full qualification applies to a new
  design. Delta qualification applies when a flight-proven item is
  modified, or when the design is unchanged but the new mission
  environment is harsher than the one already qualified -- only the
  affected tests are repeated. Qualification by similarity applies
  only when the design and process are unchanged and the qualified
  environment already envelopes the mission; either condition failing
  pushes the item back to delta.
- Two environment quantities size the programme. Thermal cycling is
  driven by the mission eclipse-cycle count multiplied by a
  qualification factor, so a low Earth orbit array accumulates far
  more required cycles than a geostationary one at the same lifetime.
  Radiation is driven by the end-of-life equivalent particle fluence
  multiplied by a margin factor; a qualification fluence below that
  target leaves the end-of-life performance unproven no matter how
  many cycles were run.
- End-of-life power is the beginning-of-life power multiplied by every
  independent degradation factor in the chain -- radiation, ultraviolet
  darkening of the cover, thermal-cycling interconnect loss,
  contamination deposit and cell-to-cell mismatch. Each factor is a
  fraction of unity retained; the product is compared against the
  power the mission requires at end of life.

## Workflow

1. Categorize every item in the photovoltaic assembly; reject an item
   type that is not part of the clause 5.5.1 chain.
2. For each item, select the route: similarity when the design and
   process are unchanged and the qualified environment envelopes the
   mission, delta when the item is flight-proven but modified or the
   envelope is not covered, otherwise full qualification.
3. Build the owed test set for the item category, subtract the tests
   the programme already performs, and flag each remaining test.
4. Compute the required thermal-cycle count from the mission eclipse
   cycles and the qualification factor, and flag a planned cycle count
   below it.
5. Compute the required qualification fluence from the end-of-life
   equivalent fluence and the radiation margin factor, and flag a
   qualification fluence below it.
6. Multiply the degradation factors onto the beginning-of-life power
   and flag an end-of-life power below what the mission requires.
7. Aggregate the test-coverage, thermal-cycling, radiation and power
   findings; the assembly is qualified only when every list is empty.

## Pitfalls

- Granting qualification by similarity because the part number did not
  change, while the new orbit raises the eclipse-cycle count or the
  trapped-particle fluence -- an unchanged design in a harsher
  environment is a delta-qualification case, not a similarity case.
- Qualifying the bare cell and treating the cell-coverglass assembly
  as covered; the assembly's failure modes live in the adhesive bond
  and the interconnect, which the bare cell programme never loads.
- Counting mission eclipse cycles as the required thermal-cycle count
  with no qualification factor, so the test article sees exactly the
  life it must survive and demonstrates no margin at all.
- Reporting the end-of-life power from the radiation factor alone --
  ultraviolet darkening, interconnect loss, contamination and mismatch
  multiply, and dropping four of five factors overstates the array by
  a wide margin.
- Treating a protection diode as a passive item outside the
  qualification scope; its reverse characteristic under a shadowed
  string is the mechanism that keeps a hot spot from destroying the
  cells around it.

## Behavior contract (gate 3)

The item categorization, route selection, owed-test, thermal-cycle,
radiation-fluence and end-of-life power logic is exercised by the gate
3 contract test:
scripts/test_e20_solar_cell_and_array_qualification.py against
scripts/e20_solar_cell_and_array_qualification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_solar_cell_and_array_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
