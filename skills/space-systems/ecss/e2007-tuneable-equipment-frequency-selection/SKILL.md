---
name: e2007-tuneable-equipment-frequency-selection
description: "Derive the tuning settings at which a tuneable or channelized unit must be measured, and assess a proposed plan against ECSS-E-ST-20-07C clause 5.2.7.2: build an evenly spread set of settings that reaches both band edges, resolve real channel centres for a channelized range, then grade a proposed plan on point count, reach to each band edge and the widest untested gap, and hold the run while any band is under-covered. Use when equipment tunes across a band, hops channels or offers selectable carriers. Trigger: ecss, e-st-20-electrical-scope, tuneable-equipment-frequency-selection, tuning-band-coverage, channel-centre-selection, band-edge-frequency-check, emission-frequency-plan-gate."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-tuneable-equipment-frequency-selection, tuning-band-coverage, channel-centre-selection, band-edge-frequency-check, emission-frequency-plan-gate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Test Setup — Tuneable-Equipment Frequency Selection (space-systems/ecss/e2007-tuneable-equipment-frequency-selection)

Use when the task is the ECSS-E-ST-20-07C clause 5.2.7.2 obligation that a
tuneable or channelized unit be measured at several settings spread across
each tuning band -- deriving the default settings, grading a plan somebody
else proposed, and holding the run while a band is under-covered.

## Domain quick reference

- A tuneable unit is a different unit at every setting. Filter skirts,
  synthesizer spur families and the amplifier match all move with the tuning,
  so one sweep at one convenient setting characterizes that setting and
  nothing else.
- The requirement is spread, not count. Three settings crowded near the
  middle of a band meet an arithmetic minimum and leave both edges -- where
  the filters roll off and the match degrades fastest -- entirely unmeasured.
- The default plan for a continuously tuneable band is an even spread that
  includes both edges: the lowest setting, the highest, and interior points
  at equal spacing between them.
- A channelized range is different in kind. Its settings are real channel
  centres spread over the channel index range, because a frequency between
  two channels is not a setting the unit can be commanded to take, and a plan
  that names one cannot be executed.
- A plan is graded on three independent things, and a plan can fail any one
  while passing the others: enough points in the band, a lowest point close
  enough to the bottom edge and a highest point close enough to the top, and
  no gap between consecutive points wider than the allowed fraction of the
  band span.
- Edge reach is measured as a fraction of the band span, not in hertz, so the
  same rule applies to a narrow channel range and a multi-octave tuner.
- A frequency outside the band it is meant to cover is a transcription error
  rather than a weak plan, and it is rejected instead of being scored.

## Workflow

1. Validate each band: a non-empty name, a positive lower edge, an upper edge
   above it, and -- when a channel plan is declared -- an integer channel
   count and a spacing whose top channel still falls inside the band.
2. For a band with no proposed plan, raise a finding and derive the default
   settings instead: channel centres when the range is channelized, an even
   spread otherwise.
3. Convert each proposed frequency to a normalized position in its band,
   rejecting any frequency that falls outside.
4. Grade the point count against the minimum for the band.
5. Grade the reach to each edge: the lowest position against the edge
   tolerance, the highest against one minus that tolerance.
6. Compute the widest gap between consecutive settings with both band edges
   treated as boundaries, and compare it with the allowed gap fraction.
7. Attach a recommended default plan to every band that failed, aggregate the
   findings and emit the gate token. Only an empty finding list releases the
   measurement.

## Pitfalls

- Measuring at the band centre alone because it is the nominal operating
  point. The edges are where the tuned circuits are furthest from nominal.
- Meeting the point count with clustered settings. Count and spread are
  separate requirements, and the gap check is what catches the cluster.
- Proposing an arithmetically even spread across a channelized range. The
  even points land between channels, and the unit cannot be commanded there.
- Applying an edge tolerance in hertz. A fixed hertz margin is generous on a
  wide tuner and impossible on a narrow channel range; the tolerance is a
  fraction of the span.
- Silently skipping a band that has no plan entry. A missing band reads as a
  covered band unless the absence itself is raised as a finding.
- Letting a normalized gap that lands a few units in the last place outside
  the allowance read as a non-conformance. The logic absorbs representation
  error with a named tolerance far below any coverage value; the allowance
  itself is never widened.

## Behavior contract (gate 3)

The band validation, even-spread and channel-centre selection, normalized
position, gap, edge-reach and point-count grading, recommended-plan
derivation and readiness-gate logic is exercised by the gate 3 contract test:
`scripts/test_e2007_tuneable_equipment_frequency_selection.py` against
`scripts/e2007_tuneable_equipment_frequency_selection_logic.py` (stdlib
unittest, offline).
Run: python3 scripts/test_e2007_tuneable_equipment_frequency_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
