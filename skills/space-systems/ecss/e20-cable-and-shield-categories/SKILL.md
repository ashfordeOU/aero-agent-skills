---
name: e20-cable-and-shield-categories
description: "Use when group the cables and shields of a spacecraft harness into categories under ECSS-E-ST-20C clause 6.3.8.3: assign every wire run to one harness category, from very sensitive receive coaxial and low-level analogue through sensitive digital and secondary power to noisy primary power, very noisy motor drive and transmit coaxial, and segregated pyrotechnic firing; derive the minimum bundle separation for each routed pair from the category ranks; select the shield termination style from the category and the highest frequency carried, and check the pigtail reactance it leaves; confirm braid optical coverage; and size the voltage a shield transfer impedance couples into a victim run. Trigger: ecss, e-st-20-electrical-scope, cable-and-shield-categories, harness-category-assignment, bundle-separation-distance, shield-termination-style, pigtail-reactance, shield-transfer-impedance, braid-optical-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e20-cable-and-shield-categories, harness-category-assignment, bundle-separation-distance, shield-termination-style, pigtail-reactance, shield-transfer-impedance, braid-optical-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Cable and Shield Categories (space-systems/ecss/e20-cable-and-shield-categories)

Use when the task is the clause 6.3.8.3 harness work of ECSS-E-ST-20C
-- putting every cable and every shield of the spacecraft harness into
the category the electromagnetic wiring clauses recognise, and showing
that the routing, the shield termination and the braid actually match
the category each run was given.

## Domain quick reference

- A run gets exactly one harness category, ordered by how much
  electromagnetic energy it emits and how little it tolerates. Rank 1
  is the very sensitive family (receive coaxial, low-level analogue,
  thermistor sensing, bridge excitation); rank 2 the sensitive family
  (digital data bus, pulse command, secondary power); rank 3 the noisy
  family (primary power feed and return, switched load feed); rank 4
  the very noisy family (motor and reaction-wheel drive, transmit
  coaxial, arc-lamp or heater chopper feed); rank 5 the pyrotechnic
  family, which is segregated rather than merely separated. A wire
  kind that maps to no category is a gap in the harness definition.
- Separation between two routed bundles follows the distance between
  their ranks, not the absolute rank. Same category runs may share a
  bundle; one rank apart needs a small gap; two ranks apart a larger
  one; three or more the largest. Any pair involving the pyrotechnic
  family, other than pyrotechnic with pyrotechnic, takes the largest
  gap and a dedicated overshield on top of it.
- Shield termination style follows the category and the highest
  frequency the run carries. Above the high-frequency threshold, and
  for the pyrotechnic family at any frequency, the shield is
  terminated circumferentially at both ends so it works as a
  transfer-impedance barrier. Below the threshold a rank 1 run is
  terminated at the source end only, so the shield does not close a
  low-frequency loop through structure. The remaining low-frequency
  ranks take the hybrid termination: direct at the source end,
  capacitive at the far end.
- A pigtail defeats a circumferential termination. Its inductance
  scales with length, and the reactance that inductance presents at
  the analysis frequency is the impedance the shield current has to
  push through, so both the length and the reactance carry an
  allowance.
- Braid optical coverage is the fraction of the circumference the
  braid actually covers; the minimum is tighter for the very
  sensitive, very noisy and pyrotechnic families than for the middle
  ranks.
- Coupling through a shield is the transfer impedance per metre times
  the coupled length times the disturbing current, compared with the
  victim run's susceptibility voltage.

## Workflow

1. Assign every run its harness category; reject a wire kind the
   clause does not cover before it reaches the routing checks.
2. For each routed pair, look up the minimum separation from the two
   category ranks and flag a pair routed closer than that, and a
   pyrotechnic pair without a dedicated overshield.
3. Derive the required shield termination style for each run from its
   category and highest frequency, and flag a declared style that
   differs.
4. Where the required style is circumferential, flag a pigtail longer
   than the allowance and a pigtail reactance above the allowance at
   the analysis frequency.
5. Flag a braid whose optical coverage is below the minimum for its
   category.
6. Compute the transfer-impedance coupled voltage for each aggressor
   and victim pair and flag one above the victim's susceptibility
   voltage.
7. Aggregate the category, separation, termination, coverage and
   coupling findings; the harness is categorized and routed correctly
   only when every list is empty.

## Pitfalls

- Routing by absolute rank rather than rank distance, which spaces two
  quiet bundles unnecessarily while letting a rank 2 run sit against a
  rank 4 drive line at the same gap.
- Treating the pyrotechnic family as just another noisy category. It
  is segregated: the largest gap plus a dedicated overshield, and the
  routing check has to look for both.
- Terminating every shield at both ends because it is the strong
  high-frequency answer. Below the threshold that closes a loop
  through structure and injects into exactly the rank 1 runs the
  shield was there to protect.
- Calling a circumferential termination done when a short pigtail
  remains. The pigtail inductance is in series with the shield, and
  its reactance rises with frequency, so a termination that measures
  well at direct current can be ineffective where it matters.
- Reading a braid coverage number without its category minimum; the
  same percentage passes on a rank 2 bundle and fails on a rank 1 run.

## Behavior contract (gate 3)

The category assignment, separation, shield-termination-style,
pigtail-reactance, optical-coverage and transfer-impedance coupling
logic is exercised by the gate 3 contract test:
scripts/test_e20_cable_and_shield_categories.py against
scripts/e20_cable_and_shield_categories_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_cable_and_shield_categories.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
