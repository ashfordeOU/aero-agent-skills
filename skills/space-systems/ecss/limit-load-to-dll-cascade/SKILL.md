---
name: limit-load-to-dll-cascade
description: "Use when derive limit loads (LL) and design limit loads (DLL) for a spacecraft structure per ECSS-E-ST-32C clauses 4.2.7–4.2.8: identify every structural level in the load hierarchy, apply a load uncertainty factor (LUF ≥ 1.0) to each LL to obtain the corresponding DLL, and propagate the resulting loads recursively from system level down through sub-assemblies to component level via structural transfer factors. Combine multi-axis load components with the applicable rule (SRSS or absolute sum), flag any LUF below unity, and confirm every structural level in the cascade carries a documented DLL before margins of safety are computed. Trigger: ecss, e-st-32-structures-scope, limit-load, design-limit-load, load-cascade, luf, structural-hierarchy, dll."
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
  tags: [ecss, e-st-32-structures-scope, limit-load, design-limit-load, load-cascade, luf, structural-hierarchy, dll]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Limit Load to DLL Cascade (space-systems/ecss/limit-load-to-dll-cascade)

Use when the task is to derive Design Limit Loads (DLL) from Limit Loads (LL) and
propagate them level by level through a spacecraft structural hierarchy, per
ECSS-E-ST-32C clauses 4.2.7–4.2.8.

## Domain quick reference

- **Limit Load (LL)**: the maximum load a structural element is expected to
  experience during its entire service life, accounting for all mission phases
  (launch, transfer, on-orbit manoeuvres, landing). LL is expressed per axis
  and per structural level. Clause 4.2.7 requires every element in the load
  path to carry a documented LL before any analysis proceeds.
- **Design Limit Load (DLL)**: LL multiplied by the Load Uncertainty Factor
  (LUF). DLL = LL × LUF. The LUF, defined in clause 4.2.8, shall be ≥ 1.0;
  values below unity are non-conforming and must be flagged. The LUF accounts
  for uncertainties in load derivation, mathematical model fidelity, and test
  data scatter.
- **Cascade rule**: loads propagate recursively from the highest structural
  level (e.g. spacecraft system) downward. The LL reaching a child level is the
  parent-level LL multiplied by a structural transfer factor that captures the
  local dynamic response or load redistribution. The child's DLL is then
  computed from its own LL and its own LUF. Each level forms an independent
  DLL calculation; the cascade is the sequential application of this rule from
  root to leaf.
- **Load combination**: when more than one independent load component acts
  simultaneously, they are combined before the LUF is applied. The two accepted
  rules are SRSS (square-root-sum-of-squares, for statistically independent
  random components) and absolute sum (ABS, for deterministic or correlated
  components); the choice must be justified.

## Workflow

1. Identify the root structural level and its LL values per axis. Confirm that
   the LL was derived from the worst-case mission-phase load envelope.
2. Determine the LUF for the root level. Verify LUF ≥ 1.0. Compute
   DLL = LL × LUF for every load component at the root level.
3. For each child structural level: obtain or derive the structural transfer
   factor that maps the parent LL to the child LL. Transfer factors > 1.0
   represent dynamic amplification; < 1.0 represent attenuation; = 1.0 means
   the parent LL is passed through unchanged.
4. Compute the child LL = parent LL × transfer factor. Then compute
   child DLL = child LL × child LUF. Record both LL and DLL at every level.
5. If multiple independent load axes must be combined at a level, apply SRSS or
   ABS according to the load model justification before multiplying by LUF.
6. Repeat steps 3–5 recursively until every leaf-level component has a
   documented LL and DLL.
7. Verify completeness: every node in the structural hierarchy must carry a DLL
   entry; a missing DLL at any node is a non-conformance.

## Pitfalls

- Applying the LUF at only one level and reading lower-level DLL values as
  DLL = LL — each level must carry its own LUF application.
- Using LUF < 1.0 as a "relief factor" — the LUF is a safety margin, not an
  attenuation. LUF < 1.0 violates clause 4.2.8 and is a non-conformance.
- Conflating LL and DLL when comparing against allowables — allowables are
  checked against DLL (and further against Ultimate Load = DLL × factor of
  safety), never against LL alone.
- Choosing SRSS combination for correlated load components — SRSS is valid only
  for statistically independent random components; correlated components must be
  combined by absolute sum.
- Propagating DLL (instead of LL) through the transfer factor — the cascade
  input to each child is the parent LL; the LUF is applied separately at the
  child level, not inherited from the parent.

## Behavior contract (gate 3)

The DLL computation, LUF validation, transfer-factor cascade, and load-combination
logic are exercised by the gate 3 contract test:
scripts/test_limit_load_to_dll_cascade.py against
scripts/limit_load_to_dll_cascade_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_limit_load_to_dll_cascade.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
