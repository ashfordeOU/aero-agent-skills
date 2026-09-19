---
name: e3301-anti-creep-barriers
description: "Evaluate the anti-creep barriers that keep a fluid lubricant away from sensitive or un-lubricated surfaces, per ECSS-E-ST-33-01C clause 4.7.3.3.3. Use when the task is proving a mechanism's oil cannot reach an optic, a detector, a latch face or a bonded joint: computing the spreading coefficient and Young contact angle of the lubricant on each barrier film, grading band width, continuity and temperature rating, walking every declared migration path to a sensitive surface for a sound intercepting barrier, and raising a separate finding where a line of sight carries vapour a surface barrier cannot stop. Trigger: ecss, e-st-33-01-mechanisms-scope, lubricant-anti-creep-barrier, lubricant-migration-path, barrier-contact-angle, barrier-spreading-coefficient, lubricant-vapour-transport, barrier-band-continuity."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-anti-creep-barriers, lubricant-anti-creep-barrier, lubricant-migration-path, barrier-contact-angle, barrier-spreading-coefficient, lubricant-vapour-transport, barrier-band-continuity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Anti-Creep Barriers (space-systems/ecss/e3301-anti-creep-barriers)

Use when the task is the clause 4.7.3.3.3 barrier requirement of
ECSS-E-ST-33-01C — stopping a fluid lubricant from migrating out of
the contact it was put in and onto a surface that cannot tolerate it,
or one that was deliberately left dry.

## Domain quick reference

- A barrier works on surface energy, not on geometry. A band of low
  critical surface energy against a lubricant of higher surface
  tension gives a negative spreading coefficient and a finite Young
  contact angle, so the oil beads at the edge of the band instead of
  running across it.
- A contact angle just above zero is not a barrier. The angle has to
  carry a design minimum, because thermal cycling, a film of
  contamination and a handling smear all reduce it in service.
- The physics is irrelevant when the band is wrong. Too narrow and a
  droplet or a fingerprint bridges it; discontinuous and the gap is
  the whole path; used past its temperature rating and the film is
  not the film that was characterised.
- The unit of assessment is the path, not the barrier. A migration
  path runs from a lubricant source to a named destination, and each
  path to a sensitive or un-lubricated surface needs at least one
  sound barrier on it. Counting barriers instead of covering paths is
  how the one unprotected route survives a review.
- A surface barrier does nothing about vapour. Where a path has a line
  of sight from the lubricated volume to the sensitive surface, the
  transport is through the gas phase and the control is a labyrinth,
  a vented enclosure or a getter — declared separately.
- A destination that is un-lubricated on purpose is as sensitive as an
  optic. A latch face or a friction brake that acquires a film of oil
  has lost the property it was designed around.

## Workflow

1. Take the lubricant's surface tension and duty temperature range as
   the reference the barriers are graded against.
2. For each barrier, compute the spreading coefficient and the Young
   contact angle; report complete wetting as a finding rather than
   raising, because a wetted band is a barrier result, not a broken
   input.
3. Grade the same barrier on band width against the minimum,
   continuity around the path, and its temperature rating against the
   duty at both ends.
4. Walk each declared migration path: sensitive destinations need at
   least one barrier that passed, and a path covered only by barriers
   that failed is reported as covered by nothing.
5. Raise a separate vapour finding for a sensitive path with a line of
   sight and no declared vapour control.
6. Report the unprotected paths by name, and keep the per-barrier
   findings alongside them so the fix can be aimed at the band or at
   the routing.

## Pitfalls

- Reading a low barrier energy as sufficient on its own. The margin
  that matters is against the lubricant's surface tension, and a
  fluid with unusually low surface tension can wet a band that works
  for a conventional oil.
- Counting barriers rather than covering paths. Three good bands and
  one bare route is a failing design, and the count looks healthy.
- Accepting a path because a barrier is named on it. A barrier that
  failed its own grading protects nothing, and the path has to be
  reported as unprotected.
- Treating a surface barrier as vapour control. Creep and evaporation
  are different transport mechanisms; a line of sight needs its own
  answer.
- Forgetting the deliberately dry surfaces. A latch face, a friction
  brake or a bonded joint is as sensitive to a film of oil as an
  optical surface, and is easier to leave off the path list.

## Behavior contract (gate 3)

The spreading coefficient, Young contact angle, wetting margin,
band-width, continuity and temperature grading, path coverage, the
vapour line-of-sight finding and the named unprotected paths are
exercised by the gate 3 contract test:
scripts/test_e3301_anti_creep_barriers.py against
scripts/e3301_anti_creep_barriers_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3301_anti_creep_barriers.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
