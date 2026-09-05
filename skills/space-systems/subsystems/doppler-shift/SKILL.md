---
name: doppler-shift
description: "Use when you must compute the doppler frequency shift on a spacecraft link: derive the line-of-sight range rate from the circular-orbit altitude and the ground elevation angle, convert it to the received frequency and offset on an s-band downlink carrier, and estimate the worst-case doppler near the horizon and the doppler-rate at acquisition for receiver acquisition design. Produces the range rate, received frequency, delta-f offset, maximum doppler, slant range and doppler rate that gate communication link acquisition. Trigger: doppler shift, received frequency offset, acquisition frequency offset, worst-case doppler, doppler rate, line-of-sight range rate, s-band downlink, leo overflight, spacecraft ground link."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: subsystems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: subsystems
  tags: [doppler-shift, range-rate-frequency-offset, doppler-rate, line-of-sight-relative-velocity, acquisition-frequency-offset, worst-case-doppler]
  version: 0.1.0
  author: AeroSkills
---

# Doppler Shift on a Spacecraft Link (space-systems/subsystems/doppler-shift)

Use when you must compute the doppler frequency shift on a spacecraft
link: the frequency offset a ground receiver must track as a
circular-orbit satellite passes, derived from the pass geometry. This
leaf implements the straight-line overflight model (range rate
rho_dot = -v * cos(elev) from the circular speed and the ground
elevation angle) in pure Python, stdlib only, and converts the range
rate into the received carrier frequency, the delta-f acquisition
offset, the worst-case doppler at the horizon and the doppler rate at
acquisition. It pairs with communication-link-budget for the received
power and margin side of the same pass, and with satellite-coverage for
the pass access geometry that feeds the elevation angle.

## Domain quick reference

- Circular speed at altitude h (m): v = sqrt(MU / (R_EARTH + h)) with
  R_EARTH = 6371.0e3 m and MU = 3.986004418e14 m^3/s^2. At 600 km,
  v = 7561.73 m/s.
- Range rate at elevation elev (deg): rho_dot = -v * cos(elev),
  negative while the satellite approaches (closing). Overhead (90 deg)
  the range rate is zero.
- Horizontal distance and slant range: x = h / tan(elev), then
  rho = sqrt(h^2 + x^2). At 600 km and 30 deg elevation,
  x = 1039.2 km and rho = 1200.0 km.
- Received frequency: f_rx = f_tx * (1 - rho_dot / C) with
  C = 299792458.0 m/s; delta_f = f_rx - f_tx. A closing satellite
  (negative rho_dot) raises the received frequency, so delta_f is
  positive while approaching and falls to zero overhead.
- Worst-case doppler: at the horizon (elev 0) the shift is
  f_tx * v / C, the maximum over the pass.
- Doppler rate at acquisition: rho_dot_dot = v^2 * h^2 / rho^3, then
  doppler_rate = f_tx / C * |rho_dot_dot| (Hz/s). The Hz/s scale is
  carrier dependent; the module defaults to the leaf S-band reference
  carrier F_TX_REF = 2.25e9 Hz, so pass f_tx for other carriers.
- Elevation domain: [0, 90] deg. The zenith point is admitted as the
  degenerate overhead case; the slant geometry is singular exactly at
  the horizon, so use max_doppler for the elevation-0 shift.
- Units are SI: m, m/s, Hz, Hz/s. ECSS frames the space engineering
  context; the relations above are standard engineering methodology,
  summary-only.

## Workflow

1. Fix the pass geometry: circular altitude h (m) and the link carrier
   f_tx (Hz), for example the 2.25 GHz S-band downlink.
2. Get the orbital speed with circular_velocity(h).
3. Get the range rate at the acquisition or current elevation with
   range_rate(h, elev_deg); negative while the satellite approaches.
4. Convert to the received carrier with doppler_shift(f_tx, h,
   elev_deg), which returns the dict {range_rate, received_freq,
   delta_f}.
5. Estimate the worst case over the pass with max_doppler(f_tx, h),
   the horizon shift; it equals doppler_shift at elevation 0.
6. Size the acquisition tracking with slant_range_and_rate(h, elev_deg,
   f_tx = F_TX_REF), which returns {x, rho, rho_dot, doppler_rate}.
7. Confirm the deterministic checks with the contract test
   scripts/test_doppler_shift.py.

## Worked example

A 600 km LEO satellite on a 2.25 GHz S-band downlink acquired at
30 deg elevation. Real module outputs (h = 600e3 m, elev = 30 deg):

- circular_velocity(600e3) = 7561.73 m/s.
- range_rate(600e3, 30) = -6548.65 m/s (closing).
- doppler_shift(2.25e9, 600e3, 30): range_rate -6548.65 m/s, received
  frequency 2250049148.9 Hz, delta_f +49148.9 Hz (+49.15 kHz).
- max_doppler(2.25e9, 600e3) = 56752.3 Hz, the horizon worst case.
- slant_range_and_rate(600e3, 30): x = 1039230.5 m, slant range
  rho = 1200000.0 m (1200.0 km), rho_dot -6548.65 m/s, doppler rate
  89.41 Hz/s at acquisition.
- Overhead identity: doppler_shift(2.25e9, 600e3, 90) gives delta_f 0
  and the received frequency back at 2250000000.0 Hz.
- Horizon identity: doppler_shift(2.25e9, 600e3, 0) equals
  max_doppler(2.25e9, 600e3) = 56752.3 Hz.

## Verification

- Confirm circular_velocity(600e3) returns 7561.73 m/s (anchor within
  1 m/s) and range_rate(600e3, 30) returns -6548.65 m/s within 1 m/s,
  with range_rate(600e3, 90) = 0.
- Confirm doppler_shift(2.25e9, 600e3, 30) returns received_freq
  2250049148.9 Hz and delta_f +49148.9 Hz within 50 Hz of the
  +49.15 kHz anchor, and that the shift is zero at 90 deg.
- Confirm max_doppler(2.25e9, 600e3) = 56752.3 Hz within 100 Hz, that
  it equals the shift at elevation 0, and that a higher orbit gives a
  smaller worst-case doppler.
- Confirm slant range 1200000.0 m within 1 km and doppler rate
  89.41 Hz/s within 2 Hz/s of the 89.4 Hz/s anchor, with dict keys
  exactly {x, rho, rho_dot, doppler_rate}.
- Confirm ValueError on h < 0, elevation below 0 or above 90 deg,
  f_tx <= 0, and on the singular horizon call of
  slant_range_and_rate.
- Run the contract test offline: python3
  scripts/test_doppler_shift.py (34 tests, deterministic, exit 0).

## Related leaves

- space-systems/subsystems/communication-link-budget: received power,
  antenna gains and margin on the same downlink; no frequency-shift
  math.
- space-systems/subsystems/antenna-aperture-sizing: the antenna
  aperture and beamwidth for the link that must acquire this shift.
- space-systems/subsystems/command-data-handling: the receiver and
  data-handling chain downstream of acquisition.
- space-systems/orbit-mechanics/satellite-coverage: pass access
  geometry and visibility windows that set the elevation profile.
- space-systems/mission-design/mission-delta-v-budget: the mission
  sizing loop the satellite design feeds.

## Pitfalls

- Flipping the sign convention: the range rate is negative while the
  satellite approaches, and a closing satellite RAISES the received
  frequency, so delta_f is positive before the pass and crosses zero
  at the zenith. Using |rho_dot| in f_rx = f_tx * (1 - rho_dot / C)
  inverts the offset and mis-sets the acquisition search direction.
- Reporting the worst-case doppler at the wrong geometry: the maximum
  shift occurs at the horizon (elevation 0), not overhead; the zenith
  shift is zero. Use max_doppler(f_tx, h), never an elevation-90
  doppler_shift call, when sizing the acquisition search range.
- Treating the doppler rate as carrier independent: doppler_rate in
  Hz/s scales with f_tx / C, so the 89.41 Hz/s worked-example value is
  valid only at the 2.25 GHz reference carrier. Pass f_tx explicitly
  for other links or the Hz/s number is wrong.
- Calling slant_range_and_rate at the exact horizon: x = h / tan(elev)
  is singular at elevation 0 and raises ValueError by design; the
  elevation-0 shift belongs to max_doppler and the doppler_shift
  functions, which stay finite there.
- Mixing this leaf with link-budget outputs: this leaf produces
  frequency-domain quantities (range rate, offsets, doppler rate)
  only; received-power and margin terms belong to
  communication-link-budget, and pass-time geometry belongs to
  satellite-coverage, not here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_doppler_shift.py

The test covers the 600 km, 2.25 GHz, 30 deg acquisition contract
(circular velocity 7561.73 m/s, range rate -6548.65 m/s, received
frequency 2250049148.9 Hz with delta_f +49148.9 Hz), the zero-shift
overhead identity, the horizon equality between max_doppler and the
elevation-0 shift, decreasing worst-case doppler with altitude, the
1200.0 km slant range and 89.41 Hz/s doppler-rate anchors, exact dict
key ordering, run-to-run determinism, the module constant values, and
ValueError rejection of negative altitude, out-of-range elevation,
non-positive carrier and the singular horizon slant call.

## Compliance

- Standards referenced, not reproduced: ECSS standards are freely
  downloadable (copyright ESA); summary-only per standards-map.yaml
  and brief 06.
- compliance: STANDARDS-REF, gated: false.
