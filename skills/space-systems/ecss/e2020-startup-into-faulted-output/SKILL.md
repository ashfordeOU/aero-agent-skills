---
name: e2020-startup-into-faulted-output
description: "Evaluate whether a current limiter starts up correctly and stays inside its own ratings when an overload or a short circuit is already sitting on its output, under ECSS-E-ST-20C clause 5.2.7.5.1. Use when a power distribution unit is assessed against a declared downstream fault set: solve the start up operating point at the top of the current limit accuracy band, split the bus between the fault and the pass element, carry the dissipation into a junction temperature and into the energy held over the trip delay, then weigh each against its rating through a named tolerance. Trigger: ecss, e-st-20c-clause-5-2-7-5-1, limiter-start-up-into-fault, downstream-short-circuit-dissipation, pass-element-junction-temperature, current-limit-accuracy-band, trip-delay-pulse-energy."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-startup-into-faulted-output, e-st-20c-clause-5-2-7-5-1, limiter-start-up-into-fault, downstream-short-circuit-dissipation, pass-element-junction-temperature, current-limit-accuracy-band, trip-delay-pulse-energy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limiter Start Up Into a Faulted Output (space-systems/ecss/e2020-startup-into-faulted-output)

Use when the task is the clause 5.2.7.5.1 question of ECSS-E-ST-20C: the
overload or the short is already there before the limiter is turned on, and
the limiter still has to come up, limit, and survive its own trip delay
without leaving any of its ratings behind.

## Domain quick reference

- Starting into a fault is not the same event as a fault appearing on a
  running output. There is no settled operating point to leave; the
  element goes from off straight into limiting, so the worst dissipation
  arrives in the first instants and the trip delay is the whole of the
  exposure.
- The dissipation belongs to the pass element, not to the fault. The bus
  splits between the two: the fault holds the limited current times its
  own resistance, and the element holds the rest. A hard short therefore
  puts the entire bus voltage across the element and is the worst case,
  while a partial overload leaves some of the bus in the fault.
- A limiter that limits high is the one to size for. The current limit
  has an accuracy band, and the top of that band is what the element
  dissipates against, so the nominal limit understates the case.
- Three ratings answer three different questions and none of them
  substitutes for the others. Steady dissipation asks what the element
  can carry; junction temperature asks what the baseplate and the thermal
  resistance leave of that; pulse energy asks what the element survives
  over the hold, which is the trip delay unless the fault clears sooner.
- A declared load that never draws more than the limit does not exercise
  the clause at all. Its result is arithmetically clean and evidentially
  empty, which is why it is reported as a coverage finding rather than a
  pass.
- A hard short is a zero resistance case, so the prospective current is
  unbounded rather than large. It has to be carried as such and not as a
  division that fails.
- The accuracy band, the trip delay, the thermal resistance, the
  baseplate temperature and the short multiple are declared unit and
  project data rather than physical constants, so they are stated with
  the result.

## Workflow

1. Validate the limiter ratings, the bus and baseplate condition, and each
   declared fault, refusing a negative resistance, a zero trip delay or a
   junction rating below absolute zero.
2. For each fault, form the total downstream resistance from the fault and
   its harness, and the prospective current the bus would drive through it
   with no limiting at all.
3. Decide whether that pulls the limiter into limiting, comparing against
   the top of the current limit accuracy band rather than the nominal
   limit.
4. Split the bus: output voltage is the limited current through the
   downstream resistance, the element takes the remainder, and their
   product with the current is the element dissipation.
5. Take the hold time as the trip delay, shortened where the declared
   fault clears sooner, and carry the dissipation into a junction
   temperature and a pulse energy.
6. Weigh dissipation, junction temperature and pulse energy against their
   ratings, each through the named tolerance, so a case cut exactly to a
   rating is not decided by representation error.
7. Group the fault set, keep the worst case by junction temperature, and
   report a set carrying no hard short, or no overload short of one, as a
   coverage finding.

## Pitfalls

- Sizing the element on the nominal current limit. The accuracy band is
  declared precisely because the part does not limit at the nominal
  value, and the top of the band is the one that dissipates.
- Treating the hard short as the only case worth running. It is the worst
  for dissipation, but the partial overload is the one that can sit in
  limiting without ever reaching a trip threshold, so both belong in the
  set.
- Attributing the dissipation to the fault. The fault is downstream of
  the limit and takes only the limited current through its own
  resistance; what has to survive the event is the element upstream of
  it.
- Reading a steady dissipation rating as the whole answer. The junction
  arrives at the baseplate temperature plus the rise through the thermal
  resistance, and a part inside its power rating can still be outside its
  junction rating on a warm baseplate.
- Reporting a load inside the rating as a passed faulted start up. The
  limiter never limited, so the case measured a healthy turn on and says
  nothing about the clause.
- Comparing dissipation, junction temperature or pulse energy against its
  rating by bare arithmetic. Each is a product or difference of measured
  quantities, so a case cut exactly to a rating can be grouped inside it
  on one platform and outside it on another.

## Behavior contract (gate 3)

The rating, bus and fault validation with their refusals, the unbounded
prospective current of a zero resistance short, the current limit accuracy
band, the bus split between fault and pass element, the clamp that keeps
the element voltage non-negative, the hold time shortened by a clearing
fault, the junction temperature and pulse energy conversions, the three
rating comparisons through their named tolerances, the not-limiting
coverage finding and the missing-short and missing-overload set findings
are exercised by the gate 3 contract test:
scripts/test_e2020_startup_into_faulted_output.py against
scripts/e2020_startup_into_faulted_output_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_startup_into_faulted_output.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
