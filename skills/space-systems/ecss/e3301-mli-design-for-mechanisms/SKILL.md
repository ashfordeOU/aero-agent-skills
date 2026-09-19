---
name: e3301-mli-design-for-mechanisms
description: "Design an MLI blanket over a moving mechanism so its cut-outs, clearances and grounding never impede the motion, under ECSS-E-ST-33-01C clause 4.7.4.3. Use when the task is stacking blanket thickness, sweep envelope, tolerance chain and billow allowance into a required clearance and comparing it with the gap available, sizing a cut-out the swept path passes through without its edge entering that path, converting the open-area fraction into an effective emittance and a parasitic leak, and confirming every layer reaches structure through enough ground points at low enough resistance. Trigger: ecss, e-st-33-01c, mli-blanket-on-mechanism, mli-cutout-sizing, mli-billow-clearance, mechanism-sweep-envelope-interference, mli-open-area-effective-emittance, mli-layer-grounding-resistance, mechanism-blanket-parasitic-leak."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-mli-design-for-mechanisms, mli-blanket-on-mechanism, mli-cutout-sizing, mli-billow-clearance, mli-open-area-effective-emittance, mli-layer-grounding-resistance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — MLI Design for Mechanisms (space-systems/ecss/e3301-mli-design-for-mechanisms)

Use when the task is the MLI step of ECSS-E-ST-33-01C clause 4.7.4.3 —
blanketing a mechanism without blanketing its motion. The blanket has to
insulate, its cut-outs have to let the moving parts through, its layers have
to be grounded, and none of that may end in the blanket touching, snagging or
loading a part that moves.

## Domain quick reference

- A blanket is not a surface, it is a volume. Twenty layers at a quarter of a
  millimetre plus an outer cover is more than five millimetres of material
  standing next to whatever moves, and that thickness belongs in the
  clearance stack alongside the sweep envelope and the tolerance chain.
- The blanket relaxes in vacuum. Whatever it measured folded on the bench, it
  billows once the trapped gas leaves and the layers separate, so a billow
  allowance is a design input and not a workmanship comment.
- A cut-out is sized on the swept diameter, not on the part diameter. A shaft
  that also orbits, wobbles or translates sweeps a larger circle than it
  occupies, and the cut-out has to clear the swept circle with margin on the
  radius, in both directions.
- Every cut-out is a hole in the thermal design. The open-area fraction pulls
  the effective emittance of the blanket up towards the emittance of whatever
  the hole exposes, and a handful of generous clearance holes can cost more
  parasitic heat than the blanket was installed to save.
- MLI layers charge. Each layer needs a conductive route to structure, the
  number of ground points scales with blanket area, and the route is a series
  chain — tab, strap, lug, joint — whose total resistance is what matters, not
  the best segment in it.

## Workflow

1. Build the blanket thickness from layer count, layer pitch and the outer
   cover.
2. Stack the sweep envelope, that thickness, the tolerance chain and the
   billow allowance into the clearance the installation needs, and subtract
   it from the gap available. A negative margin is a motion finding, not a
   thermal one.
3. Form the swept diameter of the moving part from its own diameter and its
   radial excursion, then the smallest cut-out that clears it with the
   required radial clearance on each side, and take the diametral margin of
   the cut-out actually drawn.
4. Sum the cut-out areas into an open-area fraction of the blanket, refusing
   a set of cut-outs larger than the blanket they are cut from.
5. Weight the blanket emittance and the exposed-surface emittance by that
   fraction into an effective emittance, refusing an opening that would
   insulate better than the blanket, and convert it into the parasitic heat
   the blanket exchanges with its sink.
6. Grade the parasitic leak against the budget, the ground-point count
   against the blanket area, and the series ground-path resistance against
   its limit.
7. Report the clearance and cut-out margins, the open fraction, the effective
   emittance, the parasitic leak, the grounding numbers, an explicit
   motion-unimpeded verdict and every finding.

## Pitfalls

- Treating the blanket as a zero-thickness surface in the clearance check.
  The layers are the largest single term in the stack next to the sweep
  itself, and leaving them out turns a clash into an apparent pass.
- Sizing the clearance on the as-folded blanket. It relaxes on orbit, and the
  relaxed state is the one that touches the moving part.
- Cutting the hole to the part diameter. Any excursion — an orbiting shaft, a
  deploying arm, a gimbal at end of travel — sweeps a wider circle, and the
  edge of an under-sized cut-out sits inside it.
- Taking the clearance and ignoring what it cost thermally. Cut-outs raise the
  effective emittance in proportion to their area, and a blanket generous
  enough to be safe can be too leaky to be useful; both numbers are part of
  the same design decision.
- Grounding the outer cover and calling the blanket grounded. Each layer needs
  a route to structure, and a route through a good strap and a poor lug is a
  poor route — the series total is the number to grade.
- Counting ground points without reference to blanket area. The requirement
  scales with area, so a large blanket with the same point count as a small
  one is under-grounded even though both have points.

## Behavior contract (gate 3)

The blanket thickness build-up, clearance stack, swept-diameter and cut-out
sizing, open-area fraction, effective emittance and parasitic leak, and the
ground-point count and series path resistance are exercised by the gate 3
contract test: scripts/test_e3301_mli_design_for_mechanisms.py against
scripts/e3301_mli_design_for_mechanisms_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3301_mli_design_for_mechanisms.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
