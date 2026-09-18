---
name: e7041-forwarding-control-processing-logic
description: "Determine what a service 14 subservice forwards to the real-time downlink under ECSS-E-ST-70-41C clause 6.14.3.3: take each generated report against the forward-control store, apply the enable state of its application process, hold a per-definition subsampling counter so only every nth matching report goes out, and give every report a disposition and a named reason whether it is forwarded or left to on-board storage. Use when the forwarding decision of a service 14 subservice, its subsampling or its enable state behaviour is being designed or reviewed. Refuses a subsampling rate below one. Trigger: ecss, e-st-70-41c, pus-service-14, real-time-forward-routing-decision, report-forward-disposition, forward-subsampling-counter, forwarding-enable-state, storage-only-report."
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
  tags: [ecss, e-st-70-41c, pus-service-14, e7041-forwarding-control-processing-logic, real-time-forward-routing-decision, report-forward-disposition, forward-subsampling-counter, forwarding-enable-state, storage-only-report]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Real-Time Forwarding Control — Processing Logic (space-systems/ecss/e7041-forwarding-control-processing-logic)

Use when the task is the forwarding control processing logic of
ECSS-E-ST-70-41C clause 6.14.3.3 — the decision the service 14 subservice
takes on every report the on-board software generates: forward it to the
real-time downlink now, or leave it to the storage and dump services.

## Domain quick reference

- The decision is taken once, when the report is generated, against the
  forward-control store as it stands at that instant. A definition added a
  moment later does not retrieve a report that has already been dispositioned.
- Not forwarded is not discarded. A report the store does not cover is still
  a report; it goes to on-board storage, and describing the outcome as a
  disposition rather than a pass or fail is what keeps that visible.
- The enable state of an application process sits above the definitions. A
  disabled application process forwards nothing even where the store covers
  it wholesale, and the definitions it holds stay in place for when it is
  enabled again.
- Subsampling is counted per definition, not per report stream. A rate of n
  forwards the first matching report and then every nth after it, so two
  definitions matching the same report type advance independently and a
  shared counter would silently thin one of them.
- A rate of one is the ordinary case and forwards everything that matches. A
  rate below one is not a rate at all and is a configuration error rather
  than a request to forward nothing.
- The reason attached to a decision carries the diagnostic value. Knowing
  that a report was subsampled out is a different investigation from knowing
  that no definition covered it or that its application process was disabled.

## Workflow

1. Validate the configuration: the forward-control store as a three-level
   structure, the set of enabled application processes, and every declared
   subsampling rate as a whole number of at least one.
2. Validate each report as it arrives: an application process, a service
   type and a message subtype, all present and of the right kind.
3. Resolve the widest definition in the store that covers the report,
   walking application process level, then service type level, then message
   subtype level, and remember which level matched because that is the
   counter key.
4. Where nothing covers the report, dispose of it to storage with the reason
   that no definition covered it, and move on without touching any counter.
5. Where the application process is disabled, dispose of it to storage with
   the enable-state reason, again without advancing a counter, so that
   enabling the application process later does not start mid-cycle.
6. Otherwise advance the counter for the matched definition and forward the
   report when the counter is at a multiple of the rate, starting with the
   first matching report; dispose of the others to storage as subsampled out.
7. Report every decision with its disposition and reason, the per-application
   process tallies and the final counter state.

## Pitfalls

- Reading a report that is not forwarded as a report that is lost. The
  storage path is still open, and treating the two as the same hides the
  difference between a thinned downlink and a missing report.
- Sharing one subsampling counter across definitions that match the same
  report. The two definitions then thin each other and the effective rate is
  neither of the two that were configured.
- Advancing the counter for a report that was never eligible. A disabled
  application process or an uncovered report has to leave the counter alone,
  or the first report after the application process is enabled lands at an
  arbitrary point in the cycle.
- Applying the enable state below the definitions. A wholesale definition
  would then forward from a disabled application process, which is exactly
  the case the enable state exists to stop.
- Returning only a boolean. The reason is what makes a thin downlink
  diagnosable, and a decision without one costs a pass through the
  configuration to reconstruct.

## Behavior contract (gate 3)

The configuration validation, report validation, widest-definition
resolution, enable-state precedence, per-definition subsampling counters,
disposition and reason assignment and the assembled stream assessment are
exercised by the gate 3 contract test:
scripts/test_e7041_forwarding_control_processing_logic.py against
scripts/e7041_forwarding_control_processing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_forwarding_control_processing_logic.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
