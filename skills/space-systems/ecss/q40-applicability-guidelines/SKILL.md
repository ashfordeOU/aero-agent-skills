---
name: q40-applicability-guidelines
description: "Determine which ECSS-Q-ST-40C safety requirement groups bite on a given product type at a given programme phase, using the informative applicability guidelines, and grade a tailoring proposal against that answer: a deletion of a group the guideline has biting needs a justification and customer agreement, a deletion before the group starts should have been a deferral, and retaining a group the guideline puts out of scope is cost rather than safety. Use when safety requirements are tailored onto a project. Trigger: ecss, q-st-40c, safety-requirement-applicability-guidelines, safety-requirement-tailoring, product-type-phase-applicability, tailoring-justification, out-of-scope-requirement-group."
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
  tags: [ecss, q-st-40c-safety, q-st-40c, q40-applicability-guidelines, safety-requirement-applicability-guidelines, safety-requirement-tailoring, product-type-phase-applicability, tailoring-justification, out-of-scope-requirement-group]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Safety — Applicability Guidelines (space-systems/ecss/q40-applicability-guidelines)

Use when the task is the informative applicability annex of ECSS-Q-ST-40C: the
safety requirements are being tailored onto a specific project, and the
question is which groups apply to this product at this phase and whether the
proposed tailoring can be defended.

The annex is informative. What comes out of this leaf is advice a tailoring
board weighs, not a verdict it is bound by, and the report says so — the
findings separate what is unsupported from what is arguable.

## Domain quick reference

- Applicability takes two inputs. A group applies to a product type from a
  phase onward, so answering on the product alone or the phase alone is right
  about half the time and wrong quietly.
- There are four answers, not two. A group can bite in full, bite in reduced
  form, not bite yet, or be out of scope for the product entirely. Collapsing
  reduced into applicable over-applies; collapsing not-yet into out-of-scope
  loses it permanently.
- Not-yet-applicable is the state that decays. A group deleted while it was
  merely early never comes back, which is what the deferral action is for.
- Disposal safety is out of scope for a hosted instrument and for ground
  equipment, and in scope from an early phase for anything that re-enters.
  That single row explains most tailoring arguments on mixed programmes.
- A deletion against the guideline is not forbidden; it is the case that needs
  an argument on the record and the customer behind it. A deletion with no
  justification at all is the finding, and it is a different finding.
- Retaining a group the guideline puts out of scope is not a safety problem.
  It is cost, and reporting it as a safety finding trains people to ignore the
  report.
- Tailoring a group the guideline already has in reduced form is ordinary. It
  is tailoring a group that bites in full that needs the reason written down.

## Workflow

1. Validate the context: product type and phase both from the known sets.
2. Look the group up in the product's guideline: the phase it starts, whether
   it is out of scope, and whether it bites in reduced form.
3. Compare phases by position in the sequence, not by name, so a later phase
   keeps a group that an earlier one had not reached.
4. Report the state from the four-value vocabulary and never from a boolean.
5. For a whole context, group every requirement group by state so the tailoring
   board sees the shape of the programme at that phase.
6. Grade each tailoring proposal against the state: deletion of a biting group,
   deletion before it bites, retention of an out-of-scope group, tailoring of a
   fully applicable group, deferral past the phase it bites.
7. Separate the unjustified proposals from the arguable ones and from the
   purely advisory findings.
8. Close with a tailoring position: unsupported, needs-agreement, or
   consistent, with the groups named under each.

## Pitfalls

- Answering applicability from the product type only. The phase is half the
  question and the early phases are where most of the disagreement lives.
- Turning the guideline into a two-value flag. Reduced and not-yet are the two
  states that carry the actual tailoring information.
- Deleting a group that had not started yet. Deferral keeps it in view for the
  phase that needs it; deletion removes it from the list that gets reviewed.
- Treating the informative annex as binding, so a defensible deviation is
  argued as a non-conformance instead of as a tailoring decision.
- Recording a justification and stopping there. The customer agreement is the
  other half, and the deletion is not settled without it.
- Reporting an over-applied group as a safety finding. It is cost, and mixing
  the two devalues both.
- Comparing phase names as strings. The comparison is ordinal.

## Behavior contract (gate 3)

The context validation, the per-product guideline table, the four-value
applicability states with ordinal phase comparison, the per-context grouping,
the tailoring proposal grading for delete, retain, tailor and defer, the split
between unjustified and arguable, and the unsupported / needs-agreement /
consistent position are exercised by the gate 3 contract test:
scripts/test_q40_applicability_guidelines.py against
scripts/q40_applicability_guidelines_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_applicability_guidelines.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml. The guideline table here is an
  implementable restatement of an informative annex, not a normative one.
- compliance: STANDARDS-REF, gated: false.
