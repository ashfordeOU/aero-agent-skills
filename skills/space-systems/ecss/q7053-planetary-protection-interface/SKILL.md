---
name: q7053-planetary-protection-interface
description: "Support the planetary-protection case a sterilization-compatibility test has to serve, across the ECSS-Q-ST-70-53C interface to the microbial-reduction standards ECSS-Q-ST-70-56C and ECSS-Q-ST-70-57C. Use when a bioburden allocation has to be met by a process the hardware is only qualified to survive inside a known envelope. Corrects the reference decimal-reduction time to the temperature or the sterilant concentration actually used, converts the exposure into a log reduction and a surviving spore count, compares that count with its allocation, derives the exposure the target reduction needs, and reports every required process parameter sitting outside the compatibility-qualified envelope. Trigger: ecss, q-st-70-53-sterilization-compatibility-scope, planetary-protection-bioburden-interface, decimal-reduction-time-correction, microbial-log-reduction, surviving-spore-allocation, compatibility-qualified-process-envelope."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-planetary-protection-interface, planetary-protection-bioburden-interface, decimal-reduction-time-correction, microbial-log-reduction, surviving-spore-allocation, compatibility-qualified-process-envelope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Planetary Protection Interface (space-systems/ecss/q7053-planetary-protection-interface)

Use when the task is the interface between an ECSS-Q-ST-70-53C
compatibility test and the planetary-protection case — showing that the
microbial reduction the mission needs can be obtained by a process the
hardware has actually been qualified to survive.

## Domain quick reference

- The two standards ask opposite questions of the same cycle.
  ECSS-Q-ST-70-56C and ECSS-Q-ST-70-57C ask how much bioburden the
  exposure removes; ECSS-Q-ST-70-53C asks how much of the hardware
  survives it. A cycle that satisfies one and not the other is not a
  solution, and the interface is where that is caught.
- The decimal-reduction time is a property of the organism at a stated
  condition, not a constant. For dry heat it moves with temperature
  through the z-value; for a vapour-phase process it moves with
  sterilant concentration. Using the reference value at the condition
  actually run overstates or understates the reduction by orders of
  magnitude.
- Reduction is logarithmic, so the surviving count is the initial count
  scaled by ten to the minus the number of decimal reductions achieved.
  It never reaches zero, which is why the allocation is a spore count
  and not a claim of sterility.
- The compatibility-qualified envelope is a ceiling on the process, not
  a target. Every parameter the planetary-protection process asks for —
  peak temperature, sterilant concentration, cycle count, accumulated
  exposure — has to sit inside what the compatibility test actually
  demonstrated, and a parameter the envelope never covered is outside
  it, not inside by default.
- When the allocation cannot be met inside the envelope the answer is
  not a longer cycle. It is a re-qualification of the material at the
  harder condition, a different process, or a different bioburden
  allocation, and the interface report says which of those is needed.

## Workflow

1. Validate the process kind and its parameters: a positive reference
   decimal-reduction time, a positive reference condition, a positive
   achieved condition, and a positive sensitivity coefficient.
2. Correct the decimal-reduction time to the condition actually run —
   the z-value relation for dry heat, the concentration-coefficient
   relation for a vapour-phase process.
3. Divide the accumulated exposure by the corrected decimal-reduction
   time to get the log reduction achieved.
4. Scale the initial spore count by ten to the minus that reduction to
   get the surviving count, and compare it with the allocation,
   absorbing representation error at the boundary with a named
   tolerance.
5. Where a target reduction is declared, derive the exposure it needs
   at the corrected decimal-reduction time and report the shortfall.
6. Compare every required process parameter with the
   compatibility-qualified envelope; report a parameter over its
   qualified ceiling and a parameter the envelope does not cover at all.
7. Report the conclusion: allocation met inside the envelope, or the
   specific reason it is not.

## Pitfalls

- Using the reference decimal-reduction time at a different condition.
  A twenty-degree drop against a twenty-one-degree z-value is a factor
  of about ten in the time needed, which turns a passing cycle into a
  failing one.
- Claiming sterility. The output is a surviving spore count against an
  allocation; a logarithmic reduction has no zero.
- Reading a parameter the qualified envelope never mentions as
  acceptable. An uncovered parameter is outside the envelope and needs
  qualification, not a silent pass.
- Extending the exposure to close a shortfall without re-checking the
  envelope. Accumulated exposure is itself a qualified parameter, and
  lengthening the cycle is the fastest way to leave the envelope.
- Grading the reduction and the compatibility separately and stopping
  there. The interface exists because only the intersection of the two
  is a usable process.

## Behavior contract (gate 3)

The parameter validation, decimal-reduction-time correction for both
process kinds, log-reduction and surviving-count arithmetic, allocation
comparison, required-exposure derivation and qualified-envelope
comparison are exercised by the gate 3 contract test:
scripts/test_q7053_planetary_protection_interface.py against
scripts/q7053_planetary_protection_interface_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7053_planetary_protection_interface.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
