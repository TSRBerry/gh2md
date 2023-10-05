import datetime
from dataclasses import dataclass


@dataclass
class GithubComment:
    """
    Represents a comment on an issue or PR.
    """

    user_login: str
    user_url: str
    user_avatar_url: str
    created_at: datetime.datetime
    url: str
    body: str
