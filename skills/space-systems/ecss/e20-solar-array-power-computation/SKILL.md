---
name: e20-solar-array-power-computation
description: "Use when compute the predicted output of a spacecraft solar array under ECSS-E-ST-20C clause 5.5.3, basing the prediction on cell-level measurements taken per the photovoltaic assembly standard rather than on catalogue figures: validate each measured current-voltage record and the traceability of its provenance, derive the fill factor as a plausibility screen, correct the measured maximum-power point for operating temperature, solar distance and sun-incidence angle, apply particle-fluence, ultraviolet and coverglass retention, assemble series-parallel sections with string mismatch, interconnect, harness and blocking-diode losses, then compare predicted section power against the demand and report the shortfall. Trigger: ecss, e-st-20-electrical-scope, solar-array-power-prediction, cell-level-measurement, maximum-power-point, temperature-coefficient-correction, particle-fluence-retention, series-parallel-string, photovoltaic-assembly-traceability."
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
  tags: [ecss, e-st-20-electrical-scope, e20-solar-array-power-computation, solar-array-power-prediction, cell-level-measurement, maximum-power-point, temperature-coefficient-correction, particle-fluence-retention, photovoltaic-assembly-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Solar Array Power Computation (space-systems/ecss/e20-solar-array-power-computation)

Use when the task is the array output prediction of ECSS-E-ST-20C
clause 5.5.3 -- computing what a solar array will actually deliver from
measured cell performance, with the measurement itself taken under the
photovoltaic assembly standard (ECSS-E-ST-20-08) rather than read off a
supplier catalogue sheet.

## Domain quick reference

- The clause is a provenance rule before it is an arithmetic rule. The
  prediction stands on cell-level or assembly-level measurement of the
  actual build standard. A record whose source is a datasheet figure,
  an analytical estimate or heritage from another programme is
  categorized as untraceable, and the prediction it feeds is reported
  as not admissible even when the numbers look reasonable.
- A measurement record is a current-voltage pair set at reference
  conditions: short-circuit current, open-circuit voltage, and the
  current and voltage at the maximum-power point. The maximum-power
  current sits below the short-circuit current and the maximum-power
  voltage below the open-circuit voltage; a record that violates
  either ordering is corrupt and is rejected, not corrected.
- The fill factor -- maximum-power product divided by the
  short-circuit/open-circuit product -- is the cheap screen on a
  record. A triple-junction space cell lands in a narrow band; a value
  outside a plausible band means the record mixes conditions, units or
  cell types and cannot be corrected to an operating point.
- Correcting to the operating point is three independent effects.
  Current scales with incident intensity, which is the inverse square
  of solar distance times the cosine of sun-incidence angle, and rises
  slightly with temperature. Voltage falls with temperature at a much
  larger relative rate and is treated as intensity-independent here.
  Applying a single "power temperature coefficient" to the product
  hides that the two terms move in opposite directions.
- Retention factors then multiply the corrected power: particle
  fluence over the mission (a logarithmic law against a reference
  fluence), ultraviolet darkening, and coverglass and adhesive
  transmission loss. Section assembly adds string mismatch,
  interconnect and harness losses, and a blocking-diode forward drop
  that is subtracted from the string voltage, not from the power.

## Workflow

1. Validate every cell measurement record: positive short-circuit
   current and open-circuit voltage, maximum-power current strictly
   below short-circuit current, maximum-power voltage strictly below
   open-circuit voltage.
2. Compute the fill factor and screen it against a plausible band.
   Reject a record outside the band rather than pushing it forward.
3. Categorize the provenance of each record. A measured provenance
   carries a confidence weight; an untraceable source is categorized
   as uncategorized-provenance and raised as a finding.
4. Correct the maximum-power point to the operating condition: scale
   current by intensity and by the current temperature coefficient,
   scale voltage by the voltage temperature coefficient. Reject an
   operating point that drives either corrected quantity to zero.
5. Compute the retention factor from mission particle fluence,
   ultraviolet loss and coverglass loss. Reject a fluence that drives
   retention to zero -- the cell is outside the model, not at zero
   power.
6. Assemble each section: multiply voltage by the series count and
   subtract the blocking-diode drop; multiply current by the parallel
   count and apply mismatch and interconnect losses; multiply the
   product by the harness loss and the retention factor.
7. Sum the sections, compare against the demanded power, and report
   the margin plus every provenance finding. A section set with an
   untraceable record is reported as not compliant regardless of its
   margin.

## Pitfalls

- Predicting from a catalogue maximum-power figure and treating the
  number as measured. Clause 5.5.3 is satisfied by the measurement
  chain, not by the plausibility of the value.
- Using one lumped power temperature coefficient. Current rises and
  voltage falls with temperature; lumping them loses the sign
  structure and mis-predicts any array whose hot and cold cases
  differ in which term dominates.
- Scaling voltage by intensity as well as current. String voltage is
  weakly intensity-dependent and treating it as proportional badly
  overstates a far-sun or high-incidence case.
- Subtracting the blocking-diode drop from section power instead of
  from string voltage. The drop is a fixed voltage on the string and
  its power cost scales with the section current.
- Applying the fluence retention twice -- once inside a supplied
  end-of-life measurement and again as a model factor. Confirm whether
  the record is a beginning-of-life or an already-degraded value
  before multiplying.

## Behavior contract (gate 3)

The record-validation, fill-factor screen, provenance categorization,
operating-point correction, retention and section-assembly logic is
exercised by the gate 3 contract test:
scripts/test_e20_solar_array_power_computation.py against
scripts/e20_solar_array_power_computation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_solar_array_power_computation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
