---
name: e2020-single-failure-line-containment
description: "Verify that one failure disables at most one protected distribution line, per clause 5.2.15.1.1 of ECSS-E-ST-20-20C. Use when a single-point-failure argument has to be read failure by failure rather than box by box: enumerate the protected lines, attach every declared failure point to the lines it actually takes down, refuse a line-local point that reaches past its own line, count the fan-out a shared drive, command path, return or source stage produces, and rank a protected line nobody traced above one traced and found exposed. Trigger: ecss, e-st-20-20c-clause-5-2-15-1-1, single-failure-line-containment, distribution-line-fan-out, shared-element-line-exposure, untraced-protected-line."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-15-1-1, e2020-single-failure-line-containment, distribution-line-fan-out, shared-element-line-exposure, untraced-protected-line, line-local-failure-point]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Single Failure Line Containment (space-systems/ecss/e2020-single-failure-line-containment)

Use when the task is clause 5.2.15.1.1 of ECSS-E-ST-20-20C: one failure
disables at most a single protected distribution line. The bound sits on
the failure and not on the line, so this leaf walks the failure points
and counts outward, rather than walking the lines and asking whether
each looks well protected.

## Workflow

1. Validate the policy: the bound must be a whole number of lines of at
   least one, and the exposure ceiling must sit between zero and one.
2. Build the line inventory, refusing a line declared twice and a line
   that never says whether it is protected.
3. Attach every failure point to the lines it takes down, refusing an
   unknown line reference, a line named twice, and a point that disables
   nothing at all.
4. Refuse a line-local point that reaches past its own line -- it was
   mislabelled, and leaving the label on hides the fan-out.
5. Count the fan-out of each point over the protected lines only, and
   collect the points that exceed the bound, worst first.
6. Compute the share of protected lines leaning on shared hardware, and
   compare it against the exposure ceiling separately.
7. List the protected lines no failure point ever names, then rank the
   design at its worst standing: untraced, over the bound, over the
   exposure ceiling, unprotected, contained.

## Domain quick reference

- Only a protected line is counted against the bound. An unprotected
  output is a real finding, but it belongs to whether protection exists
  at all, and folding it in here dilutes the count the clause asks for.
- The fan-out comes from the shared parts, not from the line hardware. A
  drive shared by two switches, one command path feeding two lines, a
  common return and a single source stage are where one failure becomes
  two dark lines.
- A line-local point that names another line is not a line-local point.
  The label is the claim, so it is refused rather than quietly recounted.
- A shared drive reaching only one protected line today still has that
  line on common hardware. That is worth a number of its own -- the
  share of protected lines depending on a shared element -- and it is
  reported apart from the fan-out instead of folded into it.
- A protected line no failure point ever mentions has not passed. It is
  the part of the analysis nobody did, and it outranks a line traced and
  found exposed, because the two need different work.
- The worst fan-out is what the design is reported at. An analysis full
  of comfortable ones tells you nothing once a single point reaches two.

## Pitfalls

- Reading the analysis line by line and concluding each line looks fine.
  Every line can look fine while one shared return takes four of them.
- Counting unprotected outputs inside the protected total. It lowers the
  exposed fraction and raises nothing, which is exactly backwards.
- Trusting a point labelled line-local because the label is convenient.
  The label is what is being tested, not what is being assumed.
- Declaring the same failure point twice under two names and reading the
  duplicate as independent redundancy.
- Stopping at the fan-out count and never reporting how much of the
  distribution leans on shared hardware. A design at the bound today is
  one integration change from being over it.
- Reporting an untraced protected line inside the same list as the lines
  that were traced and found contained. One needs an analysis and the
  other needs nothing, and merging them buries the one that matters.

## Behavior contract (gate 3)

The failure point kind vocabulary, the line inventory with its protected
flag, the line-local point refused when it reaches past its own line,
the fan-out counted over protected lines only, the over-bound offenders
ordered worst first, the shared-hardware exposure fraction kept apart
from the fan-out, the untraced protected lines, the waivable tracing
requirement and the ranked design verdict are exercised by the gate 3
contract test:
scripts/test_e2020_single_failure_line_containment.py against
scripts/e2020_single_failure_line_containment_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_single_failure_line_containment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
