---
name: q7031-surface-verification
description: "Assess whether a prepared substrate is genuinely fit to receive its first coat under ECSS-Q-ST-70-31C: read the water-break observation only when it was held long enough to be evidence, compare non-volatile residue and particulate obscuration against their limits, grade the abrasion profile against a two-sided roughness window that fails both too smooth and too rough, compute the substrate dew-point margin and coating-area humidity, and separate a surface failure that means preparing again from a room failure that means waiting. Use when a prepared surface is about to be coated. Trigger: ecss, q-st-70-31c, paint-surface-readiness, water-break-cleanliness-test, paint-surface-roughness-window, paint-dew-point-margin, paint-coating-area-humidity."
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
  tags: [ecss, q-st-70-31c-paint-application, q-st-70-31c, q7031-surface-verification, paint-surface-readiness, water-break-cleanliness-test, paint-surface-roughness-window, paint-dew-point-margin, paint-coating-area-humidity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paints — Prepared Surface Verification (space-systems/ecss/q7031-surface-verification)

Use when the task is the verification made on a prepared surface under
ECSS-Q-ST-70-31C, in the minutes before the first coat: whether the surface is
clean, whether its profile is inside the window the paint system needs, and
whether the substrate and the air around it are dry enough to coat at all.

## Domain quick reference

- The water-break test is an observation with a dwell attached. A film watched
  for a few seconds has not had time to retract over a contaminated patch, so a
  short-dwell observation is refused as evidence rather than recorded as a
  pass. Passing it means an unbroken film, not the absence of a noted break.
- Cleanliness has two independent axes. A film-forming residue and a
  particulate load fail in different ways and are measured differently, so a
  surface can be visually spotless and still carry residue that destroys
  adhesion.
- The roughness requirement is two-sided, and the lower bound is the one that
  gets forgotten. Too smooth starves the mechanical key the primer needs; too
  rough leaves peaks the film cannot cover, and thin film over a peak is where
  corrosion starts. Both are failures of the same requirement.
- Dryness is a margin, not a temperature. A substrate sitting near the dew
  point condenses an invisible water layer as soon as evaporating solvent cools
  it further, which is why the substrate temperature is compared against the
  dew point rather than against a fixed number.
- Humidity in the coating area and the substrate margin are separate checks.
  One can be inside its limit while the other is not, and they fail for
  different reasons.
- A surface finding and an environmental finding call for different actions.
  The surface has to be prepared again; the room only has to be waited out, and
  conflating the two either wastes a preparation or coats into a bad room.

## Workflow

1. Validate the water-break dwell and take the observation only if it stands as
   evidence.
2. Compare non-volatile residue and particulate obscuration against their
   limits, or against the per-item limits when the drawing sets them.
3. Look up the roughness window for the paint system, or take the per-item
   override, and grade the measured profile as in-window, too-smooth or
   too-rough.
4. Compute the dew-point margin from the substrate temperature and the measured
   dew point, and compare it against the minimum.
5. Compare the coating-area relative humidity against its ceiling.
6. Group the findings into surface and environment, and close on re-prepare,
   conditions-hold or ready-to-coat, with a surface finding outranking an
   environmental one.

## Pitfalls

- Recording a water-break result without its dwell. The number of seconds is
  what makes the observation mean anything, and a pass without it is an opinion.
- Grading roughness against an upper bound only. A polished surface passes that
  test and then fails adhesion, which is precisely the case the lower bound
  exists to catch.
- Comparing the substrate temperature against an air temperature limit. The
  quantity that governs condensation is the margin above the dew point, and a
  warm room with damp air can still be a condensing surface.
- Treating a humid room as a preparation failure. The surface is fine; the
  conditions are not, and preparing it again neither dries the air nor makes
  the item any readier.
- Widening a limit so an exactly-at-limit reading passes. Equality at the limit
  is a representation question handled by the tolerance inside the comparison;
  the limits stay where the drawing set them.

## Behavior contract (gate 3)

The water-break dwell validation, residue and obscuration comparisons, the
two-sided roughness window, the dew-point margin, the humidity ceiling and the
surface-versus-environment disposition are exercised by the gate 3 contract
test: scripts/test_q7031_surface_verification.py against
scripts/q7031_surface_verification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7031_surface_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
