---
name: e2008-diode-human-body-esd
description: "Assess whether a protection diode survives an electrostatic discharge representative of a charged person reaching its terminals, under ECSS-E-ST-20-08C clause 9.6.16: hold the discharge network capacitance and series resistance inside their bands, derive the peak current, decay constant, transferred charge and stored energy the step voltage produces, walk the geometric step ladder with its pulse count and both polarities, take the reverse leakage and forward voltage drift across the series, and group the surviving level into a withstand band. Use when a human body ESD step stress for protection diodes is planned or audited. Trigger: ecss, e-st-20-08c-clause-9-6-16, protection-diode-human-body-esd, diode-hbm-discharge-network, diode-hbm-peak-current, diode-hbm-stored-energy, diode-hbm-withstand-band, diode-esd-leakage-drift, diode-esd-step-stress-ladder."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-diode-human-body-esd, protection-diode-human-body-esd, diode-hbm-discharge-network, diode-hbm-peak-current, diode-hbm-stored-energy, diode-hbm-withstand-band, diode-esd-leakage-drift, diode-esd-step-stress-ladder]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Diode Human Body ESD (space-systems/ecss/e2008-diode-human-body-esd)

Use when the task is clause 9.6.16 of ECSS-E-ST-20-08C -- whether a
protection diode survives the discharge a charged person delivers when a
finger or a hand tool reaches one of its leads. A panel bay is full of
people and insulating surfaces, so this is not an exotic event: it is
the ordinary one, and the campaign that measures it has to look like the
person rather than like the bench.

## Domain quick reference

- The discharge network is the whole claim. A capacitance charged to the
  step voltage, emptied through a series resistance into the device, is
  what makes the pulse a person. A network outside its bands delivers a
  different event carrying this event's name, and every number derived
  downstream then describes that other event instead.
- Three quantities follow from the network and the step: the peak
  current is the step divided by the series resistance, the decay
  constant is the resistance times the capacitance, and the stored
  energy is what the junction has to absorb. None of them is read off an
  instrument; all three are derived, so a network check comes first.
- Stress is a ladder, not a single shot. Each level sits a fixed ratio
  above the last, and the level the part last held is the withstand. A
  ladder that climbs too gently ends below the level of interest and
  reports a survival that was never tested for.
- A level is several pulses, in both polarities. One pulse measures
  luck. One polarity leaves a conduction path of the diode entirely
  unstressed, which for a protection diode is the path that matters.
- Pulses need a recovery interval between them. Fired back to back they
  stack a thermal excursion the model does not contain.
- Survival is not the same as still conducting. Discharge damage shows
  up first as reverse leakage that grew and, later, as a forward voltage
  that moved. Both are taken before and after the series and both carry
  a limit.
- A withstand level is grouped into a band so parts can be compared. The
  band is a reporting convenience; the pass or fail is against the
  policy floor, not against the band edge.

## Workflow

1. Validate the stress policy first: withstand floor, pulses per level,
   ladder levels and ratio, recovery interval, network capacitance and
   resistance bands, and the two drift limits. A band whose lower edge
   sits above its upper edge is refused rather than used, and a ladder
   ratio of one is refused because it never rises.
2. Check the declared network against its bands before anything else.
   Out of band, the campaign is reported as network deficient and the
   survival number is not defended.
3. Build the ladder from the start voltage, ratio and level count, and
   derive the peak current, decay constant, transferred charge and
   stored energy at the surviving level.
4. Take the reverse leakage and forward voltage drift across the series
   as fractions of their starting values, and hold each against its
   limit. A drift landing exactly on a limit passes; the comparison
   tolerance absorbs representation error and the limit does not move.
5. Check the plan shape: pulses per level, polarity coverage, ladder
   depth and ratio, recovery interval. Report every finding, not the
   first.
6. Close on one verdict, the network outranking the rest because it
   decides whether the campaign measured this event at all: network
   deficient, withstand deficient, stress plan deficient, or survival
   accepted.

## Pitfalls

- Reporting a withstand voltage from a network nobody checked. The
  series resistance sets the peak current directly, so a resistance a
  factor low turns a modest step into a stress the model never intended,
  and the reported level belongs to no model at all.
- Treating the capacitance as the only network parameter. Capacitance
  sets the energy, resistance sets the peak current and together they
  set the decay; two of the three are wrong if either is out of band.
- Firing one pulse per level. Discharge damage is partly statistical,
  and a single pulse that missed the weak path returns a pass that the
  next unit will not repeat.
- Stressing one polarity. A protection diode conducts one way and blocks
  the other, and the blocking path is the one an unplanned discharge
  finds. A single-polarity campaign leaves it unmeasured.
- Climbing the ladder too gently to save time. A shallow ratio with few
  levels tops out below the floor, and the campaign then reports the top
  of its own ladder as the part's withstand.
- Declaring survival because the part still conducts. A junction with
  leakage several times its starting value is damaged; it simply has not
  finished failing yet, and the drift limits are what catch it.
- Comparing a derived drift or energy against a limit by bare
  arithmetic. These come out of products and divisions that land a few
  units in the last place either side of a limit on different hosts, so
  the comparison absorbs that error while the limit itself is never
  relaxed.

## Behavior contract (gate 3)

The policy validation, discharge network band check, peak current, decay
constant, transferred charge and stored energy derivations, the
geometric step ladder, the withstand band grouping, the leakage and
forward voltage drift fractions, the polarity coverage and plan shape
checks, and the survival verdict are exercised by the gate 3 contract
test: scripts/test_e2008_diode_human_body_esd.py against
scripts/e2008_diode_human_body_esd_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_diode_human_body_esd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
