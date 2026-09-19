---
name: q6005-wire-rebonding-rules
description: "Evaluate a proposed reattachment of an interconnect wire inside a hybrid against the bonding limits of ECSS-Q-ST-60-05C clause 10.5.3. Use when a lifted or broken wire has to be put back and the question is how many attempts the site has left: count the attempts against the allowance for that pad kind, add the accumulated bond footprints and test whether the proposed bond still fits the bondable area, apply the remnant-removal and over-footprint placement rules, flag the wire-to-pad metal pairing, and return a per-site and an overall rebonding disposition. Trigger: ecss, q-st-60-05c, hybrid-wire-rebonding-limits, hybrid-bond-site-attempt-count, hybrid-bond-pad-footprint-utilisation, hybrid-stacked-bond-prohibition, hybrid-interconnect-rebond-disposition."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-wire-rebonding-rules, hybrid-wire-rebonding-limits, hybrid-bond-site-attempt-count, hybrid-bond-pad-footprint-utilisation, hybrid-stacked-bond-prohibition, hybrid-interconnect-rebond-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Interconnect Rebonding Limits (space-systems/ecss/q6005-wire-rebonding-rules)

Use when the task is clause 10.5.3 of ECSS-Q-ST-60-05C: putting an
interconnect wire back after it has lifted, broken or been removed during
permitted corrective work, and deciding whether the site it would land on can
take another bond at all.

## Domain quick reference

- A bond site is a consumable. Every attempt deforms the pad metallisation
  under it and leaves a footprint, and neither the metallisation nor the pad
  area recovers between attempts. The allowance is therefore a count of
  attempts, not of successes: a bond that lifted still spent its turn.
- The allowance is not one number for the whole unit. A chip pad is the
  smallest and most fragile bondable surface in the assembly and takes the
  fewest attempts; a substrate pad and a package post are larger, more
  robust, and take more. Applying the chip-pad number everywhere blocks
  repairable work, and applying the post number everywhere destroys chip
  metallisation.
- Attempts and area are two independent budgets. A large pad can run out of
  attempts while it still has room, and a small pad can run out of room while
  it still has attempts. Both have to be checked, and a refusal on either is
  a refusal.
- The remnant of the previous bond is not cosmetic. Bonding onto a tail, a
  stub or a lifted heel puts the new bond on top of loose metal instead of on
  the pad, and the pull strength that results describes the remnant rather
  than the joint.
- Stacking is a property of the surface, not of the operator. A post can take
  a bond over a previous footprint; a chip pad cannot, because the
  metallisation beneath the first footprint is already worked and the
  underlying die surface has no margin left.
- A mixed wire-and-pad metal pairing is a caution, not a bar. Gold onto
  aluminium and aluminium onto gold both form intermetallics over time, which
  is a reliability finding to be recorded and screened for — it does not make
  the rebond itself impermissible.
- The overall answer is not the worst site. One refused site blocks the
  corrective work as a whole, because the unit is not repaired until every
  interconnect on the repair list is back; reporting only the site that
  failed loses the ones that would have been fine.

## Workflow

1. Validate each bond geometry. A ball bond is described by its flattened
   diameter and a wedge bond by its width and length; an unmeasured bond
   cannot be budgeted against a pad that does not grow, so it is refused as
   an input error rather than assumed.
2. Validate each site: pad kind, bondable dimensions, the bonds already
   placed, whether the remnant was removed, whether the proposed bond would
   sit over a previous footprint, and the wire and pad metals. An
   over-bonded pad validates rather than raising — it is the case being
   graded.
3. Count attempts used against the allowance for that pad kind, and report
   the remainder floored at zero so an exhausted site reads as exhausted
   rather than as a negative.
4. Sum the footprints already on the pad, add the proposed bond, and divide
   by the bondable area. Compare the utilisation with one under a tolerance,
   because a pad filled exactly by its bonds is a designed condition and a
   strict comparison there answers differently on different machines.
5. Apply the placement rules: an unremoved remnant refuses, and a bond over a
   previous footprint refuses wherever the pad kind does not permit stacking.
6. Attach the metal-pairing caution where the wire and pad metals differ, and
   grade the site as permitted, permitted-with-caution or not-permitted.
7. Roll the sites up: an unapproved procedure or any refused site blocks the
   corrective work, cautions propagate, and every site keeps its own record
   so the repair traveller can be written from the result.

## Pitfalls

- Counting successful bonds instead of attempts. A bond that lifted on
  placement consumed the site's metallisation exactly as a good one would,
  and a site graded on successes runs past its allowance without any counter
  registering it.
- Using one attempt allowance for the whole unit. Chip pads, substrate pads
  and posts do not have the same margin, and a single number is either too
  strict for the robust surfaces or too generous for the fragile ones.
- Checking the attempt count and stopping. Area is the other budget, and a
  small pad carrying two full-width wedges has no room for a third even
  though its counter still shows one attempt left.
- Comparing pad utilisation with a strict inequality. A pad filled exactly by
  its bonds is common, and the sum of products that should equal the pad area
  will not always compare that way; without a tolerance the same layout is
  accepted on one host and refused on another.
- Treating remnant removal as housekeeping. Until the tail is off, a rebond
  bonds to the tail, and the pull test that follows measures the wrong joint.
- Escalating a mixed-metal pairing to a refusal. Intermetallic growth is a
  screening and life question that belongs in the record, and refusing the
  rebond over it leaves the unit with no interconnect at all.
- Reporting only the failed site. The corrective work is one job; the sites
  that would have been accepted are needed to plan the rework, and the
  refused ones are needed to escalate it.

## Behavior contract (gate 3)

The bond geometry validation, the pad attempt allowance, the accumulated
footprint budget, the remnant and stacking placement rules, the metal-pairing
caution and the per-site and overall disposition are exercised by the gate 3
contract test: scripts/test_q6005_wire_rebonding_rules.py against
scripts/q6005_wire_rebonding_rules_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6005_wire_rebonding_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
