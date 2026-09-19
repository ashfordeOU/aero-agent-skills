---
name: q7026-process-qualification
description: "Validate that a crimping process is qualified for the terminal and wire pairing actually in front of it under ECSS-Q-ST-70-26C. Use when a new contact, conductor construction, die or tool setting reaches a harness shop and the campaign that was run has to be graded rather than assumed: demand the declared samples per setup run, grade crimp height, pull-off force and visual together on every one, insist the conforming runs were consecutive instead of cherry-picked, separate an outright fail from a qualification standing with a centring finding, and say what puts it back in front of the campaign. Trigger: ecss, q-st-70-26, crimp-process-qualification, crimp-terminal-wire-combination, crimp-height-window, crimp-consecutive-run-repeatability, crimp-requalification-trigger."
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
  tags: [ecss, q-st-70-26-crimping-scope, q7026-process-qualification, crimp-terminal-wire-combination, crimp-height-window, crimp-consecutive-run-repeatability, crimp-requalification-trigger]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Process Qualification per Terminal and Wire (space-systems/ecss/q7026-process-qualification)

Use when the task is the process-control step of ECSS-Q-ST-70-26C —
demonstrating that a named tool, die and setting produces a conforming
crimp on a named terminal and conductor, repeatably, and saying when
that demonstration expires.

## Domain quick reference

- Qualification is a statement about a combination, not about a shop
  or a tool. Terminal part number, conductor construction, tool, die
  and setting together are the qualified item, so changing any one of
  them asks the question again rather than inheriting the answer from
  the pairing next to it on the bench.
- Repeatability needs consecutive setup runs. One good batch shows the
  shop managed it once with the tool as it happened to be set that
  morning, and the claim being made is about every morning.
- The conforming runs have to be consecutive. Picking the good runs
  out of a longer campaign and passing over the ones between them
  demonstrates selection rather than a controlled process, so the
  streak is measured on the run indices and a gap breaks it.
- Every sample is graded on crimp height, pull-off force and visual
  together. Height without force misses an undersized or partly
  inserted conductor; force without height misses a die that is
  slowly closing up and will fail the run after this one.
- A process centred near a window edge is a finding, not a failure.
  Every sample conformed, so the qualification stands, but the
  campaign has recorded that half the tolerance is already spent and
  ordinary drift will now leave the window.
- Qualification expires. A die regrind, a tool replacement, a setting
  change, a change of conductor construction or simple elapsed time
  each put the combination back in front of the campaign, and a
  change nobody declared a trigger for does not.
- A value landing exactly on a bound has met it. The comparison
  absorbs representation error from the gauge conversion; the window
  and the minimum are never moved to take a sample in.

## Workflow

1. Validate the specification: an ordered, non-collapsed crimp-height
   window, a positive pull-off minimum, the samples per run, the
   consecutive runs required, a validity period and the declared
   requalification triggers.
2. Validate every sample: a whole-numbered setup run index, a crimp
   height, a pull-off force and a boolean visual result.
3. Grade each sample on all three measures, collecting every reason
   rather than stopping at the first, and treat an exact landing on a
   bound as met through a named tolerance.
4. Group the samples by setup run and grade each run: enough samples
   for the declared run size, and every one of them conforming.
5. Measure the longest streak of consecutive conforming run indices,
   so a broken or gapped campaign cannot be read as a passing one.
6. Compute where the campaign sat inside the height window and raise a
   centring finding when its mean sits outside the central band.
7. Give the verdict — not qualified on a short streak or any run
   finding, qualified with a finding when only centring was raised,
   qualified otherwise — and separately grade whether a standing
   qualification has lapsed on time or on a declared change.

## Pitfalls

- Qualifying on one good batch. Repeatability across setups is the
  property being claimed and a single run cannot evidence it.
- Counting the good runs and ignoring the bad one between them. The
  streak is what demonstrates control, so a failed run resets it.
- Grading pull-off force alone because it is the number everyone
  quotes. A drifting die passes the pull test for weeks before it
  stops passing anything.
- Treating a centring finding as a failure and rejecting a conforming
  campaign, or ignoring it and losing the early warning that the
  tolerance is half spent.
- Inheriting a qualification across conductor constructions because
  the cross-section matched. Strand count and plating change how the
  barrel forms at the same crimp height.
- Widening the height window to absorb one sample. The campaign then
  evidences the wider window with a sample of one at its edge.

## Behavior contract (gate 3)

Specification and sample validation, three-measure sample grading with
both exact-bound cases, run grading on size and conformance, the
consecutive-run streak with its gap and break cases, window centring,
the three-way verdict and the validity-and-trigger requalification
check are exercised by the gate 3 contract test:
scripts/test_q7026_process_qualification.py against
scripts/q7026_process_qualification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7026_process_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
