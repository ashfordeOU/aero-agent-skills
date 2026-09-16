---
name: q6013-class-2-hybrid-components
description: "Use when a class 2 hybrid is offered with mixed-class elements. Determine whether a hybrid microcircuit can be bought at the intermediate assurance class of ECSS-Q-ST-60-13C clause 5.6.3: refuse a hybrid carrying no procurement specification reference of its own, grade every constituent element by the class it was itself bought at, admit an element one class short only where an upscreening specification and lot traceability are declared behind it, refuse an element further short than that, cap how much of the assembly may lean on upscreening with an exact equality treated as within the cap, and take the weakest admissible element as the effective class. Trigger: ecss, q-st-60-13c-clause-5-6-3, class-two-hybrid-procurement, hybrid-element-procurement-class, hybrid-element-upscreening-recovery, upscreened-element-share-cap, weakest-admissible-element-class, hybrid-procurement-specification-reference."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-2-hybrid-components, class-two-hybrid-procurement, hybrid-element-procurement-class, hybrid-element-upscreening-recovery, upscreened-element-share-cap, weakest-admissible-element-class, hybrid-procurement-specification-reference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Hybrid Components (space-systems/ecss/q6013-class-2-hybrid-components)

Use when the task is the clause 5.6.3 procurement question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a class 2 parts
list carries a hybrid microcircuit assembled from elements bought at
mixed classes, and the question is whether the assembly can be offered
at class 2 at all, and on what the claim is actually resting.

## Domain quick reference

- A hybrid is bought against a specification, not against a vendor part
  number. With no procurement specification reference of its own there
  is nothing to buy it against, and no amount of element grading turns
  that into an admissible purchase.
- The assembled hybrid cannot be stronger than what went into it. Every
  constituent -- die, chip resistor, chip capacitor, substrate,
  interconnect, package -- carries the class it was itself bought at,
  and the weakest of them sets what the assembly can claim.
- An element with no specification reference of its own is not a weak
  element, it is an ungradable one. It is refused at validation rather
  than given the lowest class and carried into the arithmetic.
- The intermediate class admits a recovery route the top class does not:
  an element one class short can reach the target through upscreening,
  but only where the upscreening specification is named and the lot
  traceability behind it is declared. An upscreening claim with neither
  is a statement of intent, not evidence.
- The recovery has a reach and a volume limit. An element further short
  than one class is not recoverable at any evidence level, and past a
  declared share of the assembly a hybrid leaning on upscreening is an
  upscreened build wearing the target class.
- An element that reaches the target by upscreening claims the target
  and no more. Crediting it with the class of the upscreening programme
  would let a recovered element pull the whole assembly upward, which is
  the opposite of what the weakest-element rule is for.

## Workflow

1. Read the offered hybrid and refuse it outright where it carries no
   procurement specification reference; report that and stop.
2. Normalise every constituent element: a known element kind, a
   non-empty specification reference of its own, a known procurement
   class, and an upscreening block that is a mapping when present.
3. Refuse a duplicate element -- the same kind against the same
   specification twice -- so one element cannot be counted twice into a
   share it would otherwise breach.
4. Grade each element against the target class. At or above the target
   it is admissible unaided; one class short with named upscreening and
   declared lot traceability it is recoverable; anything else is
   refused, and the reason is recorded against the element kind.
5. Take the unaided share and the upscreened share over the element
   count, and compare the upscreened share with the declared cap,
   treating an exact equality as within the cap.
6. Take the effective class as the weakest rank among the elements, a
   recovered element counting as the target class and no better.
7. Return one verdict -- admissible, admissible after upscreening, or
   refused -- with the effective class, both shares, the recovered
   elements, the refused elements and every finding.

## Pitfalls

- Accepting a hybrid on the strength of its elements alone. A complete
  set of well-bought elements with no procurement specification over
  them is a bag of parts; the specification is what the purchase and
  the incoming inspection are actually written against.
- Averaging the element classes. The assembly fails where its weakest
  constituent fails, so an average lets three strong elements carry one
  weak one and reports a class the hybrid cannot hold.
- Treating an upscreening claim as evidence. Without a named
  specification and declared lot traceability there is nothing to audit,
  and an element recovered on that basis is recovered on paper only.
- Stretching the recovery past one class. Upscreening closes a gap it
  was written to close; an element two classes short needs the
  procurement redone, not more screening on what was already bought.
- Letting the whole assembly lean on upscreening. Each element can pass
  its own test while the build as a whole is an upscreened one, which is
  why the share carries a cap of its own.
- Widening the share cap so a build that lands exactly on it passes. An
  exact equality is a representation question the comparison already
  absorbs; a share above the cap is above it.
- Crediting a recovered element with the class of the upscreening
  programme. It reaches the target, and reporting it any higher lets a
  recovered element raise a class the unaided elements never supported.

## Behavior contract (gate 3)

The procurement specification refusal, element record validation, class
ranking, upscreening evidence test, one-class recovery reach, share cap
comparison, weakest-element effective class and verdict precedence are
exercised by the gate 3 contract test:
scripts/test_q6013_class_2_hybrid_components.py against
scripts/q6013_class_2_hybrid_components_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_hybrid_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
