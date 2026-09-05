# Wave-38 leaf spec: doppler-shift (space-systems, subsystems pack)

- Path: skills/space-systems/subsystems/doppler-shift/
- Pack: subsystems. Closest siblings: communication-link-budget (free
  space path loss, EIRP, received power, C/N0, Eb/N0 margin - no
  frequency-shift math), antenna-aperture-sizing, command-data-handling,
  satellite-coverage (orbit-mechanics: access geometry, pass time, revisit
  - the GEOMETRY that feeds a range-rate model, not the Doppler shift
  itself), mission-delta-v-budget. Whole-tree grep: "doppler" = ZERO
  owning hits in any leaf or router (verified: airborne-weather-radar has
  no doppler function either). ZERO owners of the Doppler-shift function.
  GENUINE SPACE gap (fresh probe).
- Standards id: ecss (reference-only; subsystems sibling convention).
  Ledger Standard: ecss.
- Family: space-systems

## Claim

Compute the Doppler frequency shift on a spacecraft-to-ground link: derive
the line-of-sight range rate from the pass geometry (circular-orbit
satellite altitude, ground elevation angle at the acquisition or current
time), compute the received frequency from the transmitted frequency and
the range rate, estimate the maximum Doppler shift near the horizon and
the Doppler rate at acquisition for receiver acquisition design. Produces
the range rate, the received frequency offset, the worst-case Doppler and
the Doppler rate that gate communication link acquisition. Does NOT do:
path loss, EIRP and link margin (communication-link-budget); pass access
time and revisit geometry (satellite-coverage); orbit propagation
(orbit-mechanics).

## Model (implement exactly)

Conventions: SI units. Earth radius R_EARTH = 6371.0e3 m, gravitational
parameter MU = 3.986004418e14 m3/s2, speed of light C = 299792458.0 m/s.
The satellite is in a circular orbit at altitude h (m); the ground station
sees it at elevation angle elev (deg) in the local frame. Documented
geometric model (a straight-line overflight in the orbital plane past the
station): at the moment the satellite is at elevation elev with the
station at the sub-satellite ground track, the line-of-sight range rate is
rho_dot = -v_sat * cos(elev) when approaching (negative = closing), with
v_sat = sqrt(MU / (R_EARTH + h)) (circular speed). The horizontal distance
x at that elevation is x = h / tan(elev) and the slant range is
rho = sqrt(h^2 + x^2) (used for the Doppler-rate computation).

Functions (pure stdlib):
- circular_velocity(h) -> float. ValueError: h < 0.
- range_rate(h, elev_deg) -> float: -v * cos(radians(elev)).
  ValueErrors: h < 0, elev outside [0, 90).
- doppler_shift(f_tx, h, elev_deg) -> dict {range_rate, received_freq,
  delta_f}: f_rx = f_tx * (1 - rho_dot / C); delta_f = f_rx - f_tx.
  ValueErrors: f_tx <= 0.
- max_doppler(f_tx, h) -> float: the shift at elev 0 (horizon), the
  worst case: v/c * f_tx magnitude.
- slant_range_and_rate(h, elev_deg) -> dict {x, rho, rho_dot,
  doppler_rate}: rho_dot_dot = v^2 * h^2 / rho^3 (the time derivative of
  the range rate at that geometry); doppler_rate = f_tx / C *
  |rho_dot_dot|.
Identity to test: doppler_shift at elev 90 (overhead, zero range rate) is
0; max_doppler equals doppler_shift at elev 0; a higher orbit (lower v)
gives a smaller max Doppler; received frequency rises as the satellite
approaches (delta_f positive with the sign convention above).

## Worked example

Verified at prep: h = 600 km (v = 7561.73 m/s), f_tx = 2.25 GHz
(S-band), elev = 30 deg:
- range_rate = -6548.65 m/s (approaching).
- received frequency = 2250049148.9 Hz; delta_f = +49148.9 Hz
  (+49.15 kHz).
- max_doppler at horizon = f_tx * v / C = 56752.3 Hz (computed at prep:
  2.25e9 * 7561.733 / 299792458 = 56752.3).
- slant range rho = 1200.0 km; doppler_rate at acquisition = 89.4 Hz/s
  (computed at prep from v^2 h^2 / rho^3 and the frequency scale).
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds from the circular-orbit kinematics
(independently evaluated by the anchor script at prep).

## Validation list (contract test must include)

- circular_velocity at 600 km = 7561.73 within 1 m/s.
- range_rate sign and magnitude at 30 deg (-6548.7 within 1 m/s);
  overhead (90 deg) = 0.
- doppler_shift anchor +49.15 kHz within 50 Hz; at 90 deg zero.
- max_doppler anchor 56.75 kHz within 100 Hz; decreases with altitude.
- slant range 1200.0 km within 1 km; doppler_rate 89.4 Hz/s within 2
  Hz/s.
- ValueErrors for h < 0, elev >= 90, f_tx <= 0.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave38-doppler-shift.yaml)

Query 1 (copy verbatim):
  "compute the doppler-shift and received-frequency offset for an s-band downlink from a 600 km leo satellite at 30 degrees elevation"
  intent: "space-systems; Doppler shift from range rate on a spacecraft link"
  expected_skill: "space-systems/subsystems/doppler-shift"
Query 2 (copy verbatim):
  "estimate the worst-case doppler and the doppler-rate at acquisition for a satellite ground link pass"
  intent: "space-systems; maximum Doppler and Doppler rate for receiver acquisition"
  expected_skill: "space-systems/subsystems/doppler-shift"
Task ids: w38-doppler-shift-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the doppler frequency
shift on a spacecraft link:" and include the outputs in the Claim. First
tag: doppler-shift. Additional tags ONLY: range-rate-frequency-offset,
doppler-rate, line-of-sight-relative-velocity, acquisition-frequency-
offset, worst-case-doppler. NEVER single generic words (doppler,
frequency, shift, satellite, link, range). 50-150 words, <=1000 chars,
no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): path loss, EIRP, C/N0, Eb/N0,
link margin (communication-link-budget); access time, revisit, swath,
coverage (satellite-coverage); Kepler propagation, orbital elements
(orbit-mechanics).
