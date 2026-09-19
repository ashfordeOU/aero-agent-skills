---
name: e3311-shielding-faraday-cap-safety-cap
description: "Verify the electromagnetic shielding and the protective caps on an initiator circuit against ECSS-E-ST-33-11C clauses 4.10.3 to 4.10.5. Attenuate an incident field through the declared shield, compare the pickup that reaches the bridgewire with the no-fire power, and return the shield effectiveness the required margin actually asks for. Audit the Faraday cap for the pin-to-pin and pin-to-case shorts a demated connector needs, and walk an ordered ground operation sequence for a safety cap removed before its authorised point or left off through an interruption. Use when reviewing initiator electromagnetic protection. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, initiator-circuit-em-shielding, eed-faraday-cap-shorting, eed-safety-cap-sequence, shield-effectiveness-no-fire-margin, initiator-rf-pickup-power."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-shielding-faraday-cap-safety-cap, initiator-circuit-em-shielding, eed-faraday-cap-shorting, eed-safety-cap-sequence, shield-effectiveness-no-fire-margin, initiator-rf-pickup-power]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Shielding, Faraday Cap and Safety Cap (space-systems/ecss/e3311-shielding-faraday-cap-safety-cap)

Use when the electromagnetic protection of an initiation circuit is being
designed or reviewed under ECSS-E-ST-33-11C clauses 4.10.3 to 4.10.5 — the
shield on the installed circuit, the Faraday cap on the demated one, and the
safety cap across the ground operation that connects them.

## Domain quick reference

- Three protections, three different states, and no one of them covers
  another. The shield covers the mated installed circuit, the Faraday
  cap covers the connector once the harness comes off, and the safety
  cap covers the operation in between.
- The bound here is the no-fire power, not the all-fire current. This is
  the safety argument: the most energy that must never reach the
  bridgewire. Reaching for the functional bound inverts the conclusion.
- Shielding is in decibels and pickup is in watts, and the conversion is
  the step that gets dropped. Power divides by ten per ten decibels and
  field strength by ten per twenty; mixing the two loses a factor of a
  hundred in either direction.
- The number that goes on a drawing is the required shield
  effectiveness, not the margin. A review that reports a shortfall in
  decibels of margin has left the reader to do the one calculation the
  analysis was for.
- A demated initiator is an antenna with a bridgewire across it. The
  Faraday cap has to short pin to pin and pin to case; one without the
  other leaves either a loop or a potential.
- The safety cap is checked against a sequence, not a state. It is
  fitted from receipt to an authorised removal point late in the flow,
  and it goes back on whenever the sequence is interrupted after that
  point. No static margin calculation can see that.
- An undeclared protective feature is an absent one. On an initiation
  circuit the assumption is never given the benefit of the doubt.

## Workflow

1. State the worst-case incident power the circuit is exposed to, the
   declared shield effectiveness, the initiator no-fire power, and the
   margin the project requires between them.
2. Attenuate the incident power through the shield in the power domain,
   and keep the field-domain factor separate so a field-strength limit
   is never divided by the power factor.
3. Compare the pickup that reaches the bridgewire with the no-fire
   power, and separate the two failure modes: pickup above the no-fire
   power is a circuit that can be set off, pickup below it but inside
   the margin is a circuit short of margin.
4. Report the margin in decibels with an absolute tolerance, because
   decibels come from a logarithm that is not correctly rounded and two
   build hosts can otherwise disagree at the bound.
5. Return the shield effectiveness the margin asks for, and check that
   recommendation back through the same attenuation.
6. Audit the Faraday cap for both shorts and for being fitted whenever
   the connector is demated, treating an undeclared property as absent.
7. Walk the ordered ground operation sequence against the authorised
   removal point: the cap fitted at every earlier step, and refitted for
   any interruption after it.
8. Rank the findings. A circuit that can be set off outranks a cap
   defect, and a cap defect outranks a shortfall in margin.

## Pitfalls

- Grading pickup against the all-fire current. That is the functional
  bound and it is larger; the safety case runs on the no-fire power.
- Converting decibels with the wrong divisor. Twenty for field, ten for
  power, and a swap is a factor of a hundred in the answer.
- Reporting a margin shortfall without the shield effectiveness that
  fixes it. The inverse is one line of the same arithmetic, and omitting
  it sends the problem back round the loop.
- Treating a shield as covering the demated case. With the harness off
  there is no shielded loop, only an initiator with exposed pins, and
  that is the Faraday cap's job.
- Shorting pin to pin but not pin to case. The bridgewire loop is closed
  and the whole connector still floats to a potential the case does not.
- Checking the safety cap as a state at one moment. It is a property of
  the whole ground sequence, and the failure is almost always a removal
  one step too early or a cap not refitted after a hold.
- Deciding the margin with a bare comparison at the bound. Use an
  absolute decibel tolerance so a design that lands exactly on the
  margin is graded the same everywhere.

## Behavior contract (gate 3)

Power, decibel and declaration validation, the power and field
attenuation factors and their consistency, the shielded pickup, the
no-fire margin including the unbounded case with no incident field, the
required-shield inverse re-checked through the same attenuation, the
Faraday cap requirements, the ordered safety cap sequence with its
authorised removal point and interruption rule, and the ranking of
verdicts are exercised by the gate 3 contract test:
scripts/test_e3311_shielding_faraday_cap_safety_cap.py against
scripts/e3311_shielding_faraday_cap_safety_cap_logic.py (stdlib
unittest, offline).
Run:
python3 scripts/test_e3311_shielding_faraday_cap_safety_cap.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
