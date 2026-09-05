---
name: ground-station-pass-planning
description: "Use when you must build the daily ground station contact schedule of a low-earth satellite: propagate the sub-satellite point over the planning horizon, compute the elevation of the satellite above each station, detect the contiguous passes above the station elevation mask, aggregate the daily contact window schedule with its downlink gap analysis, and merge the contacts of several ground stations into one plan. Produces the per-pass start, end, duration and maximum elevation, the daily contact totals, the gap list, the maximum downlink gap, and the merged multi-station contact plan that gate mission data collection and downlink assessment. Trigger: ground station pass planning, contact window schedule, pass detection, elevation mask, downlink gap analysis, multi-station contact plan, daily contact schedule, maximum downlink gap."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: mission-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: mission-design
  tags: [ground-station-pass-planning, contact-window-schedule, downlink-gap-analysis, pass-detection, multi-station-contact-plan]
  version: 0.1.0
  author: AeroSkills
---

# Ground Station Pass Planning (space-systems/mission-design/ground-station-pass-planning)

Use when you must build the daily ground station contact schedule of a
low-Earth satellite from its orbit elements and the station masks. This
leaf propagates the circular two-body sub-satellite point over the
planning horizon, computes the elevation of the satellite above each
ground station, detects the contiguous passes above the station
elevation mask, aggregates the daily contact window schedule with its
downlink gaps, and merges the contacts of several ground stations into
one plan, in pure Python stdlib. It sits between the single-pass
visibility geometry leaf (space-systems/orbit-mechanics/satellite-
coverage), the frame-level data bookkeeping leaf
(space-systems/subsystems/command-data-handling) and the RF link sizing
leaf (space-systems/subsystems/communication-link-budget): this leaf
owns the multi-pass contact schedule and the outage layer of a day, and
it consumes the orbit state from the ground-track propagation leaves.
Does NOT do: the single-pass visibility geometry and pass-duration
estimates (satellite-coverage); downlink data budgeting and frame
accounting (command-data-handling); RF link sizing (communication-link-
budget); physical orbit state propagation under Earth oblateness and
atmospheric braking effects (kepler-orbit-propagation and orbital-
perturbations own the physical propagation; this leaf takes the orbit
elements as inputs and uses a simple circular two-body ground track).

## Domain quick reference

- Fixed-step planner defaults (module constants): spherical Earth
  radius RE_KM = 6371 km, gravitational parameter MU = 398600.4418
  km^3/s^2, Earth rotation rate OMEGA_E = 7.2921159e-5 rad/s, planner
  step STEP_S = 30 s, downlink gap threshold GAP_THRESHOLD_S = 600 s.
- Orbital period of the circular orbit at altitude h: T = 2 pi
  sqrt(a^3 / mu) with a = RE_KM + h. At 550 km, T = 5730.13 s (95.5
  min).
- Sub-satellite ground track: the circular-orbit inertial position at
  the argument of latitude u(t) = u0 + n t (n the mean motion) is
  rotated from the RAAN and inclination frame, then by the Earth
  rotation greenwich_0 + OMEGA_E t; longitude is wrapped to [-180,
  180]. No oblateness terms: the track is the simple two-body
  footprint. Each orbit the Earth rotates under the track, so the
  footprint drifts west by about 23.9 deg per 95.5 min orbit at 550
  km, which sets the pass cadence over a fixed station.
- Central angle lam between the station and the sub-satellite point:
  cos(lam) = sin(phi_s) sin(phi) + cos(phi_s) cos(phi) cos(delta_lon).
- Elevation of the satellite above the station: elevation =
  atan2(cos(lam) - RE_KM / r, sin(lam)) in degrees with r = RE_KM +
  altitude. The station zenith (lam = 0) reads 90 deg; the horizon is
  the central angle where cos(lam) = RE_KM / r, 22.9961 deg at 550 km.
  A 10 deg elevation mask maps to the 14.9676 deg central angle at 550
  km, the satellite-coverage access convention used in the inverse
  identity checks.
- Pass detection: sample the elevation every 30 s over the horizon and
  accumulate contiguous samples at or above the mask into passes; pass
  duration = end_s - start_s + STEP_S for the inclusive sample run.
- Daily contact schedule: bundle the detected passes with the total
  contact seconds and list the inter-pass downlink gaps of at least
  GAP_THRESHOLD_S (600 s); a gap runs from the previous pass end plus
  one step to the next pass start.
- Maximum downlink gap: the longest interval with no contact, counting
  the horizon boundaries before the first pass and after the last pass
  (horizon minus last pass end minus one step); a satellite with no
  passes returns the whole horizon.
- Multi-station merge: run the pass detection for every station, sort
  all contacts by start, and merge any contact whose start is within
  STEP_S of the previous contact end; each merged contact keeps the
  station index of the station that opened it and the highest maximum
  elevation of the merged passes.

## Workflow

1. Fix the orbit state and the planning horizon: the orbital altitude,
   inclination, RAAN, initial argument of latitude, Greenwich angle and
   horizon_h, with the module constants RE_KM, MU, OMEGA_E, STEP_S and
   GAP_THRESHOLD_S.
2. Ground-track propagation traverse: compute the orbital period with
   orbital_period_s, then step the sub-satellite point over the horizon
   with subsatellite_point (the circular two-body ground track rotated
   by the Earth rotation).
3. Elevation traverse: compute the elevation of the satellite above the
   station from the central angle with elevation_angle (90 deg at the
   zenith, 0 at the horizon central angle).
4. Pass-detection traverse: detect the contiguous passes above the
   station elevation mask with detect_passes over the 30 s planner step
   and read the per-pass start, end, duration and maximum elevation.
5. Downlink-gap-analysis traverse: aggregate the daily contact schedule
   with daily_contact_schedule (pass count, total contact seconds, gap
   list filtered by the gap threshold) and size the longest outage with
   max_downlink_gap, horizon boundaries included.
6. Multi-station-contact-plan traverse: merge the contacts of several
   ground stations into one plan with ground_station_contact_plan and
   read the merged contact list, the total contact seconds and the
   maximum downlink gap of the plan.
7. Guard traverse: confirm the deterministic checks, the coverage
   inverse identities and the ValueError rejections with the contract
   test scripts/test_ground_station_pass_planning.py.

## Worked example

Circular LEO at 550 km, inclination 53 deg, RAAN 0, initial argument of
latitude 0, Greenwich angle 0, 24 h horizon, 30 s step. Berlin station
52.52 N, 13.405 E with a 10 deg mask (module outputs):

- Orbital period: orbital_period_s(550.0) = 5730.13 s (95.5 min).
- Pass detection: detect_passes returns 5 passes above the mask, total
  contact 2280 s (38.0 min):
  - pass 1: start 6540 s, end 6900 s, duration 390 s, max elevation
    23.350 deg;
  - pass 2: start 12450 s, end 12900 s, duration 480 s, max elevation
    66.945 deg;
  - pass 3: start 18390 s, end 18870 s, duration 510 s, max elevation
    82.905 deg;
  - pass 4: start 24360 s, end 24840 s, duration 510 s, max elevation
    62.159 deg;
  - pass 5: start 30360 s, end 30720 s, duration 390 s, max elevation
    20.611 deg.
- Daily contact schedule: daily_contact_schedule lists 4 inter-pass
  downlink gaps of 5520 s, 5460 s, 5460 s and 5490 s; max_downlink_gap
  = 55650 s (15.46 h), the trailing horizon interval after pass 5 ends
  at 30720 s.
- Multi-station plan: ground_station_contact_plan with Berlin and
  Madrid (40.42 N, 3.70 W), both masks 10 deg, returns 6 merged
  contacts, total 3540 s (59 min) and max gap 49680 s (13.8 h). The
  first merged contact starts 6270 s (opened by the Madrid station,
  index 1) and runs 660 s with max elevation 24.381 deg; Madrid's
  closing pass 36240 to 36690 s extends the day and shortens the
  trailing outage from 15.46 h to 13.8 h.

## Verification

- Confirm orbital_period_s(550.0) = 5730.13 s within 0.1 s and equal to
  the closed form 2 pi sqrt(a^3 / mu).
- Confirm subsatellite_point at t = 0 with zero argument of latitude,
  RAAN and Greenwich angle sits at lat 0, lon 0, and that the zenith
  check elevation_angle(52.52, 13.405, 52.52, 13.405, 550) reads
  89.99999 deg within 1e-3.
- Confirm the coverage inverse identity: a station at the 14.9676 deg
  central angle of the 10 deg mask observes elevation 10.000 deg within
  1e-3, and the 22.9961 deg horizon central angle of the 550 km orbit
  observes elevation 0 deg within 1e-3.
- Confirm detect_passes on the worked example returns 5 passes with the
  listed starts and durations within 1 s and maximum elevations within
  0.01 deg, and that every duration equals end minus start plus the 30
  s step.
- Confirm daily_contact_schedule totals 2280.0 s within 1 s with the 4
  listed gap durations within 1 s, and that the total equals the sum of
  the pass durations.
- Confirm max_downlink_gap = 55650.0 s within 1 s and that an empty
  pass list returns 86400.0 s (the whole 24 h horizon).
- Confirm ground_station_contact_plan (Berlin and Madrid) returns 6
  contacts, 3540.0 s within 1 s and max gap 49680.0 s within 1 s, with
  the merged total never below either single-station total and never
  above the sum of the station totals.
- Confirm ValueError rejection of negative altitudes, inclinations
  outside [0, 180] deg, negative propagation times, negative elevation
  masks and non-positive horizons.
- Confirm determinism: identical inputs return identical schedules, the
  fixed-step propagation loop uses no RNG.
- Run the contract test offline: python3
  scripts/test_ground_station_pass_planning.py (35 tests,
  deterministic).

## Related leaves

- space-systems/orbit-mechanics/satellite-coverage: the single-pass
  visibility circle and pass-duration estimates that this leaf's
  elevation mask convention inverts; coverage geometry, not the daily
  schedule.
- space-systems/subsystems/command-data-handling: the downlink data
  budgeting and frame accounting that consumes the contact totals this
  leaf produces.
- space-systems/subsystems/communication-link-budget: the RF link
  sizing for the station antennas once the contact windows are fixed.
- space-systems/orbit-mechanics/ground-track-repeat: the repeat cycle
  that sets how the daily contact pattern of this leaf repeats.
- space-systems/orbit-mechanics/kepler-orbit-propagation: the physical
  state propagation whose elements this leaf takes as inputs for the
  simple circular two-body ground track.

## Pitfalls

- Reading the maximum downlink gap from the gap list only: the maximum
  includes the horizon boundaries, so the Berlin day shows 55650 s, the
  trailing interval after the last pass, not the largest 5520 s
  inter-pass gap.
- Holding the Greenwich angle fixed over the horizon: the Earth rotates
  under the inertial track by about 23.9 deg per 95.5 min orbit at 550
  km, and the west drift sets the pass cadence over a fixed station.
- Forgetting the inclusive sample run: a pass sampled at its start and
  end spans end - start + 30 s, so a 6540 to 6900 s pass lasts 390 s,
  not 360 s.
- Setting the mask at the horizon: a 0 deg mask reaches the 22.9961 deg
  horizon central angle while a 10 deg mask shrinks the day to the
  14.9676 deg cone; masks above the highest pass of the day (about
  82.9 deg for the worked example) return no passes.
- Treating the merged plan as a sum: overlapping station contacts merge
  into one, so the multi-station total never exceeds the sum of the
  station totals and can equal the better single station when one
  station dominates every window.
- Routing frame-level downlink data budgeting here: command-data-
  handling owns how many bits fit in the contact; this leaf owns when
  the contact happens and how long the outages last.
- Routing physical orbit propagation here: this leaf's ground track is
  the simple circular two-body footprint; oblateness and atmospheric
  effects on the orbit state belong to the propagation leaves.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ground_station_pass_planning.py

The 35 tests cover the worked example anchors (period 5730.13 s within
0.1, 5 Berlin passes with starts, durations and maximum elevations
within the spec bounds, daily total 2280 s, gaps 5520/5460/5460/5490 s,
maximum downlink gap 55650 s, empty-horizon 86400 s, merged Berlin and
Madrid plan with 6 contacts, 3540 s and 49680 s), the sub-satellite
point epoch and drift checks, the zenith 90 deg identity, the coverage
inverse identities at the 14.9676 deg and 22.9961 deg central angles,
the duration identity, the merged-total bounds identity, run
determinism, and ValueError rejection of negative altitudes, out-of-
range inclinations, negative times, negative elevation masks and
non-positive horizons.

## Compliance

- Standards referenced, not reproduced: ECSS space mission design
  standards (ecss.nl) frame the ground station contact scheduling
  context; the pass geometry, two-body ground track and elevation
  relations above are common astrodynamics, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
