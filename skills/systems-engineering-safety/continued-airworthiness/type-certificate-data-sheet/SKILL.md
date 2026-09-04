---
name: type-certificate-data-sheet
description: "Use when you must compile and validate a type certificate data sheet: check that every required section is present (models, type design, approved engines and propellers, weights, certification basis, operating limitations, noise standards), validate the weight block consistency (max ramp at or above max takeoff, max landing at or below max takeoff, all positive), validate the category airspeed limitations (transport requires VMO or MMO; normal, utility and acrobatic categories require VNE), check the approved configuration consistency, and diff two revisions of the record into a per-section change summary for type certificate amendment or STC integration review. Produces the missing-section list, the validation error list, the summary counts, and the revision change report. Trigger: type certificate data sheet, TCDS record, type design record, approved engine models, weight block, category airspeed limits, VMO, MMO, VNE, TCDS revision diff."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: continued-airworthiness
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: continued-airworthiness
  tags: [type-certificate-data-sheet, tcds-validation, type-design-record, approved-model-list, category-airspeed-limits, tcds-revision-diff]
  version: 0.1.0
  author: AeroSkills
---

# Type Certificate Data Sheet (systems-engineering-safety/continued-airworthiness/type-certificate-data-sheet)

Use when a type certificate data sheet style type design record must be
compiled, validated or revised: checking the required section set, the
weight block, the category airspeed limitations and the approved engine
and propeller configuration, then summarizing counts or diffing two
revisions for a type certificate amendment or an STC integration review.
This leaf implements the TCDS record checks in pure Python, stdlib only:
every check is a small deterministic function over a plain dict record.
It pairs with the certification-basis leaf in this family, which decides
the regulation set and approval route that the certification_basis
section of the record then quotes, and with the airworthiness-limitation
leaf in this pack, which reads type-certificate limitation data as an
input to maintenance-program checks.

## Domain quick reference

- Record shape: a dict with a "category" key plus the required sections
  REQUIRED_SECTIONS = (models, type_design, engine_models,
  propeller_models, weights, certification_basis,
  operating_limitations, noise_standards). The models, engine_models and
  propeller_models sections are lists, weights is a dict holding
  max_ramp, max_takeoff and max_landing, and operating_limitations is a
  dict of named limits.
- Section presence: missing_sections returns the REQUIRED_SECTIONS keys
  absent from the record. Content checks inside sections that exist are
  separate: a missing section is reported once by missing_sections.
- Weight block rules: every weight is positive; max_ramp at or above
  max_takeoff (ramp below takeoff is an error, the fuel for start and
  taxi is not yet burned); max_landing at or below max_takeoff (landing
  weight is limited to the takeoff certified value).
- Category airspeed rules (CATEGORY_AIRSPEED_KEYS): transport requires
  VMO or MMO, any one key present and positive satisfies the rule;
  normal, utility and acrobatic categories require VNE. These follow the
  Part 25 transport limit philosophy (VMO/MMO envelope) versus the
  legacy Part 23 category rule set (VNE placard), handled here as data.
- Approved configuration: a TCDS lists the approved engine and
  propeller models, so engine_models and propeller_models must be
  non-empty; operating_limitations may carry an optional "engines" list
  of engine model references and each reference must appear in
  engine_models.
- Revision diff: tcds_revision_diff maps each section key to unchanged,
  added, removed or modified, reports the per-model change of the models
  section as models_added and models_removed, and the weight changes as
  "<key>_delta" floats such as max_takeoff_delta.
- Units: weights in the worked examples are kg and airspeeds are labeled
  in the record (ktas for VMO, Mach for MMO); limits keep the units the
  record declares, values are compared as numbers.
- Regulatory frame: FAR 25 is named only as the transport certification
  standard the sheet records, with the legacy Part 23 category rules and
  the FAR 36 noise standards treated as data entries.

## Workflow

1. Assemble the draft type design record as a dict with a "category" key
   and the section keys of the sheet being compiled.
2. Check section presence with missing_sections(record) and fill any
   REQUIRED_SECTIONS key that is absent.
3. Validate the weight block with weight_errors(record) and correct any
   missing, non-positive or inconsistent weight entries.
4. Validate the category airspeed limitations with
   airspeed_errors(record): transport needs VMO or MMO, the smaller
   categories need VNE.
5. Check the approved configuration with approved_config_errors(record):
   non-empty engine and propeller model lists and, when present, engine
   references in operating_limitations that all appear in engine_models.
6. Run the aggregate check validate_tcds(record) and read the
   missing_sections, weight_errors, airspeed_errors, config_errors lists
   and the valid flag; valid is True exactly when all four lists are
   empty.
7. Summarize the record with tcds_summary(record) for the model counts,
   the max takeoff weight and the sorted airspeed limit list.
8. For a type certificate amendment or STC integration review, diff the
   old and new revisions with tcds_revision_diff(old, new) and read the
   per-section statuses, the added and removed models, and the weight
   deltas.
9. Confirm the deterministic checks with the contract test
   scripts/test_type-certificate-data-sheet.py.

## Worked example

Record A: category "transport", models ["T-100"], type_design "T-100
basic", engine_models ["E-1", "E-2"], propeller_models ["P-1"], weights
{max_ramp 80000, max_takeoff 79000, max_landing 70000} (kg),
certification_basis ["far-25"], operating_limitations {vmo 340 (ktas),
mmo 0.84}, noise_standards ["far-36"].

- missing_sections(A) == [], weight_errors(A) == [],
  airspeed_errors(A) == [] (transport satisfied by vmo 340),
  approved_config_errors(A) == [].
- validate_tcds(A) valid True with all four error lists empty.
- tcds_summary(A): models 1, engine_models 2, propeller_models 1,
  max_takeoff_weight 79000.0, airspeed_limits ["mmo=0.84", "vmo=340"].
- Record B: category "normal" with weights {max_ramp 75000,
  max_takeoff 79000, max_landing 70000} and operating_limitations {}:
  weight_errors(B) = ["max_ramp below max_takeoff"] and
  airspeed_errors(B) = ["missing vne for category normal"], so
  validate_tcds(B) valid False.
- Revision A2 adds model "T-101" and changes max_takeoff to 79400:
  tcds_revision_diff(A, A2) reports sections models "modified" and
  weights "modified", models_added ["T-101"], models_removed [], and
  weight_deltas {"max_takeoff_delta": 400.0}.
- Configuration spot check: operating_limitations with an "engines"
  list ["E-9"] gives the error "engine reference E-9 not in approved
  engine models".

## Verification

- Confirm missing_sections on a record without propeller_models and
  noise_standards returns exactly those two, in section order.
- Confirm the weight rules: ramp below takeoff flagged, landing above
  takeoff flagged, non-positive and zero weights flagged, and a record
  with no weights section returns no weight errors (section absence is
  reported by missing_sections).
- Confirm the airspeed truth table across all four categories and that
  an unknown category is flagged.
- Confirm validate_tcds(A) valid True and validate_tcds(B) valid False
  with the two content errors of the worked example.
- Confirm the identities: valid equals all four error lists empty,
  summary counts equal their list lengths, a diff of a record with
  itself is all "unchanged", and models_added and models_removed are
  disjoint.
- Confirm ValueError rejection of non-physical inputs: a record without
  a "category" key, a weights section that is not a dict, an
  operating_limitations section that is not a dict, and non-numeric
  weight or airspeed values.
- Confirm the module is deterministic: the same record gives the same
  validation dict on every run.
- Run the contract test offline: python3
  scripts/test_type-certificate-data-sheet.py (35 tests,
  deterministic).

## Related leaves

- systems-engineering-safety/certification/certification-basis: decides
  the regulation set and approval route that the certification_basis
  section of the record then quotes.
- systems-engineering-safety/continued-airworthiness/
  ica-cmr-ali-classification: downstream in this pack, consumes the
  type-certificate limitation data when a maintenance program is checked
  against the airworthiness limitations of the type.
- systems-engineering-safety/continued-airworthiness/
  in-service-safety-assessment: the field review that reacts to events
  on the certified type after it enters service.
- systems-engineering-safety/arp4754a/configuration-management: change
  control over the type design record when the sheet is amended.

## Pitfalls

- Confusing section presence with section content: missing_sections
  reports only absent REQUIRED_SECTIONS keys, so a record with a weights
  section whose keys are wrong gets no missing-section entry but does
  get "missing weight key ..." entries from weight_errors; read both
  lists from validate_tcds.
- Treating a present but empty section as complete: operating_limitations
  {} is present, so it never appears in missing_sections, yet the
  category airspeed rule still fails for it (Record B shows exactly
  this: no missing sections, but "missing vne for category normal").
- Requiring every airspeed key: the category rule needs any one listed
  key present and positive, so a transport record with VMO alone is
  valid without MMO, and MMO alone satisfies it too.
- Checking engine references against an empty approved list: when
  engine_models is empty the config check reports "no approved engine
  models listed" and skips the reference comparison, so an "engines"
  entry does not cascade into duplicate reference errors.
- Ignoring the units declared in the record: the worked example mixes
  ktas (VMO 340) and Mach (MMO 0.84) inside one operating_limitations
  dict, and weights in kg; values are compared as numbers with the units
  treated as labels, so compare like for like.
- Reading a revision diff as a full history: tcds_revision_diff gives
  the state change between exactly two revisions, not the amendment
  trail, and a reordering of models inside the list counts as
  "modified" with empty added and removed lists.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_type-certificate-data-sheet.py

The test covers the worked example (record A valid, record B invalid
with "max_ramp below max_takeoff" and "missing vne for category
normal"), the missing-section lists on partial records, the weight rule
truth table (ramp below takeoff, landing above takeoff, non-positive
and missing weight keys), the category airspeed truth table across all
four categories with the unknown-category flag, the approved
configuration checks including engine references, the summary counts
and sorted airspeed limits, the revision diff (added and removed
models, weight deltas, self-diff all unchanged, disjoint added and
removed), the identity valid == all error lists empty, determinism, and
ValueError rejection of records without a category, non-dict weights or
operating_limitations sections, and non-numeric values.

## Compliance

- Standards referenced, not reproduced: FAR 25 frames the transport
  certification basis that the sheet records and FAR 36 the noise
  standards entry, while the legacy Part 23 category airspeed rule is
  carried as data; all are named as context only and the rules above
  are summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
