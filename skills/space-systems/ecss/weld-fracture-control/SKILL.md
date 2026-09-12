---
name: weld-fracture-control
description: "Use when assess weld fracture-control compliance for space structural hardware under ECSS-E-ST-32C clause 8.3: categorize each weld by quality level (class A, B, or C according to its stress state, service loading, and criticality), screen weld imperfections against ISO 6520-1 acceptance limits for the assigned class, compute the safe-life fatigue margin by comparing the applied stress-cycle spectrum to the S-N allowable for the weld category, and verify that the NDT method and coverage are sufficient to guarantee detection of the assumed initial flaw size. Trigger: ecss, e-st-32-structures-scope, weld, fracture-control, safe-life, fatigue, ndt, iso-6520-1, weld-imperfection, weld-quality."
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
  tags: [ecss, e-st-32-structures-scope, weld, fracture-control, safe-life, fatigue, ndt, iso-6520-1, weld-imperfection, weld-quality]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Weld Fracture Control (space-systems/ecss/weld-fracture-control)

Use when the task is the weld fracture-control assessment of
ECSS-E-ST-32C clause 8.3 — categorizing welds by quality class,
screening ISO 6520-1 imperfections against class-specific acceptance
limits, computing the safe-life fatigue margin, and verifying that the
NDT programme can detect the postulated initial flaw.

## Domain quick reference

- Clause 8.3 requires each weld in a space structure to be assigned a
  quality class before any fracture-control or fatigue work is done.
  Class A covers welds that are fracture-critical (their failure would
  be catastrophic and cannot be detected or contained); class B covers
  welds in primary load-carrying structure that are not fracture-critical;
  class C covers welds in secondary or non-structural members. A single
  weld cannot straddle two classes — it must be assigned to the highest
  applicable class.
- ISO 6520-1 groups weld imperfections into six families: cracks
  (group 100), cavities such as porosity and gas pores (group 200),
  solid inclusions (group 300), lack of fusion and penetration
  (group 400), imperfect shape including undercut and overlap
  (group 500), and miscellaneous imperfections (group 600). The
  acceptance limit for each group tightens as the weld class increases.
  Cracks and lack-of-fusion flaws are not acceptable in class A or B
  welds under any circumstance.
- Safe-life fatigue assessment requires that the safe-life factor —
  the ratio of the S-N allowable cycle count at the applicable stress
  range to the applied design lifetime cycle count — meets or exceeds
  the class-dependent minimum. Class A demands the highest factor
  (4.0), class B a moderate factor (2.0), and class C a minimum factor
  (1.5). The S-N allowable must correspond to the specific weld
  geometry and surface condition, not a generic plate allowable.
- NDT must both cover the required fraction of each weld length and
  use a method whose minimum detectable flaw size is no larger than the
  assumed initial flaw size used in the fracture analysis. Volumetric
  methods (ultrasonic, radiographic) are required for class A welds to
  detect embedded flaws; surface methods alone (penetrant, magnetic
  particle) do not satisfy class A inspection requirements.

## Workflow

1. Assign each weld a quality class: class A if the weld is
   fracture-critical (failure leads to a catastrophic event not
   detectable or mitigated by design), class B if it is in primary
   load-carrying structure, class C otherwise. Record the basis for
   the assignment against each weld joint identifier.
2. Collect the as-built weld inspection record for each joint and
   identify every imperfection reported with its ISO 6520-1 group
   code and measured size. Screen each imperfection: compare its
   measured size to the acceptance limit for its group under the
   assigned weld class. Reject the weld if any imperfection exceeds
   its limit, or if a crack or lack-of-fusion flaw is present in a
   class A or B weld regardless of size.
3. For welds subject to cyclic loading, extract the applied
   stress-cycle spectrum (stress range and associated cycle count at
   that range over the design lifetime). Identify the S-N allowable
   for the weld category and surface condition. Compute the safe-life
   factor as the allowable cycle count divided by the applied cycle
   count. Confirm that this factor meets the class minimum.
4. Identify the NDT method(s) applied to each weld, the fraction of
   the weld length inspected, and the minimum detectable flaw size for
   the chosen method. Compare the minimum detectable flaw size against
   the assumed initial flaw size used in the fracture analysis.
   Confirm that coverage meets the class requirement (100% for class A,
   50% for class B, spot-check for class C).
5. If any check from steps 2–4 produces a rejection, record the
   finding against the weld joint ID. A weld is fracture-control
   compliant only when all imperfection, safe-life, and NDT checks
   pass simultaneously.

## Pitfalls

- Assigning a weld class based on component category rather than weld
  criticality — a weld in a secondary bracket that attaches a
  fracture-critical item may itself be fracture-critical and must be
  assigned class A regardless of the bracket's classification.
- Applying an S-N allowable from the base material or a smooth
  specimen to a weld toe — weld geometry and residual stresses reduce
  the allowable significantly compared to parent material, and using
  the wrong allowable unconservatively overstates the safe-life factor.
- Counting surface NDT coverage toward the class A 100% requirement —
  penetrant and magnetic-particle testing detect only surface-breaking
  flaws; embedded flaws remain undetected, so class A requires
  volumetric inspection (UT or RT) across the full weld length.
- Treating a weld as compliant when no fatigue data are on record
  because no explicit cyclic load was identified — welds in launch
  structures experience vibration-induced fatigue and the absence of
  a documented fatigue spectrum is itself a finding, not a pass.
- Comparing the minimum detectable flaw size of the most sensitive
  method on the list rather than the method actually used on each weld
  — NDT adequacy must be tied to the specific inspection record for
  each joint, not to the capability of a method that was available but
  not applied.

## Behavior contract (gate 3)

The weld-class assignment, imperfection screening, safe-life fatigue
factor, and NDT coverage and flaw-detection logic are exercised by the
gate 3 contract test: scripts/test_weld_fracture_control.py against
scripts/weld_fracture_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_weld_fracture_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
