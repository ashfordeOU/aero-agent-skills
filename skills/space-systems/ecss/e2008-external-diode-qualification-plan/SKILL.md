---
name: e2008-external-diode-qualification-plan
description: "Use when a protection diode qualification plan is being drafted or reviewed. Evaluate the qualification programme ECSS-E-ST-20-08C clause 9.5.3 asks of external protection diodes, which runs at two levels at once, the bare diodes and the complete diode assemblies built from them: close each level against its own activity set, find the level that was planned while the other was quietly assumed, size every campaign against the specimen minimum for its level, hold assemblies built from diode lots the programme never named, and catch assembly work scheduled before the bare-diode level closes. Trigger: ecss, e-st-20-08c-clause-9-5-3, protection-diode-qualification-programme-coverage, bare-diode-and-assembly-level-split, diode-qualification-specimen-count, diode-assembly-specimen-lot-provenance, diode-qualification-level-sequencing."
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
  tags: [ecss, e-st-20-08-protection-diode-scope, e2008-external-diode-qualification-plan, e-st-20-08c-clause-9-5-3, protection-diode-qualification-programme-coverage, bare-diode-and-assembly-level-split, diode-qualification-specimen-count, diode-assembly-specimen-lot-provenance, diode-qualification-level-sequencing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS External Protection Diodes -- Qualification Programme (space-systems/ecss/e2008-external-diode-qualification-plan)

Use when the task is clause 9.5.3 of ECSS-E-ST-20-08C: the qualification
programme for external protection diodes covers the bare diodes and the
complete diode assemblies they are built into. Two populations, two
activity sets, one programme. A plan that closes one level is not most of
the way to closing both; it has answered a different question. This leaf
reads the planned activities, resolves which level each belongs to, and
returns what the programme still owes.

## Domain quick reference

- The two levels are not a coarse and a fine version of the same campaign.
  The bare diode is a die with its own electrical signature; the assembly
  adds an interconnect, a substrate, an adhesive and a thermal path, and
  every one of those is a failure mode the bare level cannot see.
- A level planned to zero is the loudest finding in the plan and the
  quietest on the page. Nothing is missing from the schedule -- the
  schedule simply never mentions that level, which is why a per-level
  coverage read is done before any activity is judged.
- The specimen minimum belongs to the level, not to the programme. Bare
  diodes are cheap and plentiful and carry the higher count; assemblies
  are expensive and carry a lower one, and a single programme-wide number
  is either wasteful at one level or meaningless at the other.
- The specimens have to come from the lots the programme names. An
  assembly built from whatever diodes were on the bench qualifies those
  diodes, not the ones being delivered, and the plan is the only place
  that link is ever written down.
- Specimens from a foreign lot outrank a short count. A short campaign
  still measures the right population; a foreign one measures something
  else and reports a number with the same confidence.
- Order is part of the programme, not a scheduling convenience. Assembly
  results taken while the bare level is still open rest on parts that were
  not yet qualified, and the assembly campaign has to be repeated if the
  bare level then moves.
- A plan with assembly work and no bare level at all has no barrier to
  check against, which reads as no sequencing finding unless the absence
  is tested for on its own.

## Workflow

1. Read the programme identifier and the diode lot identifiers; the lot
   list is the population every specimen question is asked against.
2. Resolve each planned activity to its level from the activity itself,
   and refuse an entry whose declared level disagrees with it.
3. Find the barrier: the last step the bare-diode level occupies, or
   nothing when that level is absent.
4. Size each campaign against the specimen minimum for its own level and
   report the shortfall rather than a bare pass or fail.
5. Test each activity's specimen lots against the programme's lots and
   name anything foreign.
6. Rank each activity: foreign specimen lots first, then a short campaign,
   then assembly work scheduled at or before the barrier.
7. Close each level against its own required activity set and name a level
   that carries nothing at all separately from one that is merely short.
8. Return a programme verdict that is complete only when both levels are
   covered, every campaign is sized and sourced, and the ordering holds,
   naming the arm to close first.

## Pitfalls

- Treating the assembly level as a formality once the bare diodes pass.
  The interconnect, the bond and the substrate are what the assembly level
  exists to load, and none of them were present at the bare level.
- Reading a plan as complete because every scheduled activity is sound.
  Soundness is a per-activity property; coverage is a per-level one, and a
  plan of five well-sized bare-diode campaigns can be sound and half
  empty at once.
- Applying one specimen count across both levels. It either buys
  assemblies nobody needs or leaves the bare level too thin to say
  anything about a lot.
- Accepting assembly specimens without asking which diodes went into
  them. That link is the whole reason the two levels are one programme,
  and it is written nowhere else.
- Reading the sequence as a project-planning detail. An assembly campaign
  that starts inside the bare-diode level has to be repeated if the bare
  level moves, which is a cost the plan can still avoid and the report
  cannot.
- Missing the plan that has no bare level at all. There is no barrier to
  breach, so every assembly activity passes the ordering test while the
  parts under them were never qualified.
- Merging the arms into one pass or fail. A foreign specimen lot and a
  short campaign ask for very different work, and a merged verdict asks
  for the same one twice.

## Behavior contract (gate 3)

The plan policy validation, the level and activity resolution, the
per-level specimen minimum, the specimen sufficiency and shortfall, the
specimen lot provenance, the assembly start barrier, the ranked activity
verdict, the per-level coverage, the worst-arm selection and the
programme roll-up are exercised by the gate 3 contract test:
scripts/test_e2008_external_diode_qualification_plan.py against
scripts/e2008_external_diode_qualification_plan_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_external_diode_qualification_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
