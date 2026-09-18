---
name: e50-telemetry-at-all-attitudes-and-rates
description: "Determine whether essential telemetry reaches the ground at every spacecraft attitude and body rate under ECSS-E-ST-50C clause 5.5.1: close the downlink at each sampled point of the antenna pattern from transmit power, circuit loss, sampled gain, path loss, station figure of merit and data rate, weight the closing samples by angular width into a coverage fraction, then turn the width of any hole into an outage duration at the slowest declared body rate and hold it against how long the receiver keeps lock. Use when a low-gain pattern, a tumbling or safe-mode case or an omnidirectional link budget is reviewed. Trigger: ecss, e-st-50c-clause-5-5-1, telemetry-at-all-attitudes, low-gain-antenna-pattern-coverage, body-rate-fade-outage-duration, receiver-hold-through-fade, safe-mode-telemetry-availability."
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
  tags: [ecss, e-st-50-communications-scope, e50-telemetry-at-all-attitudes-and-rates, e-st-50c-clause-5-5-1, telemetry-at-all-attitudes, low-gain-antenna-pattern-coverage, body-rate-fade-outage-duration, receiver-hold-through-fade, safe-mode-telemetry-availability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications -- Telemetry at All Attitudes and Rates (space-systems/ecss/e50-telemetry-at-all-attitudes-and-rates)

Use when the task is clause 5.5.1 of ECSS-E-ST-50C: establishing that
essential telemetry gets to the ground whatever the spacecraft is doing
-- tumbling after separation, spinning in a safe mode, pointing its
high-gain antenna at empty sky. Two separate things break it. A hole in
the pattern, and a body rate that sweeps the ground through the hole in
a way the receiver cannot ride out.

## Domain quick reference

- The attitude case and the rate case are different failures. A pattern
  hole is a geometry problem fixed with antennas or a lower data rate; a
  rate problem is a timing one fixed with receiver hold-over or a
  narrower loop. A budget closed only at boresight answers neither.
- Coverage is an angular quantity, not a sample count. Six samples do
  not each own a sixth of the sphere unless they each stand for the same
  angular width, so every sample carries its own width and the coverage
  fraction is width-weighted. Counting samples instead flatters a
  pattern sampled densely where it is strong.
- Data rate is a term in the link, not a separate decision. Every
  doubling costs three decibels, so the honest question at a pattern
  null is not whether the link closes but at what rate it closes, and
  the essential-telemetry rate is the one that has to survive the worst
  attitude.
- The slowest body rate is the worst case for an outage, not the
  fastest. A fast spin sweeps the ground through a null quickly and the
  receiver rides it; a slow tumble parks the ground inside the null for
  as long as it takes to turn, which is the case that breaks lock.
- Receiver hold-over is the quantity that decides whether an outage is
  an outage. A hole shorter than the hold is a fade the demodulator
  rides through; a hole longer than it is a re-acquisition, and
  re-acquisition during a safe mode is exactly the moment telemetry was
  needed.

## Workflow

1. Validate the pattern: each sample carries an off-boresight angle
   inside the sphere, a strictly positive angular width and a gain, with
   a missing width refused rather than assumed uniform.
2. Build the EIRP at each sample from transmit power, circuit loss and
   the sampled gain.
3. Compute the received energy per bit from the EIRP, the path loss, the
   station figure of merit, the Boltzmann term and the data rate in dB.
4. Take the margin over the required value and any implementation loss,
   treating an exact landing on zero as closing.
5. Weight the closing samples by their widths into a coverage fraction
   and record the worst margin and the total failing width.
6. Convert the failing width into an outage duration at the slowest
   declared body rate and compare it with the receiver hold time.
7. Report coverage, worst margin, outage width, outage duration and the
   ride-through verdict separately, so a geometry finding is not
   reported as a timing one.

## Pitfalls

- Closing the budget at boresight and stopping. The clause is about the
  attitudes the spacecraft was not designed to be in, and those are
  exactly the samples a boresight budget never evaluates.
- Counting samples rather than angular width. A pattern sampled finely
  near the peak and coarsely in the back lobe reports high coverage that
  the sphere does not support.
- Taking the fastest body rate as the worst case. The fast case is the
  one the receiver survives; the slow tumble is the one that holds the
  ground inside the null.
- Judging a null against a high-rate downlink. Essential telemetry has
  its own rate, and evaluating the null at the payload rate condemns a
  link that would have closed at the rate that matters.
- Treating an exact zero margin as a failure. That is a representation
  question, handled by the tolerance inside the comparison; the required
  Eb/N0 stays as specified.

## Behavior contract (gate 3)

The pattern validation, EIRP and Eb/N0 construction, margin rule,
width-weighted coverage, outage-duration conversion and the
ride-through verdict are exercised by the gate 3 contract test:
scripts/test_e50_telemetry_at_all_attitudes_and_rates.py against
scripts/e50_telemetry_at_all_attitudes_and_rates_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e50_telemetry_at_all_attitudes_and_rates.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
