---
name: e2008-protection-diode-production-control
description: "Assess the supplier written process identification document that ECSS-E-ST-20-08C clause 9.3.2 asks for before external protection diodes enter qualification: establish that what was submitted is a written document in force rather than a draft or a slide pack, hold the part inside the document scope, compare the processes the diode is genuinely made by against the set declared, confirm each declaration names the production document controlling it and the qualification lot behind it, and date the document against the lot it covers. Use when a protection diode process identification document, diode production control baseline or qualification evidence list has to be reviewed. Trigger: ecss, e-st-20-08c, external-protection-diode-process-identification, diode-production-control-document, diode-process-step-coverage, diode-qualification-lot-linkage, diode-document-issue-chronology, diode-qualification-entry-scope."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-protection-diode-production-control, external-protection-diode-process-identification, diode-production-control-document, diode-process-step-coverage, diode-qualification-lot-linkage, diode-document-issue-chronology, diode-qualification-entry-scope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- External Protection Diode Production Control (space-systems/ecss/e2008-protection-diode-production-control)

Use when the task is clause 9.3.2 of ECSS-E-ST-20-08C: the supplier writes a
process identification document covering the external protection diodes that
are about to enter qualification, and somebody has to decide whether that
document really identifies the processes. This leaf grades it on form, on
scope, on coverage, on linkage and on dates.

## Domain quick reference

- The document is what qualification is granted against. Qualifying a part
  without one qualifies a build nobody wrote down, and the next lot is free to
  be made differently without anything being violated.
- Written is a property that has to be checked, not assumed. A draft was
  written and never issued, so nothing binds the supplier to it. Slides shown
  at a review are not under configuration and cannot be reissued. A baseline
  described in a meeting leaves qualification with nothing to attach to.
- Scope runs ahead of content. This clause covers external protection diodes
  going into qualification. A diode built into the assembly is controlled
  through the assembly's own process controls, and an external diode that is
  not being qualified has nothing for this document to identify processes for.
  Carrying either inside the document files evidence against a part the
  document does not govern.
- Coverage is measured against the processes the diode is genuinely made by --
  die attach, package seal, lead forming, lead finish, screening and burn-in,
  electrical test, marking and packing -- and not against the list the supplier
  chose to submit. A process that never reaches the document is never put
  forward for qualification.
- The gap runs both ways and the two ways are different findings. A process
  used and not declared is an undeclared process. A process declared and not
  used describes a build this part did not go through, which means the document
  and the article have drifted apart.
- Five of those processes change what the part is rather than how it is
  presented: die attach, package seal, lead finish, screening and burn-in, and
  electrical test. A gap in those is a qualification gap; a gap in marking or
  packing is a documentation gap.
- A declaration has to carry two links, and they fail independently. The
  production document controlling the process says how it is held steady; the
  qualification lot says what evidence stands behind it. A declared process
  with no lot never entered qualification at all, however carefully it is
  described.
- Dates settle whether the document is a commitment or a record. A document
  issued after the lot it covers was built was written backwards from hardware
  that already existed, and the day arithmetic is the only thing that shows it.

## Workflow

1. Take the submission with its document identifier, the form it was submitted
   in, the diode role and whether the part is entering qualification, the issue
   date, the qualification lot build date, the processes the part is genuinely
   made by, and one declaration per declared process.
2. Resolve the document form: in force, written but not issued, or not a
   written document at all.
3. Settle scope before content -- an integral diode or a part not entering
   qualification is outside this document whatever it contains.
4. Compare declared against used both ways: undeclared processes, declared
   processes the part is not made by, and qualification-critical processes
   absent from the document.
5. Check each declaration names a production document controlling it and a
   qualification lot behind it, and report the two shortfalls separately.
6. Work out the share of qualification-critical processes that are both
   declared and backed by a lot, and hold it against the entry floor with a
   comparison that absorbs representation error.
7. Take the day difference between the issue date and the lot build date and
   refuse a document issued after the lot.
8. Grade the document: not in force or out of scope is not a submission; any
   coverage gap, missing link, reversed date or short entry share leaves it
   incomplete; anything else identifies the processes.

## Pitfalls

- Accepting a slide pack because it lists every process. Slides are not under
  configuration, so the list cannot be reissued and nothing tracks a change.
- Treating a draft as a document on the grounds that it is complete. Nobody
  signed it, and an unsigned process is one the supplier may leave tomorrow.
- Reviewing the content of a document that covers the wrong part. An integral
  diode is controlled through the assembly, and grading its processes here puts
  evidence under a clause that does not govern it.
- Measuring coverage against the submitted list. The list is the thing being
  graded, so grading it against itself always passes.
- Reading a declared process the part is not made by as harmless. It means the
  document describes a different build, and the difference is unexplained.
- Weighting a marking gap the same as a die attach gap. One changes how the
  part is presented and one changes what it is.
- Crediting a declaration that names a production document but no qualification
  lot. It is a controlled process that never entered qualification, which is
  precisely what this document exists to prevent.
- Skipping the date arithmetic because both dates are in the right year. A
  document issued weeks after the lot was built is a record of that lot, and
  the next lot is committed to nothing.
- Comparing an entry share against its floor by bare arithmetic. It is a
  quotient of counted processes and a document exactly on the floor can
  evaluate a unit in the last place under it; the comparison absorbs that while
  the floor stays as written.

## Behavior contract (gate 3)

The document form standing, the qualification entry scope check, the two-way
coverage comparison with the critical-process subset, the production document
and qualification lot linkage checks, the critical-process entry share against
its floor, the issue-date against lot-build-date arithmetic and the single
document verdict are exercised by the gate 3 contract test:
scripts/test_e2008_protection_diode_production_control.py against
scripts/e2008_protection_diode_production_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_protection_diode_production_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
