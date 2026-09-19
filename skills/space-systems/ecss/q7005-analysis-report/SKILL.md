---
name: q7005-analysis-report
description: "Document an infrared organic contamination analysis in the reporting format of ECSS-Q-ST-70-05C, or grade a report already issued. Use when a run is finished and the record has to state the method used, the spectra taken, the level reached and the judgement drawn, and a reviewer needs to know whether it holds together. Asks each section for only the content that particular run owes, recomputes the areal level from the report's own residue mass, area and recovery, refuses a named contaminant with no reference spectrum behind it, refuses a judgement with no level printed beside it, and separates an arithmetic defect from a tidying observation. Trigger: ecss, q-st-70-05-ir-contamination-scope, ir-contamination-analysis-report, spectra-reference-traceability, areal-level-recomputation-check, judgement-versus-required-level, reporting-resolution-versus-uncertainty."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-analysis-report, ir-contamination-analysis-report, spectra-reference-traceability, areal-level-recomputation-check, judgement-versus-required-level, reporting-resolution-versus-uncertainty]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Analysis Report (space-systems/ecss/q7005-analysis-report)

Use when the task is the reporting step of an ECSS-Q-ST-70-05C infrared
contamination analysis — writing, or grading, the record of the method
used, the spectra taken, the level obtained and the judgement drawn
against the level the surface had to meet.

## Domain quick reference

- A report carries four separate loads: what was done, what was seen,
  what it came to, and what it means. Grading them apart is the point,
  because a report is routinely thorough on the method and silent on the
  spectra, and one completeness figure hides exactly that.
- What a report owes depends on what the run was. An indirect method
  owes the solvent, the recovery fraction and a blank, because without
  them the level cannot be reconstructed or trusted. A direct read owes
  none of the three, and asking for them turns a sound report red.
- Naming a contaminant is a claim, and the claim rests on a comparison.
  A report that names a species without the reference spectrum it was
  matched against has recorded an impression. The species name is the
  part most likely to be quoted downstream, so it is the part that most
  needs its evidence attached.
- The level is recomputable. Residue mass over sampled area, lifted by
  the recovery, has to land on the level the report states, and a
  mismatch is arithmetic, not style. The most common cause is a recovery
  that was declared and then never applied.
- A judgement without the level it was made against is an opinion. The
  limit is printed beside the verdict, and a verdict that contradicts
  the report's own numbers is worse than no verdict at all, because it
  travels further than the numbers do.
- A non-detect is reported as its quantitation limit, as a bound. Nobody
  can read a blank field, and a zero in that field is a claim no
  instrument has ever supported.
- Writing a level to more places than its uncertainty supports is untidy
  rather than wrong. It is reported as an observation so the next issue
  can fix it, and it does not stop the report being used.

## Workflow

1. Validate the typed content: a named item, a known method kind, a
   known judgement token, and non-negative masses, areas, recoveries and
   levels.
2. Assemble the field list this run owes — the four sections always, the
   indirect extras when the method was indirect, the reference spectrum
   when a species is named, and a level or a quantitation limit
   according to whether anything was detected.
3. Collect the owed fields left empty, counting a whitespace-only string
   as empty, and report completeness as a fraction of what was owed.
4. Recompute the areal level from the residue mass, the sampled area and
   the recovery, and compare it with the stated level within half a step
   of the resolution the report was written at.
5. Derive the judgement the report's own numbers support and compare it
   with the judgement stated.
6. Separate blocking findings — a missing owed field, a level that does
   not follow, an unsupported species, a judgement without or against
   its limit — from observations that only ask for a tidier next issue.
7. Verdict: reportable, reportable with observations, or not reportable;
   then group a set of reports by that verdict.

## Pitfalls

- Grading every report against one fixed content list. A direct read
  then fails for a missing solvent it never used, and the list loses its
  authority the first time someone overrides it.
- Reading the stated level instead of recomputing it. A recovery
  declared and not applied passes every inspection that only reads.
- Treating a named species as a result rather than a claim. Without the
  reference spectrum the name is the least supported line in the report
  and the most quoted.
- Printing a verdict without the level it was measured against. The
  reader cannot re-derive it, and a later change of requirement leaves
  no trace in the record.
- Reporting a non-detect as zero, or as an empty cell. The bound is the
  quantitation limit and it belongs in the report.
- Blocking a report for a resolution that is merely over-fine. Mixing
  tidying observations into the blocking list trains reviewers to
  override the list.

## Behavior contract (gate 3)

The section field lists, the conditional field derivation, the missing
field scan, the level recomputation and agreement test, the implied
judgement, the blocking-versus-observation split and the report-set
grouping are exercised by the gate 3 contract test:
scripts/test_q7005_analysis_report.py against
scripts/q7005_analysis_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7005_analysis_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
