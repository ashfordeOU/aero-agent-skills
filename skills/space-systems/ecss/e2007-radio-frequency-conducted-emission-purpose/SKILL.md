---
name: e2007-radio-frequency-conducted-emission-purpose
description: "Use when verify that the radio-frequency conducted-emission aim of ECSS-E-ST-20-07C clause 5.4.3.1 is actually demonstrated: confirm the power-input lead and its matching power-return lead are both swept, confirm each sweep reaches both edges of the declared method band, compute the margin between every recorded level and the applicable conducted-emission limit, categorize each frequency as within-limit, at-limit or an exceedance, reduce every lead to its worst-case frequency, name the governing lead, and refuse a record whose frequencies do not increase or whose return lead is absent. Trigger: ecss, e-st-20-07c, rf-conducted-emission-purpose, power-input-lead-emission, power-return-lead-emission, conducted-emission-limit-margin, conducted-method-band-coverage, governing-emission-lead."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radio-frequency-conducted-emission-purpose, rf-conducted-emission-purpose, power-input-lead-emission, power-return-lead-emission, conducted-emission-limit-margin, conducted-method-band-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radio-Frequency Conducted Emission, Method Purpose (space-systems/ecss/e2007-radio-frequency-conducted-emission-purpose)

Use when the task is the aim statement of ECSS-E-ST-20-07C clause
5.4.3.1 -- establishing what the higher-band conducted-emission method
is run to show, namely that the radio-frequency current the unit puts
back onto its power-input lead and onto the matching power-return lead
stays inside the applicable limit everywhere in the method band.

## Domain quick reference

- The aim is stated over a pair of leads, not over a unit. The lead
  carrying power in and the lead carrying it back are separate
  measurement objects with their own recorded levels, and a record
  covering only one of them cannot demonstrate the aim at all. That is
  a structural defect in the record, not a low score.
- The quantity graded is a margin: the applicable limit at a frequency
  minus the level recorded at that frequency. A positive margin is
  compliance, a negative margin is an exceedance, and a margin of zero
  is a level sitting exactly on the limit -- compliant, but carried as
  a limitation because there is nothing left to absorb measurement
  uncertainty.
- Margin is a difference of two decibel values, so an exactly-on-limit
  case can land a few units in the last place either side of zero.
  That is absorbed with a named tolerance inside the comparison, never
  by moving the applicable limit.
- The aim is stated across the whole method band. A sweep that starts
  above the lower edge or stops below the upper edge has not shown the
  aim over the band it claims, so the edges are checked in their own
  right and a shortfall is a finding, not a silent pass. A project
  that has formally accepted a reduced span records it as a
  limitation instead.
- The governing result is the worst lead at its worst frequency. An
  average over frequencies, or over the two leads, hides exactly the
  narrowband peak the method exists to find.
- The purpose clause fixes the objective; it does not fix the
  equipment or the bench. Those belong to the equipment and setup
  clauses of the same method and are graded separately.

## Workflow

1. Validate the declared method band: a positive lower edge and an
   upper edge strictly above it. An inverted or collapsed band is an
   input error, not a degenerate case to clamp.
2. Normalize the lead roles and reject a duplicate declaration.
   Confirm both the power-input lead and the power-return lead are
   present, and reject the record when either is missing.
3. Validate each sweep: at least one point, strictly increasing
   positive frequencies, and a recorded level plus an applicable
   limit at every point.
4. Check band coverage per lead against both edges, allowing only a
   named relative slack at an edge.
5. Compute the margin at every frequency and categorize it as
   within-limit, at-limit or an exceedance, absorbing representation
   error at zero with the named decibel tolerance.
6. Reduce each lead to its worst-case frequency, breaking an exact
   tie on the lower frequency so the selection is reproducible, then
   reduce the set of leads to the governing lead.
7. Report the verdict with its findings (exceedances, band
   shortfalls) and its limitations (on-limit frequencies, formally
   waived spans). The aim is demonstrated only when no finding
   stands.

## Pitfalls

- Grading the input lead and assuming the return follows. The return
  lead routinely carries the higher conducted level, and the aim is
  stated over both.
- Averaging a sweep into one number. The method exists to find a
  narrowband peak; an average over the band buries it.
- Reading a margin of zero as an exceedance, or as a comfortable
  pass. It is neither: it is compliance with no measurement headroom,
  and it belongs in the limitations.
- Accepting a sweep that never reached a band edge because every
  recorded point passed. Points that were never recorded cannot pass;
  an untested edge is a coverage finding.
- Widening the applicable limit so an on-limit case reads as clearly
  compliant. The representation question is handled by the tolerance
  inside the comparison; the limit stays as specified.

## Behavior contract (gate 3)

The band validation, lead-pair completeness check, sweep validation,
band-coverage check, margin categorization, worst-case reduction and
governing-lead selection are exercised by the gate 3 contract test:
scripts/test_e2007_radio_frequency_conducted_emission_purpose.py
against
scripts/e2007_radio_frequency_conducted_emission_purpose_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radio_frequency_conducted_emission_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
