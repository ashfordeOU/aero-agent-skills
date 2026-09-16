---
name: e2008-bare-cell-process-identification-document
description: "Use when a bare cell production control document, process baseline or cell line qualification list has to be reviewed. Evaluate the supplier production control document that clause 7.2 of ECSS-E-ST-20-08C asks for before a bare solar cell design is qualified: hold the declared steps against the steps a cell is genuinely built with, check each step cites the floor instruction that controls it, confirm every control parameter carries a band that brackets its nominal and is drawn tightly enough to control anything, catch a step declared on a line other than the one being qualified, and check the document names the design under qualification and was issued before the campaign. Trigger: ecss, e-st-20-08c, bare-cell-process-identification-document, bare-cell-production-control-document, bare-cell-process-step-coverage, bare-cell-control-parameter-band, bare-cell-qualified-line-binding, bare-cell-design-baseline-identifier."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-bare-cell-process-identification-document, bare-cell-process-identification-document, bare-cell-production-control-document, bare-cell-process-step-coverage, bare-cell-control-parameter-band, bare-cell-qualified-line-binding, bare-cell-design-baseline-identifier]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells — Process Identification Document (space-systems/ecss/e2008-bare-cell-process-identification-document)

Use when the task is clause 7.2 of ECSS-E-ST-20-08C: the supplier prepares the
production control document for the bare cell design that is about to be
qualified, and somebody has to decide whether that document actually controls
the cell. This leaf grades it on coverage, on control, on the line it binds
to, and on the baseline and date it carries.

## Domain quick reference

- The document is a gate, not a description. Its job is to fix, before the
  campaign, how the cell is made, so that a qualification result can later be
  attached to a build that was committed to in advance.
- A step that never reaches the document was never put forward for
  qualification. Coverage is therefore measured against the steps a cell is
  genuinely built with -- wafer preparation, epitaxial growth, junction
  formation, antireflective coating, front and rear metallisation, mesa edge
  isolation, contact anneal and electrical sorting -- not against the list the
  supplier happened to submit.
- Naming a step is half a declaration. The other half is the production
  document that controls it: without that reference the step has a title and
  no floor instruction behind it, and a step that cites a document while
  declaring no parameter holds nothing at all.
- A control parameter needs a band, the band needs to bracket the nominal, and
  the width needs to mean something. A band sitting entirely above or below
  its nominal is a transcription defect that passes every build until somebody
  measures; a band no plausible build can leave records the step rather than
  controlling it, so width is carried as a fraction of the nominal.
- A cell line is a site, not a recipe. A step declared on a line other than
  the one under qualification moves the result onto different equipment,
  different operators and a different process history, so the line binding is
  read per step and reported on its own.
- The baseline and the date are the same question asked twice. A document that
  names another design controls other hardware, and a document issued after
  the campaign began records the build instead of defining it.

## Workflow

1. Take the document with the design under qualification, the line it is
   qualified on, its own design identifier, its issue date, the campaign start
   and one entry per declared process step.
2. Validate each step: a name the required set recognises, an optional
   controlling document reference, an optional production line, and a sequence
   of control parameters. Refuse a step the required set does not name rather
   than carrying it silently.
3. Grade every control parameter: refuse an inverted band, test whether it
   brackets the nominal, and express its width as a fraction of the nominal so
   it can be held against the policy cap.
4. Read the line the step is run on against the line under qualification.
5. Rank the step verdict -- no controlling document first, then no parameter,
   then an uncontrolled parameter, then an off-line step -- so the report names
   the root cause before the consequence.
6. Measure coverage against the required step set, name every step the
   document leaves out, and compare the share with the policy minimum through a
   comparison that absorbs representation error.
7. Check the design baseline and the issue date, then report the whole
   assessment: steps grouped by verdict, the coverage and accepted shares, the
   weakest step and every finding.

## Pitfalls

- Grading the document against its own table of contents. A list that is
  internally consistent and omits mesa edge isolation is still a document that
  never put edge isolation forward.
- Accepting a controlling document reference as proof of control. The
  reference says where the parameters live; an entry that cites a document and
  declares no parameter holds nothing.
- Reading a wide tolerance band as a generous one. A band no realistic build
  can leave is indistinguishable from having no band, which is why the width is
  measured rather than merely present.
- Treating a band that excludes its own nominal as a rounding matter. It is a
  defect in the declaration, because production builds to the nominal and the
  inspection reads the band.
- Ignoring which line a step is run on. Two lines running the same recipe are
  two process histories, and a qualification result that quietly spans both
  covers neither.
- Merging the step outcomes into one pass or fail. A step with no controlling
  document and one with a wide band are different root causes with different
  fixes, and a merged verdict sends the supplier back for the wrong correction.
- Judging a coverage share that lands exactly on its policy minimum by bare
  arithmetic. The share is a ratio of two counts and the minimum is a round
  fraction, so a document meant to sit on the minimum can land a few units in
  the last place below it; the comparison absorbs that while the limit stays
  as declared.

## Behavior contract (gate 3)

The parameter band bracketing and width grading, the ranked process step
verdict, the qualified-line binding, the coverage measurement against the
required step set, the design baseline match, the issue-date precedence check
and the rolled-up document verdict are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_process_identification_document.py against
scripts/e2008_bare_cell_process_identification_document_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_bare_cell_process_identification_document.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
