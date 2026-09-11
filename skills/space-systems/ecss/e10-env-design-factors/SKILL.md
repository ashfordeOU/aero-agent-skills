---
name: e10-env-design-factors
description: "Use when you define the natural and induced environments a
  product is exposed to across its mission phases under ECSS-E-ST-10C
  clause 5.3.2: determine the set of applicable environment types from the
  product's declared mission phases, identify the engineering domain each
  environment type belongs to, derive the design-and-test factor for that
  domain from the product's verification approach (qualification test,
  protoflight test, acceptance test, analysis, or similarity), compute the
  resulting test level from a captured limit level, and flag any applicable
  environment for which no limit level has been captured. Trigger: ecss,
  e-st-10c, environment definition, design and test factors, mission phase
  environment, qualification test, protoflight test, acceptance test,
  verification approach, limit level."
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
  tags: [ecss, e-st-10-system-scope, environment-definition, design-and-test-factors, mission-phase, verification-approach, test-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Environments and Design-and-Test Factors (space-systems/ecss/e10-env-design-factors)

Use when the task is to define, for a product, the system environments
it is exposed to and the design-and-test factors applicable to its
design and verification, per ECSS-E-ST-10C clause 5.3.2 -- mapping the
product's mission-phase exposure to applicable environment types,
deriving a design-and-test factor per environment from its engineering
domain and the product's verification approach, and checking that
every applicable environment has a captured limit level.

## Domain quick reference

- Clause 5.3.2 calls for every product to have its applicable natural
  and induced environments defined across the mission phases it
  passes through (for example ground handling, launch, transfer
  orbit, on-station operations), and for the design-and-test factor
  used to convert a captured limit level into a test level to be
  derived per environment from its engineering domain and the
  product's chosen verification approach.
- An environment type belongs to exactly one engineering domain
  (mechanical, thermal, radiation, electromagnetic); the domain, not
  the mission phase, is what selects the design-and-test factor.
- A verification approach is either test-based (qualification test,
  protoflight test, acceptance test), which uses a numeric
  design-and-test factor to convert the limit level into the level
  actually applied during test, or documentation-based (analysis,
  similarity), which instead requires a recorded margin-of-safety
  justification and has no numeric test level.
- A limit level is the environment level the product owner has
  captured for one environment type from the applicable requirement
  set; an applicable environment with no captured limit level is a
  finding, independent of whether the eventual verification approach
  is test-based or documentation-based.

## Workflow

1. Collect the product's declared mission phases and determine the
   union of environment types applicable across them; reject an
   unrecognized mission phase before it enters the assessment.
2. For each applicable environment type, look up its engineering
   domain; reject an unrecognized environment type.
3. Determine whether the product's verification approach is
   test-based or documentation-based. A documentation-based approach
   has no numeric design-and-test factor -- route it to a recorded
   margin-of-safety justification instead of a computed test level.
4. For a test-based approach, look up the design-and-test factor for
   each applicable environment's domain and compute its test level as
   the captured limit level times that factor.
5. Flag every applicable environment with no captured limit level,
   regardless of verification approach.
6. Aggregate the missing-limit-level findings and the computed test
   levels per product; the product's environment definition is not
   complete until the missing-limit-level list is empty.

## Pitfalls

- Selecting the design-and-test factor by mission phase instead of by
  engineering domain -- two environment types active in the same
  phase (for example random vibration and electromagnetic
  susceptibility during launch) can belong to different domains with
  different factors, and collapsing them onto one phase-level factor
  misapplies margin in both directions.
- Requesting a numeric design-and-test factor for a documentation-based
  verification approach (analysis, similarity) -- these approaches
  carry no test level by definition; substituting a factor anyway
  fabricates a test level that was never physically applied.
- Treating an unset limit level as "no requirement" rather than a
  finding -- an applicable environment with no captured limit level
  means the requirement was never captured, which itself blocks the
  environment definition from being complete, not a silent pass.
- Reusing a design-and-test factor from one verification approach
  (for example qualification test) when the product has since moved
  to another approach (for example protoflight test) -- the factor is
  keyed to the approach actually being used, not to whichever value
  was computed first.

## Behavior contract (gate 3)

The mission-phase-to-environment lookup, environment-to-domain lookup,
verification-approach classification, design-and-test factor lookup,
test-level computation, and per-product review logic is exercised by
the gate 3 contract test: scripts/test_e10_env_design_factors.py
against scripts/e10_env_design_factors_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e10_env_design_factors.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
