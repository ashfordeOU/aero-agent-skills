---
name: q7001-cleanliness-personnel-training
description: "Evaluate whether a person is trained to work on flight hardware inside a contamination-controlled area under ECSS-Q-ST-70-01C. Use when access to a cleanroom zone is being granted, when training currency has to be checked before a hands-on operation, or when an escort ratio has to be set for untrained staff: derive the curriculum the role and the zone demand, compare it with the records held, compute how long each completed module still runs and which have lapsed, set the earliest refresher date, and return a granted, escorted or refused decision that names the missing and expired modules. Trigger: ecss, q-st-70-01c-cleanliness-scope, contamination-control-training-curriculum, cleanroom-access-authorisation, cleanroom-garmenting-training, training-currency-expiry, cleanroom-escort-ratio, contamination-training-refresher."
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
  tags: [ecss, q-st-70-01c-cleanliness-scope, q7001-cleanliness-personnel-training, contamination-control-training-curriculum, cleanroom-access-authorisation, cleanroom-garmenting-training, training-currency-expiry, cleanroom-escort-ratio, contamination-training-refresher]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Personnel Training and Cleanroom Access (space-systems/ecss/q7001-cleanliness-personnel-training)

Use when the task is the personnel duty of ECSS-Q-ST-70-01C —
deciding what contamination-control training a person owes for the
role they hold and the zone they are entering, and whether the records
they carry let them in today.

## Domain quick reference

- People are the dominant particulate source in a cleanroom. The
  training is not an administrative formality; it is the control that
  keeps the largest contributor inside the budget the hardware was
  built against.
- The curriculum is a function of role and zone together. An inspector
  who only observes and an operator who handles hardware owe different
  modules, and the same operator owes more entering a tighter zone
  than a looser one.
- Training expires. Garmenting and cleanroom behaviour lapse soonest
  because they are motor habits that decay, while awareness and
  method modules run longer. A record with no completion date states
  nothing about currency.
- Expired is not the same as missing, and both are named. A lapsed
  module needs a refresher; an absent one needs the course. Reporting
  a single count leaves the training officer unable to plan either.
- Escort is a real control, not a loophole. An untrained person may be
  taken into a zone at a declared ratio by someone who is trained,
  because the escort is what supplies the missing behaviour.
- Escort does not extend to hands on the hardware. Once the person
  will touch flight hardware, the training has to be theirs, and the
  absence of it is a refusal rather than a ratio.
- The useful second output is the refresher date. Knowing access is
  granted today is worth less than knowing which module lapses first
  and when.

## Workflow

1. Take the person, the role, the zone, the hands-on flag, the
   training records and the date the decision is being made, and
   reject a case that cannot name the role or zone rather than
   assuming the least demanding one.
2. Derive the required curriculum from the role, and extend it with
   the modules the zone adds.
3. Validate each record: a module the catalogue contains, a readable
   completion date, and no duplicate entry for the same module.
4. Compute each module's expiry from its completion date and its own
   validity period, and the days it still has to run at the decision
   date.
5. Separate the required modules into held-and-current, expired, and
   never taken, and keep the names rather than the counts.
6. Decide access: granted when nothing is missing or expired; refused
   when the person will handle hardware and anything is outstanding;
   escorted at the zone ratio when awareness is current and only
   observation is intended; refused otherwise.
7. Report the earliest expiry among the current modules as the
   refresher date, so the next lapse is visible before it happens.

## Pitfalls

- Treating a training record as permanent. A garmenting course taken
  four years ago describes a habit that has had four years to drift,
  which is why the module carries its own validity period.
- Deriving the curriculum from the role alone. The zone is half the
  requirement, and a person cleared for one hall is not automatically
  cleared for a tighter one in the same building.
- Collapsing expired and missing into one number. They need different
  remedies on different timescales, and the count hides which one the
  person needs.
- Escorting someone into a hands-on operation. The escort can supply
  behaviour by example but cannot supply the hands, and the moment the
  untrained person touches hardware the control has gone.
- Granting access on the strength of an awareness module alone.
  Awareness explains why the zone matters; garmenting and flow
  training are what stop the person shedding into it.
- Reporting only today's verdict. A person current for three more days
  and a person current for two more years produce the same answer now
  and completely different plans, so the earliest expiry is reported
  with the decision.

## Behavior contract (gate 3)

Curriculum derivation, zone extension, record validation, expiry and
currency arithmetic, the expired-versus-missing split, the escort
ratio and the access decision are exercised by the gate 3 contract
test: scripts/test_q7001_cleanliness_personnel_training.py against
scripts/q7001_cleanliness_personnel_training_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_cleanliness_personnel_training.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
