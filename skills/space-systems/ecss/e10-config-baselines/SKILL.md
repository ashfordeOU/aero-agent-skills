---
name: e10-config-baselines
description: "Use when establishing the functional, allocated, or product configuration baseline for a space system under ECSS-E-ST-10C clause 5.4.2.2: classify the baseline type, confirm every earlier baseline in the functional-then-allocated-then-product sequence is already established, verify the gating milestone review (SRR for functional, PDR for allocated, CDR for product) has passed, check that the baseline's required configuration-management artifacts are on record, and aggregate the findings per baseline type so a program-level compliance status can be derived. Trigger: ecss, e-st-10-system-scope, configuration baseline, functional baseline, allocated baseline, product baseline, m-st-40, srr, pdr, cdr, configuration management milestones."
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
  tags: [ecss, e-st-10-system-scope, configuration-baseline, functional-baseline, allocated-baseline, product-baseline, m-st-40]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Configuration Baselines (space-systems/ecss/e10-config-baselines)

Use when the task is establishing a configuration baseline under
ECSS-E-ST-10C clause 5.4.2.2 -- determining whether the functional,
allocated, or product baseline for a space system can be established
at its correct program milestone, in the correct sequence, with the
configuration-management record it requires.

## Domain quick reference

- Clause 5.4.2.2 defines three configuration baselines established in
  a fixed sequence, each capturing a successively more detailed layer
  of the system definition: functional (the top-level requirements and
  functional interfaces), allocated (those requirements allocated down
  to each configuration item, plus the interfaces between them), and
  product (the build-to design and as-built record for each
  configuration item). A baseline may only be established once every
  earlier baseline in the sequence already exists -- there is no
  allocated baseline without a functional one, and no product baseline
  without both.
- Each baseline is gated by a program milestone review: the functional
  baseline by the system requirements review (SRR), the allocated
  baseline by the preliminary design review (PDR), and the product
  baseline by the critical design review (CDR). Establishing a
  baseline before its gating review has passed is out of sequence with
  the milestone plan under M-ST-40, regardless of whether the
  supporting documents exist.
- Each baseline also carries a minimum configuration-management record
  it must hold before it can be considered established: the functional
  baseline needs the top-level requirements document and the
  functional interface specification; the allocated baseline needs the
  per-configuration-item requirements and the interface control
  documents; the product baseline needs the build-to documentation,
  the as-built configuration list, and the verification close-out
  record. A baseline with its milestone passed but a document missing
  is not yet established -- the review flags the specific gap rather
  than treating "milestone passed" as sufficient.

## Workflow

1. Identify the baseline type under review (functional, allocated, or
   product). Reject a type outside this set before assessing it
   further.
2. Check sequence: confirm every baseline earlier than this one is
   already established. Flag the specific missing prior baseline(s)
   rather than a generic "not ready".
3. Check the milestone gate: confirm the baseline's required review
   (SRR / PDR / CDR) has passed. Flag the baseline against its
   specific required milestone when it has not.
4. Check the artifact record: confirm every required
   configuration-management artifact for this baseline type is on
   file. Flag the specific missing artifact ids.
5. Aggregate the three checks per baseline type; a baseline is ready
   to establish only when all three checks return no findings.
6. Across the program, evaluate all three baseline types together --
   an early-program state should show findings only on the baselines
   whose turn has not yet come, not spurious findings on a baseline
   that is already legitimately established.

## Pitfalls

- Treating a passed milestone review as sufficient on its own --
   clause 5.4.2.2 also requires the artifact record and the sequence
   position; a baseline with a passed CDR but no as-built configuration
   list is not yet an established product baseline.
- Allowing a later baseline to be established out of sequence because
   its own milestone has passed (e.g. PDR passed but SRR was skipped) --
   the allocated baseline cannot exist without the functional baseline
   underneath it, independent of which reviews happened to occur.
- Confusing the milestone that gates a baseline with the milestone
   that confirms it -- SRR/PDR/CDR gate the functional/allocated/
   product baselines respectively; downstream reviews (e.g. QR, AR)
   confirm readiness for later program stages and are out of scope for
   this leaf's gate check.
- Reading an empty missing-artifacts list as "fully compliant" when the
   sequence or milestone check already failed -- all three checks are
   independent findings and must all be clear, not just the last one
   evaluated.

## Behavior contract (gate 3)

The baseline-type validation, sequence, milestone-gate, and artifact
logic is exercised by the gate 3 contract test:
scripts/test_e10_config_baselines.py against
scripts/e10_config_baselines_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_config_baselines.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
