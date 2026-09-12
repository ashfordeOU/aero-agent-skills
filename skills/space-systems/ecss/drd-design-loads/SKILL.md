---
name: drd-design-loads
description: "Use when determine design loads for a space structure under ECSS-E-ST-32C Annex B: enumerate all load cases by type (static, quasi-static, dynamic-sine, dynamic-random, dynamic-shock, thermal, acoustic, pressure, inertia, combined), assign a Limit Load to each, apply partial safety factors to derive Design Limit Loads (DLL), compute Design Yield Loads (DYL = DLL × yield factor), and compute Design Ultimate Loads (DUL = DLL × ultimate factor). Flag any load case with a missing limit load, a safety factor outside the accepted range, or a load type not in the ECSS load taxonomy. Trigger: ecss, e-st-32-structures-scope, design-loads, limit-load, dll, dyl, dul, load-cases, drd, safety-factor."
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
  tags: [ecss, e-st-32-structures-scope, design-loads, limit-load, dll, dyl, dul, load-cases, drd, safety-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Design Loads Document (space-systems/ecss/drd-design-loads)

Use when the task is to determine the design loads for a space structure
per ECSS-E-ST-32C Annex B -- enumerating load cases by type, assigning
Limit Loads, and deriving the Design Limit Load (DLL), Design Yield Load
(DYL), and Design Ultimate Load (DUL) for each case.

## Domain quick reference

- A **Limit Load (LL)** is the maximum load expected during the service
  life of the structure, including all relevant load sources and
  combinations. It is the starting point for every derived design load.
- The **Design Limit Load (DLL)** is LL multiplied by a partial safety
  factor that accounts for load-definition uncertainty. For nominal cases
  this factor is 1.0 (DLL = LL), but it rises when load data scatter or
  model uncertainty is significant.
- The **Design Yield Load (DYL)** is DLL multiplied by a yield factor
  (default 1.0 for metallic structures). At DYL the structure may not
  exhibit permanent deformation beyond the allowable yield criterion.
- The **Design Ultimate Load (DUL)** is DLL multiplied by an ultimate
  factor (default 1.25 for metallic structures). At DUL the structure
  must not fracture or collapse.
- ECSS-E-ST-32C Annex B recognizes ten load-case types: static,
  quasi-static, dynamic-sine, dynamic-random, dynamic-shock, thermal,
  acoustic, pressure, inertia, and combined. Every load case in the
  DRD-DL must be categorized into exactly one of these types before its
  derived loads are computed. An unrecognized type is a finding, not a
  default.

## Workflow

1. Inventory every load source acting on the structure (launch
   quasi-static loads, sine and random vibration, shock events, steady
   manoeuvre accelerations, thermal gradients, acoustic environment,
   pressurization, combined multi-axis events) and assign each a unique
   load case identifier.
2. Categorize each load case into one of the ten recognized ECSS types.
   Reject any entry whose type string is not in the accepted taxonomy
   before proceeding to load computation; leave a clear finding that the
   type must be reconciled with the project loads specification.
3. Assign a Limit Load value to each case. The LL is derived from the
   loads analysis or test data for that load source; a load case without
   an LL value is incomplete and must be flagged as a finding before
   the DRD-DL can be accepted.
4. Compute the DLL for each case: DLL = LL × partial_safety_factor.
   Validate that the partial safety factor lies within the accepted
   range before applying it; a factor below the minimum or above the
   maximum is itself a finding.
5. Compute the DYL for each case: DYL = DLL × yield_factor. Use the
   project-agreed yield factor (default 1.0 for standard metallic); flag
   any factor outside the accepted range.
6. Compute the DUL for each case: DUL = DLL × ultimate_factor. Use the
   project-agreed ultimate factor (default 1.25 for standard metallic);
   flag any factor outside the accepted range.
7. Check for duplicate load case identifiers across the full document;
   a duplicate ID makes the document ambiguous and is a document-level
   finding.
8. Aggregate all per-case and document-level findings. The DRD-DL is
   not accepted until every finding is resolved.

## Pitfalls

- Applying the ultimate factor directly to LL instead of to DLL --
  the correct chain is LL → DLL (× partial safety factor) → DUL
  (× ultimate factor). Skipping the intermediate DLL step and writing
  DUL = LL × ultimate_factor discards the partial safety factor and
  under-reports the required design load when that factor exceeds 1.0.
- Treating an unknown load type as "static" by default -- an
  unrecognized type means the load source has not been mapped to the
  ECSS taxonomy and may require a combined or dynamic treatment that a
  static model does not cover. Default substitution suppresses a real
  gap in the loads analysis.
- Accepting a DYL equal to DLL (yield factor 1.0) as a conservative
  assumption for composite structures -- the ECSS-E-ST-32C yield factor
  for composites is not 1.0; applying a metallic default to a composite
  element produces a non-conservative yield check.
- Leaving the LL field blank and computing DLL as zero -- a missing LL
  is ambiguous; it may mean the load has not yet been determined rather
  than that it is genuinely zero, which are fundamentally different
  situations. The logic module treats a missing LL as a finding, not
  as a zero load.
- Carrying duplicate load case IDs into the DRD-DL -- if two cases
  share an ID, it is impossible to trace a margin-of-safety result back
  to the correct load definition unambiguously.

## Behavior contract (gate 3)

The load-type taxonomy, DLL/DYL/DUL computation chain, safety-factor
bounds validation, missing-field detection, and duplicate-ID check are
exercised by the gate 3 contract test:
scripts/test_drd_design_loads.py against
scripts/drd_design_loads_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_drd_design_loads.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
