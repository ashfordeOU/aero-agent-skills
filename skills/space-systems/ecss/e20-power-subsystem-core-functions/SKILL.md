---
name: e20-power-subsystem-core-functions
description: "Use when verify that a spacecraft electrical power subsystem covers its five core functions under ECSS-E-ST-20C clause 5.2.2.1: map every declared element (solar-array, regulator, battery, distribution unit, sensor) onto the generation, conditioning, storage, distribution and monitoring functions it performs, flag any core function left without an element, confirm every energy-carrying element is observable in telemetry, check redundancy unless a single-string architecture is explicitly accepted, and compute the power delivered to the loads through the conditioning and distribution efficiencies. Flags an unallocated core function, an unobservable element, an uncategorized element type and an undeclared single-string function. Trigger: ecss, e-st-20-electrical-scope, power-subsystem-core-functions, power-generation-function, power-conditioning-function, energy-storage-function, power-distribution-function, power-monitoring-function."
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
  tags: [ecss, e-st-20-electrical-scope, e20-power-subsystem-core-functions, power-generation-function, power-conditioning-function, energy-storage-function, power-distribution-function, power-monitoring-function]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Power Subsystem Core Functions (space-systems/ecss/e20-power-subsystem-core-functions)

Use when the task is proving that an electrical power subsystem
actually performs what ECSS-E-ST-20C clause 5.2.2.1 requires of it --
generating, conditioning, storing, distributing and monitoring the
spacecraft's energy -- by tracing each of those five capabilities down
to declared elements rather than to an architecture diagram.

## Domain quick reference

- Clause 5.2.2.1 is written in terms of capability, not hardware. It
  names five functions the subsystem must perform: generation (turning
  a primary source into electrical power), conditioning (regulating
  that raw output onto a usable bus), storage (holding energy so the
  bus survives eclipse, launch and any period without generation),
  distribution (routing power to the consumers with protection), and
  monitoring (making the state of the whole chain observable in
  telemetry). An architecture satisfies the clause only when every one
  of the five traces to at least one real element.
- Elements and functions are many-to-many. A solar array performs one
  function; a combined conditioning and distribution unit performs
  three; a fuel cell both generates and stores. Mapping one element to
  exactly one function is the most common way a real gap gets hidden,
  because the combined unit is booked against distribution and its
  conditioning role is then assumed to be someone else's.
- Monitoring is a function over the other four, not a peer of them.
  Every element that carries energy -- generating, conditioning,
  storing, distributing -- has to be observable, and the check is
  whether a monitoring element reports it, not whether a sensor exists
  somewhere in the subsystem. A purely monitoring element is the
  observer and is not itself an object of this check.
- Redundancy is an architectural decision, not an automatic
  requirement. A function carried by exactly one element is a real
  risk concentration, so it is flagged unless single-string operation
  for that function has been explicitly accepted and recorded. Silence
  is not acceptance.
- The chain is lossy end to end. Power reaching the loads is the
  generated power through the conditioning efficiency and then the
  distribution efficiency; quoting source output as though it were
  load-available power overstates the subsystem by the whole
  conversion loss.

## Workflow

1. Declare every subsystem element as an identifier plus an element
   type. Reject an uncategorized type before it enters the review -- an
   unmapped element contributes no function and silently leaves a gap.
2. Build the coverage map: for each element, add its identifier under
   every core function its type performs. Reject a blank or duplicated
   identifier, which would double-count a unit.
3. List the core functions with no element and raise one finding per
   unallocated function.
4. For each covered function carried by exactly one element, check the
   accepted single-string list; raise a finding when the function is
   not on it.
5. For each energy-carrying element, check it appears in the monitored
   set; raise a finding for any that does not. Reject a monitored
   identifier that is not a declared element -- it points at telemetry
   for hardware the subsystem does not have.
6. Compute the delivered power: generated power x conditioning
   efficiency x distribution efficiency, and the conversion loss
   against the generated figure.
7. Aggregate the allocation, redundancy and monitoring findings; the
   subsystem is not clause-5.2.2.1 compliant until all three lists are
   empty.

## Pitfalls

- Reading a populated block diagram as coverage. The clause is
  satisfied by elements that perform the function, and a diagram with
  a labelled box but no declared element leaves the function
  unallocated.
- Booking a multi-function unit against a single function, then
  treating the others as covered. The conditioning and distribution
  unit performs both; mapping it to distribution alone makes a real
  conditioning gap invisible.
- Counting a sensor's presence as monitoring coverage. Coverage is
  per element observed, not per sensor owned -- a subsystem with two
  current sensors and an unreported battery still has an unobservable
  energy store.
- Treating an undiscussed single-string function as accepted. The
  finding exists so the risk is recorded and signed, and clearing it
  requires a decision, not an omission.
- Quoting generated power as available power. The conditioning and
  distribution efficiencies are multiplicative, so a 0.90 and 0.95
  chain returns about 85% of source output to the loads and the
  missing 15% is real dissipation the thermal design has to take.

## Behavior contract (gate 3)

The element-to-function mapping, coverage, allocation, redundancy,
monitoring-observability and chain-efficiency logic is exercised by
the gate 3 contract test:
scripts/test_e20_power_subsystem_core_functions.py against
scripts/e20_power_subsystem_core_functions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_power_subsystem_core_functions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
