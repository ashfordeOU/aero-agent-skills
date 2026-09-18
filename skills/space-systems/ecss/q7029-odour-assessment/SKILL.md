---
name: q7029-odour-assessment
description: "Evaluate the acceptability of the odour an offgassing sample presents to a trained sensory panel under ECSS-Q-ST-70-29: keep only the scores of judges currently qualified on the reference set, check the panel is still large enough once they are dropped, average the intensity ratings, test the spread for a panel that did not agree, and grade the result against the acceptance rating. Use when an offgassing test has produced panel scores and they must become a defensible odour verdict rather than an average. Trigger: ecss, q-st-70-29, offgassing-odour-assessment, offgassing-sensory-panel, offgassing-odour-rating-scale, offgassing-panel-qualification, offgassing-panel-dispersion, crew-compartment-offgassing."
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
  tags: [ecss, q-st-70-materials-scope, q7029-odour-assessment, offgassing-odour-assessment, offgassing-sensory-panel, offgassing-odour-rating-scale, offgassing-panel-qualification, offgassing-panel-dispersion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Odour Assessment (space-systems/ecss/q7029-odour-assessment)

Use when the task is the odour step of ECSS-Q-ST-70-29: turning the individual
intensity ratings given by a trained sensory panel on an offgassing sample into
an acceptability verdict for a crew compartment, together with the reasons the
verdict can or cannot be relied on.

## Domain quick reference

- The rating scale is bounded and ordinal: from undetectable at the bottom to
  irritating at the top, in fixed steps a judge may halve but not exceed. A
  score outside the scale is a transcription error, not a strong opinion, and
  is refused rather than clamped.
- Only a judge currently qualified on the reference odour set contributes.
  Qualification lapses, so the raw sheet usually contains scores that have to
  be set aside; the panel size that matters is the size after they are.
- A panel below its minimum size does not produce a weaker verdict, it
  produces no verdict. The correct output is a finding calling for the test to
  be repeated with a full panel.
- Agreement is part of the result. A mean that sits comfortably under the
  acceptance rating but is built from one undetectable and one irritating
  score is not an acceptable sample; it is an unrepeatable measurement, and
  the dispersion check is what surfaces it.
- A single score at the top of the scale overrides the mean. One judge finding
  the sample irritating is a veto, because the crew member who reacts that way
  is the case the limit exists for.

## Workflow

1. Validate every score against the bounded scale and every judge entry
   against its qualification flag; refuse a malformed sheet outright.
2. Separate the qualified scores from the rest and record which judges were
   set aside and why.
3. Compare the qualified panel size with the declared minimum. Below it, stop
   and return the incomplete-panel finding rather than a number.
4. Compute the mean intensity of the qualified scores.
5. Compute the dispersion of those scores as the sample standard deviation and
   compare it with the agreement threshold.
6. Test for a veto score at the top of the scale.
7. Grade the mean against the acceptance rating, treating a mean sitting
   exactly on the rating as meeting it and absorbing representation error with
   a named tolerance rather than by moving the rating.
8. Report the verdict, the qualified panel size, the mean, the dispersion and
   every finding: dropped judges, short panel, poor agreement, veto score.

## Pitfalls

- Averaging the whole sheet because more scores look like more evidence.
  Unqualified judges are not a smaller weight, they are not evidence.
- Passing a sample on the mean alone when the panel did not agree. The spread
  is the signal that the sample presents differently to different people, and
  it belongs in the verdict.
- Letting a top-of-scale score be averaged away by mild scores. The veto is
  deliberate; the mean does not represent the judge who could not stay in the
  compartment.
- Reporting a verdict from a short panel with a caveat instead of a finding. A
  panel under its minimum has no statistical standing and the result must not
  be carried into acceptance.
- Nudging the acceptance rating upward to absorb a mean a hair above it. The
  rating is fixed; only representation error is absorbed, by the tolerance
  inside the comparison.

## Behavior contract (gate 3)

The scale validation, qualification filtering, minimum-panel rule, mean and
dispersion computation, veto rule and acceptance grading are exercised by the
gate 3 contract test: scripts/test_q7029_odour_assessment.py against
scripts/q7029_odour_assessment_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7029_odour_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
