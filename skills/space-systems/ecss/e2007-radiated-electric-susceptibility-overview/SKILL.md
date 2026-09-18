---
name: e2007-radiated-electric-susceptibility-overview
description: "Verify that a radiated electric field susceptibility run demonstrates the aim ECSS-E-ST-20-07C clause 5.4.11.1 introduces: the unit and its interconnecting cabling both keep working under a strong field across a wide band. Use when the method is introduced, planned or its record reviewed: confirm both exposure objects are swept, check each sweep reaches both edges of the declared band, compute the margin between the field applied and the field required at every frequency, group each point as at level, under level or overtested, mark a monitored degradation with the frequency it begins at, and name the governing object. Trigger: ecss, e-st-20-07c, radiated-electric-susceptibility-overview, electric-field-exposure-band-coverage, harness-field-exposure, applied-field-margin, susceptibility-degradation-threshold, radiated-electric-aim-demonstration."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-susceptibility-overview, electric-field-exposure-band-coverage, harness-field-exposure, applied-field-margin, susceptibility-degradation-threshold, radiated-electric-aim-demonstration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Susceptibility, Method Overview (space-systems/ecss/e2007-radiated-electric-susceptibility-overview)

Use when the task is the introductory clause of ECSS-E-ST-20-07C
clause 5.4.11.1 -- establishing what the radiated electric
susceptibility method is run to show, namely that the unit and the
cabling running into it both go on performing while an electric field
of the required strength is applied to them over a wide band.

## Domain quick reference

- The aim names two exposure objects, not one. The enclosure of the
  unit and the interconnecting cabling are separate objects with their
  own sweeps, because they couple the field in different ways: the
  enclosure through apertures and seams, the harness as a wire picking
  up a field along its length. A run that exposes only the box has not
  demonstrated the aim, and no amount of level on the box makes up for
  it.
- The graded quantity per frequency is a margin between the field
  applied and the field required, taken in decibels. Applying exactly
  the required strength is compliance. Applying less means that
  frequency was never taken to the requirement, which is a finding
  about the run rather than a result about the unit. Applying more is
  an overtest: compliant, carried as a limitation, and worth naming
  because it can stress hardware past what qualification intended.
- A field margin is a ratio taken to decibels, so an applied field
  sitting exactly on the requirement can land a few units in the last
  place either side of zero. That is absorbed with a named tolerance
  inside the comparison, never by moving the required strength.
- The aim is stated across a wide band, so both edges are checked in
  their own right. A sweep that starts above the lower edge or stops
  below the upper edge has not shown the aim over the band it claims,
  and the gap is a finding rather than a silent pass.
- A degradation seen while the field is applied is the result the
  method exists to find. What matters is not only that it happened but
  the lowest frequency it happened at, because that threshold is what
  a fix or a waiver is written against.
- The introductory clause fixes the objective. The instruments that
  raise the field, the bench layout and the way performance is watched
  belong to the equipment, setup and monitoring clauses of the same
  method and are graded there.

## Workflow

1. Validate the declared method band: a positive lower edge and an
   upper edge strictly above it. An inverted or collapsed band is an
   input error, not a degenerate case to clamp.
2. Normalize the exposure object of each record, reject a duplicate
   declaration, and name any of the two objects that never appears.
3. Validate each sweep: at least one point, strictly increasing
   positive frequencies, a positive applied and required field at
   every point, and a boolean monitored response.
4. Check band coverage per object against both edges, allowing only a
   named relative slack at an edge.
5. Compute the field margin at every frequency and group it as at
   level, under level or above level, absorbing representation error
   at zero with the named decibel tolerance.
6. Reduce each object to its worst point, breaking an exact tie on the
   lower frequency so the selection is reproducible, and take the
   lowest degraded frequency as the susceptibility threshold.
7. Aggregate: an absent object, a band shortfall, an under-level
   frequency or a monitored degradation are findings; an overtested
   frequency is a limitation. The aim is demonstrated only when no
   finding stands.

## Pitfalls

- Exposing the unit and leaving the harness in the shadow of the
  turntable. The cabling is an exposure object in its own right, and a
  field that never reaches it demonstrates nothing about it.
- Reading the forward power and assuming the field. The graded
  quantity is field strength at the unit, and the two part company as
  soon as the amplifier compresses or the antenna is mismatched.
- Averaging the margin over the band. The method exists to find the
  one frequency where the unit stops performing, and an average is the
  most reliable way to hide it.
- Recording that a degradation occurred without the frequency it
  started at. A susceptibility with no threshold cannot be fixed,
  waived or retested against.
- Accepting a sweep that stops short of the upper edge because the
  amplifier ran out there. That is exactly the finding the coverage
  check exists to raise; a formally accepted reduced span belongs on
  the record as a limitation instead.

## Behavior contract (gate 3)

The band validation, exposure-object normalization and completeness
check, sweep validation, per-frequency field margin and grouping, band
coverage, degradation threshold, governing-point selection and the
aggregate verdict are exercised by the gate 3 contract test:
scripts/test_e2007_radiated_electric_susceptibility_overview.py
against
scripts/e2007_radiated_electric_susceptibility_overview_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_susceptibility_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
