---
name: e2008-multijunction-cell-capacitance-measurement
description: "Determine what the single-junction capacitance method has to change before it is run on a multijunction cell per ECSS-E-ST-20-08C clause 11.1.5: sum the sub-cell capacitances as reciprocals into the terminal reading, partition the applied bias by those same shares, name the sub-cell that dominates both, size the bias a one-junction extraction misattributes, hold the test frequency under the corner the tunnel-junction series resistance sets, and refuse a stack too dominated by one junction to resolve at the terminals. Use when a triple-junction cell is about to be measured by a method written for one junction. Trigger: ecss, e-st-20-08c-clause-11-1-5, multijunction-cell-capacitance-measurement, subcell-series-capacitance-summation, subcell-bias-partition-share, tunnel-junction-corner-frequency-margin, dominant-subcell-identification, single-junction-method-adaptation."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-multijunction-cell-capacitance-measurement, subcell-series-capacitance-summation, subcell-bias-partition-share, tunnel-junction-corner-frequency-margin, dominant-subcell-identification, single-junction-method-adaptation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Multijunction Cell Capacitance Measurement (space-systems/ecss/e2008-multijunction-cell-capacitance-measurement)

Use when the task is clause 11.1.5 of ECSS-E-ST-20-08C -- taking the
capacitance method written for a single junction and working out what it
has to do differently on a multijunction cell, before a number measured
at two terminals is reported as though it belonged to one depletion
region.

The method is not wrong; it is written for a device the article is not.
A monolithic multijunction cell is a series stack of sub-cell junctions
with tunnel junctions between them, and the meter never sees a sub-cell.
Every quantity the single-junction method reports -- the capacitance,
the bias it was measured at, the frequency it is valid to -- means
something different once the stack is in the way.

## Domain quick reference

- Sub-cell capacitances combine as reciprocals. The terminal reading
  therefore sits below the smallest sub-cell, not above the largest,
  and a stack does not read a multiple of anything.
- The reciprocal share of each sub-cell is the single most useful
  quantity in the clause. It is simultaneously the sub-cell's weight in
  the terminal reading and its share of the applied bias, because
  series capacitors carry equal charge.
- That partition is why a single-junction extraction is wrong rather
  than imprecise. It hands the whole terminal bias to one junction,
  when the dominant junction may be taking only half of it, and the
  built-in voltage and doping that fall out are correspondingly off.
- Tunnel junctions add series resistance the single-junction method
  never budgeted for. With the stack capacitance it sets a corner
  frequency, and a test frequency near that corner reads a capacitance
  rolling off rather than the stack itself.
- A stack in which one sub-cell holds nearly the whole reciprocal sum
  cannot be resolved into its parts at the terminals at all. The other
  junctions are simply not present in the reading, and the honest
  answer is a dedicated single-junction coupon rather than a more
  determined fit.
- Bias polarity has to be checked per sub-cell, not per terminal. A
  forward terminal bias that looks modest divides unevenly, and the
  sub-cell with the largest share can be driven out of depletion while
  the terminal number still looks reasonable.

## Workflow

1. Take the declared stack and refuse it if the sub-cells are unnamed,
   repeated or carry a non-positive capacitance. Everything downstream
   is a share of a reciprocal sum, so one bad member moves every share.
2. Confirm the device actually needs the adaptation. A stack of one is
   the single-junction method's own article and should be sent back to
   it rather than run through this clause.
3. Sum the reciprocals into the terminal capacitance and compute each
   sub-cell's share of that sum.
4. Name the dominant sub-cell from the largest share, and report the
   fraction of the terminal bias a one-junction extraction would
   misattribute to it.
5. Partition the applied terminal bias by the shares and check each
   sub-cell against its own forward ceiling, rather than checking the
   terminal bias against one.
6. Compute the corner the tunnel-junction series resistance sets with
   the terminal capacitance and hold the test frequency well under it.
7. Require the campaign to declare the adaptations it applied, and
   treat an undeclared one as the single-junction method carried over
   unchanged. The verdict stays open while any finding stands.

## Pitfalls

- Multiplying a single-junction capacitance by the junction count.
  Series stacking divides, it does not multiply, and the error is in
  the wrong direction for any stored-energy argument built on top.
- Reading the terminal capacitance as the middle sub-cell's because it
  is the middle one. The reading follows the smallest capacitance, and
  which sub-cell that is depends on doping and thickness rather than on
  position in the stack.
- Extracting a built-in voltage from the terminal sweep. The bias the
  dominant junction sees is a fraction of the applied one, so the
  intercept lands at a voltage that belongs to no junction in the
  device.
- Reusing the single-junction test frequency. The stack capacitance is
  smaller and the tunnel-junction resistance is new, so the corner
  moves, and the frequency that was comfortably low on one junction can
  sit on the roll-off of a stack.
- Checking forward bias at the terminals. The partition is uneven by
  construction, and the sub-cell taking the largest share leaves
  depletion first.
- Comparing a derived share or frequency margin against a written
  ceiling by bare arithmetic. Both are quotients of floats that can
  land a few units in the last place either side of the limit, so the
  comparison absorbs that error while the limit itself is never
  relaxed.
- Fitting harder when one sub-cell dominates the reciprocal sum. The
  information about the other junctions is not in the terminal data to
  be recovered, and a fit that returns them is returning its own
  assumptions.

## Behavior contract (gate 3)

The stack validation, adaptation-necessity test, reciprocal series
summation, per-sub-cell shares, dominant sub-cell identification,
single-junction bias misattribution fraction, bias partition and
per-sub-cell forward ceiling, tunnel-junction corner frequency and its
margin, and the declared-adaptation completeness check are exercised by
the gate 3 contract test:
scripts/test_e2008_multijunction_cell_capacitance_measurement.py against
scripts/e2008_multijunction_cell_capacitance_measurement_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2008_multijunction_cell_capacitance_measurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
