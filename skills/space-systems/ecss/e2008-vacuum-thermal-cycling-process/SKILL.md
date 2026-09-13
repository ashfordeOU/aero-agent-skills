---
name: e2008-vacuum-thermal-cycling-process
description: "Identify which components of a photovoltaic article are watched for electrical continuity throughout a vacuum thermal-cycling run, per ECSS-E-ST-20-08C clause 5.5.3.11.2: separate the declared items that carry a current path from the ones no continuity monitor can watch, give each of the first group its own monitor channel and compare the demand with the channels available, size the sampling interval so the shortest credible discontinuity is still resolved, then account for every second of the run the monitor was not watching. Use when planning or auditing the in-situ monitoring of a vacuum cycling campaign. Trigger: ecss, e-st-20-08c, clause-5-5-3-11-2, vacuum-cycling-continuity-monitoring, in-situ-discontinuity-detection, monitor-channel-assignment, continuity-sampling-interval, unmonitored-run-time, cycled-article-current-path."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-vacuum-thermal-cycling-process, vacuum-cycling-continuity-monitoring, in-situ-discontinuity-detection, monitor-channel-assignment, continuity-sampling-interval, unmonitored-run-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Vacuum Cycling Continuity Monitoring (space-systems/ecss/e2008-vacuum-thermal-cycling-process)

Use when the task is the monitoring step of the vacuum thermal-cycling run of
ECSS-E-ST-20-08C clause 5.5.3.11.2 — naming the parts of the article that are
watched for continuity while the run proceeds, wiring each of them to a
channel, and showing that the watch really did last the whole run.

## Domain quick reference

- A discontinuity during cycling is transient. An interconnect that opens at
  the cold extreme and closes again on the way back leaves no trace in a
  before-and-after resistance measurement, so the whole point of monitoring is
  that it happens while the article is still cold.
- The inventory splits in two, and both halves matter. Items carrying a
  current path — strings, interconnects, bus-bar joints, bypass diodes,
  harnesses, mated connectors, bonding straps — each owe a channel. Items with
  no current path are cycled and inspected but a continuity monitor says
  nothing about them; grouping them explicitly is what stops a plan from
  reporting coverage it never had.
- One channel watches one item. A channel shared between two items reports an
  event without saying which of them produced it, which is exactly the
  information the run was instrumented to get, so a doubly claimed channel is
  an input error rather than a finding.
- Sampling sets the shortest event the monitor can see. Resolving a
  discontinuity needs more than one sample inside it, so the interval follows
  from the shortest credible event divided by the samples demanded of it. A
  slower interval does not degrade the measurement gracefully; it simply misses
  the class of event the monitoring was for.
- "Throughout" is an accounting question. A monitor started after the chamber
  did, stopped before the last ramp finished, or interrupted for a data
  download leaves cycles unwatched, and those seconds are the ones a
  discontinuity hides in. Overlapping gap records double-count unless they are
  merged, and a gap logged outside the run window belongs to neither.

## Workflow

1. Group the declared items by whether a continuity monitor can watch them at
   all, rejecting an unrecognised item rather than dropping it, and report both
   groups.
2. Assign one channel per conducting item. Refuse a channel two items claim,
   name every conducting item that has no channel, and flag a channel spent on
   an item with no current path.
3. Compare the number of channels the article needs with the number the monitor
   has, and report the shortfall rather than silently monitoring a subset.
4. Size the sampling interval from the shortest discontinuity to be caught and
   the samples demanded inside it, and report the shortest event the planned
   interval actually resolves.
5. Account for the monitoring window against the run window: a late start, an
   early stop and every logged gap, clipped to the run and merged so an overlap
   is counted once. Report unmonitored time, longest gap and gap count.
6. Aggregate the channel, sampling and window findings into one plan verdict.
   A value landing exactly on an allowance complies; the comparison tolerance
   absorbs representation error and no allowance moves.

## Pitfalls

- Monitoring the strings and nothing else. The joints, the mated connectors
  and the bonding straps are the parts a cycle works hardest, and leaving them
  off the channel list makes the most likely finding unobservable.
- Counting a bondline or a coverglass as monitored because it is on the
  article. Neither carries a current path; a continuity channel spent there
  buys nothing and hides a channel shortfall elsewhere.
- Sampling once per second because the chamber logs once per second. The
  chamber is slow and the discontinuity is not; the sampling interval belongs
  to the event being caught, not to the thermal data.
- Reporting coverage as a count of channels. Coverage is time as well as
  items: a full channel list that stopped recording for the last four cycles
  watched none of them.
- Summing overlapping gap records. Two overlapping interruptions logged by
  two subsystems are one gap, and adding them invents unmonitored time that
  never happened while hiding the real longest gap.
- Treating an unmonitored total exactly on its allowance as a breach.
  Equality at an allowance is a representation question, handled inside the
  comparison rather than by relaxing the allowance.

## Behavior contract (gate 3)

The scope grouping, channel assignment, channel-count comparison, sampling
sizing, gap clipping and merging, monitoring-window accounting and the
aggregated plan verdict are exercised by the gate 3 contract test:
scripts/test_e2008_vacuum_thermal_cycling_process.py against
scripts/e2008_vacuum_thermal_cycling_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_vacuum_thermal_cycling_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
