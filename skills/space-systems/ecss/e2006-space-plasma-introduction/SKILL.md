---
name: e2006-space-plasma-introduction
description: "Use when evaluate the space-plasma-environment a spacecraft flies through under ECSS-E-ST-20-06C clause 4.1.1 and the spacecraft-charging risks it creates: compute the debye-length and the electron-thermal-flux from ambient electron-density and electron-temperature, categorize the ambient population as cold-ionospheric, warm-magnetospheric, hot-substorm or energetic-electron, decide whether the body sits in a thin-sheath or a thick-sheath regime against its characteristic-length, derive the surface-charging and internal-charge-deposition risk families that follow, and estimate the frame-potential build-up timescale. Trigger: ecss, e-st-20-electrical-scope, e2006-space-plasma-introduction, space-plasma-environment, debye-length, electron-thermal-flux, thick-sheath-regime, hot-substorm-plasma, energetic-electron-population, spacecraft-charging-risk."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-space-plasma-introduction, space-plasma-environment, debye-length, electron-thermal-flux, thick-sheath-regime, hot-substorm-plasma, energetic-electron-population, spacecraft-charging-risk]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Space Plasma Introduction (space-systems/ecss/e2006-space-plasma-introduction)

Use when the task is the entry point of ECSS-E-ST-20-06C clause 4.1.1 --
what the ambient space-plasma actually is at the orbit under study, which
plasma regime the spacecraft body sits in, and which families of
spacecraft-charging risk that regime puts on the table. The detailed
physical mechanisms and the mitigation programme are separate leaves; this
one turns an environment record into a regime and a risk shortlist.

## Domain quick reference

- A space-plasma population is described for this purpose by two numbers:
  the ambient electron-density (particles per cubic metre) and the
  electron-temperature expressed as an energy in electronvolts. Everything
  downstream -- shielding distance, collected flux, regime, risk family --
  is derived from that pair plus the size of the body.
- The debye-length is the distance over which the plasma screens an
  imposed potential. With the electron-temperature in electronvolts it
  follows from the permittivity of free space, that temperature and the
  density; it is millimetres in the dense cold ionosphere and hundreds of
  metres in the tenuous hot magnetosphere. The same pair fixes the
  electron-thermal-flux -- one quarter of the density times the mean
  thermal speed times the elementary charge -- which is the current a
  surface collects from the ambient population.
- The regime is the ratio of debye-length to the characteristic-length of
  the body. When the screening distance is far smaller than the body the
  sheath is thin and hugs the surface; when it is comparable to or larger
  than the body the sheath is thick and orbit-limited collection applies.
  Between the two the regime is transitional and neither limit is safe to
  assume.
- Population categories drive different risk families. A cold-ionospheric
  population (sub-electronvolt, dense) does not charge a body to hazardous
  absolute potentials but drives ram-wake potential asymmetry and, on a
  high-voltage-array, arcing through the thin sheath. A warm-magnetospheric
  population raises auroral frame-potential excursions. A hot-substorm
  population of kiloelectronvolt electrons is the classic
  surface-charging driver, producing both absolute frame-potential
  excursions and differential potentials between adjacent surfaces. An
  energetic-electron population above roughly a hundred kiloelectronvolts
  penetrates the outer skin and drives internal-charge-deposition and
  buried-charge breakdown instead.
- The build-up timescale of a frame potential is the stored charge divided
  by the collected current: body capacitance times the target potential,
  over collected current density times area. It separates a regime that
  charges in seconds from one that never reaches the potential of concern
  inside an eclipse pass.

## Workflow

1. Normalise the environment record: name, electron-density,
   electron-temperature, characteristic-length, and the optional flags for
   a high-voltage-array and for eclipse exposure. Reject a non-positive
   density, temperature or length -- none of the derived quantities is
   defined there.
2. Compute the debye-length and the electron-thermal-flux from the density
   and temperature pair.
3. Categorize the population by electron-temperature band:
   cold-ionospheric, warm-magnetospheric, hot-substorm, or
   energetic-electron. A value sitting exactly on a band edge belongs to
   the upper band, and the comparison absorbs representation error so a
   product or quotient landing a few units in the last place low does not
   fall into the wrong band.
4. Determine the sheath regime from the ratio of debye-length to
   characteristic-length: thin-sheath well below the body scale,
   thick-sheath at or above it, transitional between.
5. Derive the risk families from the population, the regime and the flags,
   returning a sorted, de-duplicated set so two populations that raise the
   same risk do not double-count it.
6. Where a capacitance and a potential of concern are known, estimate the
   build-up timescale and compare it against the exposure duration of the
   orbit segment before declaring a risk credible.
7. Across a set of records, pick the worst case by electron-temperature
   (density breaking a tie) and union the risk families for the mission.

## Pitfalls

- Reading a dense plasma as a severe charging environment -- density sets
  the collected current, not the potential; it is the electron-temperature
  band that decides whether hazardous potentials are reachable at all.
- Applying thin-sheath collection everywhere because it is the familiar
  low-orbit case -- in a tenuous hot plasma the debye-length exceeds the
  body and the collection law changes, so the current estimate is wrong in
  the direction that matters.
- Treating surface-charging and internal-charge-deposition as one risk --
  they are driven by different parts of the spectrum, and a population
  that produces one may produce none of the other.
- Ignoring the build-up timescale and declaring every hot-plasma pass a
  hazard -- with a large capacitance and a weak collected current the
  potential of concern may never be reached inside the exposure window.
- Letting a band-edge comparison decide by raw floating-point ordering --
  an electron-temperature computed as a product can land a few units in
  the last place below a band edge and be categorized one band too low.

## Behavior contract (gate 3)

The debye-length, electron-thermal-flux, population categorization, sheath
regime, risk-family derivation, build-up timescale and worst-case roll-up
are exercised by the gate 3 contract test:
scripts/test_e2006_space_plasma_introduction.py against
scripts/e2006_space_plasma_introduction_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2006_space_plasma_introduction.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
