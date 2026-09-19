---
name: e50-on-board-network-error-rates
description: "Evaluate an on-board network against its error-rate budget under ECSS-E-ST-50C clause 5.7.1.8. Turn a channel bit error rate into a frame error rate for the frame length in use, derive errored frames per second and the mean time between errored frames at the offered traffic rate, estimate the residual undetected error rate left after the frame check sequence, project undetected errors across the mission, and compare raw and residual figures with the required values. Use when writing or reviewing an on-board link error budget. Trigger: ecss, e-st-50-communications, onboard-network-error-rate, bit-error-rate-to-frame-error-rate, residual-undetected-error-rate, mean-time-between-errored-frames, frame-check-sequence-coverage."
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
  tags: [ecss, e-st-50-communications, e50-on-board-network-error-rates, onboard-network-error-rate, bit-error-rate-to-frame-error-rate, residual-undetected-error-rate, mean-time-between-errored-frames, frame-check-sequence-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — On-Board Network Error Rates (space-systems/ecss/e50-on-board-network-error-rates)

Use when an on-board network has an error-rate requirement under
ECSS-E-ST-50C clause 5.7.1.8 — converting a channel bit error rate into the
frame-level and residual figures a system actually has to live with, and
grading them against what was required.

## Domain quick reference

- A bit error rate is an input, not an answer. What a system suffers is
  errored frames, at the rate it sends them, and two links with the
  same bit error rate but different frame lengths fail at different
  rates.
- The frame error rate is 1 - (1 - BER)^n. The n*BER shortcut is fine
  while the product stays far below one and drifts steadily optimistic
  as frames lengthen; on a long frame over a poor channel it reports
  more than certainty.
- Compute it through log1p and expm1, not through a power. At the rates
  a spacecraft link works at, (1 - BER)**n rounds to exactly one and
  the subtraction returns zero — a perfect link produced entirely by
  floating point.
- The mean time between errored frames is the operator-facing form of
  the same number, and it is undefined rather than infinite on an
  error-free claim or a silent link. A figure there implies a
  guarantee nobody made.
- The residual undetected error rate is the one that matters for data
  integrity. A check sequence of w bits still maps roughly one damaged
  frame in 2^w onto a valid syndrome, and nothing downstream will ever
  catch those — no retransmission scheme sees an error it was not told
  about.
- Mission exposure turns the residual rate into a count. It is the
  number a data-integrity case rests on, and it is zero only because
  no duration was declared, which is not the same as safe.

## Workflow

1. State the channel bit error rate, the frame length in bits, the
   offered link rate, the width of the frame check sequence and the
   mission duration. Refuse a fractional frame or field length and a
   probability outside zero to one.
2. Convert to a frame error rate for the frame length actually in use,
   through log1p and expm1 so the answer survives a very good channel.
3. Derive frames per second and errored frames per second, and from
   them the mean time between errored frames — reported as undefined
   where the channel was declared error-free or the link carries
   nothing.
4. Apply the check sequence to get the residual undetected error rate,
   scaling by an exact power of two rather than one built by
   multiplication.
5. Project the residual across the mission to get the expected count of
   undetected errors, and say plainly when no duration was declared.
6. Compare the achieved bit error rate and the residual rate with their
   required values, using a tolerance scaled to the values themselves.
   An absolute tolerance at these magnitudes would pass a budget missed
   by orders of magnitude.
7. Report the two budgets separately. A link can meet its bit error
   rate and still fail its residual requirement, and the remedy for
   that one is a wider check sequence or a shorter frame, not a better
   channel.

## Pitfalls

- Quoting the bit error rate as the error budget. It is the channel
  property; the requirement is almost always about frames, data
  integrity, or time between events, and those depend on frame length
  and traffic rate as much as on the channel.
- Using n*BER on a long frame. It reads high once the product
  approaches one, and on a bad channel it returns a frame error rate
  above unity, which nothing downstream is prepared for.
- Computing (1 - BER)**n directly. At 1e-9 and a kilobit frame the
  power rounds to one, the subtraction gives zero, and the link is
  declared perfect by the arithmetic rather than by the design.
- Reporting an infinite mean time between errored frames. An
  error-free declaration is an assumption; turning it into an infinity
  hands downstream analysis a guarantee that was never made.
- Stopping at the detected error rate. Retransmission fixes what the
  check sequence catches; the residual is precisely the part it does
  not, and it is the only part a data-integrity case has to argue
  about.
- Judging tiny rates with an absolute tolerance. At 1e-16 an absolute
  slack of 1e-9 accepts every design, including one that misses the
  requirement by seven orders of magnitude.
- Reporting zero mission exposure because no duration was given. That
  zero is a missing input, not a safe result.

## Behavior contract (gate 3)

Probability and bit-count validation, the frame error rate at both ends
of its range and against the naive product, frames and errored frames
per second, the undefined mean time on an error-free or silent link, the
residual scaled by the check width, mission exposure, the bit-error-rate
inverse round trip, and the two budgets graded separately at and past
their bounds are exercised by the gate 3 contract test:
scripts/test_e50_on_board_network_error_rates.py against
scripts/e50_on_board_network_error_rates_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_e50_on_board_network_error_rates.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
