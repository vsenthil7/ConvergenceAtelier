"""Domain errors shared across services."""
from __future__ import annotations


class NotFoundError(Exception):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity} {entity_id} not found")
        self.entity = entity
        self.entity_id = entity_id


class ConflictError(Exception):
    """Raised when creating an entity that already exists (unique clash)."""

    def __init__(self, entity: str, identifier: str) -> None:
        super().__init__(f"{entity} {identifier} already exists")
        self.entity = entity
        self.identifier = identifier


class UnauthorizedError(Exception):
    """Raised when authentication fails or is missing."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message)
        self.message = message


class ForbiddenError(Exception):
    """Raised when an authenticated actor lacks permission."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message)
        self.message = message
