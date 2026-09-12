---
name: e20-power-demand-versus-availability-analysis
description: "Use when compute the available electrical power against the demand for every mission phase under ECSS-E-ST-20C clause 5.2.2.2: build each phase load list from peak power and duty cycle, separate the loads that fire together from the time-averaged ones, degrade the generated power to the phase epoch, compare availability against both the averaged and the coincident-peak demand, size the stored energy that covers any deficit, and grade the discharge depth and the phase margin against their limits. Flags an energy balance that does not close, a coincident-peak shortfall, an over-discharged store, a thin phase margin and an uncategorized load. Trigger: ecss, e-st-20-electrical-scope, power-demand-versus-availability, coincident-peak-load, mission-phase-power-balance, eclipse-energy-balance, depth-of-discharge-limit, array-degradation-epoch."
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
  tags: [ecss, e-st-20-electrical-scope, e20-power-demand-versus-availability-analysis, power-demand-versus-availability, coincident-peak-load, mission-phase-power-balance, eclipse-energy-balance, depth-of-discharge-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Power Demand versus Availability (space-systems/ecss/e20-power-demand-versus-availability-analysis)

Use when the task is the phase-by-phase power balance of
ECSS-E-ST-20C clause 5.2.2.2 -- comparing what the source can deliver
at a given point in the mission against what the loads draw there,
including the peaks, and proving the store closes whatever gap
remains.

## Domain quick reference

- Clause 5.2.2.2 makes two demands that a single orbit-average number
  cannot satisfy. The comparison is per mission phase (launch, LEOP,
  transfer, nominal operations, eclipse, safe mode, end of life),
  because a subsystem that closes comfortably on the orbit average can
  still fail during a stowed-array ascent or a safe-mode recovery. And
  the comparison includes peak loads, not just averaged consumption.
- Demand therefore has two figures. The averaged demand is the sum of
  each load's peak power times its duty cycle. The coincident-peak
  demand takes the full peak of every load that fires together with
  the others, plus the averaged draw of the rest: it is what the bus
  actually sees in the worst instant of the phase. A transmitter at
  120 W on a 0.25 duty contributes 30 W to the average and 120 W to
  the coincident peak.
- Availability also has two figures. Generated power is the
  beginning-of-life source output decayed by the annual degradation
  over the elapsed years at that phase, so end-of-life availability is
  the number that governs. The instantaneous supply capability is that
  generated power plus what the store can discharge at once, and it is
  the figure the coincident peak is graded against -- a peak the array
  alone cannot serve is fine if the battery can source the difference.
- A deficit is not automatically a defect. In eclipse it is the design
  intent: the store carries the load, and the analysis question is
  whether it can. The deficit becomes a finding only when the required
  energy exceeds the whole capacity (the balance does not close) or
  when it stays within capacity but past the depth-of-discharge limit
  the cell life is sized against.
- In a phase with no generation at all, a power-ratio margin is
  meaningless -- the denominator is zero. The reserve to grade there
  is the fraction of the allowed discharge depth left unused, which is
  the same question asked in the currency that phase actually spends.

## Workflow

1. Build the phase load list: an identifier, a category (continuous,
   duty-cycled, coincident-peak), a peak power and a duty cycle.
   Reject an uncategorized load, a duplicated identifier and a duty
   cycle outside 0 to 1 before the phase is summed.
2. Compute both demand figures for the phase: averaged demand across
   every load, and coincident-peak demand taking the full peak of the
   coincident-peak loads plus the averaged draw of the others.
3. Compute the generated power at that phase's epoch: beginning-of-life
   power decayed by the annual degradation over the elapsed years.
4. Compare the coincident-peak demand against the instantaneous
   capability (generated power plus the store's discharge capability);
   a shortfall is a finding.
5. Take the deficit between averaged demand and generated power, size
   the energy the store must supply over the phase duration, and
   convert it to a discharge depth against the store's capacity. Raise
   a not-closed finding when the depth exceeds the full capacity, or a
   discharge-depth finding when it exceeds the allowed limit.
6. Grade the reserve. With generation present, use the unspent
   fraction of the available power; with no generation, use the unused
   fraction of the allowed discharge depth. Compare it against the
   margin the phase requires.
7. Repeat for every phase and aggregate. The mission is power positive
   only when no phase carries a finding.

## Pitfalls

- Grading the mission on an orbit-averaged number. Clause 5.2.2.2 is
  per phase; averaging across phases lets a healthy nominal-operations
  surplus pay for a safe-mode deficit that the spacecraft cannot
  actually move energy across.
- Summing duty-cycled averages and calling it the peak. A bus sized on
  averaged demand trips on the first instant the peaking loads fire
  together, which is exactly the case the clause calls out.
- Using beginning-of-life source output for every phase. Degradation
  is monotonic and the end-of-life phase is normally the sizing case;
  quoting the BOL figure moves the analysis to the easiest epoch
  instead of the governing one.
- Reading any eclipse deficit as a failure, or any covered deficit as
  a pass. The finding is about the store: not closing at all and
  closing past the depth-of-discharge limit are different severities,
  and discharging within the limit is nominal.
- Computing a power margin in a phase with no generation. Dividing by
  a zero source either raises or silently produces a meaningless
  number; the reserve there lives in the unused discharge depth.
- Treating the store's energy capacity and its discharge capability as
  one quantity. Capacity settles whether the energy balance closes
  over the phase; instantaneous discharge capability settles whether
  the coincident peak is served at all.

## Behavior contract (gate 3)

The load categorization, dual demand figures, epoch degradation,
peak-capability comparison, stored-energy and discharge-depth
accounting and per-phase margin logic is exercised by the gate 3
contract test:
scripts/test_e20_power_demand_versus_availability_analysis.py against
scripts/e20_power_demand_versus_availability_analysis_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_power_demand_versus_availability_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
