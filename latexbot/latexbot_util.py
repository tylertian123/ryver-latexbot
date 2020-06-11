import org
import pyryver
import re
import typing
from datetime import datetime
from dateutil import tz
from textwrap import dedent

# Make print() flush immediately
# Otherwise the logs won't show up in real time in Docker
old_print = print


def print(*args, **kwargs): # pylint: disable=redefined-builtin, missing-docstring
    kwargs["flush"] = True
    # Add timestamp
    old_print(current_time().strftime("%Y-%m-%d %H:%M:%S"), *args, **kwargs)


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

MENTION_REGEX = re.compile(r"((?:^|[^a-zA-Z0-9_!@#$%&*])(?:(?:@)(?!\/)))([a-zA-Z0-9_]*)(?:\b(?!@)|$)", flags=re.MULTILINE)


async def get_msgs_before(chat: pyryver.Chat, msg_id: str, count: int) -> typing.List[pyryver.Message]:
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
    Parse a chat name expression in the form [(name|nickname)=]<forum|team> and return the correct chat.
    """
    # Handle the name= or nickname= syntax
    if name.startswith("name="):
        # Slice off the beginning
        name = name[len("name="):]
        return ryver.get_groupchat(name=name)
    elif name.startswith("nickname="):
        name = name[len("nickname="):]
        return ryver.get_groupchat(nickname=name)
    # Handle names starting with a + (nickname reference)
    elif name.startswith("+"):
        name = name[1:]
        return ryver.get_groupchat(nickname=name)
    return ryver.get_groupchat(name=name)


def sanitize(msg: str) -> str:
    """
    Sanitize the given input text.

    Currently, this method makes all mentions ineffective by putting a space between the @ and the username.
    """
    return MENTION_REGEX.sub(r"\1 \2", msg)


def caldays_diff(a: datetime, b: datetime) -> int:
    """
    Calculate the difference in calendar days between a and b (a - b).

    Note this is different from just the regular difference, as the passing of a calendar day can be less than 24h.
    """
    a = a.replace(hour=0, minute=0, second=0, microsecond=0)
    b = b.replace(hour=0, minute=0, second=0, microsecond=0)
    return (a - b).days


_T = typing.TypeVar("T")


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


def parse_doc(doc: str) -> typing.Dict[str, typing.Any]:
    """
    Parse command documentation into a dictionary. 

    Format:

    <Short Description>

    [Optional Long Description]
    ---
    group: <Command Group>
    syntax: <Command Syntax>
    [Other Attributes]
    ---
    > [Optional Examples]
    > [More Examples]
    """
    doc = dedent(doc).strip().split("---")
    if len(doc) < 2 or len(doc) > 3:
        raise ValueError(
            f"Doc must have between 2 or 3 sections, not {len(doc)}!")
    # All sections
    if len(doc) == 3:
        desc, attrs, examples = doc
    # No examples section
    else:
        desc, attrs = doc
        examples = None

    desc = split_list(desc.strip().splitlines(), "")
    short_desc = ' '.join(s.strip() for s in desc[0])
    # No extended description
    if len(desc) == 1:
        long_desc = None
    else:
        # Join by space for lines, then join by 2 newlines for paragraphs
        # Skip first paragraph
        paras = []
        for para in desc[1:]:
            p = ""
            # Process each line
            for line in para:
                # If line starts with -, it is a list
                # List items are separated by newlines
                if line.startswith("-"):
                    if p != "":
                        p += "\n"
                # Otherwise, separate by space
                elif p != "":
                    p += " "
                p += line
            paras.append(p)
        long_desc = '\n\n'.join(paras)
    
    if examples:
        # Strip to remove possible leading space
        # Only count lines starting with >
        examples = [ex[1:].strip() for ex in examples.strip().splitlines() if ex.startswith(">")]
    
    doc_dict = {
        "short_desc": short_desc,
        "long_desc": long_desc,
        "examples": examples,
    }

    for attr in attrs.strip().splitlines():
        try:
            name, val = attr.split(":")
        except ValueError:
            raise ValueError(f"Incorrect format: {attr}")
        doc_dict[name.strip()] = val.strip()
    return doc_dict


tz_utc = tz.tzutc()

def current_time() -> datetime:
    """
    Get the current organization time, according to the server and org time zones.
    """
    return datetime.utcnow().replace(tzinfo=tz_utc).astimezone(tz.gettz(org.org_tz))


def tryparse_datetime(s: str, formats: typing.List[str]) -> datetime:
    """
    Tries to parse the given string with any of the formats listed.

    If all formats fail, returns None.
    """
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def format_access_rules(command: str, rule: typing.Dict[str, typing.Any]) -> str:
    """
    Format a command's access rules into a markdown string.
    """
    result = f"Rules for command `{command}`:"
    if "level" in rule:
        result += f"\n- `level`: {rule['level']}"
    if "allowUser" in rule:
        result += f"\n- `allowUser`: {', '.join(rule['allowUser'])}"
    if "disallowUser" in rule:
        result += f"\n- `disallowUser`: {', '.join(rule['disallowUser'])}"
    if "allowRole" in rule:
        result += f"\n- `allowRole`: {', '.join(rule['allowRole'])}"
    if "disallowRole" in rule:
        result += f"\n- `disallowRole`: {', '.join(rule['disallowRole'])}"
    return result
