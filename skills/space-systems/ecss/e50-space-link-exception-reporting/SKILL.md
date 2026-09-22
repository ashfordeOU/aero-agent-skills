---
name: e50-space-link-exception-reporting
description: "Audit a space link exception reporting design against ECSS-E-ST-50C clause 5.6.14.9 — a reporting path by which any error the link detects can be raised, over a set the clause recommends stretch to data units taken in after correction, service data units with nowhere to go, deliveries that fail, reconfiguration and unannounced link loss — and grade that coverage apart from the question the clause leaves to the design, whether a report says which exception it is, because a design can route every condition and still identify none. Name the detectable conditions no route carries, the reports whose identifying fields are absent or blank, and the burst whose one-report-per-occurrence rate saturates the very channel it reports over, with the aggregation limit that fits. Use when reviewing link fault reporting or event coverage. Trigger: ecss, e-st-50-communications, space-link-exception-reporting, unreported-link-exception, exception-report-identifying-fields, exception-report-aggregation, report-channel-budget."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.14.9
    items: [a, b]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-space-link-exception-reporting, unreported-link-exception, exception-report-identifying-fields, exception-report-aggregation, report-channel-budget, link-exception-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Space Link Exception Reporting (space-systems/ecss/e50-space-link-exception-reporting)

Use when the task is the exception reporting obligation of ECSS-E-ST-50C
clause 5.6.14.9 — that every error the link detects can be reported — together
with the question the requirement leaves to the design: whether the report that
goes out says which exception it is.

## Domain quick reference

- Coverage and identification fail independently and a single verdict
  hides that. A design can route every condition it detects and still
  identify none of them, and another can produce immaculate reports for
  the three conditions it happens to route while staying silent on the
  rest. Grading them separately is the whole job.
- The expensive failure is the condition nothing routes. The subsystem
  detected it, recorded it, and told nobody — which on the ground is
  indistinguishable from the condition never having happened.
- A blank identifying field is a gap, not a value. It renders as an
  empty cell in whatever reads the report, and an empty cell reads as
  nothing to say rather than as something not captured.
- An occurrence count of zero contradicts the report carrying it. A
  report exists because something happened, so a count below one is a
  defect in the reporting path rather than a quiet period.
- The report channel is part of the link being reported on. A condition
  recurring at high rate, reported one occurrence at a time, spends the
  downlink on saying the same thing repeatedly and crowds out the
  traffic the link exists for.
- Aggregation is the remedy and it needs the count to survive. One
  report per window carrying how many times the condition fired keeps
  the information and drops the load to a fixed cost.
- A route for something nothing detects is dead configuration. It is not
  a compliance failure, but it is a report that can never be raised, and
  it makes a coverage table look complete when it is not.

## Workflow

1. List what the subsystem can actually detect before looking at any
   routing. The detectable set is the denominator for the first item.
2. Subtract the routed conditions from it. What remains is the silent
   failure list, and it is reported first because nothing downstream
   compensates for it.
3. Hold the detectable set against the conditions the clause recommends
   covering — a data unit taken in corrupted even where the correction
   worked, a service data unit with nowhere to be delivered, a delivery
   that does not complete, a link put into another configuration, and a
   link lost with no warning. One of those the design neither detects
   nor routes should be raised as advice not taken, not as a failed
   requirement.
4. Check each configured report against the identifying field set —
   which condition, when, on which link, and how many times — treating
   an absent field and a blank one as the same finding.
5. Reject an occurrence count that is not a count, or is below one.
6. Compute the report channel load of reporting every occurrence in the
   window separately, and compare it against the report budget with a
   relative tolerance so a burst exactly filling the budget fits.
7. Where it does not fit, state the number of separate reports that do
   fit and the fixed cost of aggregating the rest into one report
   carrying a count.
8. Grade coverage and identification separately and the overall verdict
   in order: silent conditions, then a saturated channel, then
   unidentifiable reports. Note dead routes without failing either
   grade.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.14.9a | 2 |
| ECSS-E-ST-50C Rev.2 5.6.14.9b | 3 |

## Pitfalls

- Auditing the reports that exist and calling it coverage. The finding
  that matters is the condition with no report at all, and it is
  invisible in any review that starts from the report list.
- Rendering an unknown field as blank. The report then looks complete
  and the missing identification surfaces during an anomaly, which is
  the one moment it cannot be recovered.
- Reporting every occurrence of a recurring condition. The reporting
  becomes the dominant load on a link that is already in trouble, and
  the reports themselves start being lost.
- Aggregating without the count. Collapsing a burst into one report
  loses the severity, and a condition that fired a thousand times reads
  exactly like one that fired once.
- Assuming a routed condition is an identified one. The route proves
  something is sent, not that the receiving end can tell what happened.
- Deciding the channel budget with a bare inequality. A burst sized to
  exactly fill the report budget then fits on some hosts and saturates
  on others.

## Behavior contract (gate 3)

Type-set, route and occurrence-count validation, the identifying-field census
with absent and blank treated alike and a zero count refused, coverage of the
detectable set, dead routes, the report channel load with its aggregated
alternative and whole-report budget limit including the exact-budget case,
coverage and identification graded independently, and the verdict ordering that
puts a silent condition above a saturated channel are exercised by the gate 3
contract test:
scripts/test_e50_space_link_exception_reporting.py against
scripts/e50_space_link_exception_reporting_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_space_link_exception_reporting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
