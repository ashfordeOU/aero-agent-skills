---
name: telemetry-data-acquisition
description: "Design and check the flight test telemetry and data acquisition chain: size the PCM minor frame and bit rate, assign supercommutated and subcommutated channels against the frame rate, encode the time of year in IRIG time format, condition the sensor signal to the ADC span, budget the end-to-end data latency against the requirement, and verify the ground station link margin and telemetry quality against the bit error rate and dropout limits. Produces the frame and bit rate, the channel assignments, the latency and link verdicts, and the quality verdict that gates the recorded data. Use when the task is flight test telemetry and data acquisition planning, PCM frame or IRIG time coding, data latency budgeting, signal conditioning, ground station link checks, or telemetry quality checks. Trigger: pcm telemetry formats, irig time coding, data latency, signal conditioning, ground station link, bit error rate, dropout."
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
  tags: [pcm-telemetry-formats, irig-time-coding, signal-conditioning, ground-station-link, data-latency, bit-error-rate, telemetry-quality-checks, supercommutated-channels, subcommutated-channels, frame-synchronization]
  version: 0.1.0
  author: AeroSkills
---

# Flight Test Telemetry and Data Acquisition (flight-test-operations/planning/telemetry-data-acquisition)

Use when the task is the flight test telemetry and data acquisition
chain: packing the sampled channels into the PCM minor frame, coding
the IRIG time, conditioning the sensor signals to the ADC span,
budgeting the data latency from the aircraft to the ground station,
checking the ground station link, and gating the recorded data on the
telemetry quality verdict.

## Domain quick reference

- PCM minor frame: a minor frame holds words_per_frame words of
  bits_per_word bits each, so the frame carries
  words_per_frame * bits_per_word bits. Example: 64 words of 16 bits
  give a 1024 bit frame.
- PCM bit rate: the stream sends the frame frame_rate times per
  second, so the bit rate is frame_rate * words_per_frame *
  bits_per_word. Example: 50 frames/s of 1024 bits give 51200 bit/s.
- Sample rates and anti-aliasing: every channel is sampled above its
  Nyquist rate with the anti-aliasing filter set ahead of the sampler
  (see flight-test-instrumentation for the rate sizing); the
  supercommutated and subcommutated assignments then fit those channel
  rates into the PCM minor frame.
- Supercommutation: a channel sampled faster than the frame rate
  appears channel_sample_rate / frame_rate times in every frame, and
  the ratio must be an integer greater than 1. Example: a 200 Hz
  channel on a 50 frame/s stream appears 4 times per frame.
- Subcommutation: a channel sampled slower than the frame rate is
  sampled once every frame_rate / channel_sample_rate frames, an
  integer greater than 1. Example: a 25 Hz channel on a 100 frame/s
  stream is sampled once every 4 frames.
- IRIG time coding: the IRIG-B stream transmits the day of year and
  the seconds of day at 100 pulses per second; the seconds of year are
  (day_of_year - 1) * 86400 + seconds_of_day, with day_of_year in
  1..366 and seconds_of_day in [0, 86400).
- Signal conditioning: the sensor signal is amplified by the gain so
  the conditioned span (sensor_span * gain) fits the ADC full-scale
  range; an over-range conditioned signal clips at the amplifier
  before the converter.
- Data latency: the end-to-end latency is the sum of the acquisition,
  processing, and link delays, and must meet the latency requirement;
  the pipeline holds latency_s * sample_rate buffered samples, rounded
  up.
- Ground station link: the link margin is the received power minus the
  receiver sensitivity and must meet the minimum margin; a link at the
  sensitivity limit shows a rising bit error rate and dropouts.
- Quality checks: telemetry is usable when the bit error rate stays at
  or below the limit and the dropout percentage stays at or below the
  limit; either exceedance flags the recorded data for review.

## Workflow

1. Define the minor frame with pcm_frame_size(words_per_frame,
   bits_per_word) and the stream with pcm_bit_rate(frame_rate,
   words_per_frame, bits_per_word).
2. Assign the channels: supercommutated_instances(channel_sample_rate,
   frame_rate) for fast channels and subcommutated_instances(frame_rate,
   channel_sample_rate) for slow channels; every instance count must
   come out an integer or the frame rate is re-sized.
3. Code the time of year on the stream with
   irig_b_time_of_year(day_of_year, seconds_of_day).
4. Condition each channel with conditioning_verdict(sensor_span, gain,
   adc_range); re-gain any channel that is over-range.
5. Budget the data latency with total_latency(acquisition_ms,
   processing_ms, link_ms), check it with latency_ok(total_ms,
   requirement_ms), and size the buffer with
   latency_buffer_samples(latency_s, sample_rate).
6. Check the ground station link with ground_link_ok(received_power_dbm,
   sensitivity_dbm, min_margin_dbm).
7. Gate the recorded data with telemetry_quality_ok(bit_error_rate,
   dropout_percent, ber_limit, dropout_limit); release the data only on
   a True verdict.

## Pitfalls

- Under-sampling a fast channel without supercommutation: the channel
  aliases or drops samples against the frame rate.
- A non-integer supercommutation or subcommutation ratio: a channel
  cannot appear a fractional number of times per frame; re-size the
  frame rate instead of rounding.
- Sending an over-range conditioned signal to the ADC: the amplifier
  clips before the converter and the top of the signal is lost.
- Ignoring part of the latency chain: the acquisition, processing, and
  link delays all count against the end-to-end requirement.
- Flying on a link with no margin: at the sensitivity limit the bit
  error rate rises and dropouts corrupt the stream.
- Releasing data that fails the quality check: bit errors and dropouts
  must be flagged before the data feeds the analysis.
- Confusing the time base: the IRIG seconds of year is anchored to the
  day of year and the seconds of day, not to the frame count.

## Behavior contract (gate 3)

The PCM frame and bit rate sizing, supercommutation and subcommutation
assignment, IRIG time of year coding, signal conditioning verdict,
data latency checks, ground station link margin, and telemetry quality
verdict logic is exercised by the gate 3 contract test:
scripts/test_telemetry_data_acquisition.py against
scripts/telemetry_data_acquisition_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_telemetry_data_acquisition.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 set the
  flight test and certification context; telemetry and data acquisition
  practice (PCM framing, IRIG time coding, supercommutation and
  subcommutation, signal conditioning, latency budgeting, link margin,
  quality checks) is common measurement and telemetry methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
