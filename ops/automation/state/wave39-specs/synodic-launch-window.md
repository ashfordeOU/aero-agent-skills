# Wave-39 leaf spec: synodic-launch-window (space-systems, mission-design pack)

- Path: skills/space-systems/mission-design/synodic-launch-window/
- Pack: mission-design. Closest siblings: launch-window-analysis (Earth-
  orbit DAILY window geometry only: launch_azimuth_for_inclination,
  direct_injection_feasible, daily_window_center_halfwidth,
  window_open_close, sun_sync_ltan_to_raan, plane_change_delta_v,
  elevation_angle_at_crossing, beta_angle - zero interplanetary content),
  c3-departure-energy (departure energy only: c3_from_excess_speed,
  injection_speed_delta_v, parking_period, asymptote_declination - no
  window timing; its fence chain points to launch-window-analysis for
  windows), lambert-transfer, hohmann-transfer, gravity-assist-swingby.
  Whole-tree greps at prep: "synodic" = 0 hits in skills/; corpus 0 tasks.
  Heliocentric launch-window recurrence and phase geometry fall between the
  Earth-orbit daily leaf and the departure-energy leaf, unowned. GENUINE
  SPACE gap (fresh probe).
- Standards id: ecss (reference-only; mission-design pack convention).
  Ledger Standard: ecss.
- Family: space-systems

## Claim

Determine the interplanetary launch-window timing between two planets on
near-circular coplanar orbits: compute the synodic period of the launch
opportunity recurrence T_syn = (T_in * T_out) / (T_out - T_in), the
required heliocentric departure phase angle for a Hohmann window
alpha_dep = pi * (1 - ((a_in + a_out) / 2 / a_out)^1.5), the recurrence
epochs t_k = t_0 + k * T_syn, and the phase progression between windows.
Produces the synodic period, the departure phase angle, the window epochs
and the phase check that gate interplanetary mission window planning. Does
NOT do: Earth-orbit daily window geometry (launch-window-analysis);
departure energy and excess speed (c3-departure-energy); transfer orbit
design (hohmann-transfer, lambert-transfer); gravity-assist swingby.

## Model (implement exactly)

Functions (pure stdlib):
- synodic_period(inner_period_days, outer_period_days) -> T_syn =
  (T_in * T_out) / (T_out - T_in); ValueError if either period <= 0 or
  outer <= inner.
- hohmann_departure_phase_angle(inner_sma_au, outer_sma_au) -> float
  radians: pi * (1 - ((a_in + a_out) / 2 / a_out)^1.5); ValueError if
  either semi-major axis <= 0 or outer <= inner.
- window_epochs(t0_days, synodic_days, count) -> list of t_0 + k *
  T_syn for k in 0..count-1; ValueError if count < 1 or synodic_days <= 0.
- phase_progression(t_days, t0_days, synodic_days) -> float in [0, 2*pi):
  the heliocentric phase advance of the outer planet relative to the inner
  since t0, 2 * pi * ((t - t0) / T_syn mod 1).
- synodic_report(...) -> dict with keys synodic_period_days,
  departure_phase_angle_deg, window_epochs, phase_at_first_window
  (the phase at the first recurrence epoch, checked near zero modulo
  2*pi).
Defaults: Earth a = 1.0 AU, T = 365.25 days; Mars a = 1.523679 AU,
T = 686.98 days (module constants EARTH_YEAR_DAYS, MARS_YEAR_DAYS).

Identity to test: after one synodic period the phase returns to its start
(phase_progression at t0 + T_syn is 0 modulo 2*pi); the departure phase
angle for a Hohmann transfer is about 44 degrees for Earth to Mars; the
synodic period exceeds both orbital periods.

## Worked example

Earth to Mars:
- T_syn = (365.25 * 686.98) / (686.98 - 365.25) = 779.9 days.
- alpha_dep = pi * (1 - (1.26184 / 1.523679)^1.5) = 44.34 degrees.
- window epochs from t0 = 0: 0, 779.9, 1559.7 days (count 3).
- phase at t0 + T_syn is 0.0 modulo 2*pi.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (direct evaluation of the synodic and phase
formulas; independently checked at prep).

## Validation list (contract test must include)

- synodic_period(365.25, 686.98) = 779.9 days within 0.5.
- hohmann_departure_phase_angle(1.0, 1.523679) = 44.34 degrees within
  0.1 (0.7739 rad within 0.002).
- window_epochs(0, 779.9, 3) = [0, 779.9, 1559.8] within 0.1.
- phase_progression returns 0 modulo 2*pi at t0 + T_syn; monotone
  increase between windows.
- Identity: T_syn equals the beat period of the two orbital frequencies.
- ValueErrors: outer period <= inner period, non-positive periods or
  semi-major axes, count 0.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-synodic-launch-window.yaml)

Query 1 (copy verbatim):
  "compute the synodic-launch-window recurrence and the required departure phase angle for the earth to mars transfer"
  intent: "space-systems; interplanetary launch window synodic period"
  expected_skill: "space-systems/mission-design/synodic-launch-window"
Query 2 (copy verbatim):
  "determine the heliocentric departure phase angle for the hohmann window to mars from the synodic period"
  intent: "space-systems; departure phase angle for the planetary window"
  expected_skill: "space-systems/mission-design/synodic-launch-window"
Task ids: w39-synodic-launch-window-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must determine the interplanetary
launch-window timing between two planets:" and include the outputs in the
Claim. First tag: synodic-launch-window. Additional tags ONLY:
synodic-period, launch-window-recurrence, departure-phase-angle,
heliocentric-transfer, interplanetary-window, hohmann-window. NEVER single
generic words (synodic, launch, window, planet, mars, phase, transfer,
orbit). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

FORBIDDEN TOKENS (belong to siblings): launch-azimuth, inclination, ltan,
beta-angle, daily-window (launch-window-analysis); c3, excess-speed,
injection-delta-v, parking-orbit (c3-departure-energy); porkchop,
lambert (lambert-transfer); gravity-assist (gravity-assist-swingby).
