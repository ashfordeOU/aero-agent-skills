---
name: q7046-source-qualification
description: "Assess whether a threaded-fastener manufacturer may be qualified as a source under the ECSS procurement clause, on demonstrated capability and on audit. Use when ECSS-Q-ST-70-46C requires a supplier decision rather than a lot decision: reduce each qualification-lot characteristic to a capability index from its own sample statistics, let the weakest characteristic govern, weight the audit findings into a demerit total, mark any severity that blocks on its own, age the audit against its validity period, then return qualified, conditionally-qualified or not-qualified with the expiry date and the reasons. Trigger: ecss, q-st-70-46-threaded-fastener-scope, fastener-source-qualification, fastener-manufacturer-capability-index, fastener-supplier-audit-demerits, fastener-qualification-validity, fastener-governing-characteristic."
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
  tags: [ecss, q-st-70-46-threaded-fastener-scope, q7046-source-qualification, fastener-source-qualification, fastener-manufacturer-capability-index, fastener-supplier-audit-demerits, fastener-qualification-validity, fastener-governing-characteristic]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Source Qualification (space-systems/ecss/q7046-source-qualification)

Use when the task is qualifying the manufacturer rather than accepting a lot
under ECSS-Q-ST-70-46C — turning a qualification-lot measurement set and an
audit report into a status that says whether orders may be placed at all, and
for how long that answer holds.

## Domain quick reference

- Qualifying a source is a decision about a process, not about a delivery.
  The evidence is a qualification lot measured characteristic by
  characteristic, and an audit of the quality system that produced it. Either
  one alone qualifies nothing.
- Capability is read per characteristic and then taken at its weakest. A
  manufacturer whose thread pitch is superbly controlled and whose head height
  is marginal is a marginal manufacturer, because the fastener that fails is
  the one made to the feature controlled worst.
- The capability index has to come from the sample's own statistics, not from
  an assumed spread. Mean and sample standard deviation are computed with the
  n-1 divisor, and the index takes the nearer specification limit, so an
  off-centre process is not flattered by a symmetric formula.
- Audit findings are not a count. Severity weights turn them into a demerit
  total that a limit can be set against, and a finding at a blocking severity
  stops qualification regardless of the total, because one systemic failure is
  not offset by an otherwise tidy report.
- A qualification has a clock. The audit date plus the declared validity
  period fixes an expiry, and an audit already past that period supports
  nothing new even if it was clean when it was written.
- The three outcomes differ in what they permit. Not-qualified stops orders;
  conditionally-qualified permits them under a named caveat that has to be
  closed; qualified permits them until the expiry date.

## Workflow

1. Validate the manufacturer identity, the required capability index and the
   demerit limit before any arithmetic is done on the evidence.
2. Reduce each measured characteristic to mean, sample standard deviation and
   capability index, refusing a sample of fewer than two measurements and a
   zero spread that would divide the index by nothing.
3. Take the weakest characteristic as the governing one and keep its name
   with its index, so the reason text names the feature that decided it.
4. Weight the audit findings into a demerit total, group the counts by
   severity, and list the findings that block on their own.
5. Age the audit against the reference date and the validity period; keep the
   sign of the remainder so a lapse can be reported in days.
6. Combine capability, blocking findings, demerit total and currency into one
   status, and return the expiry the audit date implies.

## Pitfalls

- Averaging the capability indices across characteristics. That hides the
  weak feature behind the strong ones; the governing index is a minimum, and
  a mean of indices is not a statement about any real fastener.
- Using the population divisor on a qualification sample. With the small lots
  these samples come in, dividing by n instead of n-1 understates the spread
  and overstates the index by a margin that matters at the limit.
- Treating the capability index as symmetric about the tolerance band. An
  off-centre process is limited by the nearer limit, and the two-sided form
  reports capability the process does not have.
- Counting audit findings instead of weighting them. Ten observations and one
  systemic failure are not the same audit, and a bare count says they are.
- Letting a clean demerit total absolve a blocking finding. The total is a
  threshold on accumulated small problems; the blocking severity is a
  separate gate and is checked separately.
- Comparing the achieved index against the requirement with a bare strict
  inequality. Both sides are floats from divisions, so a process sitting
  exactly on the requirement is compared within a named tolerance while the
  requirement itself stays as specified.

## Behavior contract (gate 3)

The sample statistics, capability index, governing-characteristic selection,
audit demerit weighting with blocking severities, audit currency and expiry,
and the combined qualification status are exercised by the gate 3 contract
test: scripts/test_q7046_source_qualification.py against
scripts/q7046_source_qualification_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7046_source_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
