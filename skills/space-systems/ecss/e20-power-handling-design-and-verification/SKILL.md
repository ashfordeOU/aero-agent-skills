---
name: e20-power-handling-design-and-verification
description: "Use when compute the required design level of each radio-frequency chain element and judge the evidence offered for it, under ECSS-E-ST-20C clause 7.3.2.2: resolve the agreed power-handling margin from the element category and from how its capability is substantiated, raise the maximum operating radio-frequency power by that margin to obtain the required design level, check the declared design capability reaches it, then check the substantiation actually demonstrates it - an applied level and a dwell for verification-by-test, a correlated model for verification-by-analysis, a heritage reference and a delta-environment statement for verification-by-similarity. Trigger: ecss, e-st-20-electrical-scope, rf-power-handling-design, agreed-power-handling-margin, required-design-level, elevated-level-substantiation, rf-chain-element-capability, heritage-delta-environment."
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
  tags: [ecss, e-st-20-electrical-scope, e20-power-handling-design-and-verification, rf-power-handling-design, agreed-power-handling-margin, required-design-level, elevated-level-substantiation, heritage-delta-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Power Handling Design and Verification (space-systems/ecss/e20-power-handling-design-and-verification)

Use when the task is the design-and-verification requirement of
ECSS-E-ST-20C clause 7.3.2.2 -- taking the maximum operating
radio-frequency power each chain element sees, raising it by the
agreed power-handling margin, and deciding whether the declared design
capability and the evidence behind it actually reach that level.

## Domain quick reference

- Clause 7.3.2.2 is the step after the general capability check: the
  element is not designed to the operating level, it is designed to
  the operating level raised by an agreed margin. The margin is a
  multiplicative allowance expressed in decibels, so a 3 dB margin
  doubles the required design level and a 6 dB margin quadruples it.
- The agreed margin has two parts. A category part reflects how the
  element fails: a lossy waveguide-run or a terminating-load is
  thermally governed and well predicted, so it carries the smaller
  allowance; a narrow-gap filter-or-diplexer, a switch-or-rotary-joint,
  an antenna-feed or a connector-or-transition is field-governed with a
  sharp onset, so it carries the larger one. A substantiation part
  reflects how well the capability is known: a measured demonstration
  adds nothing, an analytical prediction adds an allowance for model
  uncertainty, and a heritage argument adds more still because the
  configuration is not the one being flown. The programme may agree a
  different category value, but it is agreed and recorded, never
  assumed.
- Design capability and demonstrated capability are separate claims
  and both are checked. A declared design capability that reaches the
  required level proves only that the designer intended it; the
  substantiation is what proves it. A verification-by-test claim needs
  the applied level and a dwell long enough for the failure mechanism
  to appear. A verification-by-analysis claim needs an identified
  model and a statement that it is correlated to measurement -- an
  uncorrelated model is a hypothesis. A verification-by-similarity
  claim needs the heritage item and an explicit statement of how the
  flight environment differs from the heritage one.
- An element substantiated exactly at its required design level is
  compliant. Because the required level is reached through a decibel
  conversion and the operating level through a sum of carrier powers,
  an exactly-compliant case can land a few units in the last place
  short; the comparison absorbs that representation error and the
  agreed margin itself is never reduced to make a case pass.

## Workflow

1. Validate each element: unique identifier, a recognized category, a
   strictly positive maximum operating radio-frequency power, a
   strictly positive declared design capability and a substantiation
   block naming a recognized method.
2. Resolve the agreed margin: take the category allowance, overridden
   by the programme-agreed value when one is recorded, and add the
   allowance implied by the substantiation method. Reject a negative
   agreed value -- a negative margin is a deficit, not an agreement.
3. Raise the maximum operating level by the resolved margin to obtain
   the required design level for that element.
4. Compare the declared design capability with the required design
   level. Flag a shortfall and record the demonstrated margin the
   capability actually supports, so the gap is quantified in decibels
   rather than asserted.
5. Check the substantiation against the required design level: the
   applied level of a measured demonstration, the predicted capability
   of a correlated model, or the heritage capability qualified by the
   delta-environment statement. Flag a missing field, an uncorrelated
   model, a dwell below the agreed minimum and an applied level below
   the required design level as separate findings.
6. Aggregate: report the per-element findings, the element with the
   smallest demonstrated margin, and the overall verdict. The chain
   meets clause 7.3.2.2 only when every element is both designed to
   and substantiated at its required design level.

## Pitfalls

- Applying one blanket margin to the whole chain. A thermally governed
  element and a field-governed element do not share a failure onset,
  and one number either over-designs the first or under-designs the
  second.
- Letting an analytical prediction carry the same margin as a measured
  demonstration. The margin exists partly to cover model uncertainty,
  so the method that carries the most uncertainty carries the largest
  allowance.
- Accepting a declared design capability as verification. The
  capability is the claim; the substantiation block is the evidence,
  and an element can pass the first check and fail the second.
- Taking a heritage argument without a delta-environment statement.
  Without it the argument asserts that two different environments are
  the same environment, which is exactly what needed proving.
- Recording an applied level without a dwell. A brief application does
  not exercise the thermal or multipaction-onset mechanisms the
  demonstration exists to expose.
- Narrowing the agreed margin so a marginal element passes. The
  comparison tolerance exists for floating-point representation error
  only; a real shortfall is redesigned or formally accepted, never
  absorbed by loosening the agreement.

## Behavior contract (gate 3)

The margin resolution, required-design-level arithmetic,
design-capability check and substantiation-evidence logic is exercised
by the gate 3 contract test:
scripts/test_e20_power_handling_design_and_verification.py against
scripts/e20_power_handling_design_and_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_power_handling_design_and_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
