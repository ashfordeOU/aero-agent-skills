# Wave-28 leaf spec: rta-time-control (avionics, flight-management pack)

- Path: skills/avionics/flight-management/rta-time-control/
- Pack: flight-management (existing siblings: flight-planning,
  lateral-navigation, vertical-navigation, performance-computation,
  radio-navigation-aids, rnp-anp-containment)
- Standards ids: do-178c  (Ledger Standard: do-178c)
- Family: avionics

## Claim

Compute the required-time-of-arrival (RTA) control function of a
flight management system: estimate the time of arrival at a downstream
waypoint from the remaining distance and the ground speed, compute the
speed adjustment needed to satisfy an RTA time constraint at the
waypoint, check the constraint against the achievable arrival window
set by the minimum and maximum cruise speeds, output the speed command
(Mach or calibrated airspeed) and the predicted time error, and update
the prediction along the leg. Produces the ETA, the time error, the
required ground speed and Mach command, the achievable window, the
feasibility verdict, and the remaining time error that gate the FMS
time-based operation.

Does NOT do: select the ECON cruise Mach from the cost index or
evaluate step climbs (performance-computation owns cost index, ECON,
step climb, top of descent); build the lateral track or great-circle
legs (lateral-navigation, flight-planning); compute the VNAV descent
path (vertical-navigation); assess RNP containment (rnp-anp-
containment).

## Model (implement exactly)

Module constants:
- GAMMA = 1.4, R_GAS = 287.05.
- TIME_TOL_S = 5.0 (RTA met when |time error| <= tolerance).

Inputs:
- remaining_distance_m (float),
- ground_speed_m_s (float, current),
- wind_along_m_s (float, positive tailwind; ground speed = true air
  speed + wind_along),
- rta_time_s (float, seconds from t_now to the required arrival),
- t_now_s (float, default 0.0),
- altitude_m (float, for the speed-of-sound conversion),
- mach_min, mach_max (float, cruise speed envelope),
- speed_mode (str "mach" or "cas"; the leaf outputs a Mach command and
  also a CAS command via the conversion when requested).

Functions:
- isa_speed_of_sound(altitude_m) -> float (same formula as
  flight-mechanics performance leaves; implement locally).
- eta_s(remaining_distance_m, ground_speed_m_s) -> float:
  distance/ground_speed (relative to t_now). ValueError on distance <
  0 or speed <= 0.
- time_error_s(eta_rel, rta_time_s, t_now_s) -> float:
  (t_now + eta) - rta (positive = late).
- required_ground_speed_m_s(remaining_distance_m, rta_time_s,
  t_now_s) -> float: distance/(rta - t_now). ValueError on rta <=
  t_now.
- tas_from_ground_speed(ground_speed_m_s, wind_along_m_s) -> float:
  ground_speed - wind_along.
- mach_from_tas(tas_m_s, altitude_m) -> float: tas/speed_of_sound.
- achievable_window(remaining_distance_m, altitude_m, wind_along_m_s,
  mach_min, mach_max) -> dict: gs_min = tas(mach_min) + wind,
  gs_max = tas(mach_max) + wind; eta_max = distance/gs_min,
  eta_min = distance/gs_max; return {gs_min, gs_max, eta_min_s,
  eta_max_s} (times relative to t_now).
- rta_speed_command(inputs) -> dict:
  eta_rel = eta_s(distance, current gs);
  err = time_error_s(eta_rel, rta, t_now);
  if |err| <= TIME_TOL_S: command holds the current speed;
  else required_gs = required_ground_speed_m_s(...);
  required_tas = tas_from_ground_speed(required_gs, wind);
  required_mach = mach_from_tas(required_tas, altitude);
  window = achievable_window(...);
  if mach_min <= required_mach <= mach_max:
    command_mach = required_mach; feasible True;
    predicted_eta = rta (error 0 by construction);
  else:
    command_mach = mach_max if required_mach > mach_max else mach_min;
    feasible False; best_eta = distance/(tas(command_mach) + wind);
    remaining_error = (t_now + best_eta) - rta;
  Output dict: {eta_rel_s, time_error_s, required_gs_m_s,
  required_mach (or None), command_mach, feasible (bool), window,
  predicted_eta_s, remaining_error_s (0 when feasible), verdict
  ("rta-feasible" or "rta-unfeasible")}.
ValueError on: remaining_distance_m < 0, ground_speed <= 0,
rta_time_s <= t_now_s, mach_min <= 0, mach_max < mach_min,
altitude_m < 0.

## Worked example

Leg remaining 450000 m (about 243 NM); current ground speed 250 m/s;
wind along +15 m/s (tailwind); altitude 10668 m (a = 296.51 m/s);
mach envelope [0.72, 0.84]; t_now = 0.
- eta_s = 450000/250 = 1800 s (assert).
- Case 1, RTA = 1900 s (arrive 100 s later than current ETA):
  err = 1800 - 1900 = -100 s (early, must slow down); assert.
  required_gs = 450000/1900 = 236.84 m/s (assert within 0.01);
  required_tas = 236.84 - 15 = 221.84 m/s;
  required_mach = 221.84/296.51 = 0.74818 (assert within 1e-4);
  inside the envelope -> command_mach 0.74818, feasible True,
  remaining_error 0, verdict "rta-feasible".
- Case 2, RTA = 1200 s (arrive 600 s earlier): required_gs =
  450000/1200 = 375 m/s; required_tas = 360 m/s; required_mach =
  1.2141 above mach_max 0.84 -> command_mach = 0.84, feasible False;
  gs at mach 0.84 = 0.84*296.51 + 15 = 249.07 + 15 = 264.07 m/s
  (assert within 0.01); best_eta = 450000/264.07 = 1704.1 s;
  remaining_error = 1704.1 - 1200 = +504.1 s late (assert within
  0.5); verdict "rta-unfeasible".
- Case 3, RTA = 1800 s (equals current ETA): |err| = 0 <= 5 ->
  hold current speed; command_mach = 250 - 15 = 235/296.51 =
  0.79257 (assert within 1e-4).
- Window check: eta_min = 450000/(0.84*296.51 + 15) = 450000/264.07
  = 1704.1 s; eta_max = 450000/(0.72*296.51 + 15) = 450000/228.49 =
  1969.4 s (assert within 0.5). An RTA of 2000 s falls outside ->
  unfeasible (slowest still late) -> command mach_min; assert.
- ValueErrors on distance -1, gs 0, rta 0 (<= t_now 0), mach_max <
  mach_min.
Keep at least 18 test methods: isa speed of sound, eta, time error
signs (early/late/on-time), required ground speed, tas/wind
conversion, mach conversion, window values, feasible command case,
hold case, unfeasible fast case, unfeasible slow case, remaining
error values, verdict strings, ValueErrors.

## Corpus tasks (ids w28-rta-time-control-1/2)

Distinctive tokens: required time of arrival, RTA time constraint,
speed adjustment, arrival window, time error, 4D trajectory, FMS time
control. Avoid: cost index, ECON cruise Mach, fuel time trade
(performance-computation); top of descent, VNAV path (vertical-
navigation); great circle leg distance (flight-planning); RNP
containment (rnp-anp-containment).

1. "compute the FMS required time of arrival speed adjustment to meet
   the RTA time constraint at the downstream waypoint and report the
   time error"
2. "check the achievable arrival window for the RTA: evaluate the
   minimum and maximum cruise speed bounds and output the Mach command
   and the feasibility verdict"

## SKILL body notes

Pair with performance-computation (speed selection neighbor),
vertical-navigation (vertical profile neighbor), and flight-planning
(route structure). RTA is the time-based operation function of the
FMS; the leaf implements the deterministic speed-command law and does
not reproduce any proprietary FMS documentation. DO-178C cited
reference-only as the software context for FMS functions.
