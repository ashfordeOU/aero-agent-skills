---
name: e2008-protection-diode-acceptance-documentation
description: "Use when a protection diode acceptance data package is about to be released with a lot. Audit the acceptance data package a protection diode lot is delivered against, the records ECSS-E-ST-20-08C clause 9.4.6 sends diode acceptance results into under the documentation rules the diode clause already sets: resolve which rule set actually governs, hold a package that quietly writes a thinner one of its own, name the acceptance activity nobody wrote up, test each record for the bias and junction temperature fields that make it re-readable, refuse a record reporting on diodes outside the delivered lot, and find the delivered diode no activity reached. Trigger: ecss, e-st-20-08c-clause-9-4-6, protection-diode-acceptance-record-completeness, protection-diode-documentation-rule-delegation, protection-diode-record-traceability-to-lot, protection-diode-acceptance-activity-coverage."
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
  tags: [ecss, e-st-20-08-protection-diode-scope, e2008-protection-diode-acceptance-documentation, e-st-20-08c-clause-9-4-6, protection-diode-acceptance-record-completeness, protection-diode-documentation-rule-delegation, protection-diode-record-traceability-to-lot, protection-diode-acceptance-activity-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Protection Diodes -- Acceptance Documentation (space-systems/ecss/e2008-protection-diode-acceptance-documentation)

Use when the task is clause 9.4.6 of ECSS-E-ST-20-08C: the results of
protection diode acceptance testing are written up under the
documentation rules the diode clause already sets, rather than under a
regime invented for the lot in hand. That delegation is the first thing
to establish, because it decides what the rest of the review is even
allowed to ask for. This leaf reads the acceptance data package, resolves
the governing rule set, decides whether each record is a record, and
returns what stands between the diode lot and release.

## Domain quick reference

- The rule set is a finding before it is a setting. A package writing
  its records under a supplier-local or project-tailored regime has
  quietly narrowed the field set, and the records then read as complete
  against rules the clause did not delegate to.
- What a narrowed regime drops is not arbitrary. It drops the bias
  conditions, the junction temperature and the calibration reference --
  exactly the three fields a diode measurement cannot be re-derived
  without, and the three nobody misses until the next lot disagrees.
- A forward drop or a leakage current with no bias and no temperature is
  a number, not a result. Diode characteristics move with both, so a
  record that omits them describes a measurement nobody can repeat.
- Coverage and completeness are two different questions. An activity
  with no record at all is a hole in the package; a record missing its
  conditions is a record nobody can re-read, and the two need different
  responses.
- A record naming diodes outside the delivered lot is not weak evidence,
  it is evidence about something else. That outranks a thin record,
  because a thin record at least describes the right population.
- Coverage is per diode as well as per activity. Five activities can each
  carry a record while one delivered diode appears in none of them, and
  the package still reads complete if only the activity list is checked.
- Draft is not delivered. A package released while its records sit
  unapproved has moved the approval step past the point where anybody
  could still act on it.
- Two records can jointly cover one activity. Splitting a lot across test
  sessions is normal, so coverage is computed over the union of the
  records rather than demanding one record per activity.

## Workflow

1. Resolve the documentation rule set the package declares, default it to
   the delegated diode-clause rules when nothing is declared, and refuse
   a rule set that is not a recognised one.
2. Name what a narrowed rule set drops, and raise that as a package
   finding before any record is read.
3. Read the lot identifier and the delivered diode identifiers; the
   delivered list is the population every later question is asked about.
4. Audit each record against the field set the resolved rule set applies,
   treating an empty diode list and an empty conditions field as missing
   rather than as present-but-blank.
5. Test each record's diode identifiers against the delivered lot and
   name anything foreign.
6. Rank each record: foreign diodes first, then missing fields, then an
   approval still pending or withdrawn.
7. Build the per-activity diode coverage over the union of the records and
   name the delivered diodes no record of that activity reached.
8. Return a package verdict that is releasable only when the delegated
   rules were applied, every activity is recorded, every record is
   complete and every delivered diode is reached.

## Pitfalls

- Reading the rule set as metadata. It is the term that decides which
  fields are even asked for, so recording it and then auditing against
  the full list reports findings the package was never held to, while
  ignoring it hides the narrowing entirely.
- Counting records instead of activities. Five records can all describe
  the same activity, and the package then reports five results and four
  holes.
- Accepting a pass statement in place of the measured results. A
  statement that the lot passed is a conclusion; the clause sends the
  results themselves into the documentation, and the conclusion cannot be
  rebuilt from its own restatement.
- Checking activity coverage and stopping there. The delivered diode that
  appears in no record is invisible to an activity-level check and is
  exactly the diode that will be queried later.
- Treating an unapproved record as a paperwork detail. It is the one
  finding that can still be closed in minutes, and the one that stops the
  package the day it ships.
- Reading a foreign diode identifier as a typo and correcting it. The
  record may genuinely describe another lot, and silently rewriting the
  identifier destroys the only evidence that it did.
- Merging the arms into one pass or fail. A missing record and an
  unsigned record ask the supplier for very different work, and a merged
  verdict asks for the same one twice.

## Behavior contract (gate 3)

The documentation policy validation, the rule-set resolution with its
dropped-field list, the applied field set, the field audit, the record
traceability test, the approval state, the ranked record verdict, the
per-activity diode coverage and the package release verdict are exercised
by the gate 3 contract test:
scripts/test_e2008_protection_diode_acceptance_documentation.py against
scripts/e2008_protection_diode_acceptance_documentation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_protection_diode_acceptance_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
