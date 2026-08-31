#!/usr/bin/env python3
"""Wave-6 corpus merge: append 2 tasks per wave-6 fragment into hit1-corpus.yaml.

- Reads eval/hit1-wave6-*.yaml fragments (2 tasks each).
- Verifies id uniqueness against the existing corpus (tasks + future_pins).
- Inserts new tasks at the END of the tasks list (before future_pins: block).
- Updates the header with a wave-6 note; keeps all historical notes.
- Deletes the standalone fragments after a successful merge.
- Prints the new task count.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path("/Users/enterprisehq/AeroSkills")
CORPUS = ROOT / "eval" / "hit1-corpus.yaml"

def main():
    text = CORPUS.read_text(encoding="utf-8")

    # split header / tasks / future_pins
    tasks_m = re.search(r"(?m)^tasks:\s*$", text)
    pins_m = re.search(r"(?m)^future_pins:\s*$", text)
    if not tasks_m or not pins_m:
        print("FAIL: cannot find tasks:/future_pins: blocks", file=sys.stderr)
        sys.exit(1)
    header = text[: tasks_m.start()]
    tasks_block = text[tasks_m.start() : pins_m.start()]
    pins_block = text[pins_m.start():]

    existing_ids = set(re.findall(r"(?m)^\s*- id:\s*(\S+)\s*$", tasks_block + pins_block))

    fragments = sorted(ROOT.glob("eval/hit1-wave6-*.yaml"))
    if not fragments:
        print("FAIL: no eval/hit1-wave6-*.yaml fragments found", file=sys.stderr)
        sys.exit(1)

    new_entries = []
    leaf_names = []
    for frag in fragments:
        ft = frag.read_text(encoding="utf-8")
        # pull task blocks: lines from '  - id:' to the next top-level key
        items = re.findall(
            r"(?ms)^  - id: (\S+)\n(.*?)(?=^  - id:|\Z)", ft
        )
        frag_ids = [i[0] for i in items]
        if len(frag_ids) != 2:
            print(f"FAIL: {frag.name} has {len(frag_ids)} tasks, expected 2", file=sys.stderr)
            sys.exit(1)
        for i, (tid, body) in enumerate(items):
            if tid in existing_ids:
                print(f"FAIL: id '{tid}' from {frag.name} already exists in corpus", file=sys.stderr)
                sys.exit(1)
            existing_ids.add(tid)
            entry = f"  - id: {tid}\n{body.rstrip()}\n"
            new_entries.append(entry)
        # leaf name from expected_skill
        exp = re.search(r"(?m)^\s*expected_skill:\s*(\S+)", ft)
        leaf_names.append(exp.group(1) if exp else frag.stem)

    n_new = len(new_entries)
    n_leaf = 113 + len(fragments)   # baseline 113 leaves (112 wave-5 + fuselage-sizing rescue)
    n_skill = 125 + len(fragments)  # 12 routers + 113 leaves
    n_tasks = 240 + n_new
    new_tasks_block = tasks_block.rstrip() + "\n" + "".join(new_entries) + "\n"

    note = (
        "# P5.2 / Wave 6 (2026-08-31, re-dispatch #4): fan-out continues to\n"
        f"# {n_leaf} verified skills ({n_skill} SKILL.md under gate 1: 12 routers + {n_leaf}\n"
        "# leaves). Wave-6 new leaves: " + ", ".join(leaf_names) + ".\n"
        f"# Corpus: {n_tasks} tasks (240 prior plus {n_new} domain tasks). Owner: Ops\n"
        "# Manager, Wave 6 build (13th-kill rescue, fresh context).\n"
    )

    new_text = header.rstrip() + "\n" + note + new_tasks_block + pins_block
    CORPUS.write_text(new_text, encoding="utf-8")

    for frag in fragments:
        frag.unlink()

    old_count = len(re.findall(r"(?m)^\s*- id:\s*(\S+)\s*$", tasks_block))
    print(f"OK: merged {n_new} tasks from {len(fragments)} fragments; corpus tasks {old_count} -> {old_count + n_new}")
    print("Leaves:", ", ".join(leaf_names))
    for frag in fragments:
        print("deleted", frag.name)

if __name__ == "__main__":
    main()
