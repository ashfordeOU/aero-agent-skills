---
name: q7004-specimen-preparation
description: "Prepare the specimen set an ECSS thermal test campaign actually needs, instrumented units included. Use when the ECSS-Q-ST-70-04C preparation clauses have to be turned into a cut list and a fixture layout: allocate cycled, uncycled reference and spare specimens from the objective and the item category, keep references separate whenever the post-test measurement is destructive, place one sensor per thermal zone with a redundant sensor on the slowest zone that controls the profile, size the bake-out from a diffusion model rather than habit, and order identification, baseline, cleaning, conditioning and inspection. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-test-specimen-allocation, uncycled-reference-specimen, thermal-zone-sensor-placement, controlling-zone-selection, specimen-bake-out-duration."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-specimen-preparation, thermal-test-specimen-allocation, uncycled-reference-specimen, thermal-zone-sensor-placement, controlling-zone-selection, specimen-bake-out-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Specimen Preparation (space-systems/ecss/q7004-specimen-preparation)

Use when the task is the specimen preparation of ECSS-Q-ST-70-04C — turning a
categorized test item into a cut list, a fixture layout and an ordered
sequence of steps, for plain coupons and for instrumented units alike.

## Domain quick reference

- Three specimen populations, not one. Cycled specimens go through the run
  and are sized by the objective. Reference specimens stay uncycled and are
  what the retained property is measured against. Spares cover handling loss
  and are a declared fraction of the cycled count, rounded up to a whole
  specimen because half a coupon cannot be cut.
- A destructive post-test measurement changes the allocation. The cycled
  specimens are consumed by the measurement, so the references have to be
  additional and cut at the same time from the same lot, never recovered from
  the cycled set afterwards. A category that carries no reference specimen
  leaves a destructive measurement with no baseline at all.
- An instrumented unit carries one sensor per declared thermal zone, a
  redundant sensor on the zone that controls the profile, and one reference
  sensor on the fixture. An uncontrolled zone is an unmeasured zone.
- The controlling zone is the slowest one, taken here as the heaviest. A
  profile controlled on a light, fast-responding zone reaches its dwell
  temperature at the sensor while the heavy zone is still short of it, and
  the dwell then runs out before the item is uniform.
- Bake-out has a duration, not a habit. Late-stage desorption of absorbed
  volatiles from a slab follows the first term of the series solution, so a
  half-thickness, a diffusivity and a target removed fraction give a time.
  Below a removed fraction of about a half the one-term model stops
  describing the process, and a measured drying curve is owed instead.
- Order matters in the preparation sequence. The dimensional and mass
  baseline is recorded before any cleaning, because a post-test reading taken
  on a cleaned specimen cannot be compared with an as-received baseline.

## Workflow

1. Declare the item category, the objective, whether the post-test
   measurement is destructive, and the spare fraction. Reject a spare
   fraction above the policy ceiling rather than silently capping it.
2. Allocate the three populations and record the note a destructive
   measurement creates, so the cut list and its justification travel together.
3. Declare the thermal zones with their masses and identifiers. Reject a
   repeated identifier and a zone without a mass; both make the sensor plan
   ambiguous.
4. Take the controlling zone as the heaviest, breaking a tie on the
   identifier so the choice is reproducible, and build the sensor placement
   around it.
5. Where a vacuum run or a moisture-sensitive item is declared, compute the
   bake-out duration from the half-thickness, the diffusivity and the target
   removed fraction, and carry the mass end point as the stopping criterion.
6. Emit the ordered preparation sequence and close with the duties: control
   on the named zone, stop the bake-out on the measured mass, and keep the
   references out of the chamber.

## Pitfalls

- Cutting the references out of the cycled set after the run. They were
  cycled, so they are not a baseline; the retained property then compares the
  run against itself and always looks flat.
- Rounding the spare count down. A spare fraction that yields a fraction of a
  specimen still needs a whole specimen, and a campaign that loses one coupon
  to handling is then short of its objective count.
- Controlling the profile on the most convenient sensor. The fixture and the
  light brackets follow the chamber quickly, so controlling there leaves the
  heavy zone short of its extreme for the whole dwell.
- Instrumenting only the zones that are easy to reach. An unmeasured zone
  cannot be shown to have reached the level, and the run then demonstrates
  the level only where the wires happened to go.
- Baking out to a fixed number of hours inherited from another programme.
  The duration scales with the square of the half-thickness and inversely
  with the diffusivity, so a thicker specimen of the same material needs four
  times the time for twice the thickness.
- Recording the baseline after cleaning. The cleaning removes mass and
  sometimes material, so the as-received condition is gone and the post-test
  mass change absorbs the cleaning.

## Behavior contract (gate 3)

The specimen allocation, destructive-measurement notes, zone validation,
controlling-zone selection, sensor placement, bake-out duration and the
ordered preparation sequence are exercised by the gate 3 contract test:
scripts/test_q7004_specimen_preparation.py against
scripts/q7004_specimen_preparation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7004_specimen_preparation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
