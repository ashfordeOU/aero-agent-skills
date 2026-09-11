---
name: e1003-el-crewed
description: "Use when run crewed-mission element tests under ECSS-E-ST-10C §6.5.7:
  vibroacoustic emission, human factors engineering (HFE), toxic offgassing, and
  audible noise. Categorize each test record into one of the four mandated test families,
  evaluate measured results against acceptance limits, and flag any missing test families
  or limit exceedances before crewed-mission qualification sign-off. Each family has
  distinct acceptance criteria: vibroacoustic levels in dB, HFE pass/fail judgments,
  offgassing concentration in mg/m³, and audible noise in dB(A). A crewed element
  is compliant only when all four families produce no findings. Trigger: ecss,
  e-st-10-system-scope, crewed-mission, vibroacoustic, hfe, toxic-offgassing,
  audible-noise, crewed-element-test."
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
  tags: [ecss, e-st-10-system-scope, crewed-mission, vibroacoustic, hfe, toxic-offgassing, audible-noise]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS E-ST-10C — Crewed-Mission Element Tests (space-systems/ecss/e1003-el-crewed)

Use when the task is to plan, execute, or verify the crewed-mission element
tests mandated by ECSS-E-ST-10C §6.5.7: vibroacoustic emission, human factors
engineering (HFE), toxic offgassing, and audible noise. These four test families
are specifically required for any hardware that will be installed in or interfaces
with a crewed cabin, and each has acceptance criteria distinct from standard
equipment-level tests.

## Domain quick reference

- §6.5.7 mandates four test families for crewed elements: vibroacoustic emission
  (the noise and vibration radiated by the equipment into the cabin structure and
  atmosphere), HFE test (human factors engineering verification that interfaces and
  controls meet crewed-habitability requirements), toxic offgassing (confirmation
  that no material in the equipment releases chemical species above the allowable
  cabin-atmosphere concentration), and audible noise (in-cabin acoustic level at
  the crew position under representative operating conditions).
- Each test family has its own measured quantity and acceptance limit: vibroacoustic
  emission is measured in dB against a structural/acoustic emission limit; HFE is a
  pass/fail judgment against a defined HFE checklist; toxic offgassing is measured
  as a concentration in mg/m³ against a per-substance cabin limit; and audible noise
  is measured in dB(A) at the crew position against the habitability noise limit.
- All four test families must be completed before a crewed element may be accepted;
  a missing test family is itself a finding that blocks acceptance.
- Vibroacoustic and audible-noise checks use the same physical quantity (acoustic
  pressure level in dB) but address different interfaces: vibroacoustic emission is
  a source characterization (what the equipment radiates into the structure/cabin),
  while audible noise is an environment check at the crew position (total ambient
  level with the equipment operating). Do not substitute one for the other.

## Workflow

1. Identify every equipment item in scope of §6.5.7 (all hardware installed in or
   directly interfacing with the crewed cabin). Build a test matrix with one row per
   item and one column per test family.
2. For each test record presented, categorize the record into one of the four test
   families (vibroacoustic_emission, hfe_test, toxic_offgassing, audible_noise).
   Reject any record whose test type is not recognized before it enters the
   acceptance assessment.
3. Evaluate each record against its acceptance limit:
   - Vibroacoustic emission: compare measured emission level (dB) to the equipment
     emission limit (dB). A measurement above the limit is a finding.
   - HFE test: verify the test judgment is a formal pass against the HFE checklist.
     A failed or incomplete judgment is a finding.
   - Toxic offgassing: compare measured offgassing concentration (mg/m³) for each
     substance to the cabin atmosphere limit for that substance. A measurement above
     any substance limit is a finding.
   - Audible noise: compare measured noise level at the crew position (dB(A)) to
     the habitability noise limit (dB(A)). A measurement above the limit is a finding.
4. After evaluating all available records, identify test families that have no
   record on file for a given equipment item. Flag each missing family as an
   acceptance blocker.
5. An equipment item is crewed-mission compliant only when its findings list is empty
   and all four test families are covered.

## Pitfalls

- Accepting a vibroacoustic emission result as satisfying the audible-noise
  requirement — these are separate families measuring different things; one result
  does not waive the other.
- Treating an HFE test as optional for equipment that is "mostly automated" —
  §6.5.7 applies to all crewed-mission elements regardless of automation level;
  the HFE family must always be covered.
- Carrying forward toxic offgassing results from a prior material build state —
  any change in materials (substitution, coating, adhesive reformulation) voids the
  prior result and requires a new offgassing measurement.
- Treating a missing test record as a pass with zero findings — a missing test
  family is an acceptance blocker, not a neutral state; it must appear in the
  findings as a missing-family flag.

## Behavior contract (gate 3)

The test-type categorization, per-family acceptance evaluation, missing-family
detection, and full crewed-element review logic is exercised by the gate 3
contract test: scripts/test_e1003_el_crewed.py against
scripts/e1003_el_crewed_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_el_crewed.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
