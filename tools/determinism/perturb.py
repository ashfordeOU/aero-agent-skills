#!/usr/bin/env python3
"""Measure whether a verdict reproduces when the environment moves.

The corpus ships a determinism claim: the same inputs produce the same
verdict. "It ran twice on my machine" does not test that claim -- running
twice holds every hidden input constant. This harness runs one pipeline
many times while moving exactly one environmental axis per run, and then
byte-diffs the artefacts. Not the summary line: the per-case verdict
record, plus raw stdout, raw stderr and the exit status.

Axes moved:

    instrument    a deliberately altered input, which MUST come out different
    repeat        the same conditions, several times (the noise floor)
    cwd           the directory the process starts in
    locale        LC_ALL / LANG
    tz            TZ
    hostname      the name the process believes the machine has
    umask         the file-creation mask the process inherits
    hashseed      PYTHONHASHSEED, including "random"
    fileorder     the order the filesystem hands back directory entries
    interpreter   every Python minor version installed on this host
    env           HOME, TMPDIR, TERM, COLUMNS, USER, SOURCE_DATE_EPOCH,
                  PYTHONUTF8, PYTHONDONTWRITEBYTECODE, and an unrelated
                  bulk variable

What a green row means, and only this: the artefact bytes did not move
when that one axis moved, on this host, for the sampled cases. An axis
that could not be moved here is reported UNTESTED. It is never reported
as passing.

A matrix of nothing but green rows is also the shape a blind instrument
makes. The `instrument` row is therefore a negative control: one leaf is
removed from a copy of the input, so the verdict has to change. If that
row comes back identical, the comparison is not working and every other
row on the page is worthless -- the harness says so and exits non-zero.

Inputs are frozen before the first run. The corpus and the SKILL.md tree
are snapshotted into the run root and every run, baseline included, reads
that snapshot. Without it a concurrent edit to the working tree would land
in the middle of the matrix and read as a determinism failure.

stdlib only, no network. The harness writes nothing inside the repository:
every run directory is created under a temporary root.

    python3 tools/determinism/perturb.py --tasks 64 --report -
"""

import argparse
import getpass
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    from . import hermeticity as _hermeticity  # pragma: no cover
except Exception:  # noqa: BLE001 - run as a script, not a package
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import hermeticity as _hermeticity

hermeticity = _hermeticity

ARTEFACT_NAMES = ("verdict.txt", "stdout.txt", "stderr.txt", "exit_code.txt")

VERDICT_LINE = re.compile(rb"^(?:PASS|FAIL) gate5-hit1: .* top1=", re.M)

UNTESTED = "UNTESTED"
IDENTICAL = "identical"
DIFFERS = "DIFFERS"
ERROR = "ERROR"


# --------------------------------------------------------------------------
# repository discovery
# --------------------------------------------------------------------------

def find_repo(start=None):
    """Walk up from this file until a directory looks like the corpus repo."""
    here = Path(start) if start else Path(__file__).resolve().parent
    here = here.resolve()
    for candidate in [here] + list(here.parents):
        if (candidate / "Makefile").is_file() and (candidate / "skills").is_dir():
            return candidate
    raise SystemExit("could not locate the repository root above %s" % here)


# --------------------------------------------------------------------------
# corpus sampling
# --------------------------------------------------------------------------

def slice_tasks(text, count=None):
    """Split the corpus text into whole task blocks, then stride-sample.

    The corpus is read as text on purpose. A YAML parser is not in the
    standard library, and the harness must not add a dependency to prove a
    claim about hermeticity. Block boundaries are the only structure this
    needs: a task starts at a two-space "- " item marker and continues
    until the next one. Lines that carry a double-quoted scalar across a
    line break are indented continuations and are kept verbatim.

    Returns (yaml_text, selected_block_count, total_block_count).
    """
    lines = text.splitlines(True)
    start = None
    for index, line in enumerate(lines):
        if line.rstrip("\n") == "tasks:":
            start = index
            break
    if start is None:
        raise ValueError("corpus has no top-level 'tasks:' key")

    blocks = []
    current = None
    for line in lines[start + 1:]:
        stripped = line.strip()
        if line.startswith("  - "):
            if current is not None:
                blocks.append(current)
            current = [line]
            continue
        if not stripped:
            continue
        indented = line[:1] in (" ", "\t")
        if not indented:
            if stripped.startswith("#"):
                continue  # a wave comment sitting between task blocks
            break  # the next top-level key ends the list
        if stripped.startswith("#") and not line.startswith("    "):
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        blocks.append(current)

    if not blocks:
        raise ValueError("corpus 'tasks:' list is empty")

    total = len(blocks)
    if not count or count >= total:
        chosen = blocks
    else:
        indices = sorted({(i * total) // count for i in range(count)})
        chosen = [blocks[i] for i in indices]

    for block in chosen:
        joined = "".join(block)
        if "expected_skill:" not in joined or "query:" not in joined:
            raise ValueError("sliced a partial task block: %r" % joined[:120])

    return "tasks:\n" + "".join("".join(b) for b in chosen), len(chosen), total


# --------------------------------------------------------------------------
# byte comparison
# --------------------------------------------------------------------------

def first_diff(left, right):
    """Return (offset, left_context, right_context) or None when equal."""
    if left == right:
        return None
    limit = min(len(left), len(right))
    offset = limit
    for i in range(limit):
        if left[i] != right[i]:
            offset = i
            break
    lo = max(0, offset - 16)
    return (
        offset,
        repr(left[lo:offset + 24]),
        repr(right[lo:offset + 24]),
    )


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# run plan
# --------------------------------------------------------------------------

class Variant(object):
    """One point in the matrix: a baseline with exactly one thing moved."""

    def __init__(self, axis, value, env=None, drop=(), cwd=None,
                 interpreter=None, skills_root=None, umask=None, note="",
                 power="normal"):
        self.axis = axis
        self.value = value
        self.env = dict(env or {})
        self.drop = tuple(drop)
        self.cwd = cwd
        self.interpreter = interpreter
        self.skills_root = skills_root
        self.umask = umask
        self.note = note
        self.power = power

    @property
    def label(self):
        return "%s=%s" % (self.axis, self.value)


class Untested(object):
    """An axis this host could not move, recorded so it is never assumed."""

    def __init__(self, axis, value, reason):
        self.axis = axis
        self.value = value
        self.reason = reason


class Pipeline(object):
    """A deterministic job whose artefacts are worth diffing."""

    name = "pipeline"

    def argv(self, cfg, variant):  # pragma: no cover - interface
        raise NotImplementedError


class Hit1Router(Pipeline):
    """Gate 5: the offline router resolved over a sample of its case set."""

    name = "hit1-router"

    def argv(self, cfg, variant):
        skills = variant.skills_root or cfg.skills_root
        return [
            variant.interpreter or cfg.interpreter,
            str(cfg.repo / "scripts" / "router_eval.py"),
            str(cfg.corpus_path),
            str(skills),
        ]


class SelfTest(Pipeline):
    """A tiny in-process pipeline used by the unit tests."""

    name = "selftest"

    SCRIPT = (
        "import os,sys\n"
        "print('PASS gate5-hit1: a top1=x/y score=1.0 expected=x/y')\n"
        "print('PASS gate5-hit1: b top1=x/z score=2.0 expected=x/z')\n"
        "print('PASS gate5-hit1: %d/%d tasks Hit@1' % (2,2))\n"
        "sys.stderr.write(os.environ.get('AERO_DET_SELFTEST_ECHO','') + '\\n')\n"
    )

    def argv(self, cfg, variant):
        return [variant.interpreter or cfg.interpreter, "-c", self.SCRIPT]


PIPELINES = {p.name: p for p in (Hit1Router, SelfTest)}


# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

class Config(object):
    def __init__(self, repo, run_root, interpreter, corpus_path, skills_root,
                 pipeline, tasks_selected, tasks_total, timeout,
                 input_digest=None, input_count=0, corpus_digest=None):
        self.repo = repo
        self.run_root = run_root
        self.interpreter = interpreter
        self.corpus_path = corpus_path
        self.skills_root = skills_root
        self.pipeline = pipeline
        self.tasks_selected = tasks_selected
        self.tasks_total = tasks_total
        self.timeout = timeout
        self.input_digest = input_digest
        self.input_count = input_count
        self.corpus_digest = corpus_digest


def baseline_env():
    """A small, fully written-out environment.

    Inheriting os.environ would make "exactly one thing moved" unprovable:
    any variable the parent happened to carry would be an unmeasured input.
    Only PATH and HOME are taken from the parent, because a Python
    interpreter without them is not a realistic run.
    """
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/"),
        "SHELL": "/bin/sh",
        "USER": "baseline-account",
        "LOGNAME": "baseline-account",
        "TMPDIR": "/tmp/",
        "TERM": "xterm-256color",
        "COLUMNS": "80",
        "LINES": "24",
        "LANG": "C",
        "LC_ALL": "C",
        "LANGUAGE": "",
        "TZ": "UTC",
        "HOSTNAME": "baseline-host",
        "HOST": "baseline-host",
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SOURCE_DATE_EPOCH": "1000000000",
    }


BASELINE_UMASK = 0o022


# --------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------

class RunResult(object):
    def __init__(self, variant, run_dir, argv, command, returncode, seconds,
                 artefacts, modes, error=None):
        self.variant = variant
        self.run_dir = run_dir
        self.argv = argv
        self.command = command
        self.returncode = returncode
        self.seconds = seconds
        self.artefacts = artefacts  # name -> bytes
        self.modes = modes          # name -> int
        self.error = error


def extract_verdict(stdout_bytes):
    """The per-case verdict record: the artefact the claim is actually about.

    The trailing "N/N tasks Hit@1" line is deliberately excluded. A summary
    string is the one part of the output that stays the same while the
    per-case results move underneath it.
    """
    keep = []
    for line in stdout_bytes.splitlines(True):
        if VERDICT_LINE.match(line):
            keep.append(line)
    return b"".join(keep)


def run_once(cfg, variant, run_dir):
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "stdout.txt"
    err_path = run_dir / "stderr.txt"

    env = baseline_env()
    env.update(variant.env)
    for key in variant.drop:
        env.pop(key, None)

    argv = cfg.pipeline.argv(cfg, variant)
    cwd = str(variant.cwd or cfg.repo)
    umask = BASELINE_UMASK if variant.umask is None else variant.umask

    # The child shell creates the artefact files itself, so the child's
    # umask is the one that shapes their mode bits. Opening them in the
    # parent would have silently applied the parent's mask instead and the
    # umask axis would have measured nothing.
    command = "umask %03o; cd %s || exit 97; exec %s > %s 2> %s" % (
        umask,
        shlex.quote(cwd),
        " ".join(shlex.quote(a) for a in argv),
        shlex.quote(str(out_path)),
        shlex.quote(str(err_path)),
    )

    started = time.monotonic()
    error = None
    try:
        proc = subprocess.run(
            ["/bin/sh", "-c", command],
            env=env,
            cwd="/",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=cfg.timeout,
        )
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        returncode = -1
        error = "timeout after %ss" % cfg.timeout
    seconds = time.monotonic() - started

    for path in (out_path, err_path):
        if not path.exists():
            path.write_bytes(b"")

    stdout_bytes = out_path.read_bytes()
    (run_dir / "exit_code.txt").write_bytes(("%d\n" % returncode).encode())
    verdict = extract_verdict(stdout_bytes)
    (run_dir / "verdict.txt").write_bytes(verdict)

    artefacts = {}
    modes = {}
    for name in ARTEFACT_NAMES:
        path = run_dir / name
        artefacts[name] = path.read_bytes()
        modes[name] = path.stat().st_mode & 0o777
    return RunResult(variant, run_dir, argv, command, returncode, seconds,
                     artefacts, modes, error)


def compare(baseline, other):
    """Compare every artefact of two runs. Returns (verdict, rows)."""
    rows = []
    identical = True
    for name in ARTEFACT_NAMES:
        left = baseline.artefacts.get(name, b"")
        right = other.artefacts.get(name, b"")
        diff = first_diff(left, right)
        if diff is None:
            rows.append({"artefact": name, "identical": True})
        else:
            identical = False
            rows.append({
                "artefact": name,
                "identical": False,
                "offset": diff[0],
                "baseline": diff[1],
                "variant": diff[2],
                "baseline_sha256": sha256(left),
                "variant_sha256": sha256(right),
            })
    return (IDENTICAL if identical else DIFFERS), rows


# --------------------------------------------------------------------------
# axes
# --------------------------------------------------------------------------

def available_locales():
    try:
        proc = subprocess.run(["locale", "-a"], capture_output=True, timeout=30)
    except Exception:  # noqa: BLE001
        return set()
    return set(proc.stdout.decode("utf-8", "replace").split())


def discover_interpreters(current):
    """Every python3 on this host, keyed by the version it reports."""
    candidates = []
    for directory in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"):
        base = Path(directory)
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if re.fullmatch(r"python3(?:\.\d+)?", entry.name):
                candidates.append(entry)
    pyenv = Path(os.path.expanduser("~/.pyenv/versions"))
    if pyenv.is_dir():
        for version in sorted(pyenv.iterdir()):
            exe = version / "bin" / "python3"
            if exe.exists():
                candidates.append(exe)
    candidates.append(Path(current))

    found = {}
    for exe in candidates:
        try:
            proc = subprocess.run(
                [str(exe), "-c",
                 "import platform,sys;print(platform.python_version());"
                 "import yaml;print(yaml.__version__)"],
                capture_output=True, timeout=60,
            )
        except Exception:  # noqa: BLE001
            continue
        if proc.returncode != 0:
            continue
        parts = proc.stdout.decode().split()
        if not parts:
            continue
        version = parts[0]
        minor = ".".join(version.split(".")[:2])
        found.setdefault(minor, (version, str(exe.resolve())))
    return found


def copy_skill_files(src_root, dst_root, reverse=False):
    """Copy only the files the router reads, creating them in a chosen order.

    The router globs for SKILL.md and nothing else, so a SKILL.md-only copy
    is input-equivalent to the tree. Creation order is a parameter because
    on some filesystems it decides the order readdir hands entries back.
    """
    dst_root = Path(dst_root)
    sources = sorted(Path(src_root).rglob("SKILL.md"))
    if reverse:
        sources = list(reversed(sources))
    count = 0
    for src in sources:
        rel = src.relative_to(src_root)
        target = dst_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(src), str(target))
        count += 1
    return count


def readdir_signature(root, limit=12):
    """The raw, unsorted order the filesystem reports for one directory."""
    root = Path(root)
    try:
        names = [e.name for e in os.scandir(str(root))]
    except OSError:
        return []
    return names[:limit]


def busiest_dir(root):
    """The relative path of the directory with the most entries.

    The root of the skills tree holds about a dozen families, which is too
    few for a readdir order to be convincing evidence either way. The
    busiest directory holds hundreds, so if two filesystems agree there
    they really do agree.
    """
    root = Path(root)
    best = None
    for dirpath, dirnames, filenames in os.walk(str(root)):
        count = len(dirnames) + len(filenames)
        rel = os.path.relpath(dirpath, str(root))
        key = (-count, rel)
        if best is None or key < best[0]:
            best = (key, rel, count)
    if best is None:
        return ".", 0
    return best[1], best[2]


def tree_digest(root, pattern="SKILL.md"):
    """A content digest of the frozen input, so the report names what it read."""
    digest = hashlib.sha256()
    count = 0
    for path in sorted(Path(root).rglob(pattern)):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        count += 1
    return digest.hexdigest(), count


def first_expected_skill(corpus_text):
    """The expected skill of the first sampled case, for the negative control."""
    match = re.search(r'expected_skill:\s*"([^"]+)"', corpus_text)
    if match:
        return match.group(1)
    match = re.search(r"expected_skill:\s*([^\s#]+)", corpus_text)
    return match.group(1) if match else None


class RamDisk(object):
    """A small HFS+ ram disk, used only to obtain a second readdir order.

    APFS returns directory entries in an order derived from the file names,
    so creating the same names in a different order changes nothing --
    measured, not assumed. HFS+ returns them in catalog (sorted) order. Two
    filesystems is the only way to actually move this axis on macOS without
    administrator rights.
    """

    def __init__(self, megabytes=192):
        self.megabytes = megabytes
        self.device = None
        self.mountpoint = None
        self.reason = None

    def attach(self):
        if platform.system() != "Darwin":
            self.reason = "not macOS; no hdiutil ram disk available"
            return False
        for tool in ("hdiutil", "newfs_hfs", "mount"):
            if shutil.which(tool) is None:
                self.reason = "%s not on PATH" % tool
                return False
        sectors = self.megabytes * 2048
        try:
            proc = subprocess.run(
                ["hdiutil", "attach", "-nomount", "ram://%d" % sectors],
                capture_output=True, timeout=120,
            )
            if proc.returncode != 0:
                self.reason = "hdiutil attach failed: %s" % proc.stderr.decode().strip()
                return False
            device = proc.stdout.decode().split()[0]
            self.device = device
            proc = subprocess.run(
                ["newfs_hfs", "-v", "AERODET", device],
                capture_output=True, timeout=120,
            )
            if proc.returncode != 0:
                self.reason = "newfs_hfs failed: %s" % proc.stderr.decode().strip()
                self.detach()
                return False
            self.mountpoint = Path(tempfile.mkdtemp(prefix="aero-det-hfs-"))
            proc = subprocess.run(
                ["mount", "-t", "hfs", device, str(self.mountpoint)],
                capture_output=True, timeout=120,
            )
            if proc.returncode != 0:
                self.reason = "mount failed: %s" % proc.stderr.decode().strip()
                self.detach()
                return False
        except Exception as exc:  # noqa: BLE001
            self.reason = "ram disk setup raised %s" % exc
            self.detach()
            return False
        return True

    def detach(self):
        if self.mountpoint is not None:
            subprocess.run(["umount", str(self.mountpoint)],
                           capture_output=True, timeout=120)
        if self.device is not None:
            subprocess.run(["hdiutil", "detach", "-force", self.device],
                           capture_output=True, timeout=120)
        if self.mountpoint is not None:
            shutil.rmtree(str(self.mountpoint), ignore_errors=True)
        self.device = None
        self.mountpoint = None


def build_axes(cfg, args, scratch, locales, interpreters, ramdisk):
    """Return (variants, untested, extra_evidence)."""
    variants = []
    untested = []
    evidence = {}
    probe_dir, probe_count = busiest_dir(cfg.skills_root)
    evidence["readdir_probe_dir"] = probe_dir
    evidence["readdir_probe_entries"] = probe_count

    # ---- instrument check: this row MUST come out different ---------------
    # A page of green rows proves nothing unless the comparison can go red.
    maimed = scratch / "skills-one-leaf-removed"
    copy_skill_files(cfg.skills_root, maimed)
    target = first_expected_skill(cfg.corpus_path.read_text(encoding="utf-8"))
    removed = maimed / (target or "") / "SKILL.md"
    if target and removed.is_file():
        removed.unlink()
        evidence["instrument_removed_leaf"] = target
        variants.append(Variant(
            "instrument", "one-leaf-removed",
            skills_root=maimed,
            note="negative control: the winning skill for the first sampled "
                 "case is gone, so the verdict has to change",
        ))
    else:
        untested.append(Untested(
            "instrument", "one-leaf-removed",
            "could not locate the first case's expected skill in the tree, so "
            "the comparison was never proved able to fail",
        ))

    # ---- repeat: the noise floor -----------------------------------------
    for i in range(args.repeats):
        variants.append(Variant("repeat", "run-%d" % (i + 2),
                                note="same conditions as the baseline"))

    # ---- working directory -----------------------------------------------
    deep = cfg.repo / "skills"
    for name, path in (
        ("root-/", Path("/")),
        ("tmp", scratch),
        ("repo/skills", deep if deep.is_dir() else cfg.repo),
        ("home", Path(os.path.expanduser("~"))),
    ):
        variants.append(Variant("cwd", name, cwd=path))

    # ---- locale -----------------------------------------------------------
    wanted = ["en_US.UTF-8", "de_DE.UTF-8", "tr_TR.UTF-8", "ja_JP.UTF-8",
              "en_US.ISO8859-1", "C.UTF-8"]
    for loc in wanted:
        if locales and loc not in locales:
            untested.append(Untested("locale", loc, "not installed on this host"))
            continue
        variants.append(Variant("locale", loc, env={"LC_ALL": loc, "LANG": loc}))

    # ---- timezone ---------------------------------------------------------
    for tz in ("America/Los_Angeles", "Europe/Berlin", "Asia/Kathmandu",
               "Pacific/Kiritimati"):
        variants.append(Variant("tz", tz, env={"TZ": tz}))

    # ---- hostname ---------------------------------------------------------
    variants.append(Variant(
        "hostname", "env-proxy",
        env={"HOSTNAME": "moved-host-9x", "HOST": "moved-host-9x"},
        power="weak",
        note="env vars only; see the untested row for the kernel host name",
    ))
    untested.append(Untested(
        "hostname", "kernel host name",
        "changing it needs administrator rights (scutil --set HostName) and "
        "macOS has no user-level UTS namespace; the artefacts were instead "
        "scanned for this machine's real name",
    ))

    # ---- umask ------------------------------------------------------------
    for mask in (0o000, 0o027, 0o077):
        variants.append(Variant("umask", "%03o" % mask, umask=mask))

    # ---- PYTHONHASHSEED ---------------------------------------------------
    for seed in ("1", "42", "4294967295"):
        variants.append(Variant("hashseed", seed, env={"PYTHONHASHSEED": seed}))
    for i in range(args.random_seeds):
        variants.append(Variant("hashseed", "random-%d" % (i + 1),
                                env={"PYTHONHASHSEED": "random"}))

    # ---- file ordering on disk -------------------------------------------
    native_copy = scratch / "skills-native-copy"
    copied = copy_skill_files(cfg.skills_root, native_copy)
    evidence["skill_md_copied"] = copied
    evidence["readdir_snapshot"] = readdir_signature(cfg.skills_root / probe_dir)
    evidence["readdir_native_copy"] = readdir_signature(native_copy / probe_dir)
    variants.append(Variant(
        "fileorder", "copy-same-fs",
        skills_root=native_copy,
        note="control: an identical input set at a different absolute path",
    ))

    native_rev = scratch / "skills-native-reversed"
    copy_skill_files(cfg.skills_root, native_rev, reverse=True)
    evidence["readdir_native_reversed"] = readdir_signature(native_rev / probe_dir)
    same_order = (evidence["readdir_native_copy"] == evidence["readdir_native_reversed"])
    evidence["creation_order_changes_readdir"] = not same_order
    if same_order:
        untested.append(Untested(
            "fileorder", "reverse creation order on the native filesystem",
            "measured: this filesystem returns directory entries in an order "
            "derived from the names, so creating them in reverse order gave "
            "the identical readdir sequence -- the axis did not actually move",
        ))
    else:
        variants.append(Variant("fileorder", "reverse-creation-order",
                                skills_root=native_rev))

    if ramdisk is not None and ramdisk.mountpoint is not None:
        hfs_copy = Path(ramdisk.mountpoint) / "skills"
        copy_skill_files(cfg.skills_root, hfs_copy)
        evidence["readdir_hfsplus"] = readdir_signature(hfs_copy / probe_dir)
        moved = evidence["readdir_hfsplus"] != evidence["readdir_native_copy"]
        evidence["second_filesystem_changes_readdir"] = moved
        if moved:
            variants.append(Variant(
                "fileorder", "hfs+-ramdisk",
                skills_root=hfs_copy,
                note="a second filesystem really does hand back a different order",
            ))
        else:
            untested.append(Untested(
                "fileorder", "second filesystem",
                "the HFS+ ram disk returned the same order as the native "
                "filesystem, so this variant would not have moved the axis",
            ))
    else:
        reason = (ramdisk.reason if ramdisk is not None
                  else "not requested (pass --ramdisk)")
        untested.append(Untested("fileorder", "second filesystem", reason))

    # ---- interpreter ------------------------------------------------------
    current_minor = ".".join(platform.python_version().split(".")[:2])
    baseline_exe = os.path.realpath(cfg.interpreter)
    for minor in sorted(interpreters):
        version, exe = interpreters[minor]
        if os.path.realpath(exe) == baseline_exe:
            continue
        note = ""
        if minor == current_minor:
            note = ("same minor version as the baseline, reached through a "
                    "different binary path; a control, not a version change")
        variants.append(Variant("interpreter", version, interpreter=exe,
                                note=note))
    evidence["interpreters"] = {k: v[0] for k, v in interpreters.items()}
    evidence["baseline_interpreter_minor"] = current_minor
    if len(interpreters) < 2:
        untested.append(Untested(
            "interpreter", "a second minor version",
            "only one usable python3 was found on this host",
        ))

    # ---- assorted environment --------------------------------------------
    alt_home = scratch / "alt-home"
    alt_home.mkdir(exist_ok=True)
    alt_tmp = scratch / "alt-tmp"
    alt_tmp.mkdir(exist_ok=True)
    env_points = [
        ("HOME", {"HOME": str(alt_home)}),
        ("TMPDIR", {"TMPDIR": str(alt_tmp) + "/"}),
        ("TERM=dumb", {"TERM": "dumb"}),
        ("COLUMNS=40", {"COLUMNS": "40"}),
        ("USER", {"USER": "someone-else", "LOGNAME": "someone-else"}),
        ("SOURCE_DATE_EPOCH", {"SOURCE_DATE_EPOCH": "2000000000"}),
        ("PYTHONUTF8=1", {"PYTHONUTF8": "1"}),
        ("PYTHONDONTWRITEBYTECODE=0", {"PYTHONDONTWRITEBYTECODE": "0"}),
        ("bulk-unrelated-var", {"AERO_DET_NOISE": "x" * 4096}),
    ]
    for label, env in env_points:
        variants.append(Variant("env", label, env=env))

    # ---- axes this host cannot move at all --------------------------------
    untested.append(Untested(
        "operating system", "anything but %s %s" % (platform.system(),
                                                    platform.release()),
        "a single host was available; a Linux or Windows run was not performed",
    ))
    untested.append(Untested(
        "cpu architecture", "anything but %s" % platform.machine(),
        "no second architecture was available",
    ))
    untested.append(Untested(
        "clock", "a wall-clock jump between runs",
        "the system clock was not moved; the artefacts were instead scanned "
        "for embedded timestamps",
    ))

    return variants, untested, evidence


def check_one_thing_moved(variant):
    """Guard the design rule: a variant differs from the baseline in one way."""
    base = baseline_env()
    moved = dict((k, v) for k, v in variant.env.items() if base.get(k) != v)
    moved_keys = set(moved) | set(variant.drop)
    structural = sum(1 for x in (variant.cwd, variant.interpreter,
                                 variant.skills_root, variant.umask)
                     if x is not None)
    return moved_keys, structural


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def build_redactor(cfg, enabled=True):
    if not enabled:
        return lambda text: text
    pairs = []

    def add(value, placeholder):
        if value and len(str(value)) >= 3:
            pairs.append((str(value), placeholder))

    add(cfg.repo, "<REPO>")
    add(cfg.run_root, "<RUN>")
    add(os.path.expanduser("~"), "<HOME>")
    host = socket.gethostname()
    add(host, "<HOST>")
    if "." in host:
        add(host.split(".")[0], "<HOST>")
    try:
        add(getpass.getuser(), "<USER>")
    except Exception:  # noqa: BLE001
        pass
    pairs.sort(key=lambda p: -len(p[0]))

    def redact(text):
        for needle, placeholder in pairs:
            text = text.replace(needle, placeholder)
        return text

    return redact


def render_report(cfg, args, baseline, results, untested, evidence,
                  scan_results, redact):
    out = []
    w = out.append
    w("# Determinism under perturbation")
    w("")
    w("Generated by `tools/determinism/perturb.py`. Every row is a measurement "
      "made on one host. A row reads `identical` only when the artefact bytes "
      "did not move; an axis that could not be moved is listed under "
      "**Untested axes** and is not counted as a pass.")
    w("")
    w("## What was run")
    w("")
    w("| field | value |")
    w("| --- | --- |")
    w("| pipeline | `%s` |" % cfg.pipeline.name)
    w("| command | `%s` |" % " ".join(
        shlex.quote(a) for a in cfg.pipeline.argv(cfg, Variant("baseline", "0"))))
    w("| corpus cases sampled | %d of %d |" % (cfg.tasks_selected, cfg.tasks_total))
    w("| sampled corpus sha256 | `%s` |" % cfg.corpus_digest)
    w("| frozen input tree | %d SKILL.md, digest `%s` |" %
      (cfg.input_count, cfg.input_digest))
    w("| artefacts diffed per run | %s |" % ", ".join("`%s`" % a for a in ARTEFACT_NAMES))
    w("| runs | %d (1 baseline + %d variants) |" % (len(results) + 1, len(results)))
    w("| host | %s %s %s |" % (platform.system(), platform.release(),
                               platform.machine()))
    w("| baseline interpreter | %s |" % platform.python_version())
    w("| baseline exit status | %d |" % baseline.returncode)
    w("| baseline verdict lines | %d |" %
      len(baseline.artefacts["verdict.txt"].splitlines()))
    w("| baseline `verdict.txt` sha256 | `%s` |" %
      sha256(baseline.artefacts["verdict.txt"]))
    w("| baseline wall time | %.1f s |" % baseline.seconds)
    w("")
    w("`verdict.txt` is the per-case record extracted from stdout -- one line "
      "per routed case, with the winning skill and its score. The trailing "
      "`N/N tasks Hit@1` summary line is excluded on purpose: a summary is the "
      "part of the output that stays still while the results move under it.")
    w("")
    w("The tree was copied into the run root before the first run and every "
      "run read that copy, so an edit to the working tree during the matrix "
      "cannot be mistaken for a determinism failure.")
    w("")
    w("Reproduce with (add your own `--report` destination):")
    w("")
    w("```")
    w("python3 tools/determinism/perturb.py %s" % " ".join(
        shlex.quote(a) for a in (getattr(args, "invocation", None) or [])))
    w("```")
    w("")
    w("This page carries no generation timestamp on purpose. It is itself an "
      "artefact of the harness and ought to reproduce; the input digests "
      "above are what identify the tree it was measured against.")
    w("")

    w("## Instrument check")
    w("")
    instrument = [(r, v) for r, v, _ in results if r.variant.axis == "instrument"]
    if not instrument:
        w("**No negative control ran.** Nothing below is trustworthy: a "
          "comparison that was never shown to fail cannot be read as a pass.")
    else:
        for res, verdict in instrument:
            if verdict == IDENTICAL:
                w("**BLIND INSTRUMENT.** `%s` removed the winning skill for "
                  "the first sampled case and the artefacts did not change. "
                  "The comparison is not working; every other row on this "
                  "page is void." % res.variant.value)
            else:
                w("`%s`: the winning skill for the first sampled case (`%s`) "
                  "was removed from a copy of the input and the artefacts "
                  "changed, as they must. The comparison can go red, so the "
                  "green rows below mean something." % (
                      res.variant.value,
                      evidence.get("instrument_removed_leaf", "?")))
    w("")

    w("## Matrix")
    w("")
    w("| axis | varied value | artefacts identical | first differing byte | note |")
    w("| --- | --- | --- | --- | --- |")
    for res, verdict, rows in results:
        expect_diff = res.variant.axis == "instrument"
        if res.error:
            detail = "run error: %s" % res.error
            state = ERROR
        elif verdict == IDENTICAL:
            detail = "--"
            state = "**BLIND**" if expect_diff else "yes"
        else:
            state = "no (expected)" if expect_diff else "**no**"
            bad = [r for r in rows if not r["identical"]]
            detail = "; ".join(
                "`%s` @ %d base=%s var=%s" % (r["artefact"], r["offset"],
                                              r["baseline"], r["variant"])
                for r in bad
            )
        note = res.variant.note
        if res.variant.power == "weak":
            note = ("**weak power** " + note).strip()
        if res.returncode != baseline.returncode:
            note = "%s. Exit %d vs baseline %d." % (
                note.rstrip(". "), res.returncode, baseline.returncode)
            note = note.lstrip(". ")
        w("| %s | `%s` | %s | %s | %s |" % (
            res.variant.axis, res.variant.value, state, detail, note or ""))
    w("")

    perturbation = [(r, v) for r, v, _ in results if r.variant.axis != "instrument"]
    identical_count = sum(1 for _, v in perturbation if v == IDENTICAL)
    w("%d of %d perturbation runs produced byte-identical artefacts "
      "(the instrument row is counted separately, above)." %
      (identical_count, len(perturbation)))
    w("")
    if perturbation:
        times = sorted(r.seconds for r, _ in perturbation)
        w("Per-run wall time: min %.1f s, median %.1f s, max %.1f s." % (
            times[0], times[len(times) // 2], times[-1]))
        w("")

    w("## Untested axes")
    w("")
    if not untested:
        w("None.")
    else:
        w("| axis | value not reached | why |")
        w("| --- | --- | --- |")
        for u in untested:
            w("| %s | %s | %s |" % (u.axis, u.value, u.reason))
    w("")

    w("## Ordering evidence")
    w("")
    w("`fileorder` is only a real axis if the filesystem actually hands back a "
      "different sequence. The raw `os.scandir` order was recorded for the "
      "busiest directory in the tree (`%s`, %s entries) in each copy:" % (
          evidence.get("readdir_probe_dir"),
          evidence.get("readdir_probe_entries")))
    w("")
    for key in ("readdir_snapshot", "readdir_native_copy",
                "readdir_native_reversed", "readdir_hfsplus"):
        if key in evidence:
            w("- `%s`: %s" % (key, ", ".join(evidence[key][:8])))
    w("")
    w("- creation order changes readdir on the native filesystem: **%s**" %
      evidence.get("creation_order_changes_readdir"))
    w("- a second filesystem changes readdir: **%s**" %
      evidence.get("second_filesystem_changes_readdir", "not attempted"))
    w("- SKILL.md files copied per tree: %s" % evidence.get("skill_md_copied"))
    w("")
    seeds = [(res, v) for res, v, _ in results if res.variant.axis == "hashseed"]
    w("Dictionary and set iteration order is not visible in a pattern scan. "
      "The test for it is the `hashseed` axis: %d runs, %d byte-identical." % (
          len(seeds), sum(1 for _, v in seeds if v == IDENTICAL)))
    w("")

    w("## umask evidence")
    w("")
    w("The artefact files are created by the child shell, not by the harness, "
      "so the child's mask really does reach them. The mode bits below show "
      "the axis moved even though the content did not:")
    w("")
    w("| run | umask | `stdout.txt` mode |")
    w("| --- | --- | --- |")
    w("| baseline | `%03o` | `%03o` |" % (BASELINE_UMASK,
                                          baseline.modes["stdout.txt"]))
    for res, _, _ in results:
        if res.variant.axis == "umask":
            w("| variant | `%s` | `%03o` |" % (res.variant.value,
                                               res.modes["stdout.txt"]))
    w("")

    w("## Hermeticity scan of the produced artefacts")
    w("")
    w("Byte-stability is necessary, not sufficient. These rules look for the "
      "traces that make an artefact machine- or moment-specific even when it "
      "happens to reproduce here.")
    w("")
    if not scan_results:
        w("No artefacts scanned.")
    else:
        w("| artefact | findings | rules hit |")
        w("| --- | --- | --- |")
        for label, findings in scan_results:
            names = sorted(set(f.rule for f in findings))
            w("| `%s` | %d | %s |" % (label, len(findings),
                                      ", ".join(names) if names else "--"))
        w("")
        for label, findings in scan_results:
            if not findings:
                continue
            w("### `%s`" % label)
            w("")
            for f in findings[:40]:
                w("- **%s** (%s) line %d, offset %d: `%s` -- %s" % (
                    f.rule, f.severity, f.line, f.offset, f.sample, f.why))
            w("")
    w("")

    w("## Reading this honestly")
    w("")
    w("- Every `identical` cell is a statement about this host, this "
      "filesystem, these interpreter builds and the sampled cases, and "
      "nothing wider.")
    w("- The untested table is part of the result, not a caveat appended to "
      "it. An axis listed there has no verdict at all.")
    w("- `umask` moves the mode bits of the files the child creates; it does "
      "not move their content for this pipeline, because the pipeline writes "
      "no files of its own. The axis is reported for completeness and its "
      "power over this pipeline is low.")
    w("")

    return redact("\n".join(out) + "\n")


def build_json(cfg, args, baseline, results, untested, evidence, scan_results,
               redact):
    payload = {
        "pipeline": cfg.pipeline.name,
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "sample": {
            "selected": cfg.tasks_selected,
            "total": cfg.tasks_total,
            "corpus_sha256": cfg.corpus_digest,
            "input_tree_digest": cfg.input_digest,
            "input_tree_files": cfg.input_count,
        },
        "baseline": {
            "returncode": baseline.returncode,
            "seconds": round(baseline.seconds, 3),
            "sha256": dict((k, sha256(v)) for k, v in baseline.artefacts.items()),
            "modes": dict((k, "%03o" % m) for k, m in baseline.modes.items()),
            "verdict_lines": len(baseline.artefacts["verdict.txt"].splitlines()),
        },
        "runs": [],
        "untested": [{"axis": u.axis, "value": u.value, "reason": u.reason}
                     for u in untested],
        "evidence": evidence,
        "hermeticity": [
            {"artefact": label, "findings": [f.as_dict() for f in findings]}
            for label, findings in scan_results
        ],
    }
    for res, verdict, rows in results:
        payload["runs"].append({
            "axis": res.variant.axis,
            "value": res.variant.value,
            "power": res.variant.power,
            "verdict": verdict,
            "returncode": res.returncode,
            "seconds": round(res.seconds, 3),
            "error": res.error,
            "modes": dict((k, "%03o" % m) for k, m in res.modes.items()),
            "artefacts": rows,
        })
    return redact(json.dumps(payload, indent=2, sort_keys=True)) + "\n"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Measure determinism under perturbation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--repo", default=None, help="repository root (default: detected)")
    p.add_argument("--pipeline", default="hit1-router", choices=sorted(PIPELINES),
                   help="which deterministic job to perturb")
    p.add_argument("--tasks", type=int, default=64,
                   help="corpus cases to sample (0 = the whole corpus; the "
                        "whole corpus takes roughly a quarter-hour per run)")
    p.add_argument("--repeats", type=int, default=2,
                   help="extra runs under baseline conditions (noise floor)")
    p.add_argument("--random-seeds", type=int, default=3,
                   help="runs with PYTHONHASHSEED=random")
    p.add_argument("--axes", default=None,
                   help="comma-separated axis names to keep")
    p.add_argument("--ramdisk", action="store_true",
                   help="create a temporary HFS+ ram disk to obtain a second "
                        "on-disk entry order (macOS; detached on exit)")
    p.add_argument("--scan", action="append", default=[],
                   help="also run the hermeticity scan over this file "
                        "(repeatable; read-only). Point it at the artefacts "
                        "the repository itself generates.")
    p.add_argument("--timeout", type=int, default=3600, help="per-run timeout")
    p.add_argument("--report", default=None,
                   help="write the markdown matrix here ('-' for stdout)")
    p.add_argument("--json", dest="json_path", default=None,
                   help="write the machine-readable result here")
    p.add_argument("--keep", action="store_true", help="keep the run directories")
    p.add_argument("--no-redact", action="store_true",
                   help="do not replace machine-specific paths in the output")
    p.add_argument("--quiet", action="store_true")
    parsed = p.parse_args(argv)
    # Kept so the report can print the command that produced it.
    parsed.invocation = measurement_args(
        list(sys.argv[1:] if argv is None else argv))
    return parsed


# Flags that choose where the operator put the output. They say nothing
# about what was measured, and their values are paths on one machine, so
# they are stripped from the "reproduce with" line in the report.
OUTPUT_FLAGS = {"--report": 1, "--json": 1, "--repo": 1,
                "--keep": 0, "--quiet": 0, "--no-redact": 0}


def measurement_args(argv):
    """Drop output destinations, keep the flags that shaped the measurement."""
    out = []
    skip = 0
    for token in argv:
        if skip:
            skip -= 1
            continue
        head = token.split("=", 1)[0]
        if head in OUTPUT_FLAGS:
            if "=" not in token:
                skip = OUTPUT_FLAGS[head]
            continue
        out.append(token)
    return out


def main(argv=None):
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else find_repo()
    pipeline = PIPELINES[args.pipeline]()

    run_root = Path(tempfile.mkdtemp(prefix="aero-determinism-"))
    scratch = run_root / "scratch"
    scratch.mkdir()
    ramdisk = None
    try:
        corpus_src = repo / "eval" / "hit1-corpus.yaml"
        corpus_path = scratch / "corpus-sample.yaml"
        skills_root = repo / "skills"
        digest = None
        count = 0
        if pipeline.name == "hit1-router":
            text = corpus_src.read_text(encoding="utf-8")
            sliced, selected, total = slice_tasks(text, args.tasks or None)
            corpus_path.write_text(sliced, encoding="utf-8")
            # Freeze the tree. The working tree may be edited while the
            # matrix runs; an input that moves mid-measurement would show up
            # as a determinism failure that is really a race.
            if not args.quiet:
                print("freezing the input tree...", file=sys.stderr)
            skills_root = scratch / "skills-snapshot"
            copy_skill_files(repo / "skills", skills_root)
            digest, count = tree_digest(skills_root)
        else:
            corpus_path.write_text("tasks: []\n", encoding="utf-8")
            selected = total = 0

        interpreter = shutil.which("python3") or sys.executable
        cfg = Config(repo, run_root, interpreter, corpus_path,
                     skills_root, pipeline, selected, total, args.timeout,
                     input_digest=digest, input_count=count,
                     corpus_digest=sha256(corpus_path.read_bytes()))

        if args.ramdisk:
            ramdisk = RamDisk()
            if not ramdisk.attach() and not args.quiet:
                print("ram disk unavailable: %s" % ramdisk.reason, file=sys.stderr)

        locales = available_locales()
        interpreters = (discover_interpreters(interpreter)
                        if pipeline.name == "hit1-router" else {})

        variants, untested, evidence = build_axes(cfg, args, scratch, locales,
                                                  interpreters, ramdisk)
        enforce_instrument = True
        if args.axes:
            keep = set(a.strip() for a in args.axes.split(","))
            variants = [v for v in variants if v.axis in keep]
            enforce_instrument = "instrument" in keep

        if not args.quiet:
            print("baseline: %s" % " ".join(
                shlex.quote(a) for a in pipeline.argv(cfg, Variant("baseline", "0"))),
                file=sys.stderr)
        baseline = run_once(cfg, Variant("baseline", "0"), run_root / "run-000")
        if baseline.returncode not in (0, 1):
            print("baseline run failed hard (exit %d):" % baseline.returncode,
                  file=sys.stderr)
            print(baseline.artefacts["stderr.txt"].decode("utf-8", "replace")[:4000],
                  file=sys.stderr)
            return 2
        if pipeline.name == "hit1-router":
            got = len(baseline.artefacts["verdict.txt"].splitlines())
            if got != selected:
                print("sample mismatch: sliced %d cases, the router reported %d"
                      % (selected, got), file=sys.stderr)
                print(baseline.artefacts["stderr.txt"].decode("utf-8", "replace")[:2000],
                      file=sys.stderr)
                return 2

        results = []
        for index, variant in enumerate(variants, start=1):
            if not args.quiet:
                print("[%2d/%2d] %-44s" % (index, len(variants), variant.label),
                      end="", file=sys.stderr, flush=True)
            res = run_once(cfg, variant, run_root / ("run-%03d" % index))
            verdict, rows = compare(baseline, res)
            results.append((res, verdict, rows))
            if not args.quiet:
                print(" %-9s %5.1fs" % (verdict, res.seconds), file=sys.stderr)

        host = socket.gethostname()
        try:
            user = getpass.getuser()
        except Exception:  # noqa: BLE001
            user = None
        literals = (str(run_root), os.environ.get("TMPDIR") or "", str(repo))
        scan_results = []
        for name in ARTEFACT_NAMES:
            findings = hermeticity.scan_bytes(
                baseline.artefacts[name], hostname=host, username=user,
                extra_literals=literals,
            )
            scan_results.append((name, findings))
        for extra in args.scan:
            path = Path(extra)
            label = str(path)
            try:
                rel = path.resolve().relative_to(repo)
                label = str(rel)
            except Exception:  # noqa: BLE001 - outside the repo, keep the path
                pass
            if not path.is_file():
                scan_results.append((label + " (missing)", []))
                continue
            scan_results.append((label, hermeticity.scan_file(
                str(path), hostname=host, username=user,
                extra_literals=literals)))

        redact = build_redactor(cfg, enabled=not args.no_redact)
        report = render_report(cfg, args, baseline, results, untested, evidence,
                               scan_results, redact)
        if args.report == "-":
            sys.stdout.write(report)
        elif args.report:
            Path(args.report).write_text(report, encoding="utf-8")
            if not args.quiet:
                print("report written: %s" % args.report, file=sys.stderr)
        if args.json_path:
            Path(args.json_path).write_text(
                build_json(cfg, args, baseline, results, untested, evidence,
                           scan_results, redact),
                encoding="utf-8")

        instrument = [r for r in results if r[0].variant.axis == "instrument"]
        blind = [r for r in instrument if r[1] == IDENTICAL]
        perturbation = [r for r in results if r[0].variant.axis != "instrument"]
        differed = [r for r in perturbation if r[1] != IDENTICAL]
        if not args.quiet:
            print("%d/%d perturbation runs byte-identical; %d untested axes"
                  % (len(perturbation) - len(differed), len(perturbation),
                     len(untested)), file=sys.stderr)
        if enforce_instrument and (blind or not instrument):
            print("INSTRUMENT CHECK FAILED: the comparison was not shown able "
                  "to detect a changed input; the matrix is void",
                  file=sys.stderr)
            return 3
        return 1 if differed else 0
    finally:
        if ramdisk is not None:
            ramdisk.detach()
        if args.keep:
            print("run directories kept under %s" % run_root, file=sys.stderr)
        else:
            shutil.rmtree(str(run_root), ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
