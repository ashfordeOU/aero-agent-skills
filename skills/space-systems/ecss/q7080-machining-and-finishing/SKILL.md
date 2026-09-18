---
name: q7080-machining-and-finishing
description: "Calculate the machining stock an as-built surface needs and grade the declared allowance against it. Use when a post-process plan for an additively manufactured part has to be sized: add the as-built valley depth, the partly fused near-surface layer, the distortion on release, the fixture datum uncertainty and a real minimum depth of cut, compare that with the stock left on the model, take machining and finishing off every machined side and check the wall that remains, confirm the finishing process reaches the surface, and watch the bore open on an internal passage. Trigger: ecss, q-st-70-80-additive-manufacturing, am-machining-stock-allowance, am-as-built-surface-layer-removal, am-post-machining-wall-thickness, am-internal-passage-finishing-reach, am-finished-bore-growth."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-machining-and-finishing, am-machining-stock-allowance, am-as-built-surface-layer-removal, am-post-machining-wall-thickness, am-internal-passage-finishing-reach, am-finished-bore-growth]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Machining and Finishing Allowances (space-systems/ecss/q7080-machining-and-finishing)

Use when the post-process clause of ECSS-Q-ST-70-80 is the task: sizing
the stock left on an additively manufactured surface for machining and
finishing, and deciding whether the plan reaches sound material without
taking the wall, or the bore, out of the design.

## Domain quick reference

- The as-built surface is not the drawing surface. Below the visible
  valley sits a layer of partly fused powder and near-surface porosity,
  and a cut that stops in it leaves the defect population intact under a
  smooth face.
- Required stock is a sum of separate reasons, not a habit: the valley
  depth of the as-built finish, the depth of the partly fused layer,
  where the part actually sits once the plate constraint is released,
  how well the fixture locates it, and the smallest depth at which the
  tool cuts rather than rubs.
- Too much stock is a finding as well. Stock is build time, powder,
  mass and more distortion, and a surface carrying several times what
  the cut needs was sized by reflex rather than from the build.
- Machining and finishing come off the same wall, and off every machined
  side of it. A wall that reads comfortably in the model can be below
  its minimum once both sides are cut and then flow-finished.
- Finishing processes differ in what they can reach. A media or tumbling
  process works on what it can touch, so an internal passage keeps its
  as-built condition no matter how many cycles are run, while an
  abrasive-flow or chemical route does reach it.
- Peening is not a finishing cut. It displaces material into compression
  rather than removing it, so declaring a stock removal for it double
  counts material that never comes off.
- On an internal passage the removal opens the bore on both sides, so a
  passage can be finished straight out of its diameter tolerance while
  every individual pass looked small.

## Workflow

1. Form the required stock for the surface by adding the valley depth and
   the partly fused layer, converted from micrometres, to the distortion
   on release, the fixture datum uncertainty and the minimum depth of
   cut.
2. Grade the declared stock against that requirement: below it the cut
   finishes inside the as-built layer; far above it the excess is called
   out as build time and distortion rather than margin.
3. Grade the finishing operation on three things at once -- whether the
   process reaches the surface it is applied to, whether it removes
   stock at all, and whether the passes fit inside the finishing
   allowance.
4. Take the machining stock plus the finishing removal off each machined
   side of the wall and compare what is left with the minimum design
   wall, reporting a wall consumed entirely as its own finding.
5. On an internal passage, double the finishing removal into bore growth
   and grade it against the upper diameter tolerance.
6. Take the worst of stock, finishing, wall and bore as the verdict, name
   the quantity that drove it, and prefix each finding with that
   quantity.
7. Where a declared allowance should land exactly on the computed
   requirement, grade it with the tolerant comparison: a sum of five
   terms does not reproduce a hand-written total bit for bit.

## Pitfalls

- Sizing stock from the roughness alone. The valley is only the first of
  five reasons the tool has to go deeper, and the distortion on release
  is usually the largest of them.
- Machining to the drawing surface and calling the defect layer removed.
  If the cut stops inside the partly fused layer, the part has a smooth
  face over exactly the population the machining was meant to take off.
- Checking the wall against the model instead of against the plan. Two
  machined sides plus a flow-finishing pass can take more than twice the
  nominal stock off a single wall.
- Assuming a finishing process reaches everywhere. Tumbling and blending
  work on what they can touch; an internal passage finished that way is
  still an as-built passage.
- Booking peening as stock removal. It changes the residual stress
  state, not the dimension, and counting it twice makes an allowance
  look spent when it is not.
- Forgetting that an internal finishing pass opens the bore from both
  sides. Each pass looks negligible and the sum is a diameter out of
  tolerance.
- Grading an on-limit allowance by bare arithmetic. The requirement is a
  sum of five terms in two units, so an allowance written to equal it
  will not compare equal without a tolerant comparison.

## Behavior contract (gate 3)

The required-stock summation, the declared-allowance grading, the
finishing reach, removal and budget checks, the post-machining wall and
the finished bore growth are exercised by the gate 3 contract test:
scripts/test_q7080_machining_and_finishing.py against
scripts/q7080_machining_and_finishing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_machining_and_finishing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
