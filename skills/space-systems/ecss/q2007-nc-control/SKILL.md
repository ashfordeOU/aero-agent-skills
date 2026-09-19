---
name: q2007-nc-control
description: "Manage a nonconformance raised at a space test centre under ECSS-Q-ST-20-07C clause 5.8.2, inside the ECSS-Q-ST-10-09 nonconformance system: categorize the anomaly major or minor from safety effect, exceeded article limit, violated requirement or invalidated conditions; derive its reporting deadline and disposition authority; decide whether the run owes a partial or a full retest; and test the proposed disposition against the customer agreement it needs. Use when a test-centre anomaly, an anomaly report log or a disposition proposal has to be adjudicated before campaign close-out. Trigger: ecss, q-st-20-07c, q-st-10-09, test-centre-nonconformance, test-anomaly-report, nonconformance-disposition-authority, test-retest-scope-decision, article-overstress-ratio, nonconformance-close-out."
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
  tags: [ecss, q-st-20-test-centre-scope, q2007-nc-control, test-centre-nonconformance, test-anomaly-report, nonconformance-disposition-authority, test-retest-scope-decision, nonconformance-close-out]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Control of Nonconformances (space-systems/ecss/q2007-nc-control)

Use when the task is the nonconformance-control step of ECSS-Q-ST-20-07C
clause 5.8.2 — deciding what an anomaly discovered at the test centre makes
the centre owe: how fast it must be reported, who owns its disposition, and
how much of the run has to be done again.

## Domain quick reference

- A test-centre anomaly has two distinguishable subjects and the control
  path differs: the test article, and the test itself. A facility fault that
  left the article untouched still invalidates the conditions and still
  forces a retest; an article defect found during test is dispositioned
  through the customer's nonconformance system whatever the facility did.
- Severity is derived, not declared. Personnel or facility safety, a level
  taken past the article's stated limit, a violated specified requirement or
  invalidated test conditions each make the anomaly major on their own. The
  derivation matters because the deadline and the authority both hang off it.
- The reporting clock starts at detection, not at the end of the run or at
  the shift handover. A major anomaly reaching the customer after the run is
  finished has already cost the customer the decision it was owed.
- Disposition authority follows severity: a minor anomaly is dispositioned by
  the centre's quality function, a major one by the customer's review board.
  Use-as-is and repair leave the article different from its specification, so
  on a major anomaly both need the customer's recorded agreement.
- Retest scope is a separate decision from disposition and is often forgotten.
  A level past the article's limit puts the whole article's state in question
  and forces the run again; invalidated conditions force the affected phases
  again, and force the whole run only when every phase is affected.
- A record marked closed while a finding is still open is itself a finding.
  Close-out of the campaign is a statement that no anomaly is unresolved, so
  it is graded on the set, not on each record in isolation.

## Workflow

1. Validate the anomaly record: identifier, detection hour, reporting hour
   and proposed disposition are all required; a report timed before its
   detection is an input error.
2. Categorize severity from the effect flags, deriving overstress from the
   applied level against the article limit when both are given rather than
   trusting a declared flag.
3. Derive the reporting deadline and the disposition authority from that
   severity, and grade the elapsed hours against the deadline with a named
   tolerance at the boundary.
4. Decide the retest scope: full for an overstressed article, full when every
   phase was invalidated, partial for the named affected phases, none when
   neither applies. Refuse to guess when conditions were invalidated but no
   phase is named.
5. Check the disposition against the permitted set and against the customer
   agreement a major use-as-is or repair requires.
6. Confirm an owed retest is either the disposition itself or recorded as
   performed; an owed retest that is neither is a finding.
7. Aggregate the campaign: count major, minor, open, late and retest-owed
   records, and permit close-out only when the finding list is empty.

## Pitfalls

- Trusting a declared overstress flag when the applied and limit levels are
  both in the record. Derive it, and treat a level exactly on the limit as
  within the limit rather than past it.
- Letting the reporting clock start at the end of the run. The deadline is
  measured from detection, so an anomaly detected early in a long campaign
  can be late before the run is over.
- Dispositioning a major anomaly use-as-is on the centre's own authority.
  The centre can propose it; only the customer's review board can agree it.
- Closing a record because the disposition was agreed while the retest it
  forced has not been performed. Disposition and retest scope are separate
  decisions and both have to be discharged.
- Repeating only the phase where the anomaly was noticed when the article
  itself was taken past a limit. The article's state, not the phase boundary,
  is what governs the scope in that case.
- Widening a reporting deadline to make an exact-equality case pass. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the deadline stays as specified.

## Behavior contract (gate 3)

The severity derivation, deadline and authority mapping, timeliness grading,
retest-scope decision, disposition validation and campaign aggregation are
exercised by the gate 3 contract test:
scripts/test_q2007_nc_control.py against
scripts/q2007_nc_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_nc_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
