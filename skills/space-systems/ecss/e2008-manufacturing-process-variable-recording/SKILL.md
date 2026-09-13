---
name: e2008-manufacturing-process-variable-recording
description: "Identify and log the process variables that move a photovoltaic assembly under ECSS-E-ST-20-08C clause 5.4.5. Use when a production readiness review has to show the recording plan was fixed before the first unit was built: derive the performance swing each variable can produce across its own control band, express it as a share of the assembly performance tolerance, set the logging each variable earns from that share, compare it against the logging actually declared, and roll the list up to a governing variable. Trigger: ecss, e-st-20-08c, pva-process-variable-recording, manufacturing-process-variable-identification, process-parameter-logging-plan, control-band-performance-swing, production-readiness-variable-list, unlogged-process-influence."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-manufacturing-process-variable-recording, pva-process-variable-recording, manufacturing-process-variable-identification, process-parameter-logging-plan, control-band-performance-swing, production-readiness-variable-list, unlogged-process-influence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Manufacturing Process-Variable Recording (space-systems/ecss/e2008-manufacturing-process-variable-recording)

Use when the task is the pre-production duty of ECSS-E-ST-20-08C clause
5.4.5 -- naming the manufacturing variables that move assembly
performance and fixing how each one is logged, before the first
production unit is built rather than after an assembly under-performs.

## Domain quick reference

- The clause is about timing as much as content. A variable that was
  never written down was never recorded, so every unit built before it
  was named carries no data on it, and no amount of later diligence
  recovers that history.
- A variable earns its recording plan from what it can actually do to
  the assembly: the performance swing it can produce across its own
  control band, which is the sensitivity of performance to the variable
  multiplied by the span the process permits it to move over. A large
  sensitivity inside a tight band is a small variable; a modest
  sensitivity inside a wide band is not.
- That swing means nothing on its own, only against the performance
  tolerance the assembly is held to. The share of the tolerance one
  variable can consume is the number that sets the logging.
- Recording method, strongest to weakest: continuous-logged (every
  unit, against time), per-lot-sampled (once per production lot),
  witness-coupon-only (inferred from a coupon processed alongside), and
  not-recorded. A variable that can consume the whole tolerance on its
  own is logged continuously; one that can consume a quarter of it is
  sampled per lot; the remainder still need a witness record, because
  the clause asks for the influencing variables to be logged, not
  merely ranked.
- Variables that move performance independently combine as a root sum
  square, which is what the assembly is expected to see; the linear
  stack is the worst case and both are worth reporting, because a list
  whose root sum square already sits near the tolerance has no room for
  a variable nobody identified.
- The useful summary of a weak plan is not the count of gaps but the
  swing that goes unrecorded. Three well-logged variables and one
  unlogged variable that owns a third of the tolerance is a plan with
  one problem, and that problem is sized.

## Workflow

1. List every manufacturing variable a process engineer can name that
   plausibly moves assembly performance, each with its units, its
   sensitivity, the control band the process permits, the recording
   method declared for it, and whether it was named before production
   started.
2. Reject a band of zero width. A value the process holds fixed is a
   setting, not a variable, and carrying it on the list dilutes the
   ranking with something that cannot swing.
3. Compute each potential performance swing across the full band, using
   the magnitude of the sensitivity so that a variable which degrades
   performance downward is not credited with a negative influence.
4. Divide each swing by the assembly performance tolerance and read the
   required recording method off the share, treating a share that lands
   on a threshold within representation error as meeting it.
5. Compare the declared recording method against the required one and
   record the shortfall in the terms a production engineer acts on:
   this variable, this band, this method, that method needed.
6. Roll the list up: rank by swing, name the governing variable, report
   the combined swing both ways, and size the swing that is currently
   unlogged. A variable identified after production started drags the
   whole plan down regardless of how well it is logged now.

## Pitfalls

- Ranking variables by sensitivity alone. Sensitivity without the
  control band is half the quantity, and the ranking it produces puts a
  tightly held variable above one the process lets wander.
- Fixing the recording plan after the first article. The clause runs
  the other way round, and a plan written after production started
  leaves a block of units with no record of the variable that the
  investigation will want most.
- Leaving a low-influence variable with no record at all. The lightest
  required method is a witness record, not nothing; a variable judged
  small on an estimated sensitivity has no data to correct the estimate
  with when the estimate turns out to be wrong.
- Counting gaps instead of sizing them. Two unlogged variables that
  each own one per cent of the tolerance are not the same problem as
  one that owns half of it, and a gap count reports them identically.
- Comparing a share against a threshold with bare arithmetic. The share
  is a quotient of products of decimal inputs, so a variable that sits
  exactly on the continuous-logging threshold can land a few units in
  the last place below it and be demoted to sampling on one platform
  and not another.

## Behavior contract (gate 3)

The band-width check, swing computation, influence share, required
recording method, adequacy comparison, ranking and plan roll-up are
exercised by the gate 3 contract test:
scripts/test_e2008_manufacturing_process_variable_recording.py against
scripts/e2008_manufacturing_process_variable_recording_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_manufacturing_process_variable_recording.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
