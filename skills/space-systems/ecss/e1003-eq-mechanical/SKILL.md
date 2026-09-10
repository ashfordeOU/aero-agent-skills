---
name: e1003-eq-mechanical
description: "Use when running equipment-level mechanical tests under ECSS-E-ST-10-03C clause 5.5.2: determine which mechanical tests apply to a given equipment item (physical properties, acceleration by static/spin/sine-burst, sinusoidal vibration, random vibration, acoustic, shock, and micro-vibration for both disturbance-generating and micro-vibration-sensitive equipment), and verify every applicable test is closed with matching evidence before the equipment's mechanical test campaign is declared complete. Trigger: equipment mechanical test, run mechanical test, physical properties test, static acceleration, spin test, sine burst, sinusoidal vibration, random vibration, acoustic test, shock test, micro-vibration, e-st-10-03, ecss."
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
  tags: [ecss, e-st-10c, equipment-testing, mechanical-test, vibration, shock, micro-vibration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Equipment Mechanical Tests (space-systems/ecss/e1003-eq-mechanical)

Use when the task is running the mechanical test set on a piece of
equipment under ECSS-E-ST-10-03C clause 5.5.2, as part of the
equipment test campaign whose baseline (qualification, acceptance, or
protoflight levels and durations) was already fixed elsewhere.

## Domain quick reference

- ECSS-E-ST-10-03C clause 5.5.2 groups the mechanical tests run on
  equipment: physical properties measurement, acceleration (static,
  spin, or sine-burst), sinusoidal vibration, random vibration,
  acoustic, shock, and micro-vibration.
- Not every test applies to every equipment item -- applicability
  depends on the item's mounting, mass distribution, and role in the
  spacecraft's dynamic environment, not on running the full set
  blindly.
- Physical properties (mass, centre of gravity, moments of inertia)
  are always measured -- every other equipment analysis (loads,
  balance, alignment) depends on having a verified, not just
  predicted, value.
- Acceleration is only meaningful when the equipment sees a
  significant quasi-static or spin-induced load; when it does, the
  test method is one of static (centrifuge), spin (for a
  spin-stabilised or rotating mount), or sine-burst (a low-frequency
  sine sweep used as a proof-load substitute for static/spin testing
  on large or stiff items) -- these are alternative methods for the
  same purpose, not additive.
- Sinusoidal and random vibration both probe the equipment's dynamic
  response and workmanship; an item already enveloped by a
  higher-level (element/system) test campaign can be waived from a
  repeat at equipment level.
- Acoustic testing targets equipment with a high area-to-mass ratio
  (e.g. deployables, large lightweight panels): a diffuse acoustic
  field couples into such items more effectively than direct
  mechanical vibration input alone, so acoustic is additive to, not a
  substitute for, random vibration.
- Shock testing applies to equipment exposed to a pyrotechnic or
  mechanical shock event (e.g. separation, deployment release) in its
  mounting location.
- Micro-vibration has two independent roles: a disturbance-generating
  item (e.g. a reaction wheel or cryocooler) is tested to characterise
  its emitted disturbance, and a micro-vibration-sensitive item (e.g.
  an optical payload) is tested to characterise its susceptibility or
  transfer function. An item can be a source, sensitive, both, or
  neither.

## Workflow

1. For each equipment item, capture its mechanical-test-relevant
   characteristics: static/spin load significance, sine-burst vs.
   static/spin method preference, spinning mount, envelopment by a
   higher-level dynamic test, area-to-mass ratio, shock exposure, and
   micro-vibration source/sensitive roles.
2. Derive the applicable acceleration method (none, static, spin, or
   sine-burst) from the load and mount flags; treat sine-burst and
   spin as mutually exclusive alternatives for the same equipment, not
   a request for both.
3. Derive the full list of applicable tests for the item: physical
   properties (always), acceleration (per step 2, if applicable),
   sinusoidal and random vibration (unless enveloped by a higher-level
   test), acoustic (if area-to-mass ratio is high), shock (if shock
   exposed), and micro-vibration per role (source, sensitive, both, or
   neither).
4. For each applicable test, determine the evidence type required to
   close it (one test report type per test/role) and record status
   (closed once matching evidence is supplied, otherwise open).
5. Before declaring the equipment's mechanical test campaign complete,
   confirm every applicable test for that equipment is closed; list
   any still open rather than assuming completion.
6. Roll the per-equipment status up across the campaign; do not report
   the campaign complete while any equipment item has an open test.

## Pitfalls

- Running the full mechanical test set regardless of applicability
  instead of deriving it from the equipment's actual characteristics.
- Selecting both sine-burst and spin as the acceleration method for
  the same equipment -- they are alternative methods, so this is an
  ambiguous configuration to catch and resolve, not to silently
  accept.
- Treating acoustic testing as replacing random vibration for a
  high-area-to-mass item instead of running both.
- Skipping micro-vibration testing for an item that is both a
  disturbance source and micro-vibration-sensitive, or closing only
  one of the two roles and treating the item as fully tested.
- Declaring the mechanical test campaign complete while any applicable
  test on any equipment item is still open.

## Behavior contract (gate 3)

The acceleration-method derivation, test-applicability, evidence, and
campaign-completeness logic is exercised by the gate 3 contract test:
scripts/test_e1003_eq_mechanical.py against
scripts/e1003_eq_mechanical_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_eq_mechanical.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
