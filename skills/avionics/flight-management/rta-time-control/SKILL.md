---
name: rta-time-control
description: "Use when you must compute the required time of arrival (RTA) function of a flight management system: estimate the arrival time at a downstream waypoint from the remaining distance and ground speed, derive the speed adjustment needed to satisfy the RTA time constraint, check the constraint against the achievable arrival window set by the minimum and maximum cruise Mach bounds, and return the Mach command, the predicted time error and the feasibility verdict for the FMS time control. Produces the ETA, time error, required ground speed and Mach command, achievable window and remaining time error. Trigger: required time of arrival, RTA time constraint, speed adjustment, arrival window, time error, 4D trajectory, FMS time control, Mach command."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
gated: false
domain: avionics
pack: flight-management
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: flight-management
  tags: [rta-time-control, required-time-of-arrival, rta-time-constraint, speed-adjustment, arrival-window, time-error, 4d-trajectory, fms-time-control]
  version: 0.1.0
  author: AeroSkills
---

# RTA Time Control (avionics/flight-management/rta-time-control)

Use when the task is the required-time-of-arrival (RTA) control function of
a flight management system: predicting the time of arrival at a downstream
waypoint, computing the speed adjustment that lands the aircraft at the
waypoint at the RTA time constraint, and judging whether the constraint
lies inside the achievable arrival window set by the minimum and maximum
cruise Mach. This leaf implements the deterministic speed-command law in
pure Python, stdlib only. It pairs with avionics/flight-management/
performance-computation for the speed selection context,
avionics/flight-management/vertical-navigation for the vertical profile,
and avionics/flight-management/flight-planning for the route structure that
carries the leg.

## Domain quick reference

- Ground speed law: GS = TAS + V_wind, with the along-track wind V_wind
  positive for a tailwind. TAS and GS in m/s.
- Estimated time of arrival: eta = d_rem / GS, a flight duration from the
  prediction time t_now, with d_rem the remaining distance.
- Time error: e = (t_now + eta) - t_RTA, positive when the aircraft is
  late against the RTA time constraint; the constraint is met when
  |e| <= TIME_TOL_S (5 s).
- Required ground speed: GS_req = d_rem / (t_RTA - t_now), the constant
  ground speed that arrives exactly at the RTA time.
- Required Mach: M_req = (GS_req - V_wind) / a, with the ISA speed of
  sound a = sqrt(GAMMA * R * T), T = 288.15 - 0.0065 h in the troposphere,
  GAMMA = 1.4, R = 287.05 J/(kg K).
- Achievable window: the cruise Mach envelope [M_min, M_max] maps to
  ground speeds GS_min = M_min * a + V_wind and GS_max = M_max * a +
  V_wind, so arrivals can only fall in [d_rem / GS_max, d_rem / GS_min]
  relative to t_now.
- Command law: met within tolerance, hold the current speed; M_req inside
  the envelope, command M_req (feasible); M_req above M_max or below
  M_min, command the nearer bound (unfeasible) and report the remaining
  time error of the best achievable arrival.
- The speed command is a Mach number; a calibrated-airspeed presentation
  of the same command is a display-layer conversion outside this leaf.
- Units are SI throughout: m, m/s, s. DO-178C frames the software context
  for the FMS function; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Fix the leg state: remaining_distance_m, ground_speed_m_s,
   wind_along_m_s, rta_time_s on the same clock as t_now_s (default 0),
   altitude_m, and the cruise envelope mach_min, mach_max.
2. Get the current prediction: eta_s for the ETA duration and
   time_error_s for the sign and size of the RTA time error.
3. Size the window: achievable_window returns gs_min, gs_max, eta_min_s
   and eta_max_s; if rta_time_s falls outside it, the constraint cannot be
   met at any cruise speed.
4. Run the command law: rta_speed_command(inputs) decides hold,
   feasible-speed-change or bound-command and returns the full verdict
   dict with required_gs_m_s, required_mach, command_mach, feasible,
   predicted_eta_s, remaining_error_s and the verdict string.
5. Convert speeds with tas_from_ground_speed and mach_from_tas when a
   side check on TAS or Mach is needed, and isa_speed_of_sound for the
   local speed of sound.
6. Confirm the deterministic checks with the contract test
   scripts/test_rta_time_control.py.

## Worked example

Leg remaining 450000 m (about 243 NM), current ground speed 250 m/s, wind
along +15 m/s (tailwind), altitude 10668 m (module speed of sound
a = 296.53 m/s; the spec display rounds it to 296.51), Mach envelope
[0.72, 0.84], t_now = 0.

- ETA: eta_s(450000, 250) = 1800 s.
- Case 1, RTA 1900 s: time_error_s(1800, 1900, 0) = -100 s (early, must
  slow). required_gs = 450000/1900 = 236.84 m/s; required TAS =
  236.84 - 15 = 221.84 m/s; required Mach = 221.84/296.53 = 0.7481
  (spec anchor 0.74818). Inside the envelope: command_mach 0.7481,
  feasible True, predicted_eta_s 1900 s, remaining_error_s 0,
  verdict rta-feasible.
- Case 2, RTA 1200 s: required_gs = 450000/1200 = 375 m/s, required Mach
  1.214, above mach_max 0.84: command_mach 0.84, feasible False; ground
  speed at Mach 0.84 = 0.84 * 296.53 + 15 = 264.09 m/s; best eta =
  450000/264.09 = 1703.97 s (spec anchor 1704.1); remaining_error_s =
  1703.97 - 1200 = +503.97 s late (spec anchor 504.1), verdict
  rta-unfeasible.
- Case 3, RTA 1800 s (equals the ETA): |error| 0 <= 5 s, hold the current
  speed; command_mach = (250 - 15)/296.53 = 0.7925 (spec anchor 0.79257).
- Window: eta_min_s = 450000/264.09 = 1703.97 s (fastest) to eta_max_s =
  450000/228.50 = 1969.33 s (slowest, spec anchor 1969.4). An RTA of
  2000 s falls beyond eta_max_s: command mach_min 0.72, feasible False,
  remaining_error_s = 1969.33 - 2000 = -30.67 s (still early), verdict
  rta-unfeasible.

## Verification

- Confirm eta_s(450000, 250) returns 1800 s exactly.
- Confirm required_gs for RTA 1900 s is 236.84 m/s within 0.01 and the
  required Mach for the 221.84 m/s TAS is within 1e-4 of 0.74818.
- Confirm the window eta bounds land within 0.5 s of 1704.1 s and
  1969.4 s and that gs = M * a + wind holds for both envelope bounds.
- Confirm the hold branch keeps the current-speed Mach 0.7925 command
  whenever |time error| <= 5 s and the feasible branch reports zero
  remaining error with predicted_eta_s equal to the RTA time.
- Confirm the unfeasible fast case (RTA 1200 s) reports remaining_error_s
  +504.1 s within 0.5 and the verdict rta-unfeasible.
- Confirm every negative distance, non-positive ground speed, RTA time at
  or before t_now, non-positive mach_min, inverted envelope, negative
  altitude and headwind above the minimum-cruise TAS raises ValueError.
- Run the contract test offline: python3
  scripts/test_rta_time_control.py (42 tests, deterministic).

## Related leaves

- avionics/flight-management/performance-computation: the cruise speed
  selection context that supplies the speed the RTA function adjusts.
- avionics/flight-management/vertical-navigation: the descent path that
  carries the aircraft to the constrained waypoint.
- avionics/flight-management/flight-planning: the route structure whose
  legs carry the remaining-distance input.
- avionics/flight-management/lateral-navigation: the lateral guidance the
  time-based operation runs alongside.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rta_time_control.py

The test covers the ISA speed of sound at sea level, cruise altitude and
in the isothermal stratosphere, the ETA division, the time error sign
convention for early, late and on-time arrivals, the required ground
speed anchor, the TAS from ground speed and wind with headwind rejection,
the Mach conversion anchors and round trip, the achievable window values
with internal consistency, the feasible slow-down command, the hold
branch on time and within tolerance, the unfeasible fast and slow cases
with their remaining error values, the nonzero t_now clock handling, the
verdict strings and the ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: DO-178C is the software
  considerations context for FMS functions and is cited reference-only;
  the RTA relations above are standard engineering methodology,
  summary-only per standards-map.yaml. No proprietary FMS documentation
  is reproduced.
- compliance: STANDARDS-REF, gated: false.
