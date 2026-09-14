---
name: e2008-solar-cell-reverse-bias-test
description: "Use when a reverse bias run on bare cells has to be sentenced. Assess a bare solar cell for output degradation after it has been driven into reverse polarity under ECSS-E-ST-20-08C clause 7.5.16: confirm the declared reverse current was really forced and held for its dwell, separate a run the supply clamped at its compliance voltage from one the cell itself carried, compute the heat the reversed cell dissipated against the hot-spot cap, take the fall in maximum power, short-circuit current and open-circuit voltage against the allowance each one carries, and refuse a comparison whose two measurements sit at different reference conditions. Trigger: ecss, e-st-20-08c-clause-7-5-16, bare-cell-reverse-bias-stress, reverse-bias-dwell-dissipated-power, reverse-bias-supply-compliance-clamp, post-reverse-bias-output-degradation, bare-cell-reverse-polarity-recovery."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-solar-cell-reverse-bias-test, e-st-20-08c-clause-7-5-16, bare-cell-reverse-bias-stress, reverse-bias-dwell-dissipated-power, reverse-bias-supply-compliance-clamp, post-reverse-bias-output-degradation, bare-cell-reverse-polarity-recovery]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Reverse Bias Test (space-systems/ecss/e2008-solar-cell-reverse-bias-test)

Use when the task is clause 7.5.16 of ECSS-E-ST-20-08C: one bare cell
put deliberately into the state a shadowed cell reaches inside a series
string -- back-driven by the cells still in the light -- and then
measured again in the forward direction to see whether it came back.

## Domain quick reference

- The stress is the first thing to check, not the last. A reverse bias
  run that never reached the declared current exercised a cell the
  string would have treated far more harshly, and a clean recovery after
  it says nothing about the hardware.
- A supply sitting at its compliance voltage while short of the declared
  current is a different finding from a short run. The instrument set
  the operating point, so the record describes the power supply rather
  than the cell, and repeating it with more compliance is the action.
- The reversed cell turns the string current into heat at its own
  reverse voltage. That product is the hot spot, it is the reason a
  bypass diode exists, and a run whose product sits over the declared
  cap damaged the cell thermally whatever the electrical result says.
- Cell temperature during the stress belongs with the stress. Past the
  declared ceiling a later loss can no longer be separated from ordinary
  thermal damage, and the run answers a question nobody asked.
- The three forward parameters are kept apart because they fail for
  different reasons. Maximum power falls for any of them; short-circuit
  current falls where the junction has been shunted; open-circuit
  voltage falls where a localised breakdown path has formed.
- So each parameter carries its own allowance. Collapsing them into a
  single power number hides the mechanism, and the mechanism is what
  decides whether one cell was unlucky or the lot has a process problem.
- Before and after have to sit at the same reference conditions. A cell
  measured a few degrees warmer afterwards reports a voltage loss that
  belongs to the thermometer, and the comparison is refused rather than
  corrected.
- The reverse current, the dwell, the temperature ceiling, the hot-spot
  cap, the three allowances, the condition tolerances and the specimen
  floor are declared project policy rather than physical constants, so
  they are stated with the result.

## Workflow

1. Take the run: one record per specimen, each with a forward
   measurement before, the reverse bias stress record, and a forward
   measurement afterwards.
2. Read the stress first: the current reached, the dwell held, the cell
   temperature, and the supply compliance the run sat against.
3. Group the stress as delivered, short, clamped by the supply, or over
   temperature, and leave a specimen unsentenced for anything but the
   first, because the stress it carries is not the declared one.
4. Multiply reverse voltage by reverse current to get the heat the cell
   had to carry, and hold that against the hot-spot cap.
5. Check the two forward measurements sit at the same irradiance and
   temperature, and refuse the comparison where they do not.
6. Reduce each of maximum power, short-circuit current and open-circuit
   voltage to the share of its baseline the cell gave up, and group each
   against its own allowance.
7. Sentence each specimen, then roll the lot up: specimen count against
   its floor, failed share against its allowance, and any unsentenced
   specimen named on its own.

## Pitfalls

- Sentencing a run whose reverse current never got there. The cell
  passed a milder test than the one the string will apply, and the
  record reads as a pass.
- Treating a supply held at compliance as an ordinary short run. The
  instrument, not the cell, decided where the operating point sat, so
  the next run needs more compliance rather than another specimen.
- Reporting only the maximum power loss. A shunted junction and a
  breakdown path both show as lost power, and only the current and
  voltage split says which one happened.
- Ignoring the dissipated product because the electrical result was
  clean. The hot spot is the damage mechanism the clause exists for, and
  a cell that carried more heat than the cap allows is not qualified by
  a benign reading afterwards.
- Comparing a post-test measurement taken warmer than the baseline. The
  temperature coefficient supplies a voltage loss all by itself, and the
  finding then belongs to the bench.
- Letting a stress that ran over the temperature ceiling stand. Thermal
  damage and reverse bias damage are no longer separable in that record,
  whichever way the numbers fell.
- Comparing a parameter loss, a dissipated power or a failed share
  against its limit by bare arithmetic. Each is a quotient or product of
  measured quantities, so a specimen cut exactly to an allowance can
  evaluate a unit in the last place over it and read as a reject on one
  platform and as compliant on another.

## Behavior contract (gate 3)

The stress read with its short, supply-clamped and over-temperature
groupings, the dissipated power and its hot-spot cap, the reference
condition comparability refusal, the per-parameter losses, the three-step
output grouping with its own allowance per parameter, the worst-parameter
roll-up, the specimen verdict and the lot population, failed share and
unsentenced roll-up are exercised by the gate 3 contract test:
scripts/test_e2008_solar_cell_reverse_bias_test.py against
scripts/e2008_solar_cell_reverse_bias_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_solar_cell_reverse_bias_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
