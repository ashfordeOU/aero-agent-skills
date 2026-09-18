---
name: e2020-output-impedance-bias-condition
description: "Verify the device voltage drop at which an output-impedance dataset was measured and reported, under ECSS-E-ST-20-20C clause 5.2.17.2.1. Use when a characterisation has to name its bias point instead of leaving the operating condition implicit: refuse a drop larger than the bus feeding it, take the declared drop against the reference bias point, compare it with the drop the reported load current and series resistance imply, hold it inside the device operating window, take the implied dissipation against the device limit, and refuse a set whose classes each pass yet straddle the tolerance as a group. Trigger: ecss, e-st-20-20c-clause-5-2-17-2, lcl-output-impedance-bias-condition, device-voltage-drop-bias-point, output-impedance-measurement-condition, series-element-voltage-drop, bias-point-commonality, protection-device-dissipation-limit."
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
  tags: [ecss, e-st-20-20-power-protection-device-scope, e2020-output-impedance-bias-condition, lcl-output-impedance-bias-condition, device-voltage-drop-bias-point, output-impedance-measurement-condition, series-element-voltage-drop, bias-point-commonality, protection-device-dissipation-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Protection Devices -- Output Impedance Bias Condition (space-systems/ecss/e2020-output-impedance-bias-condition)

Use when the task is the clause 5.2.17.2.1 measurement condition of
ECSS-E-ST-20-20C: the output impedance data supplied for a protection
device has to name the voltage the device was dropping across itself
when the data was taken, and that bias point has to be shown to be the
one the project fixed.

## Domain quick reference

- An impedance figure without its operating point is not a figure. The
  series element of a protection device is a controlled semiconductor,
  not a resistor, so how hard it is being driven changes the
  small-signal impedance the load behind it sees. The drop across the
  device is the handle the clause uses to pin that down.
- The drop is what makes two suppliers comparable. Two curves taken at
  two different bias points are two different measurements of two
  different operating conditions, and laying them over each other
  produces a family spread that is an artefact of the test setup.
- A declared drop and a measured drop are not the same claim. The
  declared figure can be carried forward from a template while the
  reported load current and series resistance imply something else
  entirely, so the two are reconciled against each other rather than
  taken on trust.
- The operating window has two ends and both matter. Too small a drop
  and the series element is barely conducting, so the measurement sits
  in a region the device never actually works in; too large and the
  element is closer to limitation than to its normal operating point,
  and the curve carries that in it.
- Per-record agreement does not give set agreement. Two classes can each
  sit inside the reference tolerance while landing on opposite sides of
  it, which puts twice the tolerance between them; the spread across
  the reported set is therefore its own separate check.
- Dissipation follows from the bias point for free. The drop times the
  current is what the series element has to shed, and a bias point that
  is defensible on impedance grounds can still be one the device cannot
  hold thermally.
- The reference and consistency tolerances, the operating window, the
  dissipation limit and the bus-share advisory ceiling are declared
  project policy rather than physical constants; the defaults in the
  logic module are a starting point a project substitutes its own values
  into.

## Workflow

1. Validate the policy: tolerances inside zero to one, an operating
   window that ascends, and a positive dissipation limit. A window that
   does not ascend is a data error, not a tight specification.
2. Validate each reported record: a positive declared drop, load
   current, series resistance and bus voltage, a unique class name, and
   a drop no larger than the bus feeding the device.
3. Validate the reference bias point itself against the operating
   window. A reference nobody can operate at fails the whole set and is
   refused up front rather than reported once per class.
4. Take the declared drop against the reference bias point as a relative
   deviation, and report it whether or not it passes so a reviewer sees
   which record sits nearest its bound.
5. Reconstruct the drop from the reported load current and series
   resistance and compare it with the declared one. Report the two
   deviations separately: a record can be on the reference and still be
   internally inconsistent, and that is a different defect.
6. Hold the declared drop inside the operating window, and take the
   implied dissipation at that drop and current against the device
   limit.
7. Take the spread of declared drops across the whole reported set
   against the same tolerance, and report a set that fails it even when
   every individual record passed.
8. Report the share of the bus voltage the device is holding as an
   advisory, so a bias point that is compliant but wasteful is visible.

## Pitfalls

- Reporting impedance without the bias point. The curve then cannot be
  compared with another supplier's, reproduced by the customer, or used
  in a stability case, and the omission is usually noticed only once two
  datasets disagree for no visible reason.
- Taking the declared drop on trust. The current and the series
  resistance in the same record imply a drop of their own, and a
  template value that survived a copy is caught by exactly that
  comparison and by nothing else.
- Treating per-record agreement as set agreement. Records on opposite
  edges of the tolerance are each compliant and are twice the tolerance
  apart, which is why the spread across the set is checked separately.
- Choosing the bias point on impedance grounds alone. The same drop sets
  the dissipation the series element has to shed at the reported
  current, and a thermally impossible bias point is not a bias point.
- Comparing a reconstructed drop or a dissipation by bare arithmetic.
  Both come out of multiplication, so a case meant to sit exactly on a
  limit can land a few units in the last place above it; the comparison
  absorbs that representation error while the limit stays as declared.

## Behavior contract (gate 3)

The policy validation, record validation, implied-drop and dissipation
arithmetic, relative deviation, reference and consistency comparisons,
operating-window and dissipation bounds, bus-share advisory, declared
drop spread and the set verdict are exercised by the gate 3 contract
test: scripts/test_e2020_output_impedance_bias_condition.py against
scripts/e2020_output_impedance_bias_condition_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_output_impedance_bias_condition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
