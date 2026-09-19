---
name: e3311-gas-generators
description: "Compute the delivered output of a pyrotechnic gas generator and grade it against ECSS-E-ST-33-11C clause 4.11.6. Use when the task is sizing or accepting a generator that drives a closed volume: turning grain mass and specific gas yield into moles, then into a closed-volume pressure at the delivered gas temperature, evaluating the cold-light-large corner against the actuation requirement and the hot-heavy-small corner against the receiver working and burst pressures, and reading pressure rise time, hot-corner gas temperature against the seal limit and solid products against the allowance. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, pyrotechnic-gas-generator-output, gas-generator-closed-volume-pressure, gas-generator-actuation-margin, gas-generator-burst-margin, gas-generator-rise-time, gas-generator-particulate-limit."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-gas-generators, pyrotechnic-gas-generator-output, gas-generator-closed-volume-pressure, gas-generator-actuation-margin, gas-generator-burst-margin, gas-generator-rise-time, gas-generator-particulate-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Gas Generators (space-systems/ecss/e3311-gas-generators)

Use when the task is the output screen of ECSS-E-ST-33-11C clause
4.11.6 -- a charge selected for the gas it produces rather than for
anything it breaks, discharging into a closed volume that has to be
moved and must not be burst.

## Domain quick reference

- A gas generator is graded on both sides at once. Too little output
  and the actuator does not move; too much and the receiver is over
  its working pressure. Neither bound is the design point, and a
  generator sized only against the first will eventually meet the
  second on a hot day with a tight cavity.
- The delivered pressure is computed, never quoted. Grain mass times
  specific gas yield gives moles; moles, the gas constant, the
  delivered temperature and the free volume give a pressure. Every
  term in that expression has a tolerance.
- The two corners are built by pushing the tolerances in opposite
  directions: light grain, large volume, cold conditioning for the
  minimum; heavy grain, small volume, hot conditioning for the
  maximum. Mixing a nominal into either corner hides the case.
- Conditioning temperature does not just change the grain; it changes
  the delivered gas temperature, and that temperature is a direct
  multiplier on the pressure. The same generator is a different
  device at the two ends of its qualification range.
- Free volume is the receiver's property and it is rarely the drawing
  number. Manufacturing tolerance, an actuator part way through its
  stroke and trapped gas all move it, and it divides the whole result.
- Working pressure and burst pressure are two different gates. A peak
  under the burst pressure but over the working pressure has not
  destroyed anything and has still left the receiver outside what it
  was qualified to hold.
- Rise time, gas temperature at the receiver and solid products are
  output qualities the pressure figure says nothing about. A
  generator can deliver exactly the right pressure, too slowly, too
  hot, and full of slag.

## Workflow

1. Normalize the generator and the receiver, rejecting a tolerance
   fraction outside its range and a receiver declaring a burst
   pressure below its own working pressure, because that pair cannot
   both be true.
2. Build the cold corner -- minimum grain mass, maximum free volume,
   cold conditioning -- and the hot corner from the opposite bounds,
   and compute the delivered gas temperature for each.
3. Turn each corner into a pressure through moles, the gas constant,
   the corner temperature and the corner volume.
4. Grade the cold pressure against the actuation requirement with
   margin; grade the hot pressure against the working pressure and
   the burst pressure as two separate findings.
5. Grade the measured rise time against the actuator's limit, the
   hot-corner gas temperature against the seal limit, and the solid
   products against the receiver's allowance.
6. Close with the corners, the failed gates and the verdict, so a
   reader can see which bound drove the outcome.

## Pitfalls

- Sizing against a nominal pressure. The nominal corner is the one
  case the hardware never presents, and both real corners sit on
  opposite sides of it.
- Taking flame temperature as the delivered gas temperature at every
  conditioning point. The shift is small in kelvin and it multiplies
  the pressure directly, so it moves both corners further apart.
- Using the drawing volume as the free volume. The actuator's own
  position and the manufacturing tolerance change the denominator of
  the whole computation.
- Reading a burst margin as the structural answer. Burst is the
  failure bound; the working pressure is the qualified bound, and a
  peak between the two is a finding even though nothing broke.
- Accepting a generator on pressure alone. Rise time, gas temperature
  and particulate are separate requirements, and a hot, slow, dirty
  charge delivers the right number and destroys the seal.
- Comparing a corner pressure with a limit by bare arithmetic. The
  pressure is a product of four measured quantities, so a design
  landing exactly on its limit can sit a few units in the last place
  above it; the comparison absorbs that while the limit stays
  untouched.

## Behavior contract (gate 3)

The generator and receiver normalization, the moles and closed-volume
pressure expressions, the delivered gas temperature shift, the cold
and hot corner construction, the actuation, working-pressure, burst,
rise-time, thermal and particulate gates and the overall verdict are
exercised by the gate 3 contract test:
scripts/test_e3311_gas_generators.py against
scripts/e3311_gas_generators_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e3311_gas_generators.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
