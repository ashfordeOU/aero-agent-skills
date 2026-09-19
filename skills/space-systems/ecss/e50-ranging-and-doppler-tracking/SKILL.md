---
name: e50-ranging-and-doppler-tracking
description: "Compute radiometric range and range rate for a space link under ECSS-E-ST-50C clause 5.6.14.7, which asks that the communication system support ranging and Doppler tracking. Turn round-trip light time into range, fold it onto the interval the ranging code distinguishes, and lift it back out with an a-priori — but only while that a-priori is known to better than half an interval. Turn two-way Doppler into range rate through the transponder turnaround ratio, and test the shift against the receiver tracking band. Use when sizing a ranging code, an a-priori or a tracking loop. Trigger: ecss, e-st-50-communications, radiometric-range-ambiguity, ranging-code-period-sizing, two-way-doppler-range-rate, doppler-tracking-bandwidth, ranging-chip-rate-resolution."
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
  tags: [ecss, e-st-50-communications, e50-ranging-and-doppler-tracking, radiometric-range-ambiguity, ranging-code-period-sizing, two-way-doppler-range-rate, doppler-tracking-bandwidth, ranging-chip-rate-resolution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Ranging and Doppler Tracking (space-systems/ecss/e50-ranging-and-doppler-tracking)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.6.14.7 —
that the communication system supports ranging and Doppler tracking — and the
question is whether the link as designed can actually deliver either
observable.

## Domain quick reference

- Supporting an observable is not the same as producing one. A two-way
  range is only a range once its ambiguity is resolved, and a two-way
  Doppler is only a range rate once the carrier stays inside the
  tracking band long enough to be measured.
- The ranging code repeats, so the measurement repeats with it. Half a
  code period of round-trip time is one interval of one-way range, and
  everything beyond that interval comes back folded onto it.
- An a-priori resolves the fold only while it is good enough. Past half
  an interval of uncertainty the a-priori is as likely to name the
  neighbouring interval as the right one, and the resolved range is then
  wrong by a whole interval rather than slightly wrong.
- Chip rate and code period are separate knobs answering separate
  questions. Chip rate sets how finely the range is resolved; code
  period sets how far away it can be before it folds.
- The turnaround ratio belongs in the Doppler arithmetic. A shift
  computed against the uplink frequency alone is wrong by that ratio,
  and on an X-band transponder that is most of the answer.
- Tracking bandwidth is sized by the worst-case range rate, not the
  nominal one. The pass geometry that produces the largest rate is the
  one the receiver has to hold, and losing lock there loses the pass.

## Workflow

1. State the geometry: round-trip light time, code period, chip rate,
   uplink frequency, turnaround ratio, tracking bandwidth, and the
   worst-case range rate the pass will reach.
2. Convert round-trip time to one-way range, then fold it onto the
   interval the code distinguishes and keep both figures.
3. Decide whether the range is beyond one interval at all. Inside it
   there is nothing to resolve, and an a-priori is not needed.
4. Where it is beyond, test the a-priori uncertainty against half an
   interval before using it, and resolve only when that test passes.
5. Convert the range rate to a two-way Doppler shift through the
   turnaround ratio, and convert it back to confirm the relation used.
6. Test the shift against half the tracking bandwidth, and report the
   bandwidth the stated worst-case rate actually demands.
7. Grade an out-of-band carrier above an unresolved range — a link that
   cannot hold lock produces neither observable — and check any code
   period or bandwidth offered as a remedy against the same model.

## Pitfalls

- Reporting a folded range as the range. It is a perfectly precise
  measurement of the wrong interval, and nothing downstream can detect
  the error without an independent a-priori.
- Using an a-priori without stating its uncertainty. Resolution silently
  becomes an assumption, and it fails by exactly one interval, which is
  large enough to be mistaken for a manoeuvre.
- Sizing the code period from the nominal range. It is the maximum range
  over the mission that folds, and the extra code length is far cheaper
  before launch than an ambiguity campaign after it.
- Omitting the turnaround ratio from the Doppler conversion. The range
  rate comes out scaled by a constant, consistently, which makes it look
  like a real bias rather than an arithmetic slip.
- Sizing the tracking loop on the mean Doppler. The shift at closest
  approach is what breaks lock, and a loop that holds the average simply
  loses the interesting part of the pass.
- Deciding either limit with a bare inequality. A carrier sitting
  exactly on the band edge, or an a-priori exactly half an interval
  wide, then passes or fails by the rounding of the grading host.

## Behavior contract (gate 3)

Time, frequency, distance and turnaround-ratio validation, the round-trip to
range conversion and its inverse, the unambiguous interval, chip-rate
resolution, the interval count and range resolution with a half-interval
a-priori bound, two-way Doppler in both signs with its inverse, the tracking
band test at its exact edge, the bandwidth inverse, and the verdict ordering
that puts a lost carrier above an unresolved range are exercised by the gate 3
contract test:
scripts/test_e50_ranging_and_doppler_tracking.py against
scripts/e50_ranging_and_doppler_tracking_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_ranging_and_doppler_tracking.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
