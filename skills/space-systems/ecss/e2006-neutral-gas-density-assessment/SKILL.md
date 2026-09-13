---
name: e2006-neutral-gas-density-assessment
description: "Use when estimate the induced plasma-density around a vehicle caused by propulsion gas release under ECSS-E-ST-20-06C clause 11.3.5: expand every release into the free-molecular far field with a cosine-law plume model, evaluate the neutral-number-density at each observation point, convert the electron-impact ionized share into an induced electron-density, add the ambient-plasma background, and check the resulting electron-plasma-frequency and Debye-length against the plasma-density-limit and radio-frequency-headroom held for that point while confirming the Knudsen-number still supports the free-molecular expansion. Trigger: ecss, e-st-20-electrical-scope, e2006-neutral-gas-density-assessment, neutral-gas-density, induced-plasma-density, propulsion-gas-release, plume-expansion-model, electron-plasma-frequency, knudsen-number-regime, debye-length."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-neutral-gas-density-assessment, neutral-gas-density, induced-plasma-density, propulsion-gas-release, plume-expansion-model, electron-plasma-frequency, debye-length]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Scope — Neutral Gas Density Assessment (space-systems/ecss/e2006-neutral-gas-density-assessment)

Use when the task is the induced-environment estimate of ECSS-E-ST-20-06C
clause 11.3.5 -- turning the gas a propulsion system releases into a
neutral-number-density and an induced electron-density around the vehicle,
and checking that density against the limits the affected points carry.

## Domain quick reference

- Clause 11.3.5 concerns the plasma a vehicle makes for itself. Every
  propulsion-related release contributes: an electric-thruster-plume,
  a chemical-thruster-plume, a cold-gas-vent and a propellant-leak all
  put neutrals into the volume, and they differ by orders of magnitude
  in how readily those neutrals become an ion-electron pair.
- The far-field neutral-number-density of a release follows from three
  quantities: the particle-emission-rate (mass flow divided by the
  particle mass of the species), the angular distribution of the plume,
  and the inverse-square range to the observation point. The angular
  distribution is a cosine-law whose exponent is fixed by the declared
  plume half-angle, normalized so the distribution integrates to one
  over the forward hemisphere; nothing is released behind the
  exit-plane.
- Ionization is an electron-impact process, so the converted share
  depends on the ionization-potential of the species measured against
  the local electron-temperature, on the dwell time of the neutral in
  the ionizing region, and on a ceiling fixed by the release mechanism.
  A high-potential species in a cool plasma converts a negligible share;
  a low-potential species in a hot plume approaches its ceiling.
- The induced electron-density is that converted share plus the ambient
  plasma background. From it follow the two quantities the rest of the
  vehicle cares about: the electron-plasma-frequency, which must sit
  below any carrier a radio-frequency link uses with a stated headroom
  factor, and the Debye-length, which sets the scale over which a
  charged surface is shielded.
- The whole far-field expansion assumes collisionless flow. The
  Knudsen-number, the mean-free-path over the characteristic length,
  decides whether that assumption holds: free-molecular well above ten,
  collision-dominated continuum well below a hundredth, transitional
  between. Near a nozzle the flow is not free-molecular and the model
  does not apply.

## Workflow

1. Validate every release source: resolve the species and the release
   mechanism, require a positive mass flow and exit velocity, and
   require a plume half-angle strictly inside the open interval between
   zero and ninety degrees. Reject an unrecognized species or mechanism
   before it enters the assessment.
2. Convert each mass flow into a particle-emission-rate using the
   particle mass of its species, and derive the cosine-law exponent that
   reproduces the declared half-angle at half the on-axis value.
3. For each observation point, evaluate the neutral-number-density
   contributed by every release from the emission rate, the normalized
   angular factor at the field angle of the point, the exit velocity and
   the inverse-square range. A point behind the exit-plane of a release
   receives nothing from it and is dropped for that pair.
4. Compute the dwell time of the neutrals out to the point, then the
   ionized share for the species and mechanism at the local
   electron-temperature, and multiply to obtain the electron-density
   each release contributes.
5. Sum those contributions, add the ambient plasma background, and
   derive the electron-plasma-frequency and the Debye-length.
6. Check the summed density against the plasma-density-limit on record,
   and the plasma frequency raised by its headroom factor against any
   carrier frequency declared at the point. Flag an exceedance; flag
   separately a point that propulsion gas reaches but which carries no
   limit at all.
7. Check the Knudsen-number at the point. Flag a transitional or
   continuum result, because the free-molecular expansion that produced
   the density is then outside its validity.
8. Aggregate across the vehicle: report the worst point and treat the
   assessment as closed only when no point carries a finding.

## Pitfalls

- Applying the far-field inverse-square expansion close to a nozzle.
  The model is collisionless by construction; inside the collisional
  core it returns a density that is both wrong and unflagged unless the
  Knudsen-number is evaluated and acted on.
- Reporting only the neutral-number-density and calling the clause
  satisfied. The clause asks for the plasma the release induces, so the
  ionized share and the ambient background both have to be carried
  through to an electron-density.
- Using one ionized share for every release. An electric-thruster-plume
  and a cold-gas-vent differ by four or more orders of magnitude in
  converted fraction, so a single value either buries the plume
  contribution or invents one for the vent.
- Ignoring the ambient plasma background. At a point far from every
  release the ambient term dominates, and omitting it makes a
  radio-frequency check pass that the real environment fails.
- Comparing the raw plasma frequency with the carrier and declaring a
  link clear. A link needs headroom above the plasma frequency, not
  equality with it, so the margin factor belongs inside the comparison.
- Leaving the plasma-density-limit unset and reading "no exceedance" as
  compliance. An absent limit means the owning requirement was never
  captured for that point; that is itself a finding, not a pass.

## Behavior contract (gate 3)

The release-validation, plume-expansion, ionized-share, plasma-frequency,
Debye-length, flow-regime and limit-comparison logic is exercised by the
gate 3 contract test:
scripts/test_e2006_neutral_gas_density_assessment.py against
scripts/e2006_neutral_gas_density_assessment_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_neutral_gas_density_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
