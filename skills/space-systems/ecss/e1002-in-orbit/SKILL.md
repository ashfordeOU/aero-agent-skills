---
name: e1002-in-orbit
description: "Use when a flight item has requirements that cannot be fully closed on the ground and must be verified once on orbit under ECSS-E-ST-10-02C clause 5.2.4.5: identify which requirements need the in-orbit stage, close them out against commissioning evidence, and reopen a previously closed requirement for re-verification when an in-orbit anomaly affects it. Trigger: in-orbit verification, commissioning, on-orbit performance, anomaly re-verification, post-launch checkout, e-st-10-02, verification stage, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, verification-stage, in-orbit, commissioning, anomaly, re-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS In-Orbit Verification & Anomaly-Driven Re-verification (space-systems/ecss/e1002-in-orbit)

Use when the task is closing out the in-orbit verification stage under
ECSS-E-ST-10-02C: deciding which requirements need it, tying closure to
commissioning evidence, and reopening requirements after an in-orbit
anomaly.

## Domain quick reference

- ECSS-E-ST-10-02C clause 5.2.4.5 is the last of the flight-facing
  verification stages (after qualification, acceptance, and pre-launch,
  see the sibling e1002-stages leaf). It covers requirements whose
  compliance can only be confirmed under the actual operational orbital
  environment -- deployment mechanisms, in-flight thermal/vacuum
  behaviour, RF link performance, microgravity-dependent behaviour --
  and that no ground stage can close out regardless of how well the
  ground stage went.
- The in-orbit stage is closely tied to the post-launch commissioning
  campaign: commissioning activities are the primary source of evidence
  used to close in-orbit requirements. A requirement not covered by any
  commissioning activity, or covered by an activity that has not yet
  run, stays open rather than defaulting to pass.
- An in-orbit anomaly that affects a requirement already closed by
  commissioning evidence reopens that requirement for re-verification;
  it is not re-closed until the anomaly's corrective action is itself
  verified (see the sibling e10-changes-nc leaf for the anomaly/
  non-conformance process itself, which this leaf does not own).

## Workflow

1. For each requirement, decide whether the in-orbit stage applies:
   flag it as in-orbit-dependent when its compliance can only be
   observed under the actual orbital environment, independent of any
   ground_stage_method already recorded for it.
2. For requirements where the in-orbit stage does not apply, mark them
   not_applicable to this stage -- they were already closed on ground
   and are out of scope here.
3. For requirements where it does apply, gather the commissioning
   activity results that list that requirement id and aggregate them:
   any failing result closes the requirement failed; otherwise any
   not-yet-run result leaves it open; only all-passing results close it
   verified; no covering activity at all also leaves it open.
4. Build the in-orbit verification matrix (one status entry per
   requirement id) and list the requirement ids still open, failed, or
   pending re-verification -- these block declaring the in-orbit
   verification record, and by extension the commissioning result
   review, complete.
5. When an in-orbit anomaly is reported, identify every requirement id
   it affects. For any of those ids currently closed verified, reopen
   it: reverification_required while the corrective action is
   unverified, reverified once the corrective action has itself been
   verified. Requirements not currently verified, or not named by the
   anomaly, are left unchanged.

## Pitfalls

- Treating a successful ground qualification or acceptance result as
  sufficient to close a requirement flagged in-orbit-dependent -- clause
  5.2.4.5 exists precisely because ground testing cannot confirm these.
- Defaulting an uncovered requirement (no commissioning activity lists
  it) to verified instead of leaving it open.
- Closing a requirement on a commissioning activity that has not yet
  run, rather than waiting for its actual pass/fail result.
- Re-closing an anomaly-affected requirement as verified before its
  corrective action has been verified, instead of the intermediate
  reverification_required state.

## Behavior contract (gate 3)

The stage-applicability, commissioning-outcome, matrix-build, and
anomaly-reverification logic is exercised by the gate 3 contract test:
scripts/test_e1002_in_orbit.py against
scripts/e1002_in_orbit_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_in_orbit.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
