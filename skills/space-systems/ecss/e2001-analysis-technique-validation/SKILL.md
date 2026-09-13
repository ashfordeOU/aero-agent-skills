---
name: e2001-analysis-technique-validation
description: "Use when validate the multipaction analysis-technique and its software under ECSS-E-ST-20-01C clause 5.3.2.4 before any predicted breakdown-level is used as evidence: categorize each evidence-record as demonstrable-heritage or measured-correlation, check a heritage-record for the same tool-build, a comparable configuration and a prior multipaction-test confrontation, check a correlation-record point by point for prediction-deviation inside the declared agreement-criterion in decibel, assemble the validated applicability-envelope in frequency-gap-product, geometry-family and electrode-material, then confirm every analysis-case falls inside it. Trigger: ecss, e-st-20-electrical-scope, analysis-technique-validation, demonstrable-heritage, measured-correlation, agreement-criterion, applicability-envelope, frequency-gap-product, prediction-deviation."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-analysis-technique-validation, analysis-technique-validation, demonstrable-heritage, measured-correlation, agreement-criterion, applicability-envelope, frequency-gap-product, prediction-deviation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Analysis Technique Validation (space-systems/ecss/e2001-analysis-technique-validation)

Use when the task is the analysis-technique validation of
ECSS-E-ST-20-01C clause 5.3.2.4 -- establishing, before a predicted
multipaction breakdown-level is offered as verification evidence, that
the theory and the software implementing it have been shown
trustworthy, either by demonstrable-heritage or by comparison against
measured-results, and establishing the region over which that
demonstration actually holds.

## Domain quick reference

- An analysis-technique is the pair theory plus software build. Neither
  half validates alone: a sound theory wrongly implemented and a
  well-exercised binary running an inapplicable model fail the same
  way, so the evidence is always attached to a named tool-build, not to
  a tool name.
- The demonstrable-heritage route rests on a prior application of the
  same build to a comparable configuration whose hardware was
  afterwards confronted with a multipaction-test result. A prior run
  that was never checked against measured-results is usage history, not
  heritage; it demonstrates that the software executes, not that it
  predicts.
- The measured-correlation route rests on a set of configurations whose
  breakdown-levels were measured. Each point yields a
  prediction-deviation, the ratio in decibel of the predicted
  breakdown-level to the measured one, and the route is accepted only
  when every point sits inside the declared agreement-criterion. A
  single point is an anecdote, so a minimum point count applies.
- Both routes validate only over the region the evidence touched. That
  region is the applicability-envelope: the span of
  frequency-gap-product covered, plus the geometry-families and the
  electrode-materials that appeared. The frequency-gap-product is the
  natural coordinate because the resonance condition of a
  parallel-plate gap scales with it.
- An analysis-case whose frequency-gap-product, geometry-family or
  electrode-material sits outside the applicability-envelope is not
  covered. The technique is not thereby wrong, but its validation says
  nothing there, and the result cannot be offered as substantiation
  until the envelope is extended with further evidence.

## Workflow

1. Declare the technique: name, tool-build version, any earlier builds
   claimed as an equivalent lineage, and the theory basis. Reject a
   theory basis outside the recognised families before any evidence is
   read.
2. Categorize every evidence-record into exactly one route --
   demonstrable-heritage or measured-correlation. Reject an
   uncategorized record rather than guessing its route.
3. For each heritage-record, check four things: the build is the
   technique build or a declared ancestor, a prior application is
   named, the geometry-family and electrode-material are recorded, and
   the prior case was confronted with a multipaction-test result.
   Record each shortfall as a finding.
4. For each correlation-record, compute the prediction-deviation of
   every comparison point, flag a point outside the declared
   agreement-criterion, and flag a record resting on fewer comparison
   points than the minimum. Retain the worst and mean deviation for the
   validation file.
5. Assemble the applicability-envelope from the accepted records only:
   the minimum and maximum frequency-gap-product, the set of
   geometry-families and the set of electrode-materials. Rejected
   evidence contributes nothing, not even its coordinates.
6. Test every intended analysis-case against the envelope and report
   the verdict: validated when all cases are covered, validated with a
   restricted envelope when one or more sit outside, and not-validated
   when no record survived assessment.

## Pitfalls

- Accepting prior use of the tool as heritage. Heritage is a prediction
  that was afterwards confronted with a multipaction-test outcome; a
  long record of runs that were never checked adds confidence in the
  user, not in the technique.
- Validating the tool rather than the build. A solver revision can
  change the secondary-emission model or the electron-tracking scheme,
  so evidence raised on an undeclared earlier build has to be carried
  across explicitly through a version lineage or not at all.
- Averaging the comparison points and declaring agreement. The
  criterion applies point by point; a set that averages inside it while
  one point sits far outside has an unmodelled effect somewhere in the
  envelope, and the mean hides exactly the case that will govern.
- Applying the validated technique outside the evidence span. A
  correlation exercise run between two frequency-gap-product values
  says nothing an order of magnitude away, and a validation quoted
  without its envelope invites precisely that extrapolation.
- Comparing a deviation with the agreement-criterion by bare
  arithmetic. The deviation is a difference of logarithms, so a point
  exactly on the criterion can land a few units in the last place
  above it; the comparison absorbs that representation error while the
  criterion itself stays untouched.

## Behavior contract (gate 3)

The route categorization, heritage checks, correlation-deviation
checks, applicability-envelope assembly and coverage verdict are
exercised by the gate 3 contract test:
scripts/test_e2001_analysis_technique_validation.py against
scripts/e2001_analysis_technique_validation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_analysis_technique_validation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
