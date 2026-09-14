---
name: q6013-class-2-radiation-verification-testing
description: "Verify a sensitive intermediate assurance commercial EEE lot against its mission dose requirement under ECSS-Q-ST-60-13C clause 5.3.8: multiply the part-level mission dose by the class radiation design margin and again by the penalty that credited heritage data carries, test the similarity claim on manufacturer, wafer process and date-code proximity before reading a dose figure, refuse the heritage credit for a dose-rate-sensitive family flown slowly with no low dose rate data behind it, reduce several heritage lots to their worst case, compare the single-event threshold in the same pass, and return verified, lot test required, evidence invalid or rejected. Use when heritage data has to become a dose verdict. Trigger: ecss, q-st-60-13c-clause-5-3-8, class-two-radiation-verification, heritage-similarity-credit, radiation-design-margin-penalty, low-dose-rate-heritage-refusal, worst-case-heritage-lot-capability, single-event-threshold-let-check."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-2-radiation-verification-testing, class-two-radiation-verification, heritage-similarity-credit, radiation-design-margin-penalty, low-dose-rate-heritage-refusal, worst-case-heritage-lot-capability, single-event-threshold-let-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE -- Class 2 Radiation Verification Testing (space-systems/ecss/q6013-class-2-radiation-verification-testing)

Use when the task is the clause 5.3.8 radiation verification of
ECSS-Q-ST-60-13C at the intermediate assurance class: a sensitive
commercial part has been procured, the verification may rest on data
from a similar lot rather than on an irradiation of the flight lot
itself, and the question is whether that evidence clears the mission.

## Domain quick reference

- The intermediate class lets heritage data stand in for a lot-specific
  irradiation, and that concession is the whole subject. Everything the
  procedure does is either deciding whether the heritage may be read at
  all or deciding what reading it costs.
- What it costs is margin. The requirement heritage evidence has to
  clear is the mission dose multiplied by the design margin and
  multiplied again by a penalty factor, because the evidence describes a
  lot nobody is going to fly. The factors multiply; a margin that is
  subtracted, or applied to the measured capability instead of to the
  mission dose, quietly changes which lots pass.
- Similarity is tested before any dose figure is read. Same
  manufacturer, same wafer process, and date codes inside a declared
  comparability window. A different assembly site is reported rather
  than refused, because it does not change the die the dose acts on.
- One failure mode is invisible to heritage data whatever the
  similarity. A dose-rate-sensitive family flown slowly can degrade more
  at the mission rate than at the high rate the heritage test used, so
  without low dose rate data behind it the credit is refused and a lot
  test is called for.
- Several heritage lots reduce to their worst case, never to their mean.
  The spread between those lots is precisely the lot-to-lot uncertainty
  the credit is being asked to cover, and averaging it away answers a
  different question.
- Inadmissible evidence and an insufficient lot fail differently. Units
  drawn from another lot, a sample too small to speak for a lot, or a
  similarity claim that does not hold make the capability figure silent
  rather than negative: the evidence is refused, and the figure is
  reported but not judged.
- A shortfall the penalty caused is not a rejection. A heritage
  capability that clears the design margin and fails only the penalised
  requirement is exactly the case a lot-specific irradiation exists to
  settle.
- Dose is not the whole radiation requirement. Where a single-event
  threshold is declared it is compared in the same pass, because a lot
  can clear the dose requirement and still be destroyed by one heavy
  ion.

## Workflow

1. Build the requirement: mission dose times design margin, times the
   heritage penalty where the evidence is not lot-specific. Keep the
   unpenalised figure alongside it; the two together are what separate a
   lot test from a rejection.
2. For lot-specific evidence, confirm the units were drawn from the
   procured flight lot and that enough of them were irradiated.
3. For heritage evidence, evaluate the similarity claim first, then
   apply the low dose rate refusal, then reduce the heritage lots to
   their worst case and name the lot that governs.
4. Compare capability with requirement using a named tolerance at the
   boundary rather than a widened requirement.
5. Compare the single-event threshold where one is declared; a declared
   requirement with no measurement behind it is refused, not defaulted.
6. Return one of four dispositions in precedence order: inadmissible
   evidence, then a lot test required, then rejected, then verified, and
   report every reason that produced it.

## Pitfalls

- Crediting a vendor datasheet figure as heritage. A datasheet is not a
  similarity claim; without the manufacturer, process and date-code
  comparison there is nothing to test the claim against.
- Averaging the heritage lots. The mean hides the low lot, which is the
  one the flight lot might resemble.
- Reading a high dose rate heritage result as covering a slow mission
  for a sensitive family. The test was silent on that failure mode
  rather than reassuring about it.
- Rejecting a lot whose evidence was inadmissible. A capability measured
  on the wrong units says nothing in either direction, so the outcome is
  a re-test on admissible evidence, not a rejection the lot has to carry.
- Treating a penalised shortfall as a rejection. The penalty exists
  because the evidence is second-hand; a lot-specific irradiation
  removes the penalty and may well clear the requirement.
- Widening the requirement to make an exact-equality case pass. An
  equality at the limit is a representation question, absorbed by the
  tolerance inside the comparison, and the required value stays as
  specified.

## Behavior contract (gate 3)

The requirement derivation, heritage penalty, similarity evaluation,
low dose rate refusal, worst-case heritage reduction, boundary margin
comparison, single-event threshold check and the four-way disposition
are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_radiation_verification_testing.py against
scripts/q6013_class_2_radiation_verification_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_class_2_radiation_verification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
