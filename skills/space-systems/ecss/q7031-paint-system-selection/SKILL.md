---
name: q7031-paint-system-selection
description: "Evaluate candidate primer and topcoat pairings for one item under ECSS-Q-ST-70-31C and return the system to apply: screen out a primer the substrate will not bond to and a topcoat not qualified over that primer, reject a candidate the mission atomic oxygen, ultraviolet dose or thermal cycle range outruns, degrade beginning-of-life solar absorptance over the ultraviolet dose, rank what survives on end-of-life absorptance and absorptance-to-emittance ratio against the thermal role, and name every rejection. Use when a finish has to be chosen rather than merely recorded. Trigger: ecss, q-st-70-31c, paint-system-selection, primer-substrate-compatibility, topcoat-primer-qualification, paint-end-of-life-absorptance, paint-thermal-role-matching."
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
  tags: [ecss, q-st-70-31c-paint-application, q-st-70-31c, q7031-paint-system-selection, paint-system-selection, primer-substrate-compatibility, topcoat-primer-qualification, paint-end-of-life-absorptance, paint-thermal-role-matching]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paints — Paint System Selection (space-systems/ecss/q7031-paint-system-selection)

Use when the task is choosing the paint system itself under ECSS-Q-ST-70-31C:
which primer goes on this substrate, which topcoat is qualified over that
primer, and whether the pairing still does its thermo-optical job after the
mission environment has had its way with it.

## Domain quick reference

- Selection is a two-link chain. The primer answers to the substrate and the
  topcoat answers to the primer; a topcoat that is perfect for the mission is
  still unusable if nothing qualified will carry it on that metal. Both links
  are checked, and a broken link is a rejection with a name, not a low score.
- Substrate chemistry is not interchangeable. Magnesium is the narrow case and
  a laminate is a different case again, which is why compatibility is looked up
  per substrate rather than inferred from "it is a metal".
- Environment ratings are hard limits, not weightings. A system rated to a
  lower atomic-oxygen fluence, ultraviolet dose or thermal-cycle range than the
  mission demands is out; letting a strong thermal score outweigh a rating
  overrun is how an unqualified system reaches a flight drawing.
- The thermal role has to hold at end of life. Solar absorptance grows under
  ultraviolet exposure while emittance moves far less, so the ratio that
  matters is the degraded one. A white finish chosen on its beginning-of-life
  absorptance can miss its radiator duty years before the mission ends.
- Degradation saturates. Absorptance cannot exceed unity, so a long-dose
  extrapolation is clamped rather than allowed to run past a physical bound.
- Ranking needs a deterministic tie-break. Two candidates whose scores agree to
  the last representable digit are ordered by name so the same inputs always
  return the same selection.

## Workflow

1. Normalise the candidate list and refuse duplicate candidate names, so a
   selection can always be traced back to one record.
2. Screen each candidate on primer-to-substrate bonding and
   topcoat-over-primer qualification.
3. Compare the mission atomic-oxygen fluence, ultraviolet dose and
   thermal-cycle range against the candidate's ratings, treating an exact match
   at the rating as met rather than exceeded.
4. Degrade beginning-of-life absorptance over the mission ultraviolet dose and
   clamp the result at unity.
5. Form the end-of-life absorptance-to-emittance ratio and score the candidate
   against the thermal role's two targets.
6. Rank the survivors, break exact ties on the name, and return the selection
   together with every rejected candidate and its reasons.

## Pitfalls

- Selecting on the topcoat alone. The topcoat carries the thermo-optical role,
  but the primer decides whether the system stays attached, and a system is
  only as good as its weaker link.
- Scoring an unrated candidate instead of rejecting it. An environment rating
  overrun is a qualification statement; folding it into a weighted score lets a
  good thermal match hide it.
- Choosing on beginning-of-life absorptance. The finish has to hold its role at
  end of life, so the comparison is made on the degraded value and the ratio
  formed from it.
- Assuming emittance degrades with absorptance. It usually moves much less, so
  the ratio drifts in one direction and a selection made on absorptance alone
  misses how far the ratio has gone.
- Leaving ties to list order. Two equal candidates must not swap places because
  the input was ordered differently; the tie-break is part of the result.

## Behavior contract (gate 3)

The compatibility screens, environment-rating comparison, ultraviolet
absorptance degradation with its unity clamp, ratio formation, thermal-role
scoring, ranking and the deterministic tie-break are exercised by the gate 3
contract test: scripts/test_q7031_paint_system_selection.py against
scripts/q7031_paint_system_selection_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7031_paint_system_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
