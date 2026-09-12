---
name: drd-fracture-control-plan
description: "Use when draft a fracture control plan (FCP) per ECSS-E-ST-32C Annex F:
  identify fracture-critical items whose structural failure would be catastrophic,
  compute the critical flaw size from fracture toughness and operating stress, verify
  the NDI detection threshold covers the assumed initial flaw, confirm the proof-test
  factor meets the minimum screening threshold, and confirm the safe-life factor
  provides adequate damage tolerance margin. Flag items where the critical flaw size
  does not exceed the assumed initial flaw, where NDI cannot detect the assumed flaw,
  or where proof-test and safe-life factors fall below programme minimums.
  Trigger: ecss, e-st-32-structures-scope, fracture-control-plan,
  fracture-critical-items, damage-tolerance, ndi, proof-test, safe-life,
  fracture-toughness."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control-plan, fracture-critical-items, damage-tolerance, ndi, proof-test, safe-life, fracture-toughness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture Control Plan (space-systems/ecss/drd-fracture-control-plan)

Use when the task is drafting or verifying a Fracture Control Plan (FCP) under
ECSS-E-ST-32C Annex F — screening structural items for fracture criticality,
establishing assumed initial flaw sizes from NDI capability, computing critical flaw
sizes from fracture mechanics, and verifying proof-test and safe-life factors.

## Domain quick reference

- Annex F divides structural items into two categories based on failure consequence:
  fracture-critical items (FCIs) whose fracture-mode failure would be catastrophic
  (loss of mission, loss of crew, or loss of vehicle), and fracture-non-critical items
  whose fracture failure carries non-catastrophic consequence. Only FCIs receive the
  full fracture-mechanics verification chain.
- The assumed initial flaw size is the largest flaw that a given NDI technique may
  fail to detect — it is treated as present in every FCI. The NDI technique is valid
  for the FCP only when its detection threshold is at or below the assumed flaw size
  (i.e. the technique can reliably find flaws that large).
- The critical flaw size a_c is derived from plane-strain fracture mechanics:
  a_c = (K_Ic / (Y × σ × √π))², where K_Ic is the plane-strain fracture toughness,
  Y is the geometry/stress-intensity factor, and σ is the peak operating stress.
  For an FCI to be acceptable, a_c must exceed the assumed initial flaw size — if it
  does not, the flaw that NDI may have missed can propagate to fracture at operating
  load.
- The proof-test factor (proof load / limit load) screens out FCIs containing flaws
  at or above the critical size; ECSS-E-ST-32C Annex F sets a minimum of 1.25 for
  metallic fracture-critical hardware.
- The safe-life factor (analysis lifetime / design lifetime) accounts for scatter in
  crack-growth data; Annex F sets a minimum of 4.0 for fracture-critical items in
  the safe-life verification path.

## Workflow

1. Inventory every structural item in scope and determine its failure consequence:
   "catastrophic" maps to fracture-critical, "non_catastrophic" maps to
   fracture-non-critical. Reject an unrecognized consequence label before it enters
   the plan. Fracture-non-critical items require only standard structural verification
   and exit the FCP process here.
2. For each FCI, record the NDI technique and its detection threshold, then establish
   the assumed initial flaw size as the threshold value (or a value agreed with the
   programme). Verify that the NDI detection threshold does not exceed the assumed
   flaw size; a technique whose threshold is larger than the assumed flaw cannot
   guarantee detection of that flaw and must be replaced or supplemented.
3. Compute the critical flaw size from the material fracture toughness K_Ic, the
   geometry factor Y for the feature geometry, and the peak operating stress σ:
   a_c = (K_Ic / (Y × σ × √π))². Compare a_c against the assumed initial flaw size;
   flag an item where a_c ≤ assumed flaw as failing the fracture-mechanics margin
   check.
4. Verify the proof-test factor for each FCI: proof factor = proof load / limit load
   must meet or exceed 1.25. Flag items below threshold.
5. Verify the safe-life factor for each FCI: analysis lifetime / design lifetime must
   meet or exceed 4.0. Flag items below threshold.
6. Aggregate all findings per FCI: an item is FCP-compliant only when the
   NDI detectability check, the critical-vs-assumed flaw check, the proof-test factor
   check, and the safe-life factor check each produce no violation.

## Pitfalls

- Applying the FCP screening criteria to non-critical items and then drawing
  compliance conclusions from the result — fracture-non-critical items do not carry
  FCP requirements and must exit the process at step 1.
- Setting the assumed initial flaw size smaller than the NDI detection threshold —
  this creates a hidden gap where flaws larger than assumed but below the threshold
  may exist undetected and go unchecked in the fracture-mechanics analysis.
- Treating a critical flaw size that equals the assumed flaw as passing — Annex F
  requires a_c to strictly exceed the assumed flaw so that the flaw NDI may have
  missed cannot propagate to fracture at the limit stress.
- Omitting the geometry factor Y from the critical flaw size formula or defaulting
  it to 1.0 for complex geometries — Y captures stress concentration and free-surface
  effects; an incorrect Y leads to an unconservative a_c.
- Reading a missing proof-test or safe-life factor record as a pass — an unrecorded
  factor means the verification was never performed, which is itself a finding, not
  an acceptable default.

## Behavior contract (gate 3)

The categorization, critical-flaw-size computation, NDI detectability, proof-test
factor, safe-life factor, and aggregated FCI review logic is exercised by the gate 3
contract test: scripts/test_drd_fracture_control_plan.py against
scripts/drd_fracture_control_plan_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_drd_fracture_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
