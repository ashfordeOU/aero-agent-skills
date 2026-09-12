---
name: e20-electrical-subsystem-safety-conformance
description: "Use when assess whether a payload or electrical subsystem conforms to the space product assurance safety requirements invoked by ECSS-E-ST-20C clause 5.9: categorize each electrical hazard into its family, derive the severity band from the credible worst-case consequence, translate that band into a failure tolerance and the count of independent monitored inhibits the design must carry, compute the charge a stored-energy source still holds when the bleed period ends and compare it against the safe touch voltage and the safe energy limit, and confirm every hazard closes on a recognized verification method with a traceable record. Trigger: ecss, e-st-20-electrical-scope, electrical-subsystem-safety-conformance, electrical-hazard-severity, failure-tolerance-inhibits, independent-inhibit-count, capacitor-bleed-down, safe-touch-voltage, hazard-closure-record, product-assurance-safety-linkage."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electrical-subsystem-safety-conformance, electrical-hazard-severity, failure-tolerance-inhibits, independent-inhibit-count, capacitor-bleed-down, safe-touch-voltage, hazard-closure-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Electrical Subsystem Safety Conformance (space-systems/ecss/e20-electrical-subsystem-safety-conformance)

Use when the task is the clause 5.9 safety linkage of ECSS-E-ST-20C --
showing that a payload or an electrical subsystem answers to the space
product assurance safety standard, so the electrical design is argued
against its hazards and not only against its own performance
requirements.

## Domain quick reference

- Every electrical hazard is categorized once into a family:
  shock and touch (an exposed live conductor, an insulation breakdown
  to chassis, a fault returning through an unintended path), stored
  energy (a bulk capacitor still holding charge, inductive flyback, a
  high voltage filter bank), thermal runaway (a cell internal short,
  an overcharge, an external short across a battery), inadvertent
  initiation (a pyrotechnic firing circuit, a deployment actuator
  command path) or radiated energy (a transmitter field, a laser
  source). A hazard kind outside that set is an unfinished record, not
  a new family to invent in place.
- Severity comes from the credible worst-case consequence, not from
  how likely it feels. Loss of life, loss of the vehicle, loss of the
  launcher or facility and a permanent disabling injury are
  catastrophic; loss of mission and a reversible injury are critical;
  the loss of one redundant string and a degraded-performance outcome
  are marginal.
- Severity sets the failure tolerance: two tolerated failures for a
  catastrophic hazard, one for a critical hazard, none for a marginal
  one, which is controlled by design instead. The inhibit count is one
  more than the tolerance -- three independent inhibits for
  catastrophic, two for critical -- because an inhibit has to still be
  standing after the tolerated failures have happened. An inhibit that
  shares a failure cause with another adds no tolerance at all, and an
  inhibit whose state cannot be monitored cannot be confirmed before
  the hazardous operation.
- A stored-energy source is safe only after its bleed path has run.
  The residual voltage decays through the resistance-capacitance
  product, the residual energy is half the capacitance times that
  voltage squared, and both are checked at the end of the bleed period
  the procedure actually allows -- together with whether that period
  is long enough to reach the safe touch voltage in the first place.
- Each hazard closes on a recognized verification method -- a safety
  test, a safety analysis, a design inspection, a review of design, or
  similarity to a flown design -- with a closure reference that can be
  traced. An open record and an untraceable one are both findings.

## Workflow

1. Categorize each electrical hazard into its family; raise on a kind
   that is not a recognized clause 5.9 electrical hazard.
2. Map the credible worst-case consequence to a severity band; raise
   on a consequence that has never been mapped, rather than defaulting
   it to marginal.
3. Derive the failure tolerance and the independent-inhibit count that
   severity demands.
4. Walk the declared inhibits: drop any that shares a failure cause,
   flag any that carries no monitoring, and flag the hazard when the
   independent count falls short of the requirement.
5. Where the hazard has a stored-energy source, compute the residual
   voltage and residual energy at the end of the allowed bleed period
   and flag an exceedance of the safe touch voltage or the safe energy
   limit; separately flag a bleed path that needs longer than the
   procedure allows.
6. Check the verification record: flag a missing record, an open one,
   and a blank closure reference; raise on a method outside the
   recognized set.
7. Aggregate across the subsystem; conformance holds only when no
   hazard carries a finding.

## Pitfalls

- Counting inhibits rather than independent inhibits. Two switches on
  the same driver, the same relay coil supply or the same command
  decoder are one inhibit for tolerance purposes however they are
  drawn.
- Reading the failure tolerance as the inhibit count. A two-failure
  tolerant catastrophic hazard needs three inhibits, not two; taking
  the tolerance number straight onto the drawing leaves the design one
  short on exactly the hazards that matter most.
- Grading severity by likelihood. The band follows the worst credible
  consequence, and an unlikely catastrophic hazard still carries the
  catastrophic inhibit requirement.
- Treating an unmapped consequence as marginal so the check passes.
  An unmapped consequence means the hazard record is unfinished, and
  it has to stop the assessment rather than flow through it.
- Declaring a capacitor bank safe because a bleed resistor is fitted.
  The question is the residual voltage and residual energy at the end
  of the period the procedure allows, which is a time constant
  calculation, not the presence of a part.
- Closing a hazard on an inhibit that nothing monitors. An inhibit
  whose state cannot be read before the hazardous operation cannot be
  shown to be in place when it is needed.

## Behavior contract (gate 3)

The hazard-categorization, severity-mapping, failure-tolerance,
independent-inhibit, stored-energy bleed-down and verification-closure
logic is exercised by the gate 3 contract test:
scripts/test_e20_electrical_subsystem_safety_conformance.py against
scripts/e20_electrical_subsystem_safety_conformance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_electrical_subsystem_safety_conformance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
