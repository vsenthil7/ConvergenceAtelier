"""Domain errors shared across services."""
from __future__ import annotations


class NotFoundError(Exception):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity} {entity_id} not found")
        self.entity = entity
        self.entity_id = entity_id
