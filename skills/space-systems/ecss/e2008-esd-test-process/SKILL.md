---
name: e2008-esd-test-process
description: "Use when verify that a discharge test on a solar-array coupon was run with the purpose-built instrumentation and defined settings ECSS-E-ST-20-08C clause 5.5.1.5.3 calls for: check the chamber pressure and coupon temperature against the test window, compute the energy stored on the external capacitance at each bias setting and compare it with the required discharge energy, derive the circuit decay constant and the peak arc current the series resistance permits, confirm the transient recorder resolves that decay and the current probe spans that peak, reconcile the discharges recorded against the plan, and reject a run that produced a sustained arc. Trigger: ecss, e-st-20-08c-clause-5-5-1-5-3, solar-array-coupon-discharge-test, external-capacitance-discharge-energy, arc-transient-recorder-resolution, peak-arc-current-probe-range, sustained-arc-rejection, discharge-bias-settings."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-esd-test-process, solar-array-coupon-discharge-test, external-capacitance-discharge-energy, arc-transient-recorder-resolution, peak-arc-current-probe-range, sustained-arc-rejection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coupon Discharge Test Process (space-systems/ecss/e2008-esd-test-process)

Use when the task is the clause 5.5.1.5.3 test process of ECSS-E-ST-20-08C --
judging whether a discharge test carried out on a solar-array coupon was
actually run the way the clause requires: in the right environment, at the
declared bias settings, through a discharge circuit that delivers the
specified energy, and watched by instrumentation purpose-built to capture
the event rather than merely notice it.

## Domain quick reference

- The coupon is a small, representative piece of the array: a handful of
  cells with their real interconnects, coverglasses and substrate. It
  stands in for the flight array, so the test conditions have to be the
  ones the array sees, not the ones the chamber happens to provide.
- The discharge is driven by an external capacitance charged to the bias
  setting, not by the coupon itself. The energy that capacitance holds,
  E = 0.5 * C * V^2, is the quantity the test requirement specifies; the
  bias voltage alone says nothing until the capacitance is known.
- The series resistance sets two things at once: the peak arc current
  I = |V| / R that the circuit can push through the discharge site, and
  the decay constant tau = R * C over which the event dies away. Both are
  instrumentation requirements, not just circuit trivia.
- Purpose-built instrumentation means the transient recorder samples fast
  enough that the decay is reconstructable -- roughly ten samples inside
  one decay constant -- and the current probe range spans the peak the
  circuit can drive. A probe that saturates reports a clipped peak, and a
  clipped peak is indistinguishable from a small one in the record.
- A sustained arc, where the array's own power keeps feeding the discharge
  after the capacitance has emptied, is a different phenomenon from the
  primary transient this test characterises. Its appearance is a reason to
  stop and re-examine the article, not a data point to average in.

## Workflow

1. Validate the coupon (cell count, active area) and the chamber conditions
   the run was carried out in; a pressure above the vacuum ceiling or a
   coupon temperature outside the declared window is a finding against the
   run, not a footnote.
2. For every defined bias setting, compute the stored energy on the external
   capacitance and compare it with the energy the test requirement calls
   for, absorbing floating-point representation error at the boundary with a
   named tolerance rather than by lowering the requirement.
3. Derive the decay constant and the peak arc current of the discharge
   circuit at that setting.
4. Check the instrumentation against both: samples per decay constant for
   the transient recorder, range against peak for the current probe.
5. Reconcile the discharge counts -- planned against required, recorded
   against planned -- so a setting that was defined but under-run is visible
   as a shortfall rather than absorbed into a total.
6. Reject a setting defined twice in the run definition; two entries at one
   bias make the discharge totals ambiguous.
7. Report every setting record, the run totals, and a run-level verdict that
   a sustained-arc observation overrides regardless of the other results.

## Pitfalls

- Reporting the bias voltage as the test level. The coupon sees the energy
  the external capacitance delivers; two runs at the same bias with
  different capacitance are different tests, and only the energy comparison
  catches that.
- Accepting a record from a probe that saturated. An undersized current
  probe returns a peak equal to its own range, which looks like a modest
  discharge; the range must be checked against the current the circuit can
  drive, before the record is read.
- Treating a detected arc as a resolved arc. A recorder that catches the
  event but places only two or three samples across the decay cannot give a
  waveform, so the peak, the duration and the charge transferred are all
  unsupported by that record.
- Averaging a sustained arc into the discharge statistics. It is a
  power-fed event with a different mechanism; folding it into the transient
  population hides both it and the transients.
- Counting discharges across the whole run instead of per setting. A run
  that over-delivers at one bias and under-delivers at another meets the
  total while leaving a required setting uncharacterised.

## Behavior contract (gate 3)

The chamber validation, stored-energy and peak-current computation, decay
constant, recorder and probe adequacy checks, discharge-count reconciliation
and the sustained-arc override are exercised by the gate 3 contract test:
scripts/test_e2008_esd_test_process.py against
scripts/e2008_esd_test_process_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2008_esd_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
