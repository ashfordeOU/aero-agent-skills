---
name: q6005-packaging-and-despatch
description: "Assess the protective packing, electrostatic precautions and shipping arrangements a finished hybrid microcircuit lot travels under, per ECSS-Q-ST-60-05 clause 13.3. Use when a shipment is being packed or a packing specification reviewed: derive the electrostatic protection level the device withstand voltage demands and compare it with the packaging actually used, size the cushion from the declared drop and allowable shock, budget the moisture against the desiccant enclosed, test the transport envelope and container against the product limits, and return the packing-provision index with one verdict. Trigger: ecss, q-st-60-05, hybrid-packaging-and-despatch, hybrid-packaging-esd-protection-level, hybrid-packaging-cushion-thickness, hybrid-packaging-desiccant-demand, hybrid-despatch-transport-envelope, hybrid-packing-provision-index."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-packaging-and-despatch, hybrid-packaging-esd-protection-level, hybrid-packaging-cushion-thickness, hybrid-packaging-desiccant-demand, hybrid-despatch-transport-envelope, hybrid-packing-provision-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Packaging and Despatch (space-systems/ecss/q6005-packaging-and-despatch)

Use when the task is clause 13.3 of ECSS-Q-ST-60-05: the packing, the
electrostatic precautions and the despatch arrangements for finished hybrid
microcircuits — everything between the last acceptance test and the receiving
inspection at the other end.

## Domain quick reference

- Electrostatic protection is demanded by the part, not chosen by the packer.
  The withstand voltage of the most sensitive device in the shipment sets a
  protection level, and the packaging either reaches it or it does not.
- A bag that does not itself generate charge is not a shield. Dissipative
  material stops the package becoming the source; only a shielding layer
  keeps an external field off the units inside it, and the two are constantly
  swapped for each other.
- Cushioning is a calculation. The drop height the shipment has to survive
  and the deceleration the units can take give a thickness through the
  efficiency of the cushion, and anything thinner is decorative padding.
- Moisture is a budget over time. What is sealed in at packing plus what
  crosses the barrier over the declared storage period has to fit inside the
  desiccant enclosed, and the units are always counted up.
- A desiccant with no humidity indicator cannot be checked on arrival. The
  receiver has to breach the barrier to find out whether the barrier held,
  which destroys the thing being checked.
- The transport mode carries its own envelope. Its temperature range has to
  sit inside the product storage limits, and a sealed container with no vent
  will not survive the pressure change of an air leg.
- The data package that travels with the shipment is graded against its own
  clauses; this leaf grades what protects the hardware.

## Workflow

1. Name the shipment and take the withstand voltage of the most sensitive
   device in it; read the demanded protection level from the sensitivity
   bands.
2. Read the level the proposed packaging build actually provides and compare
   the two.
3. Size the cushion: drop height over allowable deceleration times cushion
   efficiency, then compare with the thickness actually fitted.
4. Budget the moisture: sealed-in moisture from the enclosed volume, plus
   barrier ingress over the storage months, divided by the capacity of one
   desiccant unit and counted up.
5. Check the desiccant fitted against that count, and check that a humidity
   indicator went in with it.
6. Take the transport envelope for the declared mode and test its cold and
   hot ends against the product storage limits; check a sealed container for
   a vent whenever the route has a reduced-pressure leg.
7. Check the container for its packing list and its electrostatic handling
   label.
8. Grade the packing provisions against the full published set, take weighted
   credit over total weight as the packing-provision index, and name the
   verdict — incomplete while a mandatory provision is unspecified, rejected
   on a protection shortfall, a thin cushion, a desiccant shortfall, a
   transport finding, a deficient mandatory provision or a low index,
   acceptable with open actions while findings remain, acceptable when none do.

## Pitfalls

- Choosing the bag from the stores shelf. The demand comes from the part, and
  the most sensitive device in a mixed shipment sets it for everything in the
  box.
- Treating dissipative and shielding as interchangeable. They answer
  different threats, and a dissipative bag around a highly sensitive hybrid
  is a package that looks compliant in a photograph.
- Padding by feel. A cushion that fills the void is not a cushion sized for
  the drop, and the difference only shows up as a unit that passes incoming
  visual and fails electrically.
- Counting desiccant against volume alone. The barrier leaks for the whole
  storage period, so the same box needs more desiccant for a three-year stay
  than a three-month one.
- Enclosing desiccant without an indicator. It converts a five-second check
  on arrival into an opening of the barrier, and the check then destroys the
  protection it was verifying.
- Declaring a route without checking the container against it. Air legs bring
  both a cold soak and a pressure drop, and a sealed unvented container fails
  the second one however good the thermal design is.

## Behavior contract (gate 3)

The electrostatic protection demand and comparison, the cushion thickness
relation, the moisture budget and desiccant count, the transport envelope and
container checks, the provision grading, the packing-provision index and the
shipment verdict are exercised by the gate 3 contract test:
scripts/test_q6005_packaging_and_despatch.py against
scripts/q6005_packaging_and_despatch_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6005_packaging_and_despatch.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
