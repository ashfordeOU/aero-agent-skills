---
name: q6013-class-1-radiation-verification-testing
description: "Verify a purchased flight lot of radiation-sensitive commercial EEE parts against its mission dose requirement under ECSS-Q-ST-60-13C clause 4.3.8. Use when deciding whether a commercial lot needs a radiation verification test, sizing the irradiation sample, reducing a dose ladder into a demonstrated lot capability, and comparing the achieved radiation design margin and threshold linear energy transfer with the required values. Refuses an unordered dose ladder, credits no recovery above a failed step, and separates invalid sampling evidence from a genuine capability shortfall. Trigger: ecss, q-st-60-13c, commercial-eee-radiation-verification-test, flight-lot-irradiation-sample, total-ionising-dose-capability, radiation-design-margin, single-event-threshold-let, commercial-lot-radiation-traceability."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-radiation-verification-testing, commercial-eee-radiation-verification-test, flight-lot-irradiation-sample, total-ionising-dose-capability, radiation-design-margin, single-event-threshold-let]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Radiation Verification Testing (space-systems/ecss/q6013-class-1-radiation-verification-testing)

Use when the task is the radiation verification test of ECSS-Q-ST-60-13C
clause 4.3.8 — deciding whether a flight lot of sensitive commercial EEE
parts has to be irradiated, and judging what the irradiation demonstrated
about that lot, on a Class 1 assurance programme.

## Domain quick reference

- A commercial part number is not a controlled part number. Process,
  mask set and assembly site can move between date codes without any
  notification, so a total-ionising-dose capability measured on one lot
  is evidence about that lot only. The verification test therefore
  attaches to the **procured flight lot**, not to the part type.
- The requirement the lot has to meet is the part-level mission dose
  behind its actual shielding, multiplied by the project radiation
  design margin: required capability = mission dose x required margin.
  The margin is a ratio, never a subtraction, and it is applied before
  the lot is compared with anything.
- A dose-sensitive technology family — bipolar linear, CMOS digital,
  mixed-signal converters, optocouplers, power MOSFETs, non-volatile
  memory, voltage regulators — cannot inherit a capability figure from
  another lot. A family outside that set, with a declared capability
  that already covers the requirement, may.
- The demonstrated capability is read off the irradiation ladder as the
  highest dose step at which **every** irradiated unit was still inside
  its end-of-life electrical limits, with no failed step below it. A
  unit that drifts out at 30 krad and reads in limits again at 50 krad
  has not demonstrated 50 krad; it has demonstrated the step below the
  first failure.
- Sampling evidence and capability evidence fail differently. Units
  drawn from another date code, or a sample too small to speak for a
  lot, make the result inadmissible rather than negative — the lot is
  not rejected, the evidence is.
- Where the mission carries a single-event requirement, the measured
  threshold linear energy transfer is compared with the required
  threshold in the same pass, because a lot can clear the dose
  requirement and still be destroyed by a single heavy ion.

## Workflow

1. Compute the required part-level capability from the mission dose and
   the required radiation design margin; a margin below unity is an
   input error, not a waiver.
2. Decide whether a verification test is needed: missing declared
   capability, a declared capability below the requirement, or a
   dose-sensitive family whose capability is not evidenced on the flight
   lot each force the test and are reported with their reason.
3. Size the sample and confirm every unit comes from the flight lot.
   Record a sample below the floor, or a sample from elsewhere, as a
   sampling finding before any dose result is read.
4. Validate the irradiation ladder: doses strictly increasing, unit
   counts consistent. Reduce it to the demonstrated lot capability.
5. Convert the capability into an achieved margin against the mission
   dose and compare it with the required margin, absorbing
   floating-point representation error at the boundary with a named
   tolerance rather than by relaxing the margin.
6. Where a single-event requirement is declared, compare the measured
   threshold with the required threshold; a declared requirement with no
   measurement behind it is refused, not defaulted.
7. Report the disposition — verified, evidence invalid, or rejected —
   with every finding that produced it.

## Pitfalls

- Accepting a capability figure from the vendor datasheet or a previous
  purchase for a dose-sensitive commercial family. That figure describes
  a different lot; on an uncontrolled part number it carries no
  commitment to the lot in the store.
- Crediting the highest passing dose step regardless of what happened
  below it. The ladder is cumulative; a step above a failure was reached
  by units that had already drifted out of limits.
- Rejecting a lot when the sampling was wrong. A sample drawn outside
  the flight lot says nothing about the lot either way, so the
  disposition is inadmissible evidence and a re-test, not a rejection.
- Subtracting the margin instead of multiplying by it, or applying it to
  the measured capability instead of to the mission dose. Both change
  which lots pass, and both are silent.
- Treating a cleared dose requirement as a cleared radiation
  requirement. Threshold linear energy transfer is a separate, usually
  destructive, criterion.
- Widening the required margin to make an exact-equality case pass. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the required value stays as
  specified.

## Behavior contract (gate 3)

The capability derivation, test-necessity decision, sample validation,
irradiation-ladder reduction, margin comparison and single-event
threshold check are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_radiation_verification_testing.py against
scripts/q6013_class_1_radiation_verification_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_class_1_radiation_verification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
