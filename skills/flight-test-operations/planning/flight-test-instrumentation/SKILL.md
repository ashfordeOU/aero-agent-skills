---
name: flight-test-instrumentation
description: "Use when you must design flight test instrumentation: select sensors for the measurement parameters (air data, accelerations, angular rates, strain, control positions, engine data) with the right range, accuracy, and bandwidth, size the data acquisition sample rate against the anti-aliasing and Nyquist limits, and verify the recording, telemetry, pre-test calibration, and measurement uncertainty chain before the test. Applies the Nyquist criterion, sensor range checks, ADC quantization, and calibration currency to release an instrumented channel for flight. Trigger: instrumentation design, sample rate, anti-aliasing, Nyquist, sensor selection, telemetry, calibration, measurement uncertainty."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: planning
  tags: [flight-test-instrumentation, instrumentation-design, sample-rate, anti-aliasing, nyquist, sensor-selection, telemetry, calibration, measurement-uncertainty, data-acquisition]
  version: 0.1.0
  author: AeroSkills
---

# Flight Test Instrumentation (flight-test-operations/planning/flight-test-instrumentation)

Use when the task is designing the flight test instrumentation chain:
choosing sensors and their ranges for the measurement parameters,
sizing the data acquisition sample rate against the Nyquist and
anti-aliasing limits, checking the ADC resolution, and confirming
recording, telemetry, calibration, and uncertainty before the test.

## Domain quick reference

- Measurement parameters: air data (static and pitot pressure,
  airspeed, angle of attack and sideslip), accelerations (load
  factors in g), angular rates (deg/s), strain (microstrain or N
  via calibrated bridges), control positions (deg), engine data
  (rpm, fuel flow, pressures, temperatures). Every parameter needs a
  sensor with a defined range, accuracy, and bandwidth.
- Sensor selection: the sensor range must cover the full expected
  signal plus margin, the accuracy must be better than the
  measurement requirement, and the bandwidth must extend beyond the
  highest frequency of interest. Units stay SI (Hz, V, g, N).
- Nyquist criterion: a signal of maximum frequency fmax can be
  reconstructed from samples only when the sample rate fs satisfies
  fs >= 2 * fmax. Below the Nyquist rate, aliasing folds high
  frequencies into the passband.
- Required sample rate: practical chains sample above Nyquist to
  leave headroom for the anti-aliasing filter rolloff:
  fs_req = margin * 2 * fmax, default margin 2.5 (5 times fmax).
- ADC quantization: an N-bit converter over a full-scale range R
  resolves steps of R / 2^N (1 LSB); the worst-case quantization
  error is half the step.
- Anti-aliasing: an analog low-pass filter ahead of the sampler must
  attenuate everything above half the sample rate; sample rate and
  filter cut-off are chosen together, never separately.
- Calibration: every channel is calibrated before the test with
  traceable standards; a channel is usable only when it is calibrated
  and recalibration is not due.
- Measurement uncertainty: the combined standard uncertainty is the
  root-sum-square of the sensor, conditioning, ADC, and calibration
  components; the expanded uncertainty uses the coverage factor.

## Workflow

1. List the measurement parameters for the test and their expected
   ranges, accuracies, and maximum frequencies (SI units).
2. Select each sensor and check the range with
   sensor_range_verdict(measured_value, sensor_range); re-select
   when the value is over-range.
3. Size the acquisition chain: compute the required rate with
   required_sample_rate(max_freq, margin) and confirm it with
   nyquist_ok(sample_rate, max_freq).
4. Choose the ADC width and check the resolution with
   quantization_error(bits, range); the step must be small enough for
   the accuracy requirement.
5. Confirm the recording and telemetry path covers every channel at
   the chosen rate, with time correlation across channels.
6. Verify pre-test calibration with
   calibration_verdict(calibrated, due); release the channel only on
   a True verdict.
7. Estimate the measurement uncertainty from the component errors and
   record it with the data.

## Pitfalls

- Sampling below the Nyquist rate: aliased data is unrecoverable, no
  post-processing can remove it.
- Over-range sensors clip: an over-range value is not a measurement,
  it is a saturated channel.
- Choosing the ADC without the range: the resolution depends on both
  the bit count and the full-scale range.
- Sampling exactly at Nyquist: the criterion is a lower bound, not a
  target; real chains add margin for the anti-alias filter rolloff.
- Anti-aliasing without a filter, or a filter without the rate: the
  two are sized together.
- Flying on a channel whose calibration is due: the data cannot be
  traced to standards and the point is invalid.
- Mixing units: g, N, and V are not interchangeable without the
  documented sensitivity of each channel.
- Reporting uncertainty from one component only: the combined
  uncertainty sums all contributions in quadrature.

## Behavior contract (gate 3)

The Nyquist check, sensor range verdict, ADC quantization
resolution, required sample rate, and calibration verdict logic is
exercised by the gate 3 contract test:
scripts/test_flight_test_instrumentation.py against
scripts/flight_test_instrumentation_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_flight_test_instrumentation.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 set the
  flight test and certification context; instrumentation design
  practice (Nyquist sampling, sensor selection, quantization,
  calibration, uncertainty) is common measurement methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
