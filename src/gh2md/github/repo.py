from dataclasses import dataclass
from typing import List

from gh2md.github.issue import GithubIssue


@dataclass
class GithubRepo:
    """
    Root object representing a repo.
    """

    full_name: str
    url: str
    issues: List[GithubIssue]
