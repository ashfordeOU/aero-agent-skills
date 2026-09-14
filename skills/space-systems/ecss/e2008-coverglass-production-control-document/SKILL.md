---
name: e2008-coverglass-production-control-document
description: "Use when a coverglass production control document, deposition process baseline or qualification evidence list has to be reviewed. Review the supplier process identification document that clause 8.4 of ECSS-E-ST-20-08C asks for before coverglass production is qualified: hold the processes the glass is genuinely made by against the set the document declares, check each declared process names the production document controlling it, confirm every control parameter carries a band that brackets its nominal, is tight enough to control anything and is still wider than the measurement uncertainty behind it can resolve, and refuse qualification evidence dated before the document that committed to it. Trigger: ecss, e-st-20-08c, coverglass-production-control-document, coverglass-process-step-coverage, coverglass-control-parameter-band, coverglass-measurement-uncertainty-ratio, coverglass-qualification-evidence-date."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-coverglass-production-control-document, coverglass-process-step-coverage, coverglass-control-parameter-band, coverglass-measurement-uncertainty-ratio, coverglass-qualification-evidence-date, coverglass-process-identification-document]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses -- Production Control Document (space-systems/ecss/e2008-coverglass-production-control-document)

Use when the task is clause 8.4 of ECSS-E-ST-20-08C: the supplier writes a
process identification document covering coverglass production and submits it
for qualification, and somebody has to decide whether that document actually
identifies the processes. This leaf grades it on coverage, on control, on
measurement and on dates.

## Domain quick reference

- The document is a gate, not a catalogue. Its job is to fix, before the
  campaign, which processes the glass depends on, so that a process qualified
  later can be traced back to a commitment made earlier.
- A process that never reaches the document is never put forward for
  qualification. Coverage is therefore measured against the processes a
  coverglass is genuinely made by -- glass forming, cutting and sizing, edge
  finishing, cleaning, AR coating, UV filter deposition, conductive coating,
  marking and packaging -- not against the list the supplier happened to
  submit.
- Missing is not one finding. A qualification-critical process absent from the
  document is a hole in the qualification; a control-only process absent from
  it is a gap in the baseline. Reporting both the same way buries the first.
- Naming a process is half the declaration. The other half is the production
  document that controls it, and an entry that names one without the other
  commits to nothing anybody can build to.
- A control parameter is graded three ways and the third is the one that gets
  skipped. The band has to bracket its own nominal, or it describes some other
  setting. It has to be tight enough to control anything, or it is a range
  rather than a tolerance. And it has to be wider than the measurement behind
  it can resolve.
- That third reading is a test uncertainty ratio. A deposition rate held to a
  part in a thousand by an instrument whose uncertainty is a part in five
  hundred is not controlled, it is recorded: every reading inside the band is
  indistinguishable from every other, so the band cannot reject anything.
- Evidence dated before the document that committed to the process discharges
  nothing. It was generated under some other commitment, and accepting it
  inverts the gate the document exists to be.
- The document itself has a date to defend. Issued after the campaign began it
  is a record of what was done, not a commitment about what would be, and the
  distinction is the whole point of the clause.

## Workflow

1. Take the document with its identifier, its issue date, the campaign start
   date and one entry per declared process.
2. Compare the declared set with the required set and split what is missing
   into qualification-critical and control-only. Carry anything declared beyond
   the required set as extra baseline.
3. For each entry, check it names the production document that controls the
   process.
4. Grade every control parameter three ways: does the band bracket its nominal,
   is the relative half-width inside the policy cap, and is the half-width at
   least the declared multiple of the measurement uncertainty. Use comparisons
   that absorb representation error at each limit.
5. Resolve the standing of the qualification evidence: present or not, and
   dated on or after the document issue or before it.
6. Disposition each entry on the first thing that fails: no controlling
   document, no control parameters, a defective parameter, no evidence,
   evidence predating the document, otherwise accepted.
7. Check the document issue date precedes the campaign start.
8. Roll up: the verdict, the entries rejected, the accepted share and the
   weakest entry, with critical processes ranked ahead of control-only ones.

## Pitfalls

- Grading the list the supplier submitted. Coverage is against the processes
  the glass actually depends on, and the missing entry is invisible in the
  submitted list by definition.
- Reporting a missing critical deposition step and a missing packaging step in
  the same sentence. One of them is a hole in the qualification.
- Accepting an entry that names a process and no controlling document. There is
  nothing for the shop floor to build to and nothing for an auditor to read.
- Reading a tolerance band as controlled because it is narrow. A band narrower
  than the measurement uncertainty rejects nothing, because every reading
  inside it is indistinguishable from every other.
- Reading a band as controlled because it is wide enough to measure. If it does
  not contain its own nominal it describes some other setting entirely.
- Treating a very wide band as conservative. A tolerance that nothing can fall
  outside is not a tolerance.
- Crediting qualification evidence that predates the document. It was generated
  under another commitment, and reusing it turns the gate into paperwork
  gathered afterwards.
- Letting the document be issued after the campaign started. A gate written
  after the work is a record of the work.
- Comparing a relative band width or an uncertainty ratio against its limit by
  bare arithmetic. Both are quotients of measured quantities, so a band drawn
  exactly at the limit can evaluate a unit in the last place on the wrong side
  and read as compliant on one platform and as defective on another.

## Behavior contract (gate 3)

The required-process coverage split by criticality, the controlling-document
check, the three control parameter readings including the measurement
uncertainty ratio, the qualification evidence date standing, the per-entry
disposition, the issue-date-before-campaign check and the document roll-up are
exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_production_control_document.py against
scripts/e2008_coverglass_production_control_document_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_production_control_document.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
