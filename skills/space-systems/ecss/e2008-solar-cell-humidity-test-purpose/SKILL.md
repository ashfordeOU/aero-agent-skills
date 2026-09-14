---
name: e2008-solar-cell-humidity-test-purpose
description: "Determine what an accelerated damp storage of solar cells under ECSS-E-ST-20-08C clause 7.5.7.1.1 has to deliver: group the mechanisms damp heat attacks, contact adhesion, antireflective coating, integrated bypass diode leakage and interconnect corrosion, onto the parameter each is watched through, size the humidity and temperature acceleration the chamber buys, convert the soak into the ambient storage it stands for, and decide whether the planned monitoring can see a mechanism move. Use when scoping or defending a solar cell damp heat storage before the chamber is booked. Trigger: ecss, e-st-20-08c-clause-7-5-7-1-1, solar-cell-damp-heat-storage-purpose, humidity-acceleration-factor-peck, cell-contact-adhesion-degradation, antireflective-coating-humidity-stability, bypass-diode-reverse-leakage-drift, equivalent-ambient-storage-hours."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-solar-cell-humidity-test-purpose, solar-cell-damp-heat-storage-purpose, humidity-acceleration-factor-peck, cell-contact-adhesion-degradation, antireflective-coating-humidity-stability, bypass-diode-reverse-leakage-drift, equivalent-ambient-storage-hours]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Humidity Test Purpose (space-systems/ecss/e2008-solar-cell-humidity-test-purpose)

Use when the task is to state and defend why solar cells are put through
an accelerated damp storage under ECSS-E-ST-20-08C clause 7.5.7.1.1 --
which interfaces the damp is expected to attack, how much ambient
storage the chamber soak stands for, and whether the parameters planned
for recording can actually see any of it move.

## Domain quick reference

- The test is not aimed at the mission. A cell flies in vacuum; it
  spends the months before launch in store, in transport and in an
  integration hall, all of them at a humidity no cleanroom removes.
  That pre-launch life is the environment being reproduced.
- The damp does not attack the junction. It attacks the interfaces
  around it: moisture creeping under a contact pad until the bond
  strength falls, hydration of the antireflective stack, water taken up
  by the edge passivation of an integrated bypass diode, corrosion of
  the interconnect metallisation.
- Each mechanism is only visible through a parameter chosen in advance
  -- peel strength, reflected fraction, reverse leakage, series
  resistance. A mechanism declared with nothing recorded against it is
  declared and unwatched, and the soak passes with no evidence either
  way.
- None of those mechanisms move fast enough at room conditions to show
  in a campaign. Raising humidity and temperature together accelerates
  them, and a Peck-type model turns the soak into equivalent ambient
  storage: a humidity ratio raised to an exponent, multiplied by an
  Arrhenius term in the two temperatures.
- The acceleration is the whole argument. A chamber run at conditions
  close to ambient buys an acceleration near one, so a thousand-hour
  soak stands for a thousand hours of store and answers nothing about a
  year on the shelf.
- The exponent and the activation energy are declared assumptions, not
  measured constants of the cell. They belong in the record beside the
  equivalent hours, because the equivalence is only as defensible as
  they are.

## Workflow

1. Validate the damp policy first: humidity exponent, activation
   energy, acceleration floor and coverage floor. A non-positive
   exponent or energy is refused rather than used.
2. Group the declared degradation mechanisms, rejecting an unrecognised
   one rather than ignoring it, and map each onto the parameter it is
   watched through. Append the shared stability objective whenever any
   mechanism is present.
3. With no mechanism declared, close there: the storage is not required
   and no chamber time is owed.
4. Size the acceleration from the two conditions -- the humidity term
   from the ratio raised to the exponent, the thermal term from the
   Arrhenius form -- and multiply them into one factor.
5. Convert the soak duration into equivalent ambient hours and divide
   by the ambient storage the project has to cover. A coverage landing
   exactly on the floor passes; the comparison tolerance absorbs
   representation error and the floor does not move.
6. Compare the planned parameters against the mechanism inventory and
   name every mechanism nobody planned to watch, not the first one.
7. Close on one verdict: storage not required, storage not planned,
   monitoring not planned, exposure insufficient, monitoring
   inadequate, or damp stability evidenced.

## Pitfalls

- Justifying the test by the mission environment. The cells fly in
  vacuum, and an argument built on orbit conditions collapses the first
  time anyone reads it; the storage and transport life is the case.
- Quoting the soak duration as the result. A thousand hours at an
  acceleration of one is a thousand hours of shelf life, and only the
  factor turns it into the year the project needs covered.
- Running the chamber warm but dry, or damp but cold. Both terms
  multiply, so dropping one of them costs most of the acceleration and
  the equivalent exposure falls with it.
- Carrying an exponent or an activation energy from another material
  set. They are declared assumptions; substituting them silently
  changes the equivalent hours by a large factor with no visible edit.
- Declaring a mechanism and recording nothing for it. The soak then
  produces a pass that says only that nobody looked, which reads in the
  record exactly like a pass that says the interface held.
- Comparing coverage against its floor by bare arithmetic. The factor
  is a product of a power and an exponential, and those land a few
  units in the last place either side of a limit on different hosts, so
  the comparison absorbs that error while the floor itself is never
  relaxed.

## Behavior contract (gate 3)

The policy validation, mechanism grouping and objective mapping, the
humidity and Arrhenius acceleration terms and their product, the
equivalent ambient hours and coverage ratio, the unwatched-mechanism
inventory and the purpose verdict are exercised by the gate 3 contract
test: scripts/test_e2008_solar_cell_humidity_test_purpose.py against
scripts/e2008_solar_cell_humidity_test_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_solar_cell_humidity_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
