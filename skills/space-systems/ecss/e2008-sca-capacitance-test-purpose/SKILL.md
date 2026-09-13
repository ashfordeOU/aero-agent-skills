---
name: e2008-sca-capacitance-test-purpose
description: "Derive a panel-level capacitance figure from measured solar cell assembly samples under ECSS-E-ST-20-08C clause 6.4.3.16.1: take the mean and relative standard error of the assembly readings, convert them to a specific capacitance per active area, check that against the reference for the cell technology, then scale through the series and parallel topology into the panel value and the stored charge, arc energy and displacement current the declared panel behaviours respond to. Use when an assembly capacitance number is about to be extrapolated to a panel nobody can measure. Trigger: ecss, e-st-20-08c-clause-6-4-3-16-1, sca-capacitance-test-purpose, assembly-to-panel-capacitance-extrapolation, assembly-specific-capacitance-per-area, panel-stored-charge-and-arc-energy, capacitance-sample-standard-error, sca-sample-representativeness-band."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-capacitance-test-purpose, sca-capacitance-test-purpose, assembly-to-panel-capacitance-extrapolation, assembly-specific-capacitance-per-area, panel-stored-charge-and-arc-energy, capacitance-sample-standard-error, sca-sample-representativeness-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies -- Capacitance Test Purpose (space-systems/ecss/e2008-sca-capacitance-test-purpose)

Use when the task is to state and defend why the capacitance of a solar cell
assembly is measured under ECSS-E-ST-20-08C clause 6.4.3.16.1 -- which is not
a question about the assembly at all. The number exists so that a panel value
can be produced without building and measuring a panel, so the purpose stands
or falls on whether the sample supports that extrapolation.

## Domain quick reference

- A solar cell assembly is a junction, a coverglass and an adhesive stack over
  a substrate, so it holds charge. At the assembly scale that charge is
  negligible. At the panel scale it is what feeds an arc, loads a regulator
  and couples a transient into the harness.
- The panel cannot be measured when the answer is needed. It is built late,
  it is large, and the bus design that consumes the figure is frozen earlier.
  The assembly is the only article available in time, which is why the clause
  asks for assembly data that extrapolates rather than a panel test.
- Specific capacitance -- the assembly value divided by its active area -- is
  the quantity that carries across scale. A raw farad figure from a coupon of
  one cell size says nothing about a panel built from another.
- Representativeness is an independent check, not a restatement. The measured
  specific value is compared with the declared reference for the cell
  technology; a sample that misses that band is a correct measurement of an
  article the panel is not being built from.
- Precision propagates. The panel figure inherits the relative standard error
  of the assembly sample mean, so two readings with wide scatter produce a
  panel value whose uncertainty swamps the margin it was meant to prove.
- Topology, not area, sets the panel value: assemblies in series divide the
  capacitance, strings in parallel multiply it. A long-string, few-string
  panel can end up with less capacitance than a short-string one of the same
  area, which is the opposite of the intuition.
- The extrapolation's whole output is three panel quantities -- stored charge
  at the bus working point, the energy an arc can draw from it, and the
  displacement current a step in the working point pushes. Each is linear in
  the panel capacitance, so an extrapolation error propagates to all three.
- A panel value too small to move any of those does not earn the campaign,
  however many behaviours are declared against it.

## Workflow

1. Validate the extrapolation policy first: minimum sample count, the
   relative standard error the panel figure may inherit, the
   representativeness band and the significance trigger. A basis of one
   assembly is refused rather than used -- it reports no scatter.
2. Group the declared panel behaviours, rejecting an unrecognised one rather
   than ignoring it, and map each to the panel quantity the extrapolated
   capacitance feeds it. Append the shared objective whenever any behaviour
   is present. No behaviour means nothing is being extrapolated toward.
3. Reduce the assembly readings to a mean, a sample standard deviation and a
   relative standard error. Keep the count: it is what the precision and the
   adequacy of the basis both rest on.
4. Convert the mean to a specific capacitance per active area and compare it
   with the declared reference for the cell technology -- an input the
   measurement did not produce, so the check can actually fail.
5. Scale through the series and parallel topology into the panel value, and
   derive the stored charge, arc energy and displacement current from it.
   These are reported whatever the verdict; they are what the number was
   wanted for.
6. Test the panel value against the significance trigger before grading the
   basis. A value landing exactly on the trigger earns the campaign; the
   comparison tolerance absorbs representation error and the trigger does not
   move.
7. Close on one verdict: panel characterisation not required, assembly
   measurement not planned, extrapolation inadequate, or panel capacitance
   characterised -- reporting every inadequacy found, not only the first.

## Pitfalls

- Quoting the assembly farad figure as the answer. It is three or four orders
  below the panel value and the topology moves it in both directions, so it
  is never the number the bus analysis needs.
- Measuring one assembly. It produces a mean with no scatter behind it, and
  the panel figure it supports has an uncertainty nobody can state.
- Checking representativeness against the sample's own specific capacitance.
  That comparison shares its expression with the measurement and cannot fail
  with it; the reference for the cell technology has to come from outside.
- Extrapolating by area alone. Doubling the panel area at twice the string
  length leaves the capacitance where it was, and an area-only scaling
  reports a doubling that is not there.
- Reporting the panel capacitance without the stored charge, arc energy and
  displacement current. The farad value alone leaves every downstream
  analysis to redo the same arithmetic from it.
- Running the campaign because a behaviour was declared. A panel value under
  the significance trigger cannot move any of the three quantities, and the
  sample hardware is spent for nothing.

## Behavior contract (gate 3)

The policy validation, the sample mean, scatter and relative standard error,
the specific capacitance and representativeness ratio, the sample count and
precision checks, the series and parallel panel scaling, the panel stored
charge, arc energy and displacement current, the behaviour inventory and
objective mapping, and the purpose verdict are exercised by the gate 3
contract test: scripts/test_e2008_sca_capacitance_test_purpose.py against
scripts/e2008_sca_capacitance_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_capacitance_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
