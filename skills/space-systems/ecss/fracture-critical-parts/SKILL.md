---
name: fracture-critical-parts
description: "Use when determine which structural parts require fracture control under ECSS-E-ST-32C clause 4.2.2: screen each part by consequence of failure, applied stress ratio, pressurization status, and structural role to establish fracture criticality, assign the required fracture control method (proof test or non-destructive examination), verify that proof test factors meet the minimum allowable threshold, confirm that inspection sensitivity can detect cracks smaller than the critical crack size, and aggregate compliance findings per part. Trigger: ecss, e-st-32-structures-scope, fracture-critical, fracture-control, nde, proof-test, structural-integrity, fci."
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
  tags: [ecss, e-st-32-structures-scope, fracture-critical, fracture-control, nde, proof-test, structural-integrity, fci]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture-Critical-Part Screening and Fracture Control (space-systems/ecss/fracture-critical-parts)

Use when the task is to determine which parts in a space structure require
fracture control under ECSS-E-ST-32C clause 4.2.2 — screening parts for
fracture criticality, assigning a control method, and verifying that the
selected method meets its quantitative requirements.

## Domain quick reference

- A part is fracture critical when its fracture (from a pre-existing crack)
  could produce a catastrophic or critical system consequence AND the part
  meets at least one structural trigger: it is pressurized, it carries
  primary load, or its applied stress exceeds half of the material yield
  strength. Parts below both the consequence threshold and all structural
  triggers fall outside the fracture control scope.
- Two fracture control methods are recognised: proof test and
  non-destructive examination (NDE). A proof test applies a load above the
  operating limit to detect or fail any crack that would be critical at
  service load; NDE inspects the part and finds cracks before they reach a
  critical size. Either method may be required alone or in combination.
- Proof test compliance requires a proof factor (proof load divided by limit
  load) that meets the programme minimum threshold. A factor below the
  minimum does not eliminate cracks large enough to be critical at service
  load.
- NDE compliance requires that the inspection technique can reliably detect
  cracks smaller than half the critical crack size (a factor-of-two margin
  between detectable size and critical size). A technique that can only
  detect cracks close to or larger than the critical size provides no useful
  margin.
- The critical crack size for a part is derived from its fracture toughness
  and applied stress; it must be documented before any fracture control
  method can be verified.

## Workflow

1. For every candidate part, record: consequence of failure (catastrophic,
   critical, major, or minor), structural role (primary, secondary, or
   non-structural), whether the part is pressurized, applied stress, yield
   strength, and fracture toughness. Reject any part record missing these
   fields before proceeding.
2. Screen for fracture criticality: a part is fracture critical if its
   consequence is catastrophic or critical AND at least one of the following
   applies — the part is pressurized, the structural role is primary, or the
   stress ratio (applied stress / yield strength) is ≥ 0.5. Parts that fail
   both the consequence gate and all structural triggers are not fracture
   critical; record the reason and exclude them from further fracture control
   steps.
3. For each fracture-critical part, confirm a fracture control method is
   assigned (proof test, NDE, or both). A fracture-critical part with no
   method assigned is a compliance finding that blocks acceptance.
4. If the method includes proof test: verify the proof factor is at or above
   the programme minimum (1.25 for primary metallic structure per the
   programme fracture control plan). A sub-minimum factor means cracks of
   critical size at service load can survive the proof test undetected.
5. If the method includes NDE: verify the detectable crack size is at most
   half the critical crack size. Confirm the critical crack size is on record
   before making this check; an unset critical crack size is itself a finding.
6. Aggregate all findings per part. A part is fracture-control compliant only
   when it either (a) is not fracture critical, or (b) is fracture critical,
   has a method assigned, and all method-specific checks pass.

## Pitfalls

- Screening only by consequence and ignoring structural triggers — a part
  with a catastrophic consequence but secondary role, low stress, and no
  pressurization does not automatically require fracture control under this
  procedure; applying it blindly wastes resource on genuinely non-critical
  parts.
- Treating a proof factor just above 1.0 as adequate — cracks near the
  critical size at service load survive a 1.05-factor proof test; only factors
  at or above the programme minimum are accepted.
- Accepting NDE results without checking the detection limit against the
  critical crack size — an NDE report that found "no indications" is
  meaningless for fracture control if the technique cannot detect cracks
  smaller than the critical size.
- Leaving the critical crack size undocumented and reading a blank field as
  "no critical cracks exist" — an absent critical crack size means the
  analysis was never done, which is itself a finding.
- Using the same minimum proof factor for pressure vessels as for primary
  structure — pressure vessels typically carry a higher minimum proof factor
  than generic primary structure; check the programme fracture control plan
  for the applicable limit.

## Behavior contract (gate 3)

The screening, proof-test, and NDE compliance logic is exercised by the
gate 3 contract test:
scripts/test_fracture_critical_parts.py against
scripts/fracture_critical_parts_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fracture_critical_parts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
