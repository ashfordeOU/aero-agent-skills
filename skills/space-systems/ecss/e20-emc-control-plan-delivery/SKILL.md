---
name: e20-emc-control-plan-delivery
description: "Use when draft and hand over the electromagnetic compatibility control plan in time for the preliminary design review under ECSS-E-ST-20C clause 6.2.2: categorize each mandatory plan section as management, design or verification content, list the sections the plan does not declare, score the maturity every declared section has reached, compute the completeness index the plan holds at hand-over, count the calendar lead between the issue date and the review against the data package deadline, and prove every compatibility requirement traces into a section that exists and has been started. Trigger: ecss, e-st-20-electrical-scope, emc-control-plan-delivery, emc-control-plan-sections, plan-section-maturity-index, control-plan-delivery-lead-time, emc-requirement-plan-traceability, preliminary-design-review-data-package."
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
  tags: [ecss, e-st-20-electrical-scope, e20-emc-control-plan-delivery, emc-control-plan-delivery, emc-control-plan-sections, plan-section-maturity-index, control-plan-delivery-lead-time, emc-requirement-plan-traceability, preliminary-design-review-data-package]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- EMC Control Plan Delivery (space-systems/ecss/e20-emc-control-plan-delivery)

Use when the task is the clause 6.2.2 control plan of ECSS-E-ST-20C --
writing down how electromagnetic compatibility will be controlled on
the project and putting that document in the reviewers' hands early
enough that the preliminary design review can still act on it.

## Domain quick reference

- The plan carries twelve mandatory sections in three groups.
  Management content says what the plan applies to, who is responsible,
  what is delivered when, and how a non-conformance or waiver is
  routed. Design content carries the requirement and limit flow-down,
  the grounding and bonding concept, the shielding and harness rules,
  frequency management and protected bands, and the safety margin
  policy. Verification content carries the approach to predictive work,
  the verification and test approach, and the interference-critical
  point list. A section the plan does not declare is a gap in the
  method, not a formatting detail.
- A declared section is not automatically a delivered section. Each one
  carries a status -- not started, draft, issued, approved -- and only
  a section at issued or better is content a reviewer can act on. The
  plan's completeness index is the mean maturity over the mandatory
  set, with an undeclared section contributing nothing, so a plan
  cannot buy a high score by declaring only its finished sections.
- Because that index is a sum of maturities divided by a count, a plan
  whose sections all sit exactly at the hand-over status can land a
  unit in the last place below the threshold. The comparison absorbs
  that representation error; the threshold itself never moves.
- Delivery is a date, not an intention. The lead is the calendar
  distance between the plan's issue date and the review date, and it
  has to clear the data package deadline -- the window in which
  reviewers actually read the package. A plan issued inside that window
  is late even though its date precedes the review, and a plan issued
  after the review arrives once the architecture is already frozen,
  which is exactly the outcome the clause exists to prevent.
- The plan also has to absorb the compatibility requirements. Every
  requirement in the flow-down points at the section that implements
  it; a requirement with no section, a requirement pointing at a
  section the plan never declared, and a requirement pointing at a
  section still at not-started are three distinct findings with three
  distinct fixes.

## Workflow

1. Categorize each declared section into its group; reject a section
   that is not part of the clause 6.2.2 control plan before it reaches
   the completeness count.
2. List the mandatory sections the plan does not declare.
3. Read the status of every declared section and list those below the
   minimum status expected at hand-over.
4. Compute the completeness index as the mean maturity over the
   mandatory set, and compare it against the hand-over threshold with
   a comparison that tolerates the floating-point mean.
5. Count the calendar days between the issue date and the review date;
   flag a hand-over after the review and, separately, a hand-over
   inside the data package deadline.
6. Walk the compatibility requirement flow-down and flag every
   requirement that traces nowhere, traces to an undeclared section, or
   traces to a section that has not started.
7. Aggregate the section, maturity, timing and traceability findings.
   The plan is deliverable only when every list is empty and the index
   holds the threshold.

## Pitfalls

- Delivering a table of contents with every section named and nothing
  written -- the count looks complete while the maturity of the plan is
  that of its emptiest section.
- Reading "issued before the review" as on time; the package deadline
  is the real date, and a plan that lands a few days before the review
  is read by nobody in time to change anything.
- Letting the grounding and bonding concept sit in draft at hand-over
  because the architecture "is not final" -- that concept is one of the
  inputs the review exists to settle, and deferring it inverts the
  order.
- Treating a requirement flow-down as traced because the plan mentions
  the requirement somewhere; the trace has to land in a named section,
  and that section has to have been started.
- Averaging maturity over the sections the plan happens to declare
  rather than over the mandatory set, which makes a plan missing four
  sections score higher than one that declared them all in draft.
- Widening the hand-over threshold because a plan whose sections are
  all exactly at the expected status scored a hair under it; the
  shortfall is in the arithmetic, not in the plan.

## Behavior contract (gate 3)

The section categorization, status maturity, completeness index,
delivery lead time and requirement traceability logic is exercised by
the gate 3 contract test:
scripts/test_e20_emc_control_plan_delivery.py against
scripts/e20_emc_control_plan_delivery_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_emc_control_plan_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
