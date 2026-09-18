---
name: q7002-method-variants
description: "Determine which permitted variants of the thermal-vacuum outgassing screening test of ECSS-Q-ST-70-02C a material calls for, and the cost each carries. Use when a run departs from the baseline: a water-vapour regained determination, a longer preconditioning period for a hygroscopic material, a bake below the screening temperature for a low maximum-use-temperature material, or a longer bake for a thick specimen. Matches every declared variant against the material property indicating it and against the settings the run applied, derives the regained and recovered mass-loss figures, and says when a figure stops comparing with baseline data. Trigger: ecss, q-st-70-02, outgassing-method-variant, water-vapour-regained, recovered-mass-loss, extended-outgassing-preconditioning, reduced-bake-temperature-run, baseline-screening-comparability."
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
  tags: [ecss, q-st-70-materials-outgassing-scope, q7002-method-variants, outgassing-method-variant, water-vapour-regained, recovered-mass-loss, extended-outgassing-preconditioning, baseline-screening-comparability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening — Method Variants (space-systems/ecss/q7002-method-variants)

Use when the task is the method-control step of the ECSS-Q-ST-70-02C
thermal-vacuum outgassing screening test — deciding which permitted
departure from the baseline run a material needs, checking the run
actually matches the departure it declared, and saying what the
departure costs in comparability.

## Domain quick reference

- The baseline run is fixed: preconditioning at laboratory humidity, a
  bake at the screening temperature for the screening period, and a
  condensable collection. Every variant is a named change to exactly one
  of those, so a run can declare what it did in a way another laboratory
  can reproduce.
- Variants are indicated by the material, not chosen for convenience. A
  material that takes up water indicates the water-vapour regained
  determination and a longer preconditioning period; a material whose
  maximum use temperature sits under the screening temperature indicates
  a reduced bake; a thick specimen indicates a longer bake because the
  volatiles have further to diffuse.
- The water-vapour regained determination adds a weighing, not a change.
  After the bake the specimen is reconditioned and reweighed; the
  mass it took back, over the mass it started with, is the regained
  figure, and the total loss less that figure is the recovered mass
  loss. Because the bake is untouched, the numbers still sit alongside
  baseline data.
- Changing the bake breaks that. A run at a lower temperature or over a
  longer period gives a figure honest for that material and not
  interchangeable with a baseline figure, and the report must carry that
  statement or the two will be compared anyway.
- The two failure directions are symmetric and both matter. A variant
  declared but never performed invents a departure the reader will
  trust; a departure performed but never declared hides it. Settings and
  declaration are checked against each other in both directions.

## Workflow

1. Validate the request: known variant names, no repeats, and run
   settings inside what the method permits — a bake no hotter than the
   screening temperature and no colder than the method floor,
   preconditioning and bake periods no shorter than the baseline.
2. Read the material properties and list the variants they indicate.
3. Compare the declared variants with the settings in both directions:
   a declared variant whose setting sits at the baseline, and a setting
   moved off the baseline with no variant declared, are each a finding.
4. Check the water-vapour path specifically: the variant needs a
   reconditioning period of at least the method's length, and a
   reconditioning period recorded without the variant is its own
   finding.
5. Compare the declared variants with the indicated ones: an indicated
   variant left out, and a variant applied with no property indicating
   it, are each a finding.
6. Where the weighings are available, compute the regained figure from
   the post-bake and reconditioned masses over the initial mass, and the
   recovered mass loss from the total loss less the regained figure.
   Refuse a reconditioned specimen lighter than it was after the bake or
   heavier than it started.
7. Resolve comparability: directly comparable when every applied variant
   leaves the bake alone, otherwise not — naming the variants that broke
   it.
8. Report the applied and indicated variants, both mismatch lists, the
   derived figures, the comparability statement and every finding.

## Pitfalls

- Treating a reduced bake as a small adjustment. It is a different test
  whose number cannot be dropped into a data set built at the screening
  temperature, and nothing in the figure itself says so unless the
  report does.
- Using the regained figure without performing the reconditioning. It
  is a weighing, not an estimate, and a nominal water fraction
  substituted for it credits back mass that never returned.
- Lengthening the preconditioning quietly to help a hygroscopic material
  pass. Undeclared, it looks like a baseline run with an unusually low
  mass loss.
- Applying the water-vapour determination to a material that takes up no
  water. It adds a weighing cycle and a figure of zero, and it makes the
  test report harder to compare rather than easier.
- Reading the bake-temperature floor as advisory. Below it the species
  the screening exists to find are never mobilised, so the run reports a
  clean material it never actually challenged.

## Behavior contract (gate 3)

The variant registry, indication rules, request validation, declared
versus actual settings check in both directions, regained and recovered
mass-loss arithmetic and comparability resolution are exercised by the
gate 3 contract test: scripts/test_q7002_method_variants.py against
scripts/q7002_method_variants_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7002_method_variants.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
