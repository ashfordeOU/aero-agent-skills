---
name: e3311-electrical-requirements
description: "Verify the electrical design of an explosive initiation circuit against ECSS-E-ST-33-11C clause 4.8.2. Use when the task is screening every path that can put energy into a bridgewire: grading the worst-case stray current against the no-fire current, converting a radio-frequency field into pickup voltage and delivered power and comparing it with the no-fire power, sizing an electrostatic discharge as stored energy and grading it pin-to-pin and pin-to-case, checking that coupled nuclear-pulse energy leaves the required margin and that an immunity demonstration exists, and confirming the firing-line wiring carries every declared control. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, electro-explosive-no-fire-margin, stray-current-no-fire-screen, eed-rf-immunity-margin, eed-esd-withstand-energy, nemp-initiation-immunity, firing-line-wiring-integrity."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-electrical-requirements, electro-explosive-no-fire-margin, stray-current-no-fire-screen, eed-rf-immunity-margin, eed-esd-withstand-energy, nemp-initiation-immunity, firing-line-wiring-integrity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Electrical Requirements (space-systems/ecss/e3311-electrical-requirements)

Use when the task is the electrical screen of ECSS-E-ST-33-11C clause
4.8.2 -- showing that no path available to the flight environment, the
platform harness or the ground support equipment can put firing-level
energy into an electro-explosive device before the device is meant to
fire.

## Domain quick reference

- An electro-explosive device is a resistor that detonates, so every
  electrical requirement on it reduces to one question asked along
  several paths at once: how much energy can reach the bridgewire, and
  how far below the level that initiates it does that energy sit.
- The screening quantities are the no-fire current, the no-fire power
  and the electrostatic withstand energy. The first two are what the
  device tolerates indefinitely without initiating; the third is what
  it tolerates as a single discharge, and it is declared separately
  pin-to-pin and pin-to-case because the two paths run through
  different insulation.
- Stray current is graded as a fraction of the no-fire current rather
  than in decibel, because the quantity the circuit analysis produces
  is a current and the allowance is conventionally a percentage. A
  margin in decibel is still reported so the result can be compared
  with the radio-frequency and pulse paths.
- Radio-frequency pickup is a two-step computation, not a lookup. The
  field and the effective length of the firing-line pair give an
  open-circuit voltage; that voltage into a matched bridgewire load
  gives the delivered power; only then is there something to compare
  with the no-fire power.
- An electrostatic discharge is sized from the source, not the device:
  the stored energy of the charged body sets what arrives, and the
  device's declared withstand sets what is survivable. The ratio of
  the two is the margin, and it is taken per path.
- A nuclear-pulse margin computed from a coupling estimate is not the
  same as a demonstrated immunity. Both are recorded, and a missing
  demonstration is a finding even when the arithmetic is comfortable.
- Wiring integrity is a checklist rather than a number, but it is a
  closed one: an undeclared control is a gap in the evidence, not an
  implicit pass.

## Workflow

1. Fix the two device quantities everything else is graded against --
   the no-fire current and the no-fire power -- and reject a case that
   supplies neither, because every margin below is a ratio to them.
2. Grade the worst-case stray current. Take the allowance as the
   declared fraction of the no-fire current, report the shortfall in
   both amperes and decibel, and treat a case sitting exactly on the
   allowance as compliant rather than failing it on representation
   error.
3. Work the radio-frequency path through in order: field times
   effective length for the induced voltage, that voltage into the
   matched bridgewire for the delivered power, then the power margin
   against the policy requirement.
4. Size the electrostatic discharge from the source capacitance and
   voltage, then grade the pin-to-pin and pin-to-case withstands
   separately. Reject a case that declares only one path; the missing
   one is the one that usually fails.
5. Grade the coupled nuclear-pulse power against the same power margin
   and record whether an immunity demonstration backs it.
6. Walk the firing-line wiring controls and name each one that is
   absent, then close with the overall verdict and the list of paths
   that produced it.

## Pitfalls

- Grading stray current against the all-fire level instead of the
  no-fire level. The all-fire current is what the circuit must deliver
  on command; the no-fire current is what everything else must stay
  under, and the gap between them is the whole safety case.
- Comparing a field strength directly with a no-fire power. They are
  not the same kind of quantity, and skipping the pickup computation
  hides the two parameters that actually drive the answer: how long
  the firing-line pair is and what the bridgewire looks like as a
  load.
- Taking one electrostatic withstand figure as covering both paths.
  Pin-to-case runs through the device housing insulation and is
  routinely the weaker of the two, so a single number quoted for the
  device grades the path that was never the concern.
- Reading a comfortable nuclear-pulse margin as immunity. The margin
  is only as good as the coupling estimate behind it, and an estimate
  with no test behind it is an assumption with a decimal point.
- Treating an undeclared wiring control as satisfied. The control set
  is closed, so a silent entry means nobody looked, and a firing line
  that is not shorted until arm fails in exactly the configuration
  nobody inspected.
- Comparing margins by bare arithmetic. Each one is a ratio or a
  difference of logarithms, so a design sitting exactly on its
  requirement can land a few units in the last place below it; the
  comparison absorbs that while the requirement stays untouched.

## Behavior contract (gate 3)

The stray-current allowance, radio-frequency pickup chain,
electrostatic per-path grading, nuclear-pulse margin and demonstration
check, wiring-control walk and overall verdict are exercised by the
gate 3 contract test:
scripts/test_e3311_electrical_requirements.py against
scripts/e3311_electrical_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3311_electrical_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
