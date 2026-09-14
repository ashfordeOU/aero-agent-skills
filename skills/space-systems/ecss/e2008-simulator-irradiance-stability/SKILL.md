---
name: e2008-simulator-irradiance-stability
description: "Evaluate how steadily a solar simulator holds irradiance across each data acquisition interval under ECSS-E-ST-20-08C clause 10.1.3: validate the run and its declared windows, refuse a window the monitor never watched densely enough to describe, take the temporal instability inside every window separately from the extreme readings, hold each one under the declared limit, and report the slow drift between window means as the separate quantity it is. Use when acquisition-interval steadiness has to be shown before a current-voltage measurement is trusted, or an as-run monitor trace has to be judged. Trigger: ecss, e-st-20-08c-clause-10-1-3, solar-simulator-irradiance-stability, acquisition-interval-instability, temporal-instability-percent, simulator-monitor-sampling-cadence, simulator-run-drift-between-intervals."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-simulator-irradiance-stability, solar-simulator-irradiance-stability, acquisition-interval-instability, temporal-instability-percent, simulator-monitor-sampling-cadence, simulator-run-drift-between-intervals]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Simulator Irradiance Stability (space-systems/ecss/e2008-simulator-irradiance-stability)

Use when the task is clause 10.1.3 of ECSS-E-ST-20-08C -- how still the
simulator's irradiance holds, judged over the window during which the
data are actually acquired rather than over the run that contains it.

## Domain quick reference

- The window is the unit. A run of nine sweeps carries nine acquisition
  intervals and every one of them has to hold the limit on its own, so a
  run-wide figure that averages one bad window against eight good ones
  has described a simulator that never existed.
- The converse costs just as much. A lamp fading slowly across an hour
  holds every short window comfortably, because the movement never
  happens inside one, and a per-interval pass says nothing about whether
  the first sweep and the last are comparable. Both figures are taken;
  only the per-interval one sets the verdict.
- Monitoring is part of the requirement, not preparation for it.
  Steadiness is only demonstrated to the resolution the monitor sampled
  at, so a window holding three readings has not been shown steady -- it
  has been shown unwatched.
- Sample count and unwatched stretch fail independently. A window can
  carry twenty readings crowded into its first second and leave the rest
  unseen, so the longest gap is sized as well as the count, and the
  stretches before the first reading and after the last one both count.
- The figure is extreme to extreme, as for spatial uniformity: the
  spread between the brightest and dimmest reading inside the window,
  normalised by their sum. A one-sample dip is exactly the event the
  acquisition records as a bad point, and a mean-based figure buries it.
- The window that moved most is worth naming with its clock times. A
  campaign can usually find what happened at that moment -- a lamp
  restrike, a shutter, a supply step -- and cannot find it from a per
  cent alone.
- A window is judged against the whole interval it declares, endpoints
  included, not against whatever the monitor happened to record nearby.

## Workflow

1. Validate the stability policy first: the per-interval limit, the
   minimum readings per window, the largest unwatched share of a window,
   the run drift allowance and the marginal band. A limit at or above a
   hundred per cent is refused rather than used.
2. Read the declared acquisition windows. An absent or empty set closes
   the assessment on intervals not declared -- without them the run-wide
   spread is what gets quoted, and that is the wrong quantity.
3. Read the monitor trace: non-negative timestamps, positive readings,
   no two readings sharing a timestamp. Sort it into time order rather
   than trusting the order it arrived in.
4. For each window take the readings inside it, endpoints included, then
   judge the watching before the irradiance: count against the floor and
   longest unwatched stretch against the allowance, the leading and
   trailing stretches included. Name every thin window, not the first.
5. Take the temporal instability inside each window separately and hold
   each against the limit. Report every window that moved too far, with
   its clock times.
6. Take the drift between the window means as a separate figure and
   raise it as an advisory: it does not move the verdict, and a run that
   passes every window while drifting has produced sweeps that are not
   comparable with each other.
7. Close on one verdict: intervals not declared, interval sampling
   insufficient, instability out of limit, or instability within limit
   -- with a marginal advisory when the worst window barely cleared.

## Pitfalls

- Quoting one run-wide stability number. It is the figure a monitor log
  hands over most easily and it is not the figure this clause asks for.
- Reading a per-interval pass as a stable run. Drift between windows is
  a different failure with different consequences, and it is reported
  separately for that reason.
- Treating a thinly watched window as a steady one. An absent excursion
  and an unobserved excursion look identical in the data and are not the
  same claim.
- Counting readings without sizing the gap between them. A burst of
  samples at the start of a window satisfies any count and leaves the
  acquisition unwatched.
- Forgetting the leading and trailing stretches. A monitor that woke up
  after the window opened left that stretch unseen exactly as a stall in
  the middle would.
- Comparing a derived per cent against its limit by bare arithmetic.
  Both sides are floats that can land a unit in the last place either
  side of the bound, so the comparison absorbs that while the limit
  itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, monitor trace validation with ordering and
timestamp collision rejection, acquisition window validation, the
endpoint-inclusive window membership, the per-window sample count and
largest unwatched stretch, the extreme-to-extreme instability figure,
the window means, the run drift between them, the worst window, the
advisories and the stability verdict are exercised by the gate 3
contract test:
scripts/test_e2008_simulator_irradiance_stability.py against
scripts/e2008_simulator_irradiance_stability_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_simulator_irradiance_stability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
