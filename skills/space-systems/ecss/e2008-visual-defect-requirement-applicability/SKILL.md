---
name: e2008-visual-defect-requirement-applicability
description: "Use when a qualification population needs its applicability envelope fixed before any defect call is dispositioned. Determine which solar cell assemblies the visible defect requirements actually govern when a qualification approval is being granted under ECSS-E-ST-20-08C clause 6.4.3.1.1: separate items put forward for an approval from those circulated for information or running against lot acceptance, check each assembly category against the declared applicable set, send an item built to an unqualified build standard toward a qualification extension rather than a pass or a fail, hold a non-representative sample back from carrying the approval, and name the categories no governed item covers. Trigger: ecss, e-st-20-08c, clause-6-4-3-1-1, sca-visual-defect-applicability, qualification-approval-population-scope, cell-assembly-build-standard-envelope, qualification-extension-route, unrepresented-assembly-category."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-visual-defect-requirement-applicability, sca-visual-defect-applicability, qualification-approval-population-scope, cell-assembly-build-standard-envelope, qualification-extension-route, unrepresented-assembly-category, solar-cell-assembly-sample-representativeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Visual Defect Requirement Applicability (space-systems/ecss/e2008-visual-defect-requirement-applicability)

Use when the task is the applicability statement of ECSS-E-ST-20-08C clause
6.4.3.1.1 -- fixing which cell assemblies the visible defect rules reach when
a qualification approval is granted, before anybody grades a single defect.

## Domain quick reference

- The clause does not define a defect. It says who the defect rules apply to,
  and that is a separate question answered first. A defect call made against
  an item the rules never governed is not evidence, and a category nobody
  submitted leaves a hole in the approval that no amount of inspection closes.
- Four attributes move an item in or out of the envelope: the purpose it was
  submitted under, its assembly category, its build standard, and how far it
  reproduces the flight process.
- Purpose is the first filter and it is not a quality judgement. The rules bite
  where an approval is being granted or extended. An item circulated for
  information has no approval turning on it. An item running against lot
  acceptance inherits an approval that already exists rather than creating one,
  so it is dispositioned by acceptance criteria and not by this clause.
- Category is the second. An approval names the assembly categories it covers;
  crediting an item outside that list widens the approved population past what
  was actually examined.
- An unqualified build standard is not a failure. The item is squarely inside
  the subject matter of the rules and outside the envelope of this approval, so
  it routes to a qualification extension. Reporting it as a reject destroys a
  perfectly good article and hides the real finding, which is that the approval
  does not yet stretch that far.
- Representativeness is the quiet one. A sample that does not reproduce the
  flight process can inspect perfectly and still carry nothing, because what
  was examined is not what will fly. It goes to review rather than counting
  toward coverage.
- Governed and counts-toward-coverage are two different flags. An extension
  item and a non-representative item are both governed by the rules; neither
  closes out the category it belongs to.
- The envelope is only established when every applicable category carries at
  least the required number of governed items. Coverage is the output that
  actually matters, because it is the one the approval rests on.

## Workflow

1. Validate the policy: the applicable categories with no repeats, the
   purposes that grant an approval, the qualified build standard, the
   representativeness floor, and the items each category needs.
2. Per item, apply the filters in order -- purpose, category, build standard,
   representativeness -- and stop at the first that moves it out. The order is
   load-bearing: an information-only item of an uncovered category is out
   because nobody is approving it, and reporting the category instead points
   the reader at the wrong fix.
3. Mark each item with its state and, separately, whether it counts toward
   coverage of its category.
4. Tally coverage per applicable category against the required item count and
   name every category that falls short.
5. Take the governed sample fraction over the submission; it says how much of
   what was put forward the clause actually reaches.
6. Close with the envelope verdict, the extension list, the out-of-scope list
   and the review list kept apart, because each drives a different action.

## Pitfalls

- Grading defects before the envelope is fixed. The result is a pile of
  dispositions against items that were never in scope, and a reviewer cannot
  tell which of them supported the approval.
- Failing an item for an unqualified build standard. The article may be
  faultless; what is missing is the extension, and a reject line loses that.
- Letting an information-only item count toward category coverage. It was never
  offered for approval, so the category is still unexamined.
- Treating lot acceptance as the same activity. Acceptance runs against its own
  criteria under an approval that already exists; folding it in here makes the
  approval look broader than it is.
- Accepting a non-representative sample because it inspected clean. Clean is
  the expected result when the sample is not what will fly.
- Reporting a single verdict with no coverage breakdown. An established
  envelope and an envelope with one empty category read the same on a summary
  line and lead to completely different next steps.
- Comparing a representativeness figure with the policy floor by bare
  arithmetic. The figure is a ratio of declared quantities, so a sample sitting
  exactly on the floor can evaluate a few units in the last place below it; the
  comparison absorbs that representation error while the floor stays untouched.

## Behavior contract (gate 3)

The purpose, category, build-standard and representativeness filters, their
ordering, the governed versus counts-toward-coverage split, the per-category
coverage tally and the governed sample fraction are exercised by the gate 3
contract test:
scripts/test_e2008_visual_defect_requirement_applicability.py against
scripts/e2008_visual_defect_requirement_applicability_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_visual_defect_requirement_applicability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
