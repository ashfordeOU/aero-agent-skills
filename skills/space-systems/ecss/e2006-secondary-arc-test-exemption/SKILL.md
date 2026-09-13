---
name: e2006-secondary-arc-test-exemption
description: "Use when evaluate whether a photovoltaic array may omit the secondary-arc test campaign under ECSS-E-ST-20-06C clause 7.2.3.1: build the worst-case string-to-string potential term by term from the open-circuit operating point, the cold-temperature excursion and the regulation transient, derive the sustained-arc onset voltage for the actual conductor-gap and insulating-material at the arc site, check the potential against that onset with the required margin, check the current the parallel-strings can feed into an arc site against the sustaining limit, list the missing evidence items, and grant or refuse the exemption with the actions a refusal implies. Trigger: ecss, e-st-20-06c, secondary-arc-exemption, sustained-arc-onset, string-to-string-voltage, low-voltage-generator-waiver, arc-sustaining-current, conductor-gap, solar-array-arcing, exemption-evidence-package."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-secondary-arc-test-exemption, e-st-20-06c, secondary-arc-exemption, sustained-arc-onset, string-to-string-voltage, low-voltage-generator-waiver, arc-sustaining-current, solar-array-arcing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Secondary-Arc Test Exemption (space-systems/ecss/e2006-secondary-arc-test-exemption)

Use when the task is the clause 7.2.3.1 allowance of ECSS-E-ST-20-06C: a
photovoltaic array whose generator potential is low enough that a primary
arc cannot be driven into a sustained secondary arc may omit the
secondary-arc test campaign. This leaf decides whether that allowance
applies to a given array and, when it does not, says what has to happen
instead.

## Domain quick reference

- The allowance is a bounded exemption, not a general waiver. A primary
  arc is an initiating event; it becomes a secondary arc only when the
  generator behind it can keep the discharge channel alive. Where the
  generator cannot, the secondary-arc campaign has nothing to demonstrate
  and the clause allows it to be dropped.
- Two physical conditions have to hold together. The potential between
  adjacent strings at the arc site has to stay below the sustained-arc
  onset voltage with margin, and the current the parallel-strings can feed
  into the site has to stay below the level that keeps a channel burning.
  Either condition alone is not the exemption: a low potential with a
  large parallel-strings current, or a small current at a high potential,
  both leave a credible sustained-arc case.
- The worst-case potential is never the nameplate operating point. It is
  assembled from the operating point taken to open circuit, the rise from
  the coldest temperature in the mission profile against the reference
  temperature through the generator temperature coefficient, and the
  regulation transient the power-conditioning can impose.
- The onset voltage belongs to the arc site, not to the array. It rises
  with the gap between adjacent conductors and moves with the insulating
  material bridging them, so the value has to come from the as-built
  geometry and the material actually present, with a floor below which the
  model is not extrapolated.
- A grant is an engineering claim that has to be auditable later. The
  record has to carry the worst-case voltage derivation, the measured
  conductor gap, the insulation material and the string current
  capability; an incomplete record refuses the exemption on evidence
  grounds even when both physical conditions hold.

## Workflow

1. Collect the generator data for the array: operating point, open-circuit
   factor, temperature coefficient, coldest mission temperature, reference
   temperature and regulation transient. Reject an open-circuit factor
   below unity, a negative coefficient or transient, and a minimum
   temperature above the reference.
2. Build the worst-case string-to-string potential by summing the terms
   rather than quoting a single number, so each contribution stays visible
   in the record.
3. Derive the sustained-arc onset voltage from the measured conductor gap
   and the insulating material at the arc site, clamped at the model floor.
   Reject an unrecognized material rather than defaulting it.
4. Apply the voltage criterion: the worst-case potential has to sit at or
   below the onset voltage reduced by the required margin fraction. Treat
   a summed potential that lands a few bits above the allowance as at the
   allowance.
5. Apply the current criterion: accumulate the current of the
   parallel-strings feeding one site and compare it with the sustaining
   limit, with the same representation tolerance.
6. List the evidence items the record is missing against the required set.
7. Grant the exemption only when both criteria are satisfied and the
   evidence is complete; otherwise return the refusal reasons and map them
   to actions - run the campaign, complete the evidence package, or both.

## Pitfalls

- Quoting the nominal bus voltage as the worst case. The cold open-circuit
  excursion plus a regulation transient routinely lifts a low-voltage
  array over an onset that the nameplate number clears comfortably.
- Comparing the worst-case potential directly against the onset voltage
  with no margin. The onset is a modelled boundary, and an exemption taken
  at the boundary has no room for the as-built spread.
- Checking one string's current and forgetting that every parallel string
  tied to the same section feeds the same site. The current that sustains
  an arc is the accumulated one.
- Defaulting an unrecognized insulating material to a generic factor. The
  material sets the onset as much as the gap does, and a silent default
  turns an unverified site into a granted exemption.
- Granting the exemption on physics alone with no record behind it. The
  clause is discharged by an auditable claim; an incomplete evidence
  package is a refusal, not a formality.
- Refusing an at-limit case because a summed voltage or a summed current
  printed a hair over. The representation error belongs in the
  comparison, never in the engineering limit.

## Behavior contract (gate 3)

The worst-case-potential, onset-voltage, voltage-criterion,
current-criterion, evidence and grant-or-refuse logic is exercised by the
gate 3 contract test: scripts/test_e2006_secondary_arc_test_exemption.py
against scripts/e2006_secondary_arc_test_exemption_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_secondary_arc_test_exemption.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
