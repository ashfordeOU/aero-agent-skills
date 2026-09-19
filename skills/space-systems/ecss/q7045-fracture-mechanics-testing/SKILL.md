---
name: q7045-fracture-mechanics-testing
description: "Validate a fracture toughness test and reduce the crack growth data it came with. Use when the methods clause of ECSS-Q-ST-70-45 is generating the fracture inputs a damage tolerance assessment to ECSS-E-ST-32-01 consumes: compute the conditional toughness from the load, the section and the geometry factor at the measured crack depth, hold thickness, crack depth and remaining ligament to the plane-strain size criterion, report a maximum load that ran away from the conditional one, and fit growth rate against cyclic stress intensity without extrapolating it. Trigger: ecss, q-st-70-45, compact-specimen-geometry-factor, plane-strain-size-criterion, conditional-toughness-kq, pmax-to-pq-load-ratio, paris-crack-growth-loglog-fit."
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
  tags: [ecss, q-st-70-45-mechanical-testing-scope, q7045-fracture-mechanics-testing, compact-specimen-geometry-factor, plane-strain-size-criterion, conditional-toughness-kq, pmax-to-pq-load-ratio, paris-crack-growth-loglog-fit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing of Metals -- Fracture Mechanics Testing (space-systems/ecss/q7045-fracture-mechanics-testing)

Use when the methods clause of ECSS-Q-ST-70-45 is being used to generate the
fracture data a damage tolerance assessment to ECSS-E-ST-32-01 consumes: a
pre-cracked compact specimen has been broken, its load record and crack
depth are in hand, and the question is whether the number it produced is a
material property or only a property of that specimen.

## Domain quick reference

- The conditional toughness is not yet a toughness. It is what the load, the
  section and the geometry factor give at the measured crack depth, and it
  earns the material-property name only after the size criterion passes.
- Validity is a size question and all three lengths have to pass. Thickness,
  crack depth and remaining ligament each have to exceed a requirement that
  scales with the square of the toughness-to-yield ratio, so a tough, soft
  alloy needs a specimen most laboratories do not have.
- The size requirement depends on the answer. It is computed from the
  toughness the test produced, which is why a test cannot be pronounced valid
  before it has been reduced.
- The load record has to behave. A maximum far above the conditional load
  says the specimen was tearing in a stable way before it broke, which is a
  different quantity from the one being reported.
- A growth law is only as wide as the cyclic intensities that were run. The
  power law fits happily and extrapolates silently, and the region below the
  lowest point tested is where the threshold behaviour that was never
  measured actually lives.

## Workflow

1. Validate the geometry: the crack has to sit inside the specimen and its
   depth ratio inside the range the compact geometry factor is defined over.
2. Compute the geometry factor at that ratio and the conditional toughness
   from the conditional load, the thickness and the width.
3. Compute the plane-strain size requirement from that toughness and the
   yield strength of the same material lot.
4. Compare thickness, crack depth and remaining ligament with the
   requirement, one finding per length that misses it.
5. Compare the maximum load against the conditional load and report a record
   that ran past the ratio limit, or one whose maximum sits below it at all.
6. Withhold the reportable toughness whenever any finding stands, rather than
   reporting a specimen-specific number under a material-property name.
7. Fit growth rate against cyclic stress intensity in logarithms when growth
   data is present, and carry the cycled range so the law cannot be used
   outside it.

## Pitfalls

- Reporting the conditional toughness as the plane-strain toughness. The two
  agree exactly when the specimen was big enough, which is the only case
  where the distinction costs nothing.
- Checking thickness alone. A thick specimen with a shallow crack has a long
  ligament and a short crack, and the crack is the length that fails.
- Sizing the specimen from a handbook toughness. The criterion is evaluated
  against the toughness this test produced, not the one that was expected.
- Extrapolating the growth law below the lowest cyclic intensity cycled. The
  fitted line runs straight through the threshold region and predicts growth
  rates nobody measured.
- Accepting a record whose maximum load towers over the conditional load. The
  specimen tore stably first and the reported number is not a crack
  initiation property.

## Behavior contract (gate 3)

The compact geometry factor and its defined range, the conditional
toughness, the plane-strain size requirement and the per-length findings,
the maximum-to-conditional load ratio, the withheld reportable toughness and
the power-law growth fit with its non-extrapolated range are exercised by the
gate 3 contract test:
scripts/test_q7045_fracture_mechanics_testing.py against
scripts/q7045_fracture_mechanics_testing_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q7045_fracture_mechanics_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
