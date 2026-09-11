---
name: e1009-chain-analysis
description: "Use when verify end-to-end coordinate system transformation chains
  across all frame users in a spacecraft project, following ECSS-E-ST-10C §5.2.3.
  Inventory every coordinate system in the project, register each inter-frame
  transformation link, and trace the chain from each user frame back to a common
  root frame. Flag any user frame that cannot reach the root, detect circular
  dependencies in the directed transformation graph, and check handedness
  consistency along each resolved chain. A project is chain-compliant only when
  all users are reachable, no cycles exist, and all frames in every chain share
  the same handedness convention. Trigger: ecss, e-st-10-system-scope,
  coordinate-systems, transformation-chain, reference-frames, chain-analysis,
  frame-consistency, handedness, e-st-10c."
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
  tags: [ecss, e-st-10-system-scope, coordinate-systems, transformation-chain, reference-frames, chain-analysis, frame-consistency, handedness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Coordinate System Chain Analysis (space-systems/ecss/e1009-chain-analysis)

Use when the task is the coordinate system chain analysis of ECSS-E-ST-10C
§5.2.3 — verifying that every frame user in the project can trace an
unbroken, consistent transformation chain back to the common root inertial
frame, and that the directed graph of inter-frame transformations contains
no circular dependencies and no handedness inconsistencies.

## Domain quick reference

- A coordinate system (CS) in a spacecraft project belongs to one of the
  following types: inertial (mission-level root), body (vehicle structural),
  sensor, structural (appendage or component), orbital, or ground. Every CS
  carries a handedness convention (right-handed or left-handed) that must be
  documented at definition time and remain consistent throughout its chain.
- A transformation link connects a source CS to a target CS via one of three
  transformation types: rotation only, translation only, or rigid-body
  (rotation + translation). A bidirectional link can be traversed in either
  direction; a unidirectional link can only be traversed from source to target.
- A chain is the ordered sequence of CS nodes connected by transformation links
  from a user frame to the root inertial frame. §5.2.3 requires that every
  frame user — any subsystem, instrument, or algorithm that references a CS
  other than the root — can resolve a complete, unambiguous chain. A user frame
  with a broken chain (at least one missing link between it and the root) is
  non-compliant and must be flagged as a gap, not silently ignored.
- Circular dependencies arise when a directed transformation path returns to a
  node already on the path. A cycle does not prevent a user from reaching a
  root if an acyclic path also exists, but the cycle itself is a structural
  defect that must be reported separately and resolved before the chain analysis
  is considered complete.
- Handedness consistency is a chain-level property: if the root frame is
  right-handed, every frame in the chain should also be right-handed; a
  left-handed frame in an otherwise right-handed chain introduces an implicit
  parity flip that must be explicitly documented. If not documented, the
  mismatch is flagged.

## Workflow

1. Inventory all coordinate systems in the project and register each one with
   its type (inertial, body, sensor, structural, orbital, ground) and
   handedness (right or left). Reject any CS whose type or handedness is not
   from the known sets before it enters the analysis.
2. Register every inter-frame transformation link: source CS name, target CS
   name, transformation type (rotation, translation, rigid_body), and whether
   the link is bidirectional. Reject any link whose source or target has not
   yet been registered, and reject self-loop links (source equals target) as
   structurally invalid.
3. For each user frame (every CS other than the root, or an explicitly supplied
   list of users), find the shortest transformation chain to the root by
   breadth-first search over the link graph. Record the ordered sequence of CS
   names that forms the chain. If no path exists, record the user as missing
   and flag it.
4. Detect circular dependencies by depth-first search over the directed link
   graph (unidirectional edges only; bidirectional links do not form directed
   cycles by themselves). Report each distinct cycle as an ordered list of CS
   names.
5. For each user whose chain was resolved in step 3, check handedness
   consistency: collect the handedness of every CS in the chain and flag any
   CS whose handedness differs from the root's convention.
6. Produce a consolidated compliance report: a project is chain-compliant only
   when every user has a resolved chain (no missing), no cycles exist, and
   every chain is handedness-consistent. A project that is incomplete in any
   one dimension is non-compliant overall.

## Pitfalls

- Treating a missing chain as a pass because no violation was explicitly raised —
  an unresolved chain is itself the finding. The absence of a path from a user
  frame to the root means the user's measurements and algorithms are not
  traceable to the mission reference, which is a compliance gap, not a neutral
  result.
- Conflating bidirectional link traversal with absence of directed cycles — a
  bidirectional link {A ↔ B} does not create a directed cycle (A→B→A is a
  directed cycle only if both the A→B and B→A directed edges are present). The
  cycle check must operate on the directed graph, not the undirected one used
  for chain finding.
- Skipping handedness consistency and reading the chain as compliant — a
  handedness mismatch is not a numerical error; it changes the sign convention
  of every coordinate that passes through the affected link. It must be flagged
  whether or not the numeric transformation appears valid.
- Applying the completeness check only to frames the engineer happens to list,
  omitting recently added sensor or appendage frames — §5.2.3 requires coverage
  of all frame users, not a curated subset.

## Behavior contract (gate 3)

The CS registration, transformation linking, chain-finding, completeness
verification, cycle detection, and handedness consistency logic is exercised
by the gate 3 contract test: scripts/test_e1009_chain_analysis.py against
scripts/e1009_chain_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1009_chain_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
