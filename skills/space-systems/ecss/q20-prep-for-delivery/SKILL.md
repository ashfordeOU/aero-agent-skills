---
name: q20-prep-for-delivery
description: "Prepare a finished item for delivery under ECSS-Q-ST-20C clause 5.7.4: size the cushioning from the declared drop height and the fragility level, check the bearing stress the item puts on that cushion against the window the material is rated over, size the desiccant charge from barrier area, vapour transmission and storage duration, then derive the label fields and the protection means the item's own states make mandatory and name every one the prepared package does not carry. Use when a package has to be built, marked and protected before it ships. Trigger: ecss, q-st-20c-clause-5-7-4, preparation-for-delivery, delivery-package-cushion-sizing, package-bearing-stress-window, barrier-bag-desiccant-sizing, delivery-package-marking, esd-protective-packaging."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-prep-for-delivery, preparation-for-delivery, delivery-package-cushion-sizing, package-bearing-stress-window, barrier-bag-desiccant-sizing, delivery-package-marking, esd-protective-packaging]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Preparation for Delivery (space-systems/ecss/q20-prep-for-delivery)

Use when the task is the clause 5.7.4 preparation step of ECSS-Q-ST-20C: the
item has passed its acceptance and now has to be packaged, marked and protected
so that what the customer unpacks is what the supplier signed off.

## Domain quick reference

- Cushioning is sized from two numbers the item brings with it: the drop height
  the handling case declares, and the acceleration the item survives. The
  thickness that keeps a drop inside the fragility level falls out of those and
  the energy-absorption efficiency of the material, not out of what fits the
  box.
- A cushion is only a cushion inside its rated stress window. Too little
  bearing stress and the material never compresses, too much and it bottoms
  out; both transmit more shock to the item than a correctly loaded pad, so the
  static stress the item puts on it is a check in its own right.
- A moisture barrier is a rate problem, not a seal problem. Water crosses the
  barrier at the transmission rate of the material for as long as the item is
  stored, so the desiccant charge comes from area times rate times duration
  against the capacity of one unit — and a part unit is a whole unit.
- Marking is derived, not chosen. Each state of the item — electrostatic
  sensitivity, moisture sensitivity, a temperature limit, a cleanliness level,
  a hazard, an internal pressure — adds the field that tells the next handler
  what they are holding.
- Protection is derived the same way. Electrostatic sensitivity is not one bag;
  it is the shielding bag, the connector shunts and the grounded handling the
  bag is opened under.

## Workflow

1. Validate the item: mass, bearing area and fragility have to be real positive
   quantities, and each sensitivity state has to be stated rather than assumed.
2. Compute the cushion thickness the drop height and fragility need, and
   compare the fitted thickness against it with a relative tolerance so an
   exact-equality case is not read as a shortfall.
3. Compute the static bearing stress and raise a separate finding for each side
   of the rated window it falls outside.
4. For a moisture-sensitive item, size the desiccant charge and compare it with
   the units actually fitted; refuse the pass outright when no storage data was
   supplied, rather than treating the absence as zero ingress.
5. Derive the mandatory label fields from the item states and name each one the
   applied label does not carry, matching names without regard to case or
   separator.
6. Derive the mandatory protection means the same way and name each one the
   package does not provide.
7. Report every finding of the pass together; the package is ready only when
   none of them stands.

## Pitfalls

- Sizing the cushion on the box rather than the item. Thickness comes from drop
  height and fragility; a pad that fits the void and nothing else is a filler.
- Checking the cushion material and not the load on it. The same pad under a
  light item and a heavy one sits at two different points on its curve, and
  only one of them is in the window.
- Treating a sealed bag as moisture protection with no duration attached. The
  barrier leaks at its rated rate for the whole storage period, so the charge
  depends on how long the item waits, not on how well the seam was made.
- Rounding a desiccant requirement down. A part unit is a shortfall, and the
  charge is bought in whole units.
- Bagging an electrostatic-sensitive item and calling it protected. Without
  shunts on the connectors and a grounded opening procedure, the protection
  ends the moment the bag does.
- Stopping at the first missing label field. The package is prepared once, so
  the pass has to name every gap in that sitting.

## Behavior contract (gate 3)

The item validation, cushion thickness sizing, bearing-stress window check,
desiccant charge sizing, derived label fields, derived protection means and the
combined readiness decision are exercised by the gate 3 contract test:
scripts/test_q20_prep_for_delivery.py against
scripts/q20_prep_for_delivery_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_prep_for_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
