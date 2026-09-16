---
name: e2008-bonding-integrity-visual-inspection
description: "Use when a bonded coupon has been examined and every cell needs a disposition the full population supports. Verify that every solar cell bond on a photovoltaic coupon meets the bond integrity criteria of ECSS-E-ST-20-08C clause 5.5.3.2.20: derive the bond footprint, weight each adhesive void, edge disbond and corner disbond by where it sits rather than by its area alone, disposition missing fillets, adhesive bridges and lifted cells, roll the disbonded area up into a bonded-area fraction per cell, and hold the coupon open until the record count matches the declared cell population. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-20, solar-cell-bond-integrity, coupon-bond-population-completeness, adhesive-void-area-fraction, corner-disbond-peel-initiation, bonded-area-fraction-limit."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bonding-integrity-visual-inspection, solar-cell-bond-integrity, coupon-bond-population-completeness, adhesive-void-area-fraction, corner-disbond-peel-initiation, bonded-area-fraction-limit, solar-cell-substrate-bond-inspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Bond Integrity Visual Inspection (space-systems/ecss/e2008-bonding-integrity-visual-inspection)

Use when the task is the bond integrity check of ECSS-E-ST-20-08C clause
5.5.3.2.20 -- looking at the bond under every solar cell on the coupon, not
at a sample of them, and deciding per cell whether the bond it has left is
the bond the design asked for.

## Domain quick reference

- The check is a full population. A coupon is built to carry the cells that
  will fly, so a sampled bond check answers a different question from the one
  the clause asks; the count of records is compared against the declared cell
  count and a short set leaves the coupon open however clean the inspected
  bonds were.
- Two numbers decide a cell. How much of the footprint is still bonded, and
  where the missing bond sits. They are separate outputs because they fail the
  cell for separate reasons.
- Position is not cosmetic. A void in the middle of the footprint is a lost
  heat path out of the cell; the same area at a corner is a peel crack with a
  free edge to grow from, and the first thermal cycle drives it. The same
  measured area therefore carries a peel weight when it lies inside the corner
  zone and none when it does not.
- An edge disbond is judged on how far it reached inward, against the shortest
  span of the footprint, because that span is what is left to carry the load.
  A corner disbond is judged against that same allowance divided by the peel
  weight, so the worst geometry on the cell gets the tightest number.
- A missing fillet takes no bonded area away at all. It removes the tapered
  transition that keeps the adhesive out of shear at the cell edge, so it is
  reworkable rather than acceptable, and grading it on area misses it
  completely.
- An adhesive bridge ties a cell to its neighbour. Trimmed back it is rework;
  left in place the two cells expand against each other and it goes to review.
- A lifted cell has no bond anywhere. The other anomalies on it describe parts
  of an area that is already gone, so they are not added on top of it.
- Small accepted anomalies still accumulate. The bonded-area fraction and a
  count allowance per cell catch the bond that passed every individual limit
  and is nevertheless mostly void.

## Workflow

1. Take the declared cell count for the coupon and the inspection records.
   Reject a record set larger than the declared count, and report the
   shortfall when it is smaller.
2. Per cell, derive the bond footprint from the cell dimensions: bonded area,
   perimeter, shortest span, and the corner zone inside which a disbond peels.
3. Disposition every anomaly against its own rule, applying the peel weight to
   anything sitting inside the corner zone and recording the reason whenever a
   disposition leaves the accept band.
4. Sum the disbonded area -- unless the cell is lifted, in which case the whole
   footprint is gone -- and derive the bonded-area fraction.
5. Take the worst anomaly disposition, then apply the area rule: a bonded
   fraction under the minimum rejects the cell whatever the anomaly list said.
   Escalate to review when the accepted-anomaly count is exceeded.
6. Roll up: the worst cell verdict, the identifiers that are not accepted, the
   worst bonded fraction on the coupon, and the completeness flag. The coupon
   closes only when the record set is complete and nothing is outstanding.

## Pitfalls

- Sampling the bonds. The clause asks for the population, and a sampled check
  reports a verdict the evidence does not support.
- Grading a void on bare area. Area alone makes a corner void and a centre
  void look identical; only the corner one is a crack with somewhere to go.
- Judging an edge disbond against a fixed millimetre limit. The number that
  matters is how much of the shortest span is left carrying the cell, so the
  allowance is a fraction of that span.
- Giving a corner disbond the edge allowance. The corner is the worst geometry
  on the cell and has to be held to a tighter number, not the same one.
- Scoring a missing fillet by area. It removes no bonded area, so an
  area-driven screen marks it clean while the cell edge sits in shear.
- Adding a void area on top of a lifted cell. The footprint is already fully
  disbonded; summing it again produces an area larger than the cell.
- Accepting a cell because every anomaly passed. The bonded-area fraction and
  the count allowance exist for exactly that case.
- Comparing a measurement with a derived allowance by bare arithmetic. Every
  allowance here is a product of a criteria value and a measured span or area,
  so a measurement exactly on it can evaluate a few units in the last place
  above it; the comparison absorbs that representation error while the
  allowance stays untouched.

## Behavior contract (gate 3)

The footprint derivation, per-kind anomaly dispositioning, corner peel
weighting, edge and corner allowances, bonded-area fraction, count allowance
and the coupon population rollup are exercised by the gate 3 contract test:
scripts/test_e2008_bonding_integrity_visual_inspection.py against
scripts/e2008_bonding_integrity_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bonding_integrity_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
