---
name: e2001-level-one-multicarrier-method
description: "Use when assess the first-level multicarrier multipactor check of ECSS-E-ST-20-01C clause 5.3.2.2.4 for a critical region already treated for one carrier: convert each carrier-power into its own gap voltage, sum the crests into the worst-case peak-envelope voltage reached when every carrier aligns in phase, compare that against the single-carrier boundary voltage with the verification-route margin applied, and where the envelope crosses the derated boundary, derive the envelope repetition period from the carrier spacing, measure how long the crest holds above it, and set that dwell against the time a resonance needs to grow through the agreed number of gap crossings. Trigger: ecss, e-st-20-01c, e-st-20-electrical-scope, multicarrier-level-one-method, peak-envelope-voltage, envelope-repetition-period, gap-crossing-build-up-rule, envelope-dwell-time, carrier-frequency-spacing."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-level-one-multicarrier-method, multicarrier-level-one-method, peak-envelope-voltage, envelope-repetition-period, gap-crossing-build-up-rule, envelope-dwell-time, carrier-frequency-spacing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Level-One Multicarrier Method (space-systems/ecss/e2001-level-one-multicarrier-method)

Use when the task is the first-level multicarrier procedure of
ECSS-E-ST-20-01C clause 5.3.2.2.4 -- several carriers sharing one
critical region, where the voltage that matters is the envelope they
build together rather than any single carrier, and where a crest over
the boundary is judged on how long it lasts.

## Domain quick reference

- Carriers at different frequencies drift in and out of phase. Once per
  envelope repetition period every crest aligns, and the gap sees the
  arithmetic sum of the individual carrier voltages. That sum, not the
  root-sum-square and not the largest carrier, is the worst-case
  voltage the first level compares against the boundary.
- Because voltage adds while power goes as voltage squared, a set of
  equal carriers crests like one carrier of the square of the carrier
  count times the single-carrier power: four 50 W carriers crest like
  one carrier of 800 W, not 200 W. Budgeting on summed average
  carrier-power understates the crest by that factor.
- The envelope repeats at the reciprocal of the greatest common divisor
  of the carrier spacings. Widely spaced carriers give a short, sharp
  crest; closely spaced carriers give a long, flat one. The spacing
  plan is therefore part of the evidence, and a carrier plan change
  invalidates the assessment even at unchanged total carrier-power.
- A resonance is not established the instant the boundary is crossed:
  the electron population needs to survive an agreed number of gap
  crossings, each taking half a carrier period, before it grows into a
  discharge. So a crest above the boundary that collapses faster than
  that build-up time does not produce one, and the highest carrier
  sets the shortest build-up time, which is the conservative choice.
- The route margin is applied by derating the boundary before the dwell
  is measured, so the build-up criterion is judged against the derated
  boundary, never against the bare one.

## Workflow

1. Take the critical region, its single-carrier boundary voltage and
   the carrier plan: each carrier's frequency and its forward power.
   Reject a set with fewer than two carriers or a repeated frequency.
2. Convert each carrier-power into its gap voltage at the declared line
   impedance, with the standing-wave rise and the field-concentration
   factor applied to every carrier alike.
3. Sum the crests into the peak-envelope voltage, and record the
   equivalent single-carrier power it corresponds to, so the crest can
   be sanity-checked against the single-carrier result.
4. Convert the boundary-to-envelope ratio into a decibel margin and
   compare it with the margin owed by the verification route. A set
   that holds the owed margin on its crest is compliant, and no time
   argument is needed.
5. Where the crest is short of margin, derate the boundary by the owed
   margin, derive the envelope repetition period from the carrier
   spacings, and measure the longest time the crest holds above the
   derated boundary.
6. Compare that dwell with the build-up time of the agreed number of
   gap crossings at the highest carrier frequency. A shorter dwell is
   compliant by the build-up criterion, with the carrier plan recorded
   as part of the evidence; an equal or longer dwell is a predicted
   discharge calling for a larger gap or a reduced carrier plan.

## Pitfalls

- Adding carrier-powers instead of carrier voltages, which hides the
  square-of-the-count crest the aligned carriers actually produce.
- Assessing the strongest carrier alone because the others are small --
  every carrier adds its full crest voltage at the alignment instant.
- Measuring the dwell against the bare boundary and then claiming the
  route margin separately; the margin belongs in the derating before
  the dwell is judged.
- Taking the build-up time from the lowest carrier, which is the
  longest and the least conservative; the fastest carrier governs.
- Crediting the build-up criterion while leaving the carrier plan out
  of the assumptions, so a later frequency-plan change silently
  invalidates the only argument the compliance rested on.
- Treating carriers as incommensurate and skipping the envelope period,
  then sampling an arbitrary time window that never contains the crest.

## Behavior contract (gate 3)

The carrier-set validation, carrier-voltage, peak-envelope, envelope
period, dwell-measurement and build-up-criterion logic is exercised by
the gate 3 contract test:
scripts/test_e2001_level_one_multicarrier_method.py against
scripts/e2001_level_one_multicarrier_method_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_level_one_multicarrier_method.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
