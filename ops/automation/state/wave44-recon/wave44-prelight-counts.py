#!/usr/bin/env python3
"""Wave-44 pre-flight: baseline counts at HEAD (leaf-only, families, corpus, ledger)."""
import os, re, glob
from collections import Counter

os.chdir(os.path.expanduser('~/AeroSkills'))

all_sk = sorted(glob.glob('skills/**/SKILL.md', recursive=True))
routers = sorted(glob.glob('skills/*/SKILL.md'))
leaves = [p for p in all_sk if p not in routers]
print('total SKILL.md:', len(all_sk), '| routers:', len(routers), '| leaves:', len(leaves))

fam_counts = Counter()
for p in leaves:
    fam_counts[p.split('/')[1]] += 1
total = 0
for fam, n in sorted(fam_counts.items()):
    print(f'  {fam}: {n}')
    total += n
print('family leaf total:', total)

with open('eval/skill-ratings.md') as f:
    lines = f.read().splitlines()
rows = [l for l in lines if re.match(r'^\|\s*\d+\s*\|', l)]
print('ledger rows (physical):', len(rows))
for l in lines:
    if 'Total skills rated:' in l:
        print(l.strip())

with open('eval/hit1-corpus.yaml') as f:
    content = f.read()
print('corpus "- id:" occurrences:', content.count('- id:'))

em = 0
for root, dirs, files in os.walk('skills'):
    for fn in files:
        if fn.endswith('.md'):
            with open(os.path.join(root, fn), encoding='utf-8', errors='replace') as fh:
                em += fh.read().count('\u2014')
print('em dashes in skills/:', em)
