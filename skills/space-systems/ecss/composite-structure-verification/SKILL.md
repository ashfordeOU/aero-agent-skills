---
name: composite-structure-verification
description: "Use when verify composite structures under ECSS-E-ST-32C clause
  4.6.4: determine design allowables on the correct statistical basis (A-basis
  for single-load-path structure, B-basis for redundant structure), apply
  environmental and scatter knock-down factors, analyze all composite failure
  modes (fiber failure, matrix cracking, delamination, inter-laminar shear),
  confirm test articles are conditioned to the worst-case environment before
  structural testing, plan NDT coverage with critical defect size assessment for
  primary and secondary composite parts, and validate the building-block test
  pyramid includes mandatory coupon and component levels. Trigger: ecss,
  e-st-32-structures-scope, composite-structures, allowables,
  knock-down-factors, ndt, environment-conditioning, failure-modes,
  building-block."
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
  tags: [ecss, e-st-32-structures-scope, composite-structures, allowables, knock-down-factors, ndt, environment-conditioning, failure-modes, building-block]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Composite Structure Verification (space-systems/ecss/composite-structure-verification)

Use when the task is to verify composite structure under ECSS-E-ST-32C
clause 4.6.4 — confirming allowable basis, knock-down factor completeness,
failure-mode analysis coverage, environmental conditioning of test articles,
NDT plan coverage, and building-block test pyramid compliance.

## Domain quick reference

- Clause 4.6.4 imposes additional requirements on composite structures beyond
  the generic metallic-structure verification path. Four areas are checked in
  sequence: allowable derivation, analysis completeness, test conditioning, and
  NDT planning.
- Design allowables for composites must be derived on a statistical basis.
  A-basis (99th-percentile lower bound, 95 % confidence) is required wherever
  failure of a single load path would be catastrophic; B-basis (90th-percentile,
  95 % confidence) is acceptable for redundant load paths. Using an arbitrary
  mean value or an untraced data-sheet number is a non-compliance.
- Knock-down factors translate coupon-level allowables into design values that
  account for environment (temperature), moisture absorption (wet conditioning),
  and statistical scatter between test lots and the production population.
  All three knock-down factors must be traceable to test evidence or a
  conservative bounding assumption.
- Composite analysis must address four distinct failure modes: fiber failure
  (tensile or compressive fiber rupture), matrix cracking (transverse or
  in-plane resin cracking), delamination (out-of-plane separation of adjacent
  plies), and inter-laminar shear failure (shear-driven separation at the
  ply interface). An analysis that accounts for only net-section stress without
  separating these modes is incomplete under clause 4.6.4.
- Environment conditioning before structural testing means the test article
  must absorb moisture or undergo thermal cycling to reach the worst-case
  in-service condition before load is applied. The conditioning state recorded
  on the test article must match the design environment that drives the
  allowable being verified.
- NDT for composites must cover all primary and secondary structure. For each
  part the NDT plan must nominate a method (ultrasonic C-scan,
  through-transmission ultrasonic, radiography, thermography, or shearography)
  and record the critical defect size — the smallest flaw that must be
  detectable — so that the method's sensitivity can be confirmed.
- The building-block approach requires test evidence from at least the coupon
  level and the component level. Element and sub-component levels are strongly
  recommended but coupon and component are mandatory under the clause.

## Workflow

1. Collect the list of composite design allowables and verify that each carries
   a stated statistical basis. Flag any allowable without an explicit A-basis or
   B-basis designation. For any primary (single-load-path) structure confirm the
   basis is A-basis; a B-basis value for a single-load-path part is a finding.
2. For each allowable, confirm three knock-down factors are applied and traced:
   temperature, moisture, and scatter. Flag any allowable where one or more
   of these three factors is absent from the derivation record.
3. List the composite failure modes covered by the analysis and verify that all
   four required modes are addressed: fiber failure, matrix cracking,
   delamination, and inter-laminar shear. Flag any mode that is absent.
4. For each test article, compare its recorded conditioning state with the
   design environment condition it is intended to validate. Flag any mismatch
   (e.g., a test article conditioned room-temperature-dry being used to validate
   a hot-wet design allowable).
5. Cross-reference the NDT plan against the complete list of composite structure
   parts. For every primary or secondary part, confirm an NDT entry exists, the
   method is in the approved set, and a critical defect size is recorded.
   Flag missing entries, unknown methods, and absent defect-size assessments.
6. Survey the test pyramid: list the test levels represented across all test
   articles. Confirm that coupon-level and component-level tests are both
   present. Flag either mandatory level if absent.
7. Aggregate all findings. A composite part is not verified under clause 4.6.4
   until all six check lists are empty.

## Pitfalls

- Using a single worst-case environmental knock-down factor and omitting the
  scatter factor — scatter accounts for lot-to-lot variability and is required
  separately from the environmental factors even when the environmental margin
  appears large.
- Treating fiber-dominated laminate failure as the only failure mode and
  omitting matrix cracking — matrix cracking can govern in thin-laminate
  or off-axis loading cases and must be explicitly analyzed.
- Conditioning test coupons but not the structural-level test article — the
  conditioning requirement applies at every level of the building block
  pyramid. An unconditioned sub-component test does not substitute for a
  conditioned component test.
- Recording NDT method and coverage without stating the critical defect size —
  the detectability assessment is only credible if the minimum flaw size the
  method must find is documented; omitting it leaves the NDT plan
  unverifiable.
- Presenting coupon test data as sufficient verification — clause 4.6.4
  requires at least component-level evidence; coupon allowables alone do not
  close the verification loop.

## Behavior contract (gate 3)

The allowable-basis, knock-down-factor, failure-mode-coverage,
environment-conditioning, NDT-coverage, and test-pyramid logic is exercised
by the gate 3 contract test: scripts/test_composite_structure_verification.py
against scripts/composite_structure_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_composite_structure_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
