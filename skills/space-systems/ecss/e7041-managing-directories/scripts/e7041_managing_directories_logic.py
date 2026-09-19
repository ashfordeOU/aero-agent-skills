"""Managing directories in an on-board file system.

Anchor: ECSS-E-ST-70-41C clause 6.23.4.5 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the requests are. Four of them act on the repository structure
itself rather than on file content: create a sub-repository under an
existing one, delete a sub-repository, rename one in place, and move
one under a different parent. Each has its own way of failing and the
failures are the substance of the clause -- the happy path is a
dictionary insertion.

Why deletion is the hard one. A repository can only be deleted when
it is empty: no files and no sub-repositories. That rule exists
because there is no undo on board and no second copy, so a recursive
delete issued against the wrong path takes content that cannot be
recovered before the next pass. Refusing a non-empty delete forces
the operator to see what is inside before it goes, which is the whole
point; auto-recursing "to be helpful" removes the only guard there is.

Why a move is not a rename. A rename changes the last segment and
leaves the parent alone. A move changes the parent and keeps the
name. Both re-path every repository underneath, and both can fail in
a way the other cannot: a move can be asked to put a repository
inside itself, which detaches the whole subtree from the root and is
the one failure that corrupts rather than refuses.

Depth and naming. A file system declares a maximum depth and a name
charset; a create that would exceed the depth is refused at the
request, not discovered later by a path that no longer fits the field
carrying it.

Stdlib only, offline, deterministic.
"""

PATH_SEPARATOR = "/"
MAX_NAME_OCTETS = 64
MAX_PATH_OCTETS = 256
DEFAULT_MAX_DEPTH = 8

CREATED = "repository-created"
DELETED = "repository-deleted"
RENAMED = "repository-renamed"
MOVED = "repository-moved"

FAILURE_PARENT_UNKNOWN = "failed-parent-repository-not-found"
FAILURE_ALREADY_EXISTS = "failed-name-already-in-use"
FAILURE_UNKNOWN = "failed-repository-not-found"
FAILURE_NOT_EMPTY = "failed-repository-not-empty"
FAILURE_IS_ROOT = "failed-target-is-the-root-repository"
FAILURE_DEPTH_EXCEEDED = "failed-maximum-depth-exceeded"
FAILURE_MOVE_INTO_OWN_SUBTREE = "failed-move-into-own-subtree"
FAILURE_PATH_TOO_LONG = "failed-path-octet-cap-exceeded"

_FORBIDDEN_NAME_CHARS = (PATH_SEPARATOR, "\\", "\t", "\n", "\r", "\0")


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def validate_segment(name, label="repository name"):
    """Validate one path segment and return it unchanged."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("%s must be a non-empty string" % label)
    if name != name.strip():
        raise ValueError("%s %r has leading or trailing whitespace" % (label, name))
    for bad in _FORBIDDEN_NAME_CHARS:
        if bad in name:
            raise ValueError("%s %r contains a forbidden character" % (label, name))
    if name in (".", ".."):
        raise ValueError("%s %r is a relative marker, not a name" % (label, name))
    if len(name.encode("utf-8")) > MAX_NAME_OCTETS:
        raise ValueError("%s %r is longer than %d octets" % (label, name, MAX_NAME_OCTETS))
    return name


def split_path(path):
    """Split a repository path into its validated segments."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("repository path must be a non-empty string")
    raw = path.split(PATH_SEPARATOR)
    if any(s == "" for s in raw[1:-1]):
        raise ValueError("repository path %r has an empty segment" % (path,))
    segments = [s for s in raw if s != ""]
    if not segments:
        raise ValueError("repository path %r names no repository" % (path,))
    for segment in segments:
        validate_segment(segment, "repository path segment")
    return segments


def join_path(segments):
    """Join validated segments into a canonical repository path."""
    if not isinstance(segments, (list, tuple)) or not segments:
        raise ValueError("segments must be a non-empty list")
    for segment in segments:
        validate_segment(segment, "repository path segment")
    joined = PATH_SEPARATOR.join(segments)
    if len(joined.encode("utf-8")) > MAX_PATH_OCTETS:
        raise ValueError("repository path %r is longer than %d octets" % (joined, MAX_PATH_OCTETS))
    return joined


def normalize_path(path):
    """Normalize a repository path to its canonical form."""
    return join_path(split_path(path))


def depth_of(path):
    """Depth of a repository path, the root counting as one."""
    return len(split_path(path))


def parent_of(path):
    """Canonical path of the parent, or None for a root repository."""
    segments = split_path(path)
    if len(segments) == 1:
        return None
    return join_path(segments[:-1])


def name_of(path):
    """Last segment of a repository path."""
    return split_path(path)[-1]


def is_within(candidate, root):
    """Is this path the root itself or a repository beneath it?"""
    candidate_segments = split_path(candidate)
    root_segments = split_path(root)
    if len(candidate_segments) < len(root_segments):
        return False
    return candidate_segments[: len(root_segments)] == root_segments


def validate_tree(tree, max_depth=DEFAULT_MAX_DEPTH):
    """Validate a repository tree: path to list of file names."""
    if not isinstance(tree, dict) or not tree:
        raise ValueError("repository tree must be a non-empty mapping")
    _integer("max_depth", max_depth, 1)
    normalized = {}
    for path, files in tree.items():
        canonical = normalize_path(path)
        if canonical in normalized:
            raise ValueError("duplicate repository path %r" % (canonical,))
        if not isinstance(files, list):
            raise ValueError("repository %s files must be a list" % canonical)
        names = []
        for name in files:
            validated = validate_segment(name, "file name")
            if validated in names:
                raise ValueError("repository %s lists file %r twice" % (canonical, validated))
            names.append(validated)
        if depth_of(canonical) > max_depth:
            raise ValueError(
                "repository %s is at depth %d, past the declared maximum %d"
                % (canonical, depth_of(canonical), max_depth)
            )
        normalized[canonical] = names
    for path in normalized:
        parent = parent_of(path)
        if parent is not None and parent not in normalized:
            raise ValueError(
                "repository %s has no parent %s in the tree" % (path, parent)
            )
    return normalized


def children_of(tree, path):
    """Immediate sub-repository names, in name order."""
    working = validate_tree(tree)
    canonical = normalize_path(path)
    if canonical not in working:
        raise ValueError("repository %r is not in this tree" % (canonical,))
    depth = depth_of(canonical)
    return sorted(
        name_of(p)
        for p in working
        if is_within(p, canonical) and depth_of(p) == depth + 1
    )


def is_empty(tree, path):
    """Does this repository hold neither a file nor a sub-repository?"""
    working = validate_tree(tree)
    canonical = normalize_path(path)
    if canonical not in working:
        raise ValueError("repository %r is not in this tree" % (canonical,))
    return not working[canonical] and not children_of(working, canonical)


def _result(tree, outcome, detail=None):
    return tree, {"outcome": outcome, "detail": detail}


def create_directory(tree, parent_path, name, max_depth=DEFAULT_MAX_DEPTH):
    """Create one sub-repository under an existing parent."""
    working = validate_tree(tree, max_depth)
    validate_segment(name)
    parent = normalize_path(parent_path)
    if parent not in working:
        return _result(working, FAILURE_PARENT_UNKNOWN, parent)
    candidate_segments = split_path(parent) + [name]
    if name in working[parent] or name in children_of(working, parent):
        return _result(working, FAILURE_ALREADY_EXISTS, name)
    if len(candidate_segments) > max_depth:
        return _result(working, FAILURE_DEPTH_EXCEEDED, len(candidate_segments))
    try:
        candidate = join_path(candidate_segments)
    except ValueError:
        return _result(working, FAILURE_PATH_TOO_LONG, PATH_SEPARATOR.join(candidate_segments))
    working = dict(working)
    working[candidate] = []
    return _result(working, CREATED, candidate)


def delete_directory(tree, path, max_depth=DEFAULT_MAX_DEPTH):
    """Delete one sub-repository, refusing a non-empty one."""
    working = validate_tree(tree, max_depth)
    canonical = normalize_path(path)
    if canonical not in working:
        return _result(working, FAILURE_UNKNOWN, canonical)
    if parent_of(canonical) is None:
        return _result(working, FAILURE_IS_ROOT, canonical)
    if not is_empty(working, canonical):
        held = len(working[canonical])
        subs = len(children_of(working, canonical))
        return _result(
            working,
            FAILURE_NOT_EMPTY,
            {"file_count": held, "sub_repository_count": subs},
        )
    working = dict(working)
    del working[canonical]
    return _result(working, DELETED, canonical)


def _repath_subtree(tree, old_root, new_root):
    moved = {}
    old_segments = split_path(old_root)
    new_segments = split_path(new_root)
    for path, files in tree.items():
        if is_within(path, old_root):
            tail = split_path(path)[len(old_segments):]
            moved[join_path(new_segments + tail)] = list(files)
        else:
            moved[path] = list(files)
    return moved


def rename_directory(tree, path, new_name, max_depth=DEFAULT_MAX_DEPTH):
    """Rename a sub-repository in place, re-pathing everything below it."""
    working = validate_tree(tree, max_depth)
    validate_segment(new_name)
    canonical = normalize_path(path)
    if canonical not in working:
        return _result(working, FAILURE_UNKNOWN, canonical)
    parent = parent_of(canonical)
    if parent is None:
        return _result(working, FAILURE_IS_ROOT, canonical)
    if new_name == name_of(canonical):
        return _result(working, RENAMED, canonical)
    if new_name in working[parent] or new_name in children_of(working, parent):
        return _result(working, FAILURE_ALREADY_EXISTS, new_name)
    new_root = join_path(split_path(parent) + [new_name])
    return _result(_repath_subtree(working, canonical, new_root), RENAMED, new_root)


def move_directory(tree, path, new_parent_path, max_depth=DEFAULT_MAX_DEPTH):
    """Move a sub-repository under a different parent, subtree included."""
    working = validate_tree(tree, max_depth)
    canonical = normalize_path(path)
    new_parent = normalize_path(new_parent_path)
    if canonical not in working:
        return _result(working, FAILURE_UNKNOWN, canonical)
    if parent_of(canonical) is None:
        return _result(working, FAILURE_IS_ROOT, canonical)
    if new_parent not in working:
        return _result(working, FAILURE_PARENT_UNKNOWN, new_parent)
    if is_within(new_parent, canonical):
        return _result(working, FAILURE_MOVE_INTO_OWN_SUBTREE, new_parent)
    name = name_of(canonical)
    if name in working[new_parent] or name in children_of(working, new_parent):
        return _result(working, FAILURE_ALREADY_EXISTS, name)
    new_root_segments = split_path(new_parent) + [name]
    deepest = max(depth_of(p) for p in working if is_within(p, canonical))
    relative = deepest - depth_of(canonical)
    if len(new_root_segments) + relative > max_depth:
        return _result(working, FAILURE_DEPTH_EXCEEDED, len(new_root_segments) + relative)
    new_root = join_path(new_root_segments)
    return _result(_repath_subtree(working, canonical, new_root), MOVED, new_root)


def apply_directory_plan(tree, plan, max_depth=DEFAULT_MAX_DEPTH):
    """Apply a sequence of directory requests and report each outcome."""
    working = validate_tree(tree, max_depth)
    if not isinstance(plan, list):
        raise ValueError("plan must be a list")
    outcomes = []
    for step in plan:
        if not isinstance(step, dict):
            raise ValueError("each planned request must be a mapping")
        action = step.get("action")
        if action == "create":
            working, outcome = create_directory(
                working, step.get("parent_path"), step.get("name"), max_depth
            )
        elif action == "delete":
            working, outcome = delete_directory(working, step.get("path"), max_depth)
        elif action == "rename":
            working, outcome = rename_directory(
                working, step.get("path"), step.get("new_name"), max_depth
            )
        elif action == "move":
            working, outcome = move_directory(
                working, step.get("path"), step.get("new_parent_path"), max_depth
            )
        else:
            raise ValueError("unknown directory action %r" % (action,))
        outcome["action"] = action
        outcomes.append(outcome)
    refused = [o for o in outcomes if o["outcome"].startswith("failed-")]
    return {
        "tree": working,
        "outcomes": outcomes,
        "applied_count": len(outcomes) - len(refused),
        "refused_count": len(refused),
        "repository_count": len(working),
        "deepest_path_depth": max(depth_of(p) for p in working),
        "plan_applied_in_full": not refused,
    }
