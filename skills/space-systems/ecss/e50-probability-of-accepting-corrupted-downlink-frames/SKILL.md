---
name: e50-probability-of-accepting-corrupted-downlink-frames
description: "Assess all three obligations ECSS-E-ST-50C clause 5.6.11.9 places on an accepted corrupted downlink frame, grading each one separately: the per-frame figure against its bound, the derivation against the configuration actually declared, and the exposure across every frame the mission downlinks. Pairs a bounded-distance decoder's miscorrection probability, an exact rational, with the frame check field's escape probability. Use when a telemetry case bounds frame loss but never bounds undetected corruption, or a coding and check-field pairing is being chosen. Trigger: ecss, e-st-50c-communications-scope, corrupted-downlink-frame-acceptance, undetected-telemetry-frame-error, decoder-miscorrection-probability, frame-check-escape-probability, mission-frame-exposure."
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
    clause: 5.6.11.9
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50c-communications-scope, e50-probability-of-accepting-corrupted-downlink-frames, corrupted-downlink-frame-acceptance, undetected-telemetry-frame-error, decoder-miscorrection-probability, frame-check-escape-probability, mission-frame-exposure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Probability of Accepting Corrupted Downlink Frames (space-systems/ecss/e50-probability-of-accepting-corrupted-downlink-frames)

Use when the task is the three obligations of ECSS-E-ST-50C clause 5.6.11.9 —
that the probability of accepting a corrupted downlink frame stays inside its
bound, that the figure comes from the declared configuration, and that it is
demonstrated over the mission's frames — and the question is whether a
telemetry case really satisfies all three.

## Domain quick reference

- The clause has three obligations and they fail separately. A figure
  inside its bound that was derived from an undeclared rate proves
  nothing, and a per-frame figure inside its bound can still make an
  undetected corruption likely over a mission.
- Grading them as one verdict hides which one failed. The remedies are
  different: a tighter code, a corrected derivation, or a re-argued
  mission case.
- A coded downlink has two escape gates, not one. A block beyond the
  decoder's correction radius can land inside another codeword's radius,
  in which case the decoder reports success and passes up a wrong but
  valid block; that block then still has to get past the frame check
  field.
- Miscorrection is a property of the code's geometry, not of the
  channel. It is the fraction of the symbol space the decoding spheres
  cover, so a cleaner link does not reduce it at all.
- That fraction is a ratio of integers - a sum of binomials times powers
  of the symbol alphabet, over the alphabet raised to the parity length.
  Evaluated as an exact rational it is the same number everywhere;
  evaluated in floating point it is not.
- A declared input that nobody used is as bad as an input nobody
  declared. Both break the chain from assumption to result, and both
  read as compliant on the page where the result appears.
- The mission figure is the one an operator recognises. Over a hundred
  million frames a per-frame figure that looks negligible becomes the
  expected number of silently wrong frames.

## Workflow

1. Compute the decoder's miscorrection probability from the codeword
   length, correction radius and symbol width as an exact rational, and
   convert to a float once at the end.
2. Compute the frame check field's escape probability by dividing one by
   an exact integer power of two.
3. Multiply the codeword failure probability by the miscorrection
   probability, compound over the codewords a frame carries in the log
   domain, and multiply by the escape probability. Take the frame at
   the largest size the link sends: more codewords carry more chances
   to miscorrect, so that is the frame the recommended figure is
   written against.
4. Compare the declared derivation inputs with the inputs actually used,
   naming any that are missing or that disagree.
5. Raise the per-frame figure to the mission figure over the frames the
   mission downlinks.
6. Grade the three obligations separately, keep both escape gates
   visible in the report, and name every obligation that failed. The
   standard's own ceiling for a largest-size frame, below 10^-12, is
   put as a recommendation rather than a demand, so a figure above it
   is reported as falling short of what is recommended and not as a
   breach.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.11.9a | 6 |

## Pitfalls

- Collapsing the clause into one pass or fail. The reader then cannot
  tell whether the number, its provenance or its scope is the problem.
- Treating miscorrection as negligible because the decoder is strong.
  It is small, but it is the only path by which a decoder reports
  success on wrong data, and it does not shrink with a better link.
- Computing the sphere-covering ratio in floating point. The numerator
  and denominator are both enormous integers and the quotient is the
  only value that fits.
- Applying the frame check escape without the miscorrection gate, or the
  other way round. Either alone overstates the protection by orders of
  magnitude.
- Accepting a derivation whose inputs are stated somewhere but were not
  the ones used. That is the failure mode the second obligation exists
  to catch.
- Stopping at the per-frame figure. The third obligation is about the
  mission's frame count, which is where a negligible figure stops being
  negligible.
- Grading a figure that lands on its bound with a strict comparison.
  The verdict then turns on the platform's exponential.

## Behavior contract (gate 3)

Probability and count validation, the exact-rational miscorrection
probability with its code-geometry guards, the exact power-of-two escape
probability, the two-gate per-frame combination and its log-domain
interleave compounding, the declared-versus-used input comparison
including a missing, a null and a differently written input, the
log-domain mission figure, inclusive bound comparison and the separate
grading of all three obligations are exercised by the gate 3 contract
test:
scripts/test_e50_probability_of_accepting_corrupted_downlink_frames.py
against
scripts/e50_probability_of_accepting_corrupted_downlink_frames_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e50_probability_of_accepting_corrupted_downlink_frames.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
