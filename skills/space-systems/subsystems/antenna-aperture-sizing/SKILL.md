---
name: antenna-aperture-sizing
description: "Use when you must size the parabolic antenna aperture of a spacecraft communications link: convert a required antenna gain into the reflector diameter through the aperture efficiency, compute the achieved gain of the sized aperture, the half-power beamwidth, the pointing budget with pointing loss, and the receive gain-over-temperature G/T figure of merit. Produces the required gain, the reflector diameter, the achieved gain, the beamwidth, the pointing budget and the G/T that gate an antenna aperture sizing. Trigger: antenna aperture sizing, parabolic reflector gain, aperture efficiency, required antenna gain, half-power beamwidth, pointing loss budget, gain over temperature, spacecraft antenna sizing."
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
  tags: [antenna-aperture-sizing, parabolic-reflector-gain, aperture-efficiency, required-antenna-gain, half-power-beamwidth, pointing-loss-budget, gain-over-temperature, spacecraft-antenna-sizing]
  version: 0.1.0
  author: AeroSkills
---

# Parabolic Antenna Aperture Sizing (space-systems/subsystems/antenna-aperture-sizing)

Use when the task is sizing the parabolic reflector antenna aperture of a
spacecraft communications link in the reverse direction: the antenna gain is
an INPUT handed over from the forward link design, and this leaf converts the
required gain into the reflector diameter through the aperture efficiency,
then reports the achieved gain of the sized aperture, the half-power
beamwidth, the pointing accuracy requirement with its pointing loss, and the
receive gain-over-temperature G/T. It implements the standard
eta * (pi * D / lambda)^2 aperture model in pure Python, stdlib only,
deterministic and offline. It pairs with space-systems/subsystems/
communication-link-budget, which supplies the required-gain input; the
reverse-sizing pattern follows the precedent of the solar-array and battery
leaves.

## Domain quick reference

- Wavelength: lambda = c / f, with c = 299792458 m/s. S-band 2.2 GHz gives
  lambda about 0.13627 m.
- Aperture gain: G = eta * (pi * D / lambda)^2 linear, gain in dB is
  10 * log10(G). The aperture efficiency eta defaults to 0.6, the typical
  parabolic reflector value, and must lie in (0, 1].
- Aperture from the required gain: D = (lambda / pi) * sqrt(G_lin / eta),
  with G_lin = 10**(gain_db / 10). This is the reverse of the gain law and
  the sizing step of this leaf.
- Required-gain assembly (terms taken from the forward link design):
  G_req = margin + path loss + other losses + 10 * log10(k * T * R)
  - transmit power, all terms in dB, k = 1.380649e-23 J/K, R the data rate,
  T the system noise temperature.
- Half-power beamwidth: theta_3dB = 70 * lambda / D degrees, the standard
  lambda/D approximation for a uniformly illuminated circular aperture.
- Pointing budget: allowed pointing error = pointing_fraction * theta_3dB,
  with pointing_fraction default 0.1; pointing loss =
  12 * (pointing_fraction)^2 dB in the small-error approximation, so the
  default budget allows 0.360 deg error for 0.12 dB loss on a 3.60 deg beam.
- Gain over temperature: G/T = receive_gain_db - 10 * log10(T), dB/K, with T
  the receive system noise temperature.
- Units are SI: m, Hz, K, bps, dBW for transmit power, dB for gains and
  losses. ECSS frames the space communications context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Fix the requirement: take the required antenna gain from the forward link
   design, or assemble it with required_gain_db(margin_db, path_loss_db,
   other_losses_db, data_rate_bps, noise_temp_k, transmit_power_dbw) when the
   link terms are available.
2. Convert the operating frequency to wavelength with wavelength(freq_hz).
3. Size the aperture: aperture_from_gain(gain_db, wavelength_m, eta) returns
   the reflector diameter in meters.
4. Confirm the size closes the gain: gain_from_aperture(diameter_m,
   wavelength_m, eta) returns (gain_lin, gain_db); the achieved gain must
   match the required gain to within 1e-6 dB.
5. Compute the beam: half_power_beamwidth(diameter_m, wavelength_m) returns
   theta_3dB in degrees; the beam narrows as the diameter grows.
6. Budget the pointing: pointing_budget(theta_3db_deg, pointing_fraction)
   returns the allowed error in degrees and the pointing loss in dB.
7. Rate the receive chain: gain_over_temperature(receive_gain_db,
   noise_temp_k) returns G/T in dB/K.
8. For the whole report in one call, antenna_sizing(required_gain_db,
   freq_hz, eta, noise_temp_k, pointing_fraction) returns the wavelength,
   diameter, achieved gain, beamwidth, pointing allowance and loss, G/T
   (None when the noise temperature is not given) and the gain error.
9. Confirm the deterministic checks with the contract test
   scripts/test_antenna_aperture_sizing.py.

## Worked example

S-band downlink at f = 2.2 GHz, required gain 33.5 dBi, eta = 0.6, system
noise temperature 150 K. Real module outputs:

- Wavelength: lambda = c / f = 0.136269 m (bound about 0.13627 m).
- Reflector diameter: aperture_from_gain(33.5, 0.136269, 0.6) = 2.6496 m,
  inside the 2.5-2.8 m magnitude bound (about 2.650 m).
- Achieved gain: gain_from_aperture(2.6496, 0.136269, 0.6) = 33.500000 dB;
  the gain error achieved minus required is 0.0 dB, within 1e-6.
- Beamwidth: half_power_beamwidth = 70 * 0.136269 / 2.6496 = 3.60017 deg,
  inside the 3.3-3.9 deg bound (about 3.60 deg).
- Pointing budget: allowed error 0.36002 deg (0.1 * 3.60017) with pointing
  loss 12 * 0.1^2 = 0.12000 dB, about 0.360 deg and 0.12 dB.
- Gain over temperature: G/T = 33.5 - 10 * log10(150) = 11.7391 dB/K,
  inside the 11-13 dB/K bound (about 11.74 dB/K).

## Verification

- Confirm antenna_sizing(33.5, 2.2e9, 0.6, 150.0) returns a diameter in
  2.5-2.8 m, achieved gain 33.5 dB within 0.01 dB, beamwidth in 3.3-3.9 deg,
  G/T in 11-13 dB/K and an absolute gain error below 1e-6.
- Round trip: aperture_from_gain(gain_from_aperture(D)) recovers D to 1e-9.
- Beamwidth is monotonic decreasing in diameter; pointing fraction 0 gives
  zero pointing loss; doubling the noise temperature lowers G/T by 3.01 dB;
  the required gain rises 10 dB per decade of data rate and of noise
  temperature.
- ValueError rejection: frequency, diameter, wavelength, gain, data rate and
  noise temperature at or below zero, efficiency outside (0, 1], negative
  pointing fraction.
- Deterministic: no RNG, identical floats run to run; the convenience dict
  carries exactly the documented keys.
- Run the contract test offline: python3
  scripts/test_antenna_aperture_sizing.py (35 tests, deterministic).

## Related leaves

- space-systems/subsystems/communication-link-budget: the forward link
  budget that supplies the required-gain input this leaf sizes from.
- space-systems/subsystems/solar-array-sizing: the reverse-sizing pattern
  precedent in the same pack.
- space-systems/subsystems/spacecraft-battery-sizing: the companion power
  subsystem sizing leaf.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_antenna_aperture_sizing.py

The test covers the S-band sizing contract (diameter 2.5-2.8 m, beamwidth
3.3-3.9 deg, G/T 11-13 dB/K against the real module outputs), wavelength and
aperture gain, aperture from a required gain with the 1e-9 round trip, the
required-gain assembly scaling (10 dB per decade of data rate and noise
temperature), half-power beamwidth monotonicity, the pointing budget at the
default and zero fractions, gain over temperature with the 3.01 dB noise
doubling identity, the end-to-end sizing convenience dict and its exact key
set, ValueError rejection of every non-physical input, and run-to-run
determinism.

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-70 (space data links and
  RF comms) is a free ESA download (ecss.nl/standards); the aperture
  relations above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
