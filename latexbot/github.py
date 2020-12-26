import typing
from markdownify import markdownify


def format_author(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub author JSON into a Markdown message.
    """
    if "name" in data and "email" in data:
        return f"**{data['name']}** (*{data['email']}*)"
    else:
        return f"[**{data['login']}**]({data['html_url']})"


def format_repo(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub repository JSON into a Markdown message.
    """
    return f"[**{data['full_name']}**]({data['html_url']})"


def format_issue_or_pr(data: typing.Dict[str, typing.Any], include_title: bool = True) -> str:
    """
    Format a GitHub issue or pull request JSON into a markdown message.

    If include_title is true, the title of the issue will also be included.
    """
    result = f"[**#{data['number']}**]({data['html_url']})"
    if include_title:
        result += f" (*{data['title']}*)"
    if data.get("draft", False):
        result += " (Draft)"
    return result


def format_commit_sha(commit: str, repo: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub commit SHA into a Markdown message.
    """
    return f"[{commit[:7]}]({repo['html_url']}/commit/{commit})"


def format_ref(ref: str, repo: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub ref into a Markdown message.
    """
    if ref.startswith("refs/heads/"):
        ref = ref[len("refs/heads/"):]
        result = "branch"
    elif ref.startswith("refs/tags/"):
        ref = ref[len("refs/heads/"):]
        result = "tag"
    elif ref.startswith("refs/"):
        result = "ref"
    return f"{result} [*{ref}*]({repo['html_url']}/tree/{ref})"


####### Begin Event Formatters #######


def format_event_commit_comment(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub commit_comment event into a string.
    """
    if data['action'] != "created":
        return None
    resp = f"{format_author(data['sender'])} [commented]({data['comment']['html_url']}) on commit "
    resp += f"{format_commit_sha(data['comment']['commit_id'], data['repository'])} in "
    resp += f"{format_repo(data['repository'])}:\n\n{markdownify(data['comment']['body'])}."
    return resp


CHECK_RUN_PREFIXES = {
    "success": ":white_check_mark: Check Success:",
    "failure": ":x: Check Failed:",
    "neutral": ":heavy_minus_sign: Check Neutral:",
    "cancelled": ":warning: Check Cancelled:",
    "timed_out": ":clock3: Check Timed Out:",
    "action_required": ":heavy_exclamation_mark: Check Action Required:",
    "stale": ":clock3: Check Stale:",
}


def format_event_check_run(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub check_run event into a string.
    """
    if data['action'] == "created":
        resp = f"Check [**{data['check_run']['name']}**]({data['check_run']['html_url']}) created on branch "
        resp += f"[*{data['check_run']['check_suite']['head_branch']}*]({data['repository']['html_url']}/tree/{data['check_run']['check_suite']['head_branch']}) "
        resp += f"in {format_repo(data['repository'])}."
    elif data['action'] == "completed":
        resp = f"{CHECK_RUN_PREFIXES[data['check_run']['conclusion']]} [**{data['check_run']['name']}**]({data['check_run']['html_url']}) "
        resp += f"on branch [*{data['check_run']['check_suite']['head_branch']}*]({data['repository']['html_url']}/tree/{data['check_run']['check_suite']['head_branch']}) "
        resp += f"in {format_repo(data['repository'])}."
    else:
        resp = None
    return resp


def format_event_fork(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub fork event into a string.
    """
    resp = f":fork_and_knife: {format_author(data['sender'])} forked {format_repo(data['repository'])}: "
    resp += f"{format_repo(data['forkee'])}."
    return resp


def format_event_issues(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub issues event into a string.
    """
    resp = f"{format_author(data['sender'])} {data['action']} "
    description = f"issue {format_issue_or_pr(data['issue'])} in {format_repo(data['repository'])}"
    if data['action'] in ("opened", "edited"):
        resp += f"issue {format_issue_or_pr(data['issue'], False)} in {format_repo(data['repository'])}:\n\n"
        resp += f"# {data['issue']['title']}\n{markdownify(data['issue']['body'])}"
    elif data['action'] in ("deleted", "pinned", "unpinned", "closed", "reopened", "locked", "unlocked"):
        resp += f"{description}."
    elif data['action'] in ("assigned", "unassigned"):
        resp += f"{format_author(data['assignee'])} to {description}."
    elif data['action'] in ("labeled", "unlabeled"):
        resp += f"{description} as [**{data['label']['name']}**]({data['repository']['html_url']}/labels/{data['label']['name']})."
    else:
        return None
    return resp


def format_event_issue_comment(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub issue_comment event into a string.
    """
    if data['action'] == "deleted":
        return None
    resp = f"{format_author(data['sender'])} "
    if data['action'] == "created":
        resp += f"[commented]({data['comment']['html_url']}) on issue "
    else:
        resp += f"edited [their comment]({data['comment']['html_url']}) on issue "
    resp += f"{format_issue_or_pr(data['issue'])} in {format_repo(data['repository'])}:\n\n{markdownify(data['comment']['body'])}"
    return resp


def format_event_organization(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub organization event into a string.
    """
    if data['action'] == "member_added":
        resp = f"Welcome {format_author(data['membership']['user'])} to "
        resp += f"[**{data['organization']['login']}**](https://github.com/{data['organization']['login']})!"
    else:
        return None
    return resp


def format_event_ping(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub ping event into a string.
    """
    resp = f"A webhook of type {data['hook']['type']} has been created for "
    if "repository" in data:
        resp += f"the repository **{data['repository']['name']}**!"
    elif "organization" in data:
        resp += f"the organization **{data['organization']['login']}**!"
    resp += f"\n\n*{data['zen']}*"
    return resp


def format_event_pull_request(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub pull_request event into a string.
    """
    resp = f"{format_author(data['sender'])} "
    description = f"{format_issue_or_pr(data['pull_request'])} in {format_repo(data['repository'])}"
    if data['action'] in ("opened", "edited"):
        resp += f"{data['action']} pull request {format_issue_or_pr(data['pull_request'], False)} in "
        resp += f"{format_repo(data['repository'])}:\n\n# {data['pull_request']['title']}\n{markdownify(data['pull_request']['body'])}"
    elif data['action'] == "closed":
        resp += f"{'merged' if data['pull_request']['merged'] else 'closed without merging'} pull request {description}."
    elif data['action'] in ("locked", "unlocked", "reopened"):
        resp += f"{data['action']} pull request {description}."
    elif data['action'] == "ready_for_review":
        resp = f"Pull request {description} is ready for review."
    elif data['action'] == "review_requested":
        resp += f"is requesting reviews for {description} from {format_author(data['requested_reviewer'])}."
    elif data['action'] == "review_request_removed":
        resp += f"is no longer requesting reviews for {description} from {format_author(data['requested_reviewer'])}."
    elif data['action'] in ("assigned", "unassigned"):
        resp += f"{data['action']} {format_author(data['assignee'])} to pull request {description}."
    elif data['action'] in ("labeled", "unlabeled"):
        resp += f"{data['action']} pull request {description} as [**{data['label']['name']}**]"
        resp += f"({data['repository']['html_url']}/labels/{data['label']['name']})."
    else:
        return None
    return resp


def format_event_pull_request_review(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub pull_request_review event into a string.
    """
    description = f"{format_issue_or_pr(data['pull_request'])} in {format_repo(data['repository'])}"
    resp = f"{format_author(data['sender'])} "
    if data["review"]["state"] == "commented":
        state = "commenting on"
    elif data["review"]["state"] == "approved":
        state = "approving"
    elif data["review"]["state"] == "changes_requested":
        state = "requesting changes to"

    if data['action'] == "submitted":
        resp += f"submitted [a review]({data['review']['html_url']}) **{state}** pull request {description}:\n\n"
        resp += markdownify(data["review"]["body"])
    elif data['action'] == "edited":
        resp += f"edited [their review]({data['review']['html_url']}) **{state}** pull request {description}:\n\n"
        resp += markdownify(data["review"]["body"])
    elif data['action'] == "dismissed":
        resp += f"dismissed {format_author(data['review']['user'])}'s [review]({data['review']['html_url']}) "
        resp += f"for pull request {description}."
    else:
        return None
    return resp


def format_event_pull_request_review_comment(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub pull_request_review_comment event into a string.
    """
    if data['action'] == "deleted":
        return None
    resp = f"{format_author(data['sender'])} "
    if data['action'] == "created":
        resp += f"[commented]({data['comment']['html_url']}) on pull request "
    else:
        resp += f"edited [their comment]({data['comment']['html_url']}) on pull request "
    resp += f"{format_issue_or_pr(data['pull_request'])} in {format_repo(data['repository'])}:\n\n{markdownify(data['comment']['body'])}"
    return resp


def format_event_push(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub push event into a Markdown message.
    """
    resp = format_author(data["pusher"]) + " "
    if data['deleted']:
        resp += f"deleted {format_ref(data['ref'], data['repository'])} in {format_repo(data['repository'])}."
    else:
        if data['ref'].startswith("refs/tags/"):
            resp += f"pushed the tag {format_ref(data['ref'], data['repository'])} to {format_repo(data['repository'])}."
        else:
            resp += f"{'force ' if data['forced'] else ''}pushed {len(data['commits'])} commit(s) to "
            resp += f"{format_ref(data['ref'], data['repository'])} in {format_repo(data['repository'])}.\n"
            resp += f"[Compare Changes]({data['compare']})\n\nCommits pushed:\n| Commit | Author | Message |\n| --- | --- | --- |"
            for commit in data['commits']:
                commit_sha = commit.get("sha") or commit.get("id")
                resp += f"\n{format_commit_sha(commit_sha, data['repository'])} | "
                commit_title = commit['message'].split('\n')[0]
                resp += f"{format_author(commit['author'])} | {commit_title}"
    return resp


def format_event_release(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub release event into a string.
    """
    if data["action"] == "published":
        release_name = data['release'].get("name") or data['release'].get("tag_name")
        resp = f"{format_author(data['sender'])} published a new "
        resp += "pre-release" if data['release']['prerelease'] else "release"
        resp += f", [**{release_name}**]({data['release']['html_url']}), for {format_repo(data['repository'])}!"
        return resp
    else:
        return None


def format_event_repository(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub repository event into a string.
    """
    resp = f"The repository {format_repo(data['repository'])} has been {data['action']} "
    resp += f"by {format_author(data['sender'])}."
    return resp


def format_event_star(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub star event into a string.
    """
    if data['action'] == "created":
        return f":star: {format_author(data['sender'])} starred {format_repo(data['repository'])}!"
    else:
        return None


FORMATTERS = {
    "commit_comment": format_event_commit_comment,
    "check_run": format_event_check_run,
    "fork": format_event_fork,
    "issues": format_event_issues,
    "issue_comment": format_event_issue_comment,
    "organization": format_event_organization,
    "ping": format_event_ping,
    "pull_request": format_event_pull_request,
    "pull_request_review": format_event_pull_request_review,
    "pull_request_review_comment": format_event_pull_request_review_comment,
    "push": format_event_push,
    "release": format_event_release,
    "repository": format_event_repository,
    "star": format_event_star,
}


def format_gh_json(event: str, data: typing.Dict[str, typing.Any]) -> str:
    """
    Format the JSON sent by a GitHub webhook into a Markdown message.

    The event parameter should contain the event type, which is given in the
    X-GitHub-Event header field in the request.

    If a handler is not defined, returns None.
    """
    return FORMATTERS.get(event, lambda x: None)(data)
