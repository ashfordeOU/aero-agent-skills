---
name: e1002-post-landing
description: "Use when an element's mission profile includes physical return of hardware to Earth (descent capsule, sample-return canister, recoverable payload, splashdown-recovered stage) and the post-landing verification stage of ECSS-E-ST-10-02C must be run: confirm applicability, assess each recovered item's condition against its pre-flight baseline, flag safety-critical findings, and track items that could not be recovered for alternate evidence. Trigger: post-landing verification, recovery, returned hardware, descent capsule, sample return, splashdown, recovered payload, E-ST-10-02, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, e-st-10-02c, post-landing, recovery, verification-stage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Post-Landing Verification (space-systems/ecss/e1002-post-landing)

Use when the task is running the post-landing verification stage under
ECSS-E-ST-10-02C for an element whose mission profile returns hardware
to Earth.

## Domain quick reference

- ECSS-E-ST-10-02C clause 5.2.4.6 adds post-landing to the set of
  verification stages (alongside qualification, acceptance, pre-launch,
  in-orbit -- see the sibling e1002-stages leaf) for elements whose
  mission profile brings hardware physically back to Earth: a descent
  or re-entry capsule, a sample-return canister, a recoverable payload,
  or a stage recovered after splashdown.
- The stage is conditional, not universal: it applies "where
  applicable" -- an element that stays in orbit through disposal (no
  physical return) has no post-landing stage at all.
- Post-landing verification compares the condition of each recovered
  item (structure, mechanisms, thermal protection system, pyrotechnics,
  propulsion residuals, payload or samples, data recorders) against its
  pre-flight baseline, to confirm the item survived descent/landing as
  predicted and to close out any requirements that could only be
  verified after recovery.
- Not every item is guaranteed to be recoverable intact: an item lost,
  destroyed, or otherwise not physically recovered cannot be verified
  by inspection and needs alternate evidence (e.g. telemetry recorded
  before loss of signal) instead of being silently dropped.

## Workflow

1. Determine applicability: does the element's mission profile include
   physical return of hardware to Earth? If not, the post-landing stage
   does not apply and no further steps are needed.
2. If applicable, enumerate the recovery item list for the element
   (structure, mechanisms, thermal protection system, pyrotechnics,
   propulsion residuals, payload/samples, data recorders -- only the
   types actually present on the element).
3. For each item, record its recovery status (recovered intact,
   recovered degraded, not recovered) and whether its condition matches
   the pre-flight baseline.
4. Classify each item's verification outcome: not recovered -> not
   verifiable by inspection (alternate evidence required); recovered
   degraded, or recovered but not matching baseline -> verified with
   findings (anomaly needs engineering disposition); recovered intact
   and matching baseline -> verified.
5. Collect open findings (items needing disposition) and unverifiable
   items (items needing alternate evidence) separately -- both are gaps
   that block stage close-out until resolved.
6. Close out the post-landing stage only once every open finding and
   every unverifiable item carries a recorded disposition; an element
   that was never applicable closes out trivially.

## Pitfalls

- Running post-landing verification on an element that never returns
  to Earth (wasted effort; the stage is conditional per clause
  5.2.4.6).
- Treating "not recovered" as equivalent to "no finding" -- a lost or
  destroyed item is a verification gap requiring alternate evidence,
  not a pass.
- Closing out the stage while a safety-critical item still has an open
  finding or missing disposition.
- Forgetting that "recovered degraded" is itself a finding even when
  the item's condition still nominally matches the pre-flight baseline
  on the checked characteristics.

## Behavior contract (gate 3)

The applicability, outcome-classification, findings-collection, and
close-out logic is exercised by the gate 3 contract test:
scripts/test_e1002_post_landing.py against
scripts/e1002_post_landing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_post_landing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
