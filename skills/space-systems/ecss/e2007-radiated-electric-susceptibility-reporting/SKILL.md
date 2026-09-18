---
name: e2007-radiated-electric-susceptibility-reporting
description: "Assess what an ECSS-E-ST-20-07C clause 5.4.11.5 radiated electric susceptibility report has to put in front of a reader: validate every frequency point for generator setting, forward and reflected power and achieved field level, compute the net power delivered and the field the chamber calibration factor predicts from it, grade the decibel discrepancy against the level written into the report, confirm each point reaches the reader through a table or a graph with named axes and a logarithmic frequency axis once the span passes a decade, categorize points as reportable, unpresented or irreconcilable, and return the presentation verdict. Use when compiling or reviewing a radiated susceptibility test report. Trigger: ecss, e-st-20-07c, radiated-electric-susceptibility-reporting, susceptibility-generator-setting-record, forward-power-reporting, achieved-field-level-table, susceptibility-report-graph-axes, achieved-field-consistency-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-susceptibility-reporting, susceptibility-generator-setting-record, forward-power-reporting, achieved-field-level-table, susceptibility-report-graph-axes, achieved-field-consistency-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Susceptibility Reporting (space-systems/ecss/e2007-radiated-electric-susceptibility-reporting)

Use when the task is the reporting clause of ECSS-E-ST-20-07C clause
5.4.11.5 -- the generator settings, the forward power and the field
levels actually achieved, presented as tables or graphs so that a reader
who was not in the chamber can tell what the unit was exposed to.

## Domain quick reference

- A susceptibility result is a claim about a level, so the level is the
  thing that has to be defensible. The report therefore carries three
  numbers per frequency rather than one: what the generator was set to,
  what power reached the antenna, and what field was measured at the
  unit. Drop any of the three and the achieved level stops being
  traceable to anything.
- Forward power alone does not say what the antenna received. A
  mismatched antenna sends part of the drive back down the line, so the
  power that did work is the forward reading less the reflected one, and
  a point whose reflection swallows the drive is reporting a level that
  was never established.
- Field goes as the square root of delivered power through the chamber
  calibration factor, which bundles the antenna, the separation and the
  room into one constant. Four times the drive buys twice the field,
  which is why the last few decibels of a level are the expensive ones
  and why an achieved level well above prediction usually means a
  measurement error rather than a generous chamber.
- Reconciling the achieved field against the field the power predicts is
  the only internal check the report carries. A point that fails it is
  not a presentation defect: it says the level written into the report is
  not the level the unit saw, and the reader has no way to tell which of
  the two numbers is wrong.
- Every point has to reach the reader somehow. A table and a graph are
  alternatives, not a hierarchy, and a run may be split across both; what
  is not allowed is a frequency that was driven, recorded, and then left
  out of both exhibits.
- A graph is only readable with named axes and the right frequency scale.
  Once the span passes a decade, a linear axis compresses the bottom of
  the range into the left-hand edge, where a susceptibility at the low
  end becomes impossible to read off.
- Heavy reflection at a frequency is a limitation worth recording rather
  than a defect: the level was reached, but the drive margin there is
  thin and a retest at a higher level may not be achievable.

## Workflow

1. Normalize the reported points: every required field present and
   numeric, positive frequency, positive forward power and achieved
   field, non-negative reflection, no frequency reported twice.
2. Validate the exhibits: a table is a list of frequencies, a graph needs
   both axis labels, a recognized frequency scale and the frequencies it
   plots. Reject an invented field rather than ignoring it.
3. For each point compute the net power delivered, the field that power
   predicts through the chamber factor, and the signed decibel distance
   of the achieved field from it.
4. Grade that distance on magnitude against the reconciliation tolerance,
   absorbing representation error at the tolerance edge only.
5. Check each point appears in the table or on the graph, matching
   frequencies within a named relative tolerance.
6. Categorize each point as reportable, unpresented or irreconcilable,
   and count the categories.
7. Check the frequency axis scale against the span the points cover.
8. Report the verdict with its findings (unpresented points,
   irreconcilable levels, no exhibit at all, a wide span on a linear
   axis) and its limitations (points driven against heavy reflection).

## Pitfalls

- Reporting the achieved field and leaving the generator setting and the
  forward power out, so nothing in the record can be reconstructed and a
  retest cannot be set up from the report.
- Taking the forward power reading as the power delivered. The reflected
  reading is there precisely because the two differ, sometimes by most of
  the drive.
- Presenting the levels only as a graph with unlabelled axes, which looks
  complete and carries no readable value at any frequency.
- Plotting a span of several decades on a linear frequency axis, so the
  first decade is a few pixels wide.
- Treating a field far above the predicted one as a well-performing
  chamber. It is much more often a probe reading the wrong range or a
  calibration factor applied twice.
- Silently dropping a frequency that was driven but not plotted, which
  leaves a hole no reader can see because nothing marks it.

## Behavior contract (gate 3)

The point-record normalization, net-power computation, predicted-field
derivation, decibel discrepancy grading, table and graph validation,
axis-scale adequacy check, point categorization and report aggregation
are exercised by the gate 3 contract test:
scripts/test_e2007_radiated_electric_susceptibility_reporting.py against
scripts/e2007_radiated_electric_susceptibility_reporting_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_susceptibility_reporting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
