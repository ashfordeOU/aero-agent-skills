---
name: e2040-device-verification-method-concepts
description: "Assess whether the evidence gathering method allocated to each device requirement can actually settle it, under ECSS-E-ST-20-40C clause 4.2: fold test, analysis, similarity, review of design and inspection onto one set, derive the admissible methods from the kind of requirement and whether it carries a number, rule on a similarity claim only against a named heritage item qualified to at least the severity now claimed, and report every requirement left with no method or with evidence that would not demonstrate it. Use when a verification matrix is being allocated or reviewed. Trigger: ecss, e-st-20-40c, device-verification-method-allocation, verification-by-similarity-heritage, review-of-design-admissibility, device-workmanship-inspection, numeric-requirement-evidence, device-verification-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-verification-method-concepts, device-verification-method-allocation, verification-by-similarity-heritage, review-of-design-admissibility, device-workmanship-inspection, numeric-requirement-evidence, device-verification-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Verification Method Concepts (space-systems/ecss/e2040-device-verification-method-concepts)

Use when the task is the verification method concepts of ECSS-E-ST-20-40C
clause 4.2 -- deciding which kind of evidence shows that a device does
what its specification says and carries no built-in defect, and whether
the method somebody allocated to a requirement is evidence for that
requirement at all.

## Domain quick reference

- Five methods carry the whole verification argument: exercising the
  device, computing its behaviour, arguing from hardware already
  qualified, examining the design documentation, and examining the
  hardware itself. They are not interchangeable, and which one is
  admissible is a property of the requirement, not of the programme
  budget.
- A requirement carrying a number is settled by producing a number.
  Reading a drawing confirms that a design intends a value; it does not
  show the built device achieves it, so a numeric limit removes the
  documentary methods from the admissible set whatever the requirement
  is about.
- What a device survives is demonstrated on hardware, or argued from
  hardware already qualified to at least the same severity. Examining a
  device tells nothing about what it will withstand.
- A built-in defect is seen, not computed. Workmanship and cleanliness
  properties are answered by examining the article or by exercising it
  until a defect shows, and an analysis of them is an argument that no
  defect should exist rather than evidence that none does.
- Similarity is the only method whose admissibility depends on
  something outside the requirement. It needs a named heritage item,
  qualified to an environment at least as severe as the one being
  claimed, and unchanged in the respect being claimed. Missing any of
  the three, it is an assertion.
- Evidence strength and admissibility are separate questions. Ranking
  the methods is useful for reporting what a specification leans on;
  it never promotes an inadmissible method into an admissible one.

## Workflow

1. Fold every method and requirement-kind spelling onto the canonical
   sets, refusing an unrecognised one rather than defaulting it.
2. For each requirement, derive the admissible method set from its kind
   and from whether it carries a numeric limit. Do this before looking
   at what was allocated, so the allocation is compared with a
   standard rather than rationalised.
3. Compare the allocated method with that set. A requirement with no
   method at all is reported the same way as one with the wrong method,
   because both leave the property undemonstrated.
4. Where similarity is allocated, rule on the heritage separately:
   named item, qualified severity at least the claimed severity, design
   unchanged. Treat an exactly equal severity as covered, absorbing the
   representation error rather than refusing a legitimate claim.
5. Count the allocation across the specification so the balance of
   methods is visible, and list the requirements left unallocated.
6. Report the strongest evidence each requirement was given alongside
   the verdict, so a specification leaning on documentary methods is
   visible even when every allocation is admissible.
7. Report a specification that states no workmanship requirement at
   all: nothing in it then asks the device to be free of built-in
   defects.

## Pitfalls

- Allocating review of design to a requirement with a number in it. It
  is the commonest inadmissible allocation and it survives review
  because the drawing does show the value -- as an intention.
- Treating similarity as free. A heritage claim without a named item,
  a qualified severity and an unchanged-design statement transfers no
  evidence, and it is usually discovered at qualification review when
  there is no time left to test.
- Refusing a heritage item qualified to exactly the claimed severity.
  An equality is covered; refusing it on a floating-point comparison
  rejects a legitimate claim for a representation reason.
- Analysing workmanship. An analysis says a defect should not occur; it
  cannot say none is present in the article being delivered.
- Reading an environmental requirement as satisfiable by examination.
  Examining a device says nothing about what it withstands, and this
  allocation usually appears when the test would have been expensive.
- Confusing how strong a method is with whether it is allowed. A
  ranking is a reporting aid; the admissible set is the rule, and
  nothing in the ranking moves a method into it.

## Behavior contract (gate 3)

The method and kind folding, admissible-method derivation, numeric
limit rule, similarity heritage ruling, per-requirement allocation
verdicts, method coverage counting and unallocated requirement listing
are exercised by the gate 3 contract test:
scripts/test_e2040_device_verification_method_concepts.py against
scripts/e2040_device_verification_method_concepts_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_verification_method_concepts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
