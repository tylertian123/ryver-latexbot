import requests
from typing import *

def get_comic(number: int = None) -> Union[Dict[str, Any], None]:
    """
    Get an xkcd by number or the latest xkcd.

    If the comic does not exist, this function returns None.
    All other errors will raise a requests.HTTPError.

    Upon success, returns a dictionary in the following format:
    - "day", "month", "year": The date of the comic
    - "num": The comic number
    - "safe_title": The comic title
    - "img": A link to the comic image
    - "alt": The alt text
    - "title": The title of the comic
    - "safe_title": The title of the comic without Unicode (I think?)
    - "transcript": The comic transcript
    - "link": Unknown (always seems to be an empty string)
    - "news": Additional info
    - "extra_parts": Used for special comics, usually interactive ones (may not exist)
    """
    resp = requests.get(f"https://xkcd.com/{number}/info.0.json" if number else "https://xkcd.com/info.0.json")
    # Comic does not exist
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()
