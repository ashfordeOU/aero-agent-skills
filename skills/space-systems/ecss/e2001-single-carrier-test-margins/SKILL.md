---
name: e2001-single-carrier-test-margins
description: "Use when determine the single-carrier multipactor test-margin an ECSS-E-ST-20-01C clause 4.6.3.1 verification campaign owes a radio-frequency article: categorize the article as equipment-level or component-level, categorize its multipactor design-heritage as recurrent, modified or first-of-kind, derive the required decibel-margin from that pair with uplifts for a single tested article and for a transposed multipactor-threshold, convert the declared maximum-operating-power into the power-level the multipactor-test must actually apply, and compare the measured multipactor-threshold against that level to report every article margin-compliant or margin-deficient. Trigger: ecss, e-st-20-01c, multipactor-test-margin, single-carrier-multipactor, design-heritage-category, multipactor-threshold, rf-breakdown-margin, tested-article-count."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-single-carrier-test-margins, multipactor-test-margin, single-carrier-multipactor, design-heritage-category, multipactor-threshold, rf-breakdown-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Single-Carrier Test Margins (space-systems/ecss/e2001-single-carrier-test-margins)

Use when the task is setting the single-carrier multipactor test-margin of
ECSS-E-ST-20-01C clause 4.6.3.1 -- deciding, from the type of the article
under test and the multipactor design-heritage it can claim, how far above the
declared maximum-operating-power a single-carrier multipactor test has to be
driven before the article may be declared free of multipactor.

## Domain quick reference

- The margin is a power ratio in decibels, not an absolute power. It is
  applied to the article's declared maximum-operating-power for the
  single-carrier case, and it sets the power-level the multipactor test must
  actually reach: `required = maximum-operating-power x 10^(margin/10)`.
- Clause 4.6.3.1 makes the margin a function of two categorizations, not of
  the power alone. The first is the article type -- an equipment-level unit
  whose internal radio-frequency path is tested as built, versus a
  component-level item (connector, waveguide section, filter body) tested
  outside its final assembly, where the flight configuration adds gap and
  surface uncertainty the test did not see. The second is design-heritage:
  recurrent (an identical build standard already multipactor-tested),
  modified (a heritage design changed inside a validated envelope), or
  first-of-kind (no multipactor evidence for this geometry at all).
- Two uplifts sit on top of the base value. Testing a single article gives no
  evidence about build-to-build spread of the multipactor-threshold, so it
  costs an extra decibel; a threshold transposed from a test at a different
  frequency or gap, rather than measured on the article itself, costs another.
- The margin is demonstrated, not assumed. The achieved margin is the measured
  multipactor-threshold over the declared maximum-operating-power in decibels;
  the article is compliant only when that number reaches the required one. An
  article with no measured threshold on record is a finding, never a pass.
- The default numeric policy table in the logic module is this leaf's
  house policy for the clause; a project applying a different issue of the
  standard overrides it through the policy argument rather than editing the
  procedure.

## Workflow

1. Categorize the article as equipment-level or component-level, rejecting an
   article type the policy table does not recognize before it enters the
   campaign.
2. Categorize the multipactor design-heritage as recurrent, modified or
   first-of-kind. Heritage is a claim about the tested build standard, so a
   design change outside the validated envelope demotes it to first-of-kind.
3. Read the base decibel-margin for the (article-type, heritage) pair from
   the policy table.
4. Add the single-article uplift when only one article is put through the
   multipactor test, and the transposition uplift when the multipactor
   threshold is carried over from another frequency or gap rather than
   measured directly.
5. Convert the declared maximum-operating-power into the power-level the test
   must apply, and record it as the campaign's test-level requirement.
6. Compute the achieved margin from the measured multipactor-threshold and
   compare it against the required margin; report the shortfall in decibels
   when it falls short, and flag an article with no measured threshold as an
   open finding.
7. Aggregate per-article verdicts into a campaign verdict: the campaign is
   compliant only when no article is deficient and none is missing evidence.

## Pitfalls

- Applying the equipment-level margin to a component tested outside its flight
  assembly -- the component test did not see the final gap, surface finish or
  venting path, which is exactly why its base margin sits higher.
- Claiming recurrent heritage after a design change and dropping straight to
  the lowest margin; heritage covers the build standard actually tested, and a
  change outside the validated envelope resets the article to first-of-kind.
- Testing one article and treating the result as the population's
  multipactor-threshold -- build-to-build spread is unmeasured, which is what
  the single-article uplift pays for.
- Reading "no violation" as compliant when no multipactor-threshold was ever
  measured; an absent threshold means the demonstration was never made.
- Rounding the comparison to whole decibels, or widening the required margin
  to absorb an exactly-compliant case; the limit stays as specified and only
  floating-point representation error is absorbed by a named tolerance.

## Behavior contract (gate 3)

The categorization, margin-derivation, test-power-conversion and
compliance-comparison logic is exercised by the gate 3 contract test:
scripts/test_e2001_single_carrier_test_margins.py against
scripts/e2001_single_carrier_test_margins_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_single_carrier_test_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
