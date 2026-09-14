---
name: e2008-bare-cell-pull-test
description: "Use when a bare-cell contact pull run is planned or its records are reviewed. Assess whether the front and rear contact bonds of a bare solar cell hold under the mechanical pull ECSS-E-ST-20-08C clause 7.5.12 applies on top of environmental loading: confirm the thermal cycles and the humidity soak the lot owes were completed before any contact was pulled, resolve each recorded pull onto the contact normal and reject one dragged too far off it, turn normal force and bonded area into a bond strength, sentence every cell by its weaker site, and refuse to sentence a lot from a partial sample. Trigger: ecss, e-st-20-08c-clause-7-5-12, bare-cell-pull-test, bare-cell-contact-bond-strength, pull-after-environmental-conditioning, front-and-rear-contact-pull-sites, bare-cell-pull-off-normal-angle, bare-cell-pull-lot-sentencing."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-bare-cell-pull-test, bare-cell-contact-bond-strength, pull-after-environmental-conditioning, front-and-rear-contact-pull-sites, bare-cell-pull-off-normal-angle, bare-cell-pull-lot-sentencing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Bare Cell Pull Test (space-systems/ecss/e2008-bare-cell-pull-test)

Use when the task is the bare-cell pull test of ECSS-E-ST-20-08C clause
7.5.12 -- judging whether the bond under the front contact and the bond under
the rear contact of a bare solar cell were shown to carry load after the cell
had been through its environmental block, not before it, and whether the forces
that came off the machine can be read as bond strengths at all.

## Domain quick reference

- The clause puts mechanical loading on top of environmental loading, and the
  order is the whole point. A bond pulled straight off the production line
  reports the as-built joint; the mission gets the joint that thermal cycling
  and a humidity soak have already worked on, and only the second number
  belongs in a qualification record.
- Two contacts are assessed, not one. The front contact sits on the illuminated
  face over the grid metallisation and the rear contact covers most of the back,
  so they are laid down by different steps, carry different areas and fail at
  different loads. A cell is sentenced by whichever lets go first.
- A recorded force is not yet a bond strength. Two contacts of the same quality
  on different footprints part at different forces, so the comparable quantity
  is force per unit bonded area and the bonded area has to be declared per site
  before any number is compared with a requirement.
- The pull direction matters as much as the magnitude. A pull dragged off the
  contact normal puts part of the load into peel and shear, and the peel
  component parts a bond at a far lower reading; such a pull is rejected rather
  than corrected, because the split between the modes is not recoverable from
  one force number.
- A lot verdict is a sampling statement. Three planned cells and two pulled is
  not a lot result, and a handful of readings with no spread reported cannot
  show whether a passing mean sits close to the floor or far above it.

## Workflow

1. Compare the thermal cycles and soak hours the lot actually received against
   the ones the plan carries, treating a value sitting exactly on either
   requirement as met.
2. Walk the run sequence and place the pull relative to the environmental
   steps: a pull before any of them, and an environmental step that lands after
   the pull, are two distinct findings.
3. Resolve every recorded pull onto the contact normal, and raise a finding for
   any site pulled further off normal than the declared allowance, treating a
   pull exactly on the allowance as conformant.
4. Divide each normal force by the bonded area declared for that site to get a
   bond strength, and compare it with the minimum the bond owes.
5. Take the weaker of the two sites as the cell's result and sentence the cell
   on it; report the site that governed so a repeated failure mode is visible.
6. Reconcile the cells pulled against the cells planned, reporting a planned
   cell never pulled, a cell pulled twice, a cell pulled that is not on the plan
   and a sample under the floor as separate findings.
7. Report the lot mean, spread, lowest and highest weakest-site strength
   alongside every finding and the lot verdict.

## Pitfalls

- Accepting a pull run that preceded the environmental block because the forces
  look healthy. Those forces describe a joint the mission never sees, and no
  margin can be carried forward from them.
- Comparing forces across cells with different contact footprints. The front
  and rear contacts rarely share an area, so a rear contact parting at a higher
  force can still be the weaker bond of the two.
- Correcting an off-normal pull by dividing out the cosine and carrying on. The
  cosine recovers the normal component but says nothing about the peel the
  tilt introduced, and peel is what actually parted the bond.
- Sentencing a cell on its front contact alone. The rear contact is the larger
  bonded area and the one most exposed to the cell mounting step, so a run that
  pulls only the front leaves the more likely failure untested.
- Reporting a lot mean with no spread. A mean comfortably above the floor with
  a wide spread hides cells sitting under it, and the lot is sentenced by its
  weakest cell, never by its average.
- Counting cells instead of reconciling them. Three planned and three pulled
  hides one cell pulled twice and one never pulled.

## Behavior contract (gate 3)

The conditioning shortfall check, the run-sequence ordering check, the
off-normal resolution and allowance check, the bond strength derivation and
minimum comparison, the weaker-site cell sentencing, the sample reconciliation
and the lot statistics are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_pull_test.py against
scripts/e2008_bare_cell_pull_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2008_bare_cell_pull_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
