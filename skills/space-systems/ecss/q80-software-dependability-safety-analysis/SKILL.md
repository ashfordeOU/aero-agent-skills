---
name: q80-software-dependability-safety-analysis
description: "Perform and audit the software dependability and safety analysis of ECSS-Q-ST-80C Rev.2: grade a software FMEA worksheet for missing effects, unmitigated severe failure modes and mitigations with no requirement, raise components to the strictest category when failures can cross an unsegregated link or shared resource, check the hardware-software interaction analysis (HSIA) for hardware failures with no software requirement or no passing verification, track analysis recommendations and export the system-level ones, and propose critical item list candidates. Use when a supplier prepares the software dependability and safety analysis report or a customer reviews one. Trigger: software-fmea, sfmea, hsia, software-failure-propagation, software-critical-item-list, q80-dependability-safety-analysis."
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
  tags: [ecss, q-st-80c, q80-software-dependability-safety-analysis, q80-dependability-safety-analysis, software-fmea, sfmea, hsia, software-failure-propagation, software-critical-item-list]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Dependability and Safety Analysis (space-systems/ecss/q80-software-dependability-safety-analysis)

Use when the task is the software share of the dependability and safety
work under ECSS-Q-ST-80C Rev.2 (30 April 2025): clause 6.2.2, where the
system analyses hand down a criticality and the software analysis hands
back component categories, extra failure modes and recommendations, and
clause 5.3.2, where the results feed the critical item list. The category
of the software product as a whole and the tailoring that follows from it
belong to `q80-software-criticality-tailoring`; this skill works one level
down, component by component.

## Domain quick reference

- The analysis runs both ways. It starts from the system-level
  dependability and safety results and ends by returning new failure modes
  found at design level and recommendations for the system (a hardware
  inhibit, an architecture change) so the system analysis can absorb them.
- The methods are agreed with the customer rather than chosen alone. A
  software failure modes and effects analysis, a software fault tree and a
  common cause analysis are the usual set; the worksheet is only as good as
  the effect and severity each row states.
- Severity maps to a category when no compensating provision exists:
  catastrophic to A, critical to B, major to C, minor to D.
- A lower-category component that can bring down a higher one, through a
  failure that propagates or a resource both use, takes the higher
  category unless segregation or partitioning is shown to stop it.
- The hardware-software interaction analysis (HSIA) is answered from the
  software side: for each hardware failure it lists, a software
  requirement says how the software must react, and verification shows it
  does.
- The report is first owed at the preliminary design review (PDR) and is
  updated at the critical design review (CDR), qualification review (QR)
  and acceptance review (AR) to confirm the component categories and the
  status of each recommendation.

## Workflow

1. Collect the system-level severities and the agreed analysis methods.
2. Grade the software FMEA worksheet with `grade_sfmea`; resolve every
   unmitigated severity I or II row before going further.
3. List the interactions between components (calls, shared memory,
   processor time, buses) and run `propagate_criticality`, marking only
   those links a segregation argument really closes as prevented.
4. Check the HSIA mapping and its verification results with
   `check_hsia_coverage`.
5. Update the recommendation log with `track_recommendations` for the
   coming review and pass the system-level items upward.
6. Check the report history with `check_analysis_currency`.
7. Draft the critical item list proposals with `critical_item_candidates`
   and send the whole package to the reviewer as a draft.

## Pitfalls

- Treating the software FMEA as a one-off at PDR. Categories are
  confirmed at every later review; a stale report re-issued unchanged is
  not an update.
- Calling a link prevented because the components are in different
  files. Only a hardware split, process isolation or a real partitioning
  mechanism stops a failure crossing.
- Answering an HSIA row with a requirement that was never verified, or
  was verified on a platform without the failure injected.
- Keeping system-level recommendations inside the software report where
  the system analyst never sees them.
- Lowering a category to avoid obligations without a compensating
  provision that meets the system standard's conditions.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- A component criticality category, raised or lowered.
- A statement that a failure propagation path is prevented.
- The software dependability and safety analysis report or a critical item
  list entry sent to the customer.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The severity normalisation, the FMEA worksheet grading, the criticality
propagation over unprevented links, the HSIA coverage check, the
recommendation tracking, the report currency check and the critical item
proposals are exercised by the gate 3 contract test:
scripts/test_q80_software_dependability_safety_analysis.py against
scripts/q80_software_dependability_safety_analysis_logic.py (stdlib
unittest, offline).
Run: python3 scripts/test_q80_software_dependability_safety_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
