---
name: e20-electrical-design-documentation-set
description: "Use when audit the electrical design documentation set required by ECSS-E-ST-20C clause 4.3.2: derive which supporting analyses an electronic item actually owes -- worst case and reliability always, thermal once it dissipates power, radiation once it accumulates mission dose, electromagnetic once it carries external interfaces -- compute the worst-case parameter excursion by extreme-value or root-sum-square stacking of tolerance, temperature drift and ageing, check part derating and radiation design margin against their limits, and confirm every owed report is issued by the right review and rebuilt against the current design revision. Trigger: ecss, e-st-20-electrical-scope, electrical-design-documentation-set, worst-case-parameter-drift, part-derating-margin, radiation-design-margin, electromagnetic-compatibility-report, design-report-maturity."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electrical-design-documentation-set, worst-case-parameter-drift, part-derating-margin, radiation-design-margin, electromagnetic-compatibility-report, design-report-maturity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Design Documentation Set (space-systems/ecss/e20-electrical-design-documentation-set)

Use when the task is assembling or auditing the design reports and
supporting analyses of ECSS-E-ST-20C clause 4.3.2 -- deciding which
analyses an electrical or electronic item owes, running the margin
calculations those analyses turn on, and checking each report is issued
at the right review against the current design revision.

## Domain quick reference

- Clause 4.3.2 expects a design report backed by supporting analyses.
  Two are unconditional: the worst-case analysis (does the design still
  meet its requirements once every parameter sits at its adverse
  extreme?) and the reliability analysis (what is the failure rate and
  what are the single-point failures?). Three are conditional and are
  owed only when the item's physics calls for them: thermal once the
  item dissipates power, radiation once it accumulates mission dose,
  electromagnetic once it carries an external interface. An item that
  dissipates nothing owes no thermal report; demanding one is scope
  creep, and skipping a report that is owed is a gap.
- A worst-case parameter excursion stacks three independent drift
  contributions on the nominal value: initial tolerance, temperature
  drift (the temperature coefficient times the excursion from the
  reference temperature), and end-of-life ageing. Extreme-value
  stacking adds them arithmetically, which is conservative and cheap.
  Root-sum-square stacking combines them in quadrature, which is less
  conservative and only defensible when the contributions really are
  independent. The direction matters: the adverse extreme is the high
  side for a stress and the low side for a supply or a drive
  capability.
- Part derating compares the applied stress with the rated stress
  reduced by a derating factor. The margin is expressed as a fraction
  of the derated limit, so a negative margin means the part is run
  beyond its derated capability even if it sits under its datasheet
  rating. Radiation design margin is the ratio of the part's rated dose
  to the predicted mission dose at the part location; a ratio under the
  house minimum of two is a finding, not a judgement call.
- Report maturity is milestone-dependent. At PDR a draft is enough; at
  CDR and every later review the report must be issued. A report is
  stale whenever the design revision it was built against differs from
  the item's current design revision -- an issued but stale report is
  not evidence, because the design it analysed no longer exists.

## Workflow

1. Characterize the item: dissipated power, predicted mission dose at
   its location, and whether it carries external electrical interfaces.
   Reject a negative dissipation or dose before anything else.
2. Derive the owed analysis set from those characteristics plus the two
   unconditional analyses. This is the checklist the rest of the audit
   runs against.
3. For each parameter that drives a requirement, compute the worst-case
   excursion: pick the adverse direction, stack tolerance, temperature
   drift and ageing by extreme value unless independence has been
   argued, and compare the excursion with the requirement.
4. For each stressed part, compute the derating margin against the
   derated limit and flag any negative margin.
5. Where a radiation case exists, compute the radiation design margin
   and flag a ratio below the minimum.
6. For each owed analysis, locate its report. Flag an absent report, a
   report still in draft at CDR or later, and a report whose design
   revision does not match the item's current revision.
7. The documentation set is complete only when the completeness,
   maturity and margin finding lists are all empty.

## Pitfalls

- Producing every analysis for every item. The conditional three are
  driven by the item's physics; a report nobody owed still consumes a
  review cycle and buries the reports that matter.
- Stacking by root-sum-square to make a margin close. Quadrature
  assumes the contributions are independent; tolerance, thermal drift
  and ageing on the same part often are not, and the choice must be
  argued in the report rather than chosen for its answer.
- Reading a positive datasheet margin as a derating pass. The derating
  factor is what the limit actually is; applied stress under the rating
  but over the derated limit is a finding.
- Accepting an issued report without checking its design revision. The
  most common documentation defect is not a missing report, it is a
  real report describing a design that has since changed.
- Treating a draft at PDR the same as a draft at CDR. Maturity is read
  against the milestone; the same report is acceptable at one review
  and a finding at the next.

## Behavior contract (gate 3)

The owed-analysis derivation, worst-case stacking, derating margin,
radiation design margin, report maturity and aggregate review logic is
exercised by the gate 3 contract test:
scripts/test_e20_electrical_design_documentation_set.py against
scripts/e20_electrical_design_documentation_set_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_electrical_design_documentation_set.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
