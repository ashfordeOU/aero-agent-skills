---
name: e50-tolerance-of-run-lengths-and-transition-densities
description: "Analyze a transmitted symbol stream for the longest run of identical symbols and the density of transitions it offers, under ECSS-E-ST-50C clause 5.6.11.3, and decide whether the receiver clock recovery tolerates both. Measure the worst run and where it starts, the transition density over the whole stream and over the leanest sliding window the loop integrates, compare each against the declared limits, count the edges a starved window is missing, and report whether randomisation or a transition-rich line code is required. Use when checking bit synchronisation robustness on a spacecraft telemetry or telecommand link. Trigger: ecss, e-st-50-communications, bit-stream-run-length-limit, symbol-transition-density, clock-recovery-tolerance, sliding-window-transition-check, link-randomisation-need."
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
  tags: [ecss, e-st-50-communications, e50-tolerance-of-run-lengths-and-transition-densities, bit-stream-run-length-limit, symbol-transition-density, clock-recovery-tolerance, sliding-window-transition-check, link-randomisation-need]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Tolerance of Run Lengths and Transition Densities (space-systems/ecss/e50-tolerance-of-run-lengths-and-transition-densities)

Use when a space link has to carry whatever bit pattern the source produces,
per ECSS-E-ST-50C clause 5.6.11.3 — the longest stretch without an edge, and
whether there are enough edges everywhere to hold bit synchronisation.

## Domain quick reference

- Two obligations on the same receiver. It has to coast through the
  longest run of identical symbols the stream contains, and it has to
  be fed enough transitions to stay locked. A stream can satisfy one
  and break the other, so both are measured and both are reported.
- A density is transitions over opportunities, and a stream of n
  symbols offers n-1 of them. A one-symbol stream offers none, which is
  an undefined density rather than a density of zero.
- The average is the trap. A stream that alternates for a while and
  then sits still has a respectable overall density and a window in the
  middle with no edges at all — and the loop unlocks in that window,
  not in the average.
- So the measurement that matters is the leanest sliding window of the
  length the recovery loop integrates over, reported with where it
  starts. A position is actionable; a stream-wide figure is not.
- The shortfall belongs in whole edges. Telling a designer a window is
  0.083 short of a density is arithmetic; telling them it is one
  transition short is a change they can make.
- Both failures have the same family of remedies — randomise the
  stream, or move to a line code that guarantees edges — and naming
  which obligation failed says how much conditioning is needed.

## Workflow

1. Take the stream as it will be transmitted, after any framing and
   before or after conditioning as the question requires. Reject
   anything that is not a binary symbol rather than coercing it: a
   stream that silently became all zeros reports itself as the worst
   run in the design.
2. Group the stream into runs and take the longest, keeping its start
   position and its symbol. Ties go to the earliest occurrence so the
   answer points at the first place to look.
3. List every run over the tolerated length, not only the worst. A
   second offender says the pattern is structural rather than a one-off.
4. Compute the overall transition density, and treat a stream too short
   to contain an opportunity as undefined.
5. Compute the leanest sliding window of the receiver's integration
   length, with its start position and its transition count.
6. Convert the density limit into a whole number of transitions per
   window, rounding up but not past an exact boundary, and report the
   shortfall in edges.
7. Compare each bound with a relative tolerance, then state which
   obligation failed and whether conditioning is required.

## Pitfalls

- Judging the stream on its average transition density. The loop
  unlocks inside the leanest window, which an average hides completely.
- Reporting zero density for a stream with no transition opportunity.
  It is undefined, and a zero there reads as a starved loop instead of
  a stream too short to ask about.
- Reporting only the worst run. A single long run may be one unlucky
  frame; several say the source pattern needs conditioning.
- Expressing the density shortfall as a fraction. Edges are whole, and
  rounding the requirement down passes a window one transition short.
- Comparing a density against its limit with a bare inequality. Two
  arithmetically identical streams can straddle the bound on different
  machines, so the verdict follows the build host.

## Behavior contract (gate 3)

Stream, limit and density validation, run grouping with position and
tie handling, the over-limit run list, the overall and worst-window
densities, the undefined density of a one-symbol stream, the whole-edge
requirement and shortfall, the three-way verdict with a tolerance at
each bound and the average-hides-a-lean-window case are exercised by the
gate 3 contract test:
scripts/test_e50_tolerance_of_run_lengths_and_transition_densities.py
against
scripts/e50_tolerance_of_run_lengths_and_transition_densities_logic.py
(stdlib unittest, offline).
Run:
python3 scripts/test_e50_tolerance_of_run_lengths_and_transition_densities.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
