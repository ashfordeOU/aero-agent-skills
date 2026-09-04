# Wave-34 leaf spec: previously-developed-software (avionics, do178c pack)

- Path: skills/avionics/do178c/previously-developed-software/
- Pack: do178c. Closest siblings: configuration-management (baselines,
  problem reports, release of CURRENT data), planning (PSAC drafting),
  development / verification / software-testing (the DO-178C process
  leaves), tool-qualification (TQL criteria), do297 (IMA module-
  acceptance reuse is a DIFFERENT reuse context). Repo-wide grep: zero
  avionics hits for reuse/PDS/delta-objective tokens outside do297 and
  cFS table contexts.
- Standards id: do-178c (reference-only). Ledger Standard: do-178c.
- Family: avionics

## Claim

Scope the reuse credit of previously developed software (PDS) in a
DO-178C project: classify the reused item by origin standard, whether
it is modified, and whether its development assurance level meets the
target level (unchanged direct credit, modified PDS with delta
qualification over the changed scope plus affected interfaces, or
level-upgrade requiring additional verification at the higher level),
compute the delta objective coverage ratio against the required
objective set, and scope the regression for a modified item from its
changed code fraction and touched interfaces. Produces the reuse
classification, the credit path, the delta objective gap and verdict,
and the bounded-regression scope, the reuse-planning layer of a DO-178C
compliance argument.

Does NOT do: configuration baselines and problem reports of current
data (configuration-management); PSAC content and lifecycle planning
(planning); tool qualification criteria (tool-qualification); IMA
module-acceptance reuse per DO-297 (do297); ECSS heritage reuse
(space-systems/ecss).

## Model (implement exactly)

Conventions: classification inputs are user-declared facts about the
reused item (origin standard id string, modified flag, level-meets
flag). No RTCA objective-count tables are reproduced; the required and
covered objective counts are INPUTS to the coverage function.

Functions (pure stdlib):
- classify_pds(origin_standard, modified, level_meets) -> dict
  {reuse_class, credit_path}:
  - unchanged-direct-credit when modified is False and level_meets
    True (existing lifecycle data accepted, no delta objectives).
  - level-upgrade when level_meets is False (additional verification
    at the higher level required; treat as delta over the level gap).
  - modified-pds otherwise (delta qualification over the changed scope
    plus affected interfaces).
  ValueErrors on origin_standard empty/not a str.
- delta_objective_coverage(required_objectives, covered_objectives) ->
  dict {required, covered, delta_objectives, coverage_ratio, verdict}
  with coverage_ratio = covered / required (round 4 decimals),
  delta_objectives = required - covered, verdict =
  "delta-qualification-required" when covered < required else
  "full-coverage". ValueErrors: required <= 0, covered < 0, covered >
  required.
- modified_scope(changed_loc, total_loc, touched_interfaces,
  total_interfaces) -> dict {changed_fraction, interface_fraction,
  scope} with changed_fraction = changed/total (round 4), scope =
  "bounded-regression" when changed_fraction <= 0.2 AND
  interface_fraction <= 0.5 else "broad-regression". ValueErrors:
  changed < 0, total <= 0, changed > total, touched < 0, touched >
  total.
- pds_report(origin_standard, modified, level_meets,
  required_objectives, covered_objectives, changed_loc, total_loc,
  touched_interfaces, total_interfaces) -> dict combining all outputs.

Classification identity to test: (do-178c, False, True) -> unchanged-
direct-credit; (do-178c, True, True) -> modified-pds; (do-178c, False,
False) -> level-upgrade. Coverage verdict flips at covered == required.
Modified scope flips at the changed_fraction and interface thresholds.

## Worked example

Reference item: a previously certified autopilot module (DO-178C, DAL C
data) reused in a DAL C project: unmodified for case 1, modified (500
of 8000 LOC changed, 2 of 12 interfaces touched) for case 2, and
level-upgraded (DAL C data reused at DAL B) for case 3. Required
objectives 24 with 19 covered in the delta case.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- classify_pds('do-178c', False, True) -> reuse_class
  unchanged-direct-credit; credit_path says no delta objectives.
- classify_pds('do-178c', True, True) -> modified-pds; credit_path
  says delta qualification over the changed scope plus affected
  interfaces.
- classify_pds('do-178c', False, False) -> level-upgrade; credit_path
  says additional verification at the higher level required.
- delta_objective_coverage(24, 19): coverage_ratio = 0.7917, delta =
  5, verdict delta-qualification-required.
- modified_scope(500, 8000, 2, 12): changed_fraction = 0.0625, scope
  bounded-regression.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty/non-str origin_standard; required <= 0; covered <
  0 or > required; changed < 0; total <= 0; changed > total; touched
  < 0 or > total.
- Classification: the three worked cases return the exact classes and
  credit paths above; modified False + level False returns
  level-upgrade (not modified-pds); modified True + level False also
  level-upgrade.
- Coverage: (24, 19) ratio 0.7917 delta 5 verdict required; (24, 24)
  ratio 1.0 verdict full-coverage; doubling both inputs keeps the
  ratio.
- Modified scope: (500, 8000, 2, 12) -> 0.0625 bounded-regression; a
  30% change (2400/8000) with 2 interfaces -> broad-regression;
  changed_fraction rounds to 4 decimals.
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-previously-developed-software.yaml)

Query 1 (copy verbatim):
  "classify previously developed software reuse credit in a DO-178C project as unchanged direct credit, modified PDS or level upgrade from the modification and assurance level facts"
  intent: "avionics; DO-178C previously developed software reuse classification"
  expected_skill: "avionics/do178c/previously-developed-software"
Query 2 (copy verbatim):
  "compute the delta objective coverage ratio and the bounded regression scope of a modified reused software item for qualification"
  intent: "avionics; PDS delta objective coverage and modified software regression scope"
  expected_skill: "avionics/do178c/previously-developed-software"
Task ids: w34-previously-developed-software-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must scope the reuse credit of
previously developed software in a DO-178C project:" and include the
outputs in the Claim. First tag: previously-developed-software.
Additional tags ONLY: pds-qualification, software-reuse-credit,
delta-objective-analysis, modified-software-scope, reuse-
classification. NEVER single generic words (software, reuse, credit,
qualification, objective, delta). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): baseline, problem report,
configuration, release (configuration-management); PSAC, plan,
lifecycle (planning); tool qualification, TQL (tool-qualification);
IMA, module acceptance (do297); heritage (space-systems/ecss). The
words "previously developed software", "reuse credit", "delta
objective", "modified software scope" are this leaf's own.

Tags: [previously-developed-software, pds-qualification,
software-reuse-credit, delta-objective-analysis,
modified-software-scope, reuse-classification]

Sibling-citation lines for Related leaves:
avionics/do178c/configuration-management (baseline sibling; boundary:
current-data baselines vs reuse classification),
avionics/do178c/planning (PSAC planning sibling),
avionics/do178c/verification and software-testing (the delta
verification this leaf scopes).

Ledger Standard: do-178c.
