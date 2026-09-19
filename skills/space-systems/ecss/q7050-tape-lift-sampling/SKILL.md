---
name: q7050-tape-lift-sampling
description: "Assess a tape-lift surface sample under ECSS-Q-ST-70-50C and grade the surface it came from: subtract a blank lift, correct the counted size bands for the tape recovery efficiency on that finish, accumulate the bands from the largest downwards, scale the lifted area onto the reference area a cleanliness level is stated over, then grade each band and report the governing one. Use when reading a tape-lift count sheet, defending a recovery correction, or checking whether a lifted patch was large enough to describe the surface. Trigger: ecss, q-st-70-50c, tape-lift-sampling, tape-lift-recovery-efficiency, surface-particle-cumulative-count, blank-lift-subtraction, surface-cleanliness-level-grading."
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
  tags: [ecss, q-st-70-50c-particle-contamination-monitoring, q-st-70-50c, q7050-tape-lift-sampling, tape-lift-sampling, tape-lift-recovery-efficiency, surface-particle-cumulative-count, blank-lift-subtraction, surface-cleanliness-level-grading]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle Monitoring — Tape-Lift Sampling (space-systems/ecss/q7050-tape-lift-sampling)

Use when the task is the tape-lift part of the surface clause of
ECSS-Q-ST-70-50C: lifting the particles resident on a hardware surface with
an adhesive tape, counting them under magnification, and reading the surface
against its stated cleanliness level.

## Domain quick reference

- A lift measures the surface, not the air. It returns everything the surface
  is carrying, whatever put it there — fallout, handling, machining residue
  from before the part ever entered a cleanroom.
- A lift is never complete. The tape removes a fraction of what is resident,
  and that fraction depends on the finish, so the raw count understates the
  surface until the recovery efficiency divides it.
- The recovery correction has a credibility limit. At low efficiency the
  correction is contributing more to the reported number than the count is,
  and the right response is a better method rather than a larger multiplier.
- A blank lift taken on a clean reference coupon carries the tape's own
  inclusions and the counting background. Without it those are reported as
  particles found on the hardware.
- A cleanliness level is a cumulative distribution, not a set of independent
  bands. Each entry means particles at or above that size, so the counts are
  accumulated from the largest band downwards before anything is graded.
- A level is stated over a reference area, and a lift almost never covers it.
  Scaling the counts by the area ratio is what makes the two comparable, and
  it extrapolates: a small patch multiplies both the particles and the luck.
- Lifting more patches is the honest way to raise sampled area. Two lifts of
  the same size halve the scaling factor, which is a real improvement in the
  result rather than a change to the arithmetic.
- The surface is graded on its worst band. Averaging the bands lets a clean
  fine fraction carry a large-particle failure, and it is the large particles
  a level exists to exclude.

## Workflow

1. Validate the lift: sampled area, recovery efficiency on that finish, and
   the counted size bands.
2. Subtract the blank lift band by band, refusing a blank counted on bands
   the sample was not counted on, and flooring a band at zero rather than
   returning a negative count.
3. Divide each band by the recovery efficiency to recover the resident
   population from the lifted one.
4. Accumulate the bands from the largest size downwards into the cumulative
   form a cleanliness level is stated in.
5. Scale the cumulative counts from the total lifted area — patch area times
   the number of lifts — onto the reference area of the level.
6. Grade each band against its own allowance, absorbing an equality at the
   allowance with a tolerance rather than relaxing it, and refuse a band the
   level states no allowance for.
7. Report the governing band by utilisation, the failed bands, and the
   findings: a missing blank, a lifted area below the minimum, and a recovery
   efficiency low enough that the correction dominates.

## Pitfalls

- Reporting the raw lifted count. It is a fraction of what is on the surface,
  and the fraction moves with the finish, so an uncorrected count is not
  comparable between two parts, let alone against a level.
- Rescuing a poor recovery with a large multiplier. Below roughly half
  recovery the number reported is mostly the correction, and the measurement
  it rests on is the weaker part of the product.
- Skipping the blank. Tape carries its own inclusions and the counting method
  has its own background, and both are indistinguishable from surface
  particles once they are in the tally.
- Grading the bands as independent counts. A level is cumulative, so a band
  read on its own understates the population at or above that size and passes
  surfaces the level was written to reject.
- Scaling from a tiny patch. The area ratio multiplies the particles and the
  sampling variance together, so a small lift produces a confident-looking
  number built on whether one large particle was inside the patch.
- Averaging the bands. The large-particle bands are the reason a level exists,
  and an average lets an unusually clean fine fraction cover a failure in
  exactly the band that matters.
- Lifting from a bare optical surface. The method removes particles by
  contact and can take coating with them; a co-located witness coupon carries
  the sample instead.

## Behavior contract (gate 3)

The lift validation, blank subtraction with its band matching, recovery
efficiency correction, cumulative accumulation, reference-area scaling,
per-band grading with its at-allowance tolerance, the governing band and the
lift findings are exercised by the gate 3 contract test:
scripts/test_q7050_tape_lift_sampling.py against
scripts/q7050_tape_lift_sampling_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7050_tape_lift_sampling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
