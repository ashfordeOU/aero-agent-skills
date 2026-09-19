---
name: q7026-acceptance-rejection-criteria
description: "Evaluate a crimped termination against the acceptance and rejection criteria that belong to each defect category under ECSS-Q-ST-70-26C. Use when inspection findings from a crimping bench have to become a disposition rather than a list: grade measured pull-off force against the minimum tabulated for that conductor size, count damaged strands against an allowance that scales with the strand count, apply the per-category severity so one major finding governs the whole termination, and escalate a sampled lot to full inspection when a sample is rejected. Trigger: ecss, q-st-70-26, crimp-acceptance-rejection-criteria, crimp-defect-category-severity, crimp-pull-off-force-minimum, crimp-strand-damage-allowance, crimp-lot-sampling-escalation."
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
  tags: [ecss, q-st-70-26-crimping-scope, q7026-acceptance-rejection-criteria, crimp-defect-category-severity, crimp-pull-off-force-minimum, crimp-strand-damage-allowance, crimp-lot-sampling-escalation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Acceptance and Rejection Criteria (space-systems/ecss/q7026-acceptance-rejection-criteria)

Use when the task is the acceptance step of ECSS-Q-ST-70-26C — turning
what an inspector wrote against a crimped termination into a
disposition, one defect category at a time, and saying what that does
to the lot the termination came out of.

## Domain quick reference

- Findings are graded per defect category, not as a heap. Each
  category carries its own declared severity, and the severity is what
  picks the route: scrap, back to the bench, accept with the finding
  on the record, or accept outright. Two terminations with the same
  number of findings can therefore have opposite dispositions.
- The worst finding governs. Severities do not average and they do not
  cancel, so a single major finding takes a termination out however
  clean the rest of it was, and a handful of cosmetic marks never adds
  up to a rejection.
- A defect code nobody declared a severity for is unknown, not
  harmless. Guessing at it accepts a termination against a category
  that was never agreed with the customer, which is the quiet version
  of relaxing the criteria.
- Pull-off force is graded against the minimum tabulated for that
  conductor size. The table is a stepped requirement rather than a
  curve, so an untabulated size is refused and the criterion obtained,
  not interpolated between the two neighbouring rows.
- The strand-damage allowance scales with the conductor. A tenth of a
  fat conductor's strands is a real allowance; the same tenth of a thin
  one rounds to nothing, and below a stated strand count no damage is
  allowed at all because every strand carries a meaningful share.
- A rejected sample says something about the lot, not only about the
  sample. Sampled inspection escalates to full inspection on a
  rejection, rather than discarding the one bad unit and shipping the
  rest of a population that was never looked at.
- A force landing exactly on its tabulated minimum has met it. The
  comparison absorbs the representation error of the load cell
  conversion; the minimum itself is never lowered to let one through.

## Workflow

1. Validate the declared criteria first: a severity for every defect
   category in use, a pull-off table with no size tabulated twice, a
   strand-damage fraction inside zero to one, and a sample size.
2. Validate the inspected termination: identifier, conductor size,
   strand count, damaged-strand count not exceeding it, defect codes
   as a list, and a pull-off force when one was measured.
3. Look up the tabulated minimum for the conductor size and refuse an
   untabulated size rather than interpolating a criterion.
4. Grade the measured force against that minimum, treating an exact
   equality as met through a named tolerance.
5. Compute the strand-damage allowance from the strand count and the
   declared fraction, flooring it, and zero it below the minimum
   strand count for any damage at all.
6. Categorize each declared defect code into its severity, raising on
   a code with no declared severity, and take the worst severity as
   governing the termination.
7. Map the governing severity onto the disposition, then roll the
   graded terminations up into a lot verdict, escalating rather than
   rejecting when the inspection was a sample.

## Pitfalls

- Averaging findings. Three cosmetic marks are not a minor, and a
  major beside two cosmetics is still a rejection; the worst finding
  is the one that decides.
- Silently accepting an undeclared defect code because it sounds
  cosmetic. The severity list is the agreement, and a code outside it
  has to be added to the list before it can be dispositioned.
- Interpolating the pull-off table for a conductor size that is not on
  it. That invents a criterion, and it invents it at exactly the sizes
  nobody agreed a number for.
- Applying a flat strand-damage allowance across conductor sizes. On a
  seven-strand conductor one cut strand is a large fraction of the
  section; on a thick one it is noise.
- Discarding a rejected sample and shipping the remainder. The sample
  was taken to speak for the lot, so a rejection in it escalates the
  inspection instead of ending with that unit.
- Rejecting a pull-off force that landed on the minimum because a
  strict comparison fell the wrong side of a unit conversion.

## Behavior contract (gate 3)

Criteria and termination validation, tabulated pull-off lookup with
refusal to interpolate, the exact-minimum boundary, the scaled
strand-damage allowance, per-category severity with the worst finding
governing, and the sampled-versus-full lot roll-up are exercised by the
gate 3 contract test:
scripts/test_q7026_acceptance_rejection_criteria.py against
scripts/q7026_acceptance_rejection_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7026_acceptance_rejection_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
