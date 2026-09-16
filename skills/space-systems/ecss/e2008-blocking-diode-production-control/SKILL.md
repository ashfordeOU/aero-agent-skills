---
name: e2008-blocking-diode-production-control
description: "Use when a blocking diode process document, production baseline or process change record has to be reviewed. Assess the supplier process document that ECSS-E-ST-20-08C clause 12.3 asks for before qualified blocking diodes are produced: establish the document is issued and in force, hold the planar or mesa construction inside its scope, compare the steps the diode is genuinely built by against the steps declared, catch a step whose revision has moved away from the qualified baseline with no requalification behind it, score the share of critical steps still standing as qualified, and date the document against the lot it covers. Trigger: ecss, e-st-20-08c, blocking-diode-production-control, blocking-diode-process-document, blocking-diode-qualified-baseline-drift, blocking-diode-requalification-linkage, blocking-diode-process-step-coverage, blocking-diode-document-issue-chronology."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-production-control, blocking-diode-process-document, blocking-diode-qualified-baseline-drift, blocking-diode-requalification-linkage, blocking-diode-process-step-coverage, blocking-diode-document-issue-chronology]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Blocking Diode Production Control (space-systems/ecss/e2008-blocking-diode-production-control)

Use when the task is clause 12.3 of ECSS-E-ST-20-08C: the supplier prepares a
process document describing how qualified blocking diodes are produced, and
somebody has to decide whether that document really holds the build. This leaf
grades it on form, on scope, on step coverage, on drift away from the qualified
baseline, and on dates.

## Domain quick reference

- The load-bearing word in the clause is "qualified". The document is not a
  description of how the part happens to be made; it is the thing that keeps
  the build identical to the one qualification was granted on. Read as a
  description it passes trivially, because a description of any build is
  accurate about that build.
- Written is a property to be checked, not assumed. A draft was written and
  never issued, so nothing binds the supplier to it. Slides shown at a review
  are not under configuration and cannot be reissued when the build moves. A
  route described in a meeting leaves qualification attached to nothing.
- Scope runs ahead of content. A blocking diode integrated into the assembly is
  controlled through that assembly's own process controls, and a discrete part
  that was never granted qualification has no qualified build for a document to
  hold steady. Reviewing either one files evidence under a clause that does not
  govern it.
- Coverage is measured against the steps the diode is genuinely built by --
  junction formation, surface passivation, die attach, package seal, lead
  attach, lead finish, screening and burn-in, electrical test, marking and
  packing -- and never against the list the supplier submitted. A list graded
  against itself always passes.
- The gap runs both ways and the two ways are different findings. A step used
  and not declared is produced outside any control. A step declared and not used
  describes a route this part did not go through, so the document and the
  article have drifted apart.
- Six of those steps change what the diode is rather than how it is presented:
  junction formation, surface passivation, die attach, package seal, screening
  and burn-in, and electrical test. A gap there is a qualification gap; a gap in
  marking or packing is a documentation gap.
- Drift is the check a plain read misses. Each declared step carries the
  revision qualification ran on and the revision in force today. A step that has
  not moved is still the qualified step. A step that moved is only still
  standing when the move is carried -- a major change by a requalification
  reference, a minor change by a change notice.
- A step that moved with neither is the whole defect. The document is internally
  consistent, every process is named, and the diode is no longer produced the
  way it was qualified. Nothing on the page says so; only the revision
  arithmetic does.
- Dates settle whether the document commits or records. A document issued after
  the lot it covers was built was written backwards from hardware that already
  existed, and the day difference is the only thing that shows it.

## Workflow

1. Take the submission with its document identifier, the form it arrived in,
   the diode construction and whether qualification was granted, the issue date,
   the lot build date, the steps the part is genuinely built by, and one record
   per declared step.
2. Resolve the document form: issued and in force, written but not issued, or
   not a written document at all.
3. Settle scope before content -- an integrated diode or an unqualified part is
   outside this document whatever it contains.
4. Grade each declared step against its baseline: refuse a record whose change
   category contradicts its own revisions, then group the step as standing,
   drifted, unnotified or uncontrolled.
5. Compare declared against built both ways: undeclared steps, declared steps
   the part is not built by, and critical steps absent from the document.
6. Work out the share of qualification-critical steps that still stand as
   qualified, and hold it against the floor with a comparison that absorbs
   representation error.
7. Take the day difference between the issue date and the lot build date and
   refuse a document issued after the lot.
8. Grade the document: not in force or out of scope is not a submission; any
   coverage gap, uncarried change, uncontrolled step, reversed date or short
   standing share leaves it incomplete; anything else controls the build.

## Pitfalls

- Reading the document as a description of the build. Every description is
  accurate about the build it describes, so the review closes without ever
  asking whether that build is the qualified one.
- Accepting a slide pack because it names every step. Slides are not under
  configuration, so nothing tracks a change to them.
- Treating a draft as a document because it is complete. Nobody issued it, and
  an unissued route is one the supplier may leave tomorrow.
- Reviewing the content of a document covering the wrong part. An integrated
  diode is controlled through its assembly, and grading its steps here puts
  evidence under a clause that does not govern it.
- Measuring coverage against the submitted list. The list is the thing under
  review, so grading it against itself always passes.
- Reading a declared step the part is not built by as harmless. It means the
  document describes a different route, and the difference is unexplained.
- Weighting a marking gap the same as a junction formation gap. One changes how
  the diode is presented and one changes what it is.
- Accepting a moved revision because the step is still named. A major change
  with no requalification behind it is exactly the state this document exists to
  make visible, and it is invisible unless the revisions are compared.
- Skipping the date arithmetic because both dates fall in the right year. A
  document issued weeks after the lot was built records that lot, and the next
  lot is committed to nothing.
- Comparing the standing share against its floor by bare arithmetic. It is a
  quotient of counted steps and a document exactly on the floor can evaluate a
  unit in the last place under it; the comparison absorbs that while the floor
  stays as written.

## Behavior contract (gate 3)

The document form standing, the construction and qualification scope check, the
two-way step coverage with its critical subset, the baseline drift grading with
its major and minor carry rules, the standing share against its floor, the
issue-date against lot-build-date arithmetic and the single document verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_production_control.py against
scripts/e2008_blocking_diode_production_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_production_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
