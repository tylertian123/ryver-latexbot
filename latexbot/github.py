import typing


def format_author(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub author JSON into a Markdown message.
    """
    return f"**{data['name']}** (*{data['email']}*)"


def format_push(data: typing.Dict[str, typing.Any]) -> str:
    """
    Format a GitHub push event into a Markdown message.
    """
    resp = format_author(data["pusher"]) + " "
    if data['deleted']:
        resp += f"deleted ref [*{data['ref']}*]({data['repository']['html_url']}/tree/{data['ref']}) in [**{data['repository']['name']}**]({data['repository']['html_url']})."
    else:
        resp += f"{'force ' if data['forced'] else ''}pushed {len(data['commits'])} commits to ref "
        resp += f"[*{data['ref']}*]({data['repository']['html_url']}/tree/{data['ref']}) in [**{data['repository']['name']}**]({data['repository']['html_url']}).\n"
        resp += f"[Compare Changes]({data['compare']})\n\nCommits pushed:\n| Commit | Author | Message |\n| --- | --- | --- |"
        for commit in data['commits']:
            commit_sha = commit.get("sha") or commit.get("id")
            resp += f"\n[{commit_sha[:7]}]({data['repository']['html_url']}/commit/{commit_sha}) | "
            commit_title = commit['message'].split('\n')[0]
            resp += f"{format_author(commit['author'])} | {commit_title}"
    return resp


def format_ping(data: typing.Dict[str, typing.Any]) -> str:
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


FORMATTERS = {
    "push": format_push,
    "ping": format_ping
}


def format_gh_json(event: str, data: typing.Dict[str, typing.Any]) -> str:
    """
    Format the JSON sent by a GitHub webhook into a Markdown message.

    The event parameter should contain the event type, which is given in the
    X-GitHub-Event header field in the request.

    If a handler is not defined, returns None.
    """
    return FORMATTERS.get(event, lambda x: None)(data)
