---
name: e2008-reflectance-cut-off-definition
description: "Define the cut-off point of a coverglass reflectance coating. Use when a measured reflectance trace has to yield a defensible cut-off two laboratories would agree on under ECSS-E-ST-20-08C clause 8.7.5.3.1: take the absolute measured peak of the band, halve it, and interpolate the long-wavelength point at which the falling edge reaches that level, refusing a half level taken from a normalised trace, a band too weak to carry one, and a scan that ends before the edge arrives. Trigger: ecss, e-st-20-08c-clause-8-7-5-3-1, coverglass-reflectance-cut-off, half-of-absolute-measured-reflectance, long-wavelength-band-edge-interpolation, reflectance-band-half-level-basis, coating-band-width-between-half-levels."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reflectance-cut-off-definition, coverglass-reflectance-cut-off, half-of-absolute-measured-reflectance, long-wavelength-band-edge-interpolation, reflectance-band-half-level-basis, coating-band-width-between-half-levels]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reflectance Cut-Off Definition (space-systems/ecss/e2008-reflectance-cut-off-definition)

Use when the task is to turn a measured coverglass reflectance trace
into the cut-off the standard means under ECSS-E-ST-20-08C clause
8.7.5.3.1 -- which level the edge is taken at, which side of the band it
is taken on, and what to do when the scan cannot deliver it.

## Domain quick reference

- The cut-off is a definition before it is a number: the long-wavelength
  point at which the falling edge of the reflectance curve reaches half
  of the absolute measured reflectance of the band.
- Three words carry the whole definition. Long-wavelength separates the
  cut-off from the cut-on, which is the same level found on the rising
  side. Absolute ties the level to what the instrument read. Half fixes
  the fraction.
- Absolute means un-normalised. A band peaking at 80 percent has its
  edges at 40; a band peaking at 50 percent has them at 25. The level
  follows the coating, which is precisely why it is reproducible.
- Normalising the trace to a reference before halving is the failure the
  definition is written against. The reported edge then moves with the
  reference, so two laboratories measuring one coverglass publish two
  cut-offs and neither is wrong on its own terms.
- The edge almost never lands on a scanned wavelength, so the crossing
  is interpolated between the two points that straddle the half level.
  Snapping to the nearest scanned point quantises the answer to the step
  size of the monochromator.
- A scan that stops while the band is still flat has not measured a
  cut-off. It has established that the cut-off is somewhere past the end
  of the scan, which is a different and much weaker statement.
- A band too weak to rise clear of the noise has a half level that
  describes the noise. The peak floor is checked before any edge is
  taken from the curve.
- The cut-on is the same construction on the rising side, and the two
  together give the band width. A scan opening inside the band still
  yields a cut-off, but no width, and that shortfall is reported rather
  than filled in.

## Workflow

1. Validate the determination policy first: peak floor, scan-point
   floor, reflectance ceiling and the half-level fraction. A fraction at
   or above the whole band is refused rather than used.
2. Confirm the declared half-level basis is the absolute measured one.
   A normalised or fixed-nominal basis closes on its own verdict, since
   the number it produces is not the quantity this clause names.
3. Validate the trace: increasing wavelengths, reflectance between zero
   and the ceiling, enough points to interpolate across an edge.
4. Take the absolute peak of the band and multiply by the half-level
   fraction. Refuse the band outright when the peak is under the usable
   floor.
5. Walk from the peak toward longer wavelengths for the first pair of
   points that straddle the half level, and interpolate the crossing
   linearly between them.
6. When the falling edge never reaches the level inside the scan, close
   on the beyond-scan verdict and report the wavelength the scan
   actually reached, not an extrapolated edge.
7. Take the rising-edge partner where the scan holds one, derive the
   band width from the pair, and report the missing cut-on as a finding
   where it does not.

## Pitfalls

- Halving a normalised curve. Half of a nominal 100 percent is not half
  of what the coating reflects, and the difference lands directly on the
  reported edge in nanometres.
- Taking the half level from the short-wavelength side. That is the
  cut-on; reporting it as the cut-off inverts the band description and
  survives review because both numbers look plausible.
- Snapping the edge to the nearest scanned point. The resolution of the
  answer then depends on the step size rather than on the coating.
- Extrapolating past the end of a scan. A flat band at the last measured
  wavelength says the edge is beyond it and nothing more.
- Halving a band that never rose. A peak in the noise gives a half level
  in the noise and an edge wherever the noise happened to cross it.
- Reporting a band width when only one edge was measured. The absent
  edge is a gap, not a zero, and the width is simply unavailable.

## Behavior contract (gate 3)

The policy validation, trace validation, absolute peak, half level,
normalised-basis comparison, band strength floor, falling-edge
resolvability, cut-off interpolation, the rising-edge partner, band
width, scan upper limit and the determination verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_reflectance_cut_off_definition.py against
scripts/e2008_reflectance_cut_off_definition_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_reflectance_cut_off_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
