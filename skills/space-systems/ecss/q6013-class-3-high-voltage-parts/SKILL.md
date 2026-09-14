---
name: q6013-class-3-high-voltage-parts
description: "Determine whether a commercial part may sit in a high voltage or high power application at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.6.7: engage each axis only where its threshold is crossed, take the applied voltage as a fraction of the part rating, derive the surface path the field limit demands, take the discharge margin against the peak rather than the mean working voltage, derate the rated dissipation for the class and again along the package temperature curve, carry the junction to the rating less a held-back margin, and score the evidence across measurement, analysis and supplier declaration. Use when a high voltage or high power usage has to become a verdict. Trigger: ecss, q-st-60-13c-clause-6-6-7, class-three-high-voltage-part-application, high-power-case-temperature-derating, high-voltage-creepage-field-limit, partial-discharge-inception-margin, high-power-junction-temperature-margin, class-three-high-voltage-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c-clause-6-6-7, q6013-class-3-high-voltage-parts, class-three-high-voltage-part-application, high-power-case-temperature-derating, high-voltage-creepage-field-limit, partial-discharge-inception-margin, high-power-junction-temperature-margin, class-three-high-voltage-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 High Voltage and High Power Parts (space-systems/ecss/q6013-class-3-high-voltage-parts)

Use when the task is the clause 6.6.7 question of ECSS-Q-ST-60-13C at the
lowest assurance class: a commercial part is to sit where the voltage
across it is high, where the power through it is high, or both, and the
question is whether the derating, the geometry around it, the thermal
path under it and the evidence behind it keep the usage inside what the
class allows.

## Domain quick reference

- Two axes, two failure mechanisms, one clause. The voltage axis fails
  in the insulation around the part: a surface tracks, a coating void
  starts discharging, and nothing inside the part ever conducts. The
  power axis fails inside the part: the die runs hotter than the package
  can carry the heat away. They share a clause and share nothing else.
- The thresholds decide which checks run. An application under both is
  not partly assessed, it is outside this clause, and reporting that is
  the answer rather than an absence of one. An application over the
  power threshold but under the voltage threshold is not asked for a
  creepage path it has no need of, and asking anyway invents a finding.
- A value landing on a threshold engages the axis. A threshold is a
  floor for the assessment, not a gap to slip through, so the equality
  is admitted deliberately rather than left to a representation error.
- Discharge is taken against the peak, not the mean. A part working at a
  nominal voltage with a switching waveform on top sees the peak every
  cycle, and the discharge inside a void does not average out between
  them.
- Power derating is two deratings, and the second one is the one people
  drop. The class derates the catalogue rating; the package derates
  itself again along its own curve, at full rating up to an onset
  temperature and falling to nothing at its maximum case temperature. A
  part quoted at thirty watts on a bench at twenty-five degrees is not a
  thirty watt part at sixty-five.
- A case sitting at or above its own maximum is off the end of that
  curve. It carries no rated dissipation at all, which is a different
  finding from carrying too much, and the two deserve different words.
- The junction, not the case, is the temperature the part lives at. It
  is the case temperature plus the dissipation through the thermal
  resistance, and it is judged against the junction rating less a margin
  the class holds back rather than against the rating itself.
- Evidence has three tiers here, not two. A subject may be carried by a
  measurement, by an analysis, or by a supplier's own declaration. Each
  is credited below the one before it, so an application argued entirely
  on what a datasheet claims about itself cannot read as a measured one.

## Workflow

1. Validate the application policy first: both thresholds, the voltage
   utilization cap, the class power derating, the creepage field limit,
   the discharge margin floor, the junction margin, the analysis and
   declaration credits, the evidence share and credited floors and the
   marginal band. A discharge margin floor below one, a declaration
   credit at or above the analysis credit, a zero cap or credit, or a
   credited floor above the plain one is refused rather than used.
2. Validate the application: a reference and a part, positive applied
   and rated voltages, a peak factor no lower than one, a positive
   inception voltage and surface path, a non-negative dissipation and a
   positive power rating, a derating curve with a run in it, a positive
   thermal resistance and a junction rating no cooler than the package.
   An application with no reference or no part closes the assessment on
   application not declared.
3. Take the engaged axes from the two thresholds. Neither engaged closes
   the assessment on below both thresholds, with the note that the
   ordinary derating rules still apply.
4. On the voltage axis, take the utilization against its cap, the
   required surface path against the layout, and the discharge margin
   against its floor, comparing each with a tolerance that absorbs
   representation error so a value landing on a bound is admissible.
5. On the power axis, place the case on the package derating curve,
   report a case at or above its maximum separately from a part simply
   dissipating too much, take the derated allowance against the declared
   dissipation, then carry the junction to the rating less the class
   margin.
6. Dispose each required evidence subject as held as a measurement, held
   as an analysis, held as a supplier declaration, declared without a
   record, or absent, then report every failing list in full rather than
   truncating at the first entry.
7. Report the engaged axes, the utilization, the peak working voltage,
   the required path, the discharge margin, the derating factor, the
   allowance, the junction and its cap, the evidence share and the
   credited evidence, and raise an advisory for an axis sitting just
   inside its limit.
8. Close on one verdict: application not declared, below both
   thresholds, voltage derating exceeded, insulation spacing short,
   discharge margin short, power derating exceeded, junction temperature
   exceeded, evidence short, or application meets class three scope.

## Pitfalls

- Reading the case temperature as the answer. It is the easiest number
  to measure and the furthest from the one that fails; the junction sits
  a dissipation and a thermal resistance above it.
- Taking the datasheet power rating at face value. It is quoted at a
  bench temperature the flight mounting will never see, and the package
  derating curve is the part of the datasheet nobody prints.
- Taking the discharge margin against the working voltage rather than
  its peak. The void discharges on the peak of every cycle, and the mean
  is the one voltage it never sees.
- Checking clearance in air and calling the geometry done. The surface
  path is the requirement that degrades in service as contamination and
  outgassed deposits track along it.
- Running a creepage check on a low voltage part because the assessment
  was opened. Under the voltage threshold the axis does not engage, and
  a finding raised there is a finding against nothing.
- Treating a case above its maximum as a large overload. It is a
  different condition: the package has no rated dissipation left at that
  temperature, and moving heat off the part, not lowering the power, is
  the only close-out.
- Crediting a supplier declaration as though it were an analysis. Each
  tier is thinner than the one above it, which is what the credits
  record; a subject with no reference at all is grouped with the ones
  the application never declared.

## Behavior contract (gate 3)

The policy validation, the application validation, the threshold screen
and engaged axes, the voltage utilization, the peak working voltage, the
required surface path, the discharge margin, the package derating factor
and its clamps, the derated dissipation allowance, the junction
temperature and its margined cap, the measurement, analysis, declaration,
unrecorded and absent evidence dispositions, the evidence share, the
credited evidence, the marginal advisories and the application verdict
are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_high_voltage_parts.py against
scripts/q6013_class_3_high_voltage_parts_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6013_class_3_high_voltage_parts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
