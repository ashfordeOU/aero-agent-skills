---
name: e50-downlink-frame-rejection-rate
description: "Compute how often the ground rejects a downlink telemetry frame and grade it against its bound, per ECSS-E-ST-50C clause 5.6.11.8: turn the assumed bit error rate into a symbol error rate, walk the block decoder's binomial tail with an integer recurrence, compound it over the codewords a frame interleaves, and report the payload a pass loses outright because telemetry is rarely resent. Use when a telemetry budget quotes a frame loss figure, a block code or interleaving depth is being traded, or a pass keeps returning gaps. Trigger: ecss, e-st-50c-communications-scope, downlink-frame-rejection-rate, telemetry-frame-loss, symbol-error-probability, block-decoder-codeword-failure, telemetry-interleaving-depth."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.11.8
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50c-communications-scope, e50-downlink-frame-rejection-rate, downlink-frame-rejection-rate, telemetry-frame-loss, symbol-error-probability, block-decoder-codeword-failure, telemetry-interleaving-depth]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Downlink Frame Rejection Rate (space-systems/ecss/e50-downlink-frame-rejection-rate)

Use when the task is the single recommendation of ECSS-E-ST-50C clause
5.6.11.8 — that the rate at which downlink frames are rejected should stay
below one in a hundred thousand at the assumed bit error rate — and the
question is what that rate is for a given block code, symbol width and
interleaving depth.

## Domain quick reference

- The downlink is not the uplink reversed. A rejected telecommand is
  retransmitted; a rejected telemetry frame is usually gone, because the
  spacecraft has moved on and nothing asks for it again. The consequence
  of this rate is data loss per pass, not link occupancy.
- The failing unit is a symbol, not a bit. A block code protecting
  multi-bit symbols loses one symbol to a burst that corrupts every bit
  in it, and the decoder's strength is quoted in correctable symbols.
- Converting bits to symbols is not multiplication. A symbol fails when
  at least one of its bits does, which is close to the bit rate times the
  symbol width only while that product is small.
- A frame carries several codewords. It is rejected when any one of them
  is beyond correction, so the frame rate is worse than the codeword rate
  by roughly the interleaving depth, and quoting the codeword rate as the
  frame rate understates the loss.
- The codeword figure is a binomial tail over symbols. It falls very
  steeply with decoder strength, which is why one extra correctable
  symbol can be worth more than a decibel of margin.
- Walking the tail upward from its first term with an exact integer
  recurrence avoids ever building a large binomial coefficient and
  avoids ever subtracting a near-one head from one.
- Both compounding steps belong in the log domain. At the rates this
  clause deals with, one minus a product of numbers that agree to fifteen
  digits returns zero.

## Workflow

1. Take the assumed downlink bit error rate and the symbol width, and
   convert to a symbol error probability in the log domain.
2. Evaluate the codeword failure probability as the binomial tail beyond
   the decoder's correctable symbol count, starting at the first tail
   term and stepping upward by recurrence.
3. Stop the summation once a term is negligible against the running
   total, so the cost does not scale with the codeword length.
4. Compound the codeword figure over the codewords a frame interleaves,
   again in the log domain.
5. Multiply by the frames in a pass and by the payload bits per frame to
   state the loss in the units the mission cares about.
6. Compare with the recommended level — a frame rejection rate below
   1e-5 — and with any tighter figure the project sets, deciding the
   boundary inclusively so the verdict does not change with the build
   host. Return it with both intermediate figures kept visible. The
   clause recommends this level rather than requiring it, so a rate
   above it is reported as a recommendation not met, with its margin,
   rather than as a breach.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.11.8a | 6 |

## Pitfalls

- Reusing the uplink rejection analysis. The coding unit, the coding
  scheme and the consequence of a loss are all different.
- Multiplying the bit error rate by the symbol width. That is a small-
  argument approximation, and it is wrong exactly where the rate is
  large enough to matter.
- Quoting the codeword failure probability as the frame rejection rate.
  A frame with five codewords is rejected about five times as often.
- Treating the decoder's correctable symbol count as a linear knob. The
  tail is steep, so one symbol of extra strength moves the answer by
  orders of magnitude.
- Building the binomial coefficient directly. For a long codeword it is
  an enormous integer, and computing it is both slow and unnecessary.
- Reaching the tail as one minus the head. The head is indistinguishable
  from one in double precision and the tail comes back as exactly zero.
- Reporting the rate without the data loss. A rate that looks acceptable
  per frame can be a substantial fraction of a pass once multiplied out,
  and nothing is coming back for it.

## Behavior contract (gate 3)

Probability and count validation, the log-domain symbol error
probability, the codeword binomial tail cross-checked against an
independent brute-force sum, monotonicity in decoder strength, the
interleaving compound, the end-to-end rate, frames and payload bits lost
per pass, the inclusive bound comparison and the within / exceeded
verdict are exercised by the gate 3 contract test:
scripts/test_e50_downlink_frame_rejection_rate.py against
scripts/e50_downlink_frame_rejection_rate_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_downlink_frame_rejection_rate.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
