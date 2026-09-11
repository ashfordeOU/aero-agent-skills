---
name: e10-design-methods
description: "Use when select and validate the design methods, tools and models behind a design output under ECSS-E-ST-10C clause 5.4.1.3: separate model-based methods from rule-based ones, establish each model's validation status against the domain of applicability of the present design case, weight the confirmation each model contributes and compare the total against the threshold in the method selection plan, and confirm a recorded rationale exists wherever a design rule is applied outside its documented precedent. Trigger: ecss, e-st-10-system-scope, design-methods, model-validation, domain-of-applicability, design-rules, heritage-precedent, confirmation-weight."
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
  tags: [ecss, e-st-10-system-scope, design-methods, model-validation, domain-of-applicability, design-rules, confirmation-weight]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Design Methods and Models (space-systems/ecss/e10-design-methods)

Use when the task is to show that the design methods, tools and models
producing a design output under ECSS-E-ST-10C clause 5.4.1.3 were
selected as appropriate to that output and shown adequate before the
output was relied on.

## Domain quick reference

- Methods split into two families whose credibility rests on different
  evidence. A model-based method (analytical derivation, numerical
  simulation) is credible through a validation record. A rule-based
  method (empirical correlation, heritage design rule) is credible
  through a documented precedent whose original conditions bound the
  present case. A method type outside both families is an input error.
- A model's validation status is three-valued, not two: validated
  inside the domain the record covers, validated but applied outside
  that domain, or unvalidated. The middle state is the one that gets
  lost -- a real validation record applied to a case it never covered.
- Each model-based method contributes a confirmation weight: its base
  confidence scaled by its validation status. Out-of-domain validation
  contributes partial weight rather than none, because the record
  still says something; an unvalidated model contributes nothing at
  all, whatever base confidence it was assigned.
- The confirmation the output needs comes from the method selection
  plan, not from the methods. A threshold that has never been captured
  is itself a finding as soon as the methods contribute any weight --
  there is no default bar to clear.
- A rule-based method whose precedent does not bound the case is
  permitted, but only against a recorded rationale for relying on it.
  Absence of that rationale is the finding, not the use of the rule.
- Compliance is conjunctive: the model-confirmation and rule-based
  traceability lists must both be empty. A well-confirmed model does
  not license an unjustified design rule beside it.

## Workflow

1. Sort each method behind the design output into the model-based or
   rule-based family; reject an unrecognized method type.
2. For each model-based method, determine its validation status from
   its validation record and whether the present case falls inside the
   domain that record covers.
3. Weight each model's base confidence by its validation status and
   sum the contributions for the output.
4. Compare the total confirmation weight against the threshold
   recorded in the method selection plan; record a finding for a
   shortfall, and for a threshold never captured.
5. For the rule-based methods, determine whether any precedent fails
   to bound the case, and if so confirm a rationale is on record.
6. The design output complies only when both finding lists are empty.

## Pitfalls

- Collapsing validation to a yes/no flag, which files an out-of-domain
  model with the fully validated ones and lets a record earned in one
  regime carry a design case in another.
- Letting a high base confidence stand in for validation. Base
  confidence is scaled by the validation status, so an unvalidated
  model contributes nothing however confident its author.
- Assuming a default confirmation threshold when the method selection
  plan never recorded one. The missing threshold is the finding; an
  invented bar makes any method set appear adequate.
- Rejecting a rule-based method because its precedent does not bound
  the case. Clause 5.4.1.3 permits the reliance -- what it requires is
  the recorded rationale, so the check looks for the rationale.
- Offsetting an unjustified design rule against strong model
  confirmation. The two checks are independent and both must pass.

## Behavior contract (gate 3)

The method-family, validation-status, precedent-bounding, confirmation-
weight, model-confirmation and rule-based traceability logic is
exercised by the gate 3 contract test:
scripts/test_e10_design_methods.py against
scripts/e10_design_methods_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_design_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
