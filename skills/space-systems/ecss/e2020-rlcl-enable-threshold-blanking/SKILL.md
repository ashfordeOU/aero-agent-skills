---
name: e2020-rlcl-enable-threshold-blanking
description: "Determine whether a retriggerable latching current limiter stays off through a brief bus excursion. Use when an ECSS-E-ST-20-20C clause 5.4.4.3.1 enable design has to be shown sound: validate the enable and release points with their hysteresis, interpolate the crossings of a sampled bus trace to measure how long each excursion really dwells above the enable point, grade every nuisance excursion and every genuine request against the confirmation time, then report the feasible confirmation window and the margin at each end. Refuses an inverted threshold pair, thin hysteresis and an excursion that never settles below the release point. Trigger: ecss, e-st-20-20c, rlcl-enable-threshold, rlcl-enable-confirmation-time, enable-excursion-dwell, enable-release-hysteresis, retriggerable-limiter-turn-on, rlcl-nuisance-enable-blanking."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-rlcl-enable-threshold-blanking, rlcl-enable-threshold, rlcl-enable-confirmation-time, enable-excursion-dwell, enable-release-hysteresis, retriggerable-limiter-turn-on]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — RLCL Enable Threshold Blanking (space-systems/ecss/e2020-rlcl-enable-threshold-blanking)

Use when the task is the enable-point behaviour of ECSS-E-ST-20-20C
clause 5.4.4.3.1 — showing that a short excursion of the bus above the
enable point of a retriggerable latching current limiter leaves that
limiter off, and that the mechanism which delivers it does not also
swallow the turn-on the mission actually wants.

## Domain quick reference

- A retriggerable limiter watches its input and enables itself when the
  bus rises past an enable point, instead of waiting for a command. That
  autonomy is the whole reason the clause exists: nothing downstream
  arbitrates, so the enable decision has to be right on its own.
- A bus is noisy. A neighbouring load switching off, a transient on the
  primary side, or the tail of a fault recovery can all push the rail
  briefly past the enable point while the bus has not actually come
  back. Those excursions are the nuisance population the design rides
  through.
- The mechanism is a confirmation time: the enable condition holds
  continuously for a declared interval before the output is allowed on.
  A level comparison on its own has no memory and cannot tell a spike
  from a recovery.
- Sizing that interval is two-sided. Too short and a nuisance excursion
  outlasts it, so the limiter comes on into a bus that is not there. Too
  long and a genuine enable request is swallowed and the load never comes
  up — the failure a noise-only test never shows, because it only
  exercises the excursions.
- So the feasible window is bounded below by the longest nuisance
  excursion, raised by its margin, and above by the shortest genuine
  request, lowered by its own. A window whose ends have crossed is a
  finding in itself: no confirmation time serves both duties, and the
  thresholds or the hysteresis have to move instead.
- Enable and release are two different levels. The hysteresis between
  them is what stops the limiter chattering on the way through, so a
  band that is the wrong way up, or too narrow, is refused before any
  dwell is measured.
- Dwell comes from interpolated crossings of the enable point, not from
  counting samples: a sample-counted dwell is quantised by the logging
  rate and reports an excursion up to one sample interval away from the
  one the hardware saw.
- The margins, the hysteresis floor and the recovery rule are declared
  project policy rather than physical constants; the defaults in the
  logic module are a starting point a project substitutes its own values
  into.

## Workflow

1. Validate the policy and the threshold pair: a release point below the
   enable point, and a hysteresis band at or above the project floor. A
   pair that is the wrong way up is a data error, not a tight design.
2. Reduce each declared event to a dwell above the enable point. Where a
   sampled trace is given, take the crossings by interpolation and keep
   the longest excursion in the trace together with its peak.
3. Refuse to grade an excursion that never settles back below the
   release point: its enable condition has no resolved state, so it is
   reported as unresolved rather than passed or failed.
4. Grade every nuisance excursion against the confirmation time — it has
   to finish, with margin, before the interval expires — and every
   genuine request the other way, since it has to outlast the interval by
   its own margin to be honoured.
5. Form the feasible confirmation window from the worst event of each
   kind and say whether the declared confirmation time sits inside it.
6. Report a balanced recommendation between the two bounds when the
   window is open, and when it is closed report that fact rather than a
   number no hardware can meet.
7. Name the event behind every finding so a reviewer sees which
   excursion, not just which verdict, drove the result.

## Pitfalls

- Grading the enable on the level alone. A comparator that trips at the
  enable point is correct at every instant and still wrong overall,
  because the decision the clause asks for is about duration.
- Sizing the confirmation time against the nuisance population only.
  That end of the window is the one a noise test exercises, so it is the
  end that gets tuned, and the genuine request that is quietly swallowed
  is discovered on the spacecraft.
- Counting samples to get a dwell. The count is quantised by the logging
  rate, so a 9 ms excursion logged at 5 ms reads as 10 ms or as 5 ms
  depending on where the samples fell; the crossings are interpolated
  instead.
- Treating an excursion that never returns below the release point as a
  long excursion. It is an unresolved state, and calling it long invents
  a dwell the trace does not contain.
- Setting the release point just under the enable point to look
  decisive. The band is what keeps the enable from chattering, and a
  narrow band converts one bus event into a burst of turn-ons.
- Comparing a dwell with a confirmation time by bare arithmetic. An
  excursion meant to land exactly on the interval, or exactly on its
  margin, can fall a few units in the last place the wrong side of the
  bound; the comparison absorbs that representation error while the
  interval and the margins stay as specified.

## Behavior contract (gate 3)

The policy validation, threshold-band validation, waveform validation,
interpolated crossings, event measurement, event grading, feasible
window, recommendation and the full design judgement are exercised by
the gate 3 contract test:
scripts/test_e2020_rlcl_enable_threshold_blanking.py against
scripts/e2020_rlcl_enable_threshold_blanking_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_e2020_rlcl_enable_threshold_blanking.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
