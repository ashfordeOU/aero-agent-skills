# Wave-26 leaf spec: equivalent-level-of-safety (systems-engineering-safety, certification pack)

- Path: skills/systems-engineering-safety/certification/equivalent-level-of-safety/
- Pack: certification (existing siblings: certification-basis, means-of-compliance)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: systems-engineering-safety

## Claim

Develop an Equivalent Level of Safety (ELOS) finding for a civil
aircraft or system certification item whose design cannot show literal
compliance with an applicable airworthiness regulation paragraph: state
the regulation intent (its safety objective), quantify or qualify the
achieved level of the design, list the compensating measures that close
the gap, compute the quantitative margin when the rule carries a
numeric probability target (e.g. 25.1309 catastrophic 1e-9 per flight
hour), and return the ELOS verdict (finding recommended, conditional,
or not supportable) with the reasons list. Produces the per-item ELOS
assessment with margin, compensation coverage, and the finding
recommendation that gates the certification finding package.

Does NOT do: determine which regulations apply (certification-basis
owns the applicable parts and flags novel-feature special conditions),
select the means of compliance per item (means-of-compliance owns the
MOC classes), draft special conditions for a novel feature (avionics
far-cs25 special-conditions owns FAR 25.17 / CS 25.17 novelty
conditions), rate failure condition severity or set probability targets
(arp4761a functional-hazard-assessment owns severity to probability
target mapping). This leaf is the ELOS deviation-finding analysis for a
design that already has a regulation item and an achieved safety level.

## Model (implement exactly)

Regulation intent table (module constant INTENT_TABLE, deterministic,
paraphrased from public certification guidance, not verbatim):
- "25.1309": quantitative, catastrophic target 1e-9 per flight hour,
  hazardous 1e-7, major 1e-5 (targets keyed by the failure condition
  severity supplied as input, not re-derived here).
- "25.671": qualitative control system (control surface or system
  failure must not prevent continued safe flight and landing); intent
  severity hazardous.
- "23.1309" (normal category): quantitative, catastrophic 1e-9,
  hazardous 1e-7, major 1e-5 (same table shape).
- "25.683": qualitative, operation of the controls must not be
  adversely affected by deformation of the structure (intent severity
  hazardous).
- Any other paragraph id: qualitative, intent severity from input
  (default major) - the function accepts an explicit intent_severity
  and intent_description for paragraphs outside the table.
Inputs per item:
- regulation_paragraph (str), severity (catastrophic, hazardous, major,
  minor, none), achieved_probability (float per flight hour, or None
  for qualitative), compensating_measures (list of str, each a
  documented measure: redundancy, monitoring, operating limitation,
  flight crew procedure, maintenance action, inspection interval),
  intent_severity_override (optional str), intent_description_override
  (optional str), quantitative (bool flag, default auto from table).
Functions:
- intent_for(paragraph, severity) -> dict {quantitative, target_prob or
  intent_severity, intent_text} (ValueError on unknown paragraph only
  when no overrides supplied).
- safety_margin(target, achieved) -> ratio = target / achieved (float;
  ValueError when achieved <= 0 or target <= 0).
- margin_db(target, achieved) -> 10 * log10(ratio).
- compensation_coverage(measures, paragraph, severity) -> (score 0..1,
  accepted list, gaps list): each measure is checked against the module
  rule table MEASURE_RULES (redundancy accepted for quantitative
  catastrophic items, monitoring accepted only with redundancy or
  limitation, operating limitation accepted for qualitative items with
  crew procedure, maintenance action accepted only when it restores a
  degraded function before next flight, inspection interval accepted
  for fatigue/aging items only); coverage = weighted accepted count /
  total expected measures where expected = 1 for minor, 2 for major,
  2 for hazardous quantitative, 3 for catastrophic quantitative, 1 for
  hazardous qualitative, 2 for catastrophic qualitative (module
  constant EXPECTED_MEASURES by severity and quantitative flag).
- elos_verdict(paragraph, severity, achieved_probability, measures,
  overrides...) -> dict {margin, margin_db, coverage, verdict,
  reasons}: verdict PASS (finding recommended) when (quantitative:
  margin >= 1.0 and coverage >= 1.0) or (qualitative: coverage >= 1.0
  and no gap in the accepted list touches a primary safety function);
  CONDITIONAL when coverage < 1.0 but >= 0.5 (reasons list the missing
  measures); FAIL when margin < 1.0 or coverage < 0.5 or a catastrophic
  quantitative item has margin < 1.0 regardless of measures. Margin
  threshold 1.0 means the achieved probability is at or better than the
  target (documented as the typical ELOS acceptance line; the finding
  is always authority-approved in practice).
- finding_summary(item, verdict_dict) -> str one-paragraph summary
  with the paragraph, margin, coverage and verdict (used in the SKILL
  worked example).
ValueError on: unknown severity, achieved_probability <= 0 when
quantitative, negative measure list count is fine (empty list allowed,
coverage 0), non-finite margin inputs.

## Worked example

1. Paragraph "25.1309", severity catastrophic, achieved_probability
   2e-10, measures ["redundant-lane-monitoring", "flight-crew-procedure"]:
   margin 5.0, coverage: expected 3 measures for catastrophic
   quantitative; accepted: redundancy yes, crew procedure only when
   paired with redundancy (accepted), monitoring not present (gap) ->
   coverage 2/3 = 0.667, verdict CONDITIONAL with the monitoring gap in
   reasons. Add "failure-monitoring" measure -> coverage 1.0, verdict
   PASS.
2. Same paragraph, severity catastrophic, achieved_probability 3e-9:
   margin 0.333 < 1.0, verdict FAIL with the margin reason regardless of
   measures.
3. Paragraph "25.671" qualitative hazardous, no numeric probability,
   measures ["redundant-actuation", "jam-detection-monitoring"]:
   expected 1 measure for hazardous qualitative -> coverage 1.0 ->
   PASS.
4. ValueError on severity "very-bad" and on achieved_probability 0 for
   a quantitative item.
Keep at least 16 test methods (table lookups, margin math, margin_db,
compensation rules per measure type, coverage math, PASS/CONDITIONAL/
FAIL branches, override path, ValueErrors).

## Corpus tasks (ids w26-equivalent-level-of-safety-1/2)

Distinctive tokens: equivalent level of safety, ELOS finding,
deviation finding, regulation intent, compensating measure,
non-literal compliance, safety margin, 21.21. Avoid: certification
basis (sibling), means of compliance / moc-1 (sibling), special
condition / novel design feature (avionics far-cs25 special-conditions),
FHA severity rating (arp4761a).

1. "the yaw damper cannot show literal compliance with 25.1309 at the
   catastrophic failure condition, build the equivalent level of safety
   finding: state the regulation intent, compute the safety margin
   against the 1e-9 target with the achieved 2e-10 probability, and list
   the compensating measures that close the gap"
2. "run the ELOS deviation analysis for the qualitative 25.671 control
   system item with redundant actuation and jam detection monitoring:
   assess the compensation coverage and return the finding
   recommendation"

## SKILL body notes

Pair with certification-basis (the applicable paragraphs and path),
means-of-compliance (MOC of the finding evidence), and avionics
far-cs25 special-conditions (the novel-feature route this leaf is not).
Compliance: intent table is a paraphrased summary at reference level
(no verbatim rule text); standards referenced not reproduced.
