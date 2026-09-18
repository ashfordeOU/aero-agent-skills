---
name: e2007-radiated-electric-emission-purpose
description: "Assess whether the radiated electric-field aim of ECSS-E-ST-20-07C clause 5.4.6.1 is demonstrated: confirm the unit enclosure and the interconnecting cabling are both scanned in vertical and horizontal polarization, confirm every scan reaches both edges of the declared method band, compute the margin between each recorded field strength and the applicable radiated limit, categorize every frequency as within-limit, at-limit or an exceedance, reduce each scan to its worst-case frequency, and name the governing emitter. Use when a record has to show that what the unit and its harness radiate stays inside the applicable limit. Trigger: ecss, e-st-20-07c, radiated-electric-emission-purpose, unit-enclosure-field-emission, interconnecting-cabling-field-emission, radiated-emission-limit-margin, antenna-polarization-scan-pair, governing-radiated-emitter."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-emission-purpose, radiated-electric-emission-purpose, unit-enclosure-field-emission, interconnecting-cabling-field-emission, radiated-emission-limit-margin, antenna-polarization-scan-pair]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Emission, Method Purpose (space-systems/ecss/e2007-radiated-electric-emission-purpose)

Use when the task is the aim statement of ECSS-E-ST-20-07C clause
5.4.6.1 -- establishing what the radiated electric-field emission
method is run to show, namely that the field radiated by the unit
itself and by the interconnecting cabling harnessed to it stays inside
the applicable radiated-emission limit everywhere in the method band.

## Domain quick reference

- The aim is stated over what radiates, and that is two things, not
  one. The enclosure leaks through seams, apertures and windows; the
  cabling run to and from the unit is an efficient antenna in its own
  right and routinely dominates the lower decades. A record covering
  only the box has not addressed the aim, and that is a structural
  defect in the record rather than a low score.
- A field is a vector. An antenna responds to one projection of it, so
  a scan taken in a single polarization measures part of what is
  there. The aim is stated over the polarization pair, and a record
  with only one plane is refused for the same reason a single-emitter
  record is.
- The quantity graded is a margin: the applicable limit at a frequency
  minus the field strength recorded at it. Positive is compliance,
  negative is an exceedance, and zero is a field sitting exactly on
  the limit -- compliant, but carried as a limitation because nothing
  is left to absorb measurement uncertainty.
- Margin is a difference of two decibel values, so an exactly-on-limit
  case can land a few units in the last place either side of zero.
  That is absorbed with a named tolerance inside the comparison, never
  by moving the applicable limit.
- The aim is stated across the whole method band, which spans several
  decades and several antennas. A scan that starts above the lower
  edge or stops below the upper edge has not shown the aim over the
  band it claims, so both edges are checked in their own right. A
  project that has formally accepted a reduced span records it as a
  limitation instead.
- The governing result is the worst emitter, in its worst
  polarization, at its worst frequency. Averaging over frequencies, or
  over the two planes, buries exactly the narrowband peak the method
  exists to find.
- The purpose clause fixes the objective; it does not fix the
  instruments or the bench. Those belong to the equipment and setup
  clauses of the same method and are graded separately.

## Workflow

1. Validate the declared method band: a positive lower edge and an
   upper edge strictly above it. An inverted or collapsed band is an
   input error, not a degenerate case to clamp.
2. Normalize the emitter and polarization designations, reject a
   duplicate declaration, and refuse the record when any of the four
   emitter/polarization combinations was never recorded.
3. Validate each scan: at least one point, strictly increasing
   positive frequencies, and a recorded field strength plus an
   applicable limit at every point.
4. Check band coverage per scan against both edges, allowing only a
   named relative slack at an edge.
5. Compute the margin at every frequency and categorize it as
   within-limit, at-limit or an exceedance, absorbing representation
   error at zero with the named decibel tolerance.
6. Reduce each scan to its worst-case frequency, breaking an exact tie
   on the lower frequency so the selection is reproducible, then
   reduce the four scans to the governing emitter and plane.
7. Report the verdict with its findings (exceedances, band shortfalls)
   and its limitations (on-limit frequencies, formally waived spans).
   The aim is demonstrated only when no finding stands.

## Pitfalls

- Scanning the enclosure and assuming the harness follows. Below a
  gigahertz the cabling is usually the better radiator, and the aim is
  stated over both.
- Recording one polarization because the peak looked higher there
  during the pre-scan. The plane carrying the peak changes with
  frequency, and the aim is stated over the pair.
- Averaging a scan into one number. The method exists to find a
  narrowband peak; an average across several decades buries it.
- Reading a margin of zero as an exceedance, or as a comfortable pass.
  It is neither: it is compliance with no measurement headroom, and it
  belongs in the limitations.
- Accepting a scan that never reached a band edge because every
  recorded point passed. Points that were never recorded cannot pass;
  an untested edge is a coverage finding.
- Widening the applicable limit so an on-limit case reads as clearly
  compliant. The representation question is handled by the tolerance
  inside the comparison; the limit stays as specified.

## Behavior contract (gate 3)

The band validation, emitter and polarization completeness check,
scan validation, band-coverage check, margin categorization,
worst-case reduction and governing-emitter selection are exercised by
the gate 3 contract test:
scripts/test_e2007_radiated_electric_emission_purpose.py
against
scripts/e2007_radiated_electric_emission_purpose_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_emission_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
