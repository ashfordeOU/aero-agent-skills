---
name: q6013-class-2-high-voltage-parts
description: "Use when a high voltage use has to become an application verdict. Determine whether a commercial part may be used in a high voltage application at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.6.7: leave the clause below the declared threshold, take the applied voltage as a fraction of the part rating, derive the creepage and clearance the field limits demand and compare them with the layout, compute the gas breakdown voltage from a Townsend relation at the operating pressure, govern a powered depressurisation by the Paschen minimum instead, and score the evidence, crediting an analysis below a measurement. Trigger: ecss, q-st-60-13c-clause-5-6-7, class-two-high-voltage-part-application, high-voltage-part-voltage-derating, high-voltage-creepage-and-clearance, paschen-minimum-powered-depressurisation, high-voltage-partial-discharge-inception, high-voltage-venting-and-depressurisation-analysis."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-high-voltage-parts, class-two-high-voltage-part-application, high-voltage-part-voltage-derating, high-voltage-creepage-and-clearance, paschen-minimum-powered-depressurisation, high-voltage-partial-discharge-inception, high-voltage-venting-and-depressurisation-analysis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 High Voltage Parts (space-systems/ecss/q6013-class-2-high-voltage-parts)

Use when the task is the clause 5.6.7 high voltage question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a commercial part
is to sit in a place where the voltage across it is high, and the
question is whether the derating, the geometry around it, the ascent it
will fly through and the evidence behind it keep the application inside
what the class allows.

## Domain quick reference

- A high voltage application is not a hotter version of an ordinary one.
  The failure arrives through the gas and the surface around the part
  rather than through the die inside it, and it arrives during the ascent
  rather than on orbit.
- The clause has a floor. Below the declared high voltage threshold it
  does not constrain the application at all, and saying so is a result
  rather than a gap: the ordinary derating rules still apply and this
  assessment is not the one to run.
- Voltage derating is the only one of the four checks that concerns the
  part itself. The other three concern the space around it, which is why
  a correctly derated part in a tight layout still fails.
- Creepage and clearance are different distances with different limits. A
  path over a surface withstands less field than an open gap, because
  contamination and outgassed deposits track along it, so the required
  creepage is always the longer of the two.
- Gas breakdown follows a Townsend form of the Paschen relation at the
  pressure times the gap. Below the minimum of that curve there is no
  breakdown to sustain, and the relation is reported as unbounded there
  rather than extrapolated into a number that looks like an answer.
- The ascent decides it. An assembly energised while the pressure falls
  sweeps the whole curve including its minimum, so the minimum governs;
  an assembly that stays unpowered until the pressure has fallen never
  visits it and is judged at the pressure it operates at. That one
  declaration moves the verdict more than any distance on the layout.
- Encapsulation can stand in for the gas check, and only by an explicit
  policy decision. A fully encapsulated path has no gas gap to break
  down, but it has voids, and the partial discharge measurement is what
  carries that risk in the gas check's place.
- Evidence is scored, not ticked. A subject may be carried by analysis
  rather than by measurement at this class, which the class above does
  not allow, and analysis is credited below a measured record so that an
  application argued entirely on paper cannot read as a measured one.

## Workflow

1. Validate the high voltage policy first: the threshold, the derating
   cap, the creepage and clearance field limits, the breakdown margin
   floor, the evidence share and credited floors, the analysis credit and
   the marginal band. A creepage field limit above the clearance limit, a
   margin floor below one, a zero cap or credit, or a credited floor
   above the plain one is refused rather than used.
2. Validate the gas model: positive Townsend constants and a secondary
   emission coefficient below one.
3. Validate the application: a reference, a part, positive applied and
   rated voltages, a positive gap pressure, and a creepage no shorter
   than the clearance. An application with no reference or no part closes
   the assessment on application not declared.
4. Screen against the threshold. An applied voltage under it closes the
   assessment on below the high voltage threshold, with the note that the
   ordinary derating rules still apply.
5. Take the voltage derating, the required creepage and the required
   clearance, and compare each against its limit with a tolerance that
   absorbs representation error so a value landing on a bound is
   admissible. Report both distances when both are short.
6. Take the governing breakdown voltage: the Paschen minimum when the
   assembly is powered while the pressure falls, the value at the
   operating pressure and declared gap otherwise. Divide by the applied
   voltage and compare with the margin floor, unless a declared
   encapsulation waives the check under policy.
7. Dispose each required evidence subject as held as a measurement, held
   as an analysis, declared without a record, or absent, then report
   every failing list in full rather than truncating at the first entry.
8. Report the derating, the required distances, the governing breakdown
   voltage, the margin, the evidence share and the credited evidence, and
   raise an advisory for a derating inside the marginal band. Close on one
   verdict: application not declared, below the high voltage threshold,
   voltage derating exceeded, creepage or clearance short, gas breakdown
   margin short, evidence short, or application meets class two scope.

## Pitfalls

- Assessing the application at the on-orbit pressure when the assembly is
  powered through the ascent. The pressure sweeps down through the
  Paschen minimum on the way, and a design with a huge margin in vacuum
  can have none at all for the two minutes it passes the minimum.
- Extrapolating the Townsend expression below the minimum. It returns a
  number there, the number is not a breakdown voltage, and a margin built
  on it is a margin built on nothing.
- Checking clearance and calling the geometry done. The surface path is
  the longer requirement and the one that degrades in service as
  contamination and outgassed deposits track along it.
- Treating encapsulation as a free pass. A potted path has no gas gap and
  it does have voids, so the waiver stands only where the partial
  discharge measurement is held and the policy allows the trade.
- Reading the threshold as a gap in the assessment. Below it this clause
  simply does not apply, and reporting that is the answer rather than an
  absence of one.
- Crediting an analysis in full. Analysis is permitted here and it is
  thinner than a measurement on this build, which is what the credit
  records; an analysis claim naming no analysis is grouped with the
  subjects that hold no record at all.

## Behavior contract (gate 3)

The policy validation, the gas model validation, the application
validation, the threshold screen, the voltage derating, the required
creepage and clearance, the Paschen minimum and its pressure-gap product,
the vacuum regime, the governing breakdown voltage, the margin, the
encapsulation waiver, the measured, analysis, unrecorded and absent
evidence dispositions, the evidence share, the credited evidence, the
marginal advisories and the application verdict are exercised by the gate
3 contract test:
scripts/test_q6013_class_2_high_voltage_parts.py against
scripts/q6013_class_2_high_voltage_parts_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_high_voltage_parts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
