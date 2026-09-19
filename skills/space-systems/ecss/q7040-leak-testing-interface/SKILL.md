---
name: q7040-leak-testing-interface
description: "Derive the leak-test requirement for a brazed pressurised assembly and pick a method that can actually see it. Use when a brazement encloses a pressurised volume and the loss the mission permits has to become an allowable throughput, a tracer-equivalent rate and a named test method. Turns the permitted pressure drop and enclosed volume into an allowable rate, rescales it between the service gas and the tracer by molar mass, computes the floor a pressure-decay rig reaches from its gauge resolution and test duration, refuses a method whose floor sits above that rate with margin, and grades a measured tracer reading. Trigger: ecss, q-st-70-40-brazing-scope, brazed-assembly-leak-rate, braze-allowable-throughput, helium-equivalent-leak-rate, pressure-decay-detection-floor, braze-leak-test-method-selection, leak-tracer-species-conversion."
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
  tags: [ecss, q-st-70-40-brazing-scope, q7040-leak-testing-interface, brazed-assembly-leak-rate, braze-allowable-throughput, helium-equivalent-leak-rate, pressure-decay-detection-floor, braze-leak-test-method-selection, leak-tracer-species-conversion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — Leak Testing of Pressurised Brazements (space-systems/ecss/q7040-leak-testing-interface)

Use when the task is the leak test a brazed pressurised assembly owes
at inspection -- turning the loss the mission can tolerate into an
allowable throughput, expressing that rate in the tracer the test will
actually use, and choosing a method whose detection floor sits far
enough below it to mean something.

## Domain quick reference

- The requirement comes from the mission, not from the catalogue. The
  pressure the assembly may lose, the volume it encloses and the time
  it has to hold together fix an allowable throughput; every method
  choice afterwards is judged against that number.
- Throughput is the currency, not pressure. A rate in pressure times
  volume per unit time is what a leak detector reports and what a
  budget can be summed in, so the permitted pressure drop is
  multiplied by the enclosed volume and divided by the hold time
  before anything else happens.
- The tracer is not the service gas, and the rate is not the same
  number. Through a small brazing defect the flow is molecular, so a
  rate scales with the inverse square root of the molar mass: a
  helium reading is roughly two and a half times the nitrogen rate
  through the same path. Quoting a helium figure against a service-gas
  budget overstates the leak; quoting it the other way hides one.
- The conversion has to be reciprocal. Converting a rate to the tracer
  and back must return the original number, because the same physical
  path is being described twice; a conversion table that does not
  close is a sign the molar masses or the direction were mixed up.
- A pressure-decay rig has a floor it cannot beat. The smallest rate
  it can see is its gauge resolution times the enclosed volume divided
  by the test duration, so a large volume or a short test raises the
  floor, and the answer is a longer test or a finer gauge, not a
  longer stare at the display.
- The method needs margin over the requirement, not equality with it.
  A detector whose floor equals the allowable rate can only say the
  leak is somewhere near the limit, so the floor is required to sit a
  declared factor below it before the method is accepted.
- The least onerous adequate method wins. Immersion and pressure decay
  are cheap and coarse; a tracer sniffer and a vacuum hood are
  sensitive and slow. The selection walks from cheap to sensitive and
  stops at the first method with the margin, and a floor sitting
  exactly on the required value counts as adequate because both sides
  are floating-point products of measured quantities.

## Workflow

1. Normalise the assembly: permitted pressure drop, enclosed volume,
   hold time, service gas, tracer gas and the detection margin the
   programme declares. Reject an unrecognised gas or a non-positive
   quantity rather than defaulting it.
2. Compute the allowable throughput in the service gas from the drop,
   the volume and the time.
3. Rescale that rate into the tracer by the square root of the molar
   mass ratio, and keep both numbers: the service-gas budget and the
   tracer-equivalent figure the operator will read.
4. Where a pressure-decay rig is a candidate, compute its detection
   floor from the gauge resolution, the volume and the test duration
   before believing its catalogue sensitivity.
5. Walk the methods from least to most onerous and take the first
   whose floor sits at or below the tracer-equivalent rate divided by
   the margin. Report that no method qualifies rather than accepting
   one that does not.
6. Where a measured tracer rate exists, convert it back into the
   service gas and grade it against the allowable throughput, with the
   comparison absorbing representation error at the limit.

## Pitfalls

- Comparing a helium reading straight against a nitrogen budget. The
  same defect passes helium far faster, so the assembly is failed on
  arithmetic rather than on leakage, and a genuinely marginal joint is
  lost in the noise of the unconverted numbers.
- Taking a detector's catalogue sensitivity as the rig's floor. The
  floor of a pressure-decay measurement is set by the gauge, the
  volume and the clock; a large plenum tested for ten minutes cannot
  reach the number on the datasheet whatever the gauge can resolve.
- Requiring only that the floor be below the allowable rate. With no
  margin the reading has no resolution at the decision point, so every
  result lands as marginal and the disposition falls back to opinion.
- Forgetting that the allowable rate falls as the mission lengthens.
  The same assembly qualified for a short flight is not qualified for
  a long one, because the permitted drop is spread over a longer hold.
- Grading a measured rate against the limit by bare arithmetic. Both
  sides are products and quotients of measured quantities, so a rate
  placed deliberately on the limit can read a few units in the last
  place above it and a compliant assembly is reported as leaking.

## Behavior contract (gate 3)

Allowable throughput, the molar-mass species conversion and its
reciprocity, the pressure-decay detection floor, method selection
against the declared margin and the measured-rate verdict are exercised
by the gate 3 contract test:
scripts/test_q7040_leak_testing_interface.py against
scripts/q7040_leak_testing_interface_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q7040_leak_testing_interface.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
