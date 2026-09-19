---
name: q7026-rework-and-retermination
description: "Determine whether a failed crimp may be remade or the wire must be replaced, against the re-termination limits of ECSS-Q-ST-70-26C. Use when a bad termination is about to be cut off and crimped again and the allowance has to be checked before the wire gets shorter: count the re-terminations already taken on that wire end, consume the length each remake costs and test the reach afterwards rather than before, refuse to re-use a contact that its own crimp consumed, honour a defect category with no rework path, and return remake, replace-the-wire or scrap. Trigger: ecss, q-st-70-26, crimp-rework-permission, crimp-re-termination-limit, crimp-wire-length-budget, crimp-contact-single-use, crimp-scrap-only-defect."
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
  tags: [ecss, q-st-70-26-crimping-scope, q7026-rework-and-retermination, crimp-re-termination-limit, crimp-wire-length-budget, crimp-contact-single-use, crimp-scrap-only-defect]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Rework and Re-termination Limits (space-systems/ecss/q7026-rework-and-retermination)

Use when the task is the rework step of ECSS-Q-ST-70-26C — deciding
whether a wire end that failed its crimp may be cut back and crimped
again, how much of its allowance that spends, and when the honest
answer is a new wire or a scrapped assembly instead.

## Domain quick reference

- A remake is bought with wire. Each re-termination cuts the failed
  barrel off and strips again, so a fixed length disappears every
  time. On a short pigtail the length allowance runs out long before
  the count does, which is why both are carried.
- The count limit exists independently. Repeated stripping
  work-hardens the conductor and nicks strands in ways the next visual
  inspection will not show, so a wire end carries a maximum number of
  re-terminations whatever length is left on it.
- A crimped contact is consumed by its crimp. The barrel is
  plastically deformed onto the conductor, so removing it ends the
  contact's life and the remake needs a new one. A rule set that
  declares crimp contacts reusable is rejected rather than obeyed.
- Some defect categories have no rework path at all. Conductor damage
  under the insulation and damage to the connector housing are not
  cured by cutting the barrel off, so they scrap rather than route
  back to the bench.
- Length is judged after the cut, not before. The question is whether
  the wire still reaches its routed length with the declared slack
  once the next remake has taken its share, so a wire that looks long
  enough today can already be committed.
- A wire landing exactly on its required length still reaches. The
  comparison absorbs representation error in the length arithmetic,
  and the declared slack is never trimmed to squeeze one more remake
  out of a wire.
- A defect in neither the reworkable nor the scrap-only list is
  undecided, not reworkable. Defaulting it to rework is how a
  conductor defect ends up remade instead of scrapped.

## Workflow

1. Validate the rule set: a positive count limit, a positive length
   cost per remake, a non-negative slack, disjoint reworkable and
   scrap-only defect lists, and no contact type declaring a crimp
   contact reusable.
2. Validate the wire end: identifier, contact type, present length,
   routed length that the present length still covers, and the
   re-termination history as a non-negative whole number.
3. Route on the defect category first. A category with no rework path
   ends the question, and a category in neither list raises rather
   than defaulting.
4. Compute the re-terminations remaining from the count limit and the
   history, flooring at zero rather than reporting a negative
   allowance.
5. Compute the length left after the next remake and compare it with
   the routed length plus the declared slack, absorbing an exact
   landing with a named tolerance.
6. Collect both limit findings rather than stopping at the first, so
   a wire that is out on count and on length says so once.
7. Return the disposition, note whether a new contact is required from
   the contact type, and roll a harness batch up into remake,
   replace-wire and scrap groups with the new contacts counted.

## Pitfalls

- Checking the count and not the length. On short pigtails and
  backshell tails the wire runs out of reach first, and a count-only
  check authorises a remake that leaves the harness short.
- Measuring the reach before the cut. The remake has not happened yet,
  so the length that matters is the one after the barrel comes off.
- Re-crimping a contact that was removed from a failed crimp. The
  barrel was deformed once already and will not form the same
  gas-tight joint a second time.
- Defaulting an unlisted defect category to reworkable. The list is
  the agreement about which damage a remake actually cures.
- Trimming the declared slack to let a marginal wire through. The
  slack is service length for the next intervention, not headroom for
  this one.
- Stopping at the first limit hit, which hides a second one and sends
  the wire back a second time for the same decision.

## Behavior contract (gate 3)

Rule and wire validation, the crimp-contact reuse refusal, defect
routing including the unlisted category, the count allowance floor,
the after-the-cut length test with its exact-landing boundary, both
limits reported together and the harness batch roll-up are exercised
by the gate 3 contract test:
scripts/test_q7026_rework_and_retermination.py against
scripts/q7026_rework_and_retermination_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7026_rework_and_retermination.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
