---
name: e2008-blocking-diode-humidity-purpose
description: "Use when scoping or defending a blocking diode damp storage before the chamber is booked. Determine what a damp storage of blocking diodes under ECSS-E-ST-20-08C clause 12.6.4.1.1 has to expose: group the moisture mechanisms that attack junction function, terminal contacts and protective coating onto the parameter each is read through and the duty each threatens, size the acceleration the chamber humidity and temperature buy over the declared store, convert the soak into the storage months it stands for, refuse a factor outside the range the model was fitted over, and judge the leakage monitoring bias against the bus voltage the part has to stand off. Trigger: ecss, e-st-20-08c-clause-12-6-4-1-1, blocking-diode-damp-storage-purpose, blocking-diode-reverse-leakage-moisture-path, blocking-diode-terminal-metallisation-corrosion, blocking-diode-protective-coating-crazing, blocking-diode-monitoring-bias-adequacy."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-blocking-diode-humidity-purpose, blocking-diode-damp-storage-purpose, blocking-diode-reverse-leakage-moisture-path, blocking-diode-terminal-metallisation-corrosion, blocking-diode-protective-coating-crazing, blocking-diode-monitoring-bias-adequacy, blocking-diode-damp-storage-equivalent-months]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Blocking Diode Humidity Test Purpose (space-systems/ecss/e2008-blocking-diode-humidity-purpose)

Use when the task is to state and defend why blocking diodes are put
through a damp storage under ECSS-E-ST-20-08C clause 12.6.4.1.1 --
what weaknesses the exposure is meant to bring forward, how much store
the soak is worth, and whether anything planned can actually see them.

## Domain quick reference

- A blocking diode spends far longer in a store, a transport case and
  an integration hall than it spends carrying a string, and every one
  of those places is damp. The exposure brings the weaknesses that
  environment finds forward into a chamber, instead of leaving them to
  appear on an array that is already built.
- Three families of weakness are what the exposure is for. Function:
  moisture reaching the junction through the passivation, or sitting
  under the die attach, both of which drift an electrical parameter
  long before anything is visible. Contacts: corrosion of the terminal
  metallisation and loss of adhesion at the attachment, where the part
  still works and the joint no longer holds. Coatings: crazing or
  lifting of the protective layer, which is not a failure in itself
  but removes the barrier every other mechanism crosses.
- The duty that makes this part a blocking diode is standing off the
  bus while reverse biased, and the mechanism that ends that duty is a
  leakage path grown through wet passivation. Which is why the family
  grouping is carried alongside the duty each mechanism threatens: a
  coating finding and a leakage finding are not the same loss.
- A leakage path is only visible at the bias it opens under. A
  measurement taken at a fraction of the working bus voltage can
  report a clean part while the path that matters is already there,
  so the monitoring bias is judged against the duty bias rather than
  merely recorded next to it.
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
- Conditions being sound, monitoring being present, monitoring being
  biased hard enough and the soak being long enough are four separate
  questions. An exposure can be sound and watched and correctly biased
  and still stand for a fraction of the required shelf life.

## Workflow

1. Validate the damp-storage policy first: acceleration floor, fitted
   ceiling, required storage months, the chamber temperature and
   humidity limits and the monitoring bias floor. A fitted ceiling at
   or below the floor is refused rather than used.
2. Group the declared moisture mechanisms, rejecting an unrecognised
   one rather than ignoring it, and map each to the parameter it is
   read through, the family it belongs to and the duty it threatens.
   Append the shared objective whenever any mechanism is present.
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
6. Check monitoring coverage next: a soak can be sound and blind at
   the same time, and two coating mechanisms sharing one reading means
   one gap silences both.
7. Check the monitoring bias only where a declared mechanism is read
   through it. With no leakage mechanism on the list the bias is not a
   finding, and inventing one there is noise.
8. Compare the equivalent months against the required storage life
   last, since a shortfall only means something once the conditions
   and the monitoring stand up.
9. Close on one verdict: exposure not required, exposure not planned,
   conditions unsound, monitoring blind, monitoring under-biased,
   storage-life shortfall, or purpose served -- reporting every
   problem found, not only the first.

## Pitfalls

- Recording the monitoring bias without grading it. A leakage read at
  a small fraction of the bus voltage is a blind probe wearing the
  name of a measurement, and it passes every part put in front of it.
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
- Collapsing soundness, coverage, bias and sufficiency into one pass.
  They fail independently, and the repair for each is a different
  change to the test plan.

## Behavior contract (gate 3)

The policy validation, the mechanism catalogue with its families,
parameters and threatened duties, the objective mapping, the
monitoring coverage gaps, the bias-coverage fraction and the
mechanisms that need it, the humidity and thermal acceleration terms,
equivalent storage months, the chamber condition limits and the
purpose verdict are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_humidity_purpose.py against
scripts/e2008_blocking_diode_humidity_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_humidity_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
