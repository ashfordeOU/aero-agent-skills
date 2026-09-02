# History rewrite 2026-09-02 — name change in commit messages

Founder-directed. `git filter-branch --msg-filter` over all 516 commits on
main: commit messages now say "Aero Agent Skills" / "aero-agent-skills"
instead of the old name. Force-pushed with lease
(`a1839f4 -> 51d5c1f`, old tip preserved locally as branch
`backup-pre-name-rewrite`).

- Message-only rewrite: trees, authorship (ashfordeOU), and dates unchanged.
- Protected strings left as-is: `aeroskills.ee` (the unrelated Tallinn
  workshop named in the clearance note), `aeroskills.png` (founder logo
  source file), and the RENAME commit's own transition line.
- Repo slug renamed the same day: `arjun-0077/aero-agent-skills`
  (old GitHub URLs redirect).

Wave sessions: your clone will see a forced update with no shared tip.
Recovery is the same as the 2026-09-01 identity rewrite — fetch, reset or
cherry-pick your unpushed work onto origin/main, `make visuals`, push
fast-forward.
