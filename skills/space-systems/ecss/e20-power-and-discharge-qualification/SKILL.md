---
name: e20-power-and-discharge-qualification
description: "Use when plan or audit a qualification approach that has to close radio-frequency power-handling-capability and gas-discharge-behaviour together, under ECSS-E-ST-20C clause 7.3.4: derive the qualification-power-level from maximum-operating-power and the agreed overstress-factor, categorize the evidence route behind each axis and refuse a non-standalone route with nothing supporting it, check the dwell reaches thermal steady state at the hot case, confirm the pressure sweep crossed the whole critical band instead of sitting in vacuum, insist both axes close on one hardware-standard, and determine which axes a later design change reopens. Trigger: ecss, e-st-20-electrical-scope, power-and-discharge-qualification, qualification-power-level, qualification-overstress-factor, power-handling-capability, gas-discharge-behaviour, delta-qualification-trigger, hardware-standard-consistency."
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
  tags: [ecss, e-st-20-electrical-scope, e20-power-and-discharge-qualification, qualification-power-level, qualification-overstress-factor, power-handling-capability, gas-discharge-behaviour, delta-qualification-trigger, hardware-standard-consistency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Power and Discharge Qualification (space-systems/ecss/e20-power-and-discharge-qualification)

Use when the task is the clause 7.3.4 qualification approach of
ECSS-E-ST-20C -- the one programme that has to answer both what a
radio-frequency item can carry and how it behaves when the gas around
it can break down, on hardware whose configuration is traceable
across the two answers.

## Domain quick reference

- The clause has two axes and they are not interchangeable.
  Power-handling-capability is a thermal and ohmic question: the item
  carries the overstressed level long enough to settle, at the hot
  case it will really see. Gas-discharge-behaviour is a breakdown
  question: the item stays discharge-free at that same level while the
  ambient pressure is swept through the band where onset is lowest.
  Closing one says nothing about the other.
- Both axes are referred to the same number. The qualification level
  is the maximum operating power raised by the agreed overstress in
  decibels, and the operating envelope a campaign actually qualifies
  is the demonstrated level brought back down by the same factor. When
  the two axes demonstrate different levels, the envelope is set by
  the weaker of them.
- Evidence routes differ in what they can close alone. A dedicated
  qualification model or a protoflight campaign is standalone. A
  numerical prediction or an argument from heritage is not: it closes
  an axis only with a correlation record or a heritage-delta behind
  it, and without that record the axis stays open however good the
  numbers look.
- Dwell is a physical quantity, not a schedule item. The power axis
  needs enough dwell to reach thermal steady state -- several thermal
  time constants, floored by a minimum -- and the discharge axis needs
  enough dwell at each pressure step for onset to develop, since a
  fast sweep can pass straight through the weak point.
- One hardware standard, or a recorded link. Closing the power axis on
  a qualification model and the discharge axis on an engineering model
  is acceptable only when a configuration link ties the two standards
  together; otherwise nothing shows the qualified behaviour belongs to
  one item.
- A later design change reopens the axes it touches: gap geometry,
  surface treatment and venting path reopen the discharge axis;
  plating and thermal interface reopen the power axis; dielectric
  material, connector interface and any operating-power increase
  reopen both. A change that touches neither leaves the qualification
  standing.

## Workflow

1. Derive the qualification level from the maximum operating power and
   the agreed overstress; reject a non-positive power or a negative
   overstress.
2. Categorize the evidence route declared for each axis, resolving
   aliases, and reject an unrecognized route. Flag a non-standalone
   route with no supporting reference recorded against it.
3. Close the power axis: demonstrated level at or above the required
   level, dwell at or above several thermal time constants floored by
   the minimum, and the hot case reached. Flag a missing thermal time
   constant rather than assuming one.
4. Close the discharge axis: demonstrated level at or above the
   required level, the swept pressure band containing the whole
   critical band, and enough dwell at each step. Report each uncovered
   sub-band.
5. Check the two axes against each other: one hardware standard, or
   two with a configuration link on record.
6. Compute the operating envelope the campaign supports as the weaker
   axis's demonstrated level brought back through the overstress
   factor.
7. Map every declared design change onto the axes it reopens and state
   the delta-qualification scope. The programme is qualified only when
   no axis is open, no axis is unaddressed, and no change is left
   hanging.

## Pitfalls

- Reporting one axis as the qualification. A campaign that proves the
  item survives its dissipation says nothing about what happens at a
  few hundred pascal, and vice versa.
- Running the discharge sweep only in vacuum because that is where the
  chamber is stable. The clause is about crossing the weak band, and a
  vacuum-only sweep never reaches it.
- Sweeping pressure quickly. Onset needs dwell at each step; a fast
  ramp can cross the weakest condition without giving a discharge time
  to establish.
- Accepting a prediction as a closed axis. A numerical route earns
  closure only with a correlation to a measurement, and a heritage
  argument only with the delta written down.
- Splitting the axes across two hardware standards and never linking
  them. The pair then qualifies no single configuration.
- Treating a late gap or venting change as a paperwork update. Those
  changes reopen the discharge axis specifically, and the delta scope
  follows from which axis was touched, not from how large the change
  looks.

## Behavior contract (gate 3)

The evidence categorization, qualification-level, operating-envelope,
dwell, power-axis, discharge-axis, cross-axis-configuration and
delta-qualification logic is exercised by the gate 3 contract test:
scripts/test_e20_power_and_discharge_qualification.py against
scripts/e20_power_and_discharge_qualification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_power_and_discharge_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
