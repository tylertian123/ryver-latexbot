import typing


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
    return f"[**{data['name']}**]({data['html_url']})"


def format_commit_sha(commit: str, repo: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub commit SHA into a Markdown message.
    """
    return f"[{commit[:7]}]({repo['html_url']}/commit/{commit})"


####### Begin Event Formatters #######


def format_event_commit_comment(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub commit_comment event into a string.
    """
    if data['action'] != "created":
        return None
    resp = f"{format_author(data['sender'])} [commented]({data['comment']['html_url']}) on commit "
    resp += f"{format_commit_sha(data['comment']['commit_id'], data['repository'])} in "
    resp += f"{format_repo(data['repository'])}:\n\n{data['comment']['body']}."
    return resp


def format_event_ping(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub ping event into a string.
    """
    resp = f"A webhook of type {data['hook']['type']} has been created for "
    if "repository" in data:
        resp += f"the repository **{data['repository']['name']}**!"
    elif "organization" in data:
        resp += f"the organization **{data['organization']['name']}**!"
    resp += f"\n\n*{data['zen']}*"
    return resp


def format_event_push(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub push event into a Markdown message.
    """
    resp = format_author(data["pusher"]) + " "
    if data['deleted']:
        resp += f"deleted ref [*{data['ref']}*]({data['repository']['html_url']}/tree/{data['ref']}) in {format_repo(data['repository'])}."
    else:
        resp += f"{'force ' if data['forced'] else ''}pushed {len(data['commits'])} commits to ref "
        resp += f"[*{data['ref']}*]({data['repository']['html_url']}/tree/{data['ref']}) in {format_repo(data['repository'])}.\n"
        resp += f"[Compare Changes]({data['compare']})\n\nCommits pushed:\n| Commit | Author | Message |\n| --- | --- | --- |"
        for commit in data['commits']:
            commit_sha = commit.get("sha") or commit.get("id")
            resp += f"\n{format_commit_sha(commit_sha, data['repository'])} | "
            commit_title = commit['message'].split('\n')[0]
            resp += f"{format_author(commit['author'])} | {commit_title}"
    return resp


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
        return f"{format_author(data['sender'])} starred {format_repo(data['repository'])}!"
    else:
        return None


FORMATTERS = {
    "commit_comment": format_event_commit_comment,
    "ping": format_event_ping,
    "push": format_event_push,
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
