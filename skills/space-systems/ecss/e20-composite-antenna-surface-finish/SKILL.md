---
name: e20-composite-antenna-surface-finish
description: "Use when assess how the surface finish of a composite antenna part changes its radiating performance under ECSS-E-ST-20C clause 7.2.2.4.2: categorize the radiating face as a bare woven-carbon face, a resin-rich face, a metallized face or a coating carried over metallization, convert the root-mean-square surface error into the Ruze aperture-efficiency loss at the operating wavelength, derive the ohmic reflection loss from the sheet resistance of the conducting face, add the loss of incomplete metallization coverage and the two-way absorption of the coating, and check the summed gain-degradation against the allocation the antenna-gain-budget holds. Trigger: ecss, e-st-20c-clause-7-2-2-4-2, composite-antenna-surface-finish, ruze-surface-error-loss, sheet-resistance-ohmic-loss, metallization-coverage-loss, coating-absorption-loss, antenna-gain-degradation-allocation."
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
  tags: [ecss, e-st-20-electrical-scope, e20-composite-antenna-surface-finish, composite-antenna-surface-finish, ruze-surface-error-loss, sheet-resistance-ohmic-loss, metallization-coverage-loss, coating-absorption-loss, antenna-gain-degradation-allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Composite Antenna Surface Finish (space-systems/ecss/e20-composite-antenna-surface-finish)

Use when the task is the clause 7.2.2.4.2 concern of ECSS-E-ST-20C --
whether the finish actually applied to a composite radiating part still
lets it radiate to the performance the antenna was sold on, and what
the finish costs when it does not.

## Domain quick reference

- A composite part does not radiate because it is composite; it
  radiates because of the face presented to the wave. Four finish
  families cover the delivered hardware: a bare woven-carbon face, a
  resin-rich face left by the tooling, a metallized face (vapour
  deposited or foil), and a coating carried over the metallization for
  thermal-control reasons. The first two are not reflecting faces at
  all -- their sheet resistance is orders above the free-space
  impedance -- so the finding they raise is a missing metallization
  layer, not a loss figure. Categorizing the face first is what keeps
  a manufacturing escape from being processed as a small loss term.
- The residual surface error of a cured composite face costs
  aperture-efficiency. The closed-form penalty grows with the square of
  the ratio of root-mean-square error to wavelength, so a finish that
  is invisible at S-band is a real loss at Ka-band: the same face
  costs four times as much every time the wavelength halves. The
  closed form is a small-error result; past roughly a sixteenth of a
  wavelength it understates the face and the analysis has to move to a
  scattered-field computation.
- The conducting face is not perfect. Treated as a surface impedance
  against free space, a face of finite sheet resistance returns
  slightly less than everything, and the reflection loss climbs as the
  sheet resistance approaches the free-space impedance. Separately,
  metallization that does not cover the whole face loses the
  uncovered fraction outright, which is an area term, not an
  impedance one.
- A coating over the metallization is crossed twice -- in, off the
  metal, and out again -- so its absorption is taken over twice the
  refracted thickness, stretched by the incidence angle through the
  refraction into the layer. A bare woven face carries one more
  consequence the co-polar loss terms never show: the weave is
  directionally anisotropic and introduces cross-polarisation.

## Workflow

1. Categorize the finish of the radiating face into its family and
   reject an unrecognised one. If the family is not a reflecting face,
   raise the missing-metallization finding and do not compute an
   impedance loss for it.
2. Convert the operating frequency into a free-space wavelength and
   take the ratio of the root-mean-square surface error to it. Flag
   the case where the ratio passes the small-error validity limit,
   because the closed form then understates the loss rather than
   bounding it.
3. Compute the aperture-efficiency loss from that ratio.
4. For a reflecting face, compute the ohmic reflection loss from the
   measured sheet resistance, and the coverage loss from the fraction
   of the face the metallization actually reaches. Raise a finding for
   any coverage below unity, since that is a process escape as well as
   a loss.
5. For a coated face, compute the two-way absorption of the coating
   from its thickness, relative permittivity and loss-tangent at the
   operating wavelength and incidence angle.
6. Sum the loss terms and compare against the allocation the
   antenna-gain-budget holds for surface finish. The part is compliant
   only when the sum is inside the allocation and no family, coverage
   or validity finding is open.

## Pitfalls

- Treating a bare woven-carbon face as a reflector with a large loss.
  Its sheet resistance is not a small perturbation on the free-space
  impedance; the face does not reflect, and a loss number computed for
  it is meaningless where a missing-layer finding is owed.
- Qualifying a finish at one frequency and reusing it higher up. The
  surface-error penalty is a squared function of the error-to-
  wavelength ratio, so a face accepted at S-band can be the dominant
  loss term at Ka-band with nothing about the hardware changed.
- Reading a small computed loss as validity. Past the small-error
  limit the closed form no longer describes the face; a small number
  there is an artefact of an equation used outside its range.
- Folding the metallization coverage into the sheet resistance. One is
  an area effect and the other an impedance effect; combining them
  hides which one a process change would actually fix.
- Taking the coating absorption over one pass. The wave crosses the
  coating twice on a reflecting face, and at oblique incidence the
  refracted path is longer still -- the single-pass number is
  optimistic on both counts.
- Declaring a bare weave compliant on co-polar loss alone. The weave
  introduces cross-polarisation that none of the co-polar terms
  carries, so the polarisation requirement has to be closed separately.

## Behavior contract (gate 3)

The finish categorization, surface-error loss, ohmic and coverage
terms, coating absorption and allocation comparison are exercised by
the gate 3 contract test:
`scripts/test_e20_composite_antenna_surface_finish.py` against
`scripts/e20_composite_antenna_surface_finish_logic.py` (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e20_composite_antenna_surface_finish.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
