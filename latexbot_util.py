import org
import pyryver
import re
import typing
from datetime import datetime
from dateutil import tz
from random import randrange
from textwrap import dedent
from bs4 import BeautifulSoup


ACCESS_LEVEL_EVERYONE = 0
ACCESS_LEVEL_FORUM_ADMIN = 1
ACCESS_LEVEL_ORG_ADMIN = 2
ACCESS_LEVEL_BOT_ADMIN = 3
ACCESS_LEVEL_TYLER = 9001

ACCESS_LEVEL_STRS = {
    ACCESS_LEVEL_EVERYONE: "",
    ACCESS_LEVEL_FORUM_ADMIN: "**Accessible to Forum, Org and Bot Admins only.**",
    ACCESS_LEVEL_ORG_ADMIN: "**Accessible to Org and Bot Admins only.**",
    ACCESS_LEVEL_BOT_ADMIN: "**Accessible to Bot Admins only.**",
    ACCESS_LEVEL_TYLER: "**Accessible to Tyler only.**"
}

ACCESS_DENIED_MESSAGES = [
    "I'm sorry Dave, I'm afraid I can't do that.",
    "ACCESS DENIED",
    "![NO](https://i.kym-cdn.com/photos/images/original/001/483/348/bdd.jpg)",
    "This operation requires a higher access level. Please ask an admin.",
    "Nice try.",
    "![Access Denied](https://cdn.windowsreport.com/wp-content/uploads/2018/08/fix-access-denied-error-windows-10.jpg)",
    "![No.](https://i.imgur.com/DKUR9Tk.png)",
    "![No](https://pics.me.me/thumb_no-no-meme-face-hot-102-7-49094780.png)",
]


MENTION_REGEX = re.compile(r"(\s|^)@(\w+)(?=\s|$)", flags=re.MULTILINE)


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


def is_authorized(chat: pyryver.Chat, msg: pyryver.ChatMessage, required_level: int) -> bool:
    """
    Check if the sender of a message has a particular access level or higher.
    """
    if required_level <= ACCESS_LEVEL_EVERYONE:
        return True

    if required_level <= ACCESS_LEVEL_TYLER and msg.get_author_id() == 1311906:
        return True

    if required_level <= ACCESS_LEVEL_BOT_ADMIN and msg.get_author_id() in org.admins:
        return True

    user = pyryver.get_obj_by_field(
        org.users, pyryver.FIELD_ID, msg.get_author_id())
    if not user:
        return False

    if required_level <= ACCESS_LEVEL_ORG_ADMIN and user.is_admin():
        return True

    is_forum_admin = False
    if isinstance(chat, pyryver.GroupChat):
        member = chat.get_member(msg.get_author_id())
        if member:
            is_forum_admin = member.is_admin()

    if required_level <= ACCESS_LEVEL_FORUM_ADMIN and is_forum_admin:
        return True

    return False


def get_msgs_before(chat: pyryver.Chat, msg_id: str, count: int) -> typing.List[pyryver.Message]:
    """
    Get any number of messages before a message from an ID.

    This is similar to using pyryver.Chat.get_message(), except it doesn't have the 25 message restriction.

    Note that the oldest message is first!
    """
    msgs = []
    # Get around the 25 message restriction
    # Cut off the last one (that one is the message with the id specified)
    msgs = chat.get_message_from_id(msg_id, before=min(25, count))[:-1]
    count -= len(msgs)
    while count > 0:
        prev_msgs = chat.get_message_from_id(
            msgs[0].get_id(), before=min(25, count))[:-1]
        msgs = prev_msgs + msgs
        count -= len(prev_msgs)
    return msgs


def parse_chat_name(name: str) -> pyryver.Chat:
    """
    Parse a chat name expression in the form [(name|nickname)=]<forum|team> and return the correct chat.
    """
    field = pyryver.FIELD_NAME
    # Handle the name= or nickname= syntax
    if name.startswith("name="):
        field = pyryver.FIELD_NAME
        # Slice off the beginning
        name = name[len("name="):]
    elif name.startswith("nickname="):
        field = pyryver.FIELD_NICKNAME
        name = name[len("nickname="):]
    # Handle names starting with a + (nickname reference)
    elif name.startswith("+"):
        field = pyryver.FIELD_NICKNAME
        name = name[1:]
    return pyryver.get_obj_by_field(org.forums + org.teams, field, name)


def sanitize(msg: str) -> str:
    """
    Sanitize the given input text.

    Currently, this method makes all mentions ineffective by putting a space between the @ and the username.
    """
    return MENTION_REGEX.sub(r"\1@ \2", msg)


def get_access_denied_message() -> str:
    """
    Get an "access denied" message randomly chosen from ACCESS_DENIED_MESSAGES.
    """
    return ACCESS_DENIED_MESSAGES[randrange(len(ACCESS_DENIED_MESSAGES))]


def caldays_diff(a: datetime, b: datetime) -> int:
    """
    Calculate the difference in calendar days between a and b (a - b).

    Note this is different from just the regular difference, as the passing of a calendar day can be less than 24h.
    """
    a = a.replace(hour=0, minute=0, second=0, microsecond=0)
    b = b.replace(hour=0, minute=0, second=0, microsecond=0)
    return (a - b).days


T = typing.TypeVar("T")


def split_list(l: typing.List[T], v: T) -> typing.List[typing.List[T]]:
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


tz_utc = tz.gettz("UTC")

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


def strip_html(text: str) -> str:
    """
    Strip HTML tags from input.
    """
    # Replace <br> tags with newlines
    return BeautifulSoup(text.replace("<br>", "\n"), features="html.parser").get_text()
