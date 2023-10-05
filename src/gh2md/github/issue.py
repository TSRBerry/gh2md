import datetime
from dataclasses import dataclass
from typing import List

from gh2md.github.comment import GithubComment


@dataclass
class GithubIssue:
    """
    Represents an Issue or PR. The old Github API used to treat these as a
    single type of object, so initially I'm keeping it that way as we port
    this code to use GraphQL. It might make sense to separate out later.
    """

    user_login: str
    user_url: str
    user_avatar_url: str
    pull_request: bool
    state: str
    body: str
    comments: List[GithubComment]
    number: int
    label_names: List[str]
    title: str
    created_at: datetime.datetime
    url: str
