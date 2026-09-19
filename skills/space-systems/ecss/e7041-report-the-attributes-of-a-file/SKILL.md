---
name: e7041-report-the-attributes-of-a-file
description: "Produce the attribute report an on-board file management service returns for one named file under ECSS-E-ST-70-41C clause 6.23.4.2. Use when a ground request asks what a file is and the answer has to keep a missing repository, a missing file and a name that is really a sub-repository apart: normalising the repository path, refusing each of the three cases with its own code, reporting size in octets, lock state and whether an uplink or downlink still holds the file open, and deriving from those whether a delete or an overwrite issued now would be accepted while a read still would. Trigger: ecss, e-st-70-41c, pus-file-management, report-file-attributes-request, on-board-repository-path, file-lock-state, file-transfer-in-progress, file-attribute-failure-code."
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
  tags: [ecss, e-st-70-41-file-management-scope, e7041-report-the-attributes-of-a-file, report-file-attributes-request, on-board-repository-path, file-lock-state, file-transfer-in-progress, file-attribute-failure-code]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Report the Attributes of a File (space-systems/ecss/e7041-report-the-attributes-of-a-file)

Use when the task is the attribute request of ECSS-E-ST-70-41C clause
6.23.4.2 -- the ground names one file by the repository holding it and
the name it has inside that repository, and the on-board file
management service answers with what it knows about that file.

## Domain quick reference

- A file is addressed by two things, never one: a repository path and
  a name within that repository. The same name in two repositories is
  two different files, and a request that carries only the name is
  under-specified rather than ambiguous.
- The report carries the size in octets, whether the file is locked
  against change, and whether an on-board transfer currently holds it
  open. Everything an operator actually asks for is derived from those
  three, not read off separately.
- A request can fail three different ways and they are not
  interchangeable. The repository path names nothing: an addressing
  mistake on the ground. The repository exists but holds no such file:
  usually a file already deleted or never produced. The name given as
  a file is a sub-repository: an operator asking a directory for a
  size. Each sends the investigation somewhere different.
- Size is the downlink question. It decides whether the file fits the
  budget for the pass, so an attribute request is usually the step
  before a downlink request, not an end in itself.
- Lock state and open-transfer state together answer the delete
  question. Either one alone is enough to refuse a delete, a rename or
  an overwrite, and they are independent: a file can be unlocked and
  still held, or locked and idle.
- Reading is not blocked by either. A locked file is still
  downlinkable and a file being written can still be read. Treating
  the lock as a general no-access flag is the common inversion.
- Path spelling is not identity. A leading or trailing separator, or a
  doubled one, is a spelling of the same path, so normalise before
  comparing or two spellings of one repository look like two.

## Workflow

1. Normalise the repository path: strip the outer separators, reject
   an empty inner segment and a relative marker, validate each segment
   as a name, and enforce the path and name octet caps.
2. Resolve the repository. Absent, answer with the repository failure
   code and stop -- do not fall through to a file search.
3. Check the name against the sub-repository list before the file
   list, so a directory asked for its size gets the third code rather
   than the file-not-found one.
4. Find the file record. Absent, answer with the file failure code.
5. Report size, lock state, transfer state and creation time as held.
6. Derive the permissions: deletable, overwritable and renameable all
   require unlocked and idle; readable is unconditional.
7. For a request set, group the failures by code, total the octets of
   only the successful answers, and count the locked and held files.

## Pitfalls

- Collapsing the three failures into one "not found". The operator
  then cannot tell a mistyped repository from a deleted file.
- Searching the file list before the sub-repository list. A directory
  asked for its attributes reports as a missing file, and the sizing
  mistake behind the request is never seen.
- Reading the lock as no-access. It blocks change, not retrieval, so a
  locked file is still the one to downlink.
- Ignoring the open transfer because the file is unlocked. A file
  being uplinked right now is as undeletable as a locked one.
- Totalling the octets of a batch without dropping the failed answers.
  The downlink budget then counts files that were never found.
- Comparing raw path strings. Two spellings of one repository path
  become two repositories and half the requests fail.

## Behavior contract (gate 3)

The name and path validation, the three distinct failure codes, the
sub-repository-before-file resolution order, the derived delete,
overwrite, rename and read permissions, the batch ordering and the
per-code failure summary are exercised by the gate 3 contract test:
scripts/test_e7041_report_the_attributes_of_a_file.py against
scripts/e7041_report_the_attributes_of_a_file_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_report_the_attributes_of_a_file.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
