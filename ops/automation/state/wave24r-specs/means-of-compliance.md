# Wave-24R leaf spec: means-of-compliance (systems-engineering-safety)

- Path: skills/systems-engineering-safety/certification/means-of-compliance/
- Pack: certification (existing: certification-basis)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: systems-engineering-safety

## Claim

Means-of-compliance (MOC) selection and compliance-matrix building for
an airworthiness certification program: for each certification item
(applicable regulation paragraph), select the acceptable means of
compliance (MOC 1 engineering/analysis, MOC 2 ground test, MOC 3 flight
test, MOC 4 simulation/analysis tool, MOC 5 certification by similarity,
MOC 6 safety assessment; label the categories with the EASA/FAA-style
six-class scheme summarized at reference level), check the method is
acceptable for the item type and development assurance level, and score
the compliance matrix coverage. Produces the per-item MOC assignment,
the coverage score, and a certification-plan readiness verdict.

Does NOT do: determine the certification basis/regulations
(certification-basis leaf owns the applicable parts and special
conditions), scope the FAR-25 program end to end (avionics/far-cs25/
airworthiness owns program sequencing and the coarse four-way
analysis/test/inspection/similarity selection at the program level),
ARP4754A verification method assignment (verification-planning). This
leaf is the per-certification-item MOC matrix and coverage method.

## Method (implement exactly)

Input model: a list of certification items, each with:
- item_id (str), regulation_paragraph (str, e.g. "25.671"),
- item_kind (one of: structure, systems, powerplant, equipment,
  software, hardware, performance, handling),
- failure_severity (one of: none, minor, major, hazardous,
  catastrophic) or 'n/a',
- development_assurance_level (DAL A-E or n/a; optional).
MOC suitability table (module constant, deterministic; derived from the
public certification guidance summarized, not verbatim):
- structure: preferred MOC 1 (analysis) + MOC 2/3 (static/ground or
  flight test evidence) depending on novelty; similarity (MOC 5) only
  for minor changes.
- systems (electronic): MOC 1 + MOC 6 (safety assessment) for
  catastrophic/hazardous failures; MOC 4 simulation acceptable for
  DAL C-E.
- powerplant: MOC 2 (bench/ground test) + MOC 3 (flight test) typical;
  analysis MOC 1 supporting.
- equipment: MOC 2 environmental qualification (DO-160 style test) with
  MOC 1 analysis support.
- software: MOC 1 (lifecycle data per DO-178C) + MOC 4 (tool
  qualification where used); document that the software MOC is the
  DO-178C process assurance.
- hardware: MOC 1 + MOC 2 (DO-254 style verification).
- performance/handling: MOC 3 (flight test) with MOC 1 analysis and
  MOC 4 simulation.
Coverage and acceptance rules:
- Each item gets a primary MOC and optional supporting MOCs; the method
  returns recommended_mocs (list).
- A catastrophic item with systems kind requires MOC 6 in the set
  (safety assessment); if missing, the item is non-compliant.
- Novelty screening: an input flag novel (bool, default False) upgrades
  structure/system items to require a test MOC (2 or 3) in addition to
  analysis; similarity MOC 5 is rejected when novel = True.
- Matrix coverage score = (# items with at least one accepted MOC) /
  (# items) and completeness = all items have at least one primary MOC;
  report per-kind coverage too.
- Readiness verdict: PASS if coverage = 1.0 and no catastrophic item
  lacks MOC 6, else FAIL with reasons list.
Functions:
- moc_suitability(item_kind, severity, dal, novel) -> list of
  recommended MOC ids (ordered, primary first) or ValueError on an
  unknown kind/severity/dal.
- accept_item(item, recommended) -> (accepted_bool, reason)
- build_compliance_matrix(items) -> per-item rows + list of issues
- coverage_score(matrix) -> (overall, per_kind dict)
- compliance_verdict(matrix) -> (PASS/FAIL, reasons)
ValueError on: unknown item_kind/severity/DAL strings, empty item list,
non-finite... (strings only; no numeric inputs needed, keep the module
pure and deterministic).

## Worked example

Certification items (use in the SKILL body worked example):
1. {"item_id": "FCS-1", "regulation_paragraph": "25.671", "item_kind":
   "systems", "severity": "catastrophic", "dal": "A", "novel": true}
2. {"item_id": "STR-1", "regulation_paragraph": "25.307",
   "item_kind": "structure", "severity": "hazardous", "dal": "n/a",
   "novel": false}
3. {"item_id": "PP-1", "regulation_paragraph": "25.901",
   "item_kind": "powerplant", "severity": "major", "dal": "n/a",
   "novel": false}
Anchors (deterministic, assert exactly):
- FCS-1 recommended MOCs include 1 and 6 and at least one test MOC
  (novel systems at DAL A): assert "6" in the set and 2 or 3 present.
- STR-1 recommended: MOC 1 primary; with novel false and hazardous
  severity no MOC 6 requirement.
- PP-1 recommended: MOC 2 and/or 3 present.
- If FCS-1 were assigned only MOC 1 and 4, compliance_verdict returns
  FAIL with the MOC-6 reason; with the full set it returns PASS when all
  three items are covered.
- Coverage: 3/3 items -> overall 1.0.
- ValueError on item_kind "quantum" or severity "very-bad".
Test identities and ValueErrors as listed; keep at least 15 test
methods (suitability per kind, novelty upgrades, severity gating,
coverage math, verdict logic, error handling).

## Corpus tasks (2 tasks, ids w24r-means-of-compliance-1/2)

Distinctive tokens: means-of-compliance, moc-1, moc-2, moc-3, moc-6,
compliance-matrix, certification-item, coverage score, certification
plan. IMPORTANT: include the numbered MOC tokens (moc-1, moc-6) in the
queries and description - they are unique to this leaf. Do NOT use bare
"airworthiness", "type certificate", "certification basis", "special
conditions" as leading tokens (avionics/far-cs25 siblings + 
certification-basis own those).

1. "build the means-of-compliance matrix for my certification items:
   for each FAR-25 paragraph assign the acceptable MOC (moc-1 analysis,
   moc-2 ground test, moc-3 flight test, moc-6 safety assessment),
   require moc-6 for the catastrophic flight control system, and score
   the compliance matrix coverage"
2. "select the means of compliance for the novel primary structure item
   and the powerplant installation: run the moc suitability rules with
   the novelty screening and report the recommended moc set per
   certification item with the compliance verdict"

## SKILL body notes

Pair with certification-basis (the applicable paragraphs this leaf
assigns MOC for) and the program-level avionics airworthiness leaf.
Compliance: the MOC six-class scheme is summarized at reference level
from public certification guidance; no verbatim AMC text; standards
referenced not reproduced.
