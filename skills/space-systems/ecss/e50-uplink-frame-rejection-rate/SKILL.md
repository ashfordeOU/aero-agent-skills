---
name: e50-uplink-frame-rejection-rate
description: "Compute the rate at which a spacecraft rejects uplink frames and grade it against its bound, per ECSS-E-ST-50C clause 5.6.11.6: take the assumed bit error rate and the full on-air frame length, evaluate an uncoded frame as a log-domain tail and a corrected frame as a binomial tail, then report the retransmissions and the frames a pass is expected to lose. Use when an uplink budget quotes a per-frame rejection figure, an operator reports repeated telecommand retransmissions, or a decoder's strength is being traded against frame length. Trigger: ecss, e-st-50c-communications-scope, uplink-frame-rejection-rate, telecommand-frame-rejection, binomial-decoder-tail, uplink-retransmission-overhead, frame-length-error-trade."
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
  tags: [ecss, e-st-50c-communications-scope, e50-uplink-frame-rejection-rate, uplink-frame-rejection-rate, telecommand-frame-rejection, binomial-decoder-tail, uplink-retransmission-overhead, frame-length-error-trade]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Uplink Frame Rejection Rate (space-systems/ecss/e50-uplink-frame-rejection-rate)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.6.11.6 —
that the rate at which uplink frames are rejected stays inside its stated
bound at the assumed bit error rate — and the question is what that rate
actually is for a given frame and decoder.

## Domain quick reference

- A rejection is the good outcome. The frame was damaged and the receiver
  noticed; the clause bounds how often that happens because each one buys
  a retransmission, not because detection is a fault.
- The rate is a property of the whole on-air frame, not of its payload.
  Header, trailer and check symbol bits all ride the same channel and all
  contribute, so the length that matters is information plus every
  overhead bit.
- With no correction the rate is the probability that at least one bit is
  wrong. It grows with frame length faster than proportionally, which is
  why doubling the payload costs more than twice the rejections.
- With a decoder that corrects a fixed number of bit errors the rate is a
  binomial tail: the probability of more errors than it can fix. That is
  not a scaled version of the uncoded number, and correcting a single bit
  typically buys orders of magnitude, not a factor of two.
- The per-frame figure is not the operationally interesting one. Multiply
  it by the frames in a pass and by the mean transmissions per delivered
  frame before deciding whether the link is usable.
- The direct forms of both expressions are numerically unusable at real
  rates. One minus a near-one number and a tail reached by subtracting a
  near-one head both return noise, so the small side is summed directly
  and the arithmetic stays in the log domain.
- A rate that lands on its bound passes. Tail probabilities go through
  exponentials and logarithms that are not correctly rounded, so the
  comparison carries a relative tolerance instead of a strict inequality.

## Workflow

1. Add the overhead bits to the information bits to get the length the
   channel actually sees.
2. Take the assumed bit error rate as an input, refusing zero, one and
   anything outside them.
3. With no correction, evaluate the rejection rate in the log domain so
   a rate near ten to the minus nine survives.
4. With a decoder, sum whichever side of the binomial is the small one -
   the tail directly when the decoder is comfortably stronger than the
   expected error count, the head otherwise - and cap the number of terms.
5. Multiply the rate by the frames in a pass, and turn it into mean
   transmissions per delivered frame.
6. Compare with the bound inclusively and return the rate, the coding
   scheme, the pass-level consequence and the verdict.

## Pitfalls

- Using the payload length. The check symbol and headers are exposed to
  the channel too, and leaving them out understates the rate.
- Writing the uncoded rate as one minus a product. At the rates in this
  clause that subtracts two numbers agreeing to fifteen digits.
- Scaling the uncoded rate to approximate a coded one. The relationship
  is a binomial tail and the two differ by orders of magnitude.
- Reaching a small tail by subtracting the head from one. The head is
  indistinguishable from one in double precision and the tail comes back
  as exactly zero.
- Reporting only the per-frame figure. A rate of one in ten thousand is
  a lost frame every few seconds on a fast uplink.
- Forgetting that retransmissions compound. The mean transmissions per
  delivered frame, not the rejection rate, is what consumes the pass.
- Grading a rate that lands on the bound with a strict comparison. The
  verdict then depends on the platform's exponential.

## Behavior contract (gate 3)

Probability and bound validation, whole-count and frame-length assembly,
the log-domain uncoded rate, the binomial tail on both its small sides,
the summation guard, monotonicity in decoder strength, coding-scheme
naming, expected rejections per pass, retransmission overhead, the
inclusive bound comparison and the within / exceeded verdict are
exercised by the gate 3 contract test:
scripts/test_e50_uplink_frame_rejection_rate.py against
scripts/e50_uplink_frame_rejection_rate_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_uplink_frame_rejection_rate.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
