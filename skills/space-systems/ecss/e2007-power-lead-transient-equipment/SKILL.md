---
name: e2007-power-lead-transient-equipment
description: "Determine whether the generator and instruments declared for a power-lead transient injection under ECSS-E-ST-20-07C clause 5.4.9.2 can deliver and record the specified pulse. Use when a supply-transient bench is assembled or reviewed: raise the required terminal amplitude to the open-circuit output the source and load impedances demand, bound the generator edge and its repetition interval, derive the recording chain bandwidth, sample rate and memory depth from the pulse edge and window, set the decoupling impedance floor that keeps the pulse out of the power source, size the probe rating, categorize every declared item as adequate, marginal or inadequate, and name the governing shortfall. Trigger: ecss, e-st-20-07c, power-lead-transient-equipment, transient-generator-open-circuit-amplitude, transient-source-impedance-divider, transient-decoupling-impedance-floor, transient-chain-rise-time, transient-record-depth, transient-pulse-repetition-interval."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-power-lead-transient-equipment, transient-generator-open-circuit-amplitude, transient-source-impedance-divider, transient-decoupling-impedance-floor, transient-chain-rise-time, transient-record-depth, transient-pulse-repetition-interval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Power-Lead Transient Test Equipment (space-systems/ecss/e2007-power-lead-transient-equipment)

Use when the task is the equipment list of ECSS-E-ST-20-07C clause 5.4.9.2
-- deciding whether the transient generator, the coupling and decoupling
arrangement and the recording chain declared for a power-lead transient
injection can put the specified pulse on the lead and show what actually
arrived, before the bench is built rather than after a capture turns out to
be unusable.

## Domain quick reference

- The amplitude asked for is the amplitude at the unit's terminals, and it
  is never the amplitude the generator is set to. The generator source
  impedance and the impedance the lead presents form a divider, so a
  matched pair of impedances costs a factor of two before anything else is
  considered.
- The generator has to make the edge, and the recording chain has to be
  several times faster than the edge the generator makes. These are two
  different bounds on two different instruments, and meeting one says
  nothing about the other: a generator on the specified rise time paired
  with a chain on the same rise time records the chain, not the pulse.
- Bandwidth, sample rate and memory depth are three separate legs of the
  recording requirement. The edge sets the bandwidth through the rise-time
  bandwidth product, the bandwidth sets the rate that has to oversample it,
  and the window at that rate is a point count. A chain with two of the
  three forces the rate down at capture time, which removes the bandwidth
  again.
- The decoupling arrangement is what makes the injection a test of the unit
  rather than of the laboratory supply. The injected current divides
  between the unit and the path back into the source, and holding the share
  that escapes below an allowed fraction puts a floor under the decoupling
  impedance. Too low a floor and the supply absorbs the pulse the unit was
  supposed to see.
- The coupling path is bounded the other way. Series impedance in the
  coupling arrangement drops part of the pulse before it reaches the lead,
  so what the coupling may add is capped by the loss the test can carry.
- The repetition interval is a generator limit, not a schedule preference.
  A generator run past its duty sags from pulse to pulse, and the later
  pulses in a burst are then smaller than the first without anyone
  recording that they were.
- Fitness is three-valued. A capability comfortably past its requirement is
  adequate; one sitting on the requirement is usable but carried as a
  limitation, because instrument figures are typical rather than
  guaranteed; one short of it is inadequate and the bench cannot take the
  measurement.
- When several items are short, the one that governs is the one short by
  the largest factor, not the first one listed. That is the item whose
  replacement changes the answer.

## Workflow

1. Validate the specified pulse: positive amplitude, edge, width and
   window, a width no shorter than the edge and a window no shorter than
   the width, and every declared fraction strictly between zero and one.
2. Raise the terminal amplitude through the source and load impedances to
   the open-circuit output the generator has to produce.
3. Bound the generator edge by the specified rise time, and the repetition
   interval by the width and the duty the generator is allowed.
4. Derive the chain rise-time ceiling from the specified edge, the
   bandwidth from that ceiling, the sample rate from the bandwidth and the
   memory depth from the window, rounding a partial sample up.
5. Put a floor under the decoupling impedance from the diversion allowed
   into the power source, and a ceiling on the coupling series impedance
   from the loss allowed on the way in.
6. Normalize the declared inventory, refusing an unrecognized item and a
   duplicate declaration, and record every required item that is absent.
7. Compare each declared quantity with its requirement in the right sense,
   categorize it adequate, marginal or inadequate, reduce the inadequate
   checks to the governing shortfall and aggregate findings and
   limitations. The bench is fit only when no finding stands.

## Pitfalls

- Setting the generator to the amplitude the interface specifies and
  delivering half of it, because the divider between the source and the
  lead was never worked through.
- Choosing a generator on its edge and a scope on the same edge, so the
  recorded rise time is the chain's own and the pulse is never measured.
- Checking bandwidth and sample rate but never the memory depth, then
  shortening the window at capture time so the tail of the transient is
  outside the record.
- Sizing the decoupling on convenience, so the laboratory supply swallows
  the pulse and the unit sees a fraction of the specified transient while
  the generator reports it faithfully.
- Ignoring the series impedance the coupling arrangement adds, which is
  the other end of the same argument and drops the pulse before it ever
  reaches the lead.
- Running a burst faster than the generator's duty allows, so the later
  pulses are smaller than the first and nothing in the record says so.
- Treating a capability that exactly equals its requirement as headroom.
  Instrument figures are typical, and the next unit off the shelf sits on
  the other side.
- Reporting the first inadequate item found as the problem when another
  item is short by a far larger factor and is what actually has to change.

## Behavior contract (gate 3)

The pulse validation, open-circuit divider, generator and chain rise-time
ceilings, bandwidth, sample-rate and memory-depth derivation, decoupling
impedance floor and coupling impedance ceiling, repetition interval,
probe rating, inventory normalization, three-valued categorization and
governing-shortfall reduction are exercised by the gate 3 contract test:
scripts/test_e2007_power_lead_transient_equipment.py against
scripts/e2007_power_lead_transient_equipment_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_power_lead_transient_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
