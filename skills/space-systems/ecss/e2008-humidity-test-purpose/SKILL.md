---
name: e2008-humidity-test-purpose
description: "Use when scoping or reviewing a solar-array coupon humidity test. Justify the humidity exposure applied to an assembled photovoltaic coupon under ECSS-E-ST-20-08C clause 5.5.1.4.1: group the assembly features that carry a moisture failure mode and turn each into the objective the exposure demonstrates, accumulate the predicted ground life of manufacture, storage, transport, integration and the launch campaign into one moisture load expressed as equivalent hours at reference humidity and temperature, decide whether that load and those features justify an exposure at all, then check the planned chamber conditions are wetter, warmer and longer than the ground environment they stand in for. Trigger: ecss, e-st-20-08c, clause-5-5-1-4-1, photovoltaic-assembly-humidity-exposure, solar-array-coupon-humidity-test, ground-environment-moisture-dose, bondline-adhesion-retention, pre-launch-storage-environment."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-humidity-test-purpose, photovoltaic-assembly-humidity-exposure, solar-array-coupon-humidity-test, ground-environment-moisture-dose, bondline-adhesion-retention, pre-launch-storage-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Humidity Test Purpose (space-systems/ecss/e2008-humidity-test-purpose)

Use when the task is to state and defend why a humidity exposure is
applied to an assembled photovoltaic coupon under ECSS-E-ST-20-08C
clause 5.5.1.4.1 -- what the exposure is meant to demonstrate, whether
the hardware and its ground life justify it, and whether the planned
chamber conditions actually stand in for the environment they represent.

## Domain quick reference

- A photovoltaic assembly works in vacuum, so damp heat is not a flight
  environment. The exposure is applied because the hardware reaches
  orbit through a long ground life: manufacture, storage, transport,
  integration and a launch campaign that can sit for months in a
  coastal climate. The purpose is to show the assembled components and
  the processes that joined them endure that realistic environment.
- The purpose is specific to what the assembly contains. An adhesive
  bondline, a coverglass adhesive, a silver interconnect
  metallization, a polyimide substrate, a hygroscopic encapsulant and
  a printed harness insulation each carry a different moisture failure
  mode, so each turns into a distinct objective the exposure
  demonstrates. Output-power retention is the objective every one of
  them shares.
- Ground segments held at different conditions are only comparable once
  they are reduced to a common measure. Humidity scales the load
  against a reference ratio and temperature multiplies it on a declared
  doubling interval, so the ground life becomes one number in
  equivalent hours that segments can be summed into.
- Justification is a joint condition. An assembly with no
  moisture-sensitive feature does not earn the exposure however damp
  its ground life is, and a genuinely dry, short ground life does not
  earn it however sensitive the assembly is.
- An exposure only serves its purpose when it bounds the environment it
  stands in for: at least as humid as the worst ground segment, at
  least as warm, and carrying at least the accumulated load times the
  coverage factor. A milder exposure demonstrates nothing about the
  environment it was bought to represent.
- A stated purpose is not a served purpose. An assembly that justifies
  the exposure but has no conditions planned yet is a distinct outcome
  from one whose planned conditions fall short, and the two carry
  different actions.

## Workflow

1. Validate the dose policy first: reference conditions, doubling
   interval, trigger and coverage factor. A coverage factor below unity
   would let the exposure fall short by construction and is refused.
2. Group the declared assembly features, rejecting an unrecognised one
   rather than ignoring it, and map each to the objective it makes the
   exposure demonstrate. Append the shared output-power objective when
   any sensitive feature is present.
3. Reduce every predicted ground segment to equivalent hours at the
   reference conditions, and accumulate them into one moisture load
   together with the worst humidity and the worst temperature the
   hardware sees on the ground.
4. Decide whether the exposure is justified: a moisture-sensitive
   feature present and an accumulated load at or above the trigger. A
   load that lands exactly on the trigger justifies the exposure; the
   comparison tolerance absorbs representation error and the trigger
   does not move.
5. When it is justified, check the planned chamber conditions bound the
   ground environment on all three counts, and report each count that
   falls short with its measured value and the value it owed.
6. Close on one verdict: not required, justified but not planned,
   planned but under bounds, or bounding the ground environment, with
   the objectives the exposure serves attached to it.

## Pitfalls

- Treating the exposure as a flight-environment test. Nothing on orbit
  is humid; a rationale written that way cannot survive a review, and
  it hides the ground phases that actually drive the requirement.
- Reading only the worst ground segment. A short spell at the launch
  site can be far less total moisture load than a year of nominally
  mild warehouse storage, and the fatigue-like accumulation is what the
  bondline responds to.
- Summing raw hours across segments. Hours at thirty five degrees and
  eighty five percent are not the same hours as at twenty degrees and
  forty percent, and adding them undercounts the load badly.
- Declaring the exposure not required because the assembly looks
  robust. The decision follows the declared feature inventory, so an
  undeclared bondline or metallization silently removes an objective
  the coupon was supposed to demonstrate.
- Calling a justified exposure satisfied because a chamber run happened.
  A run milder than the ground life it represents leaves the purpose
  unserved, and that is a finding rather than a pass.

## Behavior contract (gate 3)

The policy validation, per-segment moisture dose, ground-life
accumulation, feature inventory and objective mapping, bounding check
and purpose verdict are exercised by the gate 3 contract test:
scripts/test_e2008_humidity_test_purpose.py against
scripts/e2008_humidity_test_purpose_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_humidity_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
