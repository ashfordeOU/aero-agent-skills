---
name: e7041-find-files
description: "Execute a wildcard file search across an on-board repository and judge whether its bounded report can be trusted, under ECSS-E-ST-70-41C clause 6.23.4.4. Use when a search came back with a list and the question is what it left out: matching the any-run and single-character wildcards within a name only, keeping recursion into sub-repositories an explicit flag rather than something a pattern can trigger, returning repository path with every name because one name exists in several repositories, and separating a complete report from one truncated against the report capacity with the omitted count stated. Trigger: ecss, e-st-70-41c, pus-file-management, find-files-request, on-board-file-search-wildcard, recursive-repository-search, truncated-search-report, search-report-capacity."
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
  tags: [ecss, e-st-70-41-file-management-scope, e7041-find-files, find-files-request, on-board-file-search-wildcard, recursive-repository-search, truncated-search-report, search-report-capacity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Find Files (space-systems/ecss/e7041-find-files)

Use when the task is the file search of ECSS-E-ST-70-41C clause
6.23.4.4 -- the ground gives a repository and a pattern, the on-board
file management service walks it and reports the files whose names
match, and the reply has to be read for what it does not contain.

## Domain quick reference

- The answer is repository path plus file name, never a bare name.
  The same name exists in several repositories, so a naked list is
  not addressable and the next command against it goes to the wrong
  copy.
- A pattern carries two wildcards: one standing for any run of
  characters including none, one standing for exactly one character.
  Both match within a name and neither crosses a path separator.
- Recursion is a flag, not a pattern effect. No spelling of a pattern
  can widen a search into a sub-repository; only the flag does, and it
  multiplies both the walk and the number of matches.
- The reply is a telemetry report with a capacity. More matches than
  it can carry means a truncated report, and the difference between
  "12 files match" and "12 reported of 340" is the difference between
  deleting a directory and not.
- The omitted count is the useful number. A truncated report is not
  wrong, it is partial, and the count tells the operator whether to
  narrow the pattern or walk the sub-repositories one at a time.
- A pattern of nothing but the any-run wildcard was never narrowed.
  When such a search truncates, the fix is the pattern, not a bigger
  report.
- No match is a third outcome, distinct from a failed search. The
  repository was found and walked and held nothing matching; an
  unknown repository path never got that far.
- Ordering is part of the contract. Sorting by repository path then
  name makes two passes over an unchanged repository comparable, so a
  diff between them is a real change rather than a walk order.

## Workflow

1. Validate the pattern: non-empty, no path separator, within the
   name octet cap. Validate stored names as literals -- a wildcard in
   a stored name is a corrupt directory entry, not a search.
2. Normalise the root repository path and resolve it. Unknown, answer
   with the repository failure code rather than an empty match list.
3. Build the scope: the root alone, or the root plus every repository
   beneath it when recursion is set. Test "beneath" on whole segments
   so a sibling sharing a name prefix is not swept in.
4. Walk each repository in scope and match each name with a
   backtracking wildcard matcher that stays linear over the name.
5. Sort the matches by repository path then file name.
6. Cut the list at the report capacity, and report the total match
   count and the omitted count alongside the entries.
7. Categorize the outcome as complete, truncated or no-match, and
   mark the report authoritative only when nothing was omitted.

## Pitfalls

- Reading a truncated report as the whole answer. Every decision
  taken from it is taken on an unknown fraction of the repository.
- Returning names without their repository. The list looks right and
  the follow-up command addresses a different file.
- Letting a pattern reach into a sub-repository. Recursion then
  happens by accident and the search cost is never budgeted.
- Testing "beneath the root" on a raw string prefix. A sibling whose
  name starts with the root's name is searched too.
- Reporting no match and an unknown repository the same way. One is
  a clean answer, the other never searched anything.
- Raising the report capacity to clear a truncation. The search was
  too wide; a bigger report only moves the wall.
- Leaving the walk order to the underlying storage. Two passes then
  differ for no reason and the diff is noise.

## Behavior contract (gate 3)

The pattern and name validation, the two wildcards with backtracking,
the segment-wise "beneath the root" test, non-recursive versus
recursive scope, repository-path-bearing entries, deterministic
ordering, the complete, truncated, no-match and unknown-repository
outcomes with the omitted count, and the narrow-the-pattern advice are
exercised by the gate 3 contract test: scripts/test_e7041_find_files.py
against scripts/e7041_find_files_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e7041_find_files.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
