---
name: e2008-sca-process-identification-document
description: "Assess the supplier process identification document that clause 6.2 of ECSS-E-ST-20-08C asks for before a solar cell assembly is qualified: hold the processes the assembly is actually built with against the set the document declares, check each declared process names the production document that controls it, confirm every control parameter carries a tolerance band that brackets its nominal and is drawn tightly enough to control anything, flag a process the assembly depends on that cites no qualification evidence, and check the issue date precedes the campaign. Use when an SCA process identification document, production control baseline or process qualification list has to be reviewed. Trigger: ecss, e-st-20-08c, sca-process-identification-document, sca-production-control-document, sca-process-step-coverage, sca-control-parameter-tolerance-band, sca-process-qualification-evidence, sca-process-document-issue-date."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-process-identification-document, e-st-20-08c, sca-process-identification-document, sca-production-control-document, sca-process-step-coverage, sca-control-parameter-tolerance-band, sca-process-qualification-evidence, sca-process-document-issue-date]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Process Identification Document (space-systems/ecss/e2008-sca-process-identification-document)

Use when the task is clause 6.2 of ECSS-E-ST-20-08C: the supplier writes a
production control document that identifies the cell assembly processes to be
qualified, and somebody has to decide whether that document actually
identifies them. This leaf grades the document on coverage, on control, on
evidence and on when it was issued.

## Domain quick reference

- The document is a gate, not a catalogue. Its job is to fix, before the
  campaign, which processes the assembly depends on, so that a process
  qualified later can be traced back to a commitment made earlier.
- A process that never reaches the document is never put forward for
  qualification. Coverage is therefore measured against the processes an
  assembly is genuinely built with — surface preparation, interconnector
  welding, coverglass bonding, cell-to-substrate bonding, bypass diode
  attachment, bus bar attachment, cleaning and handling — not against the
  list the supplier happened to submit.
- Naming a process is half the declaration. The other half is the production
  document that controls it: without that reference the process has a title
  and no floor instruction behind it.
- A control parameter needs a band, and the band needs to bracket the
  nominal. A band sitting entirely above or below the nominal value is a
  transcription defect that passes every build until somebody measures.
- Band width is the part reviewers skip. A tolerance drawn so wide that any
  plausible build sits inside it records the process rather than controlling
  it, so the width is measured as a fraction of the nominal and held against
  a declared limit.
- Criticality decides what evidence is owed. A process the assembly depends
  on carries a qualification evidence reference; a process held by production
  control alone closes without one, unless project policy says otherwise.
- Issue order is what the clause buys. A document issued after the campaign
  began records the build instead of defining it, so the issue date is
  compared with the campaign start date and reported as its own finding.

## Workflow

1. Validate each declared process: a name the required set recognises, an
   optional controlling document reference, a sequence of control parameters
   and an optional qualification evidence reference. Refuse a process the
   required set does not name rather than carrying it silently.
2. Grade every control parameter: normalise the band, refuse an inverted one,
   test whether it brackets the nominal, and express its width as a fraction
   of the nominal so it can be held against the policy limit.
3. Rank the process entry: a missing controlling document first, then a
   process that declares no parameter at all, then an uncontrolled parameter,
   then missing qualification evidence.
4. Measure coverage against the required process set and name every process
   the document leaves out.
5. Compare the coverage share with the policy minimum, absorbing
   floating-point representation error at the boundary with a named relative
   tolerance instead of moving the limit.
6. Compare the issue date with the campaign start date.
7. Report the whole assessment: per-process verdicts grouped by outcome, the
   coverage and accepted shares, and every finding in rank order.

## Pitfalls

- Grading the document against its own table of contents. A list that is
  internally consistent and omits coverglass bonding is still a document that
  never put coverglass bonding forward.
- Accepting a controlling document reference as proof of control. The
  reference says where the parameters live; an entry that cites a document
  and declares no parameter holds nothing at all.
- Reading a wide tolerance band as a generous one. A band no realistic build
  can leave is indistinguishable from having no band, which is why width is
  measured rather than merely present.
- Treating a band that excludes its own nominal as a rounding matter. It is a
  defect in the declaration and is reported as one, because production will
  build to the nominal and the inspection will read the band.
- Demanding qualification evidence from every process. A process held by
  production control alone does not owe a qualification report, and asking
  for one buries the critical processes that genuinely do.
- Merging the process outcomes into one pass or fail. A process with no
  controlling document and a wide band is one root cause and one fix; a
  merged verdict sends the supplier back for the wrong correction.
- Judging a coverage share that lands exactly on its policy minimum by bare
  arithmetic. The share is a ratio of two counts and the minimum is a round
  fraction, so a document meant to sit on the minimum can land a few units in
  the last place below it; the comparison absorbs that while the limit stays
  as declared.

## Behavior contract (gate 3)

The parameter validation, band bracketing and width grading, the ranked
process verdict, the coverage measurement, the issue-date precedence check
and the rolled-up document verdict are exercised by the gate 3 contract test:
scripts/test_e2008_sca_process_identification_document.py against
scripts/e2008_sca_process_identification_document_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_process_identification_document.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
