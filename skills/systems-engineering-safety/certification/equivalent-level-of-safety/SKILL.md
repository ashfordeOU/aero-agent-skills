---
name: equivalent-level-of-safety
description: "Use when you must develop an Equivalent Level of Safety (ELOS) finding for a civil aircraft or system certification item that cannot show literal compliance with an applicable airworthiness regulation paragraph: state the regulation intent and its safety objective, quantify or qualify the achieved safety level of the design, list the compensating measures that close the gap, compute the safety margin against the numeric probability target (25.1309 catastrophic 1e-9 per flight hour) when the rule is quantitative, and return the finding recommendation (finding recommended, conditional, or not supportable) with the reasons list. Produces the per-item ELOS assessment with margin, compensation coverage and the verdict that gates the certification finding package. Trigger: equivalent level of safety, ELOS finding, deviation finding, regulation intent, compensating measure, non-literal compliance, safety margin, 21.21."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: certification
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: certification
  tags: [equivalent-level-of-safety, elos-finding, deviation-finding, regulation-intent, compensating-measures, non-literal-compliance, safety-margin]
  version: 0.1.0
  author: AeroSkills
---

# Equivalent Level of Safety (systems-engineering-safety/certification/equivalent-level-of-safety)

Use when the task is an Equivalent Level of Safety (ELOS) finding for a
certification item whose design cannot show literal compliance with an
applicable airworthiness regulation paragraph: the design meets the intent
of the rule through compensating measures instead. This leaf implements the
ELOS deviation-finding analysis in pure Python, stdlib only: regulation
intent lookup, probability safety margin, compensation coverage and the
finding recommendation. It pairs with
systems-engineering-safety/certification/certification-basis (the
applicable parts and the path), with
systems-engineering-safety/certification/means-of-compliance (the MOC that
carries the finding evidence) and with avionics/far-cs25/special-conditions
(the novel-feature route this leaf is not). It takes the regulation item and
the achieved safety level as given and evaluates the deviation.

## Domain quick reference

- Regulation intent table (module constant INTENT_TABLE, paraphrase of the
  safety objective, never verbatim rule text):
  - 25.1309 quantitative: catastrophic target 1e-9 per flight hour,
    hazardous 1e-7, major 1e-5, targets keyed by the failure condition
    severity supplied as input.
  - 25.671 qualitative, intent severity hazardous: control system failure
    must not prevent continued safe flight and landing.
  - 23.1309 quantitative, normal category, same target table shape.
  - 25.683 qualitative, intent severity hazardous: control operation must
    not be adversely affected by structural deformation.
  - Any other paragraph is qualitative and needs an intent description
    override; intent severity defaults to major.
- Safety margin: margin = target / achieved probability per flight hour.
  Margin 1.0 is the typical ELOS acceptance line (achieved at or better
  than target); the finding is always authority-approved in practice.
- Margin in dB: margin_db = 10 * log10(target / achieved).
- Expected compensating measures (EXPECTED_MEASURES, by severity and
  quantitative flag): catastrophic 3 quantitative / 2 qualitative, hazardous
  2 quantitative / 1 qualitative, major 2, minor and none 1.
- Compensation coverage: coverage = accepted measure types / expected
  count, capped at 1.0. Accepted types come from the MEASURE_RULES table:
  redundancy anchors quantitative catastrophic, hazardous and major items
  and any qualitative item; monitoring is accepted only with redundancy or
  an operating limitation; an operating limitation applies to qualitative
  items and needs a flight crew procedure; a flight crew procedure is
  accepted with redundancy or an operating limitation; a maintenance action
  counts only when it restores a degraded function before the next flight;
  an inspection interval counts for fatigue and aging items only (25.571,
  25.573, 23.571).
- Verdict ladder (elos_verdict): quantitative items PASS with margin >= 1.0
  and coverage >= 1.0 and FAIL when margin < 1.0 regardless of measures;
  qualitative items PASS with coverage >= 1.0 and no primary safety
  function gap (redundancy or monitoring missing blocks the
  recommendation). Coverage between 0.5 and 1.0 is CONDITIONAL, below 0.5
  is FAIL. Verdict text: PASS is finding recommended, CONDITIONAL is
  finding conditional, FAIL is finding not supportable.

## Workflow

1. Confirm the item context: the applicable regulation paragraph, the
   failure condition severity, and the achieved probability when the rule
   carries a numeric target (these come from the certification basis and
   the functional hazard assessment; this leaf does not re-derive them).
2. State the regulation intent with intent_for(paragraph, severity). The
   function returns quantitative, target_prob or intent_severity and the
   intent text; supply intent_severity_override and
   intent_description_override for paragraphs outside the table.
3. Compute the numeric margin with safety_margin(target, achieved) and
   margin_db(target, achieved) when the item is quantitative.
4. List the compensating measures for the item and run
   compensation_coverage(measures, paragraph, severity), which returns the
   0..1 coverage score, the accepted measure types and the gaps against the
   expected measure set.
5. Run elos_verdict(paragraph, severity, achieved_probability, measures,
   overrides...) to get the verdict dict with margin, margin_db, coverage,
   verdict and reasons.
6. Summarize the finding for the certification finding package with
   finding_summary(item, verdict).

## Worked example

A yaw damper channel cannot show literal compliance with 25.1309 at the
catastrophic failure condition. Severity catastrophic, achieved
probability 2e-10 per flight hour, compensating measures
redundant-lane-monitoring and flight-crew-procedure:

- Intent: 25.1309 is quantitative; the catastrophic target is 1e-9 per
  flight hour (intent_for target_prob 1e-9).
- Margin: safety_margin(1e-9, 2e-10) = 5.0, margin_db 6.99 dB. The
  achieved 2e-10 is five times better than the 1e-9 target.
- Coverage: expected 3 measures for a catastrophic quantitative item;
  redundancy accepted, flight crew procedure accepted (paired with
  redundancy), monitoring missing. Coverage 2/3 = 0.667.
- Verdict: CONDITIONAL, with the missing monitoring measure in the
  reasons list.
- Add failure-monitoring as a third measure: monitoring is now accepted
  (redundancy present), coverage 1.0, verdict PASS (finding recommended).
  Summary: "ELOS finding for paragraph 25.1309 at catastrophic severity:
  safety margin 5.0 (6.99 dB) against the probability target.
  compensating measure coverage 1.0. verdict PASS (finding recommended)."

Second case, same item with achieved probability 3e-9: margin 0.333 below
the 1.0 acceptance line, verdict FAIL with the margin reason regardless of
measures. Third case, qualitative 25.671 control system item at hazardous
severity with redundant-actuation and jam-detection-monitoring and no
numeric probability: expected 1 measure, redundancy accepted and
monitoring accepted with it, coverage 1.0, verdict PASS. Fourth case,
inputs that raise ValueError: severity very-bad, and achieved probability
0 for a quantitative item.

## Verification

- Confirm intent_for("25.1309", "catastrophic") returns quantitative with
  target_prob 1e-9 and that the hazardous and major severities key to 1e-7
  and 1e-5.
- Confirm safety_margin(1e-9, 2e-10) returns exactly 5.0 and margin_db
  returns 6.99 dB (10 * log10(5)).
- Confirm the compensation rules per measure type: monitoring rejected
  without redundancy, operating limitation rejected without a crew
  procedure, maintenance action without a restore-before-next-flight
  qualifier rejected, inspection interval rejected off fatigue and aging
  items.
- Confirm the verdict branches: coverage 0.667 with a monitoring gap is
  CONDITIONAL and reaches PASS once monitoring is added; margin 0.333 is
  FAIL; coverage below 0.5 is FAIL; a primary safety function gap blocks a
  qualitative PASS.
- Confirm every non-physical input raises ValueError: unknown severity,
  non-positive or non-finite achieved probability on a quantitative item,
  non-positive or non-finite margin inputs, and an unknown paragraph with
  no overrides.
- Run the contract test offline: python3
  scripts/test_equivalent_level_of_safety.py (34 tests, deterministic).

## Related leaves

- systems-engineering-safety/certification/certification-basis: the
  applicable regulations and certification path that frame the item.
- systems-engineering-safety/certification/means-of-compliance: the MOC
  that carries the ELOS finding evidence in the compliance matrix.
- avionics/far-cs25/special-conditions: the FAR 25.17 / CS 25.17 novel
  feature special condition route, which this leaf does not use.
- systems-engineering-safety/arp4761a/functional-hazard-assessment: the
  severity rating and probability target inputs for the item.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_equivalent_level_of_safety.py

The test covers the intent table lookups and the override path, margin
math and the dB conversion with the round-trip identity, measure type
classification precedence, the compensation acceptance rules per measure
type, the worked example anchors (margin 5.0 with coverage 2/3 CONDITIONAL
turning PASS when monitoring is added, the 3e-9 margin FAIL, the
qualitative 25.671 PASS), coverage capping, the primary safety function
gate, and ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: the intent table is a paraphrased
  summary at reference level of FAR-25 and CS-25 rule intent (25.1309,
  25.671, 25.683 and the CS-25 counterparts), with no verbatim rule text.
- compliance: STANDARDS-REF, gated: false.
