# Wave-32 leaf spec: antenna-aperture-sizing (space-systems, subsystems pack)

- Path: skills/space-systems/subsystems/antenna-aperture-sizing/
- Pack: subsystems. Siblings: communication-link-budget (link budget
  with antenna gain as a GIVEN input), power-thermal-budget,
  solar-array-sizing, propellant-tank-sizing, spacecraft-battery-
  sizing, thermal-design, command-data-handling.
- Standards id: ecss (reference-only; pack convention for space
  leaves). Ledger Standard: ecss.
- Family: space-systems

## Claim

Size the parabolic-reflector antenna aperture of a spacecraft
communications link in the reverse direction: convert a required
antenna gain (from closing the link at a data rate) into the reflector
diameter through the aperture efficiency, compute the achieved gain of
the sized aperture, the half-power beamwidth, the pointing-accuracy
requirement and the pointing loss, and the receive gain-over-
temperature G/T figure of merit. Produces the required gain, the
reflector diameter, the achieved gain, the beamwidth, the pointing
budget and the G/T that gate an antenna aperture sizing.

Does NOT do: the forward link budget (communication-link-budget owns
EIRP, free-space path loss, received power with antenna gain as an
INPUT - this leaf computes the aperture from a gain requirement);
solar array or battery sizing (their own leaves); thermal design.

## Model (implement exactly)

Constants:
- ETA_APERTURE_DEFAULT = 0.6 (typical parabolic reflector aperture
  efficiency; declared input default).
- K_BOLTZ = 1.380649e-23 (J/K).
- LIGHT_SPEED = 299792458.0 (m/s).
- POINTING_FRACTION = 0.1 (allowed pointing error as a fraction of the
  half-power beamwidth; declared).
- POINTING_LOSS_COEF = 12.0 (dB per (theta_e/theta_3dB)^2 in the
  standard small-error approximation).

Functions (pure stdlib, deterministic; dB and linear conventions
match the communication-link-budget sibling: power in dBW, gains and
losses in dB):

- wavelength(freq_hz) -> lambda = c / f. ValueError if f <= 0.
- gain_from_aperture(diameter_m, lambda, eta =
  ETA_APERTURE_DEFAULT) -> G = eta * (pi * D / lambda)**2 (linear);
  also return gain_db = 10*log10(G).  ValueErrors on non-positive
  inputs, eta outside (0,1].
- aperture_from_gain(gain_db, lambda, eta = ETA_APERTURE_DEFAULT) ->
  D = (lambda/pi) * sqrt(G_lin / eta) with G_lin = 10**(gain_db/10).
  ValueErrors if gain_db <= 0 (aperture antennas have gain above 1).
- required_gain_db(margin_db, path_loss_db, other_losses_db,
  data_rate_bps, noise_temp_k, transmit_power_dbw) -> G_req_db =
  margin_db + path_loss_db + other_losses_db + 10*log10(K_BOLTZ *
  noise_temp_k * data_rate_bps) - transmit_power_dbw.  ValueErrors on
  non-positive data rate, noise temperature.
- half_power_beamwidth(diameter_m, lambda) -> theta_3dB_deg =
  70.0 * lambda / diameter_m (degrees; the standard
  lambda/D approximation for a uniformly illuminated circular
  aperture).  ValueErrors on non-positive inputs.
- pointing_budget(theta_3dB_deg, pointing_fraction =
  POINTING_FRACTION) -> dict {allowed_error_deg = theta_3dB *
  pointing_fraction, pointing_loss_db = POINTING_LOSS_COEF *
  (pointing_fraction)**2}.
- gain_over_temperature(receive_gain_db, noise_temp_k) -> G/T =
  receive_gain_db - 10*log10(noise_temp_k) (dB/K).  ValueError if
  noise_temp_k <= 0.
- antenna_sizing(required_gain_db, freq_hz, eta =
  ETA_APERTURE_DEFAULT, noise_temp_k = None,
  pointing_fraction = POINTING_FRACTION) -> dict {wavelength_m,
  diameter_m, achieved_gain_db, beamwidth_deg,
  pointing_allowed_deg, pointing_loss_db, gain_over_temperature_dbK
  (None when noise_temp_k None), gain_error_db (achieved - required,
  should be ~0)}.  ValueErrors propagate.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

S-band downlink at f = 2.2 GHz, required gain 33.5 dBi, eta = 0.6,
noise temperature 150 K.  Run your module and take the real outputs as
assert targets, then check the magnitude bounds:
- wavelength about 0.13627 m.
- diameter in 2.5-2.8 m (about 2.650).
- achieved_gain_db about 33.5 (within +-0.01 dB of the required).
- beamwidth_deg about 3.60 deg (70*0.13627/2.650 = 3.60; in 3.3-3.9).
- pointing_allowed_deg about 0.360 deg; pointing_loss_db about 0.12 dB
  (12*0.01).
- gain_over_temperature about 33.5 - 10*log10(150) = 33.5 - 21.76 =
  11.74 dB/K (in 11-13).
- gain_error_db within 1e-6.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: f <= 0, diameter <= 0, eta outside (0,1], gain_db <= 0,
  data rate <= 0, noise temp <= 0.
- Round trip: aperture_from_gain(gain_from_aperture(D)) == D to 1e-9.
- beamwidth decreases as diameter increases (monotonic).
- pointing budget: pointing_fraction 0 gives zero loss.
- required_gain_db increases with data rate and with noise
  temperature (10 dB/decade on each).
- G/T: doubling the noise temperature reduces G/T by 3.01 dB.
- Determinism: no RNG, identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-antenna-aperture-sizing.yaml)

Query 1 (copy verbatim):
  "size the parabolic reflector antenna diameter of a spacecraft downlink from the required antenna gain and the aperture efficiency at the operating frequency"
  intent: "space-systems; spacecraft antenna aperture sizing from gain requirement"
  expected_skill: "space-systems/subsystems/antenna-aperture-sizing"
Query 2 (copy verbatim):
  "compute the half power beamwidth the pointing accuracy budget and the gain over temperature figure of merit of a spacecraft parabolic antenna"
  intent: "space-systems; spacecraft antenna beamwidth pointing and G/T"
  expected_skill: "space-systems/subsystems/antenna-aperture-sizing"
Task ids: w32-antenna-aperture-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the parabolic antenna
aperture of a spacecraft communications link:" and include the outputs
in the Claim. First tag: antenna-aperture-sizing. Additional tags
ONLY: parabolic-reflector-gain, aperture-efficiency,
required-antenna-gain, half-power-beamwidth, pointing-loss-budget,
gain-over-temperature, spacecraft-antenna-sizing. NEVER single generic
words (antenna, aperture, gain, link, spacecraft, sizing). 50-150
words, <=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): EIRP, free-space path loss,
received power, link margin, data rate budget (communication-link-
budget owns the forward link budget; this leaf takes the required gain
as an input and can reference the link budget only as the source of
the requirement); solar array, battery, thermal (their own leaves).

Tags: [antenna-aperture-sizing, parabolic-reflector-gain,
aperture-efficiency, required-antenna-gain, half-power-beamwidth,
pointing-loss-budget, gain-over-temperature,
spacecraft-antenna-sizing]

Sibling-citation lines for Related leaves:
space-systems/subsystems/communication-link-budget (the forward link
budget that supplies the required-gain input),
space-systems/subsystems/solar-array-sizing (reverse-sizing pattern
precedent), space-systems/subsystems/spacecraft-battery-sizing.

Ledger Standard: ecss.
