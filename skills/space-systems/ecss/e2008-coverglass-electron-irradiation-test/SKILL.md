---
name: e2008-coverglass-electron-irradiation-test
description: "Evaluate how far electron bombardment darkens a coverglass and its coatings under ECSS-E-ST-20-08C clause 8.7.13. Use when a coverglass electron irradiation run is scoped or its readings audited: confirm the beam energy doses the whole thickness rather than a front layer, turn each fluence into the absorbed dose the glass took, hold the flux under the charging cap, require a conductive coating to be grounded, reduce each step's band transmittance to an optical density against the unirradiated scan, refuse a density that falls as fluence rises, fit the density as a power law, and project the end-of-life transmittance. Trigger: ecss, e-st-20-08c, clause-8-7-13, coverglass-electron-irradiation-test, coverglass-electron-optical-density, coverglass-darkening-power-law-fit, coverglass-electron-flux-cap, coverglass-coating-grounding-check."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-electron-irradiation-test, coverglass-electron-optical-density, coverglass-darkening-power-law-fit, coverglass-electron-flux-cap, coverglass-coating-grounding-check, coverglass-electron-traversal-ratio, solar-cell-assembly-optical-measurement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses — Electron Irradiation Test (space-systems/ecss/e2008-coverglass-electron-irradiation-test)

Use when the task is the coverglass electron irradiation test of
ECSS-E-ST-20-08C clause 8.7.13 -- an accelerated ageing run under an electron
beam, read as the optical stability of the coatings and of the glass beneath
them, so the transmittance the array can still count on at end of life is
projected from measured darkening rather than assumed.

## Domain quick reference

- Darkening adds in optical density, not in transmittance. Two exposures that
  each cost a tenth of the light leave eighty-one percent, not eighty, so the
  quantity that is fitted, added and projected is the density and the
  transmittance is what it is converted back into at the end.
- The beam has to cross the article. An electron that stops inside the
  coverglass dumps its damage into a front layer and darkens a specimen the
  orbit would have darkened evenly, so the range is compared with the
  thickness before any reading is trusted.
- Fluence is the beam's number, dose is the glass's. Coloured centres grow
  with the energy the glass absorbed, so a run is reported in gray as well as
  in electrons per square centimetre, and two beam energies are only
  comparable through the dose.
- Flux is a separate variable from fluence. The same total delivered fast
  charges an insulating coverglass and heats it, and a specimen that arced or
  annealed during the run is not the specimen the mission would have.
- A conductive coating must be tied to the mount. Left floating it collects
  the beam and discharges across the article, so the run measures a discharge
  path rather than the coating's radiation stability.
- Growth saturates. Density rises as a fractional power of fluence rather than
  in step with it, which is why the fit is taken on the logarithm of both and
  why extrapolating a straight line in fluence overstates end of life.

## Workflow

1. Turn the beam energy into an electron range in the glass, divide it by the
   coverglass thickness and check the ratio sits inside the traversal window.
2. Convert each step's fluence into the dose the glass absorbed, and do the
   same for the end-of-life fluence.
3. Divide each step's fluence by its beam-on time and compare the flux with
   the charging cap, treating a flux exactly on the cap as conformant.
4. Raise a finding when a conductive coating rode the run ungrounded.
5. Divide each step's band transmittance by the unirradiated scan and take the
   negative base-ten logarithm for the optical density.
6. Check each band's density rises: a fall beyond the noise allowance, or a
   density below the unirradiated reading, is a finding against that step.
7. Fit the density against fluence as a power law on the logarithm of both,
   reporting a band that never darkened as unfitted rather than as zero.
8. Project the density at the end-of-life fluence, convert it back into a
   transmittance, compare it with the budget floor, and report densities, fit,
   dose, projection, findings and verdict.

## Pitfalls

- Averaging transmittances across steps. Transmittance does not add, so an
  average over an exposure sequence is not a quantity the article ever had.
- Picking a beam energy by convenience. A soft beam that stops in the glass
  darkens a thin layer intensely and reports a coverglass far worse than the
  mission would produce at the same fluence.
- Quoting fluence alone across beam energies. Two runs at the same fluence and
  different energies deposited different doses, and only the dose compares.
- Shortening the run by raising the flux. The total is preserved and the
  experiment is not: charging, heating and annealing all scale with rate.
- Extrapolating a straight line in fluence. Density growth saturates, so a
  linear projection puts the end-of-life transmittance below anything the
  specimen would reach and the array is oversized against a fiction.
- Treating a band that did not darken as a passing result without saying so.
  It carries no fit and no projection, and reporting zero where the answer is
  unknown hides that the band was never exercised.

## Behavior contract (gate 3)

The electron range and traversal ratio, the absorbed dose, the flux cap, the
coating grounding check, the optical density reduction, the density
monotonicity check, the power-law fit, the end-of-life projection and the
transmittance floor are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_electron_irradiation_test.py against
scripts/e2008_coverglass_electron_irradiation_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_electron_irradiation_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
