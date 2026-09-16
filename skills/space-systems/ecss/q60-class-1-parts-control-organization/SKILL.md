---
name: q60-class-1-parts-control-organization
description: "Use when a declared parts control organization has to become an adequacy verdict. Assess whether the unit accountable for electronic part control is constituted as the highest reliability class demands under ECSS-Q-ST-60C clause 4.1.2.1: refuse a unit with no name, lead or appointment behind it, take each required control function in turn, treat a function held by an unqualified name or funded below its effort floor as uncovered, compute the covered share and the effort-weighted staffing, name every unassigned and every under-resourced function, test the reporting line and the independence from the design authority, and cap the control one holder may carry alone. Trigger: ecss, q-st-60c-clause-4-1-2-1, class-one-parts-control-organization, parts-control-function-coverage, parts-control-holder-concentration, parts-control-reporting-line, parts-control-design-independence, parts-control-effort-floor."
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
  tags: [ecss, q-st-60-eee-component-selection-scope, q60-class-1-parts-control-organization, class-one-parts-control-organization, parts-control-function-coverage, parts-control-holder-concentration, parts-control-reporting-line, parts-control-design-independence, parts-control-effort-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components -- Class 1 Parts Control Organization (space-systems/ecss/q60-class-1-parts-control-organization)

Use when the task is the clause 4.1.2.1 accountability question of
ECSS-Q-ST-60C at the highest reliability class: a supplier has declared
who owns electronic part control, and the question is whether that
declaration is an organization or a sentence.

## Domain quick reference

- The clause asks for one named unit with a named lead and an
  appointment behind that lead. A part control responsibility spread
  across a project without a post holding it is nobody's, and the first
  three checks exist to catch exactly that.
- A control function written against a name with no competence behind it
  and no effort allocated to it is uncovered. A chart listing every
  required function against one overloaded engineer matches the required
  list and covers none of it, so an unqualified holder or an effort
  below the declared floor reads as no holder at all.
- Coverage and staffing are two different numbers and both are reported.
  The covered share answers how many required functions carry a real
  holder; the effort-weighted staffing answers how much of a person
  stands behind the whole set, counting an unassigned function as zero
  rather than omitting it from the average. A unit can score well on one
  and badly on the other, and the pair is what a reviewer needs.
- The reporting line is part of the constitution, not an administrative
  detail. A part control unit reporting into the authority whose cost
  and schedule its refusals will hit has no standing to refuse, so the
  accepted lines are declared and checked rather than assumed, and the
  independence from the design authority is checked beside them.
- Concentration is its own failure mode. One holder carrying most of the
  required functions is a single point of failure whatever the covered
  share says, so the peak holder load is computed against a cap and a
  load sitting exactly on the cap is admissible, the comparison
  tolerance being there to absorb representation error rather than to
  widen the cap.
- Customer agreement closes the constitution. At this class the customer
  carries the residual part risk, so it has to know which unit holds the
  control and who leads it.
- The weakest covered function and its effort are worth as much as the
  verdict. A unit clearing every floor by a hair and one clearing them
  comfortably carry the same word, and nobody can recover the difference
  later from the word alone.

## Workflow

1. Validate the adequacy policy first: the minimum covered share, the
   effort floor a function must reach to count as covered, the marginal
   band inside which a covered function is still advised on, the cap on
   the share one holder may carry, and the accepted reporting lines. A
   share or floor above one, a marginal band above the floor, or an
   empty reporting-line list is refused rather than used.
2. Validate the unit identity: a non-blank unit name, a non-blank
   accountable lead, a non-blank appointment reference, a reporting line
   name, and boolean independence and customer-agreement declarations.
   An absent unit, or one missing any of the first three, closes the
   assessment on organization not established.
3. Validate every assignment record: a recognised function name, no
   duplicate function, an effort in the unit interval, a boolean
   competence flag, and a holder that may be blank but is then read as
   no holder.
4. Decide each required function: covered when it is assigned, its
   holder is named and competent, and the allocated effort reaches the
   floor. Anything else is unassigned or under-resourced, and both lists
   are reported in full rather than truncated at the first entry.
5. Take the covered share over the required functions and the
   effort-weighted staffing over the same denominator, counting an
   unassigned function as zero effort so the average cannot be improved
   by deleting a function from the chart.
6. Compare the covered share against the policy floor with a tolerance
   that absorbs representation error, then test the reporting line
   against the accepted list, the independence from the design
   authority, the peak holder share against its cap, and the customer
   agreement.
7. Report the covered share, the staffing, the unassigned and
   under-resourced functions, the peak holder and its share, the weakest
   covered function and its effort, and raise an advisory for every
   covered function inside the marginal band. Close on one verdict:
   organization not established, function coverage short, reporting line
   not accepted, organization not independent, control concentrated on
   one holder, organization not agreed with the customer, or
   organization meets class one.

## Pitfalls

- Reading an organization chart as the answer. A box on a chart with no
  appointment behind the lead and no effort behind the functions is the
  failure mode this clause exists to catch.
- Averaging effort only over the functions that appear. Deleting an
  unstaffed function would then raise the score, which is exactly
  backwards; the denominator stays the full required function list.
- Accepting a unit inside the design authority because the people are
  good. The clause is about standing, not goodwill: a unit that cannot
  overrule the design on a part choice is advisory, whoever staffs it.
- Passing a chart where one engineer holds nearly everything. The
  covered share reads perfect and the control disappears the week that
  engineer leaves, so the peak holder load is capped separately.
- Reporting a bare pass. The covered share, the staffing, the peak
  holder and the weakest function are what the next organization review
  is compared against, and the verdict word carries none of them.

## Behavior contract (gate 3)

The policy validation, unit identity validation, assignment validation,
the covered, unassigned and under-resourced decisions, the covered
share, the effort-weighted staffing, the holder load and peak share, the
weakest covered function, the reporting-line, independence and customer
agreement checks, the marginal advisories and the organization verdict
are exercised by the gate 3 contract test:
scripts/test_q60_class_1_parts_control_organization.py against
scripts/q60_class_1_parts_control_organization_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_parts_control_organization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
