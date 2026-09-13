---
name: e20-reflector-material-properties
description: "Use when compute the reflective behaviour of a reflector-antenna surface material or composite laminate and the resulting antenna impact under ECSS-E-ST-20C clause 7.2.2.3.2: categorize the reflecting surface as a metallic sheet, metallised composite, metallised membrane, bare-carbon-composite or knitted-metal-mesh, derive the skin-depth and confirm any metallisation is thick enough to stop through-coating leakage, turn the material conductivity into a radio-frequency surface-resistance and an ohmic-reflection-loss, model mesh-leakage from the cell-opening and the wire-radius, convert thermoelastic distortion into a surface-rms-error and its Ruze gain-loss, and compare the summed reflector-efficiency-loss against its allocation. Trigger: ecss, e-st-20-electrical-scope, e-st-20c-clause-7-2-2-3-2, reflector-material-properties, reflector-surface-resistance, ohmic-reflection-loss, knitted-metal-mesh-leakage, metallisation-skin-depth, ruze-surface-error-loss."
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
  tags: [ecss, e-st-20-electrical-scope, e20-reflector-material-properties, reflector-surface-resistance, ohmic-reflection-loss, knitted-metal-mesh-leakage, metallisation-skin-depth, ruze-surface-error-loss, reflector-efficiency-loss]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Reflector Material Properties (space-systems/ecss/e20-reflector-material-properties)

Use when the task is the clause 7.2.2.3.2 reflector-material step of
ECSS-E-ST-20C -- quantifying how well the chosen reflecting surface,
metal sheet or composite laminate or knitted mesh, actually reflects at
the operating frequency, and converting that material behaviour into
the loss and the surface error the antenna prediction has to carry.

## Domain quick reference

- The reflecting surface is categorized once into a material family,
  and the family decides which checks apply. A metallic sheet reflects
  from bulk metal. A metallised composite or a metallised membrane
  reflects from a thin deposited layer on a substrate that is itself a
  poor conductor, so the layer thickness is a radio-frequency
  parameter, not a process detail. A bare-carbon-composite reflects
  from a laminate whose conductivity is orders below a metal, so its
  loss must be quantified rather than assumed negligible. A
  knitted-metal-mesh reflects from a woven grid and leaks through its
  openings. A material outside the families is rejected.
- Skin-depth sets the metallisation rule. Current flows in a layer
  whose depth falls with the square root of frequency and of
  conductivity, so a deposited coating has to be several skin-depths
  thick before the substrate stops participating; a coating thinner
  than that leaks and its measured reflectivity will not match the
  bulk-metal prediction, most visibly at the low end of the band where
  the skin-depth is largest.
- Ohmic-reflection-loss follows from the radio-frequency
  surface-resistance, itself the square root of the ratio of frequency
  times permeability to conductivity. The absorbed fraction is a small
  multiple of that resistance against the free-space wave impedance,
  so a good conductor absorbs a few hundredths of a decibel per bounce
  and a poor one a measurable fraction. The relation used here is the
  good-conductor approximation, and it stops being meaningful once the
  absorbed fraction approaches unity.
- Mesh-leakage is a grid problem, not a conductivity problem. The
  woven grid behaves as a shunt inductive sheet whose normalised
  reactance grows with the cell-opening in wavelengths and with the
  logarithm of the opening over the wire-radius, so leakage rises
  steeply as the operating frequency climbs toward the cell size. Once
  the opening is no longer electrically small the grid model is no
  longer the right physics.
- Thermoelastic distortion converts the same material choice into a
  surface-rms-error, and that error costs gain by the Ruze relation,
  which grows with the square of the error in wavelengths. This is why
  a low-expansion laminate can beat a better conductor: the conduction
  term is hundredths of a decibel and the surface-error term is
  tenths. The two, plus mesh-leakage where it applies, sum into the
  reflector-efficiency-loss compared against the allocation.

## Workflow

1. Categorize the reflecting surface into its material family; reject
   a material outside the family set.
2. Take the family conductivity and compute the skin-depth at the
   lowest frequency in the band; for a metallised family, compare the
   deposited thickness against the required number of skin-depths.
3. Convert conductivity into the radio-frequency surface-resistance
   and then into the ohmic-reflection-loss at the working incidence
   angle.
4. For a knitted-metal-mesh, compute the leakage loss from the
   cell-opening, the wire-radius and the wavelength; confirm the
   opening is still electrically small.
5. Convert the material expansion coefficient, the thermal excursion
   and the reflector characteristic length into a surface-rms-error,
   and that error into a Ruze gain-loss.
6. Sum the conduction, leakage and surface-error terms into the
   reflector-efficiency-loss and compare it against the allocation.
7. Aggregate the findings; the reflecting surface is acceptable only
   when the list is empty.

## Pitfalls

- Reading a datasheet direct-current conductivity as the
  radio-frequency behaviour of a metallised surface. At microwave
  frequencies only a few micrometres of the layer carry current, so a
  coating that measures well with a four-point probe can still be
  transparent to the wave.
- Checking coating thickness at the top of the band. Skin-depth is
  largest at the lowest frequency, so the low edge is the sizing case.
- Treating a bare-carbon-composite reflecting surface as a metal with
  a small correction. Its conductivity sits orders below aluminium and
  the loss it adds is a real term in the budget.
- Judging a knitted-metal-mesh by its wire conductivity. The dominant
  term is geometric leakage through the openings, so a finer weave of
  a worse metal usually reflects better than a coarse weave of a
  better one.
- Comparing a surface-rms-error against a fixed millimetre figure
  taken from another programme. The Ruze penalty depends on the error
  in wavelengths, so the same physical surface is excellent in one
  band and unusable two octaves up.
- Adding the loss terms as efficiencies in percent and reporting the
  answer in decibels. The terms multiply as efficiencies and add as
  decibels; mixing the two understates the total.

## Behavior contract (gate 3)

The material-family categorization, skin-depth and metallisation
thickness, surface-resistance, ohmic-reflection-loss, mesh-leakage,
thermoelastic surface-rms-error, Ruze gain-loss and
reflector-efficiency-loss allocation logic is exercised by the gate 3
contract test: scripts/test_e20_reflector_material_properties.py
against scripts/e20_reflector_material_properties_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_reflector_material_properties.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
