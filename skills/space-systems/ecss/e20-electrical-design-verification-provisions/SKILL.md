---
name: e20-electrical-design-verification-provisions
description: "Use when determine the verification method and closure milestone for every electrical and electronic engineering requirement under ECSS-E-ST-20C clause 4.3.1: pick the method that actually produces evidence for the requirement characteristic at hand, check that the planned review is not earlier than the selected method can physically close, confirm each provision names an evidence artefact, and prove the verification matrix covers every requirement with no orphan provision pointing at a requirement that does not exist. Trigger: ecss, e-st-20-electrical-scope, electrical-verification-provisions, verification-method-selection, verification-milestone-closure, review-of-design-method, verification-evidence-artefact, electrical-verification-matrix."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electrical-design-verification-provisions, verification-method-selection, verification-milestone-closure, review-of-design-method, electrical-verification-matrix, verification-evidence-artefact]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Design Verification Provisions (space-systems/ecss/e20-electrical-design-verification-provisions)

Use when the task is setting or auditing the verification provisions of
ECSS-E-ST-20C clause 4.3.1 -- assigning a verification method and a
closure milestone to each electrical and electronic engineering
requirement of clause 4, and proving the resulting verification matrix
is complete and internally consistent.

## Domain quick reference

- Clause 4.3.1 offers four verification methods. Each one produces a
  different kind of evidence: analysis (a calculation or model
  prediction), review-of-design (a documented argument from the design
  data and heritage), test (a measurement on representative hardware),
  and inspection (a direct observation of the as-built item). A
  requirement is verified by one of these, not by "it looks fine".
- Not every method is acceptable for every requirement characteristic.
  A workmanship requirement is observable, so it closes by inspection
  only. A part-selection requirement is a design-data argument, so it
  closes by review-of-design or inspection, never by test. A
  performance-margin or electromagnetic-compatibility requirement is
  quantitative, so it closes by test or analysis, never by a
  review-of-design narrative. Functional-behaviour and
  interface-compatibility requirements accept the widest set.
- Method selection is driven by what is available, not by preference.
  If representative hardware exists and demonstrating the requirement
  would not destroy it, test is preferred. If the requirement is
  quantitative but no representative hardware is available (or the
  demonstration is destructive), analysis carries it. Otherwise the
  design-data argument carries it.
- A method cannot close before the evidence it needs exists. Ordering
  the project reviews SRR, PDR, CDR, QR, AR: a design-data argument can
  close at PDR, an analysis needs the detailed design so it closes no
  earlier than CDR, an inspection needs built hardware so it closes no
  earlier than QR, and a test closes at QR when a qualification model is
  available, otherwise it slips to AR on flight hardware. A provision
  that claims an earlier milestone than its method allows is optimistic
  planning, not a verification provision.
- The matrix is only complete when every requirement carries at least
  one provision and every provision points at a requirement that
  exists. Duplicate requirement identifiers make coverage unprovable and
  are rejected outright.

## Workflow

1. Collect the clause 4 electrical and electronic requirements. Each one
   carries an identifier and a characteristic (functional behaviour,
   performance margin, interface compatibility, electromagnetic
   compatibility, workmanship, part selection). Reject an unrecognized
   characteristic and reject a duplicated identifier before going
   further.
2. For each requirement, derive the preferred method from whether the
   requirement is quantitative, whether representative hardware is
   available, and whether the demonstration is destructive.
3. For each provision on record, check that the chosen method is in the
   acceptable set for that requirement's characteristic. A method
   outside the set cannot produce the evidence the requirement needs.
4. Derive the earliest milestone at which the chosen method can close,
   then compare it with the planned milestone. Flag any provision
   planned earlier than its method allows.
5. Confirm every provision names a concrete evidence artefact (report,
   procedure and results, inspection record). A provision with no named
   artefact closes nothing.
6. Run the coverage check both ways: requirements with no provision, and
   provisions referencing an identifier that is not in the requirement
   set.
7. The verification provisions are acceptable only when the per-
   provision findings and the coverage findings are both empty.

## Pitfalls

- Writing "test" against every requirement because it sounds strongest
  -- a workmanship or part-selection requirement has no test that closes
  it, and the provision will be rejected at the review it was meant to
  close.
- Planning a test closure at CDR. No hardware evidence exists at CDR;
  the provision either needs a qualification model at QR or slips to AR.
- Treating an empty findings list as coverage. A matrix with zero
  provisions produces zero per-provision findings and is still entirely
  uncovered -- coverage is a separate check and must be run on the
  requirement set, not on the provision set.
- Letting two requirements share an identifier. Coverage is computed by
  identifier, so a duplicate silently marks an unverified requirement as
  covered; this is raised as an error, not a finding.
- Recording a method and milestone but no evidence artefact. The
  artefact is what is actually reviewed at closure; without it the
  provision is a plan, not a provision.

## Behavior contract (gate 3)

The method-acceptability, method-selection, earliest-closure-milestone,
per-provision and matrix-coverage logic is exercised by the gate 3
contract test: scripts/test_e20_electrical_design_verification_provisions.py
against scripts/e20_electrical_design_verification_provisions_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e20_electrical_design_verification_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
