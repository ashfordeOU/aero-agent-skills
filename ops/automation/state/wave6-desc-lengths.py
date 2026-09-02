#!/usr/bin/env python3
import pathlib, yaml
for name in ['aerodynamics', 'flight-mechanics', 'gnc-autonomy', 'structures', 'vehicle-design']:
    p = pathlib.Path(f'<AEROSKILLS-ROOT>/skills/{name}/SKILL.md')
    fm = yaml.safe_load(p.read_text(encoding='utf-8').split('---', 2)[1])
    d = fm.get('description', '')
    print(f"{name}: desc {len(d)} chars, {len(d.split())} words")
