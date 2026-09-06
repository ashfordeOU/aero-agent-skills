# Why: release & publish machinery (read before releases/pushes)

## Release convention (founder 2026-09-03)

Every 100 new skills = one minor version bump. v1.0.0 = 1-100 ...
v1.3.0 = 301-400. Tag v1.x.0 fires GitHub Release (release-on-milestone
workflow) + npm (publish-npm on v*.0 tags). JetBrains needs a jb-v*
tag (blocked while marketplace review of 1.0.0 is pending — 2026-09-04).

## Boundary-skip bug (fixed 2026-09-03, do not regress)

Wave-29 jumped 393 → 404 in one push; the old milestone check held for
the current band end (500) and silently skipped v1.3.0 (400 crossed).
Fix: the workflow finds the LOWEST missing band tag whose boundary the
count has crossed, so skipped bands release one at a time.

## Rejected approaches / failure causes

- **Release notes with internal detail** — REJECTED (founder
  correction 2026-09-03). No wave numbers, no "cut manually", no
  process post-mortems in public text. Public notes: what shipped +
  install + verify only.
- **publish-public "no-op" misfires** — when the mirror at
  ~/Code/.aero-agent-skills-public-mirror has uncommitted export
  changes. Fix: commit the mirror + push directly.
- **Fighting the live wave tree** — waves commit every few minutes;
  full gate runs on a moving tree time out/block. For docs/workflow
  fixes use the GitHub contents API or commit+push when tree is at
  rest. Don't fight visuals-check drift during a wave.
- **Leaf quality defects** — see RULINGS-equivalent: run
  scripts/leaf-create-gate.sh before ANY leaf commit (Pitfalls +
  Behavior contract gate 3 structure, no test_-prefixed logic files,
  no "classified" as a verb).
- **Content-policy sweep trips on docs quoting red-flag terms** —
  definitional docs (MAINTENANCE_AND_HANDOVER) are exempted in
  ops/automation/content-policy-sweep.sh meta_doc_exempt.
