---
name: e2008-cell-contact-adherence-test-process
description: "Use when running or auditing a bare-cell contact adherence run. Execute the ambient pressure chamber loading every bare solar cell of a lot passes through before its contacts and bypass diode attachment are pulled under ECSS-E-ST-20-08C clause 7.5.7.2.2: fold each cell's edge clearance into its shelf footprint, hold the load under the packing cap that keeps the soak reaching every cell, confirm the pressure band and the declared dwell, refuse to sentence a lot from a partial load, then group each front contact, rear contact and diode attachment reading and sentence every cell by its weakest site. Trigger: ecss, e-st-20-08c-clause-7-5-7-2-2, bare-cell-chamber-loading, ambient-pressure-soak-dwell, cell-contact-pull-load-grouping, diode-attachment-pull-site, bare-cell-shelf-packing-fraction."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-cell-contact-adherence-test-process, bare-cell-chamber-loading, ambient-pressure-soak-dwell, cell-contact-pull-load-grouping, diode-attachment-pull-site, bare-cell-shelf-packing-fraction, bare-cell-lot-loading-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Cell Contact Adherence Test Process (space-systems/ecss/e2008-cell-contact-adherence-test-process)

Use when the task is the run itself under ECSS-E-ST-20-08C clause
7.5.7.2.2 -- every cell of the lot into the ambient pressure chamber,
held there for the declared soak, and only then pulled at the front
contact, the rear contact and the bypass diode attachment. The loading
is the part that is usually treated as housekeeping and is the part that
decides whether the pull numbers mean anything.

## Domain quick reference

- The lot is sentenced from what went into the chamber. A cell left on
  the bench was never conditioned, so it is not evidence about the lot;
  it is counted and named, and the run is reported as covering part of
  the lot rather than all of it.
- Edge clearance is not packing courtesy. It is the air gap the soak
  travels through, so it belongs inside each cell's shelf footprint and
  is added on all four sides.
- A shelf filled past its packing cap conditions its outer cells and
  merely warms its inner ones. The load then produces two populations
  under one lot number, and the weak-looking half is a loading artefact.
- Ambient pressure is a band, not a word. A chamber that drifted out of
  it ran a different conditioning, and the cells inside left in a state
  nobody declared.
- The dwell is what turns a stack of cells into conditioned cells. Short
  dwell, no conditioning, and a pull that follows it reports the joint
  the line built.
- Three sites are pulled, not one. The front contact, the rear contact
  and -- only where the cell carries one -- the bypass diode attachment.
  A cell declared to carry a diode and delivered without a diode reading
  is refused, because the site the clause names went untested.
- A cell is sentenced by its weakest site. A string does not care which
  joint let go, so the strongest two readings never rescue the third.
- Weak and gone are different outcomes. A joint under the floor is a
  reject inside the lot allowance; a joint that came away has lost the
  function outright and fails the run on its own, however small the
  population share.
- The band, the cap, the clearance, the dwell, the pull floor and the
  reject allowance are declared project policy rather than physical
  constants, so they are stated with the result.

## Workflow

1. Take the load: lot size, cells actually loaded, cell length and
   width, the edge clearance used, the usable shelf area, the chamber
   pressure and the soak dwell.
2. Fold the clearance into the cell footprint, multiply up to the shelf
   area the load needs, and take that as a fraction of the usable shelf.
3. Grade the load on five things at once -- completeness, clearance,
   packing, pressure band, dwell -- and name every failure rather than
   the first one found.
4. Stop there if any of them failed. The cells were conditioned to an
   unknown state, so the run is repeated rather than sentenced, and no
   cell is judged on numbers the chamber did not earn.
5. Reduce each conditioned cell to its site readings, refusing a diode
   cell that brought no diode reading, and group every site against the
   pull floor and the detachment threshold.
6. Sentence each cell by its weakest site, then roll the lot up: the
   rejected share against its allowance, and any outright detachment
   named on its own.

## Pitfalls

- Loading what fits and calling it the lot. The cells that stayed
  outside are exactly the ones nobody looked at, and dropping them from
  the denominator turns a partial run into a clean-looking pass.
- Packing the shelf tight to fit one more tray. The circulation the soak
  depends on is blocked by the cells themselves, so the run conditions
  its perimeter and reports the middle as strong.
- Treating the clearance as separate from the footprint. Counted apart,
  it disappears the moment the shelf area is tight, which is exactly
  when it matters.
- Accepting a chamber that sat below the band because the door was
  closed and the timer ran. Pressure is part of the conditioning
  definition, and outside the band the soak is simply another test.
- Averaging the three sites per cell. A cell with two strong contacts
  and a detached diode attachment averages to healthy and flies without
  its shadow protection.
- Reading a detached joint as a very weak one. Weak is a reject the lot
  allowance can absorb; gone is a lost function that no allowance
  covers.
- Comparing a packing fraction, a dwell or a rejected share against its
  limit by bare arithmetic. All three are quotients or sums of measured
  quantities, so a load built exactly to a cap can evaluate a unit in
  the last place over it and read as over-packed on one platform and as
  compliant on another.

## Behavior contract (gate 3)

The clearance-inclusive footprint, the required shelf area and packing
fraction against the cap, the ambient pressure band, the dwell floor,
the loading completeness rule, the per-site grouping with its refusal of
a missing diode reading, the weakest-site cell verdict, the detachment
rule and the lot roll-up are exercised by the gate 3 contract test:
scripts/test_e2008_cell_contact_adherence_test_process.py against
scripts/e2008_cell_contact_adherence_test_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_cell_contact_adherence_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
