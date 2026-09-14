---
name: e2008-coverglass-ultraviolet-exposure-test
description: "Assess whether a coverglass coating stays optically stable through accelerated ultraviolet ageing per ECSS-E-ST-20-08C clause 8.7.12. Use when a coverglass ultraviolet exposure run is planned or its data dispositioned: turn lamp setting and exposure hours into equivalent sun hours, refuse an acceleration factor past the reciprocity cap, confirm the chamber held vacuum and the specimen held temperature, check the dark control drifted less than the bench allowance, reduce each band transmittance to a retention factor and an absolute loss, flag solarisation past the allowed loss, weight the bands into one figure, and bound the delay before the scan so bleaching cannot flatter the result. Trigger: ecss, e-st-20-08c, clause-8-7-12, coverglass-ultraviolet-exposure-test, coverglass-equivalent-sun-hours, coverglass-solarisation-transmittance-loss, coverglass-ultraviolet-reciprocity-cap, coverglass-dark-control-witness."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-ultraviolet-exposure-test, coverglass-equivalent-sun-hours, coverglass-solarisation-transmittance-loss, coverglass-ultraviolet-reciprocity-cap, coverglass-dark-control-witness, coverglass-ultraviolet-vacuum-ageing, solar-cell-assembly-optical-measurement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses — Ultraviolet Exposure Test (space-systems/ecss/e2008-coverglass-ultraviolet-exposure-test)

Use when the task is the coverglass ultraviolet exposure test of
ECSS-E-ST-20-08C clause 8.7.12 -- an accelerated ageing run under an
ultraviolet lamp, read not as an endurance ordeal the glass either survives or
does not, but as a measured optical change in the coverglass coatings that
either fits inside the loss the array power budget carries or does not.

## Domain quick reference

- The dose, not the clock, is the test. A run is described by equivalent sun
  hours -- the lamp's ultraviolet intensity in suns multiplied by the hours it
  burned -- and a run that does not reach the mission's ultraviolet dose has
  aged the specimen partway, whatever its duration looks like.
- Acceleration has a ceiling. Reciprocity, the assumption that a fixed dose
  does a fixed amount of damage however fast it is delivered, holds only to a
  few suns. Past that the lamp drives mechanisms the orbit never would and the
  run answers a question the mission did not ask.
- Ultraviolet ageing is a vacuum test. In residual gas the chemistry changes,
  the shortest wavelengths are absorbed before they reach the coating, and the
  specimen is aged by a spectrum that never arrives on orbit.
- Darkening bleaches. Ultraviolet-induced absorption recovers once the
  specimen is back in air and light, so the interval between opening the
  chamber and taking the scan belongs in the record; a scan taken a week later
  measures a recovered specimen and reports the coating as stabler than it is.
- A dark control carries the bench. It rides the same mounts, the same vacuum
  and the same handling without seeing the lamp, so whatever it moved is the
  floor under every exposed number rather than a result in its own right.
- Loss is absolute, retention is a ratio. The power budget subtracts
  transmittance points, so the drop in transmittance is the judged figure and
  the ratio is how the drop is explained across bands.

## Workflow

1. Multiply the lamp's ultraviolet suns by the exposure hours into equivalent
   sun hours and compare the total with the mission dose.
2. Check the acceleration factor against the reciprocity cap and report a lamp
   driven past it rather than crediting the shortened run.
3. Confirm the chamber pressure stayed inside the vacuum limit and the
   specimen temperature inside its tolerance, treating a value exactly on a
   bound as conformant.
4. Difference the dark control's own before and after scans and compare the
   drift with the bench allowance in each band.
5. Divide each post-exposure band transmittance by the same specimen's
   pre-exposure reading for retention, and subtract for absolute loss.
6. Judge each band's absolute loss against the allowed loss and raise a
   finding per band that darkened past it.
7. Weight the bands into one solar-weighted transmittance when weights are
   supplied, rejecting weights that do not add to one.
8. Check the post-exposure scan followed the run inside the bleaching window,
   then report dose, retention, loss, findings and verdict.

## Pitfalls

- Reporting exposure hours without the lamp intensity. Five hundred hours at
  one sun and at five suns are different tests, and only the product is the
  quantity the mission dose is compared against.
- Shortening a run by raising the suns and keeping the dose. Past the
  reciprocity cap the two are no longer equivalent, and the extra intensity
  buys a result the orbit will not reproduce.
- Scanning days after the chamber opened. The darkening has partly bleached
  by then, so the coating passes on a measurement of its recovery.
- Omitting the dark control. Without it a bench drift, a remount or a fresh
  calibration lands in the exposed numbers as ultraviolet damage.
- Judging on retention alone. A band that starts low and holds its ratio can
  still cost the array more transmittance points than a band that starts high
  and drops a larger fraction.
- Averaging the bands without weights. The array does not care equally about
  every wavelength, and an unweighted mean lets an untroubled band mask a
  darkened one.

## Behavior contract (gate 3)

The equivalent-sun-hour dose, the reciprocity cap, the vacuum and temperature
checks, the dark-control drift, the band retention and absolute loss, the
solarisation limit, the solar weighting and the bleaching window are exercised
by the gate 3 contract test:
scripts/test_e2008_coverglass_ultraviolet_exposure_test.py against
scripts/e2008_coverglass_ultraviolet_exposure_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_ultraviolet_exposure_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
