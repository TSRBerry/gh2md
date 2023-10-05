from gql.dsl import DSLSchema, DSLFragment, DSLVariableDefinitions, DSLMetaField


class Fragments:
    DEFAULT_COMMIT_AUTHORS_PER_PAGE = 100
    DEFAULT_PULL_REQUEST_REVIEW_COMMENTS_PER_PAGE = 100
    DEFAULT_PULL_REQUEST_COMMIT_COMMENT_THREAD_COMMENTS_PER_PAGE = 100
    DEFAULT_PULL_REQUEST_Review_THREAD_COMMENTS_PER_PAGE = 100
    DEFAULT_ISSUE_LABELS_PER_PAGE = 100
    DEFAULT_PULL_REQUEST_LABELS_PER_PAGE = 100

    def __init__(self, ds: DSLSchema, var: DSLVariableDefinitions):
        self._ds = ds
        self.var = var

    @property
    def page_info(self) -> DSLFragment:
        page_info_fields = DSLFragment("pageInfoFields")
        page_info_fields.on(self._ds.PageInfo)
        page_info_fields.select(
            self._ds.PageInfo.endCursor,
            self._ds.PageInfo.hasNextPage,
        )

        return page_info_fields

    @property
    def rate_limit(self) -> DSLFragment:
        rate_limit_fields = DSLFragment("rateLimitFields")
        rate_limit_fields.on(self._ds.RateLimit)
        rate_limit_fields.select(
            self._ds.RateLimit.limit,
            self._ds.RateLimit.cost,
            self._ds.RateLimit.remaining,
            self._ds.RateLimit.resetAt,
        )

        return rate_limit_fields

    @property
    def node(self) -> DSLFragment:
        node_fields = DSLFragment("nodeFields")
        node_fields.on(self._ds.Node)
        node_fields.select(
            self._ds.Node.id
        )

        return node_fields

    @property
    def actor(self) -> DSLFragment:
        actor_fields = DSLFragment("actorFields")
        actor_fields.on(self._ds.Actor)
        actor_fields.select(
            self._ds.Actor.avatarUrl,
            self._ds.Actor.login,
            self._ds.Actor.url,
        )

        return actor_fields

    @property
    def git_actor(self) -> DSLFragment:
        git_actor_fields = DSLFragment("gitActorFields")
        git_actor_fields.on(self._ds.GitActor)
        git_actor_fields.select(
            self._ds.GitActor.avatarUrl,
            self._ds.GitActor.date,
            self._ds.GitActor.email,
            self._ds.GitActor.name,
        )

        return git_actor_fields

    @property
    def commit(self) -> DSLFragment:
        commit_fields = DSLFragment("commitFields")
        commit_fields.on(self._ds.Commit)
        commit_fields.select(
            self.node,
            self._ds.Commit.authoredDate,
            self._ds.Commit.authors(
                first=self.var.commitAuthorsPerPage.default(self.DEFAULT_COMMIT_AUTHORS_PER_PAGE),
                after=self.var.commitAuthorsCursor,
            ).select(
                self._ds.GitActorConnection.nodes.select(self.git_actor),
                self._ds.GitActorConnection.pageInfo.select(self.page_info),
                self._ds.GitActorConnection.totalCount,
            ),
            self._ds.Commit.committedDate,
            self._ds.Commit.committer.select(self.git_actor),
            self._ds.Commit.message,
            self._ds.Commit.messageBody,
            self._ds.Commit.oid,
            self._ds.Commit.url,
        )

        return commit_fields

    @property
    def comment(self) -> DSLFragment:
        comment_fields = DSLFragment("commentFields")
        comment_fields.on(self._ds.Comment)
        comment_fields.select(
            self._ds.Comment.author.select(self.actor),
            self._ds.Comment.authorAssociation,
            self._ds.Comment.body,
            self._ds.Comment.createdAt,
            self._ds.Comment.editor.select(self.actor),
            self._ds.Comment.lastEditedAt,
        )

        return comment_fields

    @property
    def referenced_issue(self) -> DSLFragment:
        referenced_issue_fields = DSLFragment("referencedIssueFields")
        referenced_issue_fields.on(self._ds.Issue)
        referenced_issue_fields.select(
            self.node,
            self._ds.Issue.author.select(self.actor),
            self._ds.Issue.number,
            self._ds.Issue.title,
            self._ds.Issue.url,
        )

        return referenced_issue_fields

    @property
    def referenced_pull_request(self) -> DSLFragment:
        referenced_pull_request_fields = DSLFragment("referencedPullRequestFields")
        referenced_pull_request_fields.on(self._ds.PullRequest)
        referenced_pull_request_fields.select(
            self.node,
            self._ds.PullRequest.author.select(self.actor),
            self._ds.PullRequest.isDraft,
            self._ds.PullRequest.number,
            self._ds.PullRequest.title,
            self._ds.PullRequest.url,
        )

        return referenced_pull_request_fields

    @property
    def referenced_subject(self) -> tuple[DSLFragment, DSLFragment]:
        return self.referenced_issue, self.referenced_pull_request

    @property
    def issue_or_pull_request(self) -> tuple[DSLFragment, DSLFragment]:
        return self.referenced_subject

    @property
    def closer(self) -> tuple[DSLFragment, DSLFragment]:
        return self.commit, self.referenced_pull_request

    @property
    def deployment(self) -> DSLFragment:
        deployment_fields = DSLFragment("deploymentFields")
        deployment_fields.on(self._ds.Deployment)
        deployment_fields.select(
            self.node,
            self._ds.Deployment.environment,
            self._ds.Deployment.description,
            optionalCommit=self._ds.Deployment.commit.select(self.commit),
        )

        return deployment_fields

    @property
    def reaction_group(self) -> DSLFragment:
        reaction_group_fields = DSLFragment("reactionGroupFields")
        reaction_group_fields.on(self._ds.ReactionGroup)
        reaction_group_fields.select(
            self._ds.ReactionGroup.content,
            self._ds.ReactionGroup.reactors.select(
                self._ds.ReactorConnection.totalCount,
            ),
        )

        return reaction_group_fields

    @property
    def label(self) -> DSLFragment:
        label_fields = DSLFragment("labelFields")
        label_fields.on(self._ds.Label)
        label_fields.select(
            self._ds.Label.color,
            self._ds.Label.description,
            self._ds.Label.name,
            self._ds.Label.url,
        )

        return label_fields

    @property
    def team(self) -> DSLFragment:
        team_fields = DSLFragment("teamFields")
        team_fields.on(self._ds.Team)
        team_fields.select(
            self._ds.Team.combinedSlug,
            self._ds.Team.description,
            self._ds.Team.name,
            self._ds.Team.organization.select(self.actor),
            teamAvatarUrl=self._ds.Team.avatarUrl,
        )

        return team_fields

    @property
    def added_to_merge_queue_event(self) -> DSLFragment:
        added_to_merge_queue_event_fields = DSLFragment("addedToMergeQueueEventFields")
        added_to_merge_queue_event_fields.on(self._ds.AddedToMergeQueueEvent)
        added_to_merge_queue_event_fields.select(
            self._ds.AddedToMergeQueueEvent.actor.select(self.actor),
            self._ds.AddedToMergeQueueEvent.createdAt,
            self._ds.AddedToMergeQueueEvent.enqueuer.select(self.actor),
        )

        return added_to_merge_queue_event_fields

    @property
    def added_to_project_event(self) -> DSLFragment:
        added_to_project_event_fields = DSLFragment("addedToProjectEventFields")
        added_to_project_event_fields.on(self._ds.AddedToProjectEvent)
        added_to_project_event_fields.select(
            self._ds.AddedToProjectEvent.actor.select(self.actor),
            self._ds.AddedToProjectEvent.createdAt,
            # TODO: Add this as soon as this leaves schema-preview
            #  https://docs.github.com/en/graphql/overview/schema-previews#project-event-details-preview
            # self._ds.AddedToProjectEvent.project.select(self._ds.Project.name, self._ds.Project.url),
        )

        return added_to_project_event_fields

    @property
    def assigned_event(self) -> DSLFragment:
        assigned_event_fields = DSLFragment("assignedEventFields")
        assigned_event_fields.on(self._ds.AssignedEvent)
        assigned_event_fields.select(
            self._ds.AssignedEvent.actor.select(self.actor),
            self._ds.AssignedEvent.assignee.select(self.actor),
            self._ds.AssignedEvent.createdAt,
        )

        return assigned_event_fields

    @property
    def auto_merge_disabled_event(self) -> DSLFragment:
        auto_merge_disabled_event_fields = DSLFragment("autoMergeDisabledEventFields")
        auto_merge_disabled_event_fields.on(self._ds.AutoMergeDisabledEvent)
        auto_merge_disabled_event_fields.select(
            self._ds.AutoMergeDisabledEvent.actor.select(self.actor),
            self._ds.AutoMergeDisabledEvent.createdAt,
            self._ds.AutoMergeDisabledEvent.disabler.select(self.actor),
            self._ds.AutoMergeDisabledEvent.reason,
        )

        return auto_merge_disabled_event_fields

    @property
    def auto_merge_enabled_event(self) -> DSLFragment:
        auto_merge_enabled_event_fields = DSLFragment("autoMergeEnabledEventFields")
        auto_merge_enabled_event_fields.on(self._ds.AutoMergeEnabledEvent)
        auto_merge_enabled_event_fields.select(
            self._ds.AutoMergeEnabledEvent.actor.select(self.actor),
            self._ds.AutoMergeEnabledEvent.createdAt,
            self._ds.AutoMergeEnabledEvent.enabler.select(self.actor),
        )

        return auto_merge_enabled_event_fields

    @property
    def auto_rebase_enabled_event(self) -> DSLFragment:
        auto_rebase_enabled_event_fields = DSLFragment("autoRebaseEnabledEventFields")
        auto_rebase_enabled_event_fields.on(self._ds.AutoRebaseEnabledEvent)
        auto_rebase_enabled_event_fields.select(
            self._ds.AutoRebaseEnabledEvent.actor.select(self.actor),
            self._ds.AutoRebaseEnabledEvent.createdAt,
            self._ds.AutoRebaseEnabledEvent.enabler.select(self.actor),
        )

        return auto_rebase_enabled_event_fields

    @property
    def auto_squash_enabled_event(self) -> DSLFragment:
        auto_squash_enabled_event_fields = DSLFragment("autoSquashEnabledEventFields")
        auto_squash_enabled_event_fields.on(self._ds.AutoSquashEnabledEvent)
        auto_squash_enabled_event_fields.select(
            self._ds.AutoSquashEnabledEvent.actor.select(self.actor),
            self._ds.AutoSquashEnabledEvent.createdAt,
            self._ds.AutoSquashEnabledEvent.enabler.select(self.actor),
        )

        return auto_squash_enabled_event_fields

    @property
    def automatic_base_change_failed_event(self) -> DSLFragment:
        automatic_base_change_failed_event_fields = DSLFragment("automaticBaseChangeFailedEventFields")
        automatic_base_change_failed_event_fields.on(self._ds.AutomaticBaseChangeFailedEvent)
        automatic_base_change_failed_event_fields.select(
            self._ds.AutomaticBaseChangeFailedEvent.actor.select(self.actor),
            self._ds.AutomaticBaseChangeFailedEvent.createdAt,
            self._ds.AutomaticBaseChangeFailedEvent.newBase,
            self._ds.AutomaticBaseChangeFailedEvent.oldBase,
        )

        return automatic_base_change_failed_event_fields

    @property
    def automatic_base_change_succeeded_event(self) -> DSLFragment:
        automatic_base_change_succeeded_event_fields = DSLFragment("automaticBaseChangeSucceededEventFields")
        automatic_base_change_succeeded_event_fields.on(self._ds.AutomaticBaseChangeSucceededEvent)
        automatic_base_change_succeeded_event_fields.select(
            self._ds.AutomaticBaseChangeSucceededEvent.actor.select(self.actor),
            self._ds.AutomaticBaseChangeSucceededEvent.createdAt,
            self._ds.AutomaticBaseChangeSucceededEvent.newBase,
            self._ds.AutomaticBaseChangeSucceededEvent.oldBase,
        )

        return automatic_base_change_succeeded_event_fields

    @property
    def base_ref_changed_event(self) -> DSLFragment:
        base_ref_changed_event_fields = DSLFragment("baseRefChangedEventFields")
        base_ref_changed_event_fields.on(self._ds.BaseRefChangedEvent)
        base_ref_changed_event_fields.select(
            self._ds.BaseRefChangedEvent.actor.select(self.actor),
            self._ds.BaseRefChangedEvent.createdAt,
            self._ds.BaseRefChangedEvent.currentRefName,
            self._ds.BaseRefChangedEvent.previousRefName,
        )

        return base_ref_changed_event_fields

    @property
    def base_ref_deleted_event(self) -> DSLFragment:
        base_ref_deleted_event_fields = DSLFragment("baseRefDeletedEventFields")
        base_ref_deleted_event_fields.on(self._ds.BaseRefDeletedEvent)
        base_ref_deleted_event_fields.select(
            self._ds.BaseRefDeletedEvent.actor.select(self.actor),
            self._ds.BaseRefDeletedEvent.baseRefName,
            self._ds.BaseRefDeletedEvent.createdAt,
        )

        return base_ref_deleted_event_fields

    @property
    def base_ref_force_pushed_event(self) -> DSLFragment:
        base_ref_force_pushed_event_fields = DSLFragment("baseRefForcePushedEventFields")
        base_ref_force_pushed_event_fields.on(self._ds.BaseRefForcePushedEvent)
        base_ref_force_pushed_event_fields.select(
            self._ds.BaseRefForcePushedEvent.actor.select(self.actor),
            self._ds.BaseRefForcePushedEvent.createdAt,
            self._ds.BaseRefForcePushedEvent.afterCommit.select(self.commit),
            self._ds.BaseRefForcePushedEvent.beforeCommit.select(self.commit),
        )

        return base_ref_force_pushed_event_fields

    @property
    def closed_event(self) -> DSLFragment:
        commit, pull_request = self.closer

        closed_event_fields = DSLFragment("closedEventFields")
        closed_event_fields.on(self._ds.ClosedEvent)
        closed_event_fields.select(
            self._ds.ClosedEvent.actor.select(self.actor),
            self._ds.ClosedEvent.closer.select(
                commit,
                pull_request,
            ),
            self._ds.ClosedEvent.createdAt,
            self._ds.ClosedEvent.stateReason,
            self._ds.ClosedEvent.url,
        )

        return closed_event_fields

    @property
    def comment_deleted_event(self) -> DSLFragment:
        comment_deleted_event_fields = DSLFragment("commentDeletedEventFields")
        comment_deleted_event_fields.on(self._ds.CommentDeletedEvent)
        comment_deleted_event_fields.select(
            self._ds.CommentDeletedEvent.actor.select(self.actor),
            self._ds.CommentDeletedEvent.createdAt,
            self._ds.CommentDeletedEvent.deletedCommentAuthor.select(self.actor),
        )

        return comment_deleted_event_fields

    @property
    def connected_event(self) -> DSLFragment:
        referenced_issue, referenced_pull_request = self.referenced_subject

        connected_event_fields = DSLFragment("connectedEventFields")
        connected_event_fields.on(self._ds.ConnectedEvent)
        connected_event_fields.select(
            self._ds.ConnectedEvent.actor.select(self.actor),
            self._ds.ConnectedEvent.createdAt,
            self._ds.ConnectedEvent.source.select(
                referenced_issue,
                referenced_pull_request,
            ),
            self._ds.ConnectedEvent.subject.select(
                referenced_issue,
                referenced_pull_request,
            ),
        )

        return connected_event_fields

    @property
    def convert_to_draft_event(self) -> DSLFragment:
        convert_to_draft_event_fields = DSLFragment("convertToDraftEventFields")
        convert_to_draft_event_fields.on(self._ds.ConvertToDraftEvent)
        convert_to_draft_event_fields.select(
            self._ds.ConvertToDraftEvent.actor.select(self.actor),
            self._ds.ConvertToDraftEvent.createdAt,
        )

        return convert_to_draft_event_fields

    @property
    def converted_note_to_issue_event(self) -> DSLFragment:
        converted_note_to_issue_event_fields = DSLFragment("convertedNoteToIssueEventFields")
        converted_note_to_issue_event_fields.on(self._ds.ConvertedNoteToIssueEvent)
        converted_note_to_issue_event_fields.select(
            self._ds.ConvertedNoteToIssueEvent.actor.select(self.actor),
            self._ds.ConvertedNoteToIssueEvent.createdAt,
            # TODO: Add this as soon as this leaves schema-preview
            #  https://docs.github.com/en/graphql/overview/schema-previews#project-event-details-preview
            # self._ds.ConvertedNoteToIssueEvent.project.select(self._ds.Project.name, self._ds.Project.url),
        )

        return converted_note_to_issue_event_fields

    @property
    def converted_to_discussion_event(self) -> DSLFragment:
        converted_to_discussion_event_fields = DSLFragment("convertedToDiscussionEventFields")
        converted_to_discussion_event_fields.on(self._ds.ConvertedToDiscussionEvent)
        converted_to_discussion_event_fields.select(
            self._ds.ConvertedToDiscussionEvent.actor.select(self.actor),
            self._ds.ConvertedToDiscussionEvent.createdAt,
            self._ds.ConvertedToDiscussionEvent.discussion.select(
                self._ds.Discussion.number,
                self._ds.Discussion.title,
                self._ds.Discussion.url,
            ),
        )

        return converted_to_discussion_event_fields

    @property
    def cross_referenced_event(self) -> DSLFragment:
        referenced_issue, referenced_pull_request = self.referenced_subject

        cross_referenced_event_fields = DSLFragment("crossReferencedEventFields")
        cross_referenced_event_fields.on(self._ds.CrossReferencedEvent)
        cross_referenced_event_fields.select(
            self._ds.CrossReferencedEvent.actor.select(self.actor),
            self._ds.CrossReferencedEvent.createdAt,
            self._ds.CrossReferencedEvent.referencedAt,
            self._ds.CrossReferencedEvent.source.select(
                referenced_issue,
                referenced_pull_request,
            ),
            self._ds.CrossReferencedEvent.target.select(
                referenced_issue,
                referenced_pull_request,
            ),
            self._ds.CrossReferencedEvent.willCloseTarget,
        )

        return cross_referenced_event_fields

    @property
    def demilestoned_event(self) -> DSLFragment:
        demilestoned_event_fields = DSLFragment("demilestonedEventFields")
        demilestoned_event_fields.on(self._ds.DemilestonedEvent)
        demilestoned_event_fields.select(
            self._ds.DemilestonedEvent.actor.select(self.actor),
            self._ds.DemilestonedEvent.createdAt,
            self._ds.DemilestonedEvent.milestoneTitle,
        )

        return demilestoned_event_fields

    @property
    def deployed_event(self) -> DSLFragment:
        deployed_event_fields = DSLFragment("deployedEventFields")
        deployed_event_fields.on(self._ds.DeployedEvent)
        deployed_event_fields.select(
            self._ds.DeployedEvent.actor.select(self.actor),
            self._ds.DeployedEvent.createdAt,
            self._ds.DeployedEvent.deployment.select(self.deployment),
        )

        return deployed_event_fields

    @property
    def deployment_environment_changed_event(self) -> DSLFragment:
        deployment_environment_changed_event_fields = DSLFragment("deploymentEnvironmentChangedEventFields")
        deployment_environment_changed_event_fields.on(self._ds.DeploymentEnvironmentChangedEvent)
        deployment_environment_changed_event_fields.select(
            self._ds.DeploymentEnvironmentChangedEvent.actor.select(self.actor),
            self._ds.DeploymentEnvironmentChangedEvent.createdAt,
            self._ds.DeploymentEnvironmentChangedEvent.deploymentStatus.select(
                self._ds.DeploymentStatus.deployment.select(self.deployment),
                self._ds.DeploymentStatus.environmentUrl,
            ),
        )

        return deployment_environment_changed_event_fields

    @property
    def disconnected_event(self) -> DSLFragment:
        referenced_issue, referenced_pull_request = self.referenced_subject

        disconnected_event_fields = DSLFragment("disconnectedEventFields")
        disconnected_event_fields.on(self._ds.DisconnectedEvent)
        disconnected_event_fields.select(
            self._ds.DisconnectedEvent.actor.select(self.actor),
            self._ds.DisconnectedEvent.createdAt,
            self._ds.DisconnectedEvent.source.select(
                referenced_issue,
                referenced_pull_request,
            ),
            self._ds.DisconnectedEvent.subject.select(
                referenced_issue,
                referenced_pull_request,
            ),
        )

        return disconnected_event_fields

    @property
    def head_ref_deleted_event(self) -> DSLFragment:
        head_ref_deleted_event_fields = DSLFragment("headRefDeletedEventFields")
        head_ref_deleted_event_fields.on(self._ds.HeadRefDeletedEvent)
        head_ref_deleted_event_fields.select(
            self._ds.HeadRefDeletedEvent.actor.select(self.actor),
            self._ds.HeadRefDeletedEvent.createdAt,
            self._ds.HeadRefDeletedEvent.headRefName,
        )

        return head_ref_deleted_event_fields

    @property
    def head_ref_force_pushed_event(self) -> DSLFragment:
        head_ref_force_pushed_event_fields = DSLFragment("headRefForcePushedEventFields")
        head_ref_force_pushed_event_fields.on(self._ds.HeadRefForcePushedEvent)
        head_ref_force_pushed_event_fields.select(
            self._ds.HeadRefForcePushedEvent.actor.select(self.actor),
            self._ds.HeadRefForcePushedEvent.beforeCommit.select(self.commit),
            self._ds.HeadRefForcePushedEvent.afterCommit.select(self.commit),
            self._ds.HeadRefForcePushedEvent.createdAt,
        )

        return head_ref_force_pushed_event_fields

    @property
    def head_ref_restored_event(self) -> DSLFragment:
        head_ref_restored_event_fields = DSLFragment("headRefRestoredEventFields")
        head_ref_restored_event_fields.on(self._ds.HeadRefRestoredEvent)
        head_ref_restored_event_fields.select(
            self._ds.HeadRefRestoredEvent.actor.select(self.actor),
            self._ds.HeadRefRestoredEvent.createdAt,
        )

        return head_ref_restored_event_fields

    @property
    def issue_comment(self) -> DSLFragment:
        issue_comment_fields = DSLFragment("issueCommentFields")
        issue_comment_fields.on(self._ds.IssueComment)
        issue_comment_fields.select(
            self.comment,
            self._ds.IssueComment.isMinimized,
            self._ds.IssueComment.minimizedReason,
            self._ds.IssueComment.reactionGroups.select(self.reaction_group),
            self._ds.IssueComment.url,
        )

        return issue_comment_fields

    @property
    def labeled_event(self) -> DSLFragment:
        labeled_event_fields = DSLFragment("labeledEventFields")
        labeled_event_fields.on(self._ds.LabeledEvent)
        labeled_event_fields.select(
            self._ds.LabeledEvent.actor.select(self.actor),
            self._ds.LabeledEvent.createdAt,
            self._ds.LabeledEvent.label.select(self.label),
        )

        return labeled_event_fields

    @property
    def locked_event(self) -> DSLFragment:
        locked_event_fields = DSLFragment("lockedEventFields")
        locked_event_fields.on(self._ds.LockedEvent)
        locked_event_fields.select(
            self._ds.LockedEvent.actor.select(self.actor),
            self._ds.LockedEvent.createdAt,
            self._ds.LockedEvent.lockReason,
        )

        return locked_event_fields

    @property
    def marked_as_duplicate_event(self) -> DSLFragment:
        issue, pull_request = self.issue_or_pull_request

        marked_as_duplicate_event_fields = DSLFragment("markedAsDuplicateEventFields")
        marked_as_duplicate_event_fields.on(self._ds.MarkedAsDuplicateEvent)
        marked_as_duplicate_event_fields.select(
            self._ds.MarkedAsDuplicateEvent.actor.select(self.actor),
            self._ds.MarkedAsDuplicateEvent.canonical.select(
                issue,
                pull_request,
            ),
            self._ds.MarkedAsDuplicateEvent.createdAt,
        )

        return marked_as_duplicate_event_fields

    @property
    def mentioned_event(self) -> DSLFragment:
        mentioned_event_fields = DSLFragment("mentionedEventFields")
        mentioned_event_fields.on(self._ds.MentionedEvent)
        mentioned_event_fields.select(
            self._ds.MentionedEvent.actor.select(self.actor),
            self._ds.MentionedEvent.createdAt,
            # TODO: For some reason there are no fields to indicate where this PR/Issue was mentioned
            #  see: https://docs.github.com/en/graphql/reference/objects#mentionedevent
        )

        return mentioned_event_fields

    @property
    def merged_event(self) -> DSLFragment:
        merged_event_fields = DSLFragment("mergedEventFields")
        merged_event_fields.on(self._ds.MergedEvent)
        merged_event_fields.select(
            self._ds.MergedEvent.actor.select(self.actor),
            self._ds.MergedEvent.createdAt,
            self._ds.MergedEvent.mergeRefName,
            optionalCommit=self._ds.MergedEvent.commit.select(self.commit),
        )

        return merged_event_fields

    @property
    def milestoned_event(self) -> DSLFragment:
        milestoned_event_fields = DSLFragment("milestonedEventFields")
        milestoned_event_fields.on(self._ds.MilestonedEvent)
        milestoned_event_fields.select(
            self._ds.MilestonedEvent.actor.select(self.actor),
            self._ds.MilestonedEvent.createdAt,
            self._ds.MilestonedEvent.milestoneTitle,
        )

        return milestoned_event_fields

    @property
    def moved_columns_in_project_event(self) -> DSLFragment:
        moved_columns_in_project_event_fields = DSLFragment("movedColumnsInProjectEventFields")
        moved_columns_in_project_event_fields.on(self._ds.MovedColumnsInProjectEvent)
        moved_columns_in_project_event_fields.select(
            self._ds.MovedColumnsInProjectEvent.actor.select(self.actor),
            self._ds.MovedColumnsInProjectEvent.createdAt,
            # TODO: Add this as soon as this leaves schema-preview
            #  https://docs.github.com/en/graphql/overview/schema-previews#project-event-details-preview
            # self._ds.MovedColumnsInProjectEvent.previousProjectColumnName,
            # self._ds.MovedColumnsInProjectEvent.project.select(self._ds.Project.name, self._ds.Project.url),
            # self._ds.MovedColumnsInProjectEvent.projectColumnName,
        )

        return moved_columns_in_project_event_fields

    @property
    def pinned_event(self) -> DSLFragment:
        pinned_event_fields = DSLFragment("pinnedEventFields")
        pinned_event_fields.on(self._ds.PinnedEvent)
        pinned_event_fields.select(
            self._ds.PinnedEvent.actor.select(self.actor),
            self._ds.PinnedEvent.createdAt,
        )

        return pinned_event_fields

    @property
    def pull_request_commit(self) -> DSLFragment:
        pull_request_commit_fields = DSLFragment("pullRequestCommitFields")
        pull_request_commit_fields.on(self._ds.PullRequestCommit)
        pull_request_commit_fields.select(
            self._ds.PullRequestCommit.commit.select(self.commit),
            self._ds.PullRequestCommit.url,
        )

        return pull_request_commit_fields

    @property
    def pull_request_commit_comment_thread(self) -> DSLFragment:
        pull_request_commit_comment_thread_fields = DSLFragment("pullRequestCommitCommentThreadFields")
        pull_request_commit_comment_thread_fields.on(self._ds.PullRequestCommitCommentThread)
        pull_request_commit_comment_thread_fields.select(
            self._ds.PullRequestCommitCommentThread.comments(
                first=self.var.pullRequestCommitCommentThreadCommentsPerPage.default(
                    self.DEFAULT_PULL_REQUEST_COMMIT_COMMENT_THREAD_COMMENTS_PER_PAGE
                ),
                after=self.var.pullRequestCommitCommentThreadCommentsCursor,
            ).select(
                self._ds.CommitCommentConnection.nodes.select(
                    self.comment,
                    self._ds.CommitComment.isMinimized,
                    self._ds.CommitComment.minimizedReason,
                    self._ds.CommitComment.reactionGroups.select(self.reaction_group),
                    self._ds.CommitComment.url,
                ),
                self._ds.CommitCommentConnection.pageInfo.select(self.page_info),
                self._ds.CommitCommentConnection.totalCount,
            ),
            self._ds.PullRequestCommitCommentThread.commit.select(self.commit),
            self._ds.PullRequestCommitCommentThread.position,
            optionalPath=self._ds.PullRequestCommitCommentThread.path,
        )

        return pull_request_commit_comment_thread_fields

    @property
    def pull_request_comment_connection(self) -> DSLFragment:
        pull_request_comment_connection_fields = DSLFragment("pullRequestCommentConnectionFields")
        pull_request_comment_connection_fields.on(self._ds.PullRequestReviewCommentConnection)
        pull_request_comment_connection_fields.select(
            self._ds.PullRequestReviewCommentConnection.nodes.select(
                self.node,
                self.comment,
                self._ds.PullRequestReviewComment.diffHunk,
                self._ds.PullRequestReviewComment.line,
                self._ds.PullRequestReviewComment.isMinimized,
                self._ds.PullRequestReviewComment.minimizedReason,
                self._ds.PullRequestReviewComment.outdated,
                self._ds.PullRequestReviewComment.path,
                self._ds.PullRequestReviewComment.reactionGroups.select(self.reaction_group),
                self._ds.PullRequestReviewComment.startLine,
                self._ds.PullRequestReviewComment.subjectType,
            ),
            self._ds.PullRequestReviewCommentConnection.pageInfo.select(self.page_info),
            self._ds.PullRequestReviewCommentConnection.totalCount,
        )

        return pull_request_comment_connection_fields

    @property
    def pull_request_review(self) -> DSLFragment:
        pull_request_review_fields = DSLFragment("pullRequestReviewFields")
        pull_request_review_fields.on(self._ds.PullRequestReview)
        pull_request_review_fields.select(
            self.comment,
            self._ds.PullRequestReview.comments(
                first=self.var.pullRequestReviewCommentsPerPage.default(
                    self.DEFAULT_PULL_REQUEST_REVIEW_COMMENTS_PER_PAGE
                ),
                after=self.var.pullRequestReviewCommentsCursor,
            ).select(self.pull_request_comment_connection),
            self._ds.PullRequestReview.reactionGroups.select(self.reaction_group),
            self._ds.PullRequestReview.submittedAt,
            self._ds.PullRequestReview.url,
        )

        return pull_request_review_fields

    @property
    def pull_request_review_thread(self) -> DSLFragment:
        pull_request_review_thread_fields = DSLFragment("pullRequestReviewThreadFields")
        pull_request_review_thread_fields.on(self._ds.PullRequestReviewThread)
        pull_request_review_thread_fields.select(
            self._ds.PullRequestReviewThread.comments(
                first=self.var.pullRequestReviewThreadCommentsPerPage.default(
                    self.DEFAULT_PULL_REQUEST_Review_THREAD_COMMENTS_PER_PAGE),
                after=self.var.pullRequestReviewThreadCommentsCursor,
            ).select(self.pull_request_comment_connection),
            self._ds.PullRequestReviewThread.diffSide,
            self._ds.PullRequestReviewThread.isOutdated,
            self._ds.PullRequestReviewThread.isResolved,
            self._ds.PullRequestReviewThread.line,
            self._ds.PullRequestReviewThread.path,
            self._ds.PullRequestReviewThread.resolvedBy.select(self.actor),
            self._ds.PullRequestReviewThread.startLine,
            self._ds.PullRequestReviewThread.subjectType,
        )

        return pull_request_review_thread_fields

    @property
    def ready_for_review_event(self) -> DSLFragment:
        ready_for_review_event_fields = DSLFragment("readyForReviewEventFields")
        ready_for_review_event_fields.on(self._ds.ReadyForReviewEvent)
        ready_for_review_event_fields.select(
            self._ds.ReadyForReviewEvent.actor.select(self.actor),
            self._ds.ReadyForReviewEvent.createdAt,
            self._ds.ReadyForReviewEvent.url,
        )

        return ready_for_review_event_fields

    @property
    def referenced_event(self) -> DSLFragment:
        referenced_event_fields = DSLFragment("referencedEventFields")
        referenced_event_fields.on(self._ds.ReferencedEvent)
        referenced_event_fields.select(
            self._ds.ReferencedEvent.actor.select(self.actor),
            self._ds.ReferencedEvent.commitRepository.select(
                self._ds.Repository.nameWithOwner,
                self._ds.Repository.url,
            ),
            self._ds.ReferencedEvent.isDirectReference,
            optionalCommit=self._ds.ReferencedEvent.commit.select(self.commit),
        )

        return referenced_event_fields

    @property
    def removed_from_merge_queue_event(self) -> DSLFragment:
        removed_from_merge_queue_event_fields = DSLFragment("removedFromMergeQueueEventFields")
        removed_from_merge_queue_event_fields.on(self._ds.RemovedFromMergeQueueEvent)
        removed_from_merge_queue_event_fields.select(
            self._ds.RemovedFromMergeQueueEvent.actor.select(self.actor),
            self._ds.RemovedFromMergeQueueEvent.beforeCommit.select(self.commit),
            self._ds.RemovedFromMergeQueueEvent.createdAt,
            self._ds.RemovedFromMergeQueueEvent.enqueuer.select(self.actor),
            self._ds.RemovedFromMergeQueueEvent.reason,
        )

        return removed_from_merge_queue_event_fields

    @property
    def removed_from_project_event(self) -> DSLFragment:
        removed_from_project_event_fields = DSLFragment("removedFromProjectEventFields")
        removed_from_project_event_fields.on(self._ds.RemovedFromProjectEvent)
        removed_from_project_event_fields.select(
            self._ds.RemovedFromProjectEvent.actor.select(self.actor),
            self._ds.RemovedFromProjectEvent.createdAt,
            # TODO: Add this as soon as this leaves schema-preview
            #  https://docs.github.com/en/graphql/overview/schema-previews#project-event-details-preview
            # self._ds.RemovedFromProjectEvent.project.select(self._ds.Project.name, self._ds.Project.url),
        )

        return removed_from_project_event_fields

    @property
    def renamed_title_event(self) -> DSLFragment:
        renamed_title_event_fields = DSLFragment("renamedTitleEventFields")
        renamed_title_event_fields.on(self._ds.RenamedTitleEvent)
        renamed_title_event_fields.select(
            self._ds.RenamedTitleEvent.actor.select(self.actor),
            self._ds.RenamedTitleEvent.createdAt,
            self._ds.RenamedTitleEvent.currentTitle,
            self._ds.RenamedTitleEvent.previousTitle,
        )

        return renamed_title_event_fields

    @property
    def reopened_event(self) -> DSLFragment:
        reopened_event_fields = DSLFragment("reopenedEventFields")
        reopened_event_fields.on(self._ds.ReopenedEvent)
        reopened_event_fields.select(
            self._ds.ReopenedEvent.actor.select(self.actor),
            self._ds.ReopenedEvent.createdAt,
        )

        return reopened_event_fields

    @property
    def review_dismissed_event(self) -> DSLFragment:
        review_dismissed_event_fields = DSLFragment("reviewDismissedEventFields")
        review_dismissed_event_fields.on(self._ds.ReviewDismissedEvent)
        review_dismissed_event_fields.select(
            self._ds.ReviewDismissedEvent.actor.select(self.actor),
            self._ds.ReviewDismissedEvent.createdAt,
            self._ds.ReviewDismissedEvent.dismissalMessage,
            self._ds.ReviewDismissedEvent.previousReviewState,
            self._ds.ReviewDismissedEvent.url,
        )

        return review_dismissed_event_fields

    @property
    def review_request_removed_event(self) -> DSLFragment:
        review_request_removed_event_fields = DSLFragment("reviewRequestRemovedEventFields")
        review_request_removed_event_fields.on(self._ds.ReviewRequestRemovedEvent)
        review_request_removed_event_fields.select(
            self._ds.ReviewRequestRemovedEvent.actor.select(self.actor),
            self._ds.ReviewRequestRemovedEvent.createdAt,
            self._ds.ReviewRequestRemovedEvent.requestedReviewer.select(
                self.actor,
                self.team,
            ),
        )

        return review_request_removed_event_fields

    @property
    def review_requested_event(self) -> DSLFragment:
        review_requested_event_fields = DSLFragment("reviewRequestedEventFields")
        review_requested_event_fields.on(self._ds.ReviewRequestedEvent)
        review_requested_event_fields.select(
            self._ds.ReviewRequestedEvent.actor.select(self.actor),
            self._ds.ReviewRequestedEvent.createdAt,
            self._ds.ReviewRequestedEvent.requestedReviewer.select(
                self.actor,
                self.team,
            ),
        )

        return review_requested_event_fields

    @property
    def transferred_event(self) -> DSLFragment:
        transferred_event_fields = DSLFragment("transferredEventFields")
        transferred_event_fields.on(self._ds.TransferredEvent)
        transferred_event_fields.select(
            self._ds.TransferredEvent.actor.select(self.actor),
            self._ds.TransferredEvent.createdAt,
            self._ds.TransferredEvent.fromRepository.select(
                self._ds.Repository.nameWithOwner,
                self._ds.Repository.url,
            ),
        )

        return transferred_event_fields

    @property
    def unassigned_event(self) -> DSLFragment:
        unassigned_event_fields = DSLFragment("unassignedEventFields")
        unassigned_event_fields.on(self._ds.UnassignedEvent)
        unassigned_event_fields.select(
            self._ds.UnassignedEvent.actor.select(self.actor),
            self._ds.UnassignedEvent.assignee.select(self.actor),
            self._ds.UnassignedEvent.createdAt,
        )

        return unassigned_event_fields

    @property
    def unlabeled_event(self) -> DSLFragment:
        unlabeled_event_fields = DSLFragment("unlabeledEventFields")
        unlabeled_event_fields.on(self._ds.UnlabeledEvent)
        unlabeled_event_fields.select(
            self._ds.UnlabeledEvent.actor.select(self.actor),
            self._ds.UnlabeledEvent.createdAt,
            self._ds.UnlabeledEvent.label.select(self.label),
        )

        return unlabeled_event_fields

    @property
    def unlocked_event(self) -> DSLFragment:
        unlocked_event_fields = DSLFragment("unlockedEventFields")
        unlocked_event_fields.on(self._ds.UnlockedEvent)
        unlocked_event_fields.select(
            self._ds.UnlockedEvent.actor.select(self.actor),
            self._ds.UnlockedEvent.createdAt,
        )

        return unlocked_event_fields

    @property
    def unmarked_as_duplicate_event(self) -> DSLFragment:
        issue, pull_request = self.issue_or_pull_request

        unmarked_as_duplicate_event_fields = DSLFragment("unmarkedAsDuplicateEventFields")
        unmarked_as_duplicate_event_fields.on(self._ds.UnmarkedAsDuplicateEvent)
        unmarked_as_duplicate_event_fields.select(
            self._ds.UnmarkedAsDuplicateEvent.actor.select(self.actor),
            self._ds.UnmarkedAsDuplicateEvent.canonical.select(
                issue,
                pull_request,
            ),
            self._ds.UnmarkedAsDuplicateEvent.createdAt,
        )

        return unmarked_as_duplicate_event_fields

    @property
    def unpinned_event(self) -> DSLFragment:
        unpinned_event_fields = DSLFragment("unpinnedEventFields")
        unpinned_event_fields.on(self._ds.UnpinnedEvent)
        unpinned_event_fields.select(
            self._ds.UnpinnedEvent.actor.select(self.actor),
            self._ds.UnpinnedEvent.createdAt,
        )

        return unpinned_event_fields

    @property
    def pull_request_timeline_items_connection(self) -> DSLFragment:
        pull_request_timeline_items_connection_fields = DSLFragment("pullRequestTimelineItemsConnectionFields")
        pull_request_timeline_items_connection_fields.on(self._ds.PullRequestTimelineItemsConnection)
        pull_request_timeline_items_connection_fields.select(
            self._ds.PullRequestTimelineItemsConnection.nodes.select(
                DSLMetaField("__typename"),
                self.added_to_merge_queue_event,
                self.added_to_project_event,
                self.assigned_event,
                self.auto_merge_disabled_event,
                self.auto_merge_enabled_event,
                self.auto_rebase_enabled_event,
                self.auto_squash_enabled_event,
                self.automatic_base_change_failed_event,
                self.automatic_base_change_succeeded_event,
                self.base_ref_changed_event,
                self.base_ref_deleted_event,
                self.base_ref_force_pushed_event,
                self.closed_event,
                self.comment_deleted_event,
                self.connected_event,
                self.convert_to_draft_event,
                self.converted_note_to_issue_event,
                self.converted_to_discussion_event,
                self.cross_referenced_event,
                self.demilestoned_event,
                self.deployed_event,
                self.deployment_environment_changed_event,
                self.disconnected_event,
                self.head_ref_deleted_event,
                self.head_ref_force_pushed_event,
                self.head_ref_restored_event,
                self.issue_comment,
                self.labeled_event,
                self.locked_event,
                self.marked_as_duplicate_event,
                self.mentioned_event,
                self.merged_event,
                self.milestoned_event,
                self.moved_columns_in_project_event,
                self.pinned_event,
                self.pull_request_commit,
                self.pull_request_commit_comment_thread,
                self.pull_request_review,
                self.pull_request_review_thread,
                # NOTE: This is not useful to back up
                # self.pull_request_revision_marker,
                self.ready_for_review_event,
                self.referenced_event,
                self.removed_from_merge_queue_event,
                self.removed_from_project_event,
                self.renamed_title_event,
                self.reopened_event,
                self.review_dismissed_event,
                self.review_request_removed_event,
                self.review_requested_event,
                # NOTE: This is not useful to back up
                # self.subscribed_event,
                self.transferred_event,
                self.unassigned_event,
                self.unlabeled_event,
                self.unlocked_event,
                self.unmarked_as_duplicate_event,
                self.unpinned_event,
                # NOTE: These are not useful to back up
                # self.unsubscribed_event,
                # self.user_blocked_event,
            ),
            self._ds.PullRequestTimelineItemsConnection.pageInfo.select(self.page_info),
            self._ds.PullRequestTimelineItemsConnection.totalCount,
        )

        return pull_request_timeline_items_connection_fields

    @property
    def issue_timeline_items_connection(self) -> DSLFragment:
        issue_timeline_items_connection_fields = DSLFragment("issueTimelineItemsConnection")
        issue_timeline_items_connection_fields.on(self._ds.IssueTimelineItemsConnection)
        issue_timeline_items_connection_fields.select(
            self._ds.IssueTimelineItemsConnection.nodes.select(
                DSLMetaField("__typename"),
                self.added_to_project_event,
                self.assigned_event,
                self.closed_event,
                self.comment_deleted_event,
                self.connected_event,
                self.converted_note_to_issue_event,
                self.converted_to_discussion_event,
                self.cross_referenced_event,
                self.demilestoned_event,
                self.disconnected_event,
                self.issue_comment,
                self.labeled_event,
                self.locked_event,
                self.marked_as_duplicate_event,
                self.mentioned_event,
                self.milestoned_event,
                self.moved_columns_in_project_event,
                self.pinned_event,
                self.referenced_event,
                self.removed_from_project_event,
                self.renamed_title_event,
                self.reopened_event,
                # NOTE: This is not useful to back up
                # self.subscribed_event,
                self.transferred_event,
                self.unassigned_event,
                self.unlabeled_event,
                self.unlocked_event,
                self.unmarked_as_duplicate_event,
                self.unpinned_event,
                # NOTE: These are not useful to back up
                # self.unsubscribed_event,
                # self.user_blocked_event,
            ),
            self._ds.IssueTimelineItemsConnection.pageInfo.select(self.page_info),
            self._ds.IssueTimelineItemsConnection.totalCount,
        )

        return issue_timeline_items_connection_fields

    @property
    def issue(self) -> DSLFragment:
        issue_fields = DSLFragment("issueFields")
        issue_fields.on(self._ds.Issue)
        issue_fields.select(
            self.node,
            self._ds.Issue.author.select(self.actor),
            self._ds.Issue.body,
            self._ds.Issue.createdAt,
            self._ds.Issue.labels(
                first=self.var.issueLabelsPerPage.default(self.DEFAULT_ISSUE_LABELS_PER_PAGE),
                after=self.var.issueLabelsCursor,
            ).select(
                self._ds.LabelConnection.nodes.select(self.label),
                self._ds.LabelConnection.pageInfo.select(self.page_info),
                self._ds.LabelConnection.totalCount,
            ),
            self._ds.Issue.number,
            self._ds.Issue.reactionGroups.select(self.reaction_group),
            self._ds.Issue.state,
            self._ds.Issue.stateReason,
            self._ds.Issue.timelineItems(
                first=self.var.itemsPerPage,
                after=self.var.itemsCursor,
            ).select(self.issue_timeline_items_connection),
            self._ds.Issue.title,
            self._ds.Issue.url,
        )

        return issue_fields

    @property
    def pull_request(self) -> DSLFragment:
        pull_request_fields = DSLFragment("pullRequestFields")
        pull_request_fields.on(self._ds.PullRequest)
        pull_request_fields.select(
            self.node,
            self._ds.PullRequest.author.select(self.actor),
            self._ds.PullRequest.body,
            self._ds.PullRequest.createdAt,
            self._ds.PullRequest.labels(
                first=self.var.pullRequestLabelsPerPage.default(self.DEFAULT_PULL_REQUEST_LABELS_PER_PAGE),
                after=self.var.pullRequestLabelsCursor,
            ).select(
                self._ds.LabelConnection.nodes.select(self.label),
                self._ds.LabelConnection.pageInfo.select(self.page_info),
                self._ds.LabelConnection.totalCount,
            ),
            self._ds.PullRequest.number,
            self._ds.PullRequest.reactionGroups.select(self.reaction_group),
            self._ds.PullRequest.state,
            self._ds.PullRequest.timelineItems(
                first=self.var.itemsPerPage,
                after=self.var.itemsCursor,
            ).select(self.pull_request_timeline_items_connection),
            self._ds.PullRequest.title,
            self._ds.PullRequest.url,
        )

        return pull_request_fields

    @property
    def issue_timeline_items(self) -> DSLFragment:
        issue_timeline_items_fields = DSLFragment("issueTimelineItemsFields")
        issue_timeline_items_fields.on(self._ds.Issue)
        issue_timeline_items_fields.select(
            self._ds.Issue.timelineItems(
                first=self.var.itemsPerPage,
                after=self.var.itemsCursor,
            ).select(self.issue_timeline_items_connection),
        )

        return issue_timeline_items_fields

    @property
    def pull_request_timeline_items(self) -> DSLFragment:
        pull_request_timeline_items_fields = DSLFragment("pullRequestTimelineItemsFields")
        pull_request_timeline_items_fields.on(self._ds.PullRequest)
        pull_request_timeline_items_fields.select(
            self._ds.PullRequest.timelineItems(
                first=self.var.itemsPerPage,
                after=self.var.itemsCursor,
            ).select(self.pull_request_timeline_items_connection),
        )

        return pull_request_timeline_items_fields
