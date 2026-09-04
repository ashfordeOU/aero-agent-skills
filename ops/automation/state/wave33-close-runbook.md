# Wave-33 close-out runbook (ops manager internal checklist)

Order of operations at close, per wave-33 brief sections 8-12 and prior
wave precedent (wave-32 close commits af259075 + 13eb66c6).

## 0. Preconditions (verify before close)
- >=10 leaves landed, each with own commit on HEAD chain; quiet gate green.
- git status --short: only expected files (state docs/specs or clean).

## 1. Pre-merge routing simulation (wave-32 lesson - run BEFORE merge)
python3 ops/automation/state/wave33-sim-merge.py
Expect: SIM PASS: N tasks Hit@1, zero pre-existing task thefts.
If FAIL lines name pre-existing tasks -> reword corpus tasks ONLY on the
wave-31 pn1 precedent (carry incumbent leaf's hyphenated tags), disclose.

## 2. Corpus merge (898 -> 898+2N)
python3 ops/automation/state/wave33-merge-corpus.py
- merges eval/hit1-wave33-*.yaml fragments, deletes them (0 on disk).
- verify: grep -c '^  - id:' eval/hit1-corpus.yaml == 898+2N.

## 3. Family routers parent-side (one table row + one routing bullet per
leaf; router description stays <=1024 chars - wave16-router-desc-len.py)
- rows == leaves per family (parity).
- update the family table + Routing guidance bullets by hand/patch.
- then: python3 ops/automation/state/wave16-router-desc-len.py PASS

## 4. Ratings header 442 -> 442+N (rows 443+ appended by builders at
creation - verify every new leaf path appears exactly once in ledger)
- update "Total skills rated:" line at close.

## 5. Visuals + manifests (numbers ONLY via make)
make visuals
make visuals-check  -> PASS (19 artifacts fresh)
make manifest-check (gen_manifest --check inside visuals-check)

## 6. Gates FRESH at rest
make validate   (5/5, 898+2N Hit@1)
make attest     (3/3)
make completeness (ALL REQUIRED PASS)
make value-delta (10/10 >= 0.2)
visuals-check PASS
python3 ops/automation/state/wave16-router-desc-len.py PASS
em dash sweep: grep for U+2014 in skills/ -> 0
git status --short clean (tree clean)
./ops/automation/test/run-tests.sh ALL PASS (stale-number guard G7)

## 7. Commit close (explicit paths only)
- commit message: "ops: wave-33 close (N leaves, corpus 898+2N)"
- delete fragments commit separate if any remain.

## 8. Push PRIVATE (arjun token, fast-forward, no force)
git push origin main
git ls-remote origin main  -> MUST equal local HEAD.
No Ashforde token on private repo, no visibility flip.

## 9. publish-public.sh sanctioned sync
bash ops/automation/publish-public.sh   (keeps 2da34f0e + eec11e34 fixes)
- verify public HEAD (ashfordeOU/aero-agent-skills) == expected sync commit
- GitHub CI attest SUCCESS for the sync commit (via gh, arjun token NOT
  needed for public? publish script handles; check API).

## 10. GROUP 160 close-out post
env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160 "..." 
-> capture exit code, verify SEND_EXIT=0.

## 11. wave33-state.md honest close + commit + push PRIVATE.

## 12. Final close-out report (text-only OK now).
