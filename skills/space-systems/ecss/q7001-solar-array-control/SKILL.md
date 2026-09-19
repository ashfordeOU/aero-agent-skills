---
name: q7001-solar-array-control
description: "Determine the end-of-life power a contaminated solar array still delivers and whether its second-surface mirrors hold their ratio. Use when photovoltaic wings, cover glasses or optical solar reflectors carry a cleanliness requirement and the power budget has to carry particulate obscuration, molecular film attenuation, the cover absorptance rise that same film produces, the hotter cell it drives and the temperature derating that follows, instead of a flat contamination percentage. Trigger: ecss, q-st-70-01c, solar-array-cover-glass-contamination, array-illumination-factor, photovoltaic-cell-temperature-derating, second-surface-mirror-alpha-shift, optical-solar-reflector-cleanliness, end-of-life-array-power-margin."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-solar-array-control, solar-array-cover-glass-contamination, array-illumination-factor, photovoltaic-cell-temperature-derating, second-surface-mirror-alpha-shift, end-of-life-array-power-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Solar Arrays and Second-Surface Mirrors (space-systems/ecss/q7001-solar-array-control)

Use when the task is the sensitive-hardware branch of ECSS-Q-ST-70-01C that
protects photovoltaic arrays and optical solar reflectors: converting a
predicted molecular deposition and particulate fallout into an end-of-life
delivered power and an end-of-life mirror ratio, and showing both still meet
what the mission asked for.

## Domain quick reference

- An array loses power two ways at once and they do not add the same way.
  Particulate fallout removes aperture: the obscured area fraction is simply
  gone. A molecular film attenuates what passes through the rest, so it
  multiplies rather than subtracts. The illumination factor is the product
  of the two.
- The same film has a second, slower effect. Light the film stops is
  absorbed, not reflected, so the cover absorptance climbs; the particles
  sitting on it are darker than the cover as well. That raises the solar
  load the cell has to shed.
- A photovoltaic cell is a negative-temperature-coefficient device. The
  hotter cover therefore costs power a second time, through the cell
  temperature coefficient, on top of the light it never received. Ignoring
  the coupling understates the loss.
- The cell temperature itself is not a radiative balance of the absorbed
  load alone: the electrical power leaving the wing is energy that does not
  have to be radiated, so the extracted power belongs in the balance. As
  contamination cuts the extracted power, that cooling term weakens too.
- A second-surface mirror in the same environment is graded differently.
  Its job is a low absorptance against a high emittance, so what matters is
  the alpha-over-epsilon ratio after contamination, and a mirror starting at
  a low absorptance is proportionally far more sensitive to the same film
  than a cover glass already absorbing most of the band.

## Workflow

1. Validate the array: beginning-of-life power, required end-of-life power,
   incident solar flux, area, cover thermo-optical properties, reference
   temperature, sink temperature and the cell temperature coefficient.
   Refuse a non-negative temperature coefficient.
2. Convert the predicted deposition into a film transmittance and the
   predicted percent area coverage into an obscured fraction, then form the
   illumination factor as their product.
3. Raise the cover absorptance for the light the film stops and for the
   darker particles covering part of it, capping the result at unity.
4. Solve the cell temperature at beginning of life and at end of life, in
   each case netting the electrical power actually extracted out of the
   absorbed solar load. Refuse a case extracting more than it absorbs.
5. Convert the end-of-life cell temperature into a derating factor through
   the temperature coefficient, and refuse a case where the linear model
   would drive the output to zero.
6. Multiply beginning-of-life power by the illumination factor and the
   derating factor, compare with the required power, and report the
   fractional margin, absorbing boundary representation error with a named
   tolerance.
7. Run the same absorptance model over any declared second-surface mirror
   and compare its degraded alpha-over-epsilon ratio with its allowable.

## Pitfalls

- Applying one flat contamination percentage to the array power. Obscuration
  and film attenuation compose multiplicatively, and the thermal derating is
  a third, separate term; a single percentage cannot represent all three.
- Leaving the extracted power out of the cell thermal balance. It is a
  large term on a working wing, and omitting it overstates the cell
  temperature at beginning of life more than at end of life, which hides
  the very rise being looked for.
- Grading a second-surface mirror on absorptance alone. Its requirement is
  a ratio, and an emittance that also moved can turn an apparently small
  absorptance rise into a ratio breach.
- Assuming a mirror and a cover glass degrade alike. The mirror starts far
  brighter, so the same film and the same dust cost it a much larger
  relative change; a shared contamination allowance mis-serves one of them.
- Reporting an end-of-life power without the reference temperature it was
  derated from. A power figure with no stated reference point cannot be
  compared with the cell datasheet or with the next revision of the budget.

## Behavior contract (gate 3)

The array validation, film transmittance, obscuration and illumination
factor, contaminated absorptance model, cell-temperature balance with
extracted power, temperature derating and its validity refusal, the power
margin comparison and the second-surface-mirror ratio check are exercised by
the gate 3 contract test:
scripts/test_q7001_solar_array_control.py against
scripts/q7001_solar_array_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7001_solar_array_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
