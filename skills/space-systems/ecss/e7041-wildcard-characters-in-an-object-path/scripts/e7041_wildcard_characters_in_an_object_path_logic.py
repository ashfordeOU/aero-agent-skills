"""Wildcard characters in an on-board object path.

Anchor: ECSS-E-ST-70-41C clause 6.23.3.3 (use of a wildcard character within
an object path of the file management service). Paraphrased into an
implementable procedure; no standard text is reproduced.

Model implemented here
----------------------
An object path names a repository, the directories under it and, for a file
operation, the file itself. The service may declare a wildcard character that
stands for any value of one path component. The wildcard is a whole component:
it never spans a separator and it is not a partial match inside a longer name,
so a component that mixes the wildcard with literal characters is refused
rather than matched loosely.

Procedure implemented here
--------------------------
1. Validate the declared wildcard character.
2. Split an object path into its components and validate each of them.
3. Decide whether one pattern component matches one candidate name.
4. Decide whether a whole pattern matches a whole candidate path, which needs
   the same number of components on both sides.
5. Expand a pattern over the known object paths.
6. Decide whether an operation may proceed on the expansion: an operation that
   must address a single object refuses an expansion of any other size, and a
   fan-out operation is held to its declared limit.
"""

__all__ = [
    "PATH_SEPARATOR",
    "DEFAULT_WILDCARD",
    "MAX_PATH_COMPONENTS",
    "MAX_COMPONENT_CHARS",
    "validate_wildcard",
    "split_object_path",
    "is_wildcard_component",
    "component_matches",
    "path_matches",
    "wildcard_component_count",
    "expand_object_path",
    "assess_object_path_request",
]

# Separator between the components of an object path.
PATH_SEPARATOR = "/"

# Wildcard character assumed when the subservice declares none of its own.
DEFAULT_WILDCARD = "*"

# Model limits on the shape of an object path.
MAX_PATH_COMPONENTS = 16
MAX_COMPONENT_CHARS = 64


def validate_wildcard(wildcard=DEFAULT_WILDCARD):
    """Return the declared wildcard character after validating it."""
    if not isinstance(wildcard, str):
        raise ValueError("wildcard must be a string, got %r" % (wildcard,))
    if len(wildcard) != 1:
        raise ValueError(
            "wildcard must be a single character, got %d characters" % len(wildcard)
        )
    if wildcard == PATH_SEPARATOR:
        raise ValueError("the path separator cannot also be the wildcard character")
    if wildcard.isalnum():
        raise ValueError(
            "wildcard %r is a name character, so it could not be told apart from a "
            "literal name" % wildcard
        )
    return wildcard


def split_object_path(path):
    """Return the components of an object path after validating its shape."""
    if not isinstance(path, str):
        raise ValueError("object path must be a string, got %r" % (path,))
    if not path:
        raise ValueError("object path must not be empty")
    body = path[1:] if path.startswith(PATH_SEPARATOR) else path
    if not body:
        raise ValueError("object path names no component")
    if body.endswith(PATH_SEPARATOR):
        raise ValueError("object path must not end with the path separator")
    components = body.split(PATH_SEPARATOR)
    if len(components) > MAX_PATH_COMPONENTS:
        raise ValueError(
            "object path has %d components, past the model limit of %d"
            % (len(components), MAX_PATH_COMPONENTS)
        )
    for index, component in enumerate(components):
        if not component:
            raise ValueError("object path has an empty component at position %d" % index)
        if len(component) > MAX_COMPONENT_CHARS:
            raise ValueError(
                "component %d is %d characters, past the model limit of %d"
                % (index, len(component), MAX_COMPONENT_CHARS)
            )
        if component.strip() != component:
            raise ValueError(
                "component %d carries leading or trailing whitespace" % index
            )
    return tuple(components)


def is_wildcard_component(component, wildcard=DEFAULT_WILDCARD):
    """Return whether a pattern component is the wildcard, whole and alone."""
    mark = validate_wildcard(wildcard)
    if not isinstance(component, str) or not component:
        raise ValueError("component must be a non-empty string, got %r" % (component,))
    if component == mark:
        return True
    if mark in component:
        raise ValueError(
            "component %r mixes the wildcard with literal characters; the wildcard "
            "stands for a whole component only" % component
        )
    return False


def component_matches(pattern_component, name, wildcard=DEFAULT_WILDCARD):
    """Return whether one pattern component matches one candidate name."""
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string, got %r" % (name,))
    mark = validate_wildcard(wildcard)
    if mark in name:
        raise ValueError(
            "candidate name %r carries the wildcard character; a stored object name "
            "is always literal" % name
        )
    if is_wildcard_component(pattern_component, mark):
        return True
    return pattern_component == name


def path_matches(pattern, candidate, wildcard=DEFAULT_WILDCARD):
    """Return whether a pattern matches a candidate object path.

    The wildcard never spans a separator, so a pattern matches only a
    candidate with the same number of components.
    """
    mark = validate_wildcard(wildcard)
    pattern_parts = split_object_path(pattern)
    candidate_parts = split_object_path(candidate)
    if len(pattern_parts) != len(candidate_parts):
        return False
    for pattern_part, candidate_part in zip(pattern_parts, candidate_parts):
        if not component_matches(pattern_part, candidate_part, mark):
            return False
    return True


def wildcard_component_count(pattern, wildcard=DEFAULT_WILDCARD):
    """Return how many components of a pattern are the wildcard."""
    mark = validate_wildcard(wildcard)
    return sum(
        1 for part in split_object_path(pattern) if is_wildcard_component(part, mark)
    )


def expand_object_path(pattern, candidates, wildcard=DEFAULT_WILDCARD):
    """Return the candidate object paths a pattern matches, ordered."""
    if not isinstance(candidates, (list, tuple, set, frozenset)):
        raise ValueError("candidates must be a sequence or set")
    mark = validate_wildcard(wildcard)
    matched = set()
    for index, candidate in enumerate(sorted(candidates)):
        try:
            if path_matches(pattern, candidate, mark):
                matched.add(candidate)
        except ValueError as exc:
            raise ValueError("candidates[%d]: %s" % (index, exc))
    return tuple(sorted(matched))


def assess_object_path_request(spec):
    """Assess a clause 6.23.3.3 object path against the known objects.

    spec keys: pattern, candidates. Optional keys: wildcard,
    single_object_operation (default True), fan_out_limit.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("pattern", "candidates"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    mark = validate_wildcard(spec.get("wildcard", DEFAULT_WILDCARD))
    single = spec.get("single_object_operation", True)
    if not isinstance(single, bool):
        raise ValueError(
            "single_object_operation must be a boolean, got %r" % (single,)
        )
    limit = spec.get("fan_out_limit")
    if limit is not None:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("fan_out_limit must be a positive integer, got %r" % (limit,))

    components = split_object_path(spec["pattern"])
    wildcards = wildcard_component_count(spec["pattern"], mark)
    matches = expand_object_path(spec["pattern"], spec["candidates"], mark)

    findings = []
    accepted = True
    if not matches:
        accepted = False
        findings.append("the object path matches no object currently on board")
    if single and len(matches) > 1:
        accepted = False
        findings.append(
            "the operation addresses a single object but the path expands to %d"
            % len(matches)
        )
    if single and wildcards and len(matches) == 1:
        findings.append(
            "a wildcard resolved to exactly one object; the expansion changes as "
            "soon as another object is created"
        )
    if limit is not None and len(matches) > limit:
        accepted = False
        findings.append(
            "the expansion of %d objects is past the declared fan-out limit of %d"
            % (len(matches), limit)
        )

    return {
        "components": components,
        "component_count": len(components),
        "wildcard_component_count": wildcards,
        "fully_qualified": wildcards == 0,
        "matches": matches,
        "match_count": len(matches),
        "single_object_operation": single,
        "accepted": accepted,
        "clean": not findings,
        "findings": findings,
    }
