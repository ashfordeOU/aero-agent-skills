---
name: e1003-input-tolerances
description: "Use when you need to verify that each test input applied during a space qualification or acceptance campaign falls within the allowable deviation for its input type, as specified in ECSS-E-ST-10C §4.4.2 and Table 4-1. Categorize the input by type (temperature, pressure, supply voltage, frequency, random vibration power spectral density, sine vibration level, acoustic level, humidity, or test duration), compute the actual deviation from the nominal target, and confirm the deviation does not exceed the permitted band for that category. Flag any out-of-tolerance input before the test run proceeds. Trigger: ecss, e-st-10-system-scope, input-tolerances, test-tolerances, test-input, table-4-1, tolerance-band, acceptance-testing."
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
  tags: [ecss, e-st-10-system-scope, input-tolerances, test-tolerances, test-input, table-4-1, tolerance-band, acceptance-testing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS AIT — Test Input Tolerances (space-systems/ecss/e1003-input-tolerances)

Use when the task is to confirm that every test input stimulus applied to the
unit under test remains within the allowable deviation band specified for that
input type in ECSS-E-ST-10C §4.4.2 and its accompanying table of tolerances.

## Domain quick reference

- ECSS-E-ST-10C §4.4.2 defines the maximum permitted deviation between the
  nominal (required) value of a test input and the value actually applied
  during a test. Each input type carries its own allowable band; a single
  out-of-tolerance input renders the test run non-compliant until the
  condition is resolved or the test is repeated under correct conditions.
- Nine input categories are covered: temperature (absolute deviation in °C),
  pressure (relative deviation in %), supply voltage (relative in %), frequency
  (relative in %), random vibration power spectral density (deviation in dB,
  power-ratio convention), sine vibration level (relative in %), acoustic
  sound pressure level (deviation in dB), relative humidity (absolute in %RH),
  and test duration (relative in %). Each category carries its own
  asymmetric or symmetric band derived from the standard.
- Duration has a one-sided lower bound of 0 %: a test may run longer than
  nominal (up to the upper limit) but must never be cut short, because
  accumulated exposure is a minimum-threshold requirement.
- Random vibration PSD has a one-sided upper bound of 0 dB: the applied
  spectrum may be up to 1 dB below nominal but must not exceed the specified
  level, since over-testing can introduce damage not representative of the
  mission environment.
- Acoustic SPL uses an asymmetric band: a tighter upper limit than the lower
  limit, reflecting the asymmetric risk of over-test versus under-test for
  acoustic stimuli.

## Workflow

1. For each test input, identify its category (temperature, pressure, voltage,
   frequency, random vibration PSD, sine vibration, acoustic SPL, humidity, or
   duration). Reject any input whose category is not in the supported list
   before the check proceeds.
2. Record the nominal (specified) value and the actual (applied) value for
   that input, both in consistent physical units.
3. Compute the deviation using the rule for that category:
   - Absolute: actual minus nominal (temperature, humidity).
   - Relative: (actual minus nominal) / nominal × 100 % (pressure, voltage,
     frequency, sine vibration, duration).
   - Decibel: 10 × log₁₀(actual / nominal) on a power basis (random vibration
     PSD, acoustic SPL). Both values must be strictly positive.
4. Compare the computed deviation against the allowable band [lo, hi] for that
   category. The check is inclusive at both boundaries.
5. Record a finding for any input whose deviation falls outside the band,
   stating the category, computed deviation, and the band limits.
6. The test run is input-compliant only when every input check returns
   within-tolerance. A run with any open finding is not compliant.

## Pitfalls

- Applying the same percentage band to all input types: duration and vibration
  PSD use different deviation types (one-sided, dB) that cannot be compared
  on a percentage scale without first converting.
- Treating a duration shortfall as acceptable because the difference is small:
  the lower bound on duration is 0 %, meaning any under-run is an exceedance
  regardless of magnitude.
- Using a voltage-ratio convention (20 × log₁₀) for random vibration PSD: the
  PSD is a power quantity, so the correct factor is 10 × log₁₀, not 20. Using
  20 halves the apparent dB deviation and masks exceedances.
- Checking only the inputs that are easy to measure and skipping others (e.g.
  frequency drift during a long thermal soak): every input category must be
  verified, not just the ones logged automatically by the test facility.
- Confusing the allowable input tolerance with the measurement uncertainty of
  the test instrumentation: they are separate and must both be budgeted. This
  leaf covers only the input tolerance; instrumentation uncertainty is treated
  under ECSS-E-ST-10C §4.4.3.

## Behavior contract (gate 3)

The tolerance-band lookup, deviation computation, and per-input and batch
compliance checks are exercised by the gate 3 contract test:

```
python3 scripts/test_e1003_input_tolerances.py
```

The test suite is offline, deterministic, and uses stdlib unittest only.

## Compliance

- ECSS standards are freely downloadable from the ESA website; cite the
  source and paraphrase per the project standards-map.
- compliance: STANDARDS-REF, gated: false.
