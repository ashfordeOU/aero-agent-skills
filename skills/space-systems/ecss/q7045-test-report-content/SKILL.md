---
name: q7045-test-report-content
description: "Audit a mechanical test report on metallic materials against the content its reporting clause makes it carry. Use when a laboratory file has come back and someone must decide whether it closes: build the required section set from the test method, so a fatigue file owes its run-out criterion and a fracture file its precrack record, name the gaps in the order the set requires them, reconcile the specimen register against the results table in both directions, then re-derive the printed tensile properties from the retained raw data and report every number that raw data does not reproduce. Trigger: ecss, q-st-70-45-metallic-mechanical-testing, mechanical-test-report-content, test-report-section-completeness, test-specimen-register-reconciliation, retained-raw-data-reproduction, tensile-property-rederivation."
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
  tags: [ecss, q-st-70-45-metallic-mechanical-testing, q7045-test-report-content, mechanical-test-report-content, test-report-section-completeness, test-specimen-register-reconciliation, retained-raw-data-reproduction, tensile-property-rederivation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Test Report Content (space-systems/ecss/q7045-test-report-content)

Use when the task is the reporting clause of ECSS-Q-ST-70-45: deciding
whether a mechanical test report actually carries the specimens, the
conditions, the results and the raw data behind them, or only looks as
though it does.

## Domain quick reference

- The required content set is not one list. A common set covers the
  laboratory, the material, the method reference, the specimen register,
  the conditions, the results, the retained raw data, the validity
  statement and the authorisation; the method then adds to it. A fatigue
  file owes its loading spectrum, its stress-life points and the run-out
  criterion those points were stopped at; a fracture file owes the
  precrack record, the crack-length record and the size-validity
  criterion; an impact file owes the absorbed energy and the fracture
  appearance.
- Gaps are reported in the order the set requires them, not in the order
  they were noticed. The laboratory works the chase list top to bottom,
  and a list shuffled by discovery order costs a round trip.
- The specimen register and the results table are reconciled in both
  directions. A result quoting a specimen nobody registered has no
  traceable piece of material behind it; a registered specimen with no
  result is a test the report quietly dropped, and that is the direction
  a reader never checks.
- Raw data is required so the printed numbers can be re-derived, not so
  the file is thicker. A tensile strength is the maximum force over the
  original area, an elongation is the gauge-length change over the
  original gauge length, a reduction of area follows from the diameter
  ratio, and each of them is recomputable from measurements a laboratory
  already writes down.
- Reproduction is judged to a relative tolerance, because a report
  prints rounded values. The defect being caught is a number nobody can
  get back from the data, not a number rounded to three figures.
- Raw data that contradicts itself is a refusal, not a finding: a yield
  force above the maximum force, a gauge length that shrank or a
  diameter that grew mean the file was transcribed wrong and nothing
  downstream of it can be judged.

## Workflow

1. Take the test method and build the required section set from it,
   rather than from the laboratory's own table of contents.
2. Compare the delivered report against that set and list the gaps in
   required order; report the completeness as a ratio so a report that
   is nearly closed is distinguishable from one that barely started.
3. Normalise the specimen register: identifiers are case-folded and a
   piece registered twice is a register error, not a duplicate to drop.
4. Reconcile results against the register in both directions and name
   the orphaned results and the unreported specimens separately.
5. Where raw data and printed properties are both present, validate the
   raw data for internal contradictions first, then re-derive each
   property and compare it with what was printed.
6. Report an acceptance verdict only when the section set is complete,
   the register reconciles and every printed property is reproduced.

## Pitfalls

- Auditing the table of contents instead of the method. The common
  sections are the easy ones to deliver; the method-specific sections
  are the ones a general-purpose report template leaves out.
- Checking only that every result has a specimen. The reverse direction
  is where a failed or invalid piece disappears, and a report that is
  short one specimen still looks internally consistent.
- Accepting a raw-data section because the file is present. Retention is
  satisfied by data the printed values can be recovered from; a scan of
  a machine screen that nobody can recompute from meets the letter and
  not the requirement.
- Treating a rounding difference as a reproduction failure. Judge it on
  a relative tolerance, and keep the tolerance in one named constant so
  a reviewer can see what was allowed.
- Repairing contradictory raw data by clamping it. A yield force above
  the maximum force is a transcription defect; deriving a property from
  it produces a number that looks plausible and is not measurable.
- Reporting a completeness percentage on its own. The percentage tells
  nobody which section is missing, and a single absent authorisation
  blocks acceptance just as firmly as five absent sections.

## Behavior contract (gate 3)

The method-driven section set, the ordered gap list, the completeness
ratio, the two-directional specimen reconciliation, the raw-data
validation, the tensile re-derivation and the tolerance-based
reproduction comparison are exercised by the gate 3 contract test:
scripts/test_q7045_test_report_content.py against
scripts/q7045_test_report_content_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_test_report_content.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
