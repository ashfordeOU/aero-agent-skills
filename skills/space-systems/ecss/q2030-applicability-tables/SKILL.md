---
name: q2030-applicability-tables
description: "Determine which harness requirement sets apply to a given cable or harness type at a given product category using the informative applicability tables of ECSS-Q-ST-20-30C Annex A. Use when the task is refusing a table that states one address twice, grouping a pair's requirement sets into applicable, excluded and conditionally open, holding an undecided condition open instead of reading it as a yes or a no, reporting a set the table never addressed as undetermined rather than excluded, and letting a normative clause override an informative exclusion. Trigger: ecss, q-st-20-30c, harness-applicability-tables, requirement-set-applicability, harness-type-and-class-resolution, conditional-applicability-entry, undetermined-requirement-set, informative-annex-precedence, applicability-table-contradiction."
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
  tags: [ecss, q-st-20-electrical-harness-scope, q-st-20-30c, q2030-applicability-tables, harness-applicability-tables, requirement-set-applicability, conditional-applicability-entry, undetermined-requirement-set, informative-annex-precedence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Harness Manufacturing — Annex A Applicability Tables (space-systems/ecss/q2030-applicability-tables)

Use when the task is reading the informative applicability tables of
ECSS-Q-ST-20-30C Annex A -- working out which requirement sets a
particular harness or cable type owes at a particular product category,
and knowing what the answer is and is not worth.

## Domain quick reference

- The tables are a routing aid, not a requirement. They are informative,
  so what they produce is a proposal to be confirmed against the normative
  clauses; a programme that treats a table cell as the requirement has
  moved its compliance basis into an annex that never claimed to carry it.
- A table row is an address: harness type, product category, requirement
  set. The same address stated twice is a contradiction, and there is no
  precedence rule that resolves it, so the table is repaired rather than
  interpreted. Picking the first row, the last row or the stricter one all
  produce a defensible-looking answer that nobody can reproduce.
- Three dispositions matter and they behave differently. Applicable and
  not-applicable close a set. A conditional entry does not: it names the
  condition that decides it, and until that condition is decided the set
  is OPEN. Reading an undecided conditional as applicable buys work that
  may not be owed; reading it as not-applicable drops work that is.
- A requirement set the table never addressed for a pair is undetermined,
  which is a different state again. It is the most dangerous one, because
  an absent row looks exactly like a decision to exclude when the
  applicable sets are read off as a list.
- Because the annex is informative, a normative clause that invokes a set
  the table excludes governs. The disagreement is worth reporting rather
  than silently resolving, since it usually means the table was written
  for a configuration the harness has since left.
- Coverage is the honest summary: what fraction of the requirement-set
  universe this pair has actually decided. A tidy applicable list over a
  low coverage figure is a tailoring exercise that has barely started.

## Workflow

1. Validate the table before resolving anything: every row addresses one
   harness type, one product category and one requirement set, and every
   conditional row names its deciding condition. Refuse a repeated
   address, including one that agrees with itself.
2. Fold the spellings -- case, spacing and separators -- so a table
   written by hand resolves the same way as one exported from a tool.
3. Select the rows for the pair in hand and group them into applicable,
   excluded and conditionally open.
4. Apply the conditions that have been decided, and leave the rest open
   with the condition named, so what is missing is a question rather than
   a gap.
5. Compare the addressed sets against the requirement-set universe and
   report every set the table never mentioned as undetermined.
6. Reconcile against the normative clauses actually invoked: name the
   sets invoked against an informative exclusion, and the sets invoked
   while their condition is still open, then form the governing applicable
   list.
7. Report the coverage fraction alongside the grouped lists and the
   findings, so the tailoring's completeness is visible with its result.

## Pitfalls

- Treating a table cell as the requirement. The annex is informative; the
  compliance basis stays with the normative clauses, and an audit asks for
  those.
- Resolving a doubled address by precedence. No rule ranks two rows at one
  address, so any resolution is invented; the table is repaired instead.
- Reading an undecided conditional as a yes or a no. Both are defensible
  in the moment and neither is reproducible; keeping it open with the
  condition named is what lets somebody close it later.
- Reading an absent row as not-applicable. Unaddressed is undetermined,
  and a set that quietly leaves a programme this way is normally found at
  qualification.
- Resolving for the harness type and forgetting the category. The pair is
  the address; the same cable type carries different sets at different
  product categories.
- Reporting the applicable list on its own. Without the coverage fraction
  a three-row table looks as complete as a thirty-row one.
- Silently overriding the table with a normative invocation. The normative
  clause governs, but the disagreement is evidence that the table no
  longer matches the build, and it belongs in the record.

## Behavior contract (gate 3)

The token and disposition folding, the row construction with its
conditional-condition rule, the doubled-address refusal, the pair
resolution into applicable, excluded and open sets, the condition
application, the undetermined-set report, the normative reconciliation and
the coverage fraction are exercised by the gate 3 contract test:
scripts/test_q2030_applicability_tables.py against
scripts/q2030_applicability_tables_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2030_applicability_tables.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
