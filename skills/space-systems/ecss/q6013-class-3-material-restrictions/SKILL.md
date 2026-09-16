---
name: q6013-class-3-material-restrictions
description: "Use when a Class 3 build has to show a commercial part's construction carries no banned material and every restricted one is cleared. Assess the materials and constructions declared for a commercial EEE part against the Class 3 restrictions of ECSS-Q-ST-60-13C clause 6.2.2.2: grade each declared finish, plating and package body as accepted, restricted or prohibited, test whether an applied mitigation is one the restriction actually accepts, measure plastic-encapsulation exposure against the maker's moisture floor life, and name the governing item. Trigger: ecss, q-st-60-13-commercial-eee-scope, class-3-prohibited-construction-screen, commercial-part-pure-tin-whisker-restriction, commercial-part-cadmium-and-zinc-plating-ban, commercial-part-plastic-encapsulation-moisture-floor-life, restricted-construction-mitigation-coverage, governing-construction-restriction."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-3-material-restrictions, class-3-prohibited-construction-screen, commercial-part-pure-tin-whisker-restriction, commercial-part-cadmium-and-zinc-plating-ban, commercial-part-plastic-encapsulation-moisture-floor-life, restricted-construction-mitigation-coverage, governing-construction-restriction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 3 Material Restrictions (space-systems/ecss/q6013-class-3-material-restrictions)

Use when the task is the construction screen of ECSS-Q-ST-60-13C
clause 6.2.2.2 -- deciding whether what a commercial part is made of
bars it from a Class 3 build, and whether a restricted construction has
been cleared by a mitigation the restriction actually accepts.

## Domain quick reference

- Class 3 takes a commercial part largely as the maker built it, so
  the one thing left under the buyer's control is what it is made of.
  A commercial maker optimises finish and body for a warehouse and a
  benign ground life, and several of those choices fail in vacuum, in
  a thermal cycle, or simply after a year on a shelf.
- Every declared material or construction falls in one of three
  buckets. Accepted carries no restriction. Restricted is admissible
  only against a named mitigation. Prohibited is admissible against
  nothing, because the mechanism is not one a process step removes.
- A bare tin finish is the restriction teams meet first: it grows
  whiskers that bridge adjacent conductors, and the mitigations that
  clear it all work by alloying the tin away -- a lead-bearing dip, a
  lead-bearing reflow, or a refinish. A conformal coat does not.
- Cadmium and zinc plating sublime in vacuum and redeposit where they
  are least wanted; mercury moves and is orientation dependent. These
  are prohibited rather than restricted because no process step at the
  buyer's end changes the mechanism.
- A mitigation only counts when the restriction names it. A part with
  a beryllium-oxide handling procedure against a bare tin finish has a
  procedure and an uncleared restriction, not a cleared one.
- The plastic-body restriction has a number attached. A non-hermetic
  body absorbs moisture, and the maker's moisture-sensitivity level
  sets a floor life: the hours the part may sit out of a sealed dry
  pack before it is baked again. Past it, the moisture boils at reflow
  and lifts the die.
- The useful output is the governing item -- the single worst-graded
  construction -- because the rest of the declaration is noise until
  that one is settled.

## Workflow

1. Declare every material and construction on the part by a name the
   restriction table carries. Reject an undeclared name rather than
   screening it silently; an unknown construction is an open item.
2. Look each one up and grade it accepted, mitigated, unmitigated or
   prohibited. Match applied mitigations against the ones the entry
   names, and discard the rest as ineffective for that restriction.
3. Where the part has a non-hermetic plastic body, measure the
   declared time out of the dry pack against the floor life the
   maker's moisture level sets. Report exposure sitting exactly on the
   floor life as on-limit and compliant, not as a breach.
4. Take the worst grade as the part verdict; a prohibited or
   unmitigated construction rejects it, an entirely mitigated
   declaration is accepted with its mitigations recorded.
5. Report the mitigation coverage across the restricted items, so a
   partly cleared declaration is visible as partly cleared.
6. Name the governing item and the change it demands -- a refinish, a
   bake and reseal, or a different part.

## Pitfalls

- Counting any mitigation as a mitigation. The restriction names the
  process steps that remove its own mechanism; anything else leaves a
  procedure in the file and the failure mechanism on the board.
- Treating a prohibited plating as a tough restricted one. Sublimation
  in vacuum is not something a buyer-side step reverses, so a lot with
  cadmium or zinc plating is out whatever is applied to it.
- Screening the finish and forgetting the body. The finish restriction
  and the moisture floor life are independent, and a part can clear
  every material rule while its exposure has already run out.
- Letting an unknown construction pass because it is not in the table.
  Absence from the table means nobody graded it, which is an open item
  and not an acceptance.
- Reporting only the verdict. A declaration with four restricted items
  and three cleared is a different procurement problem from one with
  four uncleared, and the coverage is what tells them apart.
- Comparing exposure with its floor life by bare arithmetic. The
  exposure is accumulated from several intervals while the floor life
  is one declared number, so an exposure built to land exactly on it
  can sit a few units in the last place above; the comparison absorbs
  that representation error while the floor life stays untouched.

## Behavior contract (gate 3)

The restriction-table validation, the per-item lookup and grading, the
mitigation-effectiveness match, the moisture floor-life lookup and
exposure grading, the worst-of-declaration roll-up, the mitigation
coverage and the governing-item selection are exercised by the gate 3
contract test:
scripts/test_q6013_class_3_material_restrictions.py against
scripts/q6013_class_3_material_restrictions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_material_restrictions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
