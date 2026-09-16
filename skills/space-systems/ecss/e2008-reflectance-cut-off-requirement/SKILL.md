---
name: e2008-reflectance-cut-off-requirement
description: "Use when a measured coverglass cut-off has to become an acceptance verdict. Verify that the reflectance cut-off wavelength measured on a coverglass agrees with the figure fixed in the coverglass source control drawing per ECSS-E-ST-20-08C clause 8.7.5.3.3: refuse a requirement carrying no drawing reference, locate the reflecting plateau in each measured spectrum, interpolate the long-wavelength crossing that defines the cut-off, compare every article against the drawing value and its tolerance band with a tie admissible, report the deviation and the share of tolerance consumed, and raise spread and one-sided-bias advisories a pass would otherwise hide. Trigger: ecss, e-st-20-08c-clause-8-7-5-3-3, coverglass-reflectance-cut-off-wavelength, coverglass-source-control-drawing-value, cut-off-crossing-interpolation, coverglass-cut-off-tolerance-band, coverglass-cut-off-bias-advisory."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reflectance-cut-off-requirement, e-st-20-08c, coverglass-reflectance-cut-off-wavelength, coverglass-source-control-drawing-value, cut-off-crossing-interpolation, coverglass-cut-off-tolerance-band, coverglass-cut-off-bias-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reflectance Cut-Off Requirement (space-systems/ecss/e2008-reflectance-cut-off-requirement)

Use when the task is the clause 8.7.5.3.3 acceptance decision of
ECSS-E-ST-20-08C: a filtered coverglass has been measured, and the
long-wavelength edge of its reflecting band is admissible only when it
agrees with the cut-off figure the coverglass source control drawing
fixes.

## Domain quick reference

- The figure comes from the source control drawing, not from the coating
  vendor's datasheet, not from house practice and not from the last
  build. A verdict quoted with no drawing reference behind it is not a
  verdict against this clause, so an unreferenced requirement closes the
  assessment instead of passing it.
- The cut-off is derived, not read. A reflectance scan is a sampled
  curve and the edge almost never lands on a sampled wavelength, so the
  edge is the interpolated wavelength at which the long-wavelength flank
  falls through a crossing level. Quoting the nearest sampled point
  instead quantises the answer to the step of the monochromator.
- The crossing level is formed from the band that was actually measured.
  Half of the reflecting plateau is the usual convention, and the
  plateau is the averaged run around the peak rather than the single
  highest sample, so one noisy point cannot set the level for the whole
  article.
- The convention has to travel with the number. A cut-off taken at half
  the plateau and a cut-off taken at a quarter of it are different
  wavelengths on the same coverglass, and a figure reported without its
  convention cannot be compared with the drawing at all.
- A scan that stops while the flank is still high has not measured a
  cut-off. Extrapolating past the last sample invents an edge, so the
  short scan is refused and sent back to the laboratory.
- The tolerance band is two-sided and often asymmetric. The share of the
  allowance a deviation consumed is reported against the side it landed
  on, because a two-nanometre excursion means something different on a
  plus-ten side than on a minus-two side.
- A lot verdict is not a lot description. Articles that all pass can
  still sit several nanometres apart, or all sit on the same side of the
  drawing value, and the second is a coating run bias rather than
  scatter. Both are advisories beside the verdict, not inside it.

## Workflow

1. Validate the evaluation policy: the crossing convention and its
   fraction, the plateau inclusion fraction, the minimum scan length and
   the advisory thresholds. An unrecognised convention is refused rather
   than defaulted.
2. Resolve the drawing requirement. An absent requirement, or one whose
   drawing reference is blank, closes immediately on requirement not
   established; a tolerance that is zero on both sides, or one that
   reaches zero wavelength, is a malformed requirement and is refused.
3. Normalise each measured scan: strictly increasing wavelengths, every
   reflectance a fraction of unity, and enough points to show a plateau
   and a flank.
4. Take the plateau as the averaged contiguous run around the peak, form
   the crossing level from it under the declared convention, and refuse a
   level that is not below the plateau.
5. Walk the flank from the end of the plateau to the first sample at or
   below the level, and interpolate the crossing linearly between that
   sample and the one before it.
6. Compare each article against the drawing value and its two-sided
   tolerance, admitting a tie, and report the signed deviation with the
   share of the side-specific allowance it consumed.
7. Close on one verdict -- requirement not established, cut-off outside
   the drawing tolerance, or cut-off meets the drawing -- and report the
   lot mean, the spread, the worst article and the spread and run-bias
   advisories alongside it.

## Pitfalls

- Comparing against a remembered wavelength. The drawing is the only
  source of the required cut-off, and a criterion applied from memory is
  a criterion nobody can audit.
- Reporting the nearest sampled wavelength as the cut-off. That makes
  the answer a property of the scan step, and two laboratories with
  different steps will disagree about identical hardware.
- Setting the crossing level from the single peak sample. One noisy
  point then moves the edge on an article whose band is perfectly
  ordinary.
- Extrapolating an edge out of a scan that ended while the flank was
  still high. The measurement simply did not reach the cut-off, and an
  invented edge is worse than a rerun.
- Folding an asymmetric tolerance into one number. The consumed share is
  only meaningful against the side the deviation actually landed on.
- Reporting a pass with no deviation figure. The verdict alone hides the
  difference between an article that grazed the band and one sitting on
  the drawing value, and the next build has nothing to compare with.
- Treating a one-sided offset as scatter. Every article high by the same
  couple of nanometres is a deposition run that drifted, and it belongs
  with the process, not silently inside a pass.
- Comparing a measurement with a band edge by bare arithmetic. The edge
  is a drawing figure combined with a tolerance, so a measurement
  exactly on it can evaluate a few units in the last place outside; the
  comparison absorbs that representation error while the tolerance stays
  untouched.

## Behavior contract (gate 3)

The policy validation, drawing requirement resolution, scan
normalisation, plateau and crossing-level derivation, flank
interpolation, the two-sided tolerance comparison with an admissible
tie, the consumed-allowance share, the lot mean, spread and worst
article, and the spread and run-bias advisories are exercised by the
gate 3 contract test:
scripts/test_e2008_reflectance_cut_off_requirement.py against
scripts/e2008_reflectance_cut_off_requirement_logic.py (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e2008_reflectance_cut_off_requirement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
