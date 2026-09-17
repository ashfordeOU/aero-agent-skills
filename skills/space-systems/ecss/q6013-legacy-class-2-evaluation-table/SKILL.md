---
name: q6013-legacy-class-2-evaluation-table
description: "Evaluate a legacy active part type against the ECSS-Q-ST-60-13C Table 8-12 evaluation list. Use when a legacy commercial active part is being adopted at the intermediate assurance class and an executed evaluation campaign has to become an evaluated-or-repeat verdict: confirm every table grouping was performed at or above its required sample, hold a grouping that consumes its devices to accept-on-zero, require devices drawn from more than one production lot so the result describes the part type rather than one build, and void a record past its currency window or one predating a declared process change. Trigger: ecss, q-st-60-13c-table-8-12, legacy-class-2-evaluation-list, evaluation-grouping-sample-shortfall, evaluation-source-lot-diversity, evaluation-currency-window, part-type-process-change, evaluation-consuming-grouping-accept-on-zero."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-legacy-class-2-evaluation-table, q-st-60-13c-table-8-12, legacy-class-2-evaluation-list, evaluation-grouping-sample-shortfall, evaluation-source-lot-diversity, evaluation-currency-window, part-type-process-change]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Legacy Class 2 Evaluation Table (space-systems/ecss/q6013-legacy-class-2-evaluation-table)

Use when the task is the legacy evaluation test list of ECSS-Q-ST-60-13C
Table 8-12 — taking the groupings, sample sizes and acceptance limits the
table sets for an active part at the intermediate assurance class and turning
an executed evaluation campaign on one part type into an evaluated-or-repeat
verdict.

## Domain quick reference

- Evaluation is per part type, not per lot. It is the one-time judgement that
  a legacy commercial part is fit to be adopted at all, which is why a
  shortfall in it is repeated rather than screened around later.
- The grouping set is the list. A campaign that ran three of the four
  groupings has not evaluated the part type, whatever the sample sizes were,
  and the absent groupings are named so the repeat is scoped rather than
  re-run whole.
- Devices come from more than one production lot. An evaluation drawn from a
  single date code characterises that build; the part type is what is being
  adopted, so the distinct source lots are counted and reported alongside the
  verdict.
- A grouping that consumes its devices is judged accept-on-zero. There is no
  rate to tolerate on four devices taken apart, so an accept number above zero
  on such a grouping is a specification error rather than a looser limit.
- Evaluation records age. A record past its currency window no longer stands
  on its own, and a declared process or fab change voids it whatever its age,
  because the devices evaluated are no longer the devices being bought.
- The sample the table asks for is a floor, not a target. Running fewer
  devices than the required sample leaves the grouping unperformed; running
  more is permitted and does not buy relief anywhere else.

## Workflow

1. Validate each grouping: an unknown grouping name, a zero sample, an accept
   number above the sample, more failures than devices sampled or an accept
   number above zero on a consuming grouping is an input error, not a
   degenerate case to clamp. Refuse a grouping that appears twice.
2. Compare each grouping's devices with the required sample and report the
   shortfall in devices rather than as a bare failure, so the repeat scope is
   readable from the record.
3. Judge failures against the accept number, and flag an accepted grouping
   that used up its allowance as marginal instead of letting it read as clean.
4. Count the distinct date codes behind the campaign and hold a result drawn
   from fewer production lots than the minimum, naming the count.
5. Age the record against the currency window, absorbing representation error
   at the boundary with a named tolerance rather than by widening the window,
   and void it outright on a declared process change.
6. Name the absent groupings, collect every rejecting grouping, and hold the
   part type when any single one rejects rather than averaging the groupings
   into one rate a clean grouping can carry.

## Pitfalls

- Treating a missing grouping as a partial pass. The evaluation is the set;
  three of four groupings is an unevaluated part type, not a 75% result.
- Drawing every evaluation device from one date code. The campaign then
  characterises a single build, and the first different lot delivered is
  outside everything that was measured.
- Honouring an accept number above zero on a grouping that takes its devices
  apart. A tolerated failure on a sample of four is not a rate, it is a
  specification error that silently doubles the acceptable defect population.
- Carrying an expired evaluation into a new procurement because its subgroups
  were clean. Cleanliness is not currency, and a process change after the
  campaign voids the record however good the numbers were.
- Widening the currency window to absorb an exact-equality case. An age
  landing exactly on the window is a representation question handled by the
  tolerance inside the comparison; the declared window stays as specified.

## Behavior contract (gate 3)

The grouping validation and accept-on-zero rule, the required-sample
shortfall, the accept-number and marginal-allowance judgement, source-lot
diversity, the currency window with its process-change override, the absent
grouping set and the overall evaluated-or-repeat disposition are exercised by
the gate 3 contract test:
scripts/test_q6013_legacy_class_2_evaluation_table.py against
scripts/q6013_legacy_class_2_evaluation_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_legacy_class_2_evaluation_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
