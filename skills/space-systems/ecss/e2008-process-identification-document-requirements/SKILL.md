---
name: e2008-process-identification-document-requirements
description: "Use when a process identification document is reviewed for content rather than for coverage. Assess the content a process identification document carries when it describes the production processes an assembly is built by, the structure ECSS-E-ST-20-08C Annex F expects: name the document section nobody wrote, test each process record for the fields that make a step re-runnable by somebody else, check every control parameter carries a band that brackets its nominal and is neither zero wide nor too wide to control anything, confirm the stated flow numbers run first to last with none repeated or skipped, and hold the described processes against the list the document itself declares. Trigger: ecss, e-st-20-08c-annex-f, process-identification-document-content, assembly-process-record-fields, assembly-process-control-parameter-band, assembly-process-flow-sequence, process-identification-document-section-audit."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-process-identification-document-requirements, e-st-20-08c-annex-f, process-identification-document-content, assembly-process-record-fields, assembly-process-control-parameter-band, assembly-process-flow-sequence, process-identification-document-section-audit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Process Identification Document -- Expected Content (space-systems/ecss/e2008-process-identification-document-requirements)

Use when the task is Annex F of ECSS-E-ST-20-08C: a process identification
document describes the production processes an assembly is built by, and
somebody has to decide whether that document actually describes them. This
leaf reviews the document as a document -- its sections, its per-process
records, its control parameters and its process flow -- rather than asking
whether the process list matches what the line really runs, which is the
coverage question a separate leaf answers.

## Domain quick reference

- A process name is not a process description. Two suppliers can both write
  "interconnector welding" and build hardware that behaves differently, so the
  record has to say where it runs, on what equipment, with which materials and
  under which parameters.
- The record is written for a reader who was not there. Every field the
  document leaves out is a decision the operator makes silently on the day,
  and it is never the same decision twice.
- A control parameter without limits is a wish. A nominal on its own tells the
  line what to aim at and nothing about what is acceptable, so a parameter
  with no band is treated as unbounded rather than as tight.
- A zero-width band is unholdable. Stating minimum, nominal and maximum as the
  same number reads as extreme control and means the process is out of
  tolerance the moment it runs.
- A band's width only means something next to its own nominal. Two degrees on
  a 250 degree bake and two degrees on a 20 degree cure are different degrees
  of control, so the width is taken as a fraction of the nominal magnitude,
  and a nominal of zero simply skips that test rather than dividing by it.
- The flow numbers are a claim about order. Numbers that repeat leave two
  steps claiming the same position, numbers that skip leave a step nobody
  wrote, and both read as an ordered document until they are counted.
- The document has to agree with itself. A process in the list with no record,
  or a record for a process the list never mentions, is a self-contradiction
  that needs no outside information to detect.

## Workflow

1. Read the document identifier; every later finding is reported against it.
2. Audit the document against the required section set, treating an empty
   string, an empty list and an empty mapping as absent.
3. Audit each process record against the required field set, treating an empty
   parameter list and a non-integer flow position as absent fields.
4. Assess each control parameter: refuse an inverted band outright, report a
   nominal with no limits as unbounded, catch a band that does not bracket its
   nominal, catch a zero-width band, then compare the width to the policy
   ceiling as a fraction of the nominal magnitude.
5. Rank each process: absent fields first, then too few parameters, then
   parameters that are present but unusable, then a missing operator
   qualification or work instruction reference.
6. Test the flow positions for repeats, skips and numbers outside the run.
7. Hold the described processes against the declared list in both directions.
8. Return a document verdict that is acceptable only when every section is
   present, every process is described, the flow is one run and the document
   agrees with its own list.

## Pitfalls

- Reviewing the document for what it says about each process and never for
  which sections are absent. A page with no gap in it looks finished, and the
  absent section is the one nobody asked for.
- Accepting a parameter table because every row has a number in it. A table of
  nominals with no limits passes that reading and controls nothing.
- Treating a zero-width tolerance as strictness. It is the one band that
  guarantees a nonconformance on the first build.
- Comparing band widths across parameters in their own units. A band is tight
  or loose only relative to what it is a band around.
- Reading the flow as ordered because the records appear in order on the page.
  Page order and stated position are different claims, and only the stated
  ones are the document's commitment.
- Checking the process list against the line and calling that the content
  review. That is the coverage question; a document can match the line exactly
  and still describe nothing a second reader could run.

## Behavior contract (gate 3)

The required section set, the required process field set, the section audit,
the process field audit, the policy-gated fields, the control parameter band
assessment, the flow sequence test, the ranked process verdict and the whole
document verdict are exercised by the gate 3 contract test:
scripts/test_e2008_process_identification_document_requirements.py against
scripts/e2008_process_identification_document_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_process_identification_document_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
