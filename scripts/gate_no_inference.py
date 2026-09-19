#!/usr/bin/env python3
"""Gate: nothing reachable from a verdict may perform model inference.

WHY THIS GATE EXISTS
--------------------
The corpus is a fixed, fully specified, design-time rule base: a deterministic
offline router plus per-leaf logic modules that compute an answer from their
inputs and nothing else. Aviation-safety guidance for AI draws its scope line
in exactly that place - a non-learning expert system whose knowledge base is
frozen at design time and verified with ordinary software-engineering methods
sits OUTSIDE the AI guidance, while a large general-purpose model brought in
off the shelf is capped at the weakest assurance level available. The line is
binary. One model call anywhere on the path that produces a verdict moves the
whole product across it, permanently, and no amount of documentation moves it
back.

So the invariant is not a promise in prose. It is enforced here, in the build:

    Nothing reachable from a verdict may perform, or arrange for, model
    inference - not by importing a model SDK, not by opening a network
    socket, not by shelling out to a model runner, not by reading a
    credential that only an inference call would need.

Rationale and the conformance statement: docs/claim-1-no-inference.md.

WHAT IT LOOKS FOR
-----------------
  model-sdk-import        an import of a hosted-model or local-model SDK
  learned-model-import    an import of a trained-model runtime (a learned
                          model is still a model even when it is not an LLM;
                          the "non-learning" half of the claim depends on this)
  network-egress-import   an import of a network egress primitive or client
  dynamic-import          importlib.import_module("<sdk>") / __import__("<sdk>")
  model-runner-exec       starting a local model runner binary
  managed-inference-call  a cloud SDK client opened against a managed
                          inference service (the bedrock-style case, which
                          needs no model-named import at all)
  inference-env-read      a read of an environment variable that only an
                          inference call would want
  network-call            a non-Python network egress call or a model
                          provider host literal

HOW IT MATCHES
--------------
Python is matched on PARSED STRUCTURE (the stdlib `ast` module), never on raw
source text. This estate has a recorded incident in which a regex word
boundary matched inside a number and a repair script then corrupted every
figure it touched; text matching over code is the same class of mistake, and
it fails in both directions - it fires on the word `openai` inside a comment
and it misses `__import__("open" + "ai")`.

Regex is used ONLY for the non-Python graded files (.js/.mjs/.cjs/.ts/.sh/.kt
and friends), because the stdlib ships no parser for those languages. Those
patterns anchor on syntactic delimiters - a quote, a paren, a shell separator
- and never on a bare word boundary, for the reason above. Identifier
matching (environment-variable names) splits on `_` and compares whole
segments, so a vendor token can never match inside a longer word by accident.

Both front ends feed the SAME policy predicates, so the Python rules and the
JavaScript/shell rules cannot drift apart.

SCOPE RULE
----------
A file is graded when BOTH of these hold:

  1. it lives under one of GRADED_TREES - the shipped corpus (`skills/`), the
     verification harness that computes verdicts (`scripts/`), and the shipped
     distribution that carries the router to users (`packages/`); and
  2. its suffix is an executable-code suffix (PY_SUFFIXES or
     OTHER_CODE_SUFFIXES).

Everything else is out of scope, deliberately:

  - Documentation never fires. Prose, Markdown, YAML and JSON are not scanned
    at all, so a skill or a design note may discuss models, name vendors and
    quote model identifiers freely. The claim is about what the code DOES, not
    about what the corpus is allowed to talk about.
  - Development-only tooling is out of scope, but only by NAME, never by
    accident: each exempt path is listed in DEV_ONLY_EXEMPT with a reason, and
    every exemption is printed on a PASS run. A silent allowlist is how an
    invariant like this rots.
  - Release and operations plumbing (`ops/`, `.github/`) is out of scope: it
    publishes artefacts, it does not compute or carry a verdict, and it
    genuinely needs the network.

HOW A FUTURE READER CHANGES THIS
--------------------------------
Everything above the DO-NOT-EDIT marker is data. To widen the ban, add the
module, binary, service, host or variable name to the matching frozenset. To
bring a new tree under the gate, add it to GRADED_TREES. To exempt a new
development-only tool, add its repo-relative path to DEV_ONLY_EXEMPT together
with a reason a reviewer can weigh - and expect that reason to be read, since
it is printed on every green run. Do not add an exemption for anything that
runs inside `make validate`, `make attest`, the router, or a leaf: those ARE
the graded path, and exempting one of them is the failure this gate exists to
prevent.

Usage:  gate_no_inference.py [repo_root]      exit 0 clean, 1 on any finding
Stdlib only. Offline. Deterministic.
"""

from __future__ import annotations

import ast
import pathlib
import re
import shlex
import sys

# ===========================================================================
# POLICY DATA - EXTENSION POINT. Edit these tables, not the logic below.
# ===========================================================================

GATE_NAME = "no-inference"

# Trees whose executable files are on the graded path, with the reason each
# one is there. Adding a tree here is how the gate grows.
GRADED_TREES: tuple[tuple[str, str], ...] = (
    ("skills", "shipped leaf logic modules and their contract tests"),
    ("scripts", "verification harness: gates, router, linters, checkers"),
    ("packages", "shipped distribution: catalog, router port, editor plugin"),
)

PY_SUFFIXES = frozenset({".py", ".pyi"})
OTHER_CODE_SUFFIXES = frozenset(
    {".js", ".mjs", ".cjs", ".jsx", ".ts", ".mts", ".cts", ".tsx",
     ".sh", ".bash", ".zsh", ".kt", ".kts"}
)
PRUNE_DIR_NAMES = frozenset(
    {".git", ".gradle", ".idea", ".mypy_cache", ".pytest_cache", ".venv",
     "__pycache__", "build", "dist", "node_modules", "venv"}
)

# Development-only tooling: path relative to the repo root -> why it is exempt.
# Printed on every PASS run so the list stays under review.
DEV_ONLY_EXEMPT: dict[str, str] = {
    "scripts/gepa-desc-opt.py":
        "authoring-time description optimiser, run by hand from a throwaway "
        "venv; never imported by a gate, by the router or by a leaf, and its "
        "output is human-reviewed text that then has to survive the whole "
        "gate battery like any other edit",
    "scripts/gepa-live-run.py":
        "single-skill variant of the same authoring-time optimiser; same "
        "reasoning, and it is not wired into any make target",
}

# Hosted- and local-model SDKs and clients. Matched as dotted module prefixes:
# an entry "google.generativeai" also catches "google.generativeai.types".
MODEL_SDK_MODULES = frozenset({
    "ai21", "anthropic", "azure.ai.inference", "azure.ai.ml", "bedrock",
    "cohere", "deepseek", "dspy", "fireworks", "gepa", "google.genai",
    "google.generativeai", "groq", "guidance", "huggingface_hub",
    "instructor", "langchain", "langchain_anthropic", "langchain_community",
    "langchain_core", "langchain_openai", "litellm", "llama_cpp",
    "llama_index", "llamaindex", "mistralai", "mlx_lm", "ollama", "openai",
    "openrouter", "outlines", "perplexity", "replicate",
    "sentence_transformers", "text_generation", "together", "vertexai",
    "vllm", "xai_sdk",
})

# Trained-model runtimes. Not LLM vendors, but a learned model in the graded
# path breaks the same claim - the rule base has to be fixed at design time.
LEARNED_MODEL_MODULES = frozenset({
    "catboost", "flax", "jax", "keras", "lightgbm", "onnx", "onnxruntime",
    "skl2onnx", "sklearn", "tensorflow", "torch", "torchvision",
    "transformers", "xgboost",
})

# Network egress primitives and clients. `socket` is here on purpose: the
# existing corpus import check allowlists it (see the REUSE note below).
NETWORK_EGRESS_MODULES = frozenset({
    "aiohttp", "boto3", "botocore", "ftplib", "grpc", "http.client",
    "httpcore", "httplib2", "httpx", "imaplib", "nntplib", "paramiko",
    "poplib", "pycurl", "requests", "smtplib", "socket", "socketserver",
    "telnetlib", "urllib.request", "urllib3", "websocket", "websockets",
    "xmlrpc.client",
})

# Local model runner executables, matched on the command's basename.
# Deliberately excludes one-syllable product names that are ordinary English
# words ("jan", "tabby"): in a regex-scanned file they would fire on prose,
# and a gate that cries wolf gets switched off.
MODEL_RUNNER_BINARIES = frozenset({
    "aichat", "gpt4all", "koboldcpp", "litellm", "llama-cli", "llama-server",
    "llamafile", "llm", "lmstudio", "localai", "mlx_lm", "mlx_lm.generate",
    "ollama", "sglang", "text-generation-launcher", "vllm",
})

# Managed cloud inference services, matched on the service-name string handed
# to a cloud SDK client factory - catches the bedrock case, which needs no
# model-named import at all.
MANAGED_INFERENCE_SERVICES = frozenset({
    "bedrock", "bedrock-agent", "bedrock-agent-runtime", "bedrock-runtime",
    "comprehend", "polly", "rekognition", "sagemaker-runtime", "textract",
    "transcribe", "translate",
})

# Environment variables that only an inference call would want.
INFERENCE_ENV_VARS = frozenset({
    "AI21_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT",
    "COHERE_API_KEY", "DEEPSEEK_API_KEY", "FIREWORKS_API_KEY",
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY",
    "GROQ_API_KEY", "HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN",
    "HUGGING_FACE_HUB_TOKEN", "LITELLM_API_KEY", "MISTRAL_API_KEY",
    "OLLAMA_HOST", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORGANIZATION",
    "OPENROUTER_API_KEY", "PERPLEXITY_API_KEY", "REPLICATE_API_TOKEN",
    "TOGETHER_API_KEY", "VERTEX_PROJECT", "XAI_API_KEY",
})

# A vendor token plus a credential suffix is also an inference credential.
# Tokens are matched as whole underscore-separated SEGMENTS, never as
# substrings, so OPENAI cannot match inside a longer word.
INFERENCE_VENDOR_TOKENS: tuple[str, ...] = (
    "AI21", "ANTHROPIC", "AZURE_OPENAI", "BEDROCK", "CLAUDE", "COHERE",
    "DEEPSEEK", "FIREWORKS", "GEMINI", "GENAI", "GROQ", "HUGGINGFACE",
    "LITELLM", "LLM", "MISTRAL", "OLLAMA", "OPENAI", "OPENROUTER",
    "PERPLEXITY", "REPLICATE", "TOGETHER", "VERTEX", "XAI",
)
CREDENTIAL_SUFFIXES: tuple[str, ...] = (
    "_API_KEY", "_API_TOKEN", "_AUTH_TOKEN", "_ACCESS_TOKEN", "_SECRET_KEY",
    "_API_BASE", "_BASE_URL", "_ENDPOINT",
)

# Python call targets that start another program, grouped by owning module.
EXEC_CALL_TARGETS = frozenset(
    ["subprocess." + name for name in (
        "Popen", "call", "check_call", "check_output", "getoutput",
        "getstatusoutput", "run")]
    + ["os." + name for name in (
        "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp",
        "execvpe", "popen", "posix_spawn", "posix_spawnp", "spawnl",
        "spawnlp", "spawnv", "spawnvp", "startfile", "system")]
    + ["asyncio." + name for name in (
        "create_subprocess_exec", "create_subprocess_shell")]
    + ["shutil.which"]
)
DYNAMIC_IMPORT_TARGETS = frozenset({"importlib.import_module", "__import__"})
CLOUD_CLIENT_FACTORIES = frozenset({"client", "create_client", "resource"})
ENV_READ_ATTRS = frozenset({"get", "getenv", "pop", "setdefault"})

# --- non-Python policy ------------------------------------------------------

# Package names as they are spelled in a JS/TS import specifier.
MODEL_SDK_JS_PACKAGES = frozenset({
    "@anthropic-ai/bedrock-sdk", "@anthropic-ai/sdk",
    "@anthropic-ai/vertex-sdk", "@aws-sdk/client-bedrock-runtime",
    "@google-cloud/aiplatform", "@google/genai", "@google/generative-ai",
    "@huggingface/inference", "@langchain/core", "@langchain/openai",
    "@mistralai/mistralai", "@tensorflow/tfjs", "@tensorflow/tfjs-node",
    "@xenova/transformers", "ai", "cohere-ai", "groq-sdk", "langchain",
    "llamaindex", "ollama", "onnxruntime-node", "openai", "replicate",
    "together-ai",
})
NETWORK_JS_PACKAGES = frozenset({
    "axios", "dgram", "dns", "got", "http", "http2", "https", "net",
    "node-fetch", "node:dgram", "node:dns", "node:http", "node:http2",
    "node:https", "node:net", "node:tls", "superagent", "tls", "undici", "ws",
})

# Model provider hosts, matched as literal substrings (no word boundaries).
MODEL_PROVIDER_HOSTS: tuple[str, ...] = (
    "127.0.0.1:11434", "api-inference.huggingface.co", "api.anthropic.com",
    "api.cohere.ai", "api.cohere.com", "api.deepseek.com",
    "api.fireworks.ai", "api.groq.com", "api.mistral.ai", "api.openai.com",
    "api.replicate.com", "api.together.xyz", "api.x.ai", "bedrock-runtime.",
    "generativelanguage.googleapis.com", "inference.ai.azure.com",
    "localhost:11434", "openrouter.ai",
)

# Non-Python network egress calls. Every pattern anchors on a syntactic
# delimiter; none uses a bare word boundary.
NETWORK_CALL_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?<![A-Za-z0-9_.$])fetch\s*\(", "global fetch() call"),
    (r"new\s+XMLHttpRequest\s*\(", "XMLHttpRequest"),
    (r"new\s+WebSocket\s*\(", "WebSocket"),
    (r"navigator\s*\.\s*sendBeacon\s*\(", "navigator.sendBeacon"),
    (r"java\s*\.\s*net\s*\.", "java.net"),
    (r"(?<![A-Za-z0-9_.])HttpClient\s*[.(]", "HttpClient"),
    (r"okhttp3\s*\.", "okhttp3"),
    (r"(?<![A-Za-z0-9_./-])(?:curl|wget)\s+[-A-Za-z0-9'\"$]",
     "curl/wget invocation"),
)

# ===========================================================================
# DO NOT EDIT BELOW THIS LINE TO CHANGE POLICY - the tables above are the policy
# ===========================================================================

# REUSE NOTE (asked for explicitly when this gate was commissioned).
# The repo already forbids non-stdlib imports in leaves, in
# scripts/check_stdlib_imports.py, invoked per file by gate 3. That check is
# an ALLOWLIST of stdlib module names, and it is narrower than this invariant
# in three ways that matter:
#   (a) gate 3 runs it only over test_*.py, so a leaf's *logic* module - the
#       thing that actually computes the answer - is never seen by it;
#   (b) its allowlist contains `socket`, so the most direct route to an
#       inference call is permitted by it;
#   (c) it matches with a line-anchored regex, not a parse.
# So this gate EXTENDS rather than duplicates it: it imports that module's
# STDLIB_ALLOW and reports whether the extension is still real (whether
# `socket` really is allowed there), then applies the network-egress rule by
# parse, over every graded file rather than over test files only. If
# check_stdlib_imports.py is ever tightened to forbid socket outright, the
# printed note changes; the enforcement here does not move.
_SIBLING = pathlib.Path(__file__).resolve().parent
if str(_SIBLING) not in sys.path:
    sys.path.insert(0, str(_SIBLING))
try:
    from check_stdlib_imports import STDLIB_ALLOW as _GATE3_STDLIB_ALLOW
except Exception:  # pragma: no cover - the note degrades, the gate does not
    _GATE3_STDLIB_ALLOW = frozenset()
_EXTENDS_GATE3 = "socket" in _GATE3_STDLIB_ALLOW


class Finding:
    __slots__ = ("rel", "line", "rule", "detail")

    def __init__(self, rel: str, line: int, rule: str, detail: str) -> None:
        self.rel, self.line, self.rule, self.detail = rel, line, rule, detail

    def key(self):
        return (self.rel, self.line, self.rule, self.detail)


# --- policy predicates (shared by the AST front end and the regex front end)

def _prefix_hit(dotted: str, table) -> str | None:
    """Longest dotted-prefix match of `dotted` against `table`, or None."""
    best = None
    for entry in table:
        if dotted == entry or dotted.startswith(entry + "."):
            if best is None or len(entry) > len(best):
                best = entry
    return best


def module_verdict(dotted: str) -> tuple[str, str] | None:
    """Return (rule, matched policy entry) if importing `dotted` is forbidden."""
    for table, rule in (
        (MODEL_SDK_MODULES, "model-sdk-import"),
        (LEARNED_MODEL_MODULES, "learned-model-import"),
        (NETWORK_EGRESS_MODULES, "network-egress-import"),
    ):
        hit = _prefix_hit(dotted, table)
        if hit is not None:
            return rule, hit
    return None


def _segments_contain(name: str, token: str) -> bool:
    """True when `token`'s underscore segments appear as consecutive segments
    of `name`. Segment comparison, not substring: OPENAI cannot match inside
    a longer word, and no word-boundary regex is involved."""
    parts = name.split("_")
    want = token.split("_")
    width = len(want)
    return any(parts[i:i + width] == want for i in range(len(parts) - width + 1))


def is_inference_env(name: str) -> bool:
    if name in INFERENCE_ENV_VARS:
        return True
    if not any(name.endswith(suffix) for suffix in CREDENTIAL_SUFFIXES):
        return False
    return any(_segments_contain(name, token) for token in INFERENCE_VENDOR_TOKENS)


def _basename(token: str) -> str:
    base = token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return base[:-4] if base.endswith(".exe") else base


def runner_in_argv(argv) -> str | None:
    """`argv` is an already-split command line. Only tokens in COMMAND
    position are considered, so a runner name appearing as an argument or
    inside a message is not a hit."""
    expect_command = True
    for token in argv:
        if token in ("|", "||", "&&", ";", "&"):
            expect_command = True
            continue
        if expect_command:
            if _basename(token) in MODEL_RUNNER_BINARIES:
                return _basename(token)
            expect_command = False
    return None


def runner_in_command_string(text: str) -> str | None:
    try:
        argv = shlex.split(text, comments=False, posix=True)
    except ValueError:
        argv = text.split()
    return runner_in_argv(argv)


# --- Python front end (ast) -------------------------------------------------

def _dotted_of(node) -> str | None:
    """Dotted source spelling of a Name/Attribute chain, else None."""
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return None
    parts.append(cur.id)
    return ".".join(reversed(parts))


def _const_str(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _const_str_list(node):
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    out = []
    for element in node.elts:
        value = _const_str(element)
        if value is None:
            return None
        out.append(value)
    return out


def _alias_map(tree) -> dict[str, str]:
    """Local name -> canonical dotted target, for the import forms the call
    analysis has to resolve (`import subprocess as sp`, `from os import
    getenv`, ...). Scope is ignored on purpose: a nested import still binds a
    name that the rest of the file can call."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
                else:
                    head = alias.name.split(".")[0]
                    aliases[head] = head
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                aliases[alias.asname or alias.name] = node.module + "." + alias.name
    return aliases


def _resolve(dotted: str, aliases: dict[str, str]) -> str:
    head, _, tail = dotted.partition(".")
    target = aliases.get(head)
    if target is None:
        return dotted
    return target + ("." + tail if tail else "")


def _scan_imports(node, rel: str, line: int, found: list) -> None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            verdict = module_verdict(alias.name)
            if verdict:
                found.append(Finding(rel, line, verdict[0],
                                     "imports %s (policy entry %s)"
                                     % (alias.name, verdict[1])))
        return
    if not (node.module and not node.level):
        return
    verdict = module_verdict(node.module)
    if verdict:
        found.append(Finding(rel, line, verdict[0],
                             "imports from %s (policy entry %s)"
                             % (node.module, verdict[1])))
        return
    for alias in node.names:
        deeper = module_verdict(node.module + "." + alias.name)
        if deeper:
            found.append(Finding(rel, line, deeper[0],
                                 "imports %s.%s (policy entry %s)"
                                 % (node.module, alias.name, deeper[1])))


def _scan_call(node, rel: str, line: int, aliases: dict[str, str], found: list) -> None:
    target = _dotted_of(node.func)
    if target is None:
        return
    resolved = _resolve(target, aliases)
    first = node.args[0] if node.args else None

    if resolved in DYNAMIC_IMPORT_TARGETS or target in DYNAMIC_IMPORT_TARGETS:
        name = _const_str(first) if first is not None else None
        if name:
            verdict = module_verdict(name)
            if verdict:
                found.append(Finding(rel, line, "dynamic-import",
                                     "%s(%r) resolves to policy entry %s"
                                     % (target, name, verdict[1])))

    if resolved in EXEC_CALL_TARGETS:
        argv = _const_str_list(first) if first is not None else None
        hit = None
        if argv is not None:
            hit = runner_in_argv(argv)
        else:
            literal = _const_str(first) if first is not None else None
            if literal is not None:
                hit = runner_in_command_string(literal)
        if hit:
            found.append(Finding(rel, line, "model-runner-exec",
                                 "%s starts the model runner %r" % (target, hit)))

    if isinstance(node.func, ast.Attribute) and node.func.attr in CLOUD_CLIENT_FACTORIES:
        service = _const_str(first) if first is not None else None
        if service is None:
            for keyword in node.keywords:
                if keyword.arg in ("service_name", "service"):
                    service = _const_str(keyword.value)
        if service and service in MANAGED_INFERENCE_SERVICES:
            found.append(Finding(rel, line, "managed-inference-call",
                                 "%s(%r) opens a managed inference service"
                                 % (target, service)))

    tail = target.rsplit(".", 1)[-1]
    if tail in ENV_READ_ATTRS:
        owner = target.rsplit(".", 1)[0] if "." in target else ""
        owner_resolved = _resolve(owner, aliases) if owner else ""
        reads_env = (
            (tail == "getenv" and owner_resolved in ("os", ""))
            or owner_resolved.endswith("environ")
        )
        name = _const_str(first) if first is not None else None
        if reads_env and name and is_inference_env(name):
            found.append(Finding(rel, line, "inference-env-read",
                                 "reads %s, which only an inference call needs" % name))


def scan_python(path: pathlib.Path, rel: str) -> list:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [Finding(rel, 0, "unreadable", "cannot be read, so it cannot be "
                                              "cleared: %s" % exc)]
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as exc:
        return [Finding(rel, exc.lineno or 0, "unparseable",
                        "cannot be parsed, so it cannot be cleared: %s" % exc.msg)]

    aliases = _alias_map(tree)
    found: list = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            _scan_imports(node, rel, line, found)
        elif isinstance(node, ast.Call):
            _scan_call(node, rel, line, aliases, found)
        elif isinstance(node, ast.Subscript):
            owner = _dotted_of(node.value)
            if owner is not None and _resolve(owner, aliases).endswith("environ"):
                name = _const_str(node.slice)
                if name and is_inference_env(name):
                    found.append(Finding(rel, line, "inference-env-read",
                                         "reads %s, which only an inference call needs"
                                         % name))
    return found


# --- non-Python front end (regex; see HOW IT MATCHES above) -----------------

_JS_MODULE_REFS = (
    re.compile(r"""require\s*\(\s*(['"])([^'"\n]+)\1"""),
    re.compile(r"""import\s*\(\s*(['"])([^'"\n]+)\1"""),
    re.compile(r"""from\s+(['"])([^'"\n]+)\1"""),
    re.compile(r"""^\s*import\s+(['"])([^'"\n]+)\1""", re.MULTILINE),
)
_ENV_REFS = (
    re.compile(r"""process\s*\.\s*env\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)"""),
    re.compile(r"""process\s*\.\s*env\s*\[\s*(['"])([A-Za-z_][A-Za-z0-9_]*)\1"""),
    re.compile(r"""System\s*\.\s*getenv\s*\(\s*(['"])([A-Za-z_][A-Za-z0-9_]*)\1"""),
    re.compile(r"""\$\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:\-}]"""),
    re.compile(r"""\$([A-Z_][A-Z0-9_]*)"""),
)
_NETWORK_CALL_RES = tuple((re.compile(pat), label) for pat, label in NETWORK_CALL_PATTERNS)
# Command-position match for a runner binary. The prefix class is line start
# or a shell/JS command separator or an opening quote - NOT plain whitespace,
# and never a bare word boundary. Plain whitespace would make the prose "the
# llm is deterministic" a finding; a command separator cannot. An opening
# quote counts as a command position on purpose, because a JS child-process
# helper is normally handed the command as a quoted string; the cost is that
# a runner name quoted inside a shipped script is also a finding, which is
# the safe side of the trade. The gap between prefix and binary is
# HORIZONTAL whitespace only: a trailing quote must not be allowed to reach
# across a newline and claim the next line's command. The binary itself is
# captured so the reported line is the line the command is on.
_RUNNER_RES = tuple(
    (re.compile(r"""(?:^|[;|&(`'"]|\$\()[^\S\n]*(?:[A-Za-z0-9_./-]*/)?("""
                + re.escape(binary) + r""")(?=[\s;|&)`'"]|$)""", re.MULTILINE), binary)
    for binary in sorted(MODEL_RUNNER_BINARIES)
)


def _line_of(source: str, index: int) -> int:
    """Line number of a byte offset. Always called with the offset of the
    CAPTURED token, never with the match start: a pattern whose prefix is a
    delimiter can begin on the previous line, and a finding reported against
    the wrong line reads as a false positive and gets dismissed."""
    return source.count("\n", 0, index) + 1


def scan_other(path: pathlib.Path, rel: str) -> list:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    found: list = []

    for pattern in _JS_MODULE_REFS:
        for match in pattern.finditer(source):
            module = match.group(2)
            line = _line_of(source, match.start(2))
            if module in MODEL_SDK_JS_PACKAGES:
                found.append(Finding(rel, line, "model-sdk-import",
                                     "imports the model SDK %r" % module))
            elif module in NETWORK_JS_PACKAGES:
                found.append(Finding(rel, line, "network-egress-import",
                                     "imports the network module %r" % module))
            else:
                verdict = module_verdict(module)
                if verdict:
                    found.append(Finding(rel, line, verdict[0],
                                         "imports %r (policy entry %s)"
                                         % (module, verdict[1])))

    for pattern in _ENV_REFS:
        for match in pattern.finditer(source):
            name = match.group(match.lastindex)
            if is_inference_env(name):
                found.append(Finding(rel, _line_of(source, match.start(match.lastindex)),
                                     "inference-env-read",
                                     "reads %s, which only an inference call needs" % name))

    for pattern, label in _NETWORK_CALL_RES:
        for match in pattern.finditer(source):
            found.append(Finding(rel, _line_of(source, match.start()), "network-call",
                                 "network egress via %s" % label))

    for pattern, binary in _RUNNER_RES:
        for match in pattern.finditer(source):
            found.append(Finding(rel, _line_of(source, match.start(1)),
                                 "model-runner-exec",
                                 "starts the model runner %r" % binary))

    for host in MODEL_PROVIDER_HOSTS:
        start = source.find(host)
        if start >= 0:
            found.append(Finding(rel, _line_of(source, start), "network-call",
                                 "names the model provider host %s" % host))

    return found


# --- scope ------------------------------------------------------------------

def graded_files(repo: pathlib.Path):
    """Yield (path, rel, kind) for every graded file. kind is 'py' or 'other'."""
    for tree_name, _why in GRADED_TREES:
        root = repo / tree_name
        if not root.is_dir():
            continue
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                entries = sorted(current.iterdir())
            except OSError:
                continue
            for entry in entries:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    if entry.name not in PRUNE_DIR_NAMES:
                        stack.append(entry)
                    continue
                suffix = entry.suffix
                if suffix in PY_SUFFIXES:
                    kind = "py"
                elif suffix in OTHER_CODE_SUFFIXES:
                    kind = "other"
                else:
                    continue
                yield entry, entry.relative_to(repo).as_posix(), kind


def main() -> int:
    if len(sys.argv) > 1:
        repo = pathlib.Path(sys.argv[1]).resolve()
    else:
        repo = pathlib.Path(__file__).resolve().parent.parent

    py_count = 0
    other_count = 0
    exempt_seen: set = set()
    findings: list = []

    for path, rel, kind in graded_files(repo):
        if rel in DEV_ONLY_EXEMPT:
            exempt_seen.add(rel)
            continue
        if kind == "py":
            py_count += 1
            findings.extend(scan_python(path, rel))
        else:
            other_count += 1
            findings.extend(scan_other(path, rel))

    findings.sort(key=Finding.key)
    deduped: list = []
    for finding in findings:
        if not deduped or finding.key() != deduped[-1].key():
            deduped.append(finding)

    if deduped:
        by_file: dict = {}
        for finding in deduped:
            by_file.setdefault(finding.rel, []).append(finding)
        print("FAIL %s: %d finding(s) in %d file(s) on the graded path can reach "
              "model inference" % (GATE_NAME, len(deduped), len(by_file)))
        for rel in sorted(by_file):
            print("  %s" % rel)
            for finding in by_file[rel]:
                print("    L%-5d %-22s %s" % (finding.line, finding.rule, finding.detail))
        print("")
        print("  The graded path is a fixed, design-time rule base. A model call on it")
        print("  - direct, over the network, through a runner binary, or via a managed")
        print("  service - breaks the invariant stated in docs/claim-1-no-inference.md")
        print("  and cannot be documented away.")
        print("  Fix: compute the answer deterministically, or move the tool off the")
        print("       graded path and record it in DEV_ONLY_EXEMPT with a reason a")
        print("       reviewer can weigh.")
        return 1

    trees = ", ".join(name + "/" for name, _why in GRADED_TREES)
    print("PASS %s: %d Python + %d other code file(s) across %d graded tree(s) are "
          "free of model inference" % (GATE_NAME, py_count, other_count, len(GRADED_TREES)))
    print("  graded: %s (executable suffixes only; prose and data are never scanned)"
          % trees)
    print("  network-egress rule %s scripts/check_stdlib_imports.py, which allowlists "
          "socket and sees test files only"
          % ("extends" if _EXTENDS_GATE3 else "no longer needs to extend"))
    for rel in sorted(DEV_ONLY_EXEMPT):
        state = "exempt" if rel in exempt_seen else "exempt (STALE: path not present)"
        print("  %s: %s - %s" % (state, rel, DEV_ONLY_EXEMPT[rel]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
