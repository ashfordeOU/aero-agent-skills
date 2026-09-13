---
name: e2001-multi-frequency-test-overview
description: "Use when derive the equivalent single-carrier drive that represents multi-frequency operation in a multipactor test under ECSS-E-ST-20-01C clause 6.4.3.1: sum the carrier amplitudes into the peak-envelope-power, model the periodic envelope of a uniform equal-amplitude carrier-comb, compare its dwell above a candidate level against the twenty-gap-crossing onset time, bisect for the sustained-envelope-level when the envelope peak is too brief to seed a discharge, floor the result at the total average-power, apply the verification margin, and screen the drive against facility and continuous thermal-rating limits. Trigger: ecss, e-st-20-electrical-scope, e-st-20-01c, multi-frequency-test-overview, equivalent-single-carrier-drive, peak-envelope-power, twenty-gap-crossing-criterion, envelope-dwell-time, carrier-comb-spacing, over-test-ratio."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multi-frequency-test-overview, equivalent-single-carrier-drive, peak-envelope-power, twenty-gap-crossing-criterion, envelope-dwell-time, carrier-comb-spacing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Multi-Frequency Test Overview (space-systems/ecss/e2001-multi-frequency-test-overview)

Use when the task is the ECSS-E-ST-20-01C clause 6.4.3.1 overview decision:
whether a unit that carries several carriers in service can be verified with
one carrier raised to an equivalent power, and what that equivalent level
actually is.

## Domain quick reference

- N phase-aligned carriers of equal amplitude and uniform spacing build a
  periodic envelope whose peak voltage is N times the single-carrier
  voltage. The peak envelope power is therefore N squared times the
  per-carrier power, while the power the item carries continuously is only
  N times it. The two differ by a factor of N, which is why the
  substitution has to be derived rather than assumed.
- The envelope repeats at the carrier spacing, and the main lobe around
  each peak narrows as either the carrier count or the spacing grows. A
  wide comb has a very brief peak; a narrow comb has a peak that lasts a
  long time compared with a radio-frequency period.
- A discharge is not established the instant the envelope crosses the onset
  threshold. Electrons have to survive a number of gap crossings before the
  avalanche exists, and with a first-order resonance each crossing takes
  half a radio-frequency period. Twenty crossings is the usual working
  figure, which fixes an onset time that scales inversely with the test
  frequency.
- Comparing the two time scales is the whole decision. When the envelope
  stays above the peak level for longer than the onset time, the peak
  envelope power is the representative level. When it does not, the
  representative level is the lower sustained level whose dwell inside one
  envelope period equals the onset time, found by bisection on the envelope
  model. It is floored at the total average power, which is always present.
- The closed-form envelope holds only for a uniform equal-amplitude comb.
  A ragged or unequal comb has to fall back to the peak envelope power,
  which is conservative, and that fallback is recorded rather than hidden.
- The equivalent drive is a continuous level, so it dissipates far more
  than the operational average. The over-test ratio against the operational
  average and the screen against the continuous thermal rating are part of
  the overview, not an afterthought: a substitution the item cannot survive
  thermally is not a valid substitution.

## Workflow

1. Validate the carrier set: at least two carriers, positive frequency and
   power on each, no duplicated frequency; sort it by frequency.
2. Derive the peak envelope power from the sum of the carrier amplitudes
   and the total average power from the plain sum of the carrier powers.
3. Measure the comb: smallest spacing, carrier count, whether the spacing
   is uniform and whether the carrier powers are equal.
4. Compute the onset time from the test frequency and the gap-crossing
   count; both are explicit parameters, never buried constants.
5. If the comb is uniform and equal-amplitude, bisect the envelope model
   for the level whose dwell equals the onset time, and floor it at the
   total average power. Otherwise take the peak envelope power and record
   why the closed-form envelope was not used.
6. Name the basis that was applied -- peak envelope, sustained envelope
   level, or average-power floor -- so the test plan carries the reason and
   not only the number.
7. Apply the verification margin to obtain the equivalent single-carrier
   drive, then screen it against the facility capability and the continuous
   thermal rating, and report the over-test ratio against the operational
   average.
8. The substitution is valid only when the finding list is empty.

## Pitfalls

- Driving the single carrier at the total average power. That reproduces
  the heating and none of the peak voltage, so it verifies nothing about
  the discharge.
- Driving it at N times the per-carrier power instead of N squared times.
  Powers do not add when the carriers are phase-aligned; amplitudes do.
- Taking the peak envelope power for a widely spaced comb without checking
  the dwell. The peak can be shorter than the onset time, in which case the
  level being tested is not the level that can seed a discharge and the
  item is over-tested, sometimes past its thermal rating.
- Applying the closed-form envelope to a ragged or unequal comb. The
  expression assumes a uniform equal-amplitude comb; outside that it is
  simply the wrong curve.
- Forgetting that the equivalent drive is continuous while the operational
  peak is momentary. Quote the over-test ratio, and check the thermal
  rating, before committing to the substitution.
- Comparing the derived drive with a facility or thermal limit using bare
  floating-point equality. A drive assembled from a sum of square roots
  lands a few units in the last place off the same limit written another
  way; absorb that in the comparison, never by raising the limit.

## Behavior contract (gate 3)

The carrier-set validation, peak-envelope and average-power derivation,
comb descriptors, envelope model, dwell bisection, onset-time rule,
sustained-level search, margin application, feasibility screen and record
assembly are exercised by the gate 3 contract test:
scripts/test_e2001_multi_frequency_test_overview.py against
scripts/e2001_multi_frequency_test_overview_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e2001_multi_frequency_test_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
