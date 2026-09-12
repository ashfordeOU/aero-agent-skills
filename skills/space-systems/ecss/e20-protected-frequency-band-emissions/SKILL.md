---
name: e20-protected-frequency-band-emissions
description: "Use when verify that the emissions of a spacecraft transmitter stay inside the limits protecting radiometric and communication bands under ECSS-E-ST-20C clause 6.3.2.3: categorize each protected band by the service it carries, build the emission set from the carrier, its harmonic series and every declared spurious product, work out how much of each emission falls inside each band from its spectral overlap and its power spectral density, sum the contributions band by band, compare each total against the limit that service carries, and confirm the harmonic sweep reaches the order the applicable radio standard expects. Trigger: ecss, e-st-20c-clause-6-3-2-3, protected-frequency-band, radio-astronomy-band-protection, passive-radiometry-band, spurious-emission-limit, harmonic-emission-suppression, in-band-power-summation, spacecraft-receive-band-protection."
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
  tags: [ecss, e-st-20-electrical-scope, e20-protected-frequency-band-emissions, protected-frequency-band, radio-astronomy-band-protection, passive-radiometry-band, spurious-emission-limit, harmonic-emission-suppression, in-band-power-summation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Protected Frequency Band Emissions (space-systems/ecss/e20-protected-frequency-band-emissions)

Use when the task is the clause 6.3.2.3 emission check of
ECSS-E-ST-20C -- showing that nothing the spacecraft radiates lands on
top of a band that somebody else is protected in, with the numeric
limits themselves coming from the applicable radio standard and the
mission's frequency filing rather than from this clause.

## Domain quick reference

- Protected bands are not one population. A radio astronomy band is
  protected because a receiver on the ground is integrating a signal
  many orders of magnitude below anything a transmitter emits. A
  passive radiometry band is protected because the measurement is the
  natural emission of the atmosphere and there is no way to subtract
  an interferer out of it. A distress and safety band is protected
  because a beacon has to be heard. A navigation band is protected
  because the receiver is correlating at negative signal-to-noise. A
  spacecraft receive band is protected because the victim is the same
  vehicle. Each service carries its own limit, and the band registry
  is what maps a band to its service.
- The emission set is larger than the carrier. It is the carrier, the
  harmonic series up to the order the sweep reaches, and every
  spurious product the equipment declares. A harmonic's power follows
  from the suppression the datasheet states for that order, or from a
  default law when it states none; because it is a multiple of the
  carrier, a harmonic of a modulated signal also occupies a
  proportionally wider bandwidth.
- What matters at a band is not whether an emission is near it but how
  much of the emission is inside it. On a uniform power spectral
  density model the in-band power is the emission power scaled by the
  fraction of its bandwidth that overlaps the band; an emission wholly
  inside contributes all of its power, and one that does not reach the
  band contributes nothing at all.
- Contributions add. A band reached by the third harmonic and by a
  declared spurious product is over its limit if the sum is over, even
  when each contributor on its own is comfortably under. The
  comparison is made in the units the limit is written in, and a total
  that sits exactly on the limit is on it, not over it.

## Workflow

1. Take the protected band registry for the mission -- default edges
   and per-service limits are a starting point, replaced by the values
   the radio standard and the frequency filing impose.
2. Build the emission set: the carrier; every harmonic from the second
   up to the declared sweep order, each with its suppression and its
   widened bandwidth; and every declared spurious product.
3. Report any declared spurious product that is missing a required
   field, and keep it out of the summation rather than guessing at the
   gap.
4. For each emission and each band, compute the spectral overlap and
   the in-band power that follows from it; drop pairs with no overlap.
5. Sum the in-band contributions band by band.
6. Compare each band total against the limit of the service that band
   carries, absorbing representation error exactly on the limit.
7. Confirm the harmonic sweep reached the minimum order; a shallow
   sweep is a finding even when every band it did look at is clean.
8. Aggregate the declaration, band-limit and sweep findings; the
   transmitter respects the protected bands only when all three lists
   are empty.

## Pitfalls

- Checking the carrier only. The carrier is normally placed in an
  allocated band by design; it is the harmonic series and the spurious
  products that land where nobody expected them.
- Comparing each contributor against the limit separately. Two
  emissions each three decibels under the limit put the band exactly
  on it, and a third takes it over.
- Applying the full emission power to a band the emission only partly
  overlaps, which overstates the case, or ignoring the overlap
  entirely because the centre frequency sits outside the band, which
  understates it.
- Stopping the harmonic sweep at the second or third order because the
  first few came out clean; a band several hundred megahertz away is
  reached by the fifth harmonic and not by the second.
- Treating the default suppression law as a measurement. It is a
  placeholder for an order the datasheet is silent on, and a real
  declared value replaces it.
- Reading a band with no contributions as a pass that needed
  computing; it simply was not reached, which is a different statement
  from being under the limit.

## Behavior contract (gate 3)

The band categorization, per-service limit, spectral overlap, in-band
power, harmonic series and suppression, per-band summation, limit
comparison and sweep-depth logic is exercised by the gate 3 contract
test: scripts/test_e20_protected_frequency_band_emissions.py against
scripts/e20_protected_frequency_band_emissions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_protected_frequency_band_emissions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
