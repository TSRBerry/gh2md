#!/usr/bin/env python
# coding: utf-8
import argparse
import datetime
import os
import pprint
import sys
from collections import defaultdict
from typing import Tuple

from gh2md.github.api import GithubAPI
from gh2md.github.issue import GithubIssue
from gh2md.github.repo import GithubRepo
from gh2md.logger import init_logger, logger
from . import templates_markdown, __version__

ENV_GITHUB_TOKEN = "GITHUB_ACCESS_TOKEN"
GITHUB_ACCESS_TOKEN_PATHS = [
    os.path.expanduser(os.path.join("~", ".config", "gh2md", "token")),
    os.path.expanduser(os.path.join("~", ".github-token")),
]

DESCRIPTION = """Export Github repository issues, pull requests and comments to markdown files:
https://github.com/mattduck/gh2md

Example: gh2md mattduck/gh2md my_issues.md

Credentials are resolved in the following order:

- A `{token}` environment variable.
- An API token stored in ~/.config/gh2md/token or ~/.github-token.

To access private repositories, you'll need a token with the full "repo" oauth
scope.

By default, all issues and pull requests will be fetched. You can disable these
using the --no... flags, eg. --no-closed-prs, or --no-prs.
""".format(
    token=ENV_GITHUB_TOKEN
)

init_logger(__name__)


def parse_args(args):
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "repo",
        help='Github repo to export, in format "owner/repo_name".',
        type=str,
        action="store",
    )
    parser.add_argument(
        "output_path",
        help="Path to write exported issues.",
        type=str,
        action="store",
    )
    parser.add_argument(
        "--multiple-files",
        help="Instead of one file, treat the given path as a directory, and create one file per issue, using a format '{created_at}.{issue_number}.{issue_type}.{issue_state}{file_extension}'.",
        action="store_true",
        dest="use_multiple_files",
    )
    parser.add_argument(
        "-I",
        "--idempotent",
        help="Remove non-deterministic values like timestamps. Two runs of gh2md will always produce the same result, as long as the Github data has not changed.",
        action="store_true",
        dest="is_idempotent",
    )
    parser.add_argument(
        "--no-prs",
        help="Don't include pull requests in the export.",
        action="store_false",
        dest="include_prs",
    )
    parser.add_argument(
        "--no-closed-prs",
        help="Don't include closed pull requests in the export.",
        action="store_false",
        dest="include_closed_prs",
    )
    parser.add_argument(
        "--no-issues",
        help="Don't include issues in the export.",
        action="store_false",
        dest="include_issues",
    )
    parser.add_argument(
        "--no-closed-issues",
        help="Don't include closed issues in the export.",
        action="store_false",
        dest="include_closed_issues",
    )
    parser.add_argument(
        "--file-extension",
        help="File extension for output files. Default is '.md'.",
        default=".md",
        type=str,
        action="store",
        dest="file_extension",
    )
    parser.add_argument(
        "--version", action="version", version="gh2md {}".format(__version__)
    )
    return parser.parse_args()


def export_issues_to_markdown_file(
    repo: GithubRepo,
    output_path: str,
    use_multiple_files: bool,
    is_idempotent: bool,
    file_extension: str = ".md",
) -> None:
    """
    Given a GithubRepo type contained already-fetched data, convert it to markdown.
    """
    formatted_issues = {}
    for issue in repo.issues:
        try:
            slug, formatted_issue = format_issue_to_markdown(issue)
        except Exception:
            logger.info(
                "Couldn't process issue due to exceptions, skipping", exc_info=True
            )
            continue
        else:
            formatted_issues[slug] = formatted_issue

    if len(formatted_issues.keys()) == 0:
        if use_multiple_files:
            logger.info(f"No issues processed, cleaning up directory: {output_path}")
            os.rmdir(output_path)
        else:
            logger.info("No issues processed, exiting without writing to file")
        return None

    if is_idempotent:
        datestring = ""
    else:
        datestring = " Generated on {}.".format(
            datetime.datetime.now().strftime("%Y.%m.%d at %H:%M:%S")
        )

    if use_multiple_files:
        # Write one file per issue
        metadata_footnote = templates_markdown.ISSUE_FILE_FOOTNOTE.format(
            repo_name=repo.full_name,
            repo_url=repo.url,
            datestring=datestring,
        )
        for issue_slug, formatted_issue in formatted_issues.items():
            issue_file_markdown = "\n".join([formatted_issue, metadata_footnote])
            issue_path = os.path.join(output_path, f"{issue_slug}{file_extension}")
            logger.info("Writing to file: {}".format(issue_path))
            with open(issue_path, "wb") as out:
                out.write(issue_file_markdown.encode("utf-8"))
    else:
        # Write everything in one file
        full_markdown_export = templates_markdown.BASE.format(
            repo_name=repo.full_name,
            repo_url=repo.url,
            issues="\n".join(formatted_issues.values()),
            datestring=datestring,
        )
        logger.info("Writing to file: {}".format(output_path))
        with open(output_path, "wb") as out:
            out.write(full_markdown_export.encode("utf-8"))
    return None


def format_issue_to_markdown(issue: GithubIssue) -> Tuple[str, str]:
    """
    Given a Github issue, return a formatted markdown block for the issue and
    its comments.
    """
    # Process the comments for this issue
    formatted_comments = ""
    if issue.comments:
        comments = []
        for comment in issue.comments:
            # logger.info("Processing comment: {}".format(comment.url))
            this_comment = templates_markdown.COMMENT.format(
                author=comment.user_login,
                author_url=comment.user_url,
                avatar_url=comment.user_avatar_url,
                date=comment.created_at.strftime("%Y-%m-%d %H:%M"),
                url=comment.url,
                body=comment.body,
            )
            comments.append(this_comment.rstrip())

        formatted_comments += "\n\n".join(comments)

    number = str(issue.number)
    if issue.pull_request:
        number += " PR"
        slugtype = "pr"
    else:
        number += " Issue"
        slugtype = "issue"

    labels = ""
    if issue.label_names:
        labels = ", ".join(["`{}`".format(lab) for lab in issue.label_names])
        labels = "**Labels**: {}\n\n".format(labels)

    formatted_issue = templates_markdown.ISSUE.format(
        title=issue.title,
        date=issue.created_at.strftime("%Y-%m-%d %H:%M"),
        number=number,
        url=issue.url,
        author=issue.user_login,
        author_url=issue.user_url,
        avatar_url=issue.user_avatar_url,
        state=issue.state,
        body=issue.body,
        comments=formatted_comments,
        labels=labels,
    )
    slug = ".".join(
        [
            issue.created_at.strftime("%Y-%m-%d"),
            str(issue.number),
            slugtype,
            issue.state,
        ]
    )
    return slug, formatted_issue.replace("\r", "")


def get_environment_token() -> str:
    try:
        logger.info(f"Looking for token in envvar {ENV_GITHUB_TOKEN}")
        token = os.environ[ENV_GITHUB_TOKEN]
        logger.info("Using token from environment")
        return token
    except KeyError:
        for path in GITHUB_ACCESS_TOKEN_PATHS:
            logger.info(f"Looking for token in file: {path}")
            if os.path.exists(path):
                logger.info(f"Using token from file: {path}")
                with open(path, "r") as f:
                    token = f.read().strip()
                    return token


def main():
    """Entry point"""
    args = parse_args(sys.argv[1:])

    if args.use_multiple_files:
        if os.path.exists(args.output_path):
            if len(os.listdir(args.output_path)):
                raise RuntimeError(
                    f"Output directory already exists and has files in it: {args.output_path}"
                )
        else:
            logger.info(f"Creating output directory: {args.output_path}")
            os.makedirs(args.output_path, exist_ok=True)

    gh = GithubAPI(token=get_environment_token())
    repo = gh.fetch_and_decode_repository(
        args.repo,
        include_closed_prs=args.include_closed_prs,
        include_closed_issues=args.include_closed_issues,
        include_prs=args.include_prs,
        include_issues=args.include_issues,
    )

    # Log issue counts
    logger.info(f"Retrieved issues for repo: {repo.full_name}")
    counts = {
        "PRs": defaultdict(int),
        "issues": defaultdict(int),
        "total": len(repo.issues),
    }
    for issue in repo.issues:
        if issue.pull_request:
            counts["PRs"][issue.state] += 1
            counts["PRs"]["total"] += 1
        else:
            counts["issues"][issue.state] += 1
            counts["issues"]["total"] += 1
    counts["PRs"] = dict(counts["PRs"])
    counts["issues"] = dict(counts["issues"])
    logger.info(f"Retrieved issue counts: \n{pprint.pformat(counts)}")

    # Convert and save markdown
    logger.info("Converting retrieved issues to markdown")
    export_issues_to_markdown_file(
        repo=repo,
        output_path=args.output_path,
        use_multiple_files=args.use_multiple_files,
        is_idempotent=args.is_idempotent,
        file_extension=args.file_extension,
    )
    logger.info("Done.")


if __name__ == "__main__":
    sys.exit(main())
