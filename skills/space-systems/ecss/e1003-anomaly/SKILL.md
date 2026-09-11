---
name: e1003-anomaly
description: "Use when resolving anomalies or failures detected during spacecraft
  testing under ECSS-E-ST-10C §4.3.4: categorize each failure by domain (hardware,
  software, environmental, electrical, mechanical), determine containment actions
  scaled to the severity level (critical/major/minor), verify the anomaly record
  captures all required documentation fields, assign a disposition code (accept
  as-is, repair and retest, waiver required, reject, pending analysis), and identify
  which test cases must be repeated as a consequence of the anomaly or its corrective
  action. Trigger: ecss, e-st-10c, anomaly, test-anomaly, containment, disposition,
  retest-decision, anomaly-resolution, test-failure."
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
  tags: [ecss, e-st-10c, anomaly, test-anomaly, containment, disposition, retest-decision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS AIT — Anomaly Handling During Testing (space-systems/ecss/e1003-anomaly)

Use when the task is to resolve an anomaly or unexpected failure detected
during spacecraft testing per ECSS-E-ST-10C §4.3.4 — categorizing the failure
domain, applying immediate containment, verifying the anomaly record, assigning
a disposition, and deriving which tests must be repeated.

## Domain quick reference

- §4.3.4 requires that every unexpected event or failure observed during a
  test be formally captured before any recovery action is taken; containment
  preserves the as-found hardware state and test data so the failure can be
  accurately reproduced and investigated.
- Anomalies are grouped by failure domain: hardware (component or structural
  failure), software (crash, data corruption, protocol error), environmental
  (temperature or pressure exceedance, contamination event), electrical
  (power anomaly, ESD event, signal degradation), or mechanical (mechanism
  jam, structural interference). Each anomaly belongs to exactly one domain.
- Severity determines containment urgency: critical anomalies require an
  immediate test halt, hardware isolation, and responsible-engineer
  notification; major anomalies require suspension of test activity and a
  risk-to-hardware assessment; minor anomalies permit continued testing with
  enhanced monitoring and documentation.
- Disposition codes drive what happens next: accept-as-is closes the anomaly
  without corrective action; repair-and-retest mandates a corrective action
  followed by a defined retest scope; waiver-required routes the anomaly to
  the configuration control authority; reject fails the item outright;
  pending-analysis holds the anomaly open while investigation continues.
- The retest scope is derived from the disposition and the set of test cases
  whose results may have been invalidated by the anomaly or by the repair
  action that follows.

## Workflow

1. Detect and immediately preserve the test state: record the exact test
   procedure reference, step number, time-stamp, and instrument readings at
   the moment of detection before touching any hardware or software controls.
2. Categorize the anomaly into exactly one failure domain (hardware, software,
   environmental, electrical, mechanical). Reject any anomaly type not in the
   defined domain set before proceeding — an uncategorized anomaly cannot be
   routed to the correct engineering authority.
3. Assess severity (critical, major, or minor) based on the potential for
   hardware damage, data loss, schedule impact, and mission-risk consequences.
   Execute the containment action list mandated by that severity level in
   order; do not skip steps.
4. Verify the anomaly record contains all required documentation fields:
   anomaly identifier, description of the observed behavior, detected-at
   timestamp, affected item reference, test procedure reference, name of the
   person who detected it, and initial findings. Flag each missing field as
   a record gap before assigning disposition.
5. Assign a disposition code. If the code is pending-analysis, flag the anomaly
   as open and do not advance to retest derivation until a final disposition
   is set. Reject any disposition string outside the recognized code set.
6. Derive the retest scope: for repair-and-retest dispositions, union the set
   of test cases directly affected by the anomaly with any test cases whose
   scope overlaps the repair action. For all other dispositions, the mandatory
   retest set is empty (though the responsible engineer may still elect to
   rerun tests at their discretion).
7. Close the anomaly record when the disposition is final, all record gaps are
   resolved, and either the retest scope is complete or the disposition does
   not require retesting.

## Pitfalls

- Touching hardware or resetting software before capturing the as-found state —
  containment must precede any recovery action; data lost at this step cannot
  be reconstructed.
- Treating a pending-analysis disposition as closed — an anomaly in this state
  is still open and must not be counted toward test completion.
- Defining the retest scope only as the test that surfaced the anomaly —
  the repair may invalidate results from earlier tests that exercised the
  same interface or subsystem; those must be included in the scope.
- Leaving the anomaly record with missing fields and proceeding to disposition —
  §4.3.4 requires a complete record before the configuration control authority
  can act on the disposition.
- Assigning a minor severity to an anomaly that involves any hardware damage
  risk, even if the immediate observable impact is small — severity must reflect
  the worst credible consequence, not the observed symptom.

## Behavior contract (gate 3)

The anomaly-categorization, containment-action derivation, record-field
validation, disposition handling, and retest-scope derivation logic is
exercised by the gate 3 contract test:
scripts/test_e1003_anomaly.py against scripts/e1003_anomaly_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1003_anomaly.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
