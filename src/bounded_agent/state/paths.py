import re

_ARTIFACT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def validate_artifact_id(value: str, *, label: str) -> str:
    """Reject path-like identifiers before they are used for artifact storage."""

    if not _ARTIFACT_ID_PATTERN.fullmatch(value) or value in {".", ".."}:
        raise ValueError(
            f"{label} must contain only letters, numbers, periods, underscores, and hyphens"
        )
    return value
