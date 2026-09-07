# Wave-46 systems-engineering-safety probe receipt (task-1, HEAD d4b4d590)

## Verdict: NO_CANDIDATES (0 GO), saturated reaffirmed FRESH

Whole-family probe re-run at HEAD d4b4d590 (wave-46 brief commit, verified
`git rev-parse HEAD` before and after all reads). Read-only probe: no git
add/commit/push, no edits to skills/, eval/, docs/, Makefile, scripts/,
ops/automation briefs, or standards-map.yaml. One write only: this receipt.
Wave-45 NO_CANDIDATES outcome re-verified from scratch with fresh greps and
sibling fence reads, not assumed. No candidate met the GO bar (clean
determinism with real published anchor, zero owner, standards-map id exists,
non-stealing Hit@1 queries).

## Family census (47 leaves, 7 packs, router parity, corpus parity)

- arp4754a 8: configuration-management, derived-requirements,
  development-assurance-levels, requirements-allocation,
  requirements-traceability, systems-planning, validation,
  verification-planning.
- arp4761a 22: beta-factor-analysis, common-cause-analysis,
  event-tree-analysis, failure-mode-criticality, failure-rate-estimation,
  fault-tree-importance-measures, fault-tree-quantification,
  fault-tree-uncertainty-analysis, fmes-coverage-analysis, fta-fmea,
  functional-hazard-assessment, maintainability-prediction,
  markov-analysis, operating-support-hazard-analysis,
  particular-risk-analysis, preliminary-system-safety-assessment,
  reliability-allocation, reliability-block-diagram,
  reliability-growth-analysis, safety-assessment, ssa-closure,
  zonal-safety-analysis.
- certification 4: certification-basis, equivalent-level-of-safety,
  means-of-compliance, mmel-development.
- continued-airworthiness 5: airworthiness-directive-compliance,
  ica-cmr-ali-classification, in-service-safety-assessment,
  msg3-maintenance-analysis, type-certificate-data-sheet.
- mbse 6: n2-diagram, requirements-modeling, state-machine,
  sysml-modeling, systems-engineering, trade-study-analysis.
- requirements 1: requirements-elicitation.
- safety-case 1: goal-structuring-notation.

Counts verified with `find skills/systems-engineering-safety -mindepth 2
-name SKILL.md` = 47. Corpus parity re-verified with probe helper
/tmp/w46_ses_census.py against eval/hit1-corpus.yaml: 1266 expected_skill
entries total, 96 systems-engineering-safety mentions, 47 distinct leaf
targets, disk leaves 47, 0 orphans, 0 unserved leaves (every corpus target
resolves to a disk leaf and every leaf carries corpus demand). Router
skills/systems-engineering-safety/SKILL.md table carries all 47 sub-skill
rows. standards-map.yaml holds 30 ids (`grep '^  - id:'` = 30); all leaf
frontmatter standards entries resolve (arp4754a, arp4761a, far-25, cs-25,
msg-3 present).

## All six ARP4761A process functions: PRESENT (re-verified on disk)

functional-hazard-assessment, preliminary-system-safety-assessment,
ssa-closure (SSA), zonal-safety-analysis, particular-risk-analysis and
operating-support-hazard-analysis each verified with a logic script and a
contract test under their scripts/ dir:
functional_hazard_assessment_logic.py, preliminary_system_safety_assessment_logic.py,
ssa_closure_logic.py, zonal_safety_analysis_logic.py,
particular_risk_analysis_logic.py, operating_support_hazard_analysis_logic.py
plus test_* peers. The broader quantitative set is equally present with
logic scripts: reliability-allocation, maintainability-prediction,
event-tree-analysis, fault-tree-importance-measures,
fault-tree-uncertainty-analysis, reliability-growth-analysis,
fmes-coverage-analysis, failure-mode-criticality, markov-analysis,
reliability-block-diagram, failure-rate-estimation, fta-fmea,
beta-factor-analysis, common-cause-analysis. No process step of the
ARP4761A FHA/PSSA/SSA/CCA flow is unowned.

## GO candidates: none. Declines (near-misses, each with fresh evidence)

| Candidate seam | Zero-owner grep result | Decline reason |
|---|---|---|
| HAZOP / PHA / HAZID hazard identification | `grep -rniw 'hazop'` and `'hazid'` over skills/: 0 real hits | No ARP4761A process slot; ARP4761A is function-based and functional-hazard-assessment owns failure-condition identification (fence: "derive the A-FHA and S-FHA failure conditions from each aircraft or system function"); HAZOP is a guideword brainstorming method, not closed-form; no corpus demand |
| STPA / system-theoretic analysis | `grep -rniw 'stpa'` over skills/: 0 real hits (earlier substring greps matched only test class names such as TestPatchThickness, not content) | Not an ARP4761A process; no standards-map id; no corpus demand; qualitative method with no deterministic anchor |
| Sneak circuit / sneak path analysis | `grep -rniw 'sneak'` over skills/: 0 hits | Proprietary methodology, no standards-map id, no corpus demand, no published closed-form anchor |
| Fault tree synthesis / automated tree construction | fault-tree-synthesis / construction / automated terms: 0 hits in skills/ | fta-fmea owns minimal cut-set extraction from AND/OR gates (fence: "compute minimal cut sets from AND/OR gate structures"); synthesis is qualitative modeling; no corpus demand; no published deterministic anchor |
| FMEA worksheet / failure-mode catalogue generation | fmes-coverage-analysis fence: "map every FMEA row to the failure condition it demonstrates through its condition_id ... report the coverage ratio" | FMEA-row to FHA-condition mapping and orphan-row flagging owned by fmes-coverage-analysis; per-item failure-mode libraries are knowledge tables (fabrication risk), no closed-form anchor |
| reliability-prediction parts count | `reliability-prediction` hits in skills/: 0 (only ops/ wave briefs name the closed seam); MIL-HDBK-217 / 217F / 217Plus / Telcordia / SR-332: 0 hits in skills/ and standards-map.yaml (30 ids, none of them) | CLOSED vein, not reopened: no MIL-HDBK-217 or Telcordia/SR-332 id in standards-map.yaml, so the gate-1 standards-resolution bar cannot be met. Sole near hit is mmpsd-allowables citing MIL-HDBK-5 heritage for material allowables, unrelated to parts-count reliability |
| Dispatch reliability / MEL relief probability math | whole-tree `grep -rniw 'dispatch'` hits are numerics dispatch (fast-fourier-transform, rank-based-hypothesis-testing), fsw software dispatch (deadline-monotonic-scheduling, fprime-component) | mmel-development owns dispatch relief: fence "screen each candidate equipment item for dispatch relief with the item inoperative ... assign the operator repair interval category (A, B, C, or D)"; inputs (gate times, deferral policies, O/M procedures) have no published closed-form anchor; no corpus demand |
| Common mode analysis content leaf | common-cause-analysis fence: "check that the analysis set covers zonal, particular risk, and common mode analysis"; tags include common-mode-analysis | CCA set-completeness check (ZSA/PRA/CMA) owned by common-cause-analysis; separate CMA content leaf has no corpus demand and no deterministic algorithm beyond what CCA scoping covers |
| MTBF / availability / repairable-system math | MTBF owned by failure-rate-estimation (mtbf_estimate, mtbf_lower_bound in logic and tests); availability owned by markov-analysis (fence: "two-state failure and repair availability with steady state limits ... steady state unavailability is lam/(lam+mu)") and reliability-block-diagram (fence: "system mission reliability R(t) = exp(-lambda t) ... exact block and system MTBF") | Fully owned across three quantitative siblings; a new availability leaf would sit inside sibling fences; no corpus task routes to such a leaf today |
| Weibull lifetime fitting seam | Weibull fit owned by cross-cutting/numerics/probability-distributions (logic: "Fit the normal, lognormal, exponential, and Weibull distributions"; WEIBULL_K_MIN/MAX/TOL constants) | Sibling fence, cross-family owner; reliability-growth-analysis additionally owns the aerospace Duane / Crow-AMSAA growth form (fence: "fit the Crow-AMSAA power-law process shape beta by deterministic MLE bisection"); no seam |
| Binomial success-run / pass-fail reliability demonstration | exact-binomial-test (cross-cutting/numerics) and acceptance-sampling, variables-acceptance-sampling (manufacturing-quality/as9100) own the binomial math | Sibling-fence owned cross-family; failure-rate-estimation owns the aerospace Poisson/chi-square demonstration form with corpus demand (fence: "apply the zero-failure rule (1.609 million test-hours demonstrate a 1e-6 per hour rate at 80 percent confidence)") |
| Severity-to-probability target lookup | `grep -rli 'extremely improbable'` over skills/ SKILL.md files: single owner functional-hazard-assessment | Fully owned by functional-hazard-assessment (targets: "extremely improbable below 1e-9/flight-hour, extremely remote below 1e-7, remote below 1e-5") and ssa-closure for closure lookup; no duplicate seam |
| Zonal hazard checklist item logic | checklist coverage owned by zonal-safety-analysis (logic + contract test present) | Fully owned; leaf contract test exercises the coverage math |
| Generic risk matrix (severity x likelihood index) | Three distinct domain-context matrix owners: operating-support-hazard-analysis (SES), flight-test-operations/planning/flight-test-safety (fence: "score the hazards on the severity by likelihood risk matrix"), manufacturing-quality/as9100/risk-management | A fourth generic leaf would overlap all sibling fences; no corpus demand; each matrix owner is context-specific by design |
| Certification planning / issue paper / special-condition seams | certification plan and program sequencing owned by avionics/far-cs25/airworthiness (logic: "Ordered steps of a transport-category type certification program") and avionics/do178c/airworthiness-liaison (fence: "liaison through the certification plan, issue papers, and open-item"); issue paper hits only in airworthiness-liaison | SES certification-basis owns certification path and special-condition flags (fence: "identify special conditions when the design has a novel or unusual feature ... select the certification path (type certificate, amended TC, supplemental type certificate, TSO authorization)"); equivalent-level-of-safety owns deviation findings; avionics siblings own program sequencing and issue papers; no unowned certification planning artifact |
| SysML sequence/activity diagram behavioral semantics | sysml-modeling fence: "select the right SysML diagram kind for each modeling purpose (block definition BDD, internal block IBD, parametric, requirement, activity, sequence, state machine, use case)" | sysml-modeling owns diagram-kind selection; behavioral execution is proprietary SysML semantics, no OMG SysML id in standards-map (30 ids confirmed absent); zero corpus demand |

## Cross-family fence checks (safety-assessment vs hazard analysis, certification)

- safety-assessment (arp4761a) owns the assessment-process spine: fence
  "classify failure-condition severity, run the FHA/PSSA/SSA sequence at
  the right design maturity, and scope the analysis set (FTA, FMEA, CCA)".
  No other family leaf owns the civil-aircraft safety assessment process;
  flight-test-operations/planning/flight-test-safety is a flight-test
  hazard/risk-matrix scorer for test ops, a different domain context, and
  25.1309 content sits with functional-hazard-assessment,
  certification-basis and equivalent-level-of-safety inside this family
  plus avionics/far-cs25/airworthiness for program scoping. No fence gap.
- Certification planning: arp4754a/systems-planning owns the development
  and certification plan artifact side of the ARP4754A flow; the
  certification pack (certification-basis, means-of-compliance,
  equivalent-level-of-safety, mmel-development) owns regulatory path,
  findings, deviations and MMEL; avionics owns program sequencing and
  liaison artifacts. No unowned certification seam with a deterministic
  anchor.
- Reliability/maintainability across families: maintainability and MTTR
  surface only in maintainability-prediction (this family),
  reliability-allocation, life-cycle-cost (vehicle-design cost context)
  and the family router; no orphan maintainability math. k-out-of-n
  redundancy math is owned by reliability-block-diagram, markov-analysis
  and beta-factor-analysis inside this family plus exact-binomial-test in
  cross-cutting; no seam.

## Closed veins (stayed closed, not reopened)

- reliability-prediction-parts-count: CLOSED as directed. Evidence: no
  MIL-HDBK-217 / Telcordia / SR-332 id in standards-map.yaml (30 ids
  grepped), 0 hits for those tokens in skills/, no leaf of that name on
  disk or in corpus.
- Generic hazard-method additions (HAZOP/PHA/HAZID/STPA): no ARP4761A
  slot, no standards-map id, no corpus demand. ARP4761A function coverage
  is complete (six process functions verified with logic scripts).
- Probability/statistics seams shared with other families (binomial,
  acceptance sampling, Weibull fitting, risk matrix): owned by
  cross-cutting, manufacturing-quality, or flight-test-operations
  siblings.
- SysML model-kind extensions: blocked on standards-map (no OMG id).
- Certification artifact seams (issue paper, certification program
  sequencing, special condition substance): owned by avionics leaves;
  certification-basis and equivalent-level-of-safety own path, special
  condition flags and deviation findings for this family.

## Evidence notes (fresh at HEAD d4b4d590)

- 637 SKILL.md tracked repo-wide (625 leaves + 12 routers per wave-46
  baseline); SES family 47 leaves, packs as listed; corpus 1266
  expected_skill entries with 96 SES mentions across 47 distinct targets,
  0 orphans, 0 unserved (helper /tmp/w46_ses_census.py).
- All six ARP4761A process-function leaf directories verified on disk with
  logic scripts and contract tests present.
- Zero-owner greps run across skills/ (excluding __pycache__) for every
  decline row above; grep output quoted per row; word-boundary greps used
  where substring false positives (test class names) appeared.
- Read-only maintained: `git status --porcelain` shows only the untracked
  ops/automation/state/wave46-* kit files placed by the wave runner
  (wave46-builder-kit.md, wave46-close-runbook.md, wave46-merge-corpus.py,
  wave46-sim-merge.py) and this receipt directory. No commits, no edits to
  skills/, eval/, docs/, scripts/, Makefile, briefs or standards-map.yaml.
