---
name: e2006-tether-description-and-applicability
description: "Use when determine whether the deployed-tether provisions of ECSS-E-ST-20-06C clause 10.1 attach to a spacecraft configuration: categorize each deployed or connecting element as an electrodynamic-tether, a conducting-tether, a non-conducting-tether, an inter-body connecting-cable or out-of-scope, from its deployed-length, its length-to-diameter slenderness and its conductor continuity; confirm the element spans two separated bodies; then enumerate the hazard families the applicability pulls into the design — motional-emf end-potential, plasma-current-collection, exposed-conductor-arcing, tether-breakage-debris, deployed-dynamics-oscillation — and flag every family carrying no control owner. Trigger: ecss, e-st-20-electrical-scope, e2006-tether-description-and-applicability, space-tether, electrodynamic-tether, tether-applicability, deployed-conductor-element, tether-hazard-inventory, inter-body-connecting-cable."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-tether-description-and-applicability, space-tether, electrodynamic-tether, tether-applicability, deployed-conductor-element, tether-hazard-inventory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Design — Tether Description and Applicability (space-systems/ecss/e2006-tether-description-and-applicability)

Use when the task is the applicability decision of ECSS-E-ST-20-06C
clause 10.1 — deciding which thin deployed or connecting elements of a
spacecraft system are tethers for the purpose of the electrical design
provisions, and which electrical hazard families that decision brings
into the design.

## Domain quick reference

- Clause 10.1 introduces a tether as a thin element deployed between
  two separated bodies of a mission: an electrodynamic-tether driven
  against the geomagnetic-field, a conducting-tether used for
  momentum-exchange or formation-keeping, a non-conducting-tether of
  purely dielectric construction, or an inter-body connecting-cable
  carrying data and power between a mothercraft and a deployed unit.
  Geometry decides membership, not intent: a deployed element counts
  as a tether once it is long compared with the bodies it links and
  slender compared with its own length (a length-to-diameter ratio at
  or above 100:1 in this leaf), and once it actually spans two bodies.
  A short jumper, a boom, or a stubby strut is out of scope even when
  it is conductive.
- The conductor construction, not the mission function, decides the
  electrical exposure. A bare-conductor element sits in direct contact
  with the ambient plasma; an insulated-conductor element is exposed
  only where the dielectric is breached; a dielectric element carries
  no conduction path at all and keeps only the mechanical families.
- The orbit regime gates two of the families. A conducting element
  sweeping the geomagnetic-field in a low or medium orbit develops a
  motional end-potential along its length; only the dense low-orbit
  plasma supports meaningful current-collection at the ends. Beyond
  that plasma, and in interplanetary flight, both families fall away
  and what remains is breakage debris and deployed-dynamics
  oscillation, which every deployed element carries regardless.
- Applicability is a gate, not a verdict. The output of this clause is
  the set of in-scope elements and the hazard families each one drags
  in; the quantitative work — end-potential magnitude, collecting-area
  sizing, insulation continuity — belongs to the clauses downstream of
  it. What clause 10.1 does own is the finding that an in-scope family
  has no control owner on record.

## Workflow

1. Inventory every deployed or connecting element: deployed length,
   diameter, conductor construction (bare, insulated, dielectric),
   mission function, and whether it spans two separated bodies.
2. Compute the slenderness of each element as deployed length over
   diameter in consistent units. An element below the minimum deployed
   length, or below the slenderness threshold, is not a tether and
   leaves the assessment. Treat an exact-boundary ratio as compliant —
   absorb the representation error in the comparison, never by moving
   the threshold.
3. Categorize each surviving element from its conductor and function:
   dielectric construction gives a non-conducting-tether whatever the
   function; an electrodynamic function gives an electrodynamic-tether;
   a data-and-power umbilical gives a connecting-cable; anything else
   conducting gives a conducting-tether.
4. Apply the spanning test. A slender deployed element that does not
   link two separated bodies is out of scope, but record it as a
   finding rather than dropping it silently — the spanning assumption
   is the one most often wrong in an early configuration.
5. Enumerate the hazard families for each in-scope element from its
   category, conductor and orbit regime. Reject an unknown conductor,
   function or regime instead of defaulting it.
6. Compare the families against the controls on record. An in-scope
   element is applicability-complete only when every family it carries
   has a named control; report each uncontrolled family as its own
   finding, then state the inventory-level verdict.

## Pitfalls

- Reading "non-conducting" as "out of scope". A dielectric tether
  still fails structurally, still oscillates, and its breakage still
  produces debris; only the conduction-driven families fall away.
- Categorizing by mission function first. An electrodynamic mission
  flown on a dielectric line has no conduction path — the construction
  overrides the intent, and reversing that order invents hazards that
  the hardware cannot produce.
- Letting a long conducting element into scope without the spanning
  test, or dropping a non-spanning one without a finding. Both hide
  the same configuration question.
- Carrying the low-orbit family set into a high orbit or an
  interplanetary leg. Current-collection needs the dense plasma and
  the motional end-potential needs the swept field; asserting them
  everywhere buries the real driver under a worst case.
- Treating an empty finding list as applicability-complete when no
  controls were ever recorded. An element with no controls on record
  produces a finding per family; silence there means the inventory was
  never populated, not that the design is clean.

## Behavior contract (gate 3)

The slenderness, categorization, spanning, hazard-family and
control-coverage logic is exercised by the gate 3 contract test:
scripts/test_e2006_tether_description_and_applicability.py against
scripts/e2006_tether_description_and_applicability_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_tether_description_and_applicability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
