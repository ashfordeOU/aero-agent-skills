---
name: e50-isochronous-services
description: "Evaluate whether a delivery stream meets the isochronous service obligation of ECSS-E-ST-50C clause 5.6.14.4, where a service promised at a fixed cadence has to arrive on that cadence and not merely at the right average rate. Compute every delivery's deviation from the ideal grid, the peak-to-peak jitter, the playout buffer that would re-time the stream, and the smallest tolerance the run would have passed under, then separate a rate error that walks the stream off the grid from bounded jitter that stays put. Use when accepting or reviewing an isochronous downlink, playback or synchronous bus service. Trigger: ecss, e-st-50-communications, isochronous-delivery-jitter, isochronous-grid-deviation, isochronous-playout-buffer-sizing, isochronous-rate-drift, isochronous-cadence-acceptance."
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
    clause: 5.6.14.4
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-isochronous-services, isochronous-delivery-jitter, isochronous-grid-deviation, isochronous-playout-buffer-sizing, isochronous-rate-drift, isochronous-cadence-acceptance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Isochronous Services (space-systems/ecss/e50-isochronous-services)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.6.14.4 —
that where an isochronous service is provided, its deliveries arrive on a fixed
cadence — and the question is whether an observed run actually did.

## Domain quick reference

- The average rate is the wrong instrument and it is the one usually
  reached for. A stream that slips a fraction on every interval keeps a
  flawless average while walking steadily off the grid, and a stream
  that alternates early and late keeps a flawless average while never
  once being on time.
- The grid is the measurement, not the intervals. Deviation is where a
  delivery sits against the slot it was due in; an interval-by-interval
  view cannot see accumulation, because each individual step looks
  nearly right the whole way down.
- Jitter and rate error are different failures with different remedies.
  Bounded jitter is absorbed by a playout buffer of fixed depth; a rate
  error is not absorbed by any buffer, because the deficit keeps growing
  for as long as the service runs.
- Peak-to-peak jitter is already the buffer size. The spread between the
  earliest and the latest delivery is exactly the depth needed to hand
  the consumer a stream that looks on time, which makes the assessment
  and the sizing the same calculation.
- The anchor has to be stated. With no declared epoch the only honest
  grid is the one starting at the first delivery, and a report that
  hides which anchor it used can be argued either way afterwards.
- A tolerance a run exactly meets is a run that conforms. Two
  arithmetically identical streams straddle a bare equality on different
  hosts, so the bound is compared with a relative tolerance.

## Workflow

1. Name the directions that carry speech or moving pictures whose worth
   expires with delay, since the cadence obligation attaches to each of
   them, and state the cadence of each as three numbers: the nominal
   period, the jitter tolerance, and the epoch the grid is anchored at —
   or record that the first delivery is the anchor because none was
   declared.
2. Reject a run that does not strictly increase before measuring
   anything. Out-of-order arrival times are a different defect and the
   cadence figures computed over them mean nothing.
3. Build the ideal grid and take each delivery's deviation from its
   slot, keeping the sign so early and late stay distinguishable.
4. Take the worst absolute deviation against the tolerance, and the
   peak-to-peak spread as the playout buffer the stream would need.
5. Measure the interval the run actually achieved and subtract the
   nominal period. Compare that rate error against the budget the run
   length can absorb — tolerance divided by the number of steps.
6. Grade each direction on its own run: within tolerance conforms;
   outside it with a rate error beyond that budget is drift; outside it
   with the mean rate intact is jitter. The link carries the service only
   where both directions of the pair conform, so a verdict taken from the
   downlink alone covers half of it.
7. Report both remedies for a jitter failure, the achieved rate for a
   drift failure, and check a proposed tolerance against the same model
   before offering it.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.14.4a | 6 |

## Pitfalls

- Accepting a service on its mean delivery rate. Both of the failures
  that matter here keep a correct mean, which is why the mean is the one
  statistic that cannot detect either of them.
- Sizing a playout buffer against a run that is drifting. The buffer
  works for the length of the sample and then quietly runs dry or
  overflows, because the deficit was never bounded.
- Measuring interval to interval instead of against the grid. A steady
  slip of a fraction of a per cent per delivery reads as clean on every
  individual interval and as a whole slot lost by the end of a pass.
- Dropping the sign from the deviations. Early and late deliveries fail
  differently — one needs buffer depth ahead of the consumer, the other
  needs it behind — and an absolute value erases which.
- Leaving the grid anchor unstated. Anchoring at the first delivery and
  anchoring at a declared epoch give different deviations for the same
  stream, and the difference is a constant nobody can reconstruct later.
- Deciding conformance with a bare inequality at the tolerance. A run
  built to sit exactly on the permitted jitter then passes or fails by
  the rounding of the build host.

## Behavior contract (gate 3)

Period, tolerance and delivery-sequence validation, grid construction, signed
deviations against a default and a declared epoch, peak-to-peak jitter, the
measured period and its rate error, the rate-error budget for the run length,
conformance at the exact tolerance bound, and the tolerance and buffer inverses
checked against the same model are exercised by the gate 3 contract test:
scripts/test_e50_isochronous_services.py against
scripts/e50_isochronous_services_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_isochronous_services.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
