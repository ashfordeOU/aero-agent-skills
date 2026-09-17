---
name: q6013-justification-document-drd
description: "Audit whether a commercial part justification document can be issued. Use when an Annex F data item under ECSS-Q-ST-60-13C has to be judged complete: name every required section the draft never wrote, validate each entry's part, intended application, usage decision, rationale, residual risk and approving authority, hold each decision to its own evidence demand, refuse a high residual risk carried on an accept-as-is decision with nothing behind it, reconcile justified parts against the declared usage list in both directions, and report section coverage judged at unity under a named tolerance. Trigger: ecss, q-st-60-13c-annex-f, commercial-part-justification-document, part-usage-decision-evidence, residual-risk-on-accept-as-is, justification-section-coverage, commercial-part-usage-list-reconciliation."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-justification-document-drd, q-st-60-13c-annex-f, commercial-part-justification-document, part-usage-decision-evidence, residual-risk-on-accept-as-is, justification-section-coverage, commercial-part-usage-list-reconciliation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Justification Document DRD (space-systems/ecss/q6013-justification-document-drd)

Use when the task is the justification-document data item of ECSS-Q-ST-60-13C
Annex F — the record that has to exist behind a decision to use a commercial
electrical, electronic and electromechanical part, and what that record has to
contain before anyone can be asked to sign it.

## Domain quick reference

- A data item is a contents contract, not a template. It says what the
  document must be able to answer; a draft that reads well but never wrote the
  residual-risk section has not answered one of the questions, and the absence
  is what the review finds, not the prose quality.
- The unit of justification is the part in its intended application, not the
  part. The same commercial device can be sound in a warm, redundant, low-rate
  housekeeping role and unsound one board away, so the application is carried
  on the entry and not assumed from the part number.
- The decision and its evidence move together. Accepting a part as it stands
  leans on heritage, the manufacturer's own assessment and a derating case;
  accepting it on the back of extra testing leans on a test plan and the
  report that closed it. Citing four documents is not the test — citing the
  four the decision actually rests on is.
- A rejection is a justified decision too, and it is finished when the risk
  record behind it exists. A rejection that also carries mitigation actions is
  self-contradictory: nobody will perform them, so either the decision or the
  action list is the wrong one.
- Residual risk gates the decision, not the other way round. A high residual
  risk carried on an accept-as-is decision means the risk was written down and
  then not acted on, which is the exact combination the data item exists to
  surface.
- Coverage runs both ways against the usage list. A part being flown with no
  entry is the obvious gap; an entry for a part the build no longer uses means
  the document and the build have drifted, and either one may be stale.

## Workflow

1. Validate the document identity: the issuing project, the identifier, the
   issue and the date, so two copies cannot disagree with nothing to settle
   them.
2. Compare the required section set against the sections the draft carries,
   name each absent section on its own, and express the result as a
   section-coverage fraction judged at unity under a named tolerance.
3. Validate every entry — part, intended application, decision, rationale,
   residual risk, approving authority, evidence citations and mitigation
   actions — rejecting a rationale too short to stand as one and an evidence
   type cited twice.
4. Hold each decision to its own evidence demand and name every demanded
   document the entry never cited, type by type.
5. Apply the decision consistency rules: high residual risk against
   accept-as-is, a mitigation decision with no actions, a rejection carrying
   actions.
6. Reconcile the justified parts against the declared usage list in both
   directions.
7. Report the per-entry results, the absent sections, the coverage fraction,
   the reconciliation and a verdict carrying every finding.

## Pitfalls

- Grading the document on length. A thick justification with no residual-risk
  section answers fewer of the data item's questions than a short one that
  answers all of them.
- Accepting an evidence list without checking what the decision needed. Four
  citations satisfy a count, not a demand, and the demand differs by decision.
- Writing the application as the part's generic function. The application is
  where the part sits in this build, and it is what makes the same device
  acceptable in one slot and not in another.
- Letting a high residual risk ride on an accept-as-is entry. The risk was
  assessed; leaving it unmitigated turns the assessment into paperwork.
- Reconciling one way only. A used part with no entry is the visible gap; an
  entry for a part no longer used is the one that reveals a stale document.
- Stopping at the first finding. The document owner needs the whole list to
  close it in one issue rather than one issue per finding.

## Behavior contract (gate 3)

The identity validation, section-coverage assessment, per-entry validation,
decision-to-evidence demand, residual-risk consistency rules, two-way usage
list reconciliation and the overall fit-to-issue verdict are exercised by the
gate 3 contract test:
scripts/test_q6013_justification_document_drd.py against
scripts/q6013_justification_document_drd_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_justification_document_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
