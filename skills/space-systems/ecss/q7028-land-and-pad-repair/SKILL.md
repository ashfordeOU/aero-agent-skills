---
name: q7028-land-and-pad-repair
description: "Evaluate a damaged land or pad on a printed-circuit-board assembly and settle how it is rebuilt. Use when a land has lifted, torn away or lost area during rework: it computes the surviving copper as a fraction of the land the design drew, picks re-bonding in place, an epoxy-bonded replacement land or an eyelet from that fraction and the state of the hole barrel, refuses a land with too little sound base material left, derives the bond area the minimum pull-off load demands, checks the annular ring the repair leaves, and holds the count of repaired lands on one footprint. Trigger: ecss, q-st-70-28c-board-repair, pcb-land-repair, pcb-pad-build-up, pcb-replacement-land-bond-area, pcb-land-pull-off-strength, pcb-annular-ring-after-repair."
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
  tags: [ecss, q-st-70-28c-board-repair, q-st-70-28c, q7028-land-and-pad-repair, pcb-land-repair, pcb-pad-build-up, pcb-replacement-land-bond-area, pcb-land-pull-off-strength, pcb-annular-ring-after-repair]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Land and Pad Repair (space-systems/ecss/q7028-land-and-pad-repair)

Use when the task is the land method clause of ECSS-Q-ST-70-28C: a land has
lifted, torn or lost copper during rework, and the repair has to put back
something a component may be soldered to and pulled on.

## Domain quick reference

- What survives is measured as an area fraction, not described in words. A
  round land around a hole and a rectangular surface-mount pad have different
  geometry and the same rule once each is reduced to copper area against the
  area the design drew.
- The surviving fraction picks the method. A land that kept most of its bond
  area is re-bonded where it lies; one that lost more than that is cut back
  and a replacement land is bonded to the base material; one that kept almost
  nothing has no sound material to bond to and is refused.
- The hole barrel overrides the fraction. If the plated barrel went with the
  land, no amount of surviving copper makes a surface repair right, because
  the through connection is what was lost, and an eyelet restores both.
- A re-bond carries only the copper that is still attached; a replacement land
  or an eyelet is built back to the designed footprint. The two therefore have
  very different bond areas, and treating them alike is how an undersized
  re-bond passes.
- The bond area needed follows from a load, not from a habit. The pull-off the
  land has to carry, divided by the stress its bond may see, gives an area,
  and that area is what the repair is compared against.
- The annular ring is checked after the repair, not before. A replacement land
  slightly off-centre or slightly undersized leaves too little ring around the
  hole, and the joint that looks sound has nothing to hold the barrel.
- Repaired lands are counted per component footprint. One rebuilt land under a
  part is a repair; three of them means the part is sitting on rebuilt copper
  and the footprint, not the land, is the thing that failed.

## Workflow

1. Reduce the land geometry — annular or rectangular — to the copper area the
   design drew.
2. Divide the surviving copper by that area to get the fraction still bonded
   down.
3. Pick the method: eyelet where the barrel is damaged or gone, re-bond where
   the fraction is high enough, a replacement land below that, and no method
   where almost nothing is left.
4. Derive the bond area the pull-off load demands at the allowable bond
   stress.
5. Compare it against the area the chosen method actually delivers — the
   surviving copper for a re-bond, the designed footprint for a rebuild.
6. Compute the annular ring the repaired land leaves around its hole, where
   there is one, and grade it against the minimum.
7. Add this land to the footprint's repaired count and grade that too; return
   the repair with every finding.

## Pitfalls

- Judging the damage by eye rather than by area. A land that looks half gone
  and a land that is half gone are different lands, and only one of them is
  re-bondable.
- Re-bonding a land whose barrel is damaged. The surface joint is sound, the
  through connection is not, and the fault is invisible from the side the
  repair was made on.
- Giving a re-bond credit for the designed footprint. The bond area used in
  the check is copper that is no longer attached, and the land passes a
  pull-off it cannot survive.
- Carrying one bond-area figure for every land. The area follows from the load
  the joint has to take, so a fixed figure is either wasteful on a signal land
  or short on one carrying a connector.
- Checking the annular ring on the drawing instead of on the repair. The
  replacement land is what is there now, and it is usually smaller and rarely
  perfectly centred.
- Counting repaired lands per repair rather than per footprint. Each one was
  approved alone, and the component now sits entirely on rebuilt copper.

## Behavior contract (gate 3)

Annular and rectangular land areas, the surviving fraction, method selection
across re-bond, replacement land, eyelet and refusal, the barrel override, the
load-derived bond area against re-bond versus rebuild area, the annular ring
after repair and the per-footprint count are exercised by the gate 3 contract
test:
scripts/test_q7028_land_and_pad_repair.py against
scripts/q7028_land_and_pad_repair_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7028_land_and_pad_repair.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
