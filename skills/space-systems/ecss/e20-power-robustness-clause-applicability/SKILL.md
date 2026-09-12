---
name: e20-power-robustness-clause-applicability
description: "Use when determine which ECSS-E-ST-20C clause 5.7.1 robustness provisions bind the power subsystem, which bind the payload, and which bind both across their shared interface: categorize each element by its scoping role, resolve every provision-element pair as applicable, applicable-via-interface or not-applicable, derive the governing interface threshold as the strictest demand on either side rather than the provision's own floor, grade demonstrated capability against that threshold, keep absent evidence distinct from a failed margin, and refuse an exclusion that carries no recorded rationale. Trigger: ecss, e-st-20-electrical-scope, power-robustness-provisions, clause-applicability-scoping, power-payload-interface, governing-withstand-threshold, applicability-rationale-record, robustness-coverage-matrix."
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
  tags: [ecss, e-st-20-electrical-scope, e20-power-robustness-clause-applicability, power-robustness-provisions, clause-applicability-scoping, power-payload-interface, governing-withstand-threshold, robustness-coverage-matrix]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Power Robustness Applicability (space-systems/ecss/e20-power-robustness-clause-applicability)

Use when the task is the ECSS-E-ST-20C clause 5.7.1 scoping question
that opens the robustness chapter: a robustness provision is addressed
to the power subsystem, to the payload, or to both of them together,
and the elements under assessment have to be matched against that
address before any withstand figure is argued.

## Domain quick reference

- Clause 5.7.1 is an applicability statement, not a performance
  requirement. Getting it wrong in either direction is costly: a
  provision wrongly excluded leaves a robustness hole nobody verifies,
  and a provision wrongly imposed loads a payload with a withstand
  case it was never meant to carry.
- Three scoping roles are distinguished on the element side. A power
  subsystem generates, stores and distributes; a payload draws from
  the distributed bus; a payload with internal power conditioning does
  both, and is therefore reached by provisions written for either
  side. That third role is the one most often mis-scoped, because it
  looks like a payload in the product tree.
- Three scopes are distinguished on the provision side: power
  subsystem, payload, or both. Crossing scope with role gives three
  outcomes. Applicable is the direct case. Applicable-via-interface is
  the case where a provision written for the other side still reaches
  an element because that element presents the power/payload
  interface, and the provision binds at that port rather than
  throughout the element. Not-applicable is a genuine exclusion.
- Where a provision reaches both sides, the number that governs the
  shared interface is not the provision's own figure -- it is the
  strictest demand made by any element the provision reaches. The
  provision's figure is a floor, and an element that needs more pulls
  the interface up for everyone on it.
- Grading is three-valued, not two. Demonstrated capability at or
  above the governing threshold passes; below it fails; and absent
  evidence is neither -- it is an open verification item, and folding
  it into the failure count hides which of the two problems is real.
- A not-applicable pair is an assertion the programme has to defend.
  Every exclusion carries a recorded rationale, and an exclusion
  without one is a scoping finding in its own right, even if the
  exclusion would have been correct.

## Workflow

1. Validate each provision: known scope, known robustness parameter,
   a positive required withstand figure, a non-blank identifier.
2. Validate each element: known scoping role, whether it presents the
   power/payload interface, its demonstrated capability map and its
   own interface demand map. Reject an unknown parameter or a negative
   value in either map, and reject duplicate identifiers.
3. Resolve applicability for every provision-element pair. Take a
   payload with internal power conditioning as reached by every scope;
   take the interface flag as what converts a cross-side provision
   from not-applicable into applicable-via-interface.
4. For each provision, compute the governing threshold across the
   elements it actually reaches: the larger of the provision floor and
   the strictest interface demand. Elements the provision does not
   reach do not contribute a demand.
5. Grade each reached element against that governing threshold as
   pass, fail, or evidence-missing, and record the percentage margin
   where evidence exists.
6. For each excluded pair, look up the recorded rationale and raise a
   finding when it is absent or blank. Aggregate into a coverage
   fraction over reached pairs; the scoping is closed only when no
   finding of either kind remains.

## Pitfalls

- Scoping by product-tree position instead of by function. A payload
  that conditions its own power sits under the payload branch but is
  reached by the power-side provisions as well, and reading its tree
  position as its scoping role drops those provisions silently.
- Collapsing applicable-via-interface into applicable. The provision
  binds at the interface port, not across the whole element; treating
  it as a full-element requirement imposes a withstand case the
  element never needed away from that port.
- Grading everyone against the provision's own figure. On a shared
  interface the strictest demand governs, so an element that meets the
  provision floor can still be short of the threshold its neighbour
  imposes on the same bus.
- Counting missing evidence as a failure, or as a pass. It is a third
  state; merging it into either one destroys the distinction between
  "this element cannot do it" and "nobody has shown that it can".
- Recording an exclusion and moving on. The applicability decision is
  the deliverable of this clause, so an exclusion with no rationale is
  the one finding that cannot be closed by any later robustness
  analysis.

## Behavior contract (gate 3)

Provision and element validation, role categorization, applicability
resolution across all scope-role crossings, governing-threshold
derivation, three-valued margin grading, rationale checking and
coverage aggregation are exercised by the gate 3 contract test:
test_e20_power_robustness_clause_applicability.py against
e20_power_robustness_clause_applicability_logic.py (stdlib unittest,
offline, deterministic). Run:
`python3 scripts/test_e20_power_robustness_clause_applicability.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
