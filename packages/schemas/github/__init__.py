"""GitHub entity schemas.

This module contains Pydantic schemas for GitHub-specific entities.
"""

from packages.schemas.github.binary_asset import BinaryAsset
from packages.schemas.github.branch import Branch
from packages.schemas.github.comment import Comment
from packages.schemas.github.commit import Commit
from packages.schemas.github.documentation import Documentation
from packages.schemas.github.github_label import GitHubLabel
from packages.schemas.github.issue import Issue
from packages.schemas.github.milestone import Milestone
from packages.schemas.github.pull_request import PullRequest
from packages.schemas.github.release import Release
from packages.schemas.github.repository import Repository
from packages.schemas.github.tag import Tag

__all__ = [
    "BinaryAsset",
    "Branch",
    "Comment",
    "Commit",
    "Documentation",
    "GitHubLabel",
    "Issue",
    "Milestone",
    "PullRequest",
    "Release",
    "Repository",
    "Tag",
]
