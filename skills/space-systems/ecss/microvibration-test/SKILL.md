---
name: microvibration-test
description: "Use when evaluate micro-vibration, microgravity, or noise disturbance test compliance for spacecraft equipment under ECSS-E-ST-32C clause 4.6.3.12: categorize each disturbance source as tonal, broadband, or transient, verify that the test measurement frequency band fully covers the required range, compute force and torque disturbance amplitudes using a force-measuring platform or equivalent fixture, compare each measured amplitude against the allocated disturbance budget, and flag any source whose amplitude exceeds the budget or whose frequency coverage is insufficient. Apply this skill when establishing or reviewing the test configuration, measurement chain, and pass/fail criteria for micro-vibration qualification or acceptance testing of rotating or oscillating equipment. Trigger: ecss, e-st-32-structures-scope, microvibration, micro-vibration, noise-disturbance, disturbance-budget, tonal-disturbance, broadband-disturbance, force-platform."
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
  tags: [ecss, e-st-32-structures-scope, microvibration, noise-disturbance, disturbance-budget, tonal, broadband, force-platform]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Micro-vibration / Noise Disturbance Test (space-systems/ecss/microvibration-test)

Use when the task is to evaluate micro-vibration, microgravity, or noise
disturbance test compliance for spacecraft equipment under ECSS-E-ST-32C
clause 4.6.3.12 — categorizing each disturbance source, verifying frequency
coverage, comparing measured amplitudes against allocated budgets, and
producing a pass/fail determination for each source and for the assessment
as a whole.

## Domain quick reference

- Clause 4.6.3.12 governs tests for equipment whose operation generates
  mechanical disturbances (reaction wheels, control moment gyroscopes,
  cryo-coolers, stepper motors, shutter mechanisms) that can degrade the
  performance of co-located sensitive payloads or instruments.
- Each disturbance source is placed into exactly one category before
  testing: tonal (discrete spectral line, e.g. a wheel at its spin
  frequency and harmonics), broadband (spectrally distributed random
  disturbance, e.g. bearing noise), or transient (impulse or short-duration
  event, e.g. a latch firing). Placement drives the measurement approach.
- The test measurement frequency range must cover the full required band
  stated in the equipment specification. A measurement that starts above
  the lower required frequency or ends below the upper required frequency
  is a gap, not a pass.
- Force and torque amplitudes are measured on a stiff force-measuring
  platform (or equivalent load cell / accelerometer chain with known
  transfer function). The measured amplitude at each frequency of interest
  is compared against the disturbance budget allocated to that source.
  Positive margin (budget minus measured ≥ 0) is required; zero margin is
  treated as marginal but compliant.
- A source that exceeds its budget at any frequency, or whose measurement
  does not cover the required band, is flagged as a finding. The overall
  assessment does not pass until every source clears both checks.

## Workflow

1. Inventory every disturbance-generating equipment item and categorize
   each as tonal, broadband, or transient. Reject any source whose type
   cannot be placed into one of these three categories before it enters
   the test matrix.
2. For each source confirm the test measurement frequency band: the band
   must span at least from the lower to the upper boundary stated in the
   equipment disturbance specification. Record any gap at the lower or
   upper bound as a finding.
3. Measure force and torque amplitudes on a force-measuring platform (or
   an approved equivalent fixture). Record the measured amplitude for
   each source at the frequency or band of interest.
4. Compare each measured amplitude against the disturbance budget allocated
   to that source. Compute the margin as budget minus measured amplitude.
   A negative margin is an exceedance; record it as a finding with the
   magnitude of the shortfall.
5. Aggregate findings per source: a source passes only when margin ≥ 0
   and frequency coverage has no gaps. A source with any finding is
   flagged.
6. Declare the assessment outcome: overall pass requires every source to
   pass. Report the count of failing sources and list all findings.

## Pitfalls

- Applying a tonal budget to a broadband source (or vice versa) invalidates
  the comparison — the budget and measurement must share the same spectral
  interpretation before any margin is meaningful.
- Reading a partial frequency measurement as coverage — if the measured
  range starts at 5 Hz and the specification requires from 1 Hz, the
  1–5 Hz band is uncovered and must be flagged, not treated as conservative.
- Treating zero margin as a failure — the convention for this assessment is
  margin ≥ 0, so zero is marginal but compliant. Recording it as a failure
  overstates the finding.
- Omitting a source from the test matrix because its amplitude is expected
  to be low — the budget check is the evidence; excluding sources before
  measurement introduces an unverified assumption that is itself a gap.

## Behavior contract (gate 3)

The source categorization, frequency coverage, margin computation, and
overall assessment logic is exercised by the gate 3 contract test:
scripts/test_microvibration_test.py against
scripts/microvibration_test_logic.py (stdlib unittest, offline). Run:

```
python3 scripts/test_microvibration_test.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
