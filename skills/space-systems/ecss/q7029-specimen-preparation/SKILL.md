---
name: q7029-specimen-preparation
description: "Prepare the test item for a crew-compartment offgassing determination under ECSS-Q-ST-70-29, where representativeness governs: size the item so the chamber sees at least the loading the cabin will see, compare the achieved loading against the cabin figure, keep the item small enough relative to the chamber that the atmosphere stays well mixed, refuse a solvent wipe, bake-out or purge that strips the very products the test looks for, require a completed cure and an item inside its post-cure age window, and count replicates for a bulk material against the single as-flown article. Use when raising or reviewing an offgassing test request. Trigger: ecss, q-st-70-29, offgassing-test-item-loading, offgassing-chamber-fill-fraction, offgassing-no-precleaning-rule, offgassing-post-cure-age-window, as-flown-article-offgassing."
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
  tags: [ecss, q-st-70-29-offgassing-determination, q-st-70-29, q7029-specimen-preparation, offgassing-test-item-loading, offgassing-chamber-fill-fraction, offgassing-no-precleaning-rule, offgassing-post-cure-age-window, as-flown-article-offgassing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Test Item Preparation (space-systems/ecss/q7029-specimen-preparation)

Use when the task is the test-item clause of ECSS-Q-ST-70-29: what goes into
the chamber for a crew-compartment offgassing determination — a quantity of a
bulk material, or a whole assembled article — how much of it, and in what
state it goes in.

## Domain quick reference

- The test item exists to reproduce a loading, not a mass. The figure that
  matters is grams of item per cubic metre of chamber, and it has to reach or
  exceed the grams per cubic metre the item will produce in the cabin. A
  chamber loaded at half the cabin understates every concentration by half.
- Loading up is allowed, loading down is not. A conservatism factor above one
  makes the test harder to pass and keeps the result usable; a factor below
  one produces a report that cannot be applied to the flight configuration.
- Small chambers force small items and small items hit the analytical floor.
  When the required mass falls below what the analysis can lift clear of the
  blank, the fix is a smaller chamber, not a bigger sample at the wrong
  loading.
- An item may not pack the chamber. Past roughly half the volume the
  atmosphere being sampled is no longer well mixed, and the sample drawn
  reflects the space around the item rather than the chamber.
- Nothing may be done to the item that removes volatiles. A solvent wipe, a
  bake-out, a vacuum conditioning or a nitrogen purge all strip exactly the
  products the determination exists to find, and each produces a clean report
  about an article that will not fly. This inverts the habit every other test
  discipline builds.
- The cure has to be finished. An incompletely cured adhesive or coating
  releases its unreacted fraction, which is neither the flight condition nor
  a conservative version of it — it is a different material.
- The item also ages out. Weeks of ambient storage release into the
  laboratory what the cabin would otherwise have received, so an item long
  past cure quietly understates the launch condition.
- The route decides the count. A bulk material is characterised across
  replicates; an assembled article is tested once, whole, in the
  configuration it flies in, because the assembly is the thing being asked
  about.

## Workflow

1. Take the route from the scope decision and validate it.
2. Compute the mass required from the cabin loading, the chamber volume and
   any conservatism, refusing a conservatism below one.
3. Compute the loading the planned mass actually achieves and compare it with
   the cabin loading.
4. Check the planned mass against the analytical floor.
5. Where an item volume is declared, compute the chamber fill fraction and
   report a packed chamber.
6. Screen the preparation steps, reporting every one that removes volatiles
   and rejecting a step that is neither permitted nor recognised.
7. Grade the cure duration achieved and the days since cure.
8. Count the test items from the route and return the plan with every
   finding, ready only when there are none.

## Pitfalls

- Sizing the item by mass because the last test used that mass. The loading
  depends on the chamber, and the same mass in a different chamber is a
  different test.
- Loading below the cabin to fit the material available. Every concentration
  then comes out low in direct proportion, and the acceptance decision is
  made on numbers that do not describe the flight configuration.
- Cleaning the article before the test. It is the reflex of every other
  laboratory discipline and it removes the answer.
- Filling the chamber with a large article and sampling anyway. The sample
  describes the gap around the item rather than a mixed atmosphere.
- Testing before the cure has finished, then reading the high result as
  conservative. The unreacted fraction is not the flight material, so the
  result is not conservative, just wrong.
- Testing an article that has sat on a shelf for a year. The volatiles went
  into the building instead of the chamber.
- Disassembling an article to test its parts. The adhesive joints, the
  coatings and the trapped residues are the assembly, and they do not exist
  on the pieces.

## Behavior contract (gate 3)

The required-mass sizing from cabin loading and chamber volume, the
conservatism floor, achieved-loading comparison, analytical mass floor,
chamber fill fraction, banned and permitted preparations, cure completion and
post-cure age window, and the per-route item count are exercised by the gate 3
contract test: scripts/test_q7029_specimen_preparation.py against
scripts/q7029_specimen_preparation_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7029_specimen_preparation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
