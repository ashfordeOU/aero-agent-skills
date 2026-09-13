---
name: e2001-seeding-for-continuous-wave-tests
description: "Use when verify that the electron-seeding arrangement of a continuous-wave multipactor run meets ECSS-E-ST-20-01C clause 6.5.2: categorize the seed-source as continuously emitting or repetitively-pulsed, decay-correct a radioactive emitter to the run date, reduce its emission by the transport-fraction and gap-capture-fraction to the seed-electron-rate actually entering the gap, convert that rate into a Poisson initiation-probability over the dwell held at each rising drive-step, compare every dwell against the dwell the stated seeding-confidence requires, and bound the accumulated seed-electron-fluence so the seed itself does not over-irradiate the article. Trigger: ecss, e-st-20-electrical-scope, e2001-seeding-for-continuous-wave-tests, continuous-wave-seeding, seed-electron-rate, poisson-initiation-probability, dwell-time-sufficiency, seed-source-decay-correction, seed-electron-fluence."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-seeding-for-continuous-wave-tests, continuous-wave-seeding, seed-electron-rate, poisson-initiation-probability, dwell-time-sufficiency, seed-source-decay-correction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Seeding Under Continuous-Wave Drive (space-systems/ecss/e2001-seeding-for-continuous-wave-tests)

Use when the task is the seeding arrangement of ECSS-E-ST-20-01C clause
6.5.2 -- showing that, while an uninterrupted carrier is applied, seed
electrons actually arrive in the gap often enough that a run which stays
quiet is evidence of margin rather than evidence of an empty gap.

## Domain quick reference

- Under continuous-wave drive the field is present at every instant of the
  dwell, so any seed electron entering the gap at any moment can start the
  avalanche. The seeding question is therefore purely one of arrival
  statistics: how long must the carrier be held before a seed electron has
  almost certainly appeared.
- Seed-electron arrivals are treated as a Poisson process of constant rate.
  The probability that at least one electron has entered after a dwell is
  one minus the exponential of the dwell divided by the mean arrival
  interval, and the dwell needed for a stated seeding-confidence is the
  natural logarithm of one minus that confidence, scaled by the same
  interval. A confidence of exactly one is unreachable and is rejected as
  an input.
- The rate that matters is the rate delivered into the gap volume, not the
  rate leaving the source. Emission is reduced by a transport-fraction
  (the share of emitted electrons that survives the path to the gap mouth)
  and a gap-capture-fraction (the share of those that actually enter the
  field region), and, for a repetitively-pulsed gun, by its emission duty.
- A radioactive seed-source weakens between qualification and use. Its
  emission is decay-corrected to the run date by halving once per half-life
  elapsed; a campaign that quotes the certificate activity of a source
  several half-lives old overstates its seeding by the same factor.
- Seeding is a deliberate irradiation of the article. The accumulated
  seed-electron-fluence over the whole dwell schedule -- rate times total
  dwell, per unit gap area -- is bounded, because an over-irradiated
  dielectric or coating changes the very secondary-emission-yield the run
  is meant to probe.
- The drive schedule itself is ordered: forward-power rises step by step so
  that the first discharge observed is the lowest one. A schedule that
  repeats or reverses a level is a schedule defect, not a seeding finding.

## Workflow

1. Categorize the seed-source: a beta-emitter, ultraviolet photoemission
   lamp or direct-current electron gun emits continuously at unity duty; a
   repetitively-pulsed gun must declare the emission duty that derates it.
   Reject an unrecognised source kind and a continuously emitting source
   that claims a duty below unity.
2. For a decaying source, correct the emission to the run date from the
   certificate rate, the half-life and the elapsed interval. Reject a
   missing half-life, a non-positive half-life or a negative interval.
3. Reduce the corrected emission by the transport-fraction, the
   gap-capture-fraction and the emission duty to obtain the seed-electron
   rate entering the gap, and invert it to the mean arrival interval.
4. For each drive step, take the declared dwell, compute the Poisson
   initiation-probability at that rate, and compute the dwell required for
   the stated seeding-confidence. A dwell short of the requirement raises a
   per-step finding carrying the step identifier. Absorb float
   representation error at the comparison rather than lowering the
   confidence.
5. Confirm the schedule rises strictly in forward-power and that no step
   identifier repeats; either defect is an input error, raised before any
   verdict is formed.
6. Sum the dwells, compute the accumulated seed-electron-fluence per unit
   gap area, and compare it against the irradiation limit. Flag an
   exceedance, and separately flag a source left obstructing the drive
   path.
7. The arrangement is acceptable only when every step reaches the seeding
   confidence, the fluence stays within its limit, and the source does not
   perturb the drive.

## Pitfalls

- Quoting the certificate activity of a beta-emitter instead of its
  decay-corrected value -- a source two half-lives past its reference date
  delivers a quarter of the assumed rate, and every dwell sized from the
  certificate figure is four times too short.
- Reading a quiet run as a pass without checking the dwell against the
  arrival interval -- at a low delivered rate a short dwell is far more
  likely to have contained no seed electron than to have contained one that
  failed to multiply.
- Confusing the emitted rate with the delivered rate -- a lamp of generous
  output behind a narrow transport path and a poorly coupled gap mouth can
  deliver orders of magnitude less into the field region.
- Treating a repetitively-pulsed gun as continuous under a continuous-wave
  carrier -- it still only emits during its own bursts, and its average
  delivery is derated by its emission duty.
- Extending dwells indefinitely to buy seeding confidence -- the
  seed-electron-fluence accumulates with the same dwell, and past the
  irradiation limit the seed is modifying the surface it is probing.
- Relaxing the seeding-confidence so a marginal dwell passes -- when a
  dwell assembled from a ramp and a hold lands a few units in the last
  place under the requirement, absorb the representation error in the
  comparison; do not move the confidence.

## Behavior contract (gate 3)

The source-categorization, decay-correction, delivered-rate,
initiation-probability, required-dwell and fluence logic is exercised by the
gate 3 contract test:
scripts/test_e2001_seeding_for_continuous_wave_tests.py against
scripts/e2001_seeding_for_continuous_wave_tests_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_seeding_for_continuous_wave_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
