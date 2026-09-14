---
name: e2008-reflectance-cut-on-definition
description: "Use when a measured reflectance curve has to yield one defensible cut-on wavelength. Define the reflectance cut-on wavelength of a coverglass coating under ECSS-E-ST-20-08C clause 8.7.5.2.1: take the absolute measured reflectance of the band the scan actually recorded, halve it to fix the crossing level, walk the short-wavelength edge to the first sample pair that straddles that level and interpolate the crossing, report the bracket width as the honest resolution of the answer, and refuse a scan whose shortest wavelength already sits above half. Trigger: ecss, e-st-20-08c-clause-8-7-5-2-1, reflectance-cut-on-wavelength, absolute-measured-reflectance-half-level, coating-short-wavelength-edge, reflectance-crossing-interpolation, coverglass-reflectance-scan-validation."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reflectance-cut-on-definition, reflectance-cut-on-wavelength, absolute-measured-reflectance-half-level, coating-short-wavelength-edge, reflectance-crossing-interpolation, coverglass-reflectance-scan-validation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Reflectance Cut-On Definition (space-systems/ecss/e2008-reflectance-cut-on-definition)

Use when the task is to place the cut-on wavelength of a measured
reflectance curve under ECSS-E-ST-20-08C clause 8.7.5.2.1 -- the short
wavelength point at which reflectance reaches half of the absolute
measured reflectance -- turned into a fixed crossing level, an
interpolated wavelength, the resolution that wavelength is actually
known to, and the cases where no cut-on exists at all.

## Domain quick reference

- The cut-on is a definition, not a threshold. There is no fixed
  percentage: the level is half of whatever absolute reflectance the
  band recorded, so it moves with the article and has to be recomputed
  for every scan rather than carried over from the last one.
- Absolute is the load-bearing word. An instrument reporting
  reflectance as a ratio against a reference mirror is giving a
  relative curve, and half of a relative curve is half of the wrong
  number. The scan is put on an absolute footing before the level is
  taken.
- Measured is the second load-bearing word. The peak that supplies the
  level is the one the scan recorded inside the band of interest, not a
  design plateau and not a datasheet figure.
- Short wavelength is the third. A reflector plateau crosses the half
  level twice, once rising below the band and once falling above it,
  and only the lower crossing is the cut-on. Searching the curve for
  any crossing finds whichever comes first in the array.
- A band window narrows which part of the scan supplies the peak. It is
  not cosmetic: a coating with a weak short-wavelength hump under its
  main band gives one cut-on for the whole scan and a different one for
  a window drawn around the hump, because the window changes the
  absolute reflectance and therefore the half level.
- A scan is a set of samples and the crossing rarely lands on one. The
  pair that straddles the half level fixes the answer by linear
  interpolation, and the wavelength gap between that pair is the
  resolution the result carries -- a crossing bracketed twenty
  nanometres apart is not known to a nanometre however many decimals
  the interpolation prints.
- Two situations have no cut-on rather than a default one. A scan whose
  shortest wavelength already reads above the half level has its edge
  below the measured range, and a band whose absolute reflectance never
  rises to a high reflectance level has nothing worth halving.
- Reflectance is a fraction of unity here. A curve still in per cent is
  refused rather than rescaled, because guessing the unit moves every
  level derived from it without saying so.

## Workflow

1. Validate the scan first: at least two samples, strictly increasing
   wavelength, reflectance finite and inside zero to one. Refuse a
   per cent curve rather than dividing it by a hundred on a guess.
2. Resolve the band window, defaulting to the full scan, and confirm it
   contains at least one sample to take a peak from.
3. Take the absolute measured reflectance as the peak inside that
   window, and record the wavelength it was recorded at.
4. Halve it. That number, not a fixed percentage, is the level the
   crossing is read at.
5. Check the shortest scanned wavelength against the level. Exactly on
   it is the cut-on; above it means the edge is outside the scan and
   the answer does not exist inside this measurement.
6. Walk the samples from the short-wavelength end up to the band peak,
   take the first pair that straddles the level, and interpolate the
   crossing between them. A crossing landing on a sample is reported as
   measured, with no interpolation and no bracket width.
7. Report the cut-on with its bracket, bracket width and edge slope, so
   the resolution travels with the number, and judge the bracket
   against the declared sampling requirement before the figure is
   quoted.

## Pitfalls

- Halving a relative reflectance curve. The definition names the
  absolute measured reflectance, and a curve referenced to a mirror
  gives a level that belongs to the mirror.
- Halving a design plateau instead of the measured peak. The level is
  defined against what this article recorded; a datasheet figure moves
  the cut-on by however much the coating run differs.
- Taking the first crossing found in the array. A plateau crosses the
  half level on both sides, and the falling crossing is a cut-off, not
  a cut-on.
- Quoting the interpolated wavelength to more precision than the scan
  carries. The bracketing samples set the resolution, and a coarse scan
  prints decimals it did not measure.
- Letting a short-wavelength hump supply the peak. Without a band
  window the absolute reflectance comes from the tallest feature
  anywhere in the scan, which may not be the band being characterised.
- Defaulting a missing cut-on to the first wavelength. A scan that
  starts above the half level has no cut-on inside it, and reporting
  its lower bound as the answer turns a truncated measurement into a
  number nobody can retract.
- Comparing a reflectance against the half level by bare arithmetic.
  The level is a product of a measured value, so a sample meant to sit
  exactly on it can evaluate a few units in the last place to either
  side; the comparison absorbs that representation error while the
  level stays untouched.

## Behavior contract (gate 3)

The scan and band-window validation, the absolute measured reflectance
and its half level, the short-wavelength crossing with its
interpolation, bracket width and edge slope, the on-sample and
truncated-edge cases, and the determination verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_reflectance_cut_on_definition.py against
scripts/e2008_reflectance_cut_on_definition_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_reflectance_cut_on_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
