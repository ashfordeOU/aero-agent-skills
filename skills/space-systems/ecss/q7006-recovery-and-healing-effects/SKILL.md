---
name: q7006-recovery-and-healing-effects
description: "Evaluate how much of a particle or UV induced degradation heals back after the beam stops, and whether the mission may be credited with it, under ECSS-Q-ST-70-06C. Use when darkening is reversible and a post-exposure series has to become a design number. Converts each post-exposure reading into a degradation, separates the recoverable part from the permanent floor, derives the exponential time constant and half-time of the approach, refuses a series that darkens again or heals past pristine, and withholds the credit from a continuously irradiated surface or a quiet interval too short against the half-time. Trigger: ecss, q-st-70-06, radiation-recovery-and-healing, darkening-reversibility, permanent-degradation-floor, recovery-time-constant, recovery-credit-admissibility, post-exposure-bleaching-series."
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
  tags: [ecss, q-st-70-06-particle-uv-radiation-testing-scope, q7006-recovery-and-healing-effects, radiation-recovery-and-healing, darkening-reversibility, permanent-degradation-floor, recovery-time-constant, recovery-credit-admissibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Recovery and Healing Effects (space-systems/ecss/q7006-recovery-and-healing-effects)

Use when the task is the recovery step of an ECSS-Q-ST-70-06C particle
or UV exposure — reading a post-exposure series, splitting what heals
from what stays, and deciding which of the two numbers the design is
allowed to use.

## Domain quick reference

- Part of what the beam did comes back. Colour centres in glasses,
  second-surface mirrors and white paints bleach thermally and under
  illumination, so a reading taken days after the run is not the
  reading the beam left behind.
- A recovery series is read in degradation units, not raw property
  units. Each post-exposure reading becomes a difference from the
  pristine value, and the recovered fraction is how much of the
  as-irradiated difference has gone.
- Two distinct numbers fall out and get confused constantly: the
  as-irradiated degradation, which is the worst the material ever is,
  and the permanent floor it settles on, which is the worst it stays.
  A campaign that reports only one of them has thrown away a design
  case.
- The approach between the two is exponential. One post-exposure point,
  the as-irradiated value and the floor give a time constant, and the
  half-time derived from it is the quantity that decides whether a
  mission's quiet intervals are long enough to matter.
- Recovery credit is a mission property, not a material property. A
  continuously irradiated surface never gets the quiet time, so it
  designs to the as-irradiated value however well the material heals on
  the bench.
- A series that darkens again, or heals past the pristine value, is
  telling you about the instrument, the handling or a contamination
  layer — not about healing.

## Workflow

1. Read the property, its degradation direction, the pristine value,
   the as-irradiated value and the post-exposure series.
2. Convert every series reading into a degradation and order the series
   by elapsed time, refusing two readings at the same time.
3. Require at least one reading taken after the exposure ended, and at
   least two readings before claiming a trend.
4. Check the series heals monotonically and never passes the pristine
   value; either violation is a finding against the measurement.
5. Take the settled reading as the permanent floor and form the
   recovered fraction against the as-irradiated degradation.
6. Derive the exponential time constant from the first usable
   intermediate reading and convert it into a half-time.
7. Test the credit: continuous exposure never earns it, and an
   intermittent one earns it only when the quiet interval runs several
   half-times.
8. Emit the two degradations, the recovered fraction, the time
   constant, the credit decision and the design degradation — the floor
   where the credit holds, the as-irradiated value where it does not.

## Pitfalls

- Reporting the recovered value as the test result. It is a design
  value only where the mission offers the quiet time; on the bench it
  is just the last reading before someone went home.
- Fitting a time constant through a point already sitting on the floor.
  The remaining fraction is zero and the fit is meaningless; pick a
  reading still visibly moving.
- Treating an eclipse as quiet time without checking it against the
  half-time. A forty-minute eclipse does nothing to a material whose
  bleaching half-time is a week.
- Calling a non-monotonic series noisy and averaging it. Re-darkening
  after a run usually means contamination or a thermal excursion, both
  of which are findings in their own right.
- Losing the as-irradiated value once the floor is known. The transient
  worst case sizes the hot case the surface has to survive at all.

## Behavior contract (gate 3)

The degradation frame, series normalization and monotonicity, permanent
floor, recovered fraction, exponential time constant and half-time,
credit admissibility and the design-value decision are exercised by the
gate 3 contract test:
scripts/test_q7006_recovery_and_healing_effects.py against
scripts/q7006_recovery_and_healing_effects_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7006_recovery_and_healing_effects.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
