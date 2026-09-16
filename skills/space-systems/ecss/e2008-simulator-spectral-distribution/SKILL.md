---
name: e2008-simulator-spectral-distribution
description: "Use when a simulator spectrum record has to be graded before test data is credited. Verify that a solar simulator's output follows the air mass zero reference spectrum closely enough to credit a measurement made under it, per ECSS-E-ST-20-08C clause 10.1.1: integrate both curves band by band with the edges interpolated onto the samples, compare each band's share of its own total rather than raw irradiance, grade every band inside a nested limit table and take the worst band as the result rather than an average, check the delivered level separately because a share comparison cancels it, and confirm the band set spans the reference. Trigger: ecss, e-st-20-08c, clause-10-1-1, solar-simulator-am0-spectral-match, solar-simulator-spectral-band-share-ratio, solar-simulator-irradiance-level-check, solar-simulator-reference-band-coverage."
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
  tags: [ecss, e-st-20-08-solar-simulator-scope, e2008-simulator-spectral-distribution, e-st-20-08c-clause-10-1-1, solar-simulator-am0-spectral-match, solar-simulator-spectral-band-share-ratio, solar-simulator-irradiance-level-check, solar-simulator-reference-band-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Simulators -- Spectral Distribution (space-systems/ecss/e2008-simulator-spectral-distribution)

Use when the task is clause 10.1.1 of ECSS-E-ST-20-08C: a solar
simulator has been measured and the question is whether what it emits
follows the air mass zero reference closely enough for a measurement
taken under it to be credited.

## Domain quick reference

- Three arms have to close, not one: the shape of the spectrum, the level
  it is delivered at, and the span of reference the comparison was made
  over. Each has its own way of going quietly green.
- The shape arm compares SHARES, not irradiances. The reference curve and
  the simulator measurement rarely arrive in the same units or at the
  same working distance, so each band's fraction of its own band-set
  total is what makes the two comparable without pretending a calibration
  is shared.
- The grade of the whole simulator is the WORST band, never an average. A
  lamp that matches in five bands and misses badly in the sixth is a lamp
  that misses, and averaging the six hides exactly the band a narrow
  spectral response would have been measured in.
- Dividing each band by the total cancels the total. That is what makes
  the shape arm scale-free and it is also why the shape arm cannot see
  the level: a simulator can follow the reference distribution perfectly
  at half the irradiance and every share ratio will still read unity.
- So the level is a separate arm. The integrated total across the band
  set is taken against the declared target under its own fractional
  tolerance, and a spectrum that passes the shape arm can still fail here.
- The band set is an input, not a fact, and a band set that spans only
  the comfortable part of the reference makes both other arms easy. The
  reference irradiance the bands enclose is therefore taken against the
  reference irradiance over its whole measured range.
- Band edges are interpolated onto the measured curve before integration,
  so a boundary falling between two samples is honoured rather than
  snapped to the nearest measurement and quietly moved.
- The band set has to be contiguous. A gap between two bands is
  irradiance belonging to neither share, and it leaves both totals
  without appearing in either.
- The grade limits are a nested ladder around unity: each grade contains
  the one tighter than it. A table that does not nest is not a ladder,
  because a ratio could then sit in a looser grade while failing a
  tighter one that does not enclose it.
- A share ratio landing exactly on a grade limit keeps the better grade,
  and the comparison absorbs representation error rather than moving the
  limit.
- A reference band carrying no irradiance has no share ratio at all.
  That is a refusal, not a zero: dividing by an empty reference band
  invents a number the measurement does not contain.

## Workflow

1. Validate both curves: wavelengths rise strictly, irradiance is never
   negative, and each carries at least two samples.
2. Validate the band set: at least two bands, each rising, contiguous
   with its neighbour, and lying inside both measured ranges.
3. Integrate each band on both curves by the trapezoidal rule with the
   band edges interpolated onto the samples.
4. Form each band's share of its own band-set total on both curves, and
   divide the simulator share by the reference share to get the band's
   share ratio.
5. Grade every band against the nested limit table under a named
   tolerance, and take the worst band as the simulator's grade.
6. Compare the simulator's integrated total across the band set with the
   declared target under its own fractional tolerance.
7. Compare the reference irradiance enclosed by the band set with the
   reference irradiance over its whole measured range, against the
   declared coverage floor.
8. Report each arm's findings with the worst band named, and accept only
   when the finding list is empty.

## Pitfalls

- Averaging the band ratios. The average of a good five and a bad one is
  a pass, and the bad band is the one a narrow-response article would
  have been measured in.
- Comparing raw irradiances instead of shares. Two curves in different
  units at different working distances disagree everywhere, and the
  disagreement says nothing about the shape.
- Reading the shape arm as a level check. Normalising by the total is
  what cancels the total; a simulator at half the intended irradiance
  reads as a perfect match on every band ratio it has.
- Treating the band set as given. A band set that stops short of the
  reference makes the match easy in exactly the region where the lamp is
  well behaved, and the coverage arm is the only thing that notices.
- Leaving a gap between bands. The irradiance in the gap belongs to
  neither share, so it silently leaves both totals and both look tidier
  than they are.
- Snapping a band edge to the nearest sample. A boundary that falls
  between two measurements has been moved, and the band it moved into
  gained irradiance the standard never gave it.
- Using a grade table that does not nest. A ratio can then fail a tighter
  grade while sitting inside a looser one that does not contain it, and
  the ladder stops ordering anything.
- Moving a grade limit to pass a ratio that sits exactly on it. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the declared limit stays as declared.
- Returning zero for a reference band with no irradiance. There is no
  share ratio there to return, and a zero reads as a measured mismatch
  rather than as an absent reference.
- Reporting a bare rejection. An off-shape band, a wrong level and a
  short band set each reject the simulator for a different reason, and
  the report names which band was worst.

## Behavior contract (gate 3)

The strictly rising curve validation, the contiguous band set with its
range check against both curves, the trapezoidal integration with band
edges interpolated rather than snapped, the share formation on each
curve's own band-set total, the per-band share ratio with an empty
reference band refused, the nested grade limit table with its project
override, the worst-band grade selection, the separate level arm against
the declared target and fractional tolerance, the reference coverage arm
against the declared floor, and the conjunctive simulator verdict with
the worst band named are exercised by the gate 3 contract test:
scripts/test_e2008_simulator_spectral_distribution.py against
scripts/e2008_simulator_spectral_distribution_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_simulator_spectral_distribution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
