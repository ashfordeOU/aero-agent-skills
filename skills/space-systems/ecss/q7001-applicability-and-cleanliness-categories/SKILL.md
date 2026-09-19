---
name: q7001-applicability-and-cleanliness-categories
description: "Determine which hardware the ECSS-Q-ST-70-01C cleanliness and contamination-control requirements apply to, then group each in-scope item by how much contamination it can tolerate. Use when an inventory mixes flight hardware, ground equipment and facility items and every item needs an applicability decision plus a sensitivity band before any cleanliness level is chosen: screens the three routes into scope, refuses an unjustified exclusion, bands the item separately on its obscuration budget and its areal deposition budget, takes the more demanding of the two, and names the axis and the item that drive a shared environment. Trigger: ecss, q-st-70-01-cleanliness-contamination-scope, contamination-control-applicability-screen, particulate-sensitivity-band, molecular-sensitivity-band, obscuration-tolerance-budget, areal-deposition-tolerance-budget, shared-environment-band-uplift."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-scope, q7001-applicability-and-cleanliness-categories, contamination-control-applicability-screen, particulate-sensitivity-band, molecular-sensitivity-band, obscuration-tolerance-budget, shared-environment-band-uplift]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness and Contamination Control — Applicability and Sensitivity Bands (space-systems/ecss/q7001-applicability-and-cleanliness-categories)

Use when the task is the entry step of ECSS-Q-ST-70-01C — settling which
items the cleanliness and contamination-control requirements reach at
all, and grouping the ones they reach by how much particulate and
molecular contamination their function can absorb before it degrades.

## Domain quick reference

- Applicability is decided by what an item is and what it touches, not
  by who owns it. Flight hardware is in scope; so is anything that
  contacts flight hardware, such as a handling fixture or a test
  adapter; so is anything sharing the controlled environment, because a
  shedding trolley contaminates the hardware beside it. An item outside
  all three routes is out of scope only with a written justification.
- Sensitivity is two independent axes, not one adjective. The
  particulate axis is set by the obscuration — percentage area coverage
  — the item's function still tolerates; the molecular axis by the
  areal deposited mass it still tolerates. An optical surface can be
  demanding on both; a radiator is usually driven by the molecular
  axis, where a thin film moves absorptance long before any particle
  count matters.
- The item's band is the more demanding of its two axes, and the axis
  that produced it is part of the answer. A band with no driving axis
  named cannot be acted on, because the two axes are controlled by
  different means — filtration and handling against particles, bakeout
  and material selection against molecular species.
- A budget expressed as a number is what makes banding reproducible.
  "Optically sensitive" is not a band; a tolerated obscuration of a
  hundredth of a percent is. An in-scope item with no budget on an axis
  is reported as unbanded on that axis rather than quietly banded as
  tolerant.
- A shared environment is held to its most demanding occupant. Banding
  each item in isolation and then processing them in one room gives the
  most demanding item the environment of the least demanding one.

## Workflow

1. Validate each item: a named, non-empty identity, and budgets that are
   real positive numbers where they are declared.
2. Decide applicability through the three routes in order and record the
   route that produced the decision; refuse an out-of-scope declaration
   that carries no justification rather than dropping the item.
3. Band the particulate axis from the obscuration budget and the
   molecular axis from the areal deposition budget, using the programme
   ladder when one is declared and the fall-back breakpoints otherwise.
   A budget exactly on a breakpoint takes the more demanding band.
4. Combine the two axes into the item band and name the driving axis —
   or both when the axes agree.
5. Group the inventory by band, count each band, and identify the item
   that drives the whole set.
6. Report the findings: an in-scope item unbudgeted on an axis, an item
   excluded from scope, and an item sharing an environment with a more
   demanding neighbour.

## Pitfalls

- Treating applicability as a flight-versus-ground question. Ground
  support equipment that touches flight hardware, and anything sharing
  the controlled volume, are inside the requirements; excluding them is
  the most common way contamination enters a clean build.
- Collapsing the two axes into one sensitivity label. Particulate and
  molecular tolerance are controlled by different means and a single
  label hides which one is binding.
- Banding an item on a qualitative description. Without a numeric
  tolerance budget the band is an opinion, and two engineers band the
  same item differently.
- Reading a missing budget as a generous one. An axis with no declared
  budget is unbanded and is reported as a gap; defaulting it to tolerant
  turns a missing allocation into a passed screen.
- Banding items individually and then sharing a cleanroom between them.
  The environment has to meet the most demanding occupant, so a shared
  environment is a finding on the looser item, not a property of it.

## Behavior contract (gate 3)

The applicability routes, the unjustified-exclusion refusal, ladder
validation, breakpoint handling at the bound, two-axis banding with the
driving axis named, inventory grouping and counts, duplicate-name
refusal and the shared-environment finding are exercised by the gate 3
contract test:
scripts/test_q7001_applicability_and_cleanliness_categories.py against
scripts/q7001_applicability_and_cleanliness_categories_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_applicability_and_cleanliness_categories.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
