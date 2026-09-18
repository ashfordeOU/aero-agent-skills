---
name: q7031-repair-and-touch-up
description: "Determine whether a local defect in a cured paint may be touched up in place or has to go back for a full strip. Use when a repair is proposed on flight hardware: resolve how deep the defect reaches and therefore what has to be rebuilt, sum old and new repairs against the allowed fraction of the painted area, spend one unit of the re-application budget that area carries, project local film thickness after the abrade and the new coat against the ceiling, and price the added mass against the unit allowance. Trigger: ecss, q-st-70-31c-painting-scope, paint-touch-up-eligibility, coating-reapplication-limit, local-repair-area-fraction, touch-up-local-film-thickness, paint-repair-blend-margin."
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
  tags: [ecss, q-st-70-31c-painting-scope, q7031-repair-and-touch-up, paint-touch-up-eligibility, coating-reapplication-limit, local-repair-area-fraction, touch-up-local-film-thickness, paint-repair-blend-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Painting — Repair and Touch-Up (space-systems/ecss/q7031-repair-and-touch-up)

Use when the task is the local repair rule of ECSS-Q-ST-70-31C: a cured coat
has a defect in it, somebody wants to fix that spot rather than strip the
part, and the question is whether the spot is still inside the budgets a
touch-up is allowed to spend.

## Domain quick reference

- Depth is the first question, because depth names the rebuild. A defect
  confined to the topcoat is abraded and re-topcoated; one into the primer
  rebuilds primer and topcoat; one down to the substrate owes surface
  preparation first. A defect that has damaged the substrate itself is not a
  coating repair at all and is dispositioned as hardware damage.
- Repaired area is cumulative over the life of the part, not per event. Three
  small repairs that individually look trivial can put a panel past the
  allowed fraction, so the fraction is computed from the prior repairs plus
  the one being proposed.
- The same local area carries a re-application budget counted in whole coats.
  Each local re-coat spends one, an area at its limit reports no remaining
  budget rather than a negative one, and an exhausted budget is a strip, not
  an argument.
- Local thickness is projected, not assumed. The abrade that precedes a
  touch-up takes film off, the repair puts film back, and the projection is
  what is left plus what goes on. A projection past the ceiling is itself a
  strip driver, because a thick local build is a thermal and an adhesion
  defect however neat it looks.
- A repair blended over too short a run leaves an abrupt edge, which is where
  the next delamination starts, and a coat applied before the recoat interval
  is met cures into the one under it.
- Findings split into two dispositions. Area, re-application and thickness
  drive a strip and repaint. Blend, recoat interval and mass are corrective
  actions on the same repair, because they change how the touch-up is done
  rather than whether it is allowed.

## Workflow

1. Resolve the defect depth and take the rebuild scheme from it; refuse a
   substrate-damaged case outright instead of coating over it.
2. Sum the prior repair areas with the proposed one and put the fraction of
   the painted area against the allowed fraction, treating a value on the
   limit as inside it.
3. Spend one unit of the re-application budget for that area and report what
   remains, never a negative number.
4. Project the local film thickness -- existing, less the abrade, plus the new
   coat -- and put it against the maximum.
5. Check the feathered blend margin and the interval since the last coat.
6. Price the repair mass from area, added film and paint density, and put it
   against the unit allowance when one is held.
7. Disposition the request: permitted with no findings; strip and repaint when
   area, re-application or thickness failed; corrective action when only the
   method did. Aggregate across the unit's repair history, summing the mass
   the repairs have added.

## Pitfalls

- Treating each touch-up as its own event, so the cumulative repaired area is
  never compared with anything.
- Losing count of how many times a spot has been re-coated, which is how an
  area quietly reaches its fourth local coat.
- Projecting thickness from the nominal instead of from the abraded state, and
  so under-reading the local build that the repair actually leaves.
- Coating over substrate damage because the defect looks like a paint defect
  from above.
- Re-coating before the interval is met to keep the shop moving, which cures
  the new film into an uncured one underneath.
- Carrying repair mass as negligible across a dozen repairs, where the unit
  mass budget only ever sees the total.

## Behavior contract (gate 3)

The depth grouping and rebuild scheme, cumulative repaired-area fraction,
re-application budget, projected local thickness, blend margin, recoat
interval, added mass and the repair disposition are exercised by the gate 3
contract test: scripts/test_q7031_repair_and_touch_up.py against
scripts/q7031_repair_and_touch_up_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7031_repair_and_touch_up.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
