---
name: e20-converter-control-loop-stability
description: "Use when evaluate the closed-loop stability of a spacecraft power converter or regulator under ECSS-E-ST-20C clause 5.7.5: categorize the loop as a switching converter, a linear regulator or a bus control loop, set the phase-margin and gain-margin targets that category carries unless the project requirement overrides them, enumerate the worst-case corner set from the temperature, input-voltage and load extremes, build the open-loop frequency response from the direct-current gain, poles, zeros, any right-half-plane zero and the modulator transport delay, locate the gain- and phase-crossover frequencies, and confirm every corner holds both margins rather than the nominal point alone. Trigger: ecss, e-st-20c-clause-5-7-5, converter-control-loop-stability, phase-margin-target, gain-margin-target, gain-crossover-frequency, phase-crossover-frequency, worst-case-corner-stability, closed-loop-regulator-margin."
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
  tags: [ecss, e-st-20-electrical-scope, e20-converter-control-loop-stability, converter-control-loop-stability, phase-margin-target, gain-margin-target, gain-crossover-frequency, worst-case-corner-stability, closed-loop-regulator-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Converter Control Loop Stability (space-systems/ecss/e20-converter-control-loop-stability)

Use when the task is the clause 5.7.5 stability demonstration of
ECSS-E-ST-20C -- showing that every closed control loop inside a power
converter or regulator keeps a stated phase margin and gain margin,
and showing it at the corners of the operating envelope rather than at
the nominal operating point.

## Domain quick reference

- A control loop is categorized once by what it regulates: a switching
  converter loop (buck, boost, buck-boost, flyback, point-of-load,
  battery charge regulator, shunt regulator), a linear regulator loop
  (series regulator, shunt regulator, low-dropout regulator), or a bus
  control loop (main bus voltage control, maximum-power-point
  control). The category sets the default margin pair the leaf
  applies when the project requirement is silent; a stated project
  requirement always overrides the default, and a requirement that
  asks for a negative margin is rejected rather than accepted.
- The demonstration point is not a single frequency response. The
  envelope is swept as a corner set: each declared axis (temperature,
  input voltage, load) must carry both of its extremes, and the corner
  set is the full combination of them. A corner with no loop model on
  record is a finding in itself -- the margin was never shown there --
  and a model offered under a label that matches no enumerated corner
  is equally a finding, because it cannot be traced to an envelope
  point.
- The open-loop response is assembled from a direct-current gain, a
  set of left-half-plane poles, a set of left-half-plane zeros, an
  optional right-half-plane zero and a transport delay. The
  right-half-plane zero and the delay both add phase lag without
  removing gain, which is why a boost-derived topology and a
  digitally sampled loop lose margin where a buck loop does not.
- Phase margin is read at the gain-crossover frequency, where the
  open-loop magnitude passes unity: it is one hundred and eighty
  degrees plus the open-loop phase there. Gain margin is read at the
  phase-crossover frequency, where the open-loop phase passes minus
  one hundred and eighty degrees: it is the attenuation below unity at
  that frequency. A loop whose phase never reaches minus one hundred
  and eighty degrees inside the analysis band has no phase crossover
  and an unbounded gain margin; that is a result, not a failure.

## Workflow

1. Categorize the loop kind; reject a kind that is not a clause 5.7.5
   converter or regulator loop before any response is built.
2. Take the default margin pair for that category and apply the
   project requirement over it, field by field, rejecting a negative
   or non-numeric target.
3. Enumerate the worst-case corners from the declared envelope axes.
   Reject an axis list that is missing a required axis, carries an
   unrecognized axis, or offers a single value where two extremes are
   needed.
4. For each enumerated corner, take its loop model and locate the
   gain-crossover frequency inside the analysis band by bisection on
   the magnitude, rejecting a band that starts below unity gain or
   ends above it.
5. Read the phase margin at that crossover. Locate the phase crossover
   the same way and read the gain margin there, treating the absence
   of a phase crossover in the band as an unbounded gain margin.
6. Compare both margins against the targets with a representation
   tolerance, so a corner that sits exactly on the target is reported
   as compliant rather than a few bits short.
7. Aggregate the coverage findings and the per-corner margin findings;
   the loop is stable to clause 5.7.5 only when both lists are empty.

## Pitfalls

- Demonstrating the margins at the nominal operating point and
  declaring the loop stable -- clause 5.7.5 asks for the worst case,
  and the worst case is normally cold temperature at maximum input
  voltage and minimum load, where the gain is highest and the
  crossover has moved up into the delay-dominated region.
- Reading phase margin at the phase crossover and gain margin at the
  gain crossover, which silently swaps the two numbers; the phase
  margin belongs at unity gain and the gain margin at minus one
  hundred and eighty degrees of phase.
- Omitting the modulator and sampling delay because it adds no
  magnitude. It adds phase lag in proportion to frequency, so it costs
  nothing at low frequency and can consume the entire margin once the
  crossover is pushed up by a high-gain corner.
- Modelling a boost-derived or buck-boost-derived topology without its
  right-half-plane zero; the magnitude then looks the same while the
  phase is optimistic by tens of degrees near crossover.
- Searching for a crossover in a band that does not bracket it and
  taking the band edge as the answer -- a band whose lower edge is
  already below unity gain, or whose upper edge is still above it,
  gives no crossover and must be rejected, not clamped.
- Treating an unbounded gain margin as a missing result and failing
  the corner; a loop whose phase stays above minus one hundred and
  eighty degrees across the analysis band has no phase crossover, and
  the gain margin is genuinely unbounded there.

## Behavior contract (gate 3)

The loop categorization, margin-target, corner-enumeration,
frequency-response, crossover-search and margin-comparison logic is
exercised by the gate 3 contract test:
scripts/test_e20_converter_control_loop_stability.py against
scripts/e20_converter_control_loop_stability_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_converter_control_loop_stability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
