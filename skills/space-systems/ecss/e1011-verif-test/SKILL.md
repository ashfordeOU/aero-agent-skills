---
name: e1011-verif-test
description: "Use when verify human factors engineering (HFE) requirements for a space system by ground tests and demonstrations per ECSS-E-ST-10-11C §4.11.3 and Annex D: identify each HFE requirement needing ground verification, assign a verification method (test, demonstration, analysis, or inspection), map each test or demonstration method to its Annex D event category, check that all mandatory Annex D ground events are covered, evaluate pre-event readiness criteria, and aggregate pass, fail, and pending status across all requirements into an overall compliance determination. Trigger: ecss, e-st-10-system-scope, hfe, human-factors, ground-test, verification, annex-d, hfe-testing, ergonomics."
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
  tags: [ecss, e-st-10-system-scope, hfe, human-factors, ground-test, verification, annex-d, hfe-testing, ergonomics]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS HFE Ground Verification — Tests and Demonstrations (space-systems/ecss/e1011-verif-test)

Use when the task is to verify human factors engineering (HFE)
requirements for a crewed space system through ground tests and
demonstrations in accordance with ECSS-E-ST-10-11C §4.11.3 and its
Annex D ground-test protocol.

## Domain quick reference

- §4.11.3 requires that HFE requirements be verified through observable
  ground activities — tests (measured outcomes) or demonstrations
  (observed functional performance) — rather than analysis or inspection
  alone, when the requirement concerns crew interaction with hardware or
  software.
- Annex D defines the mandatory ground-test event categories that must
  each be covered by at least one test or demonstration before the
  verification programme is complete. The mandatory set includes:
  functional task performance, ergonomic and anthropometric assessment,
  cognitive workload measurement, display and control interface
  evaluation, and emergency procedure demonstration. Non-mandatory
  event categories (label and cue verification, maintenance task
  demonstration, environmental ergonomics) are addressed when in scope.
- Verification methods are coded T (test), D (demonstration),
  A (analysis), and I (inspection). Only T and D methods are considered
  observable and count toward covering an Annex D mandatory event; an A
  or I method alone is insufficient for requirements that require
  observable crew performance.
- Pre-event readiness criteria must be met before each Annex D event
  begins: procedures available and approved, any measurement tools or
  anthropometric fixtures calibrated, personnel qualified, and the
  relevant hardware or software version baselined.

## Workflow

1. Inventory every HFE requirement subject to ground verification and
   assign a verification method (T, D, A, or I). For each T or D
   assignment, identify the Annex D event category the activity will
   address.
2. Check structural validity of each requirement record: all mandatory
   fields present, method code recognised, and — for T or D — a valid
   Annex D event mapping present.
3. Check mandatory Annex D event coverage: confirm at least one T or D
   requirement maps to each mandatory event category. Flag every
   uncovered mandatory event as a gap finding.
4. Before each scheduled Annex D event, evaluate the readiness criteria
   checklist; record which criteria are unmet and defer the event until
   the checklist is clear.
5. Record the outcome of each event against its requirement (PASS,
   FAIL, or PENDING). A FAIL requires root-cause investigation and a
   re-test plan before the verification closure review.
6. Aggregate pass, fail, and pending counts across all requirements.
   The verification programme is compliant only when the total is
   non-zero, fail is zero, and pending is zero, and no mandatory Annex
   D event gap findings remain.

## Pitfalls

- Accepting an analysis or inspection record as coverage for a
  mandatory Annex D event — observable performance of the crew is the
  intent of §4.11.3; an A or I entry for a crew-interaction requirement
  is a gap, not a closure.
- Closing a PENDING requirement as PASS without a recorded test outcome
  — the status field must be set by an authorised event record, not by
  inference from related activities.
- Treating a partial Annex D event (executed but criteria unmet at
  start) as a valid test — readiness criteria are gate conditions;
  results obtained when the gate was not cleared are not accepted.
- Conflating coverage of non-mandatory Annex D events with mandatory
  ones — only the five mandatory event categories close the §4.11.3
  gap; additional events provide complementary evidence but do not
  substitute for missing mandatory coverage.

## Behavior contract (gate 3)

The verification-method parsing, structural validation, mandatory event
coverage check, readiness evaluation, compliance summary, and findings
aggregation logic is exercised by the gate 3 contract test:
scripts/test_e1011_verif_test.py against
scripts/e1011_verif_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_verif_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
