---
name: e2006-plasma-instrument-spacecraft-provisions
description: "Use when determine the extra electrostatic-cleanliness provisions a science spacecraft owes its plasma-measurement instruments under ECSS-E-ST-20-06C clause 6.7: categorize each instrument by the lowest particle-energy it measures, compute the measurement distortion that the spacecraft-floating-potential and the local differential-potential impose on that energy, check the conductive-surface coverage and potential uniformity of the exposed outer skin, size the boom that places a field probe beyond the photoelectron-sheath in debye-length units, and decide whether an active-potential-control emitter is needed and at what emission-current. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c, plasma-instrument-provisions, electrostatic-cleanliness, spacecraft-floating-potential, active-potential-control, debye-length-boom, photoelectron-sheath, low-energy-particle-measurement."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-plasma-instrument-spacecraft-provisions, e-st-20-06c, plasma-instrument-provisions, electrostatic-cleanliness, spacecraft-floating-potential, active-potential-control, debye-length-boom, photoelectron-sheath]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Spacecraft Provisions for Plasma Instruments (space-systems/ecss/e2006-plasma-instrument-spacecraft-provisions)

Use when the task is the clause 6.7 add-on of ECSS-E-ST-20-06C: a
science mission carries instruments that measure the ambient plasma
itself, so the spacecraft becomes part of the instrument. The baseline
charging-control provisions of the standard protect hardware from
discharge; this clause adds the provisions that protect the
measurement from the spacecraft.

## Domain quick reference

- A plasma instrument is sensitive to the spacecraft-floating-potential
  because that potential accelerates or retards every charged particle
  before it reaches the aperture. The distortion that matters is
  relative: the shift equals the magnitude of the potential in volts
  divided by the lowest particle-energy in electronvolts the
  instrument is specified to measure. A 5 V body potential is
  negligible for a 30 keV electron-spectrometer and destroys a 2 eV
  thermal-ion channel.
- Differential-potential across the outer skin matters separately from
  the body potential. A dielectric patch inside the field-of-view of
  an aperture, or within a boom-mounted probe's near field, bends
  low-energy trajectories and creates a local sheath the instrument
  cannot deconvolve. The provision is an electrostatically-clean
  surface: a high conductive-surface coverage fraction of the exposed
  outer area, all of it bonded to a common electrical reference, and a
  tight uniformity limit on the residual surface-potential spread.
- A field probe or Langmuir probe must sit outside the body's
  photoelectron-sheath. The sheath scale is the local debye-length, so
  boom length is specified in debye-length multiples plus the physical
  photoelectron-cloud extent; a boom that satisfies the multiple but
  ends inside the photoelectron cloud is still short.
- Where the passive design cannot hold the body potential inside the
  instrument's tolerance, an active-potential-control device (an ion
  or electron emitter, or a plasma contactor) is required. Its
  emission-current is sized from the net current the spacecraft
  collects at the uncontrolled potential, with a control margin; a
  device sized below the net collected current cannot move the
  potential at all.
- Provisions are per instrument and then unioned into one mission
  requirement set. The driving instrument is the one with the lowest
  measured particle-energy, because it sets the tightest potential and
  uniformity limits for the whole spacecraft.

## Workflow

1. Categorize each payload instrument: an unrecognized instrument kind
   is rejected, and a kind outside the plasma-measurement family adds
   no clause 6.7 provision.
2. Read the lowest measured particle-energy per instrument; reject a
   non-positive energy. Derive the tolerable body potential and the
   tolerable differential-potential from that energy and the
   instrument's distortion allowance.
3. Compute the distortion each candidate design potential imposes on
   each instrument, and flag every instrument whose allowance is
   exceeded.
4. Check the outer skin: conductive-surface coverage fraction against
   the mission requirement, common-reference bonding of every
   conductive area, and the surface-potential spread against the
   uniformity limit. Treat an exact match on any limit as compliant,
   absorbing floating-point representation error with a named
   tolerance rather than relaxing the limit.
5. Size each probe boom: required length is the debye-length multiple
   for the instrument plus the photoelectron-cloud extent, and the
   installed boom is short when it falls below that.
6. Decide active-potential-control: required when the passive body
   potential exceeds the driving instrument's tolerance; if required,
   size the emission-current from the net collected current times the
   control margin and compare it with the device capability.
7. Union the per-instrument provisions into the mission set and report
   the open ones; the mission is compliant only when that list is
   empty.

## Pitfalls

- Judging the body potential against an absolute volt limit instead of
  against the lowest measured particle-energy — the same potential is
  harmless on one instrument and disqualifying on another.
- Treating a conductive coating as electrostatically clean without
  checking that every conductive area is bonded to the common
  reference; an unbonded conductive patch floats and behaves like the
  dielectric it replaced.
- Sizing a boom on debye-length multiples alone and ignoring the
  photoelectron cloud, which does not scale with the debye-length.
- Sizing an emitter from the wanted potential change rather than from
  the net collected current: a device below that current cannot shift
  the potential regardless of its voltage rating.
- Applying the provisions only to the instrument that requested them,
  when the driving instrument's limits are spacecraft-level and bind
  every exposed surface.

## Behavior contract (gate 3)

The instrument categorization, distortion computation, surface
electrostatic-cleanliness check, boom sizing, emitter sizing and
mission-level union logic is exercised by the gate 3 contract test:
`scripts/test_e2006_plasma_instrument_spacecraft_provisions.py`
against
`scripts/e2006_plasma_instrument_spacecraft_provisions_logic.py`
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_plasma_instrument_spacecraft_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
