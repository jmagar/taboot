"""Core entity schemas for Taboot platform.

Core entities represent domain-agnostic concepts that span multiple data sources:
- Person: Individual people
- Organization: Companies, teams, groups
- Place: Physical or virtual locations
- Event: Time-based occurrences
- File: Documents, code, media
"""

from packages.schemas.core.event import Event
from packages.schemas.core.file import File
from packages.schemas.core.organization import Organization
from packages.schemas.core.person import Person
from packages.schemas.core.place import Place

__all__ = ["Event", "File", "Organization", "Person", "Place"]
