---
name: synodic-launch-window
description: "Use when you must determine the interplanetary launch-window timing between two planets: compute the synodic period of the launch opportunity recurrence for near-circular coplanar orbits, the heliocentric departure phase angle required for a Hohmann window, the recurrence epochs, and the phase progression between windows. Produces the synodic period, the departure phase angle, the window epochs, and the phase check that gate interplanetary mission window planning. Trigger: synodic period, launch window recurrence, departure phase angle, hohmann window, heliocentric transfer, interplanetary window, opportunity recurrence, synodic-launch-window, earth to mars."
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
  tags: [synodic-launch-window, synodic-period, launch-window-recurrence, departure-phase-angle, heliocentric-transfer, interplanetary-window, hohmann-window]
  version: 0.1.0
  author: AeroSkills
---

# Synodic Launch Window (space-systems/mission-design/synodic-launch-window)

Use when you must determine the interplanetary launch-window timing
between two planets on near-circular coplanar orbits. This leaf computes
the synodic period of the launch opportunity recurrence, the heliocentric
departure phase angle required for a Hohmann window, the recurrence
epochs and the phase progression between windows, in pure Python stdlib.
It sits between the Earth-orbit daily launch geometry leaf
(space-systems/mission-design/launch-window-analysis) and the
departure-energy analysis of this pack that sizes the hyperbolic escape,
and it hands its window epochs to the transfer design leaves in
space-systems/orbit-mechanics. Does NOT do: Earth-orbit daily launch
geometry, hyperbolic departure-energy sizing, transfer orbit design, or
multi-planet trajectory design.

## Domain quick reference

- Synodic period of the launch opportunity recurrence: T_syn = (T_in *
  T_out) / (T_out - T_in), with T_in the inner orbital period and T_out
  the outer orbital period. It is the beat period of the two orbital
  frequencies, defined only when the outer period exceeds the inner one,
  and it always exceeds both orbital periods.
- Heliocentric departure phase angle for a Hohmann window: alpha_dep =
  pi * (1 - ((a_in + a_out) / 2 / a_out)^1.5) radians, with a_in and
  a_out the inner and outer semi-major axes. For Earth to Mars it is
  about 0.774 rad, or 44.34 degrees.
- Recurrence epochs: t_k = t_0 + k * T_syn, one launch opportunity per
  synodic period starting at the launch epoch t_0.
- Phase progression between windows: phi(t) = 2 * pi * (((t - t_0) /
  T_syn) mod 1) radians in [0, 2*pi). The phase returns to zero modulo
  2*pi at every recurrence epoch and rises monotonically between them.
- Window summary report: synodic_report bundles synodic_period_days,
  departure_phase_angle_deg, window_epochs and phase_at_first_window,
  with the phase at the first recurrence epoch near zero modulo 2*pi.
- Units: days for all periods and epochs, AU for the semi-major axes,
  radians and degrees for the angles as documented per output.
- ECSS standards frame the space mission design context; the relations
  above are standard astrodynamics methodology, summary-only.

## Workflow

1. Fix the two planets and their orbits: the inner orbital period T_in
   and semi-major axis a_in, the outer orbital period T_out and
   semi-major axis a_out. Earth to Mars defaults sit in the module
   constants EARTH_YEAR_DAYS (365.25), MARS_YEAR_DAYS (686.98),
   EARTH_SMA_AU (1.0) and MARS_SMA_AU (1.523679).
2. Compute the synodic period of the launch opportunity recurrence with
   synodic_period(inner_period_days, outer_period_days). The function
   rejects reversed or non-positive orbital periods with ValueError.
3. Compute the required heliocentric departure phase angle for the
   Hohmann window with hohmann_departure_phase_angle(inner_sma_au,
   outer_sma_au), returned in radians; convert with math.degrees when
   the plan needs degrees.
4. List the recurrence epochs with window_epochs(t0_days, synodic_days,
   count), returning t_0 + k * T_syn for k in 0..count-1. Reject count
   below 1 and non-positive synodic periods with ValueError.
5. Track the phase progression between windows with
   phase_progression(t_days, t0_days, synodic_days), the synodic cycle
   fraction since t_0 as an angle in [0, 2*pi); zero modulo 2*pi at
   every recurrence epoch, monotonically rising in between.
6. Bundle the window geometry with synodic_report(inner_period_days,
   outer_period_days, inner_sma_au, outer_sma_au, t0_days, count) and
   read the synodic period, the departure phase angle in degrees, the
   window epochs and the phase at the first recurrence epoch.
7. Confirm the deterministic checks with the contract test
   scripts/test_synodic_launch_window.py.

## Worked example

Earth to Mars: T_in = 365.25 days, T_out = 686.98 days, a_in = 1.0 AU,
a_out = 1.523679 AU, t_0 = 0 days.

- Synodic period: T_syn = (365.25 * 686.98) / (686.98 - 365.25) =
  779.9069 days (779.9 days to one decimal), exceeding both orbital
  periods.
- Departure phase angle: alpha_dep = pi * (1 - (1.26184 / 1.523679)^1.5)
  = 0.773952 rad = 44.3442 degrees (44.34 degrees to two decimals).
- Recurrence epochs from t_0 = 0: 0.0, 779.9069, 1559.8138 days (0,
  779.9, 1559.8 days to one decimal), window_epochs(0.0, 779.9069, 3).
- Phase check: the phase progression at t_0 + T_syn is 0.0 modulo 2*pi,
  so the next window opens exactly one synodic period later; at half a
  synodic period the phase reaches pi.
- Report: synodic_report(365.25, 686.98, 1.0, 1.523679) returns
  synodic_period_days 779.9069, departure_phase_angle_deg 44.3442,
  window_epochs [0.0, 779.9069, 1559.8138] and phase_at_first_window
  0.0.

## Verification

- Confirm synodic_period(365.25, 686.98) returns 779.9069 days, within
  0.5 days of the 779.9 day anchor, and that it equals the beat period
  1 / (1/365.25 - 1/686.98) of the two orbital frequencies.
- Confirm hohmann_departure_phase_angle(1.0, 1.523679) returns 0.773952
  rad, 44.3442 degrees, within 0.1 degrees of the 44.34 degree anchor.
- Confirm window_epochs(0.0, 779.9, 3) returns 0.0, 779.9 and 1559.8
  days within 0.1, and that the epochs are spaced by exactly one synodic
  period.
- Confirm the phase progression returns zero modulo 2*pi at every
  recurrence epoch and stays monotone between epochs, with the half
  synodic point at pi.
- Confirm the synodic_report dict exposes exactly the four documented
  keys with values matching the individual functions.
- Confirm ValueError rejection: outer period not exceeding the inner
  period, non-positive orbital periods or semi-major axes, window count
  below 1, and non-positive synodic periods.
- Run the contract test offline: python3
  scripts/test_synodic_launch_window.py (29 tests, deterministic).

## Related leaves

- space-systems/mission-design/launch-window-analysis: the Earth-orbit
  daily launch geometry that this leaf does not cover.
- space-systems/orbit-mechanics/hohmann-transfer: the transfer orbit
  flown between the departure and arrival planets once the window epoch
  is set.
- space-systems/mission-design/mission-delta-v-budget: the mission-level
  delta-v context around the interplanetary window planning.

## Pitfalls

- Confusing the synodic period with an orbital period: T_syn = 779.9
  days for Earth to Mars exceeds both the 365.25 day inner period and
  the 686.98 day outer period, so launch opportunities recur less often
  than either planet completes an orbit.
- Reporting radians where the plan expects degrees: the departure phase
  angle is 0.773952 rad but 44.3442 degrees, and synodic_report stores
  degrees under departure_phase_angle_deg; convert explicitly in the
  other functions.
- Treating every planetary pair as outward: the synodic period and
  departure phase angle formulas require the outer orbit to exceed the
  inner one, and reversed or equal inputs raise ValueError rather than
  silently returning a negative recurrence.
- Reading the phase progression as an instantaneous geometric angle: it
  is the synodic cycle fraction since t_0, zero modulo 2*pi only at the
  window epochs, so evaluating it halfway between windows gives pi, not
  a departure condition.
- Calling window_epochs with a zero or negative count: at least one
  window is required, and count below 1 raises ValueError.
- Rounding the synodic period before spacing epochs: window_epochs must
  use the full precision value (779.9069 days, not 779.9) or the epoch
  drift accumulates over many recurrences.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_synodic_launch_window.py

The test covers the Earth to Mars synodic period anchor (779.9 days
within 0.5), the beat-period identity, the departure phase angle anchors
(0.7739 rad and 44.34 degrees within the spec bounds), the recurrence
epoch anchors (0, 779.9, 1559.8 days within 0.1), the zero phase at
every recurrence epoch, the monotone phase progression with the half
synodic point at pi, the exact synodic_report keys and values, run
determinism, and ValueError rejection of reversed or non-positive
orbital periods, non-positive semi-major axes, window counts below 1 and
non-positive synodic periods.

## Compliance

- Standards referenced, not reproduced: ECSS mission design standards
  (ecss.nl) frame the space mission design context; the synodic window
  relations above are standard astrodynamics methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
