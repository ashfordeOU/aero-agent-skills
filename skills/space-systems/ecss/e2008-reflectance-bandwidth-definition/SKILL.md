---
name: e2008-reflectance-bandwidth-definition
description: "Derive the fractional reflectance bandwidth of a coverglass filter from its cut-on and cut-off wavelengths per ECSS-E-ST-20-08C clause 8.7.5.4.1: validate the edge pair, take the span between them, divide it by the band centre under a declared arithmetic or geometric convention, report the figure as a fraction and as a percentage, invert it back to the edge pair so a declared bandwidth and centre can be checked, and quantify how far the two centre conventions separate before a figure changes meaning. Use when a coverglass bandwidth figure has to be computed, converted or reconciled. Trigger: ecss, e-st-20-08c-clause-8-7-5-4-1, coverglass-reflectance-fractional-bandwidth, coverglass-cut-on-cut-off-span, band-centre-wavelength-convention, geometric-band-centre-inversion, coverglass-bandwidth-percent-conversion."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reflectance-bandwidth-definition, e-st-20-08c, coverglass-reflectance-fractional-bandwidth, coverglass-cut-on-cut-off-span, band-centre-wavelength-convention, geometric-band-centre-inversion, coverglass-bandwidth-percent-conversion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reflectance Bandwidth Definition (space-systems/ecss/e2008-reflectance-bandwidth-definition)

Use when the task is clause 8.7.5.4.1 of ECSS-E-ST-20-08C: stating what
the reflectance bandwidth of a filtered coverglass actually is, so that
one number can stand for the pair of band edges that produced it.

## Domain quick reference

- The bandwidth is a ratio, not a width. It is the span from cut-on to
  cut-off divided by the wavelength at the centre of the band, so it is
  dimensionless, and two filters of very different absolute width in
  nanometres can carry the same figure.
- Scaling both edges together leaves the figure untouched. That is the
  point of the definition -- it describes the shape of the band rather
  than where the band sits -- and it is also the definition's blind spot,
  because a band that has translated bodily still reports the same
  bandwidth.
- "Centre of the band" is two different wavelengths. The arithmetic mean
  of the edges and their geometric mean coincide only for an
  infinitesimally narrow band; for every real one the arithmetic mean is
  the larger, so it always produces the smaller bandwidth figure.
- The size of that gap tracks the width of the band. It is a fraction of
  a per cent for a narrow filter and tens of per cent for a band spanning
  an octave or more, so a wide-band figure quoted without its convention
  is not a figure anybody can use.
- The unit has to travel too. The same quantity appears as a fraction in
  one document and as a percentage in the next, and a bare 0.4 beside a
  bare 40 describes one filter twice. A fraction large enough that it
  could only have been a percentage is refused rather than used.
- The definition inverts in closed form, and that is what makes it
  checkable. Under an arithmetic centre the edges sit half a span either
  side of it. Under a geometric centre, with the square root of the edge
  ratio written as one unknown, the bandwidth is that unknown minus its
  reciprocal, so the unknown is the positive root of a quadratic and the
  edges are the centre divided and multiplied by it.
- An edge pair, a stated centre and a stated bandwidth are three numbers
  with one degree of freedom between them. Any two determine the third,
  so a statement carrying all three can be internally false, and the
  edges are the measurement that arbitrates.

## Workflow

1. Validate the edge pair first: both wavelengths finite and positive,
   and the cut-off strictly above the cut-on. A zero or inverted span has
   no bandwidth and is refused rather than returned as zero.
2. Resolve the centre convention. An unrecognised convention is an error,
   not a silent default to the arithmetic mean.
3. Take the span, take the centre under that convention, and divide.
4. Report the result as a fraction and as a percentage together, so the
   figure cannot be copied onward without its unit.
5. Report both conventions and the separation between them alongside the
   requested one, so a reader can see at a glance whether the choice of
   centre matters for this band.
6. When a bandwidth and a centre are given instead of edges, invert the
   definition to recover the edge pair -- by half-span for an arithmetic
   centre, by the quadratic root for a geometric one -- and refuse an
   arithmetic bandwidth at or above two, which would put the cut-on at or
   below zero wavelength.
7. When all three numbers are stated, check them field by field against
   the edge pair and report which one disagrees rather than declaring the
   statement merely inconsistent.

## Pitfalls

- Quoting the span in nanometres as the bandwidth. That is the numerator
  only, and it makes a wide filter at long wavelengths look worse than a
  narrow filter at short ones when they are the same design.
- Switching centre convention between the drawing and the report. The
  figure moves by a fraction of a per cent on a narrow band and by tens
  of per cent on a wide one, and nothing in the number itself shows that
  it happened.
- Mixing a fraction and a percentage. A figure of 0.4 and a figure of 40
  are the same band, and a comparison between them fails a filter that is
  exactly on target.
- Averaging the edges when the band is wide. The geometric centre is the
  one that keeps the two edges symmetric in ratio, which is what a filter
  edge pair actually is; the arithmetic mean sits above it and quietly
  shrinks the reported bandwidth.
- Reading an unchanged bandwidth as an unchanged band. The ratio is blind
  to a bodily shift of both edges, so the centre wavelength has to be
  carried beside it.
- Inverting an arithmetic bandwidth of two or more. There is no such
  band; the cut-on lands at or below zero wavelength, and the arithmetic
  is telling you the convention was wrong.
- Comparing a stated figure with a derived one by bare equality. The
  derived value comes from a division and a square root, so it can sit a
  few units in the last place away from an exactly equal statement; the
  comparison absorbs that representation error rather than widening any
  engineering limit.

## Behavior contract (gate 3)

The edge-pair validation, convention and unit resolution, arithmetic and
geometric band centres, the fractional and percentage bandwidth, the
scaling invariance, the reported separation between the two conventions,
the closed-form inversion under both conventions and the field-by-field
band statement check are exercised by the gate 3 contract test:
scripts/test_e2008_reflectance_bandwidth_definition.py against
scripts/e2008_reflectance_bandwidth_definition_logic.py (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e2008_reflectance_bandwidth_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
