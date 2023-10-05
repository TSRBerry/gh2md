import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

import requests
from dateutil.parser import parse as dateutil_parse

from gh2md.github.comment import GithubComment
from gh2md.github.issue import GithubIssue
from gh2md.github.repo import GithubRepo
from gh2md.logger import logger


@dataclass
class GithubAPI:
    """
    Handles GraphQL API queries.
    """

    token: str = None
    per_page: int = 100

    _ENDPOINT = "https://api.github.com/graphql"
    _REPO_QUERY = """
        query(
          $owner: String!
          $repo: String!
          $issuePerPage: Int!
          $issueNextPageCursor: String
          $pullRequestPerPage: Int!
          $pullRequestNextPageCursor: String
          $issueStates: [IssueState!]
          $pullRequestStates: [PullRequestState!]
        ) {
          rateLimit {
            limit
            cost
            remaining
            resetAt
          }
          repository(owner: $owner, name: $repo) {
            nameWithOwner
            url
            issues(
              first: $issuePerPage
              after: $issueNextPageCursor
              filterBy: { states: $issueStates }
              orderBy: { field: CREATED_AT, direction: DESC }
            ) {
              totalCount
              pageInfo {
                endCursor
                hasNextPage
              }
              nodes {
                id
                number
                url
                title
                body
                state
                createdAt
                author {
                  login
                  url
                  avatarUrl
                }
                labels(first: $issuePerPage) {
                  nodes {
                    name
                    url
                  }
                }
                comments(first: $issuePerPage) {
                  totalCount
                  pageInfo {
                    endCursor
                    hasNextPage
                  }
                  nodes {
                    body
                    createdAt
                    url
                    author {
                      login
                      url
                      avatarUrl
                    }
                  }
                }
              }
            }
            pullRequests(
              first: $pullRequestPerPage
              after: $pullRequestNextPageCursor
              states: $pullRequestStates
              orderBy: { field: CREATED_AT, direction: DESC }
            ) {
              totalCount
              pageInfo {
                endCursor
                hasNextPage
              }
              nodes {
                id
                number
                url
                title
                body
                state
                createdAt
                author {
                  login
                  url
                  avatarUrl
                }
                labels(first: $pullRequestPerPage) {
                  nodes {
                    name
                    url
                  }
                }
                comments(first: $pullRequestPerPage) {
                  totalCount
                  pageInfo {
                    endCursor
                    hasNextPage
                  }
                  nodes {
                    body
                    createdAt
                    url
                    author {
                      login
                      url
                      avatarUrl
                    }
                  }
                }
              }
            }
          }
        }
    """

    _NODE_COMMENT_QUERY = """
        query($perPage: Int!, $id: ID!, $commentCursor: String!) {
          rateLimit {
            limit
            cost
            remaining
            resetAt
          }
          node(id: $id) {
            ... on Issue {
              comments(first: $perPage, after: $commentCursor) {
                totalCount
                pageInfo {
                  endCursor
                  hasNextPage
                }
                nodes {
                  body
                  createdAt
                  url
                  author {
                    login
                    url
                    avatarUrl
                  }
                }
              }
            }
            ... on PullRequest {
              comments(first: $perPage, after: $commentCursor) {
                totalCount
                pageInfo {
                  endCursor
                  hasNextPage
                }
                nodes {
                  body
                  createdAt
                  url
                  author {
                    login
                    url
                    avatarUrl
                  }
                }
              }
            }
          }
        }
    """

    def __post_init__(self):
        self._session = None  # Requests session
        self._total_pages_fetched = 0
        if not self.token:
            print(
                "No Github access token found, exiting. Use gh2md --help so see options for providing a token."
            )
            sys.exit(1)

        # For testing
        per_page_override = os.environ.get("_GH2MD_PER_PAGE_OVERRIDE", None)
        if per_page_override:
            self.per_page = int(per_page_override)

    def _request_session(self) -> requests.Session:
        if not self._session:
            self._session = requests.Session()
            self._session.headers.update({"Authorization": "token " + self.token})
        return self._session

    def _post(
        self, json: Dict[str, Any], headers: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Make a graphql request and handle errors/retries.
        """
        if headers is None:
            headers = {}
        err = False
        for attempt in range(1, 3):
            try:
                resp = self._request_session().post(
                    self._ENDPOINT, json=json, headers=headers
                )
                resp.raise_for_status()
                err = False
                self._total_pages_fetched += 1
                break
            except (
                Exception
            ):  # Could catch cases that aren't retryable, but I don't think it's too annoying
                err = True
                logger.warning(
                    f"Exception response from request attempt {attempt}", exc_info=True
                )
                time.sleep(3)

        if err:
            decoded = {}
            logger.error("Request failed multiple retries, returning empty data")
        else:
            decoded = resp.json()
            rl = decoded.get("data", {}).get("rateLimit")
            if rl:
                logger.info(
                    f"Rate limit info after request: limit={rl['limit']}, cost={rl['cost']}, remaining={rl['remaining']}, resetAt={rl['resetAt']}"
                )

            errors = decoded.get("errors")
            if errors:
                err = True
                logger.error(f"Found GraphQL errors in response data: {errors}")

        return decoded, err

    def _fetch_repo(
        self,
        owner: str,
        repo: str,
        include_issues: bool,
        include_closed_issues: bool,
        include_prs: bool,
        include_closed_prs: bool,
    ) -> Dict[str, Any]:
        """
        Makes the appropriate number of requests to retrieve all the requested
        issues and PRs.

        Any additional comments beyond the first page in each issue/PR have to
        be fetched separately and merged with the results at the end. This is
        because they live underneath the issue/PR with their own respective
        pagination.
        """

        variables = {
            "owner": owner,
            "repo": repo,
        }
        if include_issues:
            variables["issuePerPage"] = self.per_page
            if not include_closed_issues:
                variables["issueStates"] = ["OPEN"]
        else:
            variables["issuePerPage"] = 0

        if include_prs:
            variables["pullRequestPerPage"] = self.per_page
            if not include_closed_prs:
                variables["pullRequestStates"] = ["OPEN"]
        else:
            variables["pullRequestPerPage"] = 0

        issue_cursor, has_issue_page = None, True
        pr_cursor, has_pr_page = None, True
        success_responses = []
        was_interrupted = False
        while has_issue_page or has_pr_page:
            try:
                # Make the request
                if issue_cursor:
                    variables["issueNextPageCursor"] = issue_cursor
                if pr_cursor:
                    variables["pullRequestNextPageCursor"] = pr_cursor
                data, err = self._post(
                    json={"query": self._REPO_QUERY, "variables": variables}
                )
                if err:
                    break
                else:
                    success_responses.append(data)

                    issues = data["data"]["repository"]["issues"]
                    if issues["nodes"]:
                        issue_cursor = issues["pageInfo"]["endCursor"]
                        has_issue_page = issues["pageInfo"]["hasNextPage"]
                    else:
                        issue_cursor, has_issue_page = None, False

                    prs = data["data"]["repository"]["pullRequests"]
                    if prs["nodes"]:
                        pr_cursor = prs["pageInfo"]["endCursor"]
                        has_pr_page = prs["pageInfo"]["hasNextPage"]
                    else:
                        pr_cursor, has_pr_page = None, False

                    logger.info(
                        f"Fetched repo page. total_requests_made={self._total_pages_fetched}, repo_issue_count={issues['totalCount']}, repo_pr_count={prs['totalCount']} issue_cursor={issue_cursor or '-'} pr_cursor={pr_cursor or '-'}"
                    )
            except (SystemExit, KeyboardInterrupt):
                logger.warning("Interrupted, will convert retrieved data and exit")
                was_interrupted = True
                break

        # Merge all the pages (including comments) into one big response object
        # by extending the list of nodes in the first page. This makes it easier
        # for the rest of the code to deal with it rather than passing around
        # one page at a time. The size of the response data is small enough that
        # memory shouldn't be a concern.
        merged_pages = success_responses[0] if success_responses else {}
        for page in success_responses[1:]:
            merged_pages["data"]["repository"]["issues"]["nodes"].extend(
                page["data"]["repository"]["issues"]["nodes"]
            )
            merged_pages["data"]["repository"]["pullRequests"]["nodes"].extend(
                page["data"]["repository"]["pullRequests"]["nodes"]
            )
        if not was_interrupted:
            self._fetch_and_merge_comments(merged_pages)
        return merged_pages

    def _fetch_and_merge_comments(self, merged_pages: Dict[str, Any]) -> None:
        """
        For any issues/PRs that are found to have an additional page of comments
        available, fetch the comments and merge them with the original data.
        """
        if not merged_pages.get("data"):
            return

        all_nodes = (
            merged_pages["data"]["repository"]["issues"]["nodes"]
            + merged_pages["data"]["repository"]["pullRequests"]["nodes"]
        )

        for original_node in all_nodes:
            if not original_node["comments"]["pageInfo"]["hasNextPage"]:
                continue

            has_page, comment_cursor = (
                True,
                original_node["comments"]["pageInfo"]["endCursor"],
            )
            while has_page:
                try:
                    variables = {
                        "id": original_node["id"],
                        "perPage": self.per_page,
                        "commentCursor": comment_cursor,
                    }
                    data, err = self._post(
                        json={"query": self._NODE_COMMENT_QUERY, "variables": variables}
                    )
                    if err:
                        break
                    else:
                        comments = data["data"]["node"]["comments"]
                        if comments["nodes"]:
                            comment_cursor = comments["pageInfo"]["endCursor"]
                            has_page = comments["pageInfo"]["hasNextPage"]
                        else:
                            comment_cursor, has_page = None, False

                        logger.info(
                            f"Fetched page for additional comments. total_requests_made={self._total_pages_fetched}, issue_comment_count={comments['totalCount']}, comment_cusor={comment_cursor}"
                        )

                        # Merge these comments to the original data
                        original_node["comments"]["nodes"].extend(comments["nodes"])

                except (SystemExit, KeyboardInterrupt):
                    logger.warning("Interrupted, will convert retrieved data and exit")
                    break

    def fetch_and_decode_repository(
        self,
        repo_name: str,
        include_issues: bool,
        include_prs: bool,
        include_closed_issues: bool,
        include_closed_prs: bool,
    ) -> GithubRepo:
        """
        Entry point for fetching a repo.
        """
        logger.info(f"Initiating fetch for repo: {repo_name}")
        owner, repo = repo_name.split("/")
        response = self._fetch_repo(
            owner=owner,
            repo=repo,
            include_issues=include_issues,
            include_prs=include_prs,
            include_closed_issues=include_closed_issues,
            include_closed_prs=include_closed_prs,
        )

        try:
            repo_data = response["data"]["repository"]
        except KeyError:
            logger.error("Repository data missing in response, can't proceed")
            raise

        issues = []
        prs = []
        for i in repo_data["issues"]["nodes"]:
            try:
                issues.append(
                    self._parse_issue_or_pull_request(i, is_pull_request=False)
                )
            except Exception:
                logger.warning(f"Error parsing issue, skipping: {i}", exc_info=True)

        for pr in repo_data["pullRequests"]["nodes"]:
            try:
                prs.append(self._parse_issue_or_pull_request(pr, is_pull_request=True))
            except Exception:
                logger.warning(
                    f"Error parsing pull request, skipping: {pr}", exc_info=True
                )

        return GithubRepo(
            full_name=repo_data["nameWithOwner"],
            url=repo_data["url"],
            # We have to sort in application code because these are separate
            # objects in the GraphQL API.
            issues=sorted(issues + prs, key=lambda x: x.number, reverse=True),
        )

    def _parse_issue_or_pull_request(
        self, issue_or_pr: Dict[str, Any], is_pull_request: bool
    ) -> GithubIssue:
        i = issue_or_pr
        comments = []
        for c in i["comments"]["nodes"]:
            try:
                comments.append(
                    GithubComment(
                        created_at=dateutil_parse(c["createdAt"]),
                        body=c["body"],
                        user_login=c["author"]["login"]
                        if c.get("author")
                        else "(unknown)",
                        user_url=c["author"]["url"] if c.get("author") else "(unknown)",
                        user_avatar_url=c["author"]["avatarUrl"]
                        if c.get("author")
                        else "(unknown)",
                        url=c["url"],
                    )
                )
            except Exception:
                logger.warning(f"Error parsing comment, skipping: {c}", exc_info=True)
        return GithubIssue(
            pull_request=is_pull_request,
            user_login=i["author"]["login"] if i.get("author") else "(unknown)",
            user_url=i["author"]["url"] if i.get("author") else "(unknown)",
            user_avatar_url=i["author"]["avatarUrl"]
            if i.get("author")
            else "(unknown)",
            state=i["state"].lower(),
            body=i["body"],
            number=i["number"],
            title=i["title"],
            created_at=dateutil_parse(i["createdAt"]),
            url=i["url"],
            label_names=[node["name"] for node in i["labels"]["nodes"]],
            comments=comments,
        )
