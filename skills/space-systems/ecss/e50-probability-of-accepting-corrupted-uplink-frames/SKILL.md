---
name: e50-probability-of-accepting-corrupted-uplink-frames
description: "Derive how often a spacecraft accepts a corrupted uplink frame as sound and grade it against its bound, per ECSS-E-ST-50C clause 5.6.11.7: multiply the residual corruption figure by the escape probability of every detection layer, build two to the minus k from an exact integer power of two, raise the per-frame number to a mission number, and search for the shortest check field that would suffice. Use when an uplink case bounds rejections but never bounds undetected corruption, or a frame check field length is being chosen. Trigger: ecss, e-st-50c-communications-scope, corrupted-uplink-frame-acceptance, undetected-uplink-frame-error, frame-check-escape-probability, uplink-detection-layer-stack, check-field-length-selection."
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
  tags: [ecss, e-st-50c-communications-scope, e50-probability-of-accepting-corrupted-uplink-frames, corrupted-uplink-frame-acceptance, undetected-uplink-frame-error, frame-check-escape-probability, uplink-detection-layer-stack, check-field-length-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Probability of Accepting Corrupted Uplink Frames (space-systems/ecss/e50-probability-of-accepting-corrupted-uplink-frames)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.6.11.7 —
that the probability of accepting a corrupted uplink frame as if it were
sound stays inside its stated bound — and the question is what that
probability is for a given detection design.

## Domain quick reference

- This is the dangerous half of the pair with the rejection rate. A
  rejected frame is a detected fault that costs a retransmission; an
  accepted corrupted frame is an undetected fault that gets executed, so
  its bound is always much tighter.
- The figure is a product of two independent things: how often a frame
  reaches the detector corrupted, and how often the detector misses. The
  first comes from the channel and any correction; the second comes only
  from the detection code.
- The escape probability of a well-behaved detection code of k bits is
  two to the minus k, and it does not move with the bit error rate.
  Improving the channel therefore buys the first factor and nothing at
  all from the second.
- Independent detection layers multiply. A frame check field plus an
  authentication tag plus a sequence check escape together only when all
  of them escape, which is why two sixteen-bit layers behave like one
  thirty-two bit layer.
- A layer that detects nothing is a layer with escape probability one. It
  belongs in the product as such, rather than being silently dropped,
  because dropping it hides that it was ever counted.
- The per-frame figure understates the exposure. The number worth
  arguing about is the chance of at least one acceptance across every
  frame the mission uplinks, and a rare per-frame event over a long
  mission is not rare.
- Two to the minus k has to be built from an exact integer power of two.
  Raising two to a negative power in floating point gives a value whose
  last bit can differ between hosts, and the shortest sufficient check
  length then comes out one bit different.

## Workflow

1. Take the residual corruption probability from the rejection analysis,
   after any error correction, rather than recomputing it here.
2. Build the escape probability of the frame check field by dividing one
   by an exact integer power of two, refusing a length that is a unit
   mistake.
3. Multiply in any further independent detection layer, keeping a layer
   that detects nothing visible as a factor of one.
4. Multiply the two factors to get the per-frame figure.
5. Raise it to the mission figure over the frames the mission uplinks,
   in the log domain, and report the mean gap between acceptances.
6. Compare with the bound inclusively, and search upward through integer
   check lengths for the shortest field that would satisfy it.

## Pitfalls

- Reusing the rejection bound here. Undetected acceptance is a different
  event with a far tighter limit, and one bound cannot serve both.
- Expecting a cleaner channel to fix an escape problem. The escape factor
  is fixed by the code length; only a longer or better code moves it.
- Counting a detection layer twice because it appears in two documents.
  The layers multiply, so a duplicate silently buys imaginary orders of
  magnitude.
- Dropping a layer that detects nothing instead of entering it as one.
  The product is then right by accident and unauditable.
- Quoting the per-frame figure as the answer. Over a mission's frame
  count the mission figure can be thousands of times larger.
- Raising two to a negative power in floating point. The exact integer
  power of two is free and reproducible.
- Solving for the check length with a logarithm. An integer search
  returns the same integer everywhere; a logarithm can land either side
  of a bit boundary.

## Behavior contract (gate 3)

Probability and count validation with controlled endpoints, the exact
integer power-of-two escape probability, its ceiling, the multiplication
of independent detection layers including a no-op layer, the per-frame
product, the log-domain mission figure, the mean gap between
acceptances, the inclusive bound comparison, the integer search for the
shortest sufficient check length and the within / exceeded verdict are
exercised by the gate 3 contract test:
scripts/test_e50_probability_of_accepting_corrupted_uplink_frames.py
against
scripts/e50_probability_of_accepting_corrupted_uplink_frames_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e50_probability_of_accepting_corrupted_uplink_frames.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
