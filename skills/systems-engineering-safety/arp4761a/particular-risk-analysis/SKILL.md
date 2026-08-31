---
name: particular-risk-analysis
description: "Use when you must perform or review a particular risk analysis (PRA) per ARP4761A: quantify the probability of a single-event risk (rotor burst, tire burst, bird strike, fire, lightning), combine it with the conditional probability that the hazard leads to a failure condition, and assess hazard zone containment, separation, and redundant routing mitigations. Produces event-exposure probabilities, combined failure-condition probabilities, and zone verdicts for the safety assessment. Trigger: particular risk analysis, rotor burst, tire burst, bird strike, containment, hazard zone, arp4761a, pra."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [particular-risk-analysis, arp4761a, rotor-burst, tire-burst, bird-strike, containment, hazard-zone, pra]
  version: 0.1.0
  author: AeroSkills
---

# ARP4761A Particular Risk Analysis (systems-engineering-safety/arp4761a/particular-risk-analysis)

Use when the task is a particular risk analysis (PRA) per ARP4761A: a
single event that can affect the aircraft or a system as a whole, its
probability and consequences, and the zone mitigations that keep
protected equipment safe.

## Domain quick reference

- PRA covers single-event risks that are not internal system
  failures: rotor burst, tire burst, bird strike, fire, and lightning.
- Each event has a probability per flight hour; exposure over the
  relevant flight time gives the probability that the event occurs at
  all during that exposure.
- The analysis combines the event probability with the conditional
  probability that the hazard created by the event damages a system,
  producing the failure-condition probability contribution.
- Equipment is grouped in hazard zones; containment, separation, and
  redundant routing keep protected zones outside the hazard zone.
- PRA results feed the system safety assessment and close against
  the failure-condition probability requirements for the severity
  class.

## Workflow

1. List the applicable particular events (rotor burst, tire burst,
   bird strike, fire, lightning) and their probability per flight
   hour.
2. Compute the event exposure probability over the exposure time
   with exposure_probability.
3. For each hazard created by the event, combine the event
   probability with the conditional probability of the failure
   condition using conditional_probability.
4. Map equipment to zones and check hazard zone overlap with the
   protected zones using containment_verdict.
5. Add mitigation (containment, separation, redundant routing) where
   the verdict is action, then reassess the zone.
6. Roll the contributions into the safety assessment and verify the
   failure-condition probability budget closes.

## Pitfalls

- Using the event probability alone and skipping the conditional
  probability that the hazard actually reaches the system.
- Treating containment as absolute when the hazard zone still
  overlaps a protected zone.
- Missing events that originate outside the system under analysis
  (tires, engine rotors, birds, fire, lightning).
- Double counting a failure condition already covered by the fault
  tree or zonal safety analysis.

## Behavior contract (gate 3)

The probability combination, exposure, and zone verdict logic is
exercised by the gate 3 contract test:
scripts/test_particular_risk_analysis.py against
scripts/particular_risk_analysis_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_particular_risk_analysis.py

## Compliance

- Standards referenced, not reproduced: ARP4761A text is
  proprietary (SAE); summary-only per standards-map.yaml and
  brief 06.
- compliance: STANDARDS-REF, gated: false.
