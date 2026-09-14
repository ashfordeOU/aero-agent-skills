---
name: e2008-failed-bare-cell-components
description: "Use when failed bare cells have to be dispositioned and counted. Determine the treatment a bare solar cell component receives once it exhibits any mode the failure criteria list, under ECSS-E-ST-20-08C clause 7.6.2: refuse a policy that fixes no treatment for a listed mode, withdraw the component on one mode rather than on severity, scrap it for a mode no repair reverses, open rework only while cycles remain, retain a failed test article for the evidence it carries, raise segregation and a non-conformance entry, and report the shortfall the withdrawals leave against the ordered quantity. Trigger: ecss, failed-bare-cell-treatment, failed-bare-cell-segregation, failed-bare-cell-nonconformance-record, failed-bare-cell-rework-admissibility, failed-bare-cell-scrap-disposition, bare-cell-lot-quantity-shortfall."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-failed-bare-cell-components, e-st-20-08c-clause-7-6-2, failed-bare-cell-treatment, failed-bare-cell-segregation, failed-bare-cell-nonconformance-record, failed-bare-cell-rework-admissibility, failed-bare-cell-scrap-disposition, bare-cell-lot-quantity-shortfall]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Failed Bare Cell Components (space-systems/ecss/e2008-failed-bare-cell-components)

Use when the task is clause 7.6.2 of ECSS-E-ST-20-08C: what happens to a
bare cell component once it exhibits any of the failure modes the
preceding criteria list. This leaf reads the declared mode list, a
treatment policy and one batch of components, and returns a disposition
per component plus the lot rollup the delivery count depends on.

## Domain quick reference

- One listed mode is the whole test. A component exhibiting any single
  mode is a failed component and leaves the deliverable population; the
  clause does not grade modes into serious and tolerable, and a treatment
  built on severity has replaced the criterion with a judgement.
- Withdrawal comes first and is unconditional. What follows -- scrap,
  rework, retention -- varies with the mode and the role, but the
  component is out of the delivered quantity the moment a mode is
  present, so the count and the paperwork start from the same place.
- The modes decide whether a remedy exists. A mode the policy places
  beyond repair rules the component out permanently, and one irreversible
  mode is enough however many reworkable ones sit beside it. The policy,
  not the inspector, fixes which is which, and a policy that leaves a
  listed mode unplaced cannot disposition anything.
- Rework is bounded by history, not only by mode. A component already
  reworked to the limit is out of remedies even for a mode that would
  otherwise be repairable, because each cycle takes more out of a thin
  cell than the last one did.
- Rework is checked afterwards. A repair that nobody re-tested is a
  repair nobody has evidence for, so the re-test travels with the rework
  permission rather than being a separate decision.
- Role changes the treatment, not the verdict. A failed test article is
  as failed as a failed deliverable, but scrapping it destroys the
  evidence the investigation was going to work from, so it is retained
  and segregated instead.
- A failed component is never recovered by measuring it again. Re-test
  after rework checks the repair; re-test instead of rework is a search
  for a favourable reading, and it returns an article to the lot that
  nothing was done to.
- The lot count is the consequence nobody sees coming. Withdrawals are
  per component and the shortfall is per delivery, so a batch that
  treated every failure correctly can still be short of the ordered
  quantity, and that is a finding rather than a silent delivery.

## Workflow

1. Validate the listed failure mode set the criteria handed over: a
   non-empty list, no mode named twice, every mode named. With no list
   there is nothing for a component to exhibit.
2. Validate the treatment policy against that list: every listed mode
   placed in exactly one treatment category, no category holding a mode
   the criteria never listed, a whole number of rework cycles, and the
   segregation, non-conformance and re-test flags stated. An unplaced
   mode closes the assessment on treatment not established.
3. Read each component record back: a non-blank identifier, a known
   role, only modes from the declared list, and a non-negative rework
   history. A mode nobody declared fixes no treatment and is refused.
4. Release a component showing no mode, and count it toward the delivery
   only if it is a deliverable.
5. Withdraw every component showing at least one mode, and attach the
   segregation and non-conformance entries the policy requires.
6. Disposition the withdrawn component: retain a test article for its
   evidence; scrap a deliverable exhibiting any irreversible mode;
   otherwise open rework while cycles remain, with the re-test attached,
   and scrap it once they do not. Record a request to return it on a
   re-test alone as a finding rather than granting it.
7. Roll the batch up: the withdrawn, scrapped, reworked and retained
   identifiers, the non-conformance list, the delivered quantity against
   the ordered one, and the shortfall. Close on one verdict: treatment
   not established, lot quantity shortfall, or failed components treated.

## Pitfalls

- Ranking the modes before applying the clause. Any one listed mode
  fails the component, and a severity screen in front of that quietly
  raises the acceptance threshold.
- Leaving a listed mode with no treatment in the policy. It looks like a
  gap in paperwork until a component exhibits it and nobody can say what
  happens next.
- Reworking a component that has already been reworked to the limit.
  Each cycle costs more than the last on a thin cell, and the history is
  part of the decision.
- Granting a return to the lot on a re-test. The component is unchanged;
  only the reading is, and the next reading may be different again.
- Scrapping a failed test article. It is the only physical evidence for
  the failure, and the investigation that needs it cannot be reopened
  once it is gone.
- Counting a withdrawn component in the delivered quantity. The
  withdrawal and the count have to agree, otherwise the lot ships short
  and the shortfall is found downstream.
- Treating the shortfall as arithmetic nobody needs to see. It is the
  consequence of correct treatment, and it is the finding the programme
  acts on.

## Behavior contract (gate 3)

The listed mode validation, the policy coverage check with its unplaced
and double-placed mode refusals, the component record read-back with its
undeclared-mode refusal, the release of a clean component, the
unconditional withdrawal on one mode, the scrap, rework and retention
dispositions, the rework cycle history, the re-test attachment, the
return-by-re-test finding, the non-conformance list, the delivered
quantity and the lot shortfall verdict are exercised by the gate 3
contract test:
scripts/test_e2008_failed_bare_cell_components.py against
scripts/e2008_failed_bare_cell_components_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_failed_bare_cell_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
