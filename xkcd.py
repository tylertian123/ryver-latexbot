import aiohttp
from typing import *

async def get_comic(number: int = None) -> Union[Dict[str, Any], None]:
    """
    Get an xkcd by number or the latest xkcd.

    If the comic does not exist, this function returns None.
    All other errors will raise a requests.HTTPError.

    Upon success, returns a dictionary in the following format:
    - "day", "month", "year": The date of the comic (str)
    - "num": The comic number (int)
    - "safe_title": The comic title (str)
    - "img": A link to the comic image (str)
    - "alt": The alt text (str)
    - "title": The title of the comic (str)
    - "safe_title": The title of the comic without Unicode (I think?) (str)
    - "transcript": The comic transcript (str)
    - "link": Unknown (always seems to be an empty string) (str)
    - "news": Additional info (str)
    - "extra_parts": Used for special comics, usually interactive ones (may not exist) (obj)
    """
    url = f"https://xkcd.com/{number}/info.0.json" if number else "https://xkcd.com/info.0.json"
    async with aiohttp.request("GET", url) as resp:
        # Comic does not exist
        if resp.status == 404:
            return None
        resp.raise_for_status()
        return await resp.json()


def comic_to_str(comic: Dict[str, Any]) -> str:
    """
    Convert a comic info dict to a markdown-formatted message string.
    """
    msg = f"Comic #{comic['num']} (Posted {comic['year']}-{comic['month'].zfill(2)}-{comic['day'].zfill(2)}):\n\n"
    msg += f"# {comic['title']}\n![{comic['alt']}]({comic['img']})\n*Alt: {comic['alt']}*"
    if "extra_parts" in comic:
        msg += "\n\n***Note: This comic contains extra parts that cannot be displayed here. "
        msg += f"Check out the full comic at https://xkcd.com/{comic['num']}.***"
    return msg
