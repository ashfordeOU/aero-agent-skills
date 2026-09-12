---
name: e20-bus-voltage-excursion-robustness
description: "Use when verify that a spacecraft electrical subsystem stays robust when a protection device clears a fault and when the primary bus voltage leaves its normal band, under ECSS-E-ST-20C clause 5.7.4: categorize each protection device, check its rating against the derated steady current and the fault current available to clear it, compare the let-through energy with the harness withstand and with the downstream device for coordination, categorize each bus excursion by magnitude and duration, and report equipment outside its declared ride-through envelope. Trigger: ecss, e-st-20-electrical-scope, bus-voltage-excursion, fuse-blowing-robustness, fuse-let-through-i2t, protection-selectivity, primary-bus-undervoltage, primary-bus-overvoltage, equipment-ride-through-envelope."
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
  tags: [ecss, e-st-20-electrical-scope, e20-bus-voltage-excursion-robustness, bus-voltage-excursion, fuse-blowing-robustness, fuse-let-through-i2t, protection-selectivity, primary-bus-undervoltage, equipment-ride-through-envelope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Bus Voltage Excursion Robustness (space-systems/ecss/e20-bus-voltage-excursion-robustness)

Use when the task is the clause 5.7.4 robustness demonstration of
ECSS-E-ST-20C -- showing that the electrical subsystem behaves
acceptably when a protection device blows and when the primary bus
voltage departs from its normal band, whether briefly or for long
enough that the departure is the new operating condition.

## Domain quick reference

- Each protection device is categorized once as single shot (a fuse
  that clears the fault and stays open for the rest of the mission) or
  resettable (a latching or foldback limiter, a breaker). The category
  decides more than the arithmetic: a single-shot device sitting on a
  circuit the operators expect to re-arm in flight is a finding
  whatever its rating.
- A device rating has two sides that pull against each other. It has
  to be large enough that the derated steady current never approaches
  it -- the rating divided into the steady current gives the derating
  factor the policy demands -- and small enough that the fault current
  actually available on that circuit exceeds it by the blow ratio the
  device needs to clear at all. A fuse that never blows protects
  nothing.
- What clears through the device is an energy, the fault current
  squared times the clearing time. The harness downstream has its own
  withstand figure in the same units, and the comparison between the
  two is the check that the wire survives the event the fuse is there
  to end.
- Coordination between a downstream and an upstream device is the same
  energy comparison across two devices: the upstream device must not
  begin to melt before the downstream one has finished clearing, with
  a coordination ratio of margin between them. Without it a local
  fault takes out the whole feeder.
- A bus excursion is categorized on two axes at once. Magnitude places
  it above or below the nominal window or inside it; duration against
  the transient limit decides whether the departure is a transient the
  equipment has to survive or a sustained condition it has to keep
  working in.
- Each equipment declares a nested envelope: absolute limits outside
  which it is damaged, an operating window inside which it functions,
  plus whether it rides through a sustained departure and whether it
  comes back on its own. One excursion yields at most one finding, and
  the damage case takes precedence over the functional one.
- A computed figure meets a limit when it sits at or inside it. Ratios
  and products land a few units in the last place past an exactly
  compliant boundary, so the comparisons absorb that representation
  error rather than moving the limit.

## Workflow

1. Categorize each protection device as single shot or resettable;
   reject an unrecognized kind, a non-positive rating and a
   non-positive blow ratio before any arithmetic.
2. Compute the rating the derating policy demands from the steady
   current and flag a device rated below it; compute the blow ratio
   from the available fault current and flag a device the circuit
   cannot clear.
3. Flag a single-shot device on a circuit that has to be re-armed in
   flight.
4. Compute the let-through energy from the fault current and the
   clearing time and flag a harness whose withstand it exceeds.
5. For each upstream/downstream pair, require the upstream minimum
   melting energy to exceed the downstream let-through by the
   coordination ratio, and flag a pair that does not.
6. Categorize each bus excursion by magnitude against the nominal
   window and duration against the transient limit.
7. For each equipment and each excursion outside the nominal window,
   report in order of precedence: a voltage beyond its absolute
   limits, a sustained departure it does not ride through, or a
   departure from its operating window it cannot recover from without
   a ground command.
8. Aggregate the protection, harness, selectivity and excursion
   findings; the subsystem is robust only when all four lists are
   empty.

## Pitfalls

- Sizing a fuse only against the steady load and never against the
  available fault current -- a device rated so far above the fault the
  circuit can deliver simply never opens, and the fault burns the
  harness instead.
- Comparing currents where the clause needs energies; a device with a
  lower current rating can still pass more energy than a higher-rated
  one if it clears more slowly, and only the squared-current-times-time
  figure settles it.
- Checking each device against its own circuit and calling the
  protection scheme verified -- coordination is a property of the
  pair, and an upstream device that melts first turns a contained
  fault into a lost feeder.
- Treating every departure from the nominal window as one condition --
  a transient that the equipment survives and recovers from is
  acceptable, while the same magnitude held for minutes is a different
  requirement entirely, and only the duration axis separates them.
- Reading an equipment's operating window as its survival limit; the
  absolute limits are what decide damage, and collapsing the two
  reports a destroyed unit and a briefly unavailable one identically.
- Comparing a ratio or a product against a limit with a bare
  inequality -- an exactly compliant circuit can report a breach of a
  few units in the last place, so the comparison must absorb
  representation error without loosening the limit.

## Behavior contract (gate 3)

The device categorization, derated-rating, blow-ratio, let-through
energy, harness withstand, coordination, excursion categorization and
equipment ride-through logic is exercised by the gate 3 contract test:
scripts/test_e20_bus_voltage_excursion_robustness.py against
scripts/e20_bus_voltage_excursion_robustness_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_bus_voltage_excursion_robustness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
