---
name: q7050-link-to-70-01c
description: "Convert particle contamination monitoring results into the surface cleanliness verification evidence a programme owes under ECSS-Q-ST-70-01C. Use when witness plates or fallout monitors have been read over a monitoring period and those readings must become an end-of-exposure percentage area coverage compared with the declared cleanliness level. Projects the measured fallout rate over the remaining exposure, sums the per-size-bin obscuration, holds a requirement reference size coarser than the monitored bins to a lower-bound statement, and refuses a projection reaching further beyond the monitored period than the programme allows. Trigger: ecss, q-st-70-50, q-st-70-01, particle-fallout-monitoring, witness-plate-obscuration, percentage-area-coverage, surface-cleanliness-level-verification, contamination-monitoring-handover."
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
  tags: [ecss, q-st-70-50-particle-contamination-monitoring-scope, q7050-link-to-70-01c, particle-fallout-monitoring, witness-plate-obscuration, percentage-area-coverage, surface-cleanliness-level-verification, contamination-monitoring-handover]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle Contamination Monitoring — Handover to Cleanliness Verification (space-systems/ecss/q7050-link-to-70-01c)

Use when the task is the interface step of particle contamination
monitoring — taking what the witness plates and fallout monitors
actually read and turning it into the surface cleanliness evidence the
ECSS-Q-ST-70-01C requirement set is verified against.

## Domain quick reference

- Monitoring produces counts per size bin on a known collecting area
  over a known period. The cleanliness requirement is written as a
  surface level, not as counts, so the handover is a conversion and not
  a transcription: counts become obscured area, obscured area becomes a
  percentage area coverage, and only that percentage meets the level.
- Obscuration is quadratic in particle size. A single bin at fifty
  micrometres carries the area of a hundred particles at five, so a
  count-weighted summary of a monitoring run says almost nothing about
  the level the surface will be verified at, and the per-bin areas must
  be summed rather than the counts.
- Monitoring almost never spans the whole exposure. What is measured is
  a fallout rate, and the verification figure is that rate projected
  over the exposure the hardware will see. The projection is credible
  only a limited way past the monitored period; beyond that the
  deposition environment has not been observed at all and the honest
  response is to refuse the projection and keep monitoring.
- A requirement referenced to a particle size larger than the coarsest
  monitored bin cannot be verified upward from the monitoring data. The
  unmonitored coarse tail carries area, so the computed coverage is a
  lower bound and must be reported as one instead of as the value.
- The level a coverage figure meets is read off the programme level
  table, which is an input to this step. An equality at a level boundary
  is a representation question, absorbed by a named tolerance, never by
  moving the boundary.

## Workflow

1. Validate the collecting area, the monitored period and every size
   bin: a non-positive area or period, a non-positive diameter or a
   negative count is an input error rather than a value to clamp.
2. Form the per-bin fallout rate as counts over collecting area over
   monitored days, keeping the bins separate.
3. Check the projection horizon: the exposure duration divided by the
   monitored period against the allowed extrapolation factor. Refuse a
   projection past that factor instead of reporting it with a caveat.
4. Project each bin rate over the exposure duration and the exposed
   area to obtain the end-of-exposure count per bin.
5. Sum the projected obscured area, one bin at a time, as the count
   times the projected area of a disc of the bin diameter, and divide by
   the exposed area to get the percentage area coverage.
6. Compare the requirement reference size with the coarsest monitored
   bin; when the reference is coarser, mark the result a lower bound and
   raise the finding rather than reporting a bare number.
7. Read the level met from the programme level table, compare it with
   the declared level using the named tolerance, and report the
   projected coverage, the level met, the bound status and every
   finding.

## Pitfalls

- Reporting the monitored coverage as the verification figure. The
  monitored period is shorter than the exposure, so the un-projected
  number is the coverage the hardware had on the day of the reading,
  not the coverage it will be verified at.
- Summing counts across bins and applying one nominal particle size.
  The area is quadratic in diameter, so a mean size understates a
  distribution with a coarse tail by a large factor.
- Projecting an arbitrarily long exposure from a short monitoring run.
  A rate measured over a day says nothing about a year of a changing
  environment, and stretching it silently converts an unmonitored
  period into evidence.
- Reporting a lower-bound coverage as though it were the value. When
  the requirement reference size sits above the coarsest monitored bin,
  the coarse tail was never collected and the figure can only move
  upward.
- Widening a level boundary so a marginal run meets the declared level.
  The tolerance inside the comparison exists for representation error;
  the boundary itself stays as the programme wrote it.

## Behavior contract (gate 3)

The input validation, fallout-rate formation, projection-horizon
refusal, per-bin obscuration summation, lower-bound detection and level
comparison are exercised by the gate 3 contract test:
scripts/test_q7050_link_to_70_01c.py against
scripts/q7050_link_to_70_01c_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7050_link_to_70_01c.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
