---
name: e1011-ops-nomenclature
description: "Use when validate operations nomenclature consistency across a mission operations document or interface control document per ECSS-E-ST-10-11C §4.3.3: confirm each crew role label belongs to the canonical set (Commander, Pilot, Mission Specialist, Payload Specialist, Flight Engineer, Ground Controller, Flight Director), confirm each mission phase term matches the standard vocabulary (launch, ascent, orbit insertion, on-orbit operations, rendezvous, docking, de-orbit, reentry, landing, recovery), confirm command type labels match the authorized taxonomy, and detect synonym conflicts where a single operational concept is referred to by multiple non-equivalent terms within the same document. Flag abbreviations, non-standard synonyms, and unrecognized terms for correction to canonical form before baselining. Trigger: ecss, e-st-10-system-scope, ops-nomenclature, crew-roles, mission-phases, command-types, operational-terminology, nomenclature-consistency."
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
  tags: [ecss, e-st-10-system-scope, ops-nomenclature, crew-roles, mission-phases, command-types, operational-terminology, nomenclature-consistency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Operations Nomenclature Consistency (space-systems/ecss/e1011-ops-nomenclature)

Use when the task is applying operations nomenclature consistently across
a mission document per ECSS-E-ST-10-11C §4.3.3 — validating crew role
labels, mission phase terms, and command type designations against the
canonical vocabulary, and detecting synonym conflicts where a single
concept appears under multiple non-equivalent labels.

## Domain quick reference

- §4.3.3 requires that every person, role, phase, and command type
  referenced in operations documentation uses the established term from
  the agreed operations vocabulary. Introducing an ad-hoc label or
  local abbreviation for a concept that already has a canonical term
  creates ambiguity during real-time operations and violates the
  consistency requirement.
- Crew roles have a fixed canonical set: Commander, Pilot, Mission
  Specialist, Payload Specialist, Flight Engineer, Science Officer,
  Ground Controller, Flight Director, CAPCOM, Systems Engineer, Flight
  Surgeon. An abbreviation such as CDR (for Commander) or FE (for
  Flight Engineer) is non-standard unless the document's own glossary
  has formally equated it to the canonical form at first use.
- Mission phase terms are drawn from a standard vocabulary: launch,
  ascent, orbit insertion, on-orbit operations, rendezvous, docking,
  undocking, de-orbit, reentry, landing, recovery, contingency, abort.
  Synonyms such as "liftoff" for "launch" or "deorbit" for "de-orbit"
  are non-standard and must be replaced or formally defined.
- A synonym conflict occurs when two or more distinct labels appear in
  the same document to mean the same canonical concept — for example,
  both "launch" and "liftoff" used in separate sections without a
  stated equivalence. The conflict must be resolved to a single
  canonical form throughout.

## Workflow

1. Collect every crew role label, mission phase term, and command type
   designator that appears in the document under review. Record each
   term together with its location (section or paragraph reference).
2. For each crew role label, look it up in the canonical role set. If
   it matches exactly, it passes. If it is a known abbreviation or
   synonym, flag it with the canonical replacement. If it is
   unrecognized, flag it as an unknown term requiring resolution.
3. For each mission phase term, look it up in the canonical phase
   vocabulary. Apply the same three-outcome rule: pass, synonym flag,
   or unknown flag.
4. For each command type designator, check it against the authorized
   command taxonomy. Flag any term not found.
5. Scan for synonym conflicts across all terms collected: group terms
   by their resolved canonical concept, and flag any concept that maps
   to more than one distinct label within the document.
6. Produce a finding list grouped by category (crew role, mission
   phase, command type, synonym conflict). A document is nomenclature-
   compliant only when all four finding lists are empty.

## Pitfalls

- Accepting a formally undefined abbreviation as equivalent to its
  canonical form because the meaning "seems obvious" — §4.3.3 requires
  the equivalence to be stated in a document glossary; implied
  equivalence does not satisfy the requirement.
- Resolving synonym conflicts by picking whichever term appears more
  often — the resolution must align to the canonical vocabulary, not
  to local frequency.
- Treating a term as unknown and therefore out of scope — an
  unrecognized term is a finding, not a reason to skip the check; it
  must be resolved or formally added to the vocabulary before the
  document can be baselined.
- Checking role labels in isolation without checking phase terms and
  command types — §4.3.3 applies to the entire operations vocabulary,
  not just crew designations.

## Behavior contract (gate 3)

The canonical-set lookup, synonym detection, and synonym-conflict logic
are exercised by the gate 3 contract test:
scripts/test_e1011_ops_nomenclature.py against
scripts/e1011_ops_nomenclature_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_ops_nomenclature.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
