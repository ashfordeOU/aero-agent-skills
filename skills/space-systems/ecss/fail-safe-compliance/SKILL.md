---
name: fail-safe-compliance
description: "Use when verify fail-safe structural compliance under ECSS-E-ST-32C clause 6.3.3: identify each fail-safe item in the structure, determine the governing damage scenario (element loss, through-crack, or partial-crack), compute residual strength after that damage and compare it against the required residual load capability, confirm the inspection method and interval provide at least two detection opportunities before catastrophic failure, and assess whether widespread fatigue damage conditions could cause simultaneous loss of multiple load-path elements before detection. Each item produces a compliance verdict with explicit findings. Trigger: ecss, e-st-32-structures-scope, fail-safe, residual-strength, widespread-fatigue-damage, inspection-interval, damage-scenario, structural-integrity, fail-safe-compliance."
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
  tags: [ecss, e-st-32-structures-scope, fail-safe, residual-strength, widespread-fatigue-damage, inspection-interval, damage-scenario, structural-integrity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fail-Safe Item Compliance (space-systems/ecss/fail-safe-compliance)

Use when the task is the fail-safe compliance assessment required by
ECSS-E-ST-32C clause 6.3.3 — verifying that each fail-safe structural item
retains adequate residual strength after a partial failure event, that damage
is detectable before catastrophic failure, and that widespread fatigue damage
conditions are precluded within the inspection schedule.

## Domain quick reference

- Clause 6.3.3 requires fail-safe structural items to maintain sufficient
  residual strength after the assumed damage state (element loss, through-crack,
  or bay failure) until that damage is detected and repaired. Residual strength
  is compared directly against the design limit load or an agreed residual load
  level — no knockdown beyond the damage itself is applied.
- The damage scenario for each item must be defined before the residual strength
  can be assessed. Recognized scenario types are: element-loss (complete loss of
  one redundant load path), through-crack (crack penetrating the full thickness),
  partial-crack (crack across part of the cross-section), and bay-failure (loss
  of a skin bay between frames or stringers). An unrecognized scenario type is
  rejected before calculation begins.
- The inspection requirement has two dimensions: detectability (the damage must
  be large enough for the chosen inspection method to reliably find it) and
  interval (the inspection must be repeated often enough to guarantee at least
  two opportunities to detect damage before the structure reaches the critical
  damage size). Both dimensions must pass independently.
- Widespread fatigue damage (WFD) describes a condition in which multiple
  similar structural elements (e.g., a row of fastener holes) accumulate fatigue
  damage simultaneously. A WFD risk is flagged when the fraction of each
  element's individual fatigue life consumed within one inspection interval
  reaches or exceeds the WFD threshold (default 0.5), indicating that a
  significant portion of the population could fail between consecutive
  inspections.

## Workflow

1. Inventory every structural item that relies on load-path redundancy for its
   structural category and confirm each one is recorded as fail-safe (not
   safe-life or damage-tolerant). Reject any item with an unrecognized category
   before it enters the compliance check.
2. For each fail-safe item, define the governing damage scenario: select from
   element-loss, through-crack, partial-crack, or bay-failure. Reject any
   scenario type not on the recognized list.
3. Compute the residual strength of the damaged structure and compare it against
   the required residual load (typically the design limit load). Record the
   margin; flag any item where residual strength falls below the required load.
4. Estimate the number of load cycles for the initial post-failure damage to
   grow to the critical size using a constant growth-rate model. Divide the
   result by the inspection interval to determine the number of available
   inspection opportunities; flag any item with fewer than two opportunities.
5. Check detectability: confirm that the initial post-failure damage size is at
   or above the detection threshold for the chosen inspection method. Flag any
   item where the initial damage is below that threshold.
6. Assess WFD potential: for each group of similar structural elements, compute
   the fraction of individual fatigue life consumed per inspection interval. Flag
   any group where that fraction meets or exceeds the WFD threshold.
7. Aggregate findings per item. An item is fail-safe compliant only when all
   four checks (residual strength, inspection interval, detectability, WFD) are
   clear. Report each finding with explicit numeric detail.

## Pitfalls

- Applying the full design load as the residual load without accounting for the
  agreed residual load level — some programmes accept a fraction of limit load
  as the residual requirement; using the wrong reference load either understates
  or overstates compliance.
- Counting inspection opportunities from the time of manufacture rather than
  from the onset of the assumed damage — the interval window starts when the
  damage scenario is first possible, not when the structure enters service.
- Treating detectability as satisfied because a capable inspection method is
  listed, without confirming that the initial damage size exceeds the method's
  threshold — a capable method applied to damage below its threshold produces
  no detection.
- Overlooking WFD by analysing only individual fastener holes or elements in
  isolation — WFD is a population-level effect and must be assessed across the
  full group of similar elements sharing the same fatigue loading.
- Calling an item compliant when only the residual strength check passes — all
  four checks (residual strength, interval, detectability, WFD) must be clear
  simultaneously.

## Behavior contract (gate 3)

The damage-scenario validation, residual-strength check, cycle-to-critical
estimation, inspection-interval check, detectability check, and WFD assessment
are exercised by the gate 3 contract test:
scripts/test_fail_safe_compliance.py against
scripts/fail_safe_compliance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fail_safe_compliance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
