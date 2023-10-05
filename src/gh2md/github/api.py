import logging
import os
import sys
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

from dateutil.parser import parse as dateutil_parse
from gql import Client
from gql.dsl import DSLSchema
from gql.transport.exceptions import TransportError
from gql.transport.requests import RequestsHTTPTransport
from graphql import DocumentNode

from gh2md.github.comment import GithubComment
from gh2md.github.issue import GithubIssue
from gh2md.github.queries import Queries
from gh2md.github.repo import GithubRepo
from gh2md.logger import get_logger

logger: logging.Logger


@dataclass
class GithubAPI:
    """
    Handles GraphQL API queries.
    """

    token: str = None
    per_page: int = 100

    _ENDPOINT = "https://api.github.com/graphql"
    _QUERIES: Queries = None

    def __post_init__(self):
        global logger
        logger = get_logger()
        self._client = None  # GQL client
        self._ds = None  # GQL DSL schema
        self._total_pages_fetched = 0
        if not self.token:
            print(
                "No Github access token found, exiting. Use gh2md --help so see options for providing a token."
            )
            sys.exit(1)

        self._QUERIES = Queries(self._request_dsl_schema())

        # For testing
        per_page_override = os.environ.get("_GH2MD_PER_PAGE_OVERRIDE", None)
        if per_page_override:
            self.per_page = int(per_page_override)

    def _request_session(self) -> Client:
        if not self._client:
            transport = RequestsHTTPTransport(
                self._ENDPOINT,
                verify=True,
                retries=3,
                headers={'Authorization': f'Bearer {self.token}'}
            )

            self._client = Client(transport=transport, fetch_schema_from_transport=True)
        return self._client

    def _request_dsl_schema(self) -> DSLSchema:
        if not self._ds:
            with self._request_session():
                self._ds = DSLSchema(self._request_session().schema)
        return self._ds

    def _post(self, document: DocumentNode, variables: Optional[dict[str, Any]] = None) -> Tuple[Dict[str, Any], bool]:
        """
        Make a graphql request and handle errors/retries.
        """
        with self._request_session() as session:
            try:
                result = session.execute(document, variables, get_execution_result=True)
                err = False
                self._total_pages_fetched += 1
            except TransportError:
                logger.exception("Request failed multiple retries, returning empty data")
                return {}, True

        if not err:
            rl = result.data.get("rateLimit")
            if rl:
                logger.info(
                    f"Rate limit info after request: limit={rl['limit']}, cost={rl['cost']}, remaining={rl['remaining']}, resetAt={rl['resetAt']}"
                )

            if result.errors:
                err = True
                logger.error(f"Found GraphQL errors in response data: {result.errors}")

        return result.data, err

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
                    self._QUERIES.repository(),
                    variables
                )
                if err:
                    break
                else:
                    success_responses.append(data)

                    issues = data["repository"]["issues"]
                    if issues["nodes"]:
                        issue_cursor = issues["pageInfo"]["endCursor"]
                        has_issue_page = issues["pageInfo"]["hasNextPage"]
                    else:
                        issue_cursor, has_issue_page = None, False

                    prs = data["repository"]["pullRequests"]
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
            merged_pages["repository"]["issues"]["nodes"].extend(
                page["repository"]["issues"]["nodes"]
            )
            merged_pages["repository"]["pullRequests"]["nodes"].extend(
                page["repository"]["pullRequests"]["nodes"]
            )
        if not was_interrupted:
            self._fetch_and_merge_timeline_items(merged_pages)
        return merged_pages

    def _fetch_and_merge_timeline_items(self, merged_pages: Dict[str, Any]) -> None:
        """
        For any issues/PRs that are found to have an additional page of timeline items
        available, fetch the items and merge them with the original data.
        """
        if not merged_pages.get("repository"):
            return

        all_nodes = (
                merged_pages["repository"]["issues"]["nodes"]
                + merged_pages["repository"]["pullRequests"]["nodes"]
        )

        for original_node in all_nodes:
            if not original_node["timelineItems"]["pageInfo"]["hasNextPage"]:
                continue

            has_page, items_cursor = (
                True,
                original_node["timelineItems"]["pageInfo"]["endCursor"],
            )
            while has_page:
                try:
                    variables = {
                        "id": original_node["id"],
                        "itemsPerPage": self.per_page,
                        "itemsCursor": items_cursor,
                    }
                    data, err = self._post(
                        self._QUERIES.node(),
                        variables
                    )
                    if err:
                        break
                    else:
                        comments = data["node"]["timelineItems"]
                        if comments["nodes"]:
                            items_cursor = comments["pageInfo"]["endCursor"]
                            has_page = comments["pageInfo"]["hasNextPage"]
                        else:
                            items_cursor, has_page = None, False

                        logger.info(
                            f"Fetched page for additional items. total_requests_made={self._total_pages_fetched}, timelineItems_count={comments['totalCount']}, timelineItems_cursor={items_cursor}"
                        )

                        # Merge these items to the original data
                        original_node["timelineItems"]["nodes"].extend(comments["nodes"])

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
            repo_data = response["repository"]
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
        timeline_items = []
        for c in i["timelineItems"]["nodes"]:
            try:
                timeline_items.append(
                    # TODO: Replace this and get the right class from the __typename
                    GithubComment(
                        created_at=dateutil_parse(c["createdAt"]),
                        body=c["body"]
                        if c.get("body")
                        else "",
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
            comments=timeline_items,
        )
