---
name: e2008-sca-thermal-cycling-purpose
description: "Assess whether a solar cell assembly thermal cycling test is earned and whether it represents one year of orbital eclipses under ECSS-E-ST-20-08C clause 6.4.3.7.1: derive the eclipse-driven cycles a year of the declared orbit imposes and the hot-to-cold swing each one drives, group the assembly features that carry a thermal-fatigue failure mode into the reliability objectives the cycling demonstrates, then check the planned cycle count and temperature extremes bound that orbital year instead of falling short of it. Use when scoping or reviewing the purpose of a solar cell assembly thermal cycling test. Trigger: ecss, e-st-20-08c-clause-6-4-3-7-1, solar-cell-assembly-thermal-cycling-purpose, orbital-eclipse-cycle-count, sca-interconnect-thermal-fatigue, eclipse-representative-cycle-budget, sca-cycling-reliability-objectives."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-thermal-cycling-purpose, solar-cell-assembly-thermal-cycling-purpose, orbital-eclipse-cycle-count, sca-interconnect-thermal-fatigue, eclipse-representative-cycle-budget, sca-cycling-reliability-objectives]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies -- Thermal Cycling Test Purpose (space-systems/ecss/e2008-sca-thermal-cycling-purpose)

Use when the task is to state and defend why a thermal cycling test is applied
to a solar cell assembly sample under ECSS-E-ST-20-08C clause 6.4.3.7.1 --
what the cycling is meant to demonstrate about the sample's reliability,
whether the mission's eclipse history justifies it at all, and whether the
planned run actually stands in for the year of orbital eclipses it represents.

## Domain quick reference

- The stress the test reproduces is fatigue, not overload. Each entry into and
  exit from eclipse swings the assembly between its cold and hot extremes, and
  the joints inside it accumulate damage cycle by cycle. A single excursion to
  either extreme tells a reviewer almost nothing about a year of them.
- The cycle count comes from the orbit, not from habit. A year of orbits is the
  year divided by the orbital period, and only the fraction of those orbits
  that carry an eclipse produce a swing. A low orbit gives thousands of cycles
  a year; a long-period orbit gives a few hundred; a full-sun orbit gives none.
- The purpose is specific to what the assembly contains. A welded
  cell-to-interconnect joint, a stress-relief loop, a coverglass adhesive
  bondline, a rear metallization, a bypass diode attachment and a
  cell-to-substrate adhesive each carry a distinct thermal-fatigue failure
  mode, so each turns into a separate reliability objective the cycling
  demonstrates. Output retention is the objective they all share.
- Justification is a joint condition. An assembly with no fatigue-sensitive
  feature does not earn the test however many eclipses the orbit has; a
  full-sun orbit does not earn it however sensitive the assembly is; and a
  swing too small to strain anything does not earn it either.
- A run only serves its purpose when it bounds the orbital year on all three
  counts: at least as many cycles, at least as hot and at least as cold. A run
  milder or shorter than the year it stands in for demonstrates nothing about
  that year.
- A stated purpose is not a served purpose. An assembly that justifies the
  cycling but has no run planned yet is a distinct outcome from one whose
  planned run falls short, and the two carry different actions.

## Workflow

1. Validate the purpose policy first: the minutes in a year, the cycle
   trigger, the minimum stress range and the coverage factor. A coverage
   factor below unity would let the run fall short by construction and is
   refused.
2. Group the declared assembly features, rejecting an unrecognised one rather
   than ignoring it, and map each to the reliability objective it makes the
   cycling demonstrate. Append the shared output-retention objective when any
   sensitive feature is present.
3. Derive the orbital year: the eclipse-driven cycles a year of the declared
   orbit imposes, and the hot-to-cold swing each transition drives. Refuse an
   orbit whose cold extreme is not below its hot extreme.
4. Decide whether the cycling is justified: a fatigue-sensitive feature
   present, an annual cycle count at or above the trigger, and a swing at or
   above the minimum stress range. A value landing exactly on a threshold
   justifies the test; the comparison tolerance absorbs representation error
   and the threshold does not move.
5. When it is justified, check the planned run bounds the orbital year on
   count, hot extreme and cold extreme, and report each count that falls short
   with its planned value and the value it owed.
6. Close on one verdict: not required, justified but not planned, planned but
   under representation, or representing the orbital year, with the objectives
   the cycling serves attached to it.

## Pitfalls

- Quoting a cycle count with no orbit behind it. Four thousand cycles is
  generous for a long-period orbit and short of a year for a low one, so a
  count carried over from a previous programme can silently under-represent
  the mission it is now being used for.
- Counting every orbit as a cycle. Orbits outside the eclipse season produce
  no swing, so multiplying the orbit count by a full year overstates the
  fatigue the assembly actually accumulates and buys test time that
  demonstrates nothing.
- Reading only the cycle count and ignoring the extremes. A run at the right
  count but a narrower swing loads the joints far less per cycle, and the
  fatigue the test was bought to demonstrate never happens.
- Declaring the cycling not required because the assembly looks robust. The
  decision follows the declared feature inventory, so an undeclared bondline
  or metallization silently removes an objective the sample was supposed to
  demonstrate.
- Calling a justified test satisfied because a chamber run happened. A run
  short of the orbital year it represents leaves the purpose unserved, and
  that is a finding rather than a pass.

## Behavior contract (gate 3)

The policy validation, eclipse cycle derivation, orbital stress range, feature
inventory and objective mapping, representation check and purpose verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_sca_thermal_cycling_purpose.py against
scripts/e2008_sca_thermal_cycling_purpose_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_sca_thermal_cycling_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
