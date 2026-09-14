---
name: e2008-bare-cell-qualification-general
description: "Determine whether a bare solar cell has actually been qualified under ECSS-E-ST-20-08C clause 7.4.1, where the customer makes the grant and the supplier only produces the evidence: test the evidence set for an activity nobody ran and one claimed without a report, find the non-conformance still open against the article, check a grant exists and came from the customer rather than from the supplier about itself, match its scope to the delivered configuration, then roll the programme up over the articles it delivers. Use when a bare cell is being treated as qualified. Trigger: ecss, e-st-20-08c-clause-7-4-1, bare-solar-cell-qualification-grant, bare-cell-qualification-evidence-completeness, bare-cell-grant-issuing-authority, bare-cell-qualification-scope-match."
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
  tags: [ecss, e-st-20-08-bare-solar-cell-scope, e2008-bare-cell-qualification-general, e-st-20-08c-clause-7-4-1, bare-solar-cell-qualification-grant, bare-cell-qualification-evidence-completeness, bare-cell-grant-issuing-authority, bare-cell-qualification-scope-match]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells -- Qualification, General (space-systems/ecss/e2008-bare-cell-qualification-general)

Use when the task is clause 7.4.1 of ECSS-E-ST-20-08C: a bare solar cell
becomes qualified when the customer grants the qualification, and the
customer grants it once the evidence is complete. Finishing a test
programme is therefore not the same event as being qualified. This leaf
reads the evidence and the grant as two separate things, and returns
what is missing from whichever one is short.

## Domain quick reference

- The grant is an act by the customer, not a status the supplier
  reaches. A supplier that has run every test has produced a complete
  dossier and nothing more, and the difference matters the first time
  somebody downstream asks who accepted the argument.
- Evidence and paperwork fail independently. A complete dossier with no
  grant and a signed grant over a half-finished dossier are both
  unqualified, and they need opposite work to close.
- A declared activity with no report behind it is not evidence. A
  dossier line naming a test is a claim; the report is the thing a
  reviewer can disagree with, and a line without one is an assertion.
- A grant rests on the evidence that existed when it was made. Evidence
  found incomplete afterwards does not weaken the grant, it voids it,
  which is why incomplete evidence is reported ahead of every other arm.
- An open non-conformance is a live question about the article. Granting
  over one moves a decision the customer had reserved into a document
  that says the decision was already taken.
- A grant carries a scope. Cell type, supplier and process baseline are
  what the evidence was gathered on, and a delivered article differing
  in any of them is outside what was granted however recent the grant is.
- Delivered, not submitted, is the population to roll up over. An
  article that ships without ever being put forward is the worst
  finding available, because every other one at least means somebody
  looked at it.

## Workflow

1. Read the article and its identity attributes, and refuse one that
   does not declare them.
2. Read the dossier: name the required activity that is absent, and the
   activity that is declared without a report reference, as two separate
   deficiencies.
3. Collect the non-conformances still open against the article.
4. Read the grant if there is one: refuse an unknown issuing party,
   require a grant reference, and decide whether the issuer is entitled
   to grant under policy.
5. Match the grant's scope to the delivered configuration and name the
   attributes that differ.
6. Rank the arms into one article verdict: incomplete evidence, then an
   open non-conformance, then no grant at all, then a grant from the
   wrong party, then a grant that does not reach the configuration.
7. Roll the programme up over the delivered articles: name the delivered
   articles nobody submitted, group the rest by verdict, report the
   qualified share, and return a verdict that is clean only when no
   delivered article is open.

## Pitfalls

- Reading a finished test programme as a qualification. The programme
  produces the input to the decision; the decision is the customer's and
  it either happened or it did not.
- Accepting a supplier declaration because the tests were real. The
  tests being real is why the dossier is worth reading, and it is not
  the question the clause is asking.
- Counting dossier lines instead of reports. A dossier can list every
  required activity and reference none of them, and an activity count
  reports that as complete.
- Ranking the missing grant above the thin evidence. A missing grant is
  closed by asking for it; incomplete evidence is closed by running
  tests, and reporting the cheap one first hides the expensive one.
- Treating a grant as unconditional. It covers a configuration, and a
  process baseline that moved since the grant was written takes the
  delivered article outside it without anybody editing the grant.
- Rolling up over the submitted articles instead of the delivered ones.
  An article that ships without a submission then leaves no trace in the
  rollup at all, which is the one failure the rollup exists to catch.

## Behavior contract (gate 3)

The evidence completeness test, the unbacked-activity distinction, the
open non-conformance collection, the issuing authority rule, the grant
scope match, the ranked article verdict and the programme rollup over
delivered articles are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_qualification_general.py against
scripts/e2008_bare_cell_qualification_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_qualification_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
