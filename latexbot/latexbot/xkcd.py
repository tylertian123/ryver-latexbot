import aiohttp
from typing import Union, Dict, Any

async def get_comic(number: int = None, session: aiohttp.ClientSession = None) -> Union[Dict[str, Any], None]:
    """
    Get an xkcd by number or the latest xkcd.

    If the comic does not exist, this function returns None.
    All other errors will raise a aiohttp.ClientResponseError.

    An optional client session may be provided.

    Upon success, returns a dictionary in the following format:
    - "day", "month", "year": The date of the comic (str)
    - "num": The comic number (int)
    - "safe_title": The comic title (str)
    - "img": A link to the comic image (str)
    - "alt": The alt text (str)
    - "title": The title of the comic (str)
    - "safe_title": The title of the comic without Unicode (I think?) (str)
    - "transcript": The comic transcript (str)
    - "link": The URL the comic image links to, or an empty string (str)
    - "news": Additional info (str)
    - "extra_parts": Used for special comics, usually interactive ones (may not exist) (obj)
    """
    url = f"https://xkcd.com/{number}/info.0.json" if number else "https://xkcd.com/info.0.json"
    if session is not None:
        req = session.get(url)
    else:
        req = aiohttp.request("GET", url)
    async with req as resp:
        # Comic does not exist
        if resp.status == 404:
            return None
        resp.raise_for_status()
        return await resp.json()


def comic_to_str(comic: Dict[str, Any]) -> str:
    """
    Convert a comic info dict to a markdown-formatted message string.
    """
    msg = f"Comic #{comic['num']} (Posted {comic['year']}-{comic['month'].zfill(2)}-{comic['day'].zfill(2)}):\n\n# {comic['title']}\n"
    if comic["link"]:
        msg += f"[![{comic['alt']}]({comic['img']})]({comic['link']})"
    else:
        msg += f"![{comic['alt']}]({comic['img']})"
    msg += f"\n*Alt: {comic['alt']}*"
    if "extra_parts" in comic:
        msg += "\n\n***Note: This comic contains extra parts that cannot be displayed here. "
        msg += f"Check out the full comic at https://xkcd.com/{comic['num']}.***"
    return msg
