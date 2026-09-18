---
name: e2020-essential-load-retrigger-disabling
description: "Audit which command paths may switch off the retrigger behaviour of a limiter feeding an essential spacecraft load, under ECSS-E-ST-20-20C clause 5.2.6.4.1. Use when a power architecture has to show that this authority stays on the ground: refuse essentiality asserted with no rationale reference, sort each path by where the command originates rather than where it executes so an uplinked time-tagged sequence still counts, name every essential limiter an onboard decision could disable, and count how many of them the widest onboard path reaches. Trigger: ecss, e-st-20-20c-clause-5-2-6-4-1, essential-load-retrigger-disable-authority, ground-originated-retrigger-disable-command, onboard-autonomy-retrigger-disable-exposure, essential-load-limiter-grouping, essential-load-retrigger-exposure-count."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-6-4-1, e2020-essential-load-retrigger-disabling, essential-load-retrigger-disable-authority, ground-originated-retrigger-disable-command, onboard-autonomy-retrigger-disable-exposure, essential-load-limiter-grouping, essential-load-retrigger-exposure-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Limiters -- Essential Load Retrigger Disabling (space-systems/ecss/e2020-essential-load-retrigger-disabling)

Use when the task is the clause 5.2.6.4.1 question of ECSS-E-ST-20-20C:
switching retrigger off on a limiter that feeds an essential spacecraft
load is a decision to give that load up after one trip, and only a
command originating on the ground may take it.

## Domain quick reference

- Disabling retrigger changes what the limiter is. A limiter that
  recovers by itself becomes one that stays open after the first trip,
  and on an essential load that is the decision to lose the load. The
  clause puts that decision on the ground, with a person and a record
  behind it.
- Origin is not the moment of execution. A time-tagged sequence uplinked
  from the ground and run hours later is still ground originated: a
  person decided it and the decision is on the uplink record. An action
  produced by onboard fault management is not, however sound its
  reasoning, because nobody on the ground decided this load would be
  given up.
- Sorting the command paths by where they execute rather than where they
  originate is the mistake that admits autonomy through the back door,
  and it looks conservative while doing it -- an uplinked sequence gets
  refused and an onboard reflex gets through.
- Essentiality is a declared property with a rationale behind it. A load
  asserted essential with no reference to the criticality record cannot
  be assessed, because the strength of this protection then depends on a
  word nobody can audit.
- The exposure is counted, not just detected. How many essential
  limiters an onboard path can reach is the number that matters: one
  autonomy function with authority over a dozen essential limiters is a
  different architecture from a dozen functions holding one each, and
  the verdict alone does not separate them.
- An essential limiter nobody can disable at all is worth naming too. It
  does not breach this clause, but ground has then lost a deliberate way
  to give the load up, which is a design choice rather than an accident
  someone should make knowingly.
- Non-essential limiters sit outside the clause. They are grouped so the
  counts have an honest denominator, not so they are judged.

## Workflow

1. Validate the authority policy first: whether an essentiality
   rationale is required, how many exposed essential limiters the
   project admits, and the reach at which one onboard path earns its own
   finding. A fractional allowance, or an advisory reach of zero, is
   refused rather than used.
2. Index every declared command path with two separate facts: whether
   the command originates on the ground, and whether it executes onboard.
   Keeping them separate is what stops a time-tagged uplink being
   grouped with onboard autonomy.
3. Validate every limiter record: identifier, the load behind it, the
   essentiality flag, its rationale reference and the paths permitted to
   disable its retrigger. Duplicate identifiers and an authority naming
   an undeclared path are refused.
4. Group the population by essentiality and close the assessment on
   essentiality not established when a limiter is asserted essential
   with no rationale, or when nothing in the population is essential at
   all.
5. For every essential limiter, name the permitted paths that do not
   originate on the ground. Report all of them, not the first.
6. Count the exposed essential limiters, take their share of the
   essential population, and find the single onboard path reaching the
   most of them, breaking a tie on the path name so the result is
   reproducible.
7. Close on one verdict: essentiality not established, non-ground
   disable authority on an essential load, or disable authority ground
   only -- with the exposure count, its fraction, the widest path and
   any advisory beside it.

## Pitfalls

- Grouping the command paths by where they run. An uplinked time-tagged
  sequence runs onboard and is still a ground decision; an onboard
  reflex runs onboard and is not. Execution location answers a different
  question from the one this clause asks.
- Letting fault management keep a retrigger inhibit because it is
  cautious. Caution is not the issue: the clause reserves the decision,
  and a well-reasoned onboard inhibit on an essential load is exactly
  the case it was written for.
- Accepting the word essential on its own. Without the criticality
  reference the population being protected is whatever the last person
  typed, and the assessment cannot be repeated.
- Reporting exposure as a yes or no. The count and the widest path are
  what tell a reviewer whether one change closes the finding or twelve
  do.
- Widening the assessment to non-essential limiters. Onboard authority
  over a non-essential load is not a breach of this clause, and reading
  it as one makes every later finding easier to dismiss.

## Behavior contract (gate 3)

The policy validation, command-path indexing by origin and execution,
limiter-record validation, essentiality grouping and rationale check,
the non-ground authority determination, the exposure count and fraction,
the widest onboard path and the advisories are exercised by the gate 3
contract test:
scripts/test_e2020_essential_load_retrigger_disabling.py against
scripts/e2020_essential_load_retrigger_disabling_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_essential_load_retrigger_disabling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
