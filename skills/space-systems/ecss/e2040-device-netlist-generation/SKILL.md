---
name: e2040-device-netlist-generation
description: "Generate the synthesised netlist ECSS-E-ST-20-40C clause 5.5.2 puts at the head of detailed design, together with the record that lets the run be repeated: pin every source and constraint file to a revision, pin the synthesis tool and the technology library to a version, name the netlist and the reports the run wrote, report every cell the run left unresolved, weigh each resource used against the budget while letting a figure landing exactly on the budget stay inside it, and demand a disposition on each warning in a category that blocks. Use when a synthesis run is set up, repeated or documented. Trigger: ecss, e-st-20-electrical-scope, device-netlist-generation, synthesis-run-reproducibility, technology-library-pinning, netlist-resource-utilisation, unresolved-netlist-cell."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-netlist-generation, device-netlist-generation, synthesis-run-reproducibility, technology-library-pinning, netlist-resource-utilisation, unresolved-netlist-cell, synthesis-warning-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Netlist Generation (space-systems/ecss/e2040-device-netlist-generation)

Use when the task is the first detailed design duty of
ECSS-E-ST-20-40C clause 5.5.2 -- producing the synthesised netlist and
the record that goes with it, and saying whether that record is enough
for somebody else to obtain the same netlist from the same inputs.

## Domain quick reference

- The netlist is an output, and on its own it is not evidence of
  anything. What makes it usable downstream is the record of what went
  in: the sources, the constraints, the tool and the technology
  library, each pinned to a revision or a version.
- A run missing any one pin is not reproducible, and the gap is
  invisible at the time. The netlist is there, it looks right, and the
  fact that nobody can say which library version produced it only
  surfaces when a second run gives different timing.
- The technology library is the pin most often left off, because it
  feels like part of the tool rather than part of the design. It is
  not: a library revision changes cell timing, and the same sources
  through the same tool then produce a netlist that behaves
  differently.
- A run with no constraints completes. It produces a netlist nobody
  can use, because the tool optimised against nothing, so an empty
  constraint set is a finding rather than a permitted case.
- Utilisation is a ratio of what a resource used to what the device
  has. A figure landing exactly on the budget is inside it, so the
  comparison absorbs representation error: a computed two-thirds
  landing on a two-thirds budget is a pass, and a strict comparison is
  what fails a design that exactly fits.
- Unresolved cells and undispositioned warnings both survive into the
  next phase. A cell the run could not bind is a hole in the netlist;
  a blocking warning nobody answered is a decision deferred to
  whoever reads the log next, which is usually nobody.

## Workflow

1. Resolve the run record: sources, constraints, tool, technology
   library, outputs, utilisation figures, unresolved cells and
   warnings. Refuse a repeated identifier or an unknown key as an
   input defect.
2. Report each source or constraint file carrying no revision, and the
   tool or library carrying no version.
3. Report a run whose constraint set is empty.
4. Report a run that named no netlist output, and one that named no
   report.
5. Report every cell the run left unresolved, naming it.
6. Compute each resource utilisation as a ratio and compare it against
   its budget, treating a figure on the budget as inside and reporting
   only a genuine excursion.
7. Report every warning in a blocking category carrying no
   disposition, and derive whether the run as a whole is reproducible.

## Pitfalls

- Treating the netlist as the deliverable. Without the pins the
  netlist is a one-off artefact, and the next run is a new design
  rather than a repeat.
- Leaving the technology library unpinned because the tool is pinned.
  The library sets the cell timing, so the same sources and the same
  tool can still produce a netlist that behaves differently.
- Running without constraints because the run completes. The tool
  optimised against nothing, and the result reads as a successful
  synthesis in every log the project keeps.
- Failing a resource that lands exactly on its budget. A computed
  two-thirds against a two-thirds budget can sit a unit in the last
  place above it and reject a design that exactly fits.
- Carrying warnings forward with no disposition. They are grouped by
  category precisely so the blocking ones get an answer, and an
  unanswered one becomes a defect found during netlist verification
  instead.

## Behavior contract (gate 3)

The run resolution, source and constraint pinning, tool and library
version checks, output recording, unresolved-cell reporting, the
utilisation-against-budget comparison with exact landings inside, the
warning-disposition check and the reproducibility verdict are
exercised by the gate 3 contract test:
scripts/test_e2040_device_netlist_generation.py against
scripts/e2040_device_netlist_generation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_netlist_generation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
