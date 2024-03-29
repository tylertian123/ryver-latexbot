"""
Utility functions and constants.
"""

import aiohttp
import asyncio
import datetime
import json
import marshmallow
import pyryver
import re
import string
import typing


DATE_FORMAT = "%Y-%m-%d %H:%M"
CALENDAR_DATE_FORMAT = "%Y-%m-%d"
DATE_DISPLAY_FORMAT = "%b %d %Y"
TIME_DISPLAY_FORMAT = "%I:%M %p"
DATETIME_DISPLAY_FORMAT = DATE_DISPLAY_FORMAT + " " + TIME_DISPLAY_FORMAT
ALL_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%b %d %Y",
    "%b %d, %Y",
]
ALL_TIME_FORMATS = [
    "%H:%M",
    "%I:%M %p",
    "%I:%M%p",
]

XKCD_PROFILE = "https://www.explainxkcd.com/wiki/images/6/6d/BlackHat_head.png"

MACRO_CHARS = set(string.ascii_lowercase + string.digits + "_")

MENTION_REGEX = re.compile(r"((?:^|[^a-zA-Z0-9_!@#$%&*\\])(?:(?:@)(?!\/)))([a-zA-Z0-9_]*)(?:\b(?!@)|$)", flags=re.MULTILINE)
MACRO_REGEX = re.compile(r"(^|[^a-z0-9_\\])\.([a-z0-9_]+)\b", flags=re.MULTILINE)
CHAT_LOOKUP_REGEX = re.compile(r"([a-z]+)=(.*)")


async def get_msgs_before(chat: pyryver.Chat, msg_id: str, count: int) -> typing.List[pyryver.ChatMessage]:
    """
    Get any number of messages before a message from an ID.

    This is similar to using pyryver.Chat.get_message(), except it doesn't have the 25 message restriction.

    Note that the oldest message is first!
    """
    msgs = []
    # Get around the 25 message restriction
    # Cut off the last one (that one is the message with the id specified)
    msgs = (await pyryver.retry_until_available(chat.get_messages_surrounding, msg_id, before=min(25, count), timeout=5.0))[:-1]
    count -= len(msgs)
    while count > 0:
        prev_msgs = (await pyryver.retry_until_available(chat.get_messages_surrounding, msgs[0].get_id(), before=min(25, count), timeout=5.0))[:-1]
        msgs = prev_msgs + msgs
        count -= len(prev_msgs)
    return msgs


def parse_chat_name(ryver: pyryver.Ryver, name: str) -> pyryver.Chat:
    """
    Parse a chat name expression in the form [(name|nickname|username|email|id|jid)=][+|@]<forum|team|user>
    and return the correct chat.
    """
    if not name:
        raise ValueError("Name cannot be none or empty")
    match = CHAT_LOOKUP_REGEX.match(name) # type: re.Match
    if match:
        key = match.group(1)
        val = match.group(2)
        if key not in ("name", "nickname", "id", "jid", "email", "username"):
            raise ValueError(f"Invalid query param type: {key}")
        if key == "id":
            val = int(val)
        # Handle chat/user mention in query
        elif (key == "nickname" and val.startswith("+")) or (key == "username" and val.startswith("@")):
            val = val[1:]
        # Handle both users and teams/forums
        # Nicknames only apply to group chats
        if key == "nickname":
            return ryver.get_groupchat(**{key: val})
        # Emails and usernames can only be used to look up users
        if key == "email" or key == "username":
            return ryver.get_user(**{key: val})
        # IDs and JIDs can be used to look up anything
        if key == "id" or key == "jid":
            return ryver.get_chat(**{key: val})
        # Names are ambiguous, so try both
        return ryver.get_groupchat(**{key: val}) or ryver.get_user(**{key: val})
    # Alternative mention syntax
    elif name.startswith("@"):
        name = name[1:]
        return ryver.get_user(username=name)
    # Alternative nickname syntax
    elif name.startswith("+"):
        name = name[1:]
        return ryver.get_groupchat(nickname=name)
    return ryver.get_groupchat(name=name) or ryver.get_user(name=name)


def sanitize(msg: str) -> str:
    """
    Sanitize the given input text.

    Currently, this method makes all mentions ineffective by putting a space between the @ and the username.
    """
    return MENTION_REGEX.sub(r"\1 \2", msg)


def caldays_diff(a: datetime.datetime, b: datetime.datetime) -> int:
    """
    Calculate the difference in calendar days between a and b (a - b).

    Note this is different from just the regular difference, as the passing of a calendar day can be less than 24h.
    """
    a = a.replace(hour=0, minute=0, second=0, microsecond=0)
    b = b.replace(hour=0, minute=0, second=0, microsecond=0)
    return (a - b).days


_T = typing.TypeVar("_T")


def split_list(l: typing.List[_T], v: _T) -> typing.List[typing.List[_T]]:
    """
    Split a list into smaller lists by value.
    """
    start = 0
    result = []
    for i, elem in enumerate(l):
        if elem == v:
            result.append(l[start:i])
            start = i + 1
    result.append(l[start:])
    return result


def tryparse_datetime(s: str, formats: typing.List[str]) -> datetime:
    """
    Tries to parse the given string with any of the formats listed.

    If all formats fail, returns None.
    """
    for fmt in formats:
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def format_access_rules(ryver: pyryver.Ryver, command: str, rule) -> str:
    """
    Format a command's access rules into a markdown string.
    """
    result = f"Rules for command `{command}`:"
    if rule.level:
        result += f"\n- Override Level: {rule.level}"
    if rule.allow_users:
        result += f"\n- Allow Users: {', '.join(ryver.get_user(id=uid).get_username() for uid in rule.allow_users)}"
    if rule.disallow_users:
        result += f"\n- Disallow Users: {', '.join(ryver.get_user(id=uid).get_username() for uid in rule.disallow_users)}"
    if rule.allow_roles:
        result += f"\n- Allow Roles: {', '.join(rule.allow_roles)}"
    if rule.disallow_roles:
        result += f"\n- Disallow Roles: {', '.join(rule.disallow_roles)}"
    return result


async def send_json_data(chat: pyryver.Chat, data: typing.Any, message: str, filename: str, from_user: pyryver.User, msg_creator: pyryver.Creator):
    """
    Send a JSON to the chat.

    If the JSON is less than 3900 characters, it will be sent as text.
    Otherwise it will be attached as a file.
    """
    json_data = json.dumps(data, indent=2)
    if len(json_data) < 3900:
        await chat.send_message(f"```json\n{json_data}\n```", msg_creator)
    else:
        file = await chat.get_ryver().upload_file(filename, json_data, "application/json")
        await chat.send_message(message, creator=msg_creator, attachment=file, from_user=from_user)


async def get_attached_json_data(msg: pyryver.ChatMessage, msg_contents: str) -> typing.Any:
    """
    Load the JSON data attached to the message.

    If there is a file attached, the contents will be downloaded and the JSON data will
    be loaded from it. Otherwise, the message contents will be used for the data.

    If an error occurs, a ValueError will be raised with a message.
    """
    file = msg.get_attached_file()
    if file:
        # Get the actual contents
        try:
            data = (await file.download_data()).decode("utf-8")
        except aiohttp.ClientResponseError as e:
            raise ValueError(f"Error while trying to GET file attachment: {e}") from e
        except UnicodeDecodeError as e:
            raise ValueError(f"File needs to be encoded with utf-8! The following decode error occurred: {e}") from e
    else:
        data = msg_contents

    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON: {e}") from e


def slice_range(l: typing.List[_T], r: str) -> typing.List[_T]:
    """
    Slice a list based on a range specified in string form.

    A range can be one of the following:
    - A single number, e.g. "10" for the top 10 results.
    - Two numbers separated by a dash, e.g. "10-20" for the 10th result to the 20th result (inclusive).
    - A number followed by a plus, e.g. `10+`, for everything after and including the 10th result.
    """
    if r.endswith("+"):
        return l[int(r[:-1]) - 1:]
    elif "-" in r:
        start, end = r.split("-")
        return l[int(start) - 1:int(end)]
    else:
        return l[:int(r)]


def parse_args(args: typing.Iterable[str], *syntax: typing.Union[typing.Tuple[str, typing.Callable[[str], typing.Any]], typing.Tuple[str, typing.Callable[[str], typing.Any], typing.Any]]) -> typing.List[typing.Any]:
    """
    Parse arguments.

    The args should be an iterable of strings representing the values of the args.
    The syntax should each be tuples of either 2 or 3 elements, containing
    (name, func, default), where func will be used to evaluate the value of the
    argument, and default is an optional default value for the argument if not supplied.
    If the func is None, then the string value will be used directly.
    """
    if len(args) > len(syntax):
        raise ValueError("Too many arguments!")
    results = []
    for i, s in enumerate(syntax):
        if i >= len(args):
            if len(s) == 3:
                results.append(s[2])
            else:
                raise ValueError(f"Not enough arguments! Please supply a value for '{s[0]}'.")
        else:
            try:
                results.append(s[1](args[i]) if s[1] else args[i])
            except ValueError as e:
                raise ValueError(f"{args[i]} is not a valid value for '{s[0]}': {e}") from e
    return results


def paginate(text: typing.Iterable[str], title: str = "", header: str = "", sep: str = "\n", limit: int = 3900) -> typing.Generator[str, str, None]:
    """
    Break up rows of text into pages.

    Only the first page will have the title, while the header is added to every page.
    The length of each page will not exceed the limit, excluding the page number message
    at the end. Page numbers will not be added if there is only one page.

    The separator will be inserted between every pair of consecutive lines. By default a
    newline is used. No separator is inserted between the title and header or header and
    content.
    """
    pages = []
    page = None
    for row in text:
        if page is None:
            page = title + header
            new_page = page + row
        else:
            new_page = page + sep + row
        if len(new_page) < limit:
            page = new_page
        else:
            pages.append(page)
            page = header + row
    pages.append(page)
    for i, page in enumerate(pages):
        if len(pages) == 1:
            yield page
        else:
            yield page + f"\n\n*Page {i + 1} of {len(pages)}*"


def ordinal(n: int) -> str:
    """
    Return the ordinal representation of the given number, e.g. 1st, 2nd, etc.
    """
    if 10 <= n <= 20:
        return str(n) + "th"
    d = n % 10
    if 1 <= d <= 3:
        return str(n) + ["st", "nd", "rd"][d - 1]
    return str(n) + "th"


def contains_ignorecase(s: str, i: typing.Iterable[str]) -> bool:
    """
    Return whether the string s is in i when case is ignored.
    """
    return s.casefold() in (t.casefold() for t in i)


async def process_concurrent(objs: typing.List[typing.Any], process: typing.Callable[[typing.Any], typing.Awaitable], workers: int = 5):
    """
    Run a processing coroutine on a list of objects with multiple concurrent workers.
    """
    # Divide and round up
    step = (len(objs) - 1) // workers + 1
    async def _proc_range(start, end):
        for i in range(start, end):
            await process(objs[i])
    return asyncio.gather(*(_proc_range(i * step, min((i + 1) * step, len(objs))) for i in range(workers)))


def format_validation_error(e: marshmallow.ValidationError) -> str:
    """
    Format a marshmallow ValidationError into a nice markdown string.
    """
    return "\n".join(f"* {k}\n" + "\n".join(f"  * {m}" for m in v) for k, v in e.messages.items())
