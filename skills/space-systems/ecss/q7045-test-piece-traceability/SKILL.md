---
name: q7045-test-piece-traceability
description: "Audit the traceability of a set of metallic test pieces back to the material they were cut from, as ECSS-Q-ST-70-45C requires: confirm every piece names its cast or heat, its lot and its product form, resolve the sampling position and orientation within the product, reject a piece whose declared heat is not on the release documentation, and grade the sampled set for orientation and through-thickness coverage before any property derived from it is quoted. Use when accepting machined blanks, reconstructing where a suspect result came from or auditing a test report for sampling provenance. Trigger: ecss, q-st-70-45c, metallic-test-piece-traceability, test-piece-heat-lot-linkage, test-piece-sampling-location, test-piece-orientation-coverage, material-release-documentation."
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
  tags: [ecss, q-st-70-45c-metallic-mechanical-testing, q-st-70-45c, q7045-test-piece-traceability, metallic-test-piece-traceability, test-piece-heat-lot-linkage, test-piece-sampling-location, test-piece-orientation-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Test Piece Traceability (space-systems/ecss/q7045-test-piece-traceability)

Use when the task is the traceability part of the test-piece clause of
ECSS-Q-ST-70-45C: linking each machined test piece back to the cast or heat,
the lot and the position in the product it was taken from, and judging whether
the sampled set supports the property being reported.

## Domain quick reference

- A mechanical property belongs to a material in a place, not to a material.
  The same plate gives a different strength and a very different ductility
  along the rolling direction and through the thickness, so a result with no
  orientation attached is not attributable to anything.
- Position through the section matters as much as direction. A piece taken
  from the surface of a thick forging sees a different grain structure from
  one taken at mid-thickness, and quoting the surface number as the product
  property is how a design ends up with an allowable the part cannot meet.
- The heat or cast identifier is the link to the chemistry and to the release
  documentation. A piece that names a heat the release paperwork does not
  contain is orphaned: it may be good material, but nothing on file says so.
- Lot and heat answer different questions. The heat is the melt; the lot is
  the batch that went through the same processing. Two lots from one heat can
  be heat-treated differently, so both identifiers are needed and neither
  substitutes for the other.
- Traceability is per piece, not per delivery. A box of blanks with one
  certificate on the outside loses the link the moment two blanks from
  different plates are mixed, so each piece carries its own record.
- Coverage is a property of the set. Every piece can be perfectly traceable
  and the set can still be useless, because they all came from one corner of
  one plate and the orientation the design loads in was never sampled.
- Concentration in one heat is a finding even when the count is met. A
  property meant to represent a material cannot be derived from a set that
  represents one melt, and the count alone will not show it.

## Workflow

1. Validate each piece record: a unique piece identifier, a heat or cast
   identifier, a lot identifier, the product form and the orientation.
2. Normalise the orientation to the longitudinal, long-transverse and
   short-transverse set, refusing a token that maps to none of them rather
   than guessing which axis was meant.
3. Resolve the sampling position: the named through-thickness location and,
   where a depth is given, check it is inside the product thickness.
4. Cross-check each declared heat and lot against the release documentation on
   file and list the orphans, the pieces whose material has no paperwork.
5. Detect duplicate piece identifiers, which make two different results
   indistinguishable in the report.
6. Grade the set: which of the required orientations were sampled, which
   through-thickness locations were sampled, and what fraction of the pieces
   came from the single most-used heat.
7. Close with a per-piece verdict and a set-level verdict, keeping an
   individually traceable piece distinct from a set with adequate coverage.

## Pitfalls

- Accepting a delivery certificate as per-piece traceability. It covers the
  consignment; once blanks are mixed, only a mark on each piece says which
  plate it came from.
- Treating lot and heat as the same identifier. Different lots from one melt
  can have had different heat treatment, and a property that moved with the
  treatment will not be explained by the chemistry on the heat certificate.
- Recording orientation only for the transverse pieces. An unmarked piece is
  not longitudinal by default; it is unattributed, and that is a rejection.
- Reading a surface-location result as the product property. The position
  through the section is part of the result, and the quoted value has to say
  which location it came from.
- Declaring coverage met because the piece count is met. Counts and coverage
  are separate gates, and a set concentrated in one heat or one orientation
  fails the second while passing the first.
- Repairing an orphaned piece by assigning it the heat of its neighbours in
  the box. That invents provenance; the piece is either traced from its own
  mark or set aside.

## Behavior contract (gate 3)

The per-piece record validation, orientation normalisation, sampling-position
resolution, release-documentation cross-check, duplicate-identifier detection,
orientation and location coverage grading and the heat-concentration rule are
exercised by the gate 3 contract test:
scripts/test_q7045_test_piece_traceability.py against
scripts/q7045_test_piece_traceability_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_test_piece_traceability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
