---
name: e2006-surface-charging-analysis
description: "Use when compute the vehicle-wide surface-potential-analysis required by ECSS-E-ST-20-06C clause 6.4: assemble the external-material-inventory row by row, categorize every exposed item as charge-dissipating or charge-storing from its sheet-resistivity and its bonding-path, check the inventoried area against the declared external-area so no exposed item escapes the assessment, evaluate the secondary-emission-yield and backscatter-yield at the worst-case plasma-temperature, solve each item's equilibrium-potential for the sunlit and the eclipsed case, derive the vehicle-frame-potential from the bonded dissipative items, and compare every differential-charging-offset against its breakdown-limit. Trigger: ecss, e-st-20-06c, external-material-inventory, surface-potential-analysis, vehicle-frame-potential, differential-charging-offset, secondary-emission-yield, dielectric-surface-potential, charging-analysis-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-surface-charging-analysis, e-st-20-06c, external-material-inventory, surface-potential-analysis, vehicle-frame-potential, differential-charging-offset, secondary-emission-yield, charging-analysis-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Surface-Charging Analysis (space-systems/ecss/e2006-surface-charging-analysis)

Use when the task is the clause 6.4 provision of ECSS-E-ST-20-06C: the
two linked products it asks for are an inventory of every material
exposed to the ambient plasma and an analysis of the potentials that
inventory produces across the vehicle. This leaf builds the inventory,
proves it covers the whole external-area, and turns it into a
per-item equilibrium-potential and a differential-charging-offset
against the vehicle-frame-potential.

## Domain quick reference

- The inventory is the gate on the analysis, not paperwork around it.
  An external item that never reaches the inventory is never given a
  potential, and the analysis then reports a compliant vehicle while
  an uninventoried dielectric floats to kilovolt level. The inventoried
  area is therefore compared against the declared external-area of the
  configuration, and a shortfall is a finding in its own right.
- Each inventoried item is categorized by its charge path, not by its
  material family. An item bonded to structure whose sheet-resistivity
  sits at or below the dissipative limit drains its collected charge
  and is charge-dissipating; an unbonded item, or a bonded one above
  that limit, holds charge across a substorm and is charge-storing.
  A conductor left floating is charge-storing — the bonding-path and
  the resistivity are two independent conditions and both apply.
- The potential of an exposed item follows from the emitted-electron
  fraction at the worst-case plasma-temperature. Secondary-emission
  follows a peaked yield curve — rising with impact energy, peaking at
  a material-specific energy of a few hundred electronvolts, then
  collapsing — and backscatter adds a roughly flat term. The net
  collected fraction is one minus their sum; an item whose emitted
  fraction already exceeds unity cannot charge negative at all.
- Illumination decides the sign. A sunlit item carries a photoelectron
  term that usually exceeds the ambient electron current and pins it a
  few volts positive; the same item in eclipse loses that term and
  floats to a large negative potential set by the plasma-temperature.
  A vehicle with sunlit and eclipsed faces therefore carries its worst
  offset across the terminator, not across its hottest surface.
- Bonded dissipative items share one conductor, so they sit at the
  vehicle-frame-potential — the area-weighted result of their own
  balances — and carry no offset of their own. The hazard quantity is
  the offset of each charge-storing item against that frame, judged
  against the breakdown-limit of the material, because a uniformly
  charged vehicle is far less hazardous than a modest offset across a
  dielectric gap.

## Workflow

1. Normalise every inventory row: an identifier, a known external
   material, a positive area, a positive sheet-resistivity, an
   illumination state and an explicit bonding flag. Reject an unknown
   material, a non-finite area or a missing bonding flag before the
   analysis starts, and reject a duplicate identifier outright.
2. Categorize each row as charge-dissipating or charge-storing from
   the bonding flag and the sheet-resistivity limit. A row exactly at
   the limit is dissipative — the comparison absorbs representation
   error rather than moving the limit.
3. Sum the inventoried area and compare it with the declared
   external-area. Record a coverage gap when the inventory falls
   short, and an overrun when it exceeds the declared figure, since
   both mean the configuration and the analysis disagree.
4. Evaluate the emitted fraction of each item at the worst-case
   plasma-temperature from its secondary-emission peak, the energy of
   that peak and its backscatter fraction.
5. Solve each item's equilibrium-potential: subtract the photoelectron
   term for a sunlit item, omit it for an eclipsed one, and return the
   pinned positive value when emission or illumination prevents any
   negative excursion.
6. Derive the vehicle-frame-potential as the area-weighted potential
   of the bonded dissipative items. An inventory with no bonded
   dissipative item has no reference and is an input error, not a
   zero result.
7. Report each item at its potential band, its offset against the
   frame, and the findings: an offset above the breakdown-limit, an
   absolute potential above an optional ceiling, and any coverage gap
   or overrun. The vehicle is compliant only when that list is empty.

## Pitfalls

- Treating the inventory as a documentation step and analysing only
  the items someone flagged as sensitive. The clause pairs the two
  products precisely because the missing row is the one that charges.
- Reading a bonded conductor as safe without its sheet-resistivity, or
  a low-resistivity coating as safe without its bonding-path. Either
  condition alone leaves the item charge-storing.
- Giving every surface one shared vehicle potential. The sunlit and
  eclipsed cases of the same material differ by kilovolts, and that
  difference is the hazard the clause exists to surface.
- Judging compliance on the absolute potential. The offset against the
  frame drives the discharge; a vehicle charged uniformly to a high
  negative potential can still be acceptable.
- Widening the breakdown-limit so a boundary case passes. An offset
  that lands a few units in the last place above the limit is the same
  physical value as the limit and the comparison absorbs it; an offset
  genuinely above it is a finding.

## Behavior contract (gate 3)

The inventory validation, conduction-path categorization, area
coverage, emission yield, equilibrium-potential solution,
vehicle-frame-potential and offset assessment are exercised by the
gate 3 contract test: scripts/test_e2006_surface_charging_analysis.py
against scripts/e2006_surface_charging_analysis_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_surface_charging_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
