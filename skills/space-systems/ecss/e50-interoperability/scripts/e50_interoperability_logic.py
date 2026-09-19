"""Interoperability of a space link with its cross-support partners.

Anchor: ECSS-E-ST-50C Rev.2 clause 5.6.4 -- interoperability. Paraphrased into
an implementable procedure; no standard text is reproduced.

The single normative item is that the interoperability the mission needs is
specified: which external assets the space link has to work with, and on what
terms. This turns into a deterministic profile comparison.

A profile is a mapping from a link attribute -- frequency band, modulation,
channel coding, frame format -- to the options that side can actually operate.
Two sides interoperate on an attribute when their option sets intersect. They
interoperate at all when every attribute intersects and no attribute is left
undeclared on either side.

Three outcomes, not two. A partner whose profile shares an option on every
attribute is supported. A partner that shares none on some attribute is
unsupported, and the attributes responsible are named. A partner that simply
never declared an attribute is unconfirmed -- which is not the same as
incompatible, and is repaired by asking rather than by redesigning.

Where a partner is unsupported the remedy is reported as the options the
mission would have to add, per attribute, because the mission side is the side
that can be changed.

Stdlib only, offline, deterministic.
"""

__all__ = [
    "SUPPORTED",
    "UNSUPPORTED",
    "UNCONFIRMED",
    "PARTIAL",
    "REQUIRED_PROFILE_ATTRIBUTES",
    "validate_option",
    "validate_profile",
    "validate_partner_catalogue",
    "common_options",
    "mismatched_attributes",
    "unconfirmed_attributes",
    "partner_verdict",
    "negotiated_profile",
    "options_to_add",
    "cross_support_fraction",
    "assess_interoperability",
]

SUPPORTED = "supported"
UNSUPPORTED = "unsupported"
UNCONFIRMED = "unconfirmed"
PARTIAL = "partial"

# Attributes every side has to declare before interoperability can be assessed.
REQUIRED_PROFILE_ATTRIBUTES = (
    "frequency-band",
    "modulation",
    "channel-coding",
    "frame-format",
)


def validate_option(value, name="option"):
    """Return a stripped non-empty option token."""
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    token = value.strip()
    if not token:
        raise ValueError("%s must not be blank" % name)
    return token


def validate_profile(profile, name="profile"):
    """Return a profile as attribute -> frozenset of options.

    Every required attribute has to be present with at least one option: a
    side that declares no modulation has not declared a profile, and treating
    the gap as "anything goes" invents an agreement nobody made.
    """
    if not isinstance(profile, dict):
        raise ValueError("%s must be a mapping of attribute to options" % name)
    out = {}
    for attribute, options in profile.items():
        key = validate_option(attribute, "%s attribute" % name)
        if isinstance(options, (str, bytes)) or not hasattr(options, "__iter__"):
            raise ValueError(
                "%s attribute %r must carry a sequence of options" % (name, key)
            )
        tokens = frozenset(
            validate_option(o, "%s option for %s" % (name, key)) for o in options
        )
        if not tokens:
            raise ValueError("%s attribute %r declares no options" % (name, key))
        if key in out:
            raise ValueError("%s repeats attribute %r" % (name, key))
        out[key] = tokens
    for attribute in REQUIRED_PROFILE_ATTRIBUTES:
        if attribute not in out:
            raise ValueError("%s does not declare %r" % (name, attribute))
    return out


def validate_partner_catalogue(partners):
    """Return the cross-support partners as name -> validated profile."""
    if not isinstance(partners, dict):
        raise ValueError("partners must be a mapping of partner name to profile")
    if not partners:
        raise ValueError("partners must name at least one cross-support asset")
    return {
        validate_option(name, "partner name"): validate_profile(
            profile, "partner %s profile" % name
        )
        for name, profile in partners.items()
    }


def common_options(mission_profile, partner_profile, attribute):
    """Return the options both sides operate on one attribute, sorted."""
    mission = validate_profile(mission_profile, "mission profile")
    partner = validate_profile(partner_profile, "partner profile")
    key = validate_option(attribute, "attribute")
    if key not in mission:
        raise ValueError("mission profile does not declare %r" % key)
    if key not in partner:
        return ()
    return tuple(sorted(mission[key] & partner[key]))


def mismatched_attributes(mission_profile, partner_profile):
    """Return attributes both sides declare with no option in common."""
    mission = validate_profile(mission_profile, "mission profile")
    partner = validate_profile(partner_profile, "partner profile")
    shared = sorted(set(mission) & set(partner))
    return tuple(a for a in shared if not (mission[a] & partner[a]))


def unconfirmed_attributes(mission_profile, partner_profile):
    """Return mission attributes the partner never declared."""
    mission = validate_profile(mission_profile, "mission profile")
    partner = validate_profile(partner_profile, "partner profile")
    return tuple(sorted(set(mission) - set(partner)))


def partner_verdict(mission_profile, partner_profile):
    """Return supported, unsupported or unconfirmed for one partner."""
    clashes = mismatched_attributes(mission_profile, partner_profile)
    if clashes:
        return UNSUPPORTED
    if unconfirmed_attributes(mission_profile, partner_profile):
        return UNCONFIRMED
    return SUPPORTED


def negotiated_profile(mission_profile, partner_profile):
    """Return one operating option per attribute for a supported partner.

    The lowest-sorting common option is taken so two runs of the same pair
    always produce the same operating agreement.
    """
    if partner_verdict(mission_profile, partner_profile) != SUPPORTED:
        raise ValueError("no operating profile exists for a partner that is not supported")
    mission = validate_profile(mission_profile, "mission profile")
    partner = validate_profile(partner_profile, "partner profile")
    return {a: sorted(mission[a] & partner[a])[0] for a in sorted(mission)}


def options_to_add(mission_profile, partner_profile):
    """Return, per mismatched attribute, the partner options the mission lacks."""
    mission = validate_profile(mission_profile, "mission profile")
    partner = validate_profile(partner_profile, "partner profile")
    out = {}
    for attribute in mismatched_attributes(mission, partner):
        out[attribute] = tuple(sorted(partner[attribute] - mission[attribute]))
    return out


def cross_support_fraction(mission_profile, partners):
    """Return the share of declared partners this link can already work with."""
    catalogue = validate_partner_catalogue(partners)
    supported = sum(
        1
        for profile in catalogue.values()
        if partner_verdict(mission_profile, profile) == SUPPORTED
    )
    return supported / float(len(catalogue))


def assess_interoperability(mission_profile, partners, required_partners):
    """Grade a link's declared interoperability against its cross-support set."""
    mission = validate_profile(mission_profile, "mission profile")
    catalogue = validate_partner_catalogue(partners)
    if isinstance(required_partners, (str, bytes)) or not hasattr(
        required_partners, "__iter__"
    ):
        raise ValueError("required_partners must be a sequence of partner names")
    required = []
    for item in required_partners:
        token = validate_option(item, "required partner")
        if token not in catalogue:
            raise ValueError(
                "required partner %r has no declared profile; interoperability "
                "cannot be assessed against it" % token
            )
        if token not in required:
            required.append(token)
    if not required:
        raise ValueError(
            "required_partners must name at least one asset; an unstated "
            "interoperability requirement is the defect, not an empty result"
        )
    per_partner = {}
    findings = []
    for name in sorted(catalogue):
        verdict = partner_verdict(mission, catalogue[name])
        per_partner[name] = verdict
        if verdict == UNSUPPORTED:
            clashes = mismatched_attributes(mission, catalogue[name])
            remedy = options_to_add(mission, catalogue[name])
            findings.append(
                "%s shares no option on %s; adding %s to the link restores it"
                % (
                    name,
                    ", ".join(clashes),
                    "; ".join(
                        "%s %s" % (a, "/".join(remedy[a])) for a in clashes if remedy[a]
                    )
                    or "a compatible option",
                )
            )
        elif verdict == UNCONFIRMED:
            findings.append(
                "%s never declared %s; the requirement is unconfirmed rather "
                "than unmet"
                % (name, ", ".join(unconfirmed_attributes(mission, catalogue[name])))
            )
    required_supported = [n for n in required if per_partner[n] == SUPPORTED]
    if len(required_supported) == len(required):
        verdict = SUPPORTED
    elif required_supported:
        verdict = PARTIAL
    else:
        verdict = UNSUPPORTED
    for name in required:
        if per_partner[name] != SUPPORTED:
            findings.append(
                "%s is a required cross-support asset and is %s"
                % (name, per_partner[name])
            )
    return {
        "partner_verdicts": per_partner,
        "required_partners": tuple(required),
        "required_supported": tuple(required_supported),
        "cross_support_fraction": cross_support_fraction(mission, catalogue),
        "interoperable": verdict == SUPPORTED,
        "verdict": verdict,
        "findings": tuple(findings),
    }
