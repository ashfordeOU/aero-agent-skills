---
name: life-extension-reactivation
description: "Use when assess pressure hardware for service-life extension, reactivation after dormancy, or re-acceptance following storage or design modification under ECSS-E-ST-32C §4.2.4: determine whether remaining fatigue and fracture life covers the requested extension with adequate safety margin, verify that a reactivated item passes all mandatory seal, structural, and functional checks within its maximum dormancy limit, and evaluate whether a component seeking re-acceptance has confirmed material traceability, a valid or updated certification basis, and supporting test data. Flag items that require re-qualification before service resumption. Trigger: ecss, e-st-32-structures-scope, life-extension, reactivation, re-acceptance, pressure-hardware, dormancy, re-qualification, safety-margin, fatigue-life."
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
  tags: [ecss, e-st-32-structures-scope, life-extension, reactivation, re-acceptance, pressure-hardware, dormancy, re-qualification, safety-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Service-Life Extension, Reactivation, and Re-acceptance (space-systems/ecss/life-extension-reactivation)

Use when the task is the service-life extension, reactivation, or
re-acceptance assessment of pressure hardware (PH) under
ECSS-E-ST-32C §4.2.4 — determining whether remaining life, dormancy
history, and certification basis support continued or resumed operation
of a hardware item beyond its original design envelope.

## Domain quick reference

- **Service-life extension**: the original certified life (in cycles or
  operating hours) represents the design basis. When an extension is
  requested, the remaining life (certified minus consumed) must cover
  the requested additional duration with a sufficient safety margin.
  If operating loads have increased since original certification, the
  effective remaining life is reduced proportionally (Miner's rule
  analogue); the safety margin is computed against this reduced value.
  An extension is approvable only when the margin meets or exceeds the
  programme minimum; otherwise re-qualification is required.
- **Reactivation**: a hardware item that has been stored or dormant for
  an extended period is subject to degradation mechanisms (seal
  relaxation, corrosion initiation, lubricant migration) that are not
  captured by the original certification. Before reactivation, a
  dormancy duration check is performed against the programme maximum
  limit; items exceeding that limit require re-qualification before any
  re-use. Items within the limit must pass a seal integrity inspection,
  a structural/visual inspection, and a functional test as a minimum
  readiness gate.
- **Re-acceptance**: a component seeking re-acceptance (after storage,
  re-use, or following a design change) must have a confirmed
  unbroken material traceability chain, an applicable certification
  basis, and current test or inspection data supporting its condition.
  A design change automatically elevates the re-acceptance path to
  conditional, requiring a full re-qualification test campaign;
  if no supporting test data exists, re-acceptance is rejected outright.
  Loss of material traceability is an unconditional rejection regardless
  of other findings.

## Workflow

1. Identify the assessment type for the hardware item: life extension,
   reactivation, re-acceptance, or a combination of all three. Collect
   the certified life, consumed life, dormancy duration, certification
   documentation status, and material traceability records before
   entering any calculation step.
2. For a life extension request, compute the remaining life
   (certified minus consumed). If new operating loads exceed the
   original design loads, reduce the effective remaining life using
   the fractional load increase. Compute the safety margin as
   (effective remaining life / extension request) multiplied by the
   applied safety factor. Compare against the programme minimum safety
   factor; reject if below threshold.
3. For a reactivation request, compare the dormancy duration against
   the programme maximum dormancy limit. If exceeded, flag as
   requiring re-qualification and stop; do not proceed to inspection
   checks until re-qualification is complete. Within the limit,
   verify seal integrity, structural and visual condition, and
   functional performance in that order. Any failed check is a
   rejection.
4. For re-acceptance, first confirm material traceability. If
   traceability cannot be confirmed, reject immediately. Then check
   whether the design has changed since original certification: a
   changed design requires a full re-qualification campaign and, if
   test data exists, yields conditional acceptance; without test data,
   reject. For an unchanged design, verify the original certification
   is still applicable and that current test or inspection data is on
   record; each absence yields conditional acceptance with a mandatory
   action item.
5. Aggregate all findings across the three assessment types into an
   overall verdict: any rejected or re-qualification-required finding
   makes the overall verdict rejected; conditional findings without
   rejections yield a conditional verdict; only when all three paths
   are clear is the overall verdict approved.
6. Document each finding with its specific reason and any required
   actions, and carry the aggregated verdict into the structural
   compliance record for the hardware item.

## Pitfalls

- Applying the full certified life as if it were entirely remaining
  when part has already been consumed — only the unused portion is
  available to cover an extension, and ignoring consumed life
  overstates the achievable margin.
- Treating a dormancy period that exceeds the programme limit as merely
  a longer inspection — exceeding the maximum dormancy triggers
  mandatory re-qualification; no inspection outcome can substitute for
  a re-qualification test on a hardware item that has been stored
  beyond its permitted period.
- Accepting a design-changed item on the basis of original
  certification alone — a design change invalidates the original
  certification basis and requires a re-qualification campaign; the
  absence of test data after a design change is an outright rejection,
  not a gap to be noted and accepted provisionally.
- Conflating "material traceability confirmed" with "paperwork filed" —
  traceability must cover the full chain from raw material to the
  specific hardware serial number; a gap anywhere in that chain is an
  unconfirmed traceability and triggers rejection.
- Overlooking the load-increase correction when computing safety margin
  for a life extension — if the item will operate at higher loads than
  its original design basis, the effective remaining life is lower than
  the nominal remaining life, and computing margin against the nominal
  value overstates the true margin.

## Behavior contract (gate 3)

The life extension, reactivation readiness, re-acceptance, and
aggregated summary logic is exercised by the gate 3 contract test:
scripts/test_life_extension_reactivation.py against
scripts/life_extension_reactivation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_life_extension_reactivation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
