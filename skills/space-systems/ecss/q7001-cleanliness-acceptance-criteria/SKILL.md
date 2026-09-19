---
name: q7001-cleanliness-acceptance-criteria
description: "Evaluate a measured cleanliness value against its acceptance criterion and route what an exceedance creates. Use when a particulate or molecular result has landed near or beyond its limit under ECSS-Q-ST-70-01C: spend the expanded measurement uncertainty on the side of the party making the claim so a straddling value repeats the measurement rather than the cleaning, size the exceedance as a multiple of the limit, group it as minor or major with criticality and recurrence, and route it to re-clean and re-verify, to a use-as-is backed by an accepted impact analysis, or to a review board. Trigger: ecss, q-st-70-01c, cleanliness-acceptance-decision-rule, cleanliness-exceedance-ratio, cleanliness-nonconformance-route, cleanliness-guard-band-uncertainty, reclean-and-reverify-disposition, cleanliness-review-board-escalation."
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
  tags: [ecss, q-st-70-01-cleanliness-scope, q7001-cleanliness-acceptance-criteria, cleanliness-acceptance-decision-rule, cleanliness-exceedance-ratio, cleanliness-nonconformance-route, cleanliness-guard-band-uncertainty, reclean-and-reverify-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness -- Acceptance Criteria and Exceedance Handling (space-systems/ecss/q7001-cleanliness-acceptance-criteria)

Use when the task is the acceptance step of cleanliness verification
under ECSS-Q-ST-70-01C: a measured particulate or molecular value is in
hand, a limit applies to it, and the decision to accept, repeat or raise
a nonconformance has to be made and routed.

## Domain quick reference

- A decision rule is agreed before the measurement, not after it. Under
  a guard-banded rule the measurement uncertainty is spent by whoever
  makes the claim; under a shared-risk rule the value alone is compared
  and both parties carry the uncertainty.
- A straddling result is a measurement problem. When the value plus its
  expanded uncertainty sits outside the limit while the value minus it
  sits inside, neither an accept nor a reject is supportable, and what
  repeats is the measurement rather than the cleaning.
- Expanded is not standard. The uncertainty compared against a limit
  carries the declared coverage factor; using the standard uncertainty
  in its place quietly halves the guard band.
- The size of an exceedance is a ratio, not a difference. A tenth of a
  milligram over a tight limit and over a loose one are not the same
  event, and the ratio is what the grouping runs on.
- Criticality overrides size. A surface whose function the limit
  directly protects earns a major nonconformance on any exceedance,
  however small the ratio.
- Recurrence changes the route. A first exceedance on a reachable
  surface is re-cleaned and re-verified; the same exceedance after the
  cleaning says the cleaning is not the answer and the case belongs to
  a review board.
- Use-as-is is not a shortcut. It is available only where an accepted
  impact analysis bounds the effect of the measured value on the
  function the limit exists to protect.

## Workflow

1. Validate the result: identifier, non-negative value, positive limit,
   non-negative standard uncertainty, coverage factor, decision rule,
   and the criticality, reachability and recurrence flags.
2. Form the expanded uncertainty from the standard uncertainty and the
   coverage factor.
3. Decide against the limit under the declared rule: accept when the
   upper bound stays inside, reject when the lower bound sits outside,
   indeterminate in between; absorb an exact equality with a named
   relative tolerance rather than by moving the limit.
4. On an indeterminate outcome, route the measurement for repeat and
   stop; no nonconformance is raised on an unresolved reading.
5. On a reject, compute the exceedance ratio and group the
   nonconformance as minor or major using the ratio together with
   criticality and recurrence.
6. Route the disposition: re-clean and re-verify a reachable first
   occurrence, use-as-is only behind an accepted impact analysis, and
   escalate to a review board otherwise.
7. Summarise a set of results into verdict counts, escalated
   identifiers, the accepted fraction and the pooled findings.

## Pitfalls

- Comparing the bare value to the limit under a guard-banded rule. The
  guard band is the rule; dropping it turns an agreed risk allocation
  into an unstated one.
- Raising a nonconformance on a straddling result. The hardware has not
  been shown to be out of limit, and the paperwork records a defect the
  measurement cannot support.
- Reading a small exceedance on a critical optic as minor. The ratio is
  small and the consequence is not, which is exactly what the
  criticality flag is for.
- Re-cleaning the same surface a second time after the same exceedance.
  Two identical results are evidence about the process, and the second
  cleaning cycle spends schedule to learn nothing new.
- Recording use-as-is with the impact analysis still open. The
  disposition is only as good as the analysis behind it, and an
  intended one is not an accepted one.
- Reporting an accepted fraction without the indeterminate results.
  They are neither passes nor failures, and folding them either way
  misstates where the verification actually stands.

## Behavior contract (gate 3)

The result validation, expanded-uncertainty formation, guard-banded and
shared-risk decision rules, boundary tolerance, exceedance ratio,
minor-major grouping, disposition routing and set summary are exercised
by the gate 3 contract test:
scripts/test_q7001_cleanliness_acceptance_criteria.py against
scripts/q7001_cleanliness_acceptance_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_cleanliness_acceptance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
