---
name: e2001-electron-seeding-general-provisions
description: "Use when determine how the electron-seeding obligation of ECSS-E-ST-20-01C clause 6.5.1 is discharged for a multipaction-test-campaign: categorize the seed-electron access of every critical radio-frequency gap of the flight-representative article as direct-line-of-sight, aperture-coupled or enclosed-beyond-reach; route an unreachable gap onto a dedicated breadboard or development-model; score that substitute attribute by attribute against the article gap-height, drive-frequency, surface-roughness, base-material, surface-coating and gap-geometry; and confirm the substitute is itself open to the seed-source with its seeding-effectiveness demonstrated before its result is transferred to the article. Trigger: ecss, e-st-20-electrical-scope, e2001-electron-seeding-general-provisions, electron-seeding-provisions, seed-electron-access, dedicated-breadboard-substitution, breadboard-representativeness, multipaction-test-seeding, seed-source-line-of-sight."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-electron-seeding-general-provisions, electron-seeding-provisions, seed-electron-access, dedicated-breadboard-substitution, breadboard-representativeness, multipaction-test-seeding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Electron-Seeding General Provisions (space-systems/ecss/e2001-electron-seeding-general-provisions)

Use when the task is the general seeding provision of ECSS-E-ST-20-01C
clause 6.5.1 -- deciding whether a seed-electron source can reach the
critical gap of the article under multipactor-test, and, where the gap is
sealed beyond its reach, whether a dedicated breadboard or development-model
is representative enough to carry the seeded run on the article's behalf.

## Domain quick reference

- Multipaction is a vacuum resonant-discharge effect that needs a starting
  free electron. Under laboratory vacuum the natural free-electron
  population inside a small enclosed gap is sparse and intermittent, so an
  unseeded run can pass simply because no electron happened to be present
  while the drive was applied. Clause 6.5 removes that ambiguity by
  requiring a deliberate seed-electron population; clause 6.5.1 sets the
  general provisions that govern how the seed reaches the gap at all.
- Seed-electron access has three categories. Direct-line-of-sight: the
  source (radioactive beta emitter, ultraviolet photoemission lamp or
  electron gun) has an unobstructed path into the gap volume.
  Aperture-coupled: no direct view, but a coupling aperture, vent hole or
  waveguide port is open enough, and the intervening structure attenuates
  the seed flux little enough, that electrons still enter. Enclosed: the
  gap sits behind sealed metal with no usable opening, and no practicable
  source placement reaches it.
- An enclosed gap does not excuse the seeding obligation; it moves it. The
  gap is reproduced on a dedicated breadboard, development-model,
  engineering-model or purpose-built test-piece that is open to the source,
  and the seeded result transfers to the article only when the substitute
  is demonstrably representative.
- Representativeness is judged attribute by attribute, not as a global
  impression. Dimensional attributes (gap-height, drive-frequency) drive
  the frequency-gap product that fixes the resonant order, and hold tight
  tolerances. Surface-roughness is looser but still bounded, because
  roughness changes the effective secondary-emission-yield. Base-material,
  surface-coating and gap-geometry are categorical: an unlike material or
  an unlike coating changes the yield curve outright and cannot be traded
  against a tight dimension.
- A substitute that is itself unreachable by the source, or whose seeding
  was never demonstrated to work, discharges nothing. Seeding-effectiveness
  evidence belongs with the substitute, not with the article it stands in
  for.

## Workflow

1. List every critical radio-frequency gap of the flight-representative
   article. For each, record whether the source has a line-of-sight path,
   the open coupling-aperture area, and the seed-flux attenuation of the
   intervening structure. Reject a gap record that omits any of the three
   or carries a negative area or attenuation.
2. Categorize each gap: direct-line-of-sight when the view is unobstructed;
   aperture-coupled when the open area meets the minimum and the
   attenuation stays within the ceiling; otherwise enclosed-beyond-reach.
   Absorb float representation error at each limit rather than widening the
   limit itself.
3. Derive the seeding route. A direct or aperture-coupled gap is seeded on
   the article. An enclosed gap is routed onto a dedicated substitute
   model. Offering a substitute for a gap the source can already reach is a
   finding, not a convenience -- it substitutes evidence without cause.
4. For each substitute, score representativeness against the article gap:
   relative deviation on gap-height, drive-frequency and surface-roughness
   against their tolerances, exact agreement on base-material,
   surface-coating and gap-geometry. Name each failing attribute
   individually.
5. Confirm the substitute is itself seedable (run step 2 on its own gap)
   and that its seeding-effectiveness was demonstrated. A blocked or
   unverified substitute yields its own finding, independent of how well
   its dimensions match.
6. Aggregate per gap and across the campaign. The clause 6.5.1 provision is
   satisfied only when every critical gap holds either a seeded article run
   or a seeded, verified, representative substitute run, and the finding
   list is empty.

## Pitfalls

- Reading an unseeded pass on an enclosed gap as a clean result -- with no
  seed population the run only proves that no electron happened to appear,
  which is an absence of evidence, not evidence of margin.
- Accepting a breadboard because it "looks the same" -- a matching
  gap-height with an unlike surface-coating reproduces the geometry and not
  the secondary-emission-yield, and the discharge threshold follows the
  yield.
- Treating a large coupling aperture as sufficient on its own -- a wide
  opening behind a deeply attenuating path still starves the gap; the area
  and the attenuation are two conditions, not one.
- Recording seeding-effectiveness evidence against the flight article when
  the seeded run was performed on the substitute -- the evidence has to sit
  on the hardware that was actually seeded, or the transfer argument has a
  hole in it.
- Widening a representativeness tolerance so a near-miss substitute passes
  -- the correct fix for a value that lands a few units in the last place
  over a limit is to absorb the representation error in the comparison, not
  to relax the engineering tolerance.

## Behavior contract (gate 3)

The access-categorization, route-selection, representativeness-scoring and
substitute-seedability logic is exercised by the gate 3 contract test:
scripts/test_e2001_electron_seeding_general_provisions.py against
scripts/e2001_electron_seeding_general_provisions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_electron_seeding_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
