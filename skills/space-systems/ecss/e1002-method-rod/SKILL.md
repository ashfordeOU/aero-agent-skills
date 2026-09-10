---
name: e1002-method-rod
description: "Use when verify a requirement's compliance under the review-of-design method of ECSS-E-ST-10-02C clause 5.2.2.4: classify each design-evidence item (drawing, analysis report, design description, supplier certificate, heritage data, similarity data) as direct or heritage evidence, apply the admissibility rule for a safety-critical requirement backed only by heritage evidence, roll up each item's compliant, non_compliant, open, or not_applicable disposition into an overall requirement status, and assemble a review-of-design report entry per requirement while flagging any requirement absent from the report. Trigger: ecss, e-st-10-02c, review of design, rod, design evidence, heritage data, similarity data, verification report, requirement close-out."
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
  tags: [ecss, e-st-10-02c, review-of-design, verification-method, design-evidence, heritage-data, verification-report]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Review-of-Design Verification Method (space-systems/ecss/e1002-method-rod)

Use when the task is closing out a requirement by the review-of-design
method of ECSS-E-ST-10-02C clause 5.2.2.4 -- examining already-existing
design documentation against the requirement, rather than generating
new test or measurement data for this verification action.

## Domain quick reference

- Clause 5.2.2.4 describes review of design as a documented
  examination of existing design data -- drawings, analysis reports,
  design descriptions, supplier certificates, or heritage/similarity
  records from a qualified prior design -- against the requirement
  text, closed out by a review-of-design report. It does not itself
  generate new test or measurement data; that is what distinguishes it
  from the test and analysis methods.
- Evidence items split into two families: direct evidence (drawing,
  analysis report, design description, supplier certificate) speaks to
  the current design itself, while heritage evidence (heritage data,
  similarity data) draws on the qualification history of a prior
  design or a documented similarity assessment. An evidence item
  outside both families is rejected before it enters the review.
- A safety-critical requirement backed only by heritage evidence (no
  direct evidence item at all) is not admissible for review-of-design
  close-out unless a similarity assessment has been explicitly
  approved to extend that heritage to the safety-critical case; this
  mirrors the sibling e10-req-verif-methods rule that safety-critical
  requirements should not be closed by review of design alone.
- Each evidence item carries a disposition -- compliant, non_compliant,
  open (still under review), or not_applicable -- and the requirement's
  overall status rolls up from the full evidence set: any non_compliant
  item fails the requirement outright; failing that, any open item
  keeps the requirement open; failing that, at least one compliant item
  closes it compliant; a set containing only not_applicable items
  closes nothing and is itself a finding (no evidence actually
  demonstrated compliance).

## Workflow

1. For each requirement assigned the review-of-design method, gather
   its evidence items and classify each one as direct or heritage
   evidence; reject an evidence item of an unrecognized type before it
   enters the review.
2. Check the evidence set's admissibility: a safety-critical
   requirement with heritage evidence only, and no approved similarity
   assessment extending it, is flagged rather than closed.
3. Record a disposition (compliant, non_compliant, open, not_applicable)
   for every evidence item, then roll the set up into one overall
   requirement status by the non_compliant > open > compliant >
   no_compliant_evidence precedence.
4. Assemble the review-of-design report: one entry per requirement,
   carrying its evidence set, admissibility issues, rolled-up status,
   and the reviewer of record; a report entry without a reviewer of
   record is rejected.
5. Confirm every requirement assigned the review-of-design method has a
   report entry; flag any requirement id missing from the report
   rather than treating silence as compliance.
6. Only treat a requirement as closed when its rolled-up status is
   compliant and it carries no outstanding admissibility issue; carry
   every other case forward to engineering disposition.

## Pitfalls

- Accepting a heritage-only evidence set for a safety-critical
  requirement without an approved similarity assessment -- heritage
  data from a different design does not automatically transfer to a
  safety-critical claim.
- Reading "no non_compliant item" as closed -- an open item still means
  the review is incomplete, and a set of only not_applicable items
  never demonstrated compliance in the first place.
- Treating a compliant rolled-up status as sufficient to close the
  requirement while an admissibility issue is still outstanding on the
  same entry.
- Leaving a requirement out of the review-of-design report and
  interpreting its absence as a pass; clause 5.2.2.4 closes a
  requirement through a documented report entry, not through silence.

## Behavior contract (gate 3)

The evidence-classification, admissibility, status-rollup, and
report-completeness logic is exercised by the gate 3 contract test:
scripts/test_e1002_method_rod.py against
scripts/e1002_method_rod_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_method_rod.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
