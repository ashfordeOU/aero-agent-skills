---
name: communication-link-budget
description: "Use when you must build or check a spacecraft communications link budget: compute the free space path loss from distance and frequency, derive EIRP from transmit power and antenna gain, estimate received power and carrier to noise density ratio, and verify the link margin against the required energy per bit to noise ratio at the data rate. Produces path loss, EIRP, received power, C/N0, Eb/N0, and the margin verdict that closes the link. Trigger: link budget, path loss, eirp, carrier to noise density, eb n0, link margin, data rate, spacecraft communications."
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
  subdomain: subsystems
  tags: [communication-link-budget, eirp, free-space-path-loss, c-n0, eb-n0, link-margin, data-rate, spacecraft-communications]
  version: 0.1.0
  author: AeroSkills
---

# Spacecraft Communication Link Budget (space-systems/subsystems/communication-link-budget)

Use when the task is a spacecraft communications link budget: Friis
free-space path loss, EIRP, received power, carrier to noise density
ratio, and the Eb/N0 margin at the data rate.

Units convention (stated once): power and EIRP in dBW, gains and
losses in dB, distance in meters, frequency in hertz, noise
temperature in kelvin, data rate in bits per second, C/N0 in dB-Hz,
Eb/N0 and margin in dB. No Watt/dBW mixing anywhere.

## Domain quick reference

- Free-space path loss: L_fs = 20*log10(4*pi*d/lambda) dB, where
  lambda = c/f with c = 299792458 m/s; doubling distance or frequency
  adds about 6 dB of loss.
- EIRP (dBW) = transmit power (dBW) + transmit antenna gain (dB).
- Received power: Pr = EIRP + Gr - L_fs - L_other (dBW), where other
  losses lump atmospheric, pointing, and polarization effects.
- Carrier to noise density: C/N0 = Pr + 228.6 - 10*log10(T) dB-Hz
  (228.6 is 10*log10(1/k) with k = 1.380649e-23 J/K); doubling the
  system noise temperature costs 3 dB.
- Eb/N0 = C/N0 - 10*log10(R); the required Eb/N0 comes from the
  modulation and coding scheme, and the margin is the difference.
- ECSS-E-ST-50C (communications) sets the European baseline for space
  data link budgets; ECSS standards are free to download from
  https://ecss.nl/standards/ (name + paraphrase + link only).

## Workflow

1. Set the link geometry: slant distance (m) and carrier frequency
   (Hz); compute free_space_path_loss.
2. Combine transmit power (dBW) and antenna gain (dB) with
   eirp_dbw.
3. Add the receive gain and subtract path and other losses with
   received_power_dbw.
4. Convert received power to carrier to noise density with the
   system noise temperature: cno_db_hz.
5. Close the budget with link_margin at the data rate against the
   required Eb/N0; treat ok False as a design failure, not a
   rounding error.

## Pitfalls

- Mixing watts and dBW in one chain; convert transmit power to dBW
  once, then keep everything in dBW.
- Feeding kilometers or gigahertz into the Friis formula without
  converting to meters and hertz.
- Dropping other losses (pointing, polarization, atmospheric) and
  calling a paper link closed.
- Checking the margin at the wrong data rate; 10*log10(R) is the
  per-bit penalty.
- Accepting a negative margin because the raw C/N0 still looks
  large.

## Behavior contract (gate 3)

The path loss, EIRP, received power, C/N0, and margin logic is
exercised by the gate 3 contract test:
scripts/test_link_budget_logic.py against scripts/link_budget_logic.py
(stdlib unittest, offline). Run from the repo root:
python3 skills/space-systems/subsystems/communication-link-budget/scripts/test_link_budget_logic.py

## Compliance

- Standards referenced, not reproduced: ECSS standards are freely
  downloadable (copyright ESA); summary-only per standards-map.yaml
  and brief 06.
- compliance: STANDARDS-REF, gated: false.
