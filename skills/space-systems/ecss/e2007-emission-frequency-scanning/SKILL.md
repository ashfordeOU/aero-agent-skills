---
name: e2007-emission-frequency-scanning
description: "Verify that an emission measurement sweeps the complete declared frequency span required by ECSS-E-ST-20-07C clause 5.2.9.3. Use when a radiated or conducted emission run is planned or graded: merge the recorded receiver scan segments into their union, expose every sub-band the scan never visited, compute the covered fraction of the declared span, flag segments swept too fast for their resolution bandwidth to register a narrowband emission, report out-of-band excursions and redundant overlap, and decide whether the span was truly swept or the run must be repeated. Trigger: ecss, e-st-20-07c, emission-frequency-scanning, emission-span-coverage, receiver-scan-segment, emission-sweep-time-adequacy, uncovered-emission-sub-band, emission-resolution-bandwidth-dwell."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-emission-frequency-scanning, emission-span-coverage, receiver-scan-segment, emission-sweep-time-adequacy, uncovered-emission-sub-band, emission-resolution-bandwidth-dwell]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Emission Frequency Scanning (space-systems/ecss/e2007-emission-frequency-scanning)

Use when the task is the frequency-span scanning requirement of
ECSS-E-ST-20-07C clause 5.2.9.3 -- showing that an emission
measurement actually swept the whole declared span, so that a quiet
result means the band is quiet rather than that the receiver never
looked there.

## Domain quick reference

- The declared band is the contract. A run is graded against the span
  the test specification declared, not against the span the receiver
  happened to be configured for. A scan that stops short of the
  declared stop frequency has not met the clause, however clean the
  part it did cover looks.
- Real runs arrive as several segments, because the resolution
  bandwidth changes with frequency. Coverage is therefore a property
  of the union of the segments, not of any one of them. Merge first,
  then compare the union against the band; a per-segment check will
  pass a set of segments that together still leave a hole.
- Two segments that touch at a shared edge leave no hole. Two
  segments separated by even a narrow interval leave a sub-band the
  measurement never visited, and a narrowband emitter sitting in that
  interval is invisible to the run. Report the gap with its width so
  the reviewer can judge what could hide in it.
- Covering the span is necessary but not sufficient. A segment swept
  faster than its resolution cells can settle under-reads every
  narrowband emission in it. The sweep time a segment needs scales
  with the number of resolution bandwidths it crosses, so a wide
  segment on a narrow bandwidth needs a long sweep, and a segment
  narrower than a single cell still needs one full dwell.
- Reaching outside the declared band is not a defect. It costs time
  and it can pick up signals that are not being graded, so it is
  recorded as a limitation on the run, as is overlap between
  neighbouring segments -- redundant coverage, not missing coverage.
- Coverage is grouped as complete, partial or absent. Only complete
  coverage with every segment swept slowly enough supports a verdict;
  anything else sends the run back for a rescan of the affected
  sub-bands.

## Workflow

1. Validate the declared band: positive start, stop strictly above
   start. Reject a band that cannot be graded rather than grading it.
2. Validate the recorded segments: positive edges, stop above start,
   positive resolution bandwidth, positive sweep time. Accept them in
   any order and sort by start frequency.
3. Merge the segments into their union, treating touching edges as
   continuous within a named frequency tolerance.
4. Subtract the union from the declared band to expose every uncovered
   sub-band, and sum the clipped union to get the covered span and the
   covered fraction.
5. For each segment compute the sweep time it needed from its span and
   its resolution bandwidth, and compare against the time recorded.
6. Report out-of-band excursions and redundant overlaps as limitations.
7. Aggregate: uncovered sub-bands and under-swept segments are
   findings that force a rescan; everything else is a limitation on an
   otherwise swept span.

## Pitfalls

- Checking each segment against the band separately. Every segment can
  sit inside the band while the set of them still leaves a hole; only
  the union answers the clause.
- Treating a coverage fraction near one as complete. A fraction of
  0.999 still names a sub-band no instrument visited, and that is
  exactly where an unexpected carrier hides.
- Passing a run because the receiver reported the full span. The span
  it stepped across and the span it dwelt on are different quantities
  when the sweep time is short.
- Comparing float edges with a bare equality. Segment edges written by
  a controller can differ in the last bits, and a bare comparison
  turns a touching pair into a spurious gap.
- Counting overlap as a defect and rescanning for it. Overlap costs
  time; it never loses a sub-band.

## Behavior contract (gate 3)

The band and segment validation, union merge, uncovered sub-band
detection, coverage fraction and grouping, sweep-time adequacy,
excursion and overlap reporting and the aggregate verdict are
exercised by the gate 3 contract test:
scripts/test_e2007_emission_frequency_scanning.py against
scripts/e2007_emission_frequency_scanning_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2007_emission_frequency_scanning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
