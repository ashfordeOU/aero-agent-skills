---
name: e50-simultaneous-support-of-differing-source-rates
description: "Allocate downlink capacity across telemetry sources that generate at different rates, as ECSS-E-ST-50C clause 5.5.6 requires: total the offered load with transport overhead against the link capacity, apportion virtual-channel slots by largest-remainder so every source keeps a share of at least one slot, derive each source's service interval and end-to-end latency from that apportionment, size the on-board buffer the interval implies, and flag any source squeezed onto a common rate instead of its own. Use when planning a virtual-channel bandwidth split, sizing telemetry buffers, or diagnosing packet loss on a slow source. Trigger: ecss, e-st-50-communications-scope, simultaneous-differing-source-rates, virtual-channel-slot-apportionment, telemetry-service-interval, source-buffer-depth-sizing, downlink-capacity-overbooking, mixed-rate-telemetry-multiplexing."
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
    clause: 5.5.6
    items: [a]
    relation: implements
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.5.6
    items: [b]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications-scope, e50-simultaneous-support-of-differing-source-rates, mixed-rate-telemetry-multiplexing, virtual-channel-slot-apportionment, telemetry-service-interval, source-buffer-depth-sizing, downlink-capacity-overbooking, largest-remainder-slot-allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Simultaneous Support of Differing Source Rates (space-systems/ecss/e50-simultaneous-support-of-differing-source-rates)

Use when the task is the mixed-rate provision of ECSS-E-ST-50C clause
5.5.6 — showing that the telemetry system carries, at the same time, data
from sources that generate at different rates, each served at its own
rate rather than at a rate imposed on all of them.

## Domain quick reference

- Two separate things have to hold. Capacity first: the offered load of
  all sources together, grossed up by frame and coding overhead, has to
  fit the downlink. Then simultaneity, which is what the clause is
  about: each source has to be served at its own generation rate, so
  meeting the total while starving the slow or the fast source is not
  compliance.
- Slot apportionment is integer arithmetic on a finite cycle. A cycle of
  frames is divided among the sources in proportion to demand, but the
  shares are whole slots, so the rounding rule matters: largest
  remainder keeps the total exact and is reproducible, while independent
  rounding per source silently over- or under-books the cycle.
- A source apportioned zero slots is the failure this clause names. It
  is not a small under-service; the source is not carried at all, and it
  is exactly what happens to a low-demand housekeeping source when
  slots are apportioned by demand alone with no floor.
- Service interval, not bandwidth, sets latency. A source with enough
  average bandwidth can still overflow if its slots are bunched: the
  interval between two of its slots, plus its own generation period,
  bounds the age of the oldest datum when it finally leaves.
- Buffer depth follows from the interval. Between two services the
  source keeps generating, so the buffer has to hold a whole service
  interval of production rounded up to whole packets; sizing it to the
  average rate alone loses the burst that the interval creates.
- Differing rates are the point, so the spread is worth reporting. When
  the fastest and slowest demand differ by orders of magnitude, a single
  common service rate cannot suit both, and the apportionment is what
  proves it did not have to.

## Workflow

1. Validate each source: a name, a positive packet size in bits, a
   positive generation period, a positive maximum latency, and the
   priority the mission assigned it. Zero or negative entries are input
   errors.
2. Compute each source's demand as packet bits divided by generation
   period, and the offered load as the sum grossed up by the transport
   overhead factor.
3. Compare the offered load with the downlink capacity, absorbing
   floating-point representation error at the boundary with a named
   tolerance rather than by inflating the capacity.
4. Apportion the cycle's slots in proportion to demand by largest
   remainder, so the slots sum exactly to the cycle and ties resolve on
   the source name.
5. Report any source apportioned zero slots: it is carried at no rate at
   all, which is the condition the clause forbids. Report with it any
   source the apportionment would serve at a rate other than the one it
   generates at — the rate belongs to the source, and the downlink is
   not entitled to set it.
6. Derive each source's service interval from its slot count and the
   cycle duration, add its own generation period, and compare with its
   declared maximum latency.
7. Close the apportionment against what the clause asks of it: every
   source carried in the same cycle at its own demand, and each one
   inside the maximum latency it declared. Where those two compete, take
   slots from the lowest-priority source that still meets its own limit,
   re-derive the intervals, and report a conflict no reordering resolves
   rather than accepting a miss.
8. Size the buffer per source as the packets generated in one service
   interval, rounded up, and report it with the demand spread between
   the fastest and slowest source.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.5.6a | 7 |
| ECSS-E-ST-50C Rev.2 5.5.6b | 5 |

## Pitfalls

- Checking the capacity total and stopping. The total fitting says
  nothing about whether the slow source ever gets a slot; both halves of
  the clause need their own check.
- Apportioning by independent rounding. Rounding each share to the
  nearest slot makes the slots sum to something other than the cycle,
  and the discrepancy shows up as a silently dropped or idle frame.
- Sizing buffers from average demand. Between services a source produces
  a whole service interval of data; a buffer sized on the average rate
  overflows on the first long gap between its slots.
- Reading bandwidth share as latency. A source can hold a large share of
  the capacity and still miss its latency if its slots are adjacent in
  the cycle rather than spread through it.
- Forcing a common packet rate to simplify the multiplexer. That is the
  design this clause exists to prevent: it either wastes capacity on the
  slow sources or truncates the fast ones.

## Behavior contract (gate 3)

The source validation, demand and offered-load computation, capacity
comparison, largest-remainder slot apportionment, service interval,
latency screening and buffer sizing are exercised by the gate 3 contract
test: scripts/test_e50_simultaneous_support_of_differing_source_rates.py
against
scripts/e50_simultaneous_support_of_differing_source_rates_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e50_simultaneous_support_of_differing_source_rates.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
