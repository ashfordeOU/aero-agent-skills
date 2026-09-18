---
name: e2007-emission-data-presentation
description: "Evaluate the automatic amplitude-versus-frequency presentation an emission test must display while it runs, under ECSS-E-ST-20-07C clause 5.2.9.4. Use when a facility plotting chain is configured or reviewed: confirm the plot is produced with no operator action and appears during the run rather than afterwards, check the axes really carry amplitude against frequency in recognized units, require the displayed span to cover the declared test band with the applicable limit line overlaid, derive the slowest refresh interval that still shows the sweep progressing, and group the chain as live, deferred or operator-initiated. Trigger: ecss, e-st-20-07c, emission-data-presentation, amplitude-versus-frequency-plot, automatic-plot-generation, live-emission-display, emission-plot-refresh-interval, emission-limit-line-overlay."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-emission-data-presentation, amplitude-versus-frequency-plot, automatic-plot-generation, live-emission-display, emission-plot-refresh-interval, emission-limit-line-overlay]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Emission Data Presentation (space-systems/ecss/e2007-emission-data-presentation)

Use when the task is the data-presentation requirement of
ECSS-E-ST-20-07C clause 5.2.9.4 -- showing that an emission test draws
amplitude against frequency and puts that plot in front of the
operator automatically while the measurement is still running, not as
a report assembled afterwards.

## Domain quick reference

- Two conditions, not one. The plot must be produced without an
  operator asking for it, and it must appear during the run. A chain
  that meets one and not the other is grouped as deferred (automatic
  but after the fact) or operator-initiated (produced only on demand);
  neither satisfies the clause, and the two are worth naming
  separately because the repair is different in each case.
- The reason the clause wants the plot live is operational. An
  emission run that is going wrong -- a mispatched cable, a
  support-equipment carrier, an amplifier oscillating -- is obvious in
  the first seconds of a plot and invisible in a table of numbers. A
  chain that only plots afterwards spends the whole run before anyone
  can see it was wasted.
- The plot has to be the right plot. Amplitude on the vertical axis,
  frequency on the horizontal, in units that belong to those
  quantities. A vertical axis labelled in a frequency unit is not a
  cosmetic slip; it usually means the trace being drawn is not the
  measured amplitude at all.
- The displayed axis span must cover the declared test band. An axis
  that starts above the band start or stops below the band stop hides
  part of the measurement even though the receiver is scanning it, and
  the operator loses exactly the live view the clause is asking for.
- Refresh is a rate requirement derived from the sweep, not a fixed
  number. The display must update several times across one receiver
  sweep for the operator to see the sweep progressing; the slowest
  acceptable interval is the sweep time divided by that update count.
- Display latency is separate from refresh. A plot that arrives later
  than the interval that supersedes it is always showing stale data.
  That degrades the live view without removing it, so it is a
  limitation on the run rather than a finding against the clause, as
  is a missing limit-line overlay.

## Workflow

1. Validate the plotting-chain configuration: the generation and
   timing flags are booleans, the axis quantities and units are
   recognized tokens, the refresh interval is positive, the latency is
   non-negative, and the displayed axis is a real span.
2. Resolve the display mode from the generation and timing flags: live,
   deferred or operator-initiated.
3. Check the axes carry amplitude against frequency, and that each
   axis unit belongs to the quantity on that axis.
4. Compare the displayed axis span with the declared test band and
   report either end that is not shown.
5. Derive the slowest refresh interval from the sweep time and the
   required updates per sweep, then compare the configured interval
   against it and count the updates the operator actually receives.
6. Compare the display latency against the refresh interval.
7. Aggregate: a non-live mode, wrong axes, an uncovered band end or a
   refresh too slow are findings; a missing limit line and a stale
   latency are limitations on an otherwise compliant chain.

## Pitfalls

- Accepting "the system plots automatically" as compliance. Automatic
  generation into a post-run report is exactly the deferred case the
  clause is written against.
- Fixing a refresh interval in seconds and reusing it everywhere. The
  requirement scales with the sweep; an interval that is live on a
  slow sweep shows almost nothing on a fast one.
- Reading the axis labels and stopping there. A frequency unit on the
  amplitude axis is a signal that the wrong trace is being plotted,
  and it will not announce itself any other way.
- Zooming the displayed axis to the interesting part of the band. The
  receiver still scans the whole span, but the operator can no longer
  see the part that was zoomed out of view.
- Treating a missing limit line as a pass/fail item. It does not stop
  the plot being live; it does stop an exceedance being obvious, so
  record it as a limitation rather than failing the chain on it.

## Behavior contract (gate 3)

The configuration validation, display-mode grouping, axis quantity and
unit checks, axis-span shortfall detection, refresh-interval
derivation, update counting, latency currency and the aggregate
verdict are exercised by the gate 3 contract test:
scripts/test_e2007_emission_data_presentation.py against
scripts/e2007_emission_data_presentation_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2007_emission_data_presentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
