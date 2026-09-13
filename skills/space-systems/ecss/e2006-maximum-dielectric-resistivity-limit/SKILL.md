---
name: e2006-maximum-dielectric-resistivity-limit
description: "Use when compute the maximum permitted resistivity of a spacecraft external dielectric under ECSS-E-ST-20-06C clause 6.2.2: derive the bounding charging-current-density from the electron-flux, secondary-emission and photoemission balance, convert an allowable differential-potential into a bulk-resistivity ceiling through the material thickness and into a sheet-resistivity ceiling along the bleed-path length, compare each declared material resistivity against its ceiling with an explicit margin, and flag every dielectric above its ceiling as needing a conductive-coating or bleed-path grounding fix. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c, dielectric-resistivity-ceiling, bulk-resistivity-limit, sheet-resistivity-limit, charging-current-density, bleed-path-resistance, differential-charging-control."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-maximum-dielectric-resistivity-limit, dielectric-resistivity-ceiling, bulk-resistivity-limit, sheet-resistivity-limit, charging-current-density, bleed-path-resistance, differential-charging-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Scope — Maximum Dielectric Resistivity Limit (space-systems/ecss/e2006-maximum-dielectric-resistivity-limit)

Use when the task is the clause 6.2.2 resistivity ceiling of
ECSS-E-ST-20-06C — turning a bounding charging-current-density and an
allowable differential-potential into the highest resistivity an
external dielectric may have, and checking every declared material
against that ceiling.

## Domain quick reference

- Clause 6.2.2 does not state a resistivity number in isolation: the
  ceiling is *derived*. A dielectric exposed to the charging
  environment collects a net current density; that current has to leak
  to the structural reference through the material itself. Ohm's law in
  the bulk gives the potential the material sustains,
  `V = rho * J * t`, so requiring `V <= V_allow` inverts to a ceiling
  `rho_max = V_allow / (J * t)`. A thicker dielectric therefore gets a
  *lower* resistivity ceiling for the same allowable differential-potential.
- The net driving current density is a balance, not a single flux:
  incident electron flux reduced by the secondary-emission and
  backscatter yields it provokes, then offset by collected ion flux and
  by photoemission on a sunlit surface. When the emitted fraction
  exceeds unity the surface charges positive and the sign of the net
  current flips; the ceiling is derived from the magnitude either way.
  An environment whose terms cancel supplies no driver at all, and no
  ceiling can be derived from it — that is an input defect, not a pass.
- A surface treated with a conductive coating is governed by a sheet
  (per-square) resistivity instead. Current is collected uniformly over
  the bleed path and drains to a grounded edge, so the accumulated drop
  along a path of length `L` is `rho_s * J * L^2 / 2`, giving a sheet
  ceiling `rho_s_max = 2 * V_allow / (J * L^2)`. The quadratic term is
  why a long bleed path fails a coating that a short one passes.
- Materials are first placed in a resistivity regime — conductive,
  static-dissipative, or insulating — to steer the review. The regime is
  descriptive only; an insulating-regime material is not automatically
  non-compliant, and a dissipative-regime material is not automatically
  compliant. Only the derived ceiling decides.

## Workflow

1. Establish the bounding charging-current-density for the worst-case
   environment: combine incident electron flux, secondary-emission and
   backscatter yields, collected ion flux and photoemission into a net
   current density, then take its magnitude. Reject an environment
   whose net current density is zero.
2. Fix the allowable differential-potential for the surface from the
   charging-control budget. Never carry a default silently — an unset
   allowable is a finding.
3. Derive the bulk-resistivity ceiling from the allowable potential,
   the bounding current density and the dielectric thickness. Where a
   conductive coating is declared, derive the sheet-resistivity ceiling
   from the bleed-path length as well.
4. Compare each declared resistivity against its ceiling, absorbing
   float representation error at the boundary with a relative tolerance
   rather than by widening the ceiling. Record the margin as a ratio so
   a marginal pass is visible as such.
5. For a material above its bulk ceiling, check whether a declared
   conductive coating meets the sheet ceiling. A coating that itself
   fails leaves the item non-compliant; a coating that passes records
   the item as mitigated by the bleed path.
6. Aggregate per item: the inventory is compliant only when no item is
   above its ceiling unmitigated and no item is missing the inputs
   needed to derive one.

## Pitfalls

- Applying a single remembered resistivity figure to every dielectric.
  The ceiling scales inversely with thickness and with the bounding
  current density, so the same material passes on one item and fails on
  another.
- Using the incident electron flux as the driving current density.
  Ignoring secondary-emission and photoemission overstates the driver,
  tightens the ceiling, and fails compliant materials.
- Comparing a sheet resistivity against a bulk ceiling, or the reverse.
  The two have different units and different geometry factors; the
  sheet path is quadratic in the bleed-path length.
- Widening the engineering ceiling to make an exact-boundary case pass.
  The drift is representation error in a product of powers of ten;
  absorb it with a relative tolerance in the comparison and leave the
  limit alone.
- Reading a static-dissipative regime label as compliance. The regime
  bands are review aids; the derived ceiling is the requirement.

## Behavior contract (gate 3)

The current-density balance, bulk and sheet ceiling derivation,
margin, regime categorization and inventory aggregation are exercised
by the gate 3 contract test:
scripts/test_e2006_maximum_dielectric_resistivity_limit.py against
scripts/e2006_maximum_dielectric_resistivity_limit_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_maximum_dielectric_resistivity_limit.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
