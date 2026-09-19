---
name: e7041-summary-report-the-content-of-a-repository
description: "Generate the shallow content summary an on-board repository returns under ECSS-E-ST-70-41C clause 6.23.4.6 and judge what it does not cover. Use when a repository listing is about to be acted on and the counts have to mean the right thing: naming each immediate object with its type only, keeping the direct file count and octet total apart from the branch totals so a parent's summary is never read as its whole subtree, listing a sub-repository without a size because it has none of its own, and reporting a truncated listing while the counts still span every object held. Trigger: ecss, e-st-70-41c, pus-file-management, repository-summary-report, on-board-repository-listing, direct-versus-branch-octets, truncated-summary-listing, empty-repository-outcome."
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
  tags: [ecss, e-st-70-41-file-management-scope, e7041-summary-report-the-content-of-a-repository, repository-summary-report, on-board-repository-listing, direct-versus-branch-octets, truncated-summary-listing, empty-repository-outcome]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Summary-Report the Content of a Repository (space-systems/ecss/e7041-summary-report-the-content-of-a-repository)

Use when the task is the summary report of ECSS-E-ST-70-41C clause
6.23.4.6 -- the ground names one repository, the on-board file
management service answers with what it directly holds, and the reply
has to be read for its depth as well as its content.

## Domain quick reference

- The summary is thinner than an attribute report on purpose. Each
  object gets a name and a type, nothing more, so a repository with
  many objects still fits one reply. Lock state and creation time
  belong to the attribute request, not here.
- It is one level deep. The listing names the immediate children and
  stops; it never walks into a sub-repository. The count it gives for
  a parent is objects one level down, not files in the branch.
- That is the reading error the report invites. "Four objects" in a
  parent whose branch holds two hundred files is the right number to
  the wrong question, so the direct and branch totals are worth
  carrying side by side rather than leaving one to be inferred.
- A sub-repository entry carries no size. It has none of its own --
  its content belongs to it, not to its parent -- and stamping a
  number there is how a branch total leaks into a direct one.
- The reply is bounded like every telemetry report. Past the entry
  capacity the listing is truncated, but the counts are computed over
  everything held, so a truncated report still answers "how many".
- Empty is a real answer, distinct from a failed request. A
  repository that was found and holds nothing is the one that can be
  deleted as it stands; an unknown path never got that far.
- Direct octets decide the downlink. Whether the repository fits one
  pass is a question about what it holds itself, not its branch.
- Ordering is part of the contract, so two summaries of an unchanged
  repository are comparable and a diff between them is a change.

## Workflow

1. Normalise the repository path and validate the tree: every
   non-root repository has its parent present, no duplicate file
   name, no negative size.
2. Resolve the path. Absent, answer with the failure code rather than
   an empty summary -- they are different facts.
3. Collect the immediate children: each file as a file entry with its
   size, each direct sub-repository as a repository entry with none.
4. Sort the entries by type then name so the listing is stable.
5. Count files and sub-repositories separately, and the objects as
   their sum, over everything held rather than over the listing.
6. Total the direct octets, and separately walk the branch for the
   branch octets and branch file count.
7. Cut the listing at the entry capacity, report the omitted count,
   and mark the report authoritative only when nothing was omitted.
8. Flag the summary as shallow whenever the branch totals exceed the
   direct ones, and say by how much.

## Pitfalls

- Reading a parent's object count as its branch content. The number
  is one level deep and the branch can be orders larger.
- Giving a sub-repository entry a size. Either it is wrong or it is a
  branch total in a field that means direct octets.
- Dropping the counts when the listing truncates. The report then
  answers neither "what is in here" nor "how much".
- Recursing to make the summary complete. A recursive listing is a
  different, far larger request and will truncate on real content.
- Reporting an unknown repository as an empty one. One is deletable
  as it stands, the other is an addressing mistake.
- Sizing a downlink from the branch total. The pass has to carry what
  this repository itself holds.
- Leaving the listing order to the underlying storage, so two
  identical summaries diff against each other.

## Behavior contract (gate 3)

The path and tree validation, immediate-child collection, the typed
entries with a sizeless sub-repository, deterministic ordering, the
separate file, sub-repository and object counts, direct versus branch
octets and branch file count, the complete, truncated, empty and
unknown-repository outcomes with the omitted count, the shallowness
flag and the deletable-as-is verdict are exercised by the gate 3
contract test:
scripts/test_e7041_summary_report_the_content_of_a_repository.py
against
scripts/e7041_summary_report_the_content_of_a_repository_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_summary_report_the_content_of_a_repository.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
