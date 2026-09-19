---
name: q7001-manned-areas-interface
description: "Calculate the total offgassing hazard index a hardware item adds to a crewed compartment and whether the atmosphere still closes. Use when equipment is installed in a habitable volume and the cleanliness case has to run from per-species offgassing rates, measured or scaled from installed mass, through the steady-state cabin concentration set by the air revitalisation path, to each species' share of its maximum allowable concentration, the summed total, the driving species and the separate airborne particulate limit. Trigger: ecss, q-st-70-01c, q-st-70-29c, crewed-compartment-offgassing, cabin-total-hazard-index, maximum-allowable-concentration-share, airborne-particulate-cabin-limit, habitable-volume-contamination-interface."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-manned-areas-interface, crewed-compartment-offgassing, cabin-total-hazard-index, maximum-allowable-concentration-share, airborne-particulate-cabin-limit, habitable-volume-contamination-interface]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Crewed-Area Interface (space-systems/ecss/q7001-manned-areas-interface)

Use when the task sits on the boundary between the sensitive-hardware
cleanliness provisions of ECSS-Q-ST-70-01C and the crewed-compartment
offgassing determination of ECSS-Q-ST-70-29C: showing that an item installed
in a habitable volume leaves the cabin atmosphere inside its total hazard
index and inside its airborne particulate limit.

## Domain quick reference

- In a crewed volume the receiver is a person, so the requirement is a
  breathable concentration rather than a surface cleanliness level. Each
  offgassed species is graded against its own maximum allowable
  concentration, and that share is its hazard index.
- The indices add. A cabin full of species each at a tenth of its own limit
  is not automatically acceptable, which is why an item is accepted on a
  total index well below unity — it has to leave room for everything else
  already in the volume.
- Steady-state concentration is set by the removal path, not by the volume.
  A larger cabin only delays the steady state; what the crew eventually
  breathes is the offgassing rate divided by the air revitalisation flow
  times its removal efficiency. Dividing the rate by the volume answers a
  different question.
- Rate itself comes two ways and they must not be mixed for one species: a
  measured article rate from the offgassing test, or a specific rate per
  kilogram multiplied by the installed mass. Declaring both leaves no
  traceable number.
- Airborne particulate is a separate requirement with its own limit and its
  own cause — abrasion, crew activity and filter bypass rather than
  offgassing — so it is reported alongside the molecular total and never
  folded into it.

## Workflow

1. Validate the compartment: volume, air revitalisation flow, removal
   efficiency, allowable total index, measured airborne particulate and its
   limit. Refuse a zero removal efficiency, which has no steady state, and a
   flow implausible against the volume, which is a units error.
2. Resolve every species' offgassing rate, either measured directly or as a
   specific rate times installed mass, refusing a species that declares both.
3. Convert each rate into a steady-state cabin concentration through the
   effective removal flow.
4. Divide each concentration by that species' maximum allowable
   concentration to get its hazard index, and sum the indices.
5. Name the driving species — the largest single index — so the next design
   iteration knows which material to change.
6. Compare the total with the allowable total, absorbing boundary
   representation error with a named tolerance, and separately name any
   species that exceeds its own limit on its own.
7. Compare the airborne particulate loading with its limit and report the
   headroom alongside the molecular result.

## Pitfalls

- Dividing the offgassing rate by the cabin volume. That gives a
  concentration rise per unit time, not a steady state; the removal flow and
  its efficiency are what set the level the crew lives with.
- Accepting an item because no single species reaches its own limit. The
  total is what the atmosphere is graded on, and a spread of small
  contributions can fail while every species passes individually.
- Reporting a total with no driving species. The total tells you there is a
  problem; only the largest contributor tells you which material to change.
- Mixing a measured article rate with a mass-scaled rate for the same
  species. The two come from different tests at different scales and the
  combination cannot be traced back to either.
- Treating airborne particulate as covered by the molecular case. Its
  sources and its removal path are different, and a cabin well inside its
  hazard index can still be over its particulate limit.

## Behavior contract (gate 3)

The compartment and species validation, the dual rate routes and their
mutual exclusion, steady-state concentration through the removal path,
per-species hazard index, the summed total with its boundary tolerance, the
driving-species selection, the per-species own-limit check and the separate
particulate comparison are exercised by the gate 3 contract test:
scripts/test_q7001_manned_areas_interface.py against
scripts/q7001_manned_areas_interface_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7001_manned_areas_interface.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
