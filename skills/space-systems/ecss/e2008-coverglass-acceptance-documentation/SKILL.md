---
name: e2008-coverglass-acceptance-documentation
description: "Use when a coverglass acceptance data package is about to be released with a batch. Audit the acceptance records a coverglass batch is delivered against, the documentation rule set ECSS-E-ST-20-08C clause 8.5.4 sends coverglass acceptance results into: name the acceptance activity nobody wrote up, hold a record written to a rule edition the governing set has superseded, test each record for the fields those rules demand including measurement uncertainty and calibration, refuse a record reporting on coverglasses outside the delivered batch, find the delivered coverglass no activity reached, catch a retention period shorter than the rules require, and rank the arms into one release verdict. Trigger: ecss, e-st-20-08c-clause-8-5-4, coverglass-acceptance-record-conformance, coverglass-documentation-rule-edition, coverglass-acceptance-data-package-release, coverglass-record-traceability-to-batch, coverglass-acceptance-activity-coverage."
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
  tags: [ecss, e-st-20-08-coverglass-scope, e2008-coverglass-acceptance-documentation, e-st-20-08c-clause-8-5-4, coverglass-acceptance-record-conformance, coverglass-documentation-rule-edition, coverglass-acceptance-data-package-release, coverglass-record-traceability-to-batch, coverglass-acceptance-activity-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses -- Acceptance Documentation (space-systems/ecss/e2008-coverglass-acceptance-documentation)

Use when the task is clause 8.5.4 of ECSS-E-ST-20-08C: the results of
coverglass acceptance testing are written up under the documentation
rules already established for coverglasses, not under whatever template
the test house happened to open. A record that satisfies a generic
laboratory form and not the coverglass rule set is a record that will be
re-read against rules it was never written to. This leaf reads the
acceptance package, decides whether each record is a record under the
governing rules, and returns what stands between the batch and release.

## Domain quick reference

- The rule set is the yardstick, and it has an edition. A record citing
  a superseded edition may carry every field its own template asked for
  and still be short of what the current rules ask for, which is exactly
  how a thin record passes a field-by-field review.
- Coverage and completeness are separate questions. An activity with no
  record at all is a hole in the package; a record missing its test
  conditions is a record nobody can re-read. They need different work,
  so they are reported separately.
- A coverglass result is an optical result, so uncertainty is part of
  it. A transmittance figure with no uncertainty statement cannot be
  compared against the specification limit it is meant to clear, and the
  comparison is the whole point of the measurement.
- Calibration belongs in the record, not in a drawer. The equipment
  reference is what lets a transmittance or resistivity reading be
  re-derived years later, and it is the first field to go missing when a
  record is written from memory.
- A record naming pieces outside the delivered batch is not weak
  evidence, it is evidence about something else. That outranks every
  other arm, because a thin record at least describes the right
  population.
- Retention is a property of the record the rules set, not of the
  archive that happens to hold it. A record scheduled for destruction
  before the array it protects is flown is a record that will not exist
  when the question is asked.
- Coverage is per piece as well as per activity. Six activities can each
  have a record while one delivered coverglass appears in none of them,
  and the package still reads complete if only the activity list is
  checked.
- Two records can jointly cover one activity. Splitting a batch across
  test sessions is normal, so coverage is computed over the union of the
  records rather than demanding one record per activity.

## Workflow

1. Read the batch identifier and the delivered coverglass identifiers;
   the delivered list is the population every later question is asked
   about.
2. Read the governing documentation rules and refuse a rule set that
   lists its own edition as superseded, since no record could then cite
   one in force.
3. Read each record, refuse an activity the acceptance programme does
   not contain, refuse a record citing an edition the rule set neither
   governs nor retired, and refuse a package declaring a record twice.
4. Audit each record against the required field set, treating an empty
   piece list, an empty conditions field, an absent uncertainty
   statement and an empty calibration reference as missing rather than
   as present-but-blank.
5. Test each record's coverglass identifiers against the delivered batch
   and name anything foreign.
6. Rank each record: foreign pieces first, then a superseded rule
   edition, then missing fields, then a retention period below the
   required one, then an approval still pending or withdrawn.
7. Build the per-activity piece coverage over the union of the records
   and name the delivered coverglasses no record of that activity
   reached.
8. Return a batch verdict that is releasable only when every activity is
   recorded, every record conforms and every delivered piece is reached,
   with all findings collected in one list.

## Pitfalls

- Reviewing the records against a general record template. The clause
  points at the coverglass documentation rules specifically, and a
  package graded against the generic template passes with none of the
  optical fields the coverglass rules add.
- Ignoring the edition a record cites. Two records can be equally
  complete and one of them still be written to rules that were replaced,
  which no field-count comparison between them will ever surface.
- Counting records instead of activities. Six records can all describe
  the same activity, and the package then reports six results and five
  holes.
- Accepting a summary in place of the measured results. A statement that
  the batch passed is a conclusion; the clause sends the results
  themselves into the documentation, and the conclusion cannot be
  rebuilt from its own restatement.
- Recording a transmittance without its uncertainty. The number looks
  like a result, clears the limit by a margin nobody can size, and is
  the number an anomaly investigation will want a bound on first.
- Checking activity coverage and stopping there. The delivered
  coverglass that appears in no record is invisible to an activity-level
  check and is exactly the piece that will be queried later.
- Treating an unapproved record as a paperwork detail. It is the one
  finding that can still be closed in minutes, and it is the one that
  stops the package the day it ships.
- Reading a foreign piece identifier as a typo and correcting it. The
  record may genuinely describe another batch, and silently rewriting
  the identifier destroys the only evidence that it did.
- Merging the arms into one pass or fail. A missing record, a record on
  an old edition and an unsigned record ask the supplier for very
  different work, and a merged verdict asks for the same one three
  times.

## Behavior contract (gate 3)

The documentation rule set validation, the required activity and field
sets, the field audit, the rule-edition test, the retention test, the
batch traceability test, the approval state, the ranked record verdict,
the per-activity piece coverage and the package release verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_acceptance_documentation.py against
scripts/e2008_coverglass_acceptance_documentation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_acceptance_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
