"""
Very simple module for getting top posts from Reddit.

Does not authenticate.
"""

import aiohttp
import typing

REDDIT_URL = "https://www.reddit.com"

POST_FORMAT = "# {title}\n\nPosted in [r/{sub}](https://www.reddit.com/r/{sub})" \
              + " by [u/{author}](https://www.reddit.com/u/{author}) ({votes} votes)" \
              + "  \n![{title}]({img})  \n[Link]({link})"

async def get_top_post_formatted(subreddit: str, seen: typing.Optional[typing.Collection[str]] = (),
                                 max_depth: int = 10, batch_size: int = 5, nsfw: bool = False,
                                 session: typing.Optional[aiohttp.ClientSession] = None) -> str:
    """
    Get the top post as a markdown formatted string.
    This only grabs posts that are images.

    subreddit - The subreddit to get posts from
    seen - A set of posts to exclude from the result
    max_depth - The maximum number of posts to try before giving up
    batch_size - The number of posts to get at a time (since some posts may be invalid)
    nsfw - If true, nsfw posts will not be filtered

    Raises ValueError if max depth reached without finding a suitable post.
    Raises aiohttp.ClientError for HTTP and connection errors.
    """
    url = f"{REDDIT_URL}/r/{subreddit}/top.json?limit={batch_size}"
    session_provided = session is not None
    if not session_provided:
        session = aiohttp.ClientSession()
    try:
        post = None
        after = None
        depth = 0
        while post is None:
            if depth > max_depth:
                raise ValueError(f"Max depth of {max_depth} posts searched without a suitable result")
            depth += batch_size
            # Get a batch
            async with session.get(url if after is None else url + "&after=" + after) as resp:
                data = await resp.json()
                posts = data["data"]["children"]
            after = data["data"]["after"]
            # Filter out invalid posts
            for p in posts:
                d = p["data"]
                if d.get("id") in seen or d.get("post_hint") != "image" or (not nsfw and d.get("over_18")):
                    continue
                post = d
                break
        votes = post.get("ups", 0) - post.get("downs", 0)
        votes = str(votes) if votes < 1000 else f"{votes / 1000:.1f}k"
        return POST_FORMAT.format(
            title=post.get("title"),
            link=post.get("permalink"),
            sub=post.get("subreddit"),
            author=post.get("author"),
            votes=votes,
            img=post.get("url")
        )
    # Cleanup if the session wasn't provided by the caller
    finally:
        if not session_provided:
            await session.close()
