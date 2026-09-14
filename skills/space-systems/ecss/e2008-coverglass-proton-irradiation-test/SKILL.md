---
name: e2008-coverglass-proton-irradiation-test
description: "Verify that a proton irradiation matrix ages both the coverglass substrate and the coatings on it per ECSS-E-ST-20-08C clause 8.7.14. Use when a coverglass proton exposure matrix is built or its results dispositioned: convert each energy line into a stopping depth, group the lines by whether their protons rest in the coating, in the glass or clean through it, refuse a matrix that leaves either layer unexposed, hold every line under the flux cap, reduce each line's band transmittance to an optical density, add those densities into one darkening figure, and judge the transmittance left against the array power budget. Trigger: ecss, e-st-20-08c, clause-8-7-14, coverglass-proton-irradiation-test, coverglass-proton-stopping-depth, coverglass-energy-line-coverage, coverglass-additive-optical-density, coverglass-proton-flux-cap."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-proton-irradiation-test, coverglass-proton-stopping-depth, coverglass-energy-line-coverage, coverglass-additive-optical-density, coverglass-proton-flux-cap, coverglass-coating-and-substrate-exposure, solar-cell-assembly-optical-measurement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses — Proton Irradiation Test (space-systems/ecss/e2008-coverglass-proton-irradiation-test)

Use when the task is the coverglass proton irradiation test of
ECSS-E-ST-20-08C clause 8.7.14 -- an accelerated ageing run under a proton
beam that has to reach the glass and the coatings on it, read as a matrix of
energy lines whose stopping depths decide which part of the article each line
actually aged and whose darkening adds into one optical figure.

## Domain quick reference

- A proton stops. Unlike an electron it does not thin out through the article
  and carry on; it slows, deposits the bulk of its energy at the end of its
  track and comes to rest, so the energy of a line and the depth it damages
  are the same statement.
- Range climbs faster than energy. Doubling the energy roughly triples the
  depth, which is why a matrix spanning the coating and the glass spans well
  under a decade in depth and more than that in energy.
- Coverage is the clause. A matrix of megaelectronvolt lines ages the glass
  and never touches the coating the array has to see through, while a matrix
  of soft lines colours the coating and leaves the substrate untested; both
  answer half the question and read as a pass.
- A line that crosses the whole coverglass has left the article. Its damage
  lands in whatever sits behind the glass, so it belongs in the cell's
  exposure record and not in the coverglass darkening figure.
- Darkening adds in optical density. A spectrum flown as separate lines on
  separate specimens superposes in density and nowhere else, so the lines are
  summed there and converted back into transmittance once.
- Rate is a variable of its own. The same fluence delivered fast heats and
  charges an insulating coverglass, and a specimen that annealed or arced
  during the run is not the specimen the mission would fly.

## Workflow

1. Validate the energy lines as a strictly rising set of at least two, since
   one line cannot reach both the coating and the substrate.
2. Turn each line's energy into a stopping depth with the range law, allowing
   the coefficient and power to be overridden for a doped or denser glass.
3. Group each line by where it came to rest: in the coating, in the glass
   under it, or past the back face.
4. Raise a finding for a required layer no line reaches, and a finding for
   each line that crosses the whole coverglass.
5. Divide each line's fluence by its beam-on time and compare the flux with
   the cap, treating a flux exactly on the cap as conformant.
6. Divide each line's band transmittance by the unirradiated scan of the same
   specimen and take the negative base-ten logarithm for the density.
7. Raise a finding for a line whose specimen reads clearer than it started,
   beyond the measurement allowance.
8. Sum the per-line densities per band, convert the total back into a
   transmittance, compare it with the budget floor, and report depths,
   grouping, densities, the combined figure, findings and verdict.

## Pitfalls

- Choosing energy lines by what the beam line offers. The lines have to be
  chosen from the thicknesses of the article, and a matrix that never lands a
  proton in the coating cannot speak about the coating at all.
- Summing transmittances across lines. Transmittance multiplies and density
  adds, so summing the wrong one understates the darkening of a whole matrix.
- Counting a pass-through line in the coverglass total. Its damage went past
  the glass, so including it borrows an exposure the coverglass never had.
- Quoting one fluence for a matrix. Each line carries its own fluence from the
  mission spectrum, and a single figure hides which line did the damage.
- Delivering a line fast to save beam time. The total is preserved and the
  specimen is not; heating during the run anneals the colour centres the test
  exists to measure.
- Reading a brightened specimen as a good result. A density below the
  unirradiated scan is a remount, a clean or a bench change, and it should
  invalidate the line rather than reduce the matrix total.

## Behavior contract (gate 3)

The proton range law, the stopping-depth grouping, the coating and substrate
coverage requirement, the pass-through finding, the flux cap, the per-line
optical density reduction, the brightening check, the additive combined
density and the transmittance floor are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_proton_irradiation_test.py against
scripts/e2008_coverglass_proton_irradiation_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_proton_irradiation_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
