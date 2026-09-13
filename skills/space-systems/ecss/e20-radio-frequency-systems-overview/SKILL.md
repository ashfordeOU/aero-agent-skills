---
name: e20-radio-frequency-systems-overview
description: "Use when compute and cross-check the radio-frequency chain introduced by ECSS-E-ST-20C clause 7.1: place every element into transmitter-chain, receiver-chain, antenna or transmission-line and confirm no family is left unpopulated, derive effective-isotropic-radiated-power from transmitter output, feeder-loss and antenna-gain, add free-space-path-loss over the slant-range at the carrier frequency, convert the voltage-standing-wave-ratio of each guided-wave interface into mismatch-loss, form the receiver figure-of-merit and the carrier-to-noise-density it yields, then compare that against the density the data-rate and the required-energy-per-bit demand before declaring the link-margin. Trigger: ecss, e-st-20-electrical-scope, e20-radio-frequency-systems-overview, radio-frequency-chain, transmitter-receiver-chain, transmission-line-mismatch, free-space-path-loss, carrier-to-noise-density, link-margin-budget."
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
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e20-radio-frequency-systems-overview, radio-frequency-chain, transmitter-receiver-chain, transmission-line-mismatch, free-space-path-loss, carrier-to-noise-density, link-margin-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Radio-Frequency Systems Overview (space-systems/ecss/e20-radio-frequency-systems-overview)

Use when the task is the introductory radio-frequency description of
ECSS-E-ST-20C clause 7.1 -- naming the four equipment families that make
up a radio-frequency system, confirming the chain from transmitter to
receiver is unbroken, and running the overview-level link budget that
the families imply.

## Domain quick reference

- Clause 7.1 introduces a radio-frequency system as four families, each
  of which must carry at least one element before the system is
  describable end to end. The transmitter-chain modulates and raises the
  carrier (modulator, up-converter, solid-state or travelling-wave-tube
  amplifier). The receiver-chain selects and recovers it (pre-selection
  filter, low-noise amplifier, down-converter, demodulator). The antenna
  couples the guided wave to free space at each end (reflector, horn,
  patch-array, helix). The transmission-line carries the guided wave
  between equipment and antenna (coaxial cable, rectangular waveguide,
  microstrip line, rotary joint). An element that belongs to none of
  these is rejected rather than absorbed into the nearest family.
- The overview-level arithmetic is the link budget. Effective isotropic
  radiated power is the transmitter output less the transmit feeder
  attenuation plus the transmit antenna-gain; the feeder sits between
  amplifier and antenna, so its loss is subtracted, never added.
  Free-space-path-loss grows as twenty times the logarithm of the
  product of slant-range and carrier frequency -- doubling either adds
  about six decibels.
- Every guided-wave interface reflects part of the incident wave. The
  voltage-standing-wave-ratio gives the reflection magnitude as its
  excess over unity divided by its sum with unity, and the mismatch-loss
  is the decibel shortfall of the transmitted fraction. A ratio of one
  is a perfect match and costs nothing; a ratio below one is not
  physical and is rejected.
- The receiving end is characterised by its figure-of-merit -- receive
  antenna-gain less receive feeder attenuation less ten times the
  logarithm of the system noise temperature. The carrier-to-noise
  density available is the received carrier level above the noise
  density, and the density required is the energy-per-bit ratio the
  modulation and coding demand plus ten times the logarithm of the
  data-rate plus any implementation shortfall. The difference is the
  link-margin, and the house minimum at overview level is three
  decibels.

## Workflow

1. Inventory the radio-frequency elements and place each one in exactly
   one family: transmitter-chain, receiver-chain, antenna or
   transmission-line. Reject an unrecognised element type before the
   system is assessed.
2. Check every family is populated. An empty family means the chain has
   a gap the overview cannot describe, and the link budget that follows
   would rest on an element nobody has named.
3. Compute the effective-isotropic-radiated-power from transmitter
   output, transmit feeder attenuation and transmit antenna-gain.
4. Compute the free-space-path-loss from the slant-range and the carrier
   frequency, and the mismatch-loss implied by the
   voltage-standing-wave-ratio at the transmit and receive guided-wave
   interfaces.
5. Compute the received carrier level: radiated power less path loss and
   mismatch losses, plus receive antenna-gain, less receive feeder
   attenuation.
6. Form the receiver figure-of-merit and the carrier-to-noise density it
   yields, and the density the data-rate and the required
   energy-per-bit ratio demand.
7. Take the link-margin as the difference and hold it against the
   minimum. The overview is consistent only when the family findings and
   the interface and margin findings are all empty; the computed figures
   are reported alongside them for the design report.

## Pitfalls

- Adding the feeder attenuation to the transmitter output instead of
  subtracting it. The feeder sits between the amplifier and the antenna,
  so the radiated power is always below the amplifier output, and a sign
  error here flatters the whole budget by twice the feeder loss.
- Treating the voltage-standing-wave-ratio as a loss in decibels. It is
  a dimensionless ratio; the decibel penalty is the mismatch-loss
  derived from it, and a ratio of two costs about half a decibel, not
  two.
- Using ten times the logarithm for the free-space-path-loss. The
  spreading term is a squared dependence on both range and frequency, so
  the coefficient is twenty; using ten halves every path loss in the
  budget.
- Reading a populated element list as a complete chain. Four amplifiers
  and a waveguide still leave the receiver-chain and the antenna family
  empty; the check is one element per family, not a count.
- Comparing the received carrier level directly with a required
  energy-per-bit ratio. The two are not the same quantity -- the
  data-rate and the noise density must be brought in first, or the
  comparison is dimensionally meaningless.

## Behavior contract (gate 3)

The element-family placement, chain-completeness, effective isotropic
radiated power, free-space path loss, mismatch loss, received carrier
level, figure-of-merit, carrier-to-noise density, required density,
link-margin and aggregate system review logic is exercised by the gate 3
contract test: scripts/test_e20_radio_frequency_systems_overview.py
against scripts/e20_radio_frequency_systems_overview_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_radio_frequency_systems_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
