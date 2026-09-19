---
name: q7028-conformal-coating-repair
description: "Assess a conformal coating repair after board rework: the area stripped, the film re-applied over it, and the cure it was given, under ECSS-Q-ST-70-28. Use when coating was removed to reach a joint and the re-coated area has to be signed off. Checks the removal cleared the footprint by a working margin without stripping sound film off untouched hardware, grades every thickness reading and the mean separately, confirms the lap onto surrounding coating, interpolates the cure time the chosen temperature demands, then returns accept, re-coat or refuse. Trigger: ecss, q-st-70-28, conformal-coating-repair, conformal-coating-removal-margin, conformal-coating-film-thickness, conformal-coating-lap-overlap, conformal-coating-cure-schedule."
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
  tags: [ecss, q-st-70-28-board-repair-scope, q7028-conformal-coating-repair, conformal-coating-removal-margin, conformal-coating-film-thickness, conformal-coating-lap-overlap, conformal-coating-cure-schedule, conformal-coating-re-application]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Conformal Coating Repair (space-systems/ecss/q7028-conformal-coating-repair)

Use when the task is the coating part of the repair methods of
ECSS-Q-ST-70-28 — the coating that had to be taken off to reach a joint
or a track, and the film put back over the reworked area once the work
underneath was finished and accepted.

## Domain quick reference

- Coating removal is bounded on both sides, and the two bounds protect
  different things. Too little removal leaves film at the edge of the
  work area that will be heat-damaged from underneath and will not bond
  to the new coat. Too much strips sound coating from hardware nobody
  touched, and that loss is not recovered by re-coating.
- Because of that asymmetry the two findings do not carry the same
  weight. An under-margin removal is corrected by stripping a little
  further and re-coating; an over-stripped area has already changed
  parts of the board outside the repair, and belongs to the
  nonconformance route, not to the touch-up route.
- The film is graded twice: every individual reading against the
  thickness band, and the mean of the readings separately. A film that
  averages inside the band can still be bare at one point, and a bare
  point is where moisture and conductive debris get in.
- The lap onto the surrounding sound coating is what closes the repair.
  A film that stops at the edge of the stripped area leaves a seam
  around the whole perimeter, so the lap is measured, not assumed from
  the fact that coating was applied generously.
- Cure is time-at-temperature, and the two trade. A cure schedule is
  therefore read by interpolating the time the chosen temperature
  demands rather than by picking the nearest tabulated row; a
  temperature outside the tabulated span is refused, because the
  chemistry beyond the span is not the same reaction.

## Workflow

1. Validate the reworked footprint, the stripped area, the thickness
   readings, the lap and the cure record; a stripped area smaller than
   the footprint it is supposed to clear is an input error.
2. Compute the per-side removal margin along and across, and grade the
   smallest against the minimum and the largest against the maximum.
3. Grade each thickness reading against the band, note the index of
   every thin and every thick point, and grade the mean separately.
4. Compare the lap onto the surrounding sound coating with its minimum.
5. Interpolate the cure hours the held temperature demands, refusing a
   temperature outside the tabulated span, and compare with the hours
   actually held; report the shortfall rather than a pass or fail alone.
6. Return refuse when sound coating was stripped beyond the maximum
   margin, re-coat when any other characteristic failed, accept only
   when all of them passed, and name every finding.

## Pitfalls

- Grading the film on its mean thickness. The mean hides the one point
  where the coat ran thin, which is the point the repair will fail at.
- Treating over-stripping as a touch-up. Removing sound coating from
  untouched hardware has already altered the board outside the repair
  area and cannot be undone by applying more film.
- Assuming a lap exists because the coat looks generous. The seam around
  the stripped perimeter is the path into the repair, so the lap is
  measured against its minimum like any other characteristic.
- Reading the cure schedule by nearest row. Time and temperature trade
  continuously; rounding to the nearest tabulated temperature either
  over-cures or, worse, signs off a film that never reached its
  properties.
- Extrapolating the cure schedule past its tabulated span to justify a
  hot fast cure. Outside the span the reaction is not the one the
  schedule describes, so the point is refused, not projected.
- Relaxing the thickness band or the lap minimum for a marginal repair.
  An exact equality at a limit is a representation question, absorbed by
  the tolerance inside the comparison; the limit stays as specified.

## Behavior contract (gate 3)

The input validation, two-sided removal-margin test, per-reading and
mean thickness grading, lap check, cure-schedule interpolation with
extrapolation refused, and the refuse / re-coat / accept ladder are
exercised by the gate 3 contract test:
scripts/test_q7028_conformal_coating_repair.py against
scripts/q7028_conformal_coating_repair_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7028_conformal_coating_repair.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
