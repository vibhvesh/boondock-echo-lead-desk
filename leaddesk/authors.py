"""Who is allowed to trigger archive or search-config issue actions."""

from __future__ import annotations

from collections.abc import Iterable

# The repo owner is always allowed, even if the collaborators API is empty.
DEFAULT_OWNER = "vibhvesh"


def is_allowed_author(
    login: str | None,
    collaborators: Iterable[str] | None = None,
    owner: str = DEFAULT_OWNER,
) -> bool:
    """True only for the owner or a listed repo collaborator. Case-insensitive."""
    name = (login or "").strip().lstrip("@").lower()
    if not name:
        return False
    allowed = {owner.lower()}
    if collaborators:
        allowed.update(c.strip().lstrip("@").lower() for c in collaborators if c)
    return name in allowed
