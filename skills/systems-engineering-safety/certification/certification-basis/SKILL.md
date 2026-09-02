---
name: certification-basis
description: "Use when you must determine the applicable certification regulations and the certification path for a civil aircraft or system: map the project type and aircraft category to the governing airworthiness parts (FAR-25 or CS-25 for transport airplanes, Part 23 or CS-23 for normal airplanes, Part 27 and Part 29 for rotorcraft, Part 33 for engines, Part 35 for propellers), identify special conditions when the design has a novel or unusual feature not covered by the regulation, and select the certification path (type certificate, amended TC, supplemental type certificate, TSO authorization) with the required finding types (compliance finding, means of compliance, certification program). Produces the certification basis list, the special condition flags, and the certification path recommendation. Trigger: certification basis, applicable regulations, FAR-25 applicability, CS-25, type certificate, supplemental type certificate, TSO authorization, special conditions, certification path, regulatory applicability."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: certification
  tags: [certification-basis, type-certificate, supplemental-type-certificate, tso, special-conditions, far-25-applicability, cs-25, certification-program, means-of-compliance, regulatory-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# Certification Basis (systems-engineering-safety/certification/certification-basis)

Use when the task is the regulatory applicability and certification path
determination for a civil aircraft or system: which airworthiness
regulations apply to the product, whether the design needs special
conditions for novel features, and which certification path (TC, amended
TC, STC, TSO) the program follows.

This leaf determines the basis and the path. It does not perform or claim
any certification activity itself; the certification authority makes the
binding determinations.

## Domain quick reference

- The certification basis names the governing airworthiness regulation
  plus program-specific amendments and special conditions, agreed with
  the certification authority at application.
- Applicability runs on product type and category: transport category
  airplanes fall under 14 CFR Part 25 (FAR-25) in the US and CS-25 in
  Europe; normal, utility, acrobatic and commuter airplanes under
  Part 23 / CS-23; rotorcraft under Part 27 / CS-27 (normal category)
  or Part 29 / CS-29 (transport category); engines under Part 33 /
  CS-E; propellers under Part 35 / CS-P.
- The procedural side (issuance of type certificates, supplemental type
  certificates and TSO authorizations) runs through 14 CFR Part 21 and
  the CS-21 equivalents, paraphrased here only at the rule level.
- A special condition is added to the basis when the design has a novel
  or unusual feature that the existing regulation does not cover
  (FAR 25.17 / CS-25.17 for transport airplanes, with analogous
  paragraphs in the other parts).
- Certification paths: a new type design takes a type certificate (TC);
  a major change by the type certificate holder takes an amended TC; a
  major change by anyone else takes a supplemental type certificate
  (STC); an article meeting a Technical Standard Order takes TSO
  authorization.
- Required finding types: the certification basis itself, the means of
  compliance (analysis, test, inspection, similarity), the compliance
  finding, and the certification program that sequences the work.
- Jurisdiction decides the regulation family: FAA programs use the FAR
  parts, EASA programs use the CS parts; a program can hold a basis in
  both when it seeks approval in both jurisdictions.

## Regulation mapping table

| Product | Category | FAA regulation | EASA regulation |
|---|---|---|---|
| Airplane | Transport | 14 CFR Part 25 (FAR-25) | CS-25 |
| Airplane | Normal, utility, acrobatic, commuter | 14 CFR Part 23 (FAR-23) | CS-23 |
| Rotorcraft | Normal | 14 CFR Part 27 (FAR-27) | CS-27 |
| Rotorcraft | Transport | 14 CFR Part 29 (FAR-29) | CS-29 |
| Engine | Any | 14 CFR Part 33 (FAR-33) | CS-E |
| Propeller | Any | 14 CFR Part 35 (FAR-35) | CS-P |

Representative subpart structure for FAR-25 / CS-25: A General, B Flight,
C Structure, D Design and Construction, E Powerplant, F Equipment,
G Operating Limitations and Information, H Electrical Wiring
Interconnection Systems. The authoritative subpart and paragraph listing
is the regulation itself (eCFR for the FAR, EASA easy access rules for
the CS); the tables here are routing summaries.

## Special conditions

A feature is flagged for a special condition when it is novel or unusual
and not covered by the existing regulation. Representative novelty
keywords:

- fly-by-wire, envelope protection, autonomous operation
- lithium battery power, electric or hybrid-electric propulsion,
  high-voltage distribution
- composite primary structure, morphing surfaces, active load
  alleviation, additively manufactured primary structure
- hydrogen fuel systems, blended wing body configurations

A feature described as conventional, proven, legacy, existing, aluminum
or metallic does not flag on its own. The flag feeds the certification
basis; the detailed special condition scope for transport airplanes is
drafted by the avionics/far-cs25/special-conditions leaf.

## Certification paths

| Path | Trigger | Basis clause |
|---|---|---|
| Type certificate (TC) | New type design of an aircraft, engine or propeller | Regulation plus amendments plus special conditions at application |
| Amended TC | Major change by the type certificate holder | Existing basis plus the delta for changed areas |
| Supplemental type certificate (STC) | Major change by someone other than the type certificate holder | Existing type certificate basis plus the STC delta |
| TSO authorization | Article meeting a Technical Standard Order | The TSO minimum performance standard plus applicable airworthiness requirements |
| Minor change | Minor change by the type certificate holder | No new basis; change shown not to affect the existing basis |

## Workflow

1. Name the product type (airplane, rotorcraft, engine, propeller,
   article) and the aircraft category (transport, normal, utility,
   acrobatic, commuter).
2. Determine the applicable regulation with regulation_for or
   applicable_regulations: transport airplane maps to FAR-25 / CS-25,
   normal category airplane to Part 23 / CS-23, rotorcraft to Part 27
   or Part 29, engine to Part 33, propeller to Part 35.
3. Map the regulation to the product areas with paragraphs_for (systems,
   flight-controls, structure, powerplant, equipment, and so on) to
   scope which paragraphs the program must show compliance with.
4. Run detect_special_conditions over the design features and collect
   the flags for the basis; route each flagged feature to the
   special-conditions leaf for the detailed scope.
5. Select the certification path with select_certification_path from
   the change context (new type design, major or minor change) and the
   modifier role (type certificate holder or other).
6. Assemble the basis with certification_basis and record the finding
   types: certification basis, means of compliance, compliance finding,
   certification program.

## Worked example

New transport category airplane with a full-authority fly-by-wire
flight control system featuring envelope protection:

1. Product airplane, category transport.
2. Regulation: FAR-25 (US program), CS-25 if EASA approval is sought.
3. Areas: flight-controls (25.671, 25.672), systems (25.1309), and the
   remaining subparts B through H as applicable.
4. Special conditions: fly-by-wire and envelope protection are flagged
   as novel; both enter the basis as special conditions pending the
   authority's agreement.
5. Path: new type design, so a type certificate, with the full finding
   set (certification basis, means of compliance, compliance finding,
   certification program).
6. Basis summary: FAR-25 with two special condition flags and a TC path.

Second example: an operator installs a new avionics modification with a
lithium battery on an existing transport category airplane. Product is
the airplane, change is major, modifier role is other, so the path is a
supplemental type certificate; the lithium battery feature flags a
special condition for the STC delta basis.

## Pitfalls

- Routing to avionics/far-cs25/airworthiness for the CONTENT of the
  standards: that leaf covers what the airworthiness standards require
  (for example the 25.1309 safety assessment); this leaf covers which
  regulations apply and which path to take.
- Routing special condition SCOPING here: the flag lives in this leaf,
  the detailed special condition content for transport airplanes lives
  in avionics/far-cs25/special-conditions.
- Claiming any certification outcome: this leaf determines the basis
  and the path; only the certification authority issues the findings.
- Mixing jurisdictions: FAR-25 and CS-25 are different instruments with
  different amendment levels; name the jurisdiction before assembling
  the basis.
- Confusing category with class: category (transport, normal) drives
  the part number; class (airplane, rotorcraft) drives the product
  type. Both are needed for the mapping.
- Treating the basis as fixed at first pass: amendments, special
  conditions and the authority's agreement can all change the basis
  before it is finalized.

## Behavior contract (gate 3)

The regulation applicability, special condition detection and path
selection logic is exercised by the gate 3 contract test:
scripts/test_certification_basis.py against
scripts/certification_basis_logic.py (stdlib unittest, offline,
deterministic). Run:
python3 scripts/test_certification_basis.py

## Compliance

- FAR-25 and CS-25 are cited as reference only for the regulatory
  applicability and path determination. Regulation names, part numbers
  and paragraph numbers are public-domain references; every clause in
  this leaf is a paraphrase, not verbatim text.
- compliance: STANDARDS-REF, gated: false.
