---
name: e20-plastic-antenna-dielectric-losses
description: "Use when compute the dielectric loss that plastic parts add in the radio-frequency-power-path of a spacecraft antenna under ECSS-E-ST-20C clause 7.2.2.4.3: categorize each part as a radome, a lens, a matching layer, a waveguide window, a feed-support insulator or a structural item sitting outside the field, derive the attenuation constant from the relative permittivity and loss-tangent at the operating frequency, stretch the refracted path by the incidence angle, cascade the insertion-loss of the chain against the allocated radio-frequency-path budget, convert each dissipated fraction into a temperature rise through the part thermal-resistance, and reject a part driven past its maximum-use-temperature. Trigger: ecss, e-st-20c-clause-7-2-2-4-3, plastic-part-dielectric-loss, loss-tangent-attenuation, radome-insertion-loss, dielectric-interface-mismatch, dissipated-radio-frequency-heating, maximum-use-temperature-check."
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
  tags: [ecss, e-st-20-electrical-scope, e20-plastic-antenna-dielectric-losses, plastic-part-dielectric-loss, loss-tangent-attenuation, radome-insertion-loss, dielectric-interface-mismatch, dissipated-radio-frequency-heating, maximum-use-temperature-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Plastic Antenna Dielectric Losses (space-systems/ecss/e20-plastic-antenna-dielectric-losses)

Use when the task is the clause 7.2.2.4.3 concern of ECSS-E-ST-20C --
what a plastic part standing in the transmitted field takes out of the
chain, and whether what it absorbs cooks the part itself.

## Domain quick reference

- Only the parts the field actually crosses belong in the budget. A
  radome, a lens, a matching layer, a waveguide window and a
  feed-support insulator sit in the field; a structural bracket or a
  harness standoff outside the aperture does not, and carries neither
  an insertion-loss nor a heating consequence. Categorizing the parts
  first is what stops a shrouded bracket from being budgeted and a
  window from being forgotten.
- A low-loss plastic attenuates in proportion to the square root of
  its relative permittivity and to its loss-tangent, and inversely to
  the free-space wavelength. The frequency dependence is what catches
  designs out: the same window that is invisible at C-band takes real
  decibels at Ka-band because the attenuation constant scales linearly
  with frequency while the part thickness stays put.
- The geometric thickness is not the path. A wave arriving at an angle
  refracts into the slab and travels further inside it than the
  thickness suggests, the bending being weaker the denser the
  material. The absorbed path is the refracted one.
- Two different things take level out of the chain and they must not be
  merged. Absorption turns into heat inside the part; interface
  mismatch at an untuned slab reflects back towards the source and
  never becomes heat. Both count against the insertion-loss budget,
  only the first feeds the thermal check -- and a part deliberately
  matched (a tuned matching layer, a half-wave window) carries the
  absorption without the mismatch.
- The heat is a part-level limit, not a chain-level one. What a part
  absorbs raises it above its mounting interface through its own
  thermal-resistance, and the resulting temperature is checked against
  the maximum-use-temperature of the plastic. Each part downstream
  sees a lower level than the one before it, so the chain has to be
  walked in order rather than assessed part by part at the transmitter
  level.

## Workflow

1. Categorize every plastic part in the assembly and drop the ones
   outside the radiating field. Reject an unrecognised family before it
   enters the budget.
2. For each in-field part, derive the attenuation constant from its
   relative permittivity and loss-tangent at the operating frequency.
3. Turn the thickness into a refracted path using the incidence angle
   and the material index, then convert that path into an absorption
   loss.
4. Add the interface mismatch of the slab unless the part is declared
   impedance-matched, and keep the two terms separately: the sum is the
   insertion-loss of the part, the absorption alone is its heat.
5. Cascade the level down the chain, so each part is assessed at the
   level actually reaching it rather than at the transmitter output.
6. Convert what each part absorbs into a temperature rise through its
   thermal-resistance, add the baseline interface temperature and
   compare against the maximum-use-temperature of the material.
7. Sum the insertion-loss of the chain and compare against the
   allocated radio-frequency-path budget. The assembly is compliant
   only when the chain is inside its allocation and no part is above
   its temperature limit.

## Pitfalls

- Budgeting the mismatch as heat. An untuned slab reflects a large
  share of what it removes from the chain straight back towards the
  source; counting that as dissipation inflates the temperature rise,
  sometimes by an order of magnitude on a thin low-loss radome where
  the mismatch dominates the loss entirely.
- Reusing a qualified part at a higher frequency. The attenuation
  constant is proportional to frequency, so a part accepted in one band
  is not accepted two bands up without a fresh number.
- Taking the geometric thickness as the absorbed path. At oblique
  incidence the refracted path is longer, and the error grows with the
  angle -- the normal-incidence figure is optimistic everywhere off
  boresight.
- Assessing each part at the transmitter level. A chain of parts is
  cascaded: the second sees what the first passed, and budgeting them
  all at the input level overstates both the loss and the heating of
  everything downstream.
- Closing the assessment on the chain loss alone. The chain can be
  comfortably inside its allocation while one thin, thermally isolated
  part sits above its maximum-use-temperature; the temperature check is
  per part and independent of the budget.
- Letting a part exactly on its temperature limit fail on rounding. The
  reached temperature is a baseline plus a product of a dissipated
  fraction and a resistance, so a compliant part can land a few units in
  the last place above the limit; the check absorbs that representation
  error rather than the limit being raised.

## Behavior contract (gate 3)

The part categorization, attenuation constant, refracted path,
absorption and mismatch split, cascaded chain walk and
maximum-use-temperature check are exercised by the gate 3 contract
test: `scripts/test_e20_plastic_antenna_dielectric_losses.py` against
`scripts/e20_plastic_antenna_dielectric_losses_logic.py` (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e20_plastic_antenna_dielectric_losses.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
