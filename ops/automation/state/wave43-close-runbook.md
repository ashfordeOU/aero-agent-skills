# Wave-43 close-out runbook (ops manager internal checklist)

Order of operations at close, per wave-43 brief sections 8-12 and prior
wave precedent (wave-42 close commits + reconciliation doctrine).

## 0. Preconditions (verify before close)
- >=10 leaves landed, each with own commit on HEAD chain; quiet gate green.
- git status --short: only expected files (state docs/specs, fragments
  eval/hit1-wave43-*.yaml, or clean).
- Every leaf's six artifacts + ledger row verified on the HEAD chain; ledger
  rows contiguous; physical row order normalized ascending (wave-39/40/41/42
  lesson: RMW race scrambles rows; re-add lost rows immediately).

## 1. Pre-merge routing simulation (wave-32 lesson - run BEFORE merge)
python3 ops/automation/state/wave43-sim-merge.py
Expect: SIM PASS: N tasks Hit@1, zero pre-existing task thefts.
If FAIL lines name pre-existing tasks -> reword corpus tasks ONLY on the
wave-31 pn1 precedent (carry incumbent leaf's hyphenated tags), disclose.

## 2. Corpus merge (1178 -> 1178+2N)
python3 ops/automation/state/wave43-merge-corpus.py
- merges eval/hit1-wave43-*.yaml fragments, deletes them (0 on disk).
- verify: grep -c '^  - id:' eval/hit1-corpus.yaml == 1178+2N.

## 3. Family routers parent-side (one table row + one routing bullet per
leaf; router description stays <=1024 chars - wave16-router-desc-len.py)
- rows == leaves per family (parity).
- update the family table + Routing guidance bullets by hand/patch.
- then: python3 ops/automation/state/wave16-router-desc-len.py PASS

## 4. Ratings header 581 -> 581+N (rows 582+ appended by builders at
creation - verify every new leaf path appears exactly once in ledger)
- update "Total skills rated:" line at close.
- normalize physical ledger row order to ascending before header update
  (wave-39 lesson #3).

## 5. Visuals + manifests (numbers ONLY via make)
make visuals
make visuals-check  -> PASS (artifacts fresh)
(make manifest-check runs inside visuals-check)

## 6. Gates FRESH at rest
make validate   (5/5, 1178+2N Hit@1)
make attest     (3/3)
make completeness (ALL REQUIRED PASS)
make value-delta (10/10 >= 0.2)
visuals-check PASS
python3 ops/automation/state/wave16-router-desc-len.py PASS
em dash sweep: git grep -l the U+2014 char in skills/ -> report REAL COUNT
(0 preferred)
git status --short clean (tree clean)
ops/automation/stale-number-guard.sh PASS (stale-number guard G7) OR
./ops/automation/test/run-tests.sh ALL PASS (includes G7)

## 7. Commit close (explicit paths only)
- commit message: "ops: wave-43 close (N leaves, corpus 1178+2N)"
- delete fragments commit separate if any remain.

## 8. Push PRIVATE (arjun token, fast-forward, no force)
BACKGROUND process with notify-on-complete (pre-push hook battery can exceed
180s foreground timeout - wave-40/41/42 lesson). If the pre-push hook blocks:
root-cause the failing gate FIRST (loop standalone validate, grep the failing
test file), fix structurally, purge __pycache__, verify under BOTH
interpreters (python3 = /usr/bin 3.9.6 vs ~/.pyenv/versions/3.13.12/bin/python3),
THEN retry - never blind-retry (wave-41/42 exact-float lesson).
git push origin main
git ls-remote origin main  -> MUST equal local HEAD.
No Ashforde token on private repo, no visibility flip.

## 9. publish-public.sh sanctioned sync
bash ops/automation/publish-public.sh   (keeps 2da34f0e + eec11e34 + 4819dc97 fixes)
- verify public HEAD (ashfordeOU/aero-agent-skills) == expected sync commit
  (note: hourly automation may have raced ahead - record the ACTUAL public
  commit per wave-42 lesson)
- GitHub CI attest SUCCESS for the sync commit (via gh).

## 10. GROUP 160 close-out post
env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160 "..."
-> capture exit code, verify SEND_EXIT=0.

## 11. wave43-state.md honest close + commit + push PRIVATE.

## 12. Final close-out report (text-only OK now).
