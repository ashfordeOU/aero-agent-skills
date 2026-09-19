---
name: e50-mixed-housekeeping-and-payload-data
description: "Verify that housekeeping telemetry keeps its cadence while it shares a downlink with bulk payload data, under ECSS-E-ST-50C clause 5.6.10: housekeeping is small and time critical, payload is large and patient, and the multiplexing has to protect the first without starving the second. Compute the housekeeping reservation, the delay a payload transfer unit in progress imposes before the next report can go, the payload rate and contact volume actually left, and the unit cap or link rate that restores both. Use when sizing a shared housekeeping and payload downlink. Trigger: ecss, e-st-50-communications, housekeeping-payload-multiplexing, housekeeping-cadence-protection, payload-transfer-unit-blocking, housekeeping-link-reservation, shared-downlink-volume-split."
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
  tags: [ecss, e-st-50-communications, e50-mixed-housekeeping-and-payload-data, housekeeping-payload-multiplexing, housekeeping-cadence-protection, payload-transfer-unit-blocking, housekeeping-link-reservation, shared-downlink-volume-split]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Mixed Housekeeping and Payload Data (space-systems/ecss/e50-mixed-housekeeping-and-payload-data)

Use when one downlink carries both the spacecraft's own health reports and the
payload's bulk output, per ECSS-E-ST-50C clause 5.6.10 — whether each keeps
its service when the other is busy.

## Domain quick reference

- The two services are opposites and that is the whole difficulty.
  Housekeeping is a few kilobits on a fixed cadence whose value
  collapses when it is late; payload is megabits whose only measure is
  volume delivered. One link, two success criteria.
- The housekeeping reservation is tiny and is not the problem. Frame
  size over cadence is usually a fraction of a percent of the link, so
  a capacity-only comparison says there is nothing to discuss and
  misses the actual failure.
- The actual failure is latency, and it comes from the payload unit
  already on the wire. On a link that cannot interrupt a transfer, the
  next housekeeping report waits for the whole unit and then for its
  own serialisation, and both terms belong in the number.
- Two remedies, both arithmetic: cap the payload transfer unit so it
  serialises inside the housekeeping latency budget, or make the link
  preemptible so the wait is only the report itself. State which one
  the design assumes, because the answers differ by the whole unit.
- There is a third case worth naming: a housekeeping frame that cannot
  serialise inside its own latency budget. No payload cap recovers
  that, and saying so stops a segmentation exercise that cannot work.
- Payload success is volume over a contact, not a rate on a datasheet.
  Multiply the remaining rate by the contact length and compare against
  what the mission has to move.

## Workflow

1. State housekeeping as a frame size and a cadence, and payload as an
   offered rate and a transfer unit size. Four numbers, none optional.
2. Compute the housekeeping rate and its share of the link, then the
   payload capacity as the remainder, floored at zero rather than
   reported negative.
3. Compute the worst-case housekeeping latency: the payload unit it
   waits behind, plus its own time on the wire.
4. Declare whether the link can interrupt a payload transfer unit. It
   changes the latency by the whole unit and is an architecture fact,
   not a tuning parameter.
5. Compare the latency with its budget and the payload offer with the
   remaining capacity, both with a relative tolerance, so a design
   sized exactly to a bound comes out compliant.
6. Where the cadence misses, report the largest payload unit the budget
   allows — or say that the housekeeping frame alone overruns it, in
   which case segmentation cannot help.
7. Where the payload misses, report the link rate that carries both,
   and the volume the contact delivers at the rate that exists.

## Pitfalls

- Judging the mix on capacity. Housekeeping costs almost no bandwidth
  and still misses its deadline behind one long payload unit.
- Forgetting the report's own serialisation time. Being scheduled next
  is not being sent, and on a slow link the frame itself is the larger
  of the two terms.
- Assuming the scheduler can interrupt a payload transfer. Where it
  cannot, no priority setting removes the blocking interval.
- Protecting the cadence by shrinking the payload unit until the link
  is all overhead. The remaining throughput is the other half of the
  clause and has to be reported alongside.
- Deciding the latency verdict with a bare inequality at the budget.
  Two arithmetically identical designs can straddle the bound on
  different machines, so the verdict depends on the build host.

## Behavior contract (gate 3)

Frame, cadence, rate and unit validation, the housekeeping reservation
and share, the preemptible and non-preemptible latency, the three-way
verdict with a tolerance at the latency and capacity bounds, the
unrecoverable frame-alone case, the contact volume and the two sizing
inverses checked against the same model are exercised by the gate 3
contract test:
scripts/test_e50_mixed_housekeeping_and_payload_data.py against
scripts/e50_mixed_housekeeping_and_payload_data_logic.py
(stdlib unittest, offline).
Run:
python3 scripts/test_e50_mixed_housekeeping_and_payload_data.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
