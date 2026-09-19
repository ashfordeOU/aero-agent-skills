---
name: e7041-file-access-protection
description: "Assess whether an on-board file operation is permitted against the protection state of its target under ECSS-E-ST-70-41C clause 6.23.4.3. Use when a delete, rename, move, overwrite or copy-destination has been refused and the operator needs to know which guard refused it: separating the deliberate lock, cleared by an unlock command, from a transfer handle that only finishes on its own, keeping read and downlink permitted under both, treating a re-lock as idempotent while reporting an unlock of a file that was never locked, and screening a whole operation plan into the part an unlock clears and the part only waiting clears. Trigger: ecss, e-st-70-41c, pus-file-management, on-board-file-lock, file-unlock-request, file-transfer-handle, destructive-file-operation-refusal, file-operation-plan-screening."
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
  tags: [ecss, e-st-70-41-file-management-scope, e7041-file-access-protection, on-board-file-lock, file-unlock-request, file-transfer-handle, destructive-file-operation-refusal, file-operation-plan-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — File Access Protection (space-systems/ecss/e7041-file-access-protection)

Use when the task is the file protection of ECSS-E-ST-70-41C clause
6.23.4.3 -- the lock that stops an on-board file being destroyed, what
it does and does not stop, and why an operation can still be refused
after the lock has been cleared.

## Domain quick reference

- The lock guards content, not access. It refuses delete, rename,
  move, overwrite and being the destination of a copy. It does not
  refuse a read and it does not refuse a downlink. Reading the lock as
  a general no-access flag is the inversion that leaves a needed file
  undownlinked during the only pass available.
- Two independent guards refuse a destructive operation and they
  compose. The lock is set deliberately and cleared deliberately. A
  transfer handle -- an uplink still writing, a downlink still reading
  -- was set by nobody and clears only when the transfer ends.
- The two states are orthogonal. A file can be unlocked and held, or
  locked and idle, or both, or neither. Four combinations, and only
  the last permits a delete.
- Which guard refused matters more than that one did. The remedy for
  a lock is an unlock command; the remedy for a handle is waiting.
  A report that says only "refused" sends the operator to issue an
  unlock that will not help.
- Locking an already locked file is idempotent and unremarkable.
  Unlocking a file that was not locked is worth reporting: it usually
  means the operator is on the wrong file and now believes a guard is
  cleared that is still set elsewhere.
- Clearing a lock does not release a handle. An unlock followed
  straight by a delete still fails while the transfer runs, and the
  second refusal reads as the unlock not having worked.
- Protection is per file, not per repository. A repository with one
  locked file is not a protected repository; the plan against it is
  partly executable and the split is the useful answer.

## Workflow

1. Validate each file name and each operation token against the known
   sets before deciding anything.
2. Build the protection table: name, lock flag, handle state. Refuse
   a duplicate name outright -- two rows for one file means two
   different answers to the same question.
3. Categorize the operation. Read and downlink are permitted whatever
   the protection state; only the destructive set is decided further.
4. Test the lock first, then the handle, and record both flags even
   when the first already refused, so a doubly guarded file is not
   reported as needing only an unlock.
5. Attach the remedy that matches the guard that refused.
6. For a lock or unlock request, report applied, already-set,
   was-not-locked or unknown-file rather than a bare success flag.
7. For a plan, count what an unlock alone would clear and what only
   waiting would clear, and report the plan executable only when
   nothing was refused.

## Pitfalls

- Blocking a read or a downlink on a locked file. The content is
  exactly what the lock was set to preserve for downlink.
- Reporting one refusal reason for a file that is both locked and
  held. The unlock is issued, the delete fails again, and the second
  failure looks like a fault.
- Treating an unlock of an unlocked file as a silent success. The
  operator walks away believing a guard was cleared.
- Assuming an unlock releases the transfer. Nothing on the ground
  ends an in-progress uplink by clearing a lock.
- Mutating the protection table in place while screening a plan. The
  later verdicts are then decided against a state the plan has not
  actually reached.
- Judging a repository protected or unprotected as a whole. The split
  between the two remedies is per file.

## Behavior contract (gate 3)

The name and operation validation, the destructive-versus-readable
categorization, the lock-then-handle verdict order with both flags
retained, the four lock and unlock outcomes, handle release, the
per-repository protection report and the plan split into unlock-clears
and waiting-clears are exercised by the gate 3 contract test:
scripts/test_e7041_file_access_protection.py against
scripts/e7041_file_access_protection_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e7041_file_access_protection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
