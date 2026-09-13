---
name: e2006-surface-metallic-part-bonding
description: "Use when verify that every structural and mechanical metallic part of a spacecraft is electrically bonded under ECSS-E-ST-20-06C clause 6.3.1: trace each part's bond path to the structural reference across the bonding network, add series strap and joint resistances along the lowest-resistance route, combine redundant straps in parallel, compare the effective bond resistance against its bond-category ceiling, convert a bounding discharge transient into the resistive and inductive potential the strap sustains, and report every part left electrically isolated from the structural reference. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c, metallic-part-bonding, bond-path-resistance, structural-reference-continuity, differential-charging-control, bond-strap-inductance, redundant-bond-strap."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-surface-metallic-part-bonding, metallic-part-bonding, bond-path-resistance, structural-reference-continuity, differential-charging-control, bond-strap-inductance, redundant-bond-strap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Scope — Surface Metallic Part Bonding (space-systems/ecss/e2006-surface-metallic-part-bonding)

Use when the task is the clause 6.3.1 bonding requirement of
ECSS-E-ST-20-06C — proving that every structural and mechanical
metallic part is tied to the structural reference by a bond path good
enough to keep differential charging between metals controlled.

## Domain quick reference

- The requirement is a *network* property, not a per-part attribute. A
  part is bonded when a conductive route exists from it to the
  structural reference; the route may run through other parts. Two
  parts each carrying an excellent strap to a third part that is itself
  floating are both unbonded. Reachability therefore has to be resolved
  over the whole bond graph before any resistance is judged.
- Along a route, joint and strap resistances add in series. Between two
  parts, redundant straps combine in parallel, so a second strap lowers
  the effective resistance but never below the better of the two. The
  governing number for a part is the lowest total resistance any route
  to the structural reference achieves — a poor parallel route does not
  degrade a good one.
- The ceiling on that effective resistance depends on the part's bond
  category. A primary-structure bond carries the tightest ceiling; a
  bond whose only job is to bleed electrostatic charge off a mechanical
  fitting is allowed orders of magnitude more. Judging a bleed bond
  against a primary-structure ceiling manufactures findings; judging a
  primary-structure bond against a bleed ceiling hides them.
- The bond also has to survive a discharge transient, and there the DC
  resistance is usually not what dominates. A strap's series inductance
  produces a potential proportional to the current slew rate, so a long
  narrow strap can sustain hundreds of volts during a fast event while
  measuring only milliohms at DC. This is why the clause is satisfied by
  short, wide straps rather than by low DC resistance alone.
- A part with no declared exposed area cannot have its quasi-static
  collected current computed. That is missing evidence, not a pass.

## Workflow

1. Inventory every structural and mechanical metallic part with its
   bond category, and inventory every declared bond as an endpoint pair
   with a measured resistance. Reject an unknown category and an
   endpoint that names no part and is not the structural reference.
2. Collapse redundant straps between the same endpoint pair into one
   effective resistance by parallel combination, building the bond
   network.
3. Resolve the lowest-resistance route from each part to the structural
   reference by accumulating series resistance across the network. Any
   part the reference cannot reach is electrically isolated — the first
   and most severe finding class.
4. Compare each part's effective bond resistance against its
   bond-category ceiling, absorbing float representation error at the
   boundary with a relative tolerance rather than by relaxing the
   ceiling.
5. Compute the quasi-static differential potential from the part's
   collected environmental current across its bond resistance, and the
   transient potential from the bounding discharge current through the
   strap resistance plus its inductive term. Compare both against the
   allowable differential potential.
6. Aggregate per part: the bonding network is compliant only when no
   part is isolated, no ceiling is exceeded, no potential check fails
   and no part is missing the evidence needed to run a check.

## Pitfalls

- Confirming a strap exists and stopping there. A strap to a floating
  neighbour is not a bond to the structural reference; only graph
  reachability settles it.
- Summing parallel straps or paralleling series segments. Series adds,
  parallel divides; inverting the two either invents margin or invents
  a finding.
- Taking the first route found instead of the lowest-resistance route.
  The governing number is the best route, and a search that stops early
  reports a resistance the hardware does not have.
- Judging bonding on DC resistance only. The inductive term dominates a
  fast discharge, so a strap can pass a milliohm check and still sustain
  a damaging transient potential.
- Treating a part with no declared exposed area as compliant because no
  potential could be computed. Absent evidence is a finding.

## Behavior contract (gate 3)

The network construction, series and parallel combination,
lowest-resistance route resolution, isolation detection, category
ceiling check and transient potential logic are exercised by the gate 3
contract test: scripts/test_e2006_surface_metallic_part_bonding.py
against scripts/e2006_surface_metallic_part_bonding_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_surface_metallic_part_bonding.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
