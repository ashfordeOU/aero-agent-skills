---
name: e2008-diode-humidity-test-purpose
description: "Determine what a damp storage of protection diodes under ECSS-E-ST-20-08C clause 9.6.6.1.1 has to expose: group the moisture mechanisms that attack diode function, contact metallisation and protective coating onto the parameter each is read through, size the acceleration the chamber humidity and temperature buy over the declared store, convert the soak into the storage months it stands for, refuse conditions outside the range the model was fitted over, and decide whether the planned monitoring can see a mechanism move at all. Use when scoping or defending a protection diode damp storage before the chamber is booked. Trigger: ecss, e-st-20-08c-clause-9-6-6-1-1, protection-diode-damp-storage-purpose, diode-reverse-leakage-moisture-drift, diode-contact-metallisation-corrosion, diode-protective-coating-crazing, diode-damp-storage-equivalent-months."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-diode-humidity-test-purpose, protection-diode-damp-storage-purpose, diode-reverse-leakage-moisture-drift, diode-contact-metallisation-corrosion, diode-protective-coating-crazing, diode-damp-storage-equivalent-months]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Protection Diode Humidity Test Purpose (space-systems/ecss/e2008-diode-humidity-test-purpose)

Use when the task is to state and defend why protection diodes are put
through a damp storage under ECSS-E-ST-20-08C clause 9.6.6.1.1 -- what
weaknesses the exposure is meant to bring forward, how much store the
soak is worth, and whether anything planned can actually see them.

## Domain quick reference

- A protection diode spends far longer in a store, a transport case
  and an integration hall than it spends making power, and every one
  of those places is damp. The exposure brings the weaknesses that
  environment finds forward into a chamber, instead of leaving them to
  appear on an array that is already built.
- Three families of weakness are what the exposure is for. Function:
  moisture reaching the junction through the passivation, or sitting
  under the die attach, both of which drift an electrical parameter
  long before anything is visible. Contacts: corrosion of the contact
  metallisation and loss of adhesion at the terminal attachment, where
  the part still works and the joint no longer holds. Coatings:
  crazing or lifting of the protective layer, which is not a failure
  in itself but removes the barrier every other mechanism crosses.
- The coating family is the one most often left out, because nothing
  it does shows up electrically during the soak. It is also the one
  that decides how fast the other two proceed afterwards.
- The exposure is an accelerated stand-in, not a wait. Chamber
  humidity and temperature above the declared store buy a factor, and
  that factor times the soak is the storage the run is worth.
- A factor beyond the range the acceleration model was fitted over is
  not a bigger number, it is a number outside its own evidence. Above
  the humidity ceiling the part is under condensation rather than damp
  air, which is a different mechanism, not a faster one.
- A mechanism with no parameter reading it is one the chamber cannot
  report. The soak then passes in silence, and silence is recorded as
  a pass.
- Conditions being sound, monitoring being complete and the soak being
  long enough are three separate questions. An exposure can be sound
  and watched and still stand for a fraction of the required shelf
  life.

## Workflow

1. Validate the damp-storage policy first: acceleration floor, fitted
   ceiling, required storage months and the chamber temperature and
   humidity limits. A fitted ceiling at or below the floor is refused
   rather than used.
2. Group the declared moisture mechanisms, rejecting an unrecognised
   one rather than ignoring it, and map each to the parameter it is
   read through and the family it belongs to. Append the shared
   objective whenever any mechanism is present.
3. Decide whether the exposure is required at all: with no mechanism
   declared there is nothing for it to bring forward, and that is a
   distinct outcome from an exposure that is required and unplanned.
4. Size the acceleration factor from the chamber and store conditions,
   and convert the soak into equivalent storage months. Both are
   reported whatever the verdict, because they are what the exposure
   was wanted for.
5. Judge the conditions before anything else: inside the acceleration
   band the model supports, and inside the temperature and humidity
   the part may be held at in damp air.
6. Check monitoring coverage separately: a soak can be sound and blind
   at the same time.
7. Compare the equivalent months against the required storage life
   last, since a shortfall only means something once the conditions
   and the monitoring stand up.
8. Close on one verdict: exposure not required, exposure not planned,
   conditions unsound, monitoring blind, storage-life shortfall, or
   purpose served -- reporting every problem found, not only the first.

## Pitfalls

- Listing only the electrical mechanisms. The contact and coating
  families fail where no electrical parameter moves during the soak,
  and they are why the part is looked at as well as measured.
- Reading a large acceleration factor as a strong test. Past the
  fitted range the model has no evidence behind it, and the months it
  claims are arithmetic rather than a result.
- Pushing the chamber humidity towards saturation. Condensation is a
  different mechanism from damp air, so the run stops standing in for
  the store it was meant to represent.
- Sizing the exposure on duration. Hours in a chamber whose conditions
  are unstated buy no store at all; equivalent months are what the
  shelf-life requirement is written in.
- Declaring a mechanism and not measuring its parameter. The exposure
  then runs to completion and reports nothing, and nothing is filed as
  a pass.
- Collapsing soundness, coverage and sufficiency into one pass. They
  fail independently, and the repair for each is a different change to
  the test plan.

## Behavior contract (gate 3)

The policy validation, the humidity and thermal acceleration terms,
equivalent storage months, the mechanism inventory, family grouping
and objective mapping, monitoring coverage, the chamber condition
limits and the purpose verdict are exercised by the gate 3 contract
test: scripts/test_e2008_diode_humidity_test_purpose.py against
scripts/e2008_diode_humidity_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_humidity_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
