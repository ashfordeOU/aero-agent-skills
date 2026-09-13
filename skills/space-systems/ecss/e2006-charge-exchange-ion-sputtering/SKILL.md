---
name: e2006-charge-exchange-ion-sputtering
description: "Use when verify that the erosion charge-exchange-ions sputter from a spacecraft surface stays inside the agreed allowance, per ECSS-E-ST-20-06C clause 11.2.4: categorize the exposure as direct-beam-impingement, charge-exchange-backflow or no-ion-exposure, convert the collected ion-current-density into an ion-number-flux, evaluate the near-threshold sputter-yield of the surface material at the arrival energy, combine flux, yield and atomic-number-density into an erosion-rate, integrate that rate over the exposure time into an erosion-depth, and check the depth against both the agreed allowance and the coating-thickness reserve. Trigger: ecss, e-st-20-electrical-scope, charge-exchange-ion-erosion, sputter-yield-threshold, ion-number-flux, surface-erosion-depth, coating-thickness-reserve, sputtered-material-redeposition."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-charge-exchange-ion-sputtering, charge-exchange-ion-erosion, sputter-yield-threshold, ion-number-flux, surface-erosion-depth, coating-thickness-reserve, sputtered-material-redeposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging -- Charge-Exchange Ion Sputtering (space-systems/ecss/e2006-charge-exchange-ion-sputtering)

Use when the task is the erosion verification of ECSS-E-ST-20-06C
clause 11.2.4 -- showing that the material a charge-exchange ion
population sputters off an exposed surface over the mission stays
inside the erosion allowance agreed for that surface.

## Domain quick reference

- A beam ion that exchanges charge with a slow neutral near the
  thruster leaves behind a slow ion that no longer follows the beam.
  Those charge-exchange ions are steered by the local plasma potential
  and reach surfaces well off the thrust axis, where they arrive with
  tens to a few hundred electronvolts -- enough to sputter material
  away over a multi-year firing programme.
- Exposure is categorized before any erosion number is produced.
  Inside the beam cone with a clear view the surface takes direct beam
  impingement, which is a layout finding rather than a case the
  charge-exchange allowance covers. Outside the cone the surface sees
  the charge-exchange backflow, which is the population this clause is
  about. A shadowed surface sees no ions and erodes nothing.
- Sputtering has a threshold: below a material-specific impact energy
  no atom is ejected, and just above it the yield rises steeply before
  flattening. The module carries that behaviour as a near-threshold
  fit, k * (sqrt(E) - sqrt(E_threshold))^2, saturating at a tabulated
  maximum, with per-material threshold, coefficient, saturation and
  atomic number density. An unlisted material is uncategorized and
  rejected rather than given a default yield.
- The erosion chain is: collected ion-current-density divided by the
  ion charge gives the ion-number-flux; flux times yield divided by
  the atomic number density gives the recession rate in metres per
  second; rate times exposure time gives the erosion-depth. Doubly
  charged ions carry twice the charge per particle, so the same
  current density is half the number flux and half the erosion.
- Two limits are held against that depth. The agreed erosion allowance
  is the customer or subsystem requirement and is the clause verdict.
  The coating-thickness reserve is the physical one: an optical,
  conductive or thermal coating eroded through changes the surface
  property the coating exists to provide, even when the bare depth
  looks small. Material sputtered off one surface does not vanish --
  it becomes a deposition source on another, which is why an
  unassessed redeposition is recorded rather than ignored.

## Workflow

1. Categorize the exposure of each surface from the plume half-angle,
   its off-axis angle and its line of sight: direct beam impingement
   (raise the layout finding), charge-exchange backflow, or no ion
   exposure (erosion is zero and the surface drops out).
2. Look up the material fit constants; reject an unlisted material
   before any erosion is computed.
3. Evaluate the sputter yield at the arrival energy. At or below the
   material threshold the yield is zero and the surface does not
   erode, which is a legitimate pass recorded as an observation.
4. Convert the collected ion-current-density into an ion-number-flux,
   dividing by the ion charge state.
5. Combine flux, yield and atomic number density into a recession
   rate, then carry it over the exposure time into an erosion-depth in
   micrometres.
6. Compare the depth against the agreed allowance, reporting margin
   and utilisation; a surface with no agreed allowance on record is an
   unevidenced requirement, not a pass.
7. Compare the depth against the coating thickness where a coating is
   declared, and record an unassessed redeposition of the sputtered
   material so the link to the deposition budget stays visible.
8. Aggregate across surfaces and name the worst; the set is compliant
   only when every surface carries an empty blocking-finding list.

## Pitfalls

- Applying a yield below the threshold energy. A linear extrapolation
  through the threshold predicts erosion where a real surface has
  none, and it is the low-energy charge-exchange population that this
  clause is mostly about, so the error lands exactly where it matters.
- Using the ion current density as if it were a number flux. The
  charge state divides it, and a beam with a significant doubly
  charged fraction erodes measurably less per ampere than a singly
  charged one.
- Verifying against the bare depth allowance and ignoring the coating.
  A fraction of a micrometre is a comfortable number against a
  structural allowance and a total loss for a coating of the same
  order.
- Treating a surface inside the beam cone as a charge-exchange case.
  Direct impingement is orders of magnitude more severe, and folding
  it into this allowance hides a layout problem behind a compliant
  number.
- Widening the agreed allowance to admit a case that lands a few
  representation bits over it. The comparison already carries a named
  closeness tolerance, so an equality passes without the agreed limit
  being moved.

## Behavior contract (gate 3)

The material table, near-threshold sputter yield, exposure
categorization, ion-number-flux, erosion-rate, erosion-depth,
allowance, coating-reserve and aggregation logic is exercised by the
gate 3 contract test:
scripts/test_e2006_charge_exchange_ion_sputtering.py against
scripts/e2006_charge_exchange_ion_sputtering_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_charge_exchange_ion_sputtering.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
