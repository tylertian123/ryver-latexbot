import org
import pyryver
import re
import typing
from datetime import datetime
from random import randrange


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


def is_authorized(chat: pyryver.Chat, msg: pyryver.ChatMessage, required_level: int, admins: typing.Set[int]) -> bool:
    """
    Check if the sender of a message has a particular access level or higher.
    """
    if required_level <= ACCESS_LEVEL_EVERYONE:
        return True

    if required_level <= ACCESS_LEVEL_TYLER and msg.get_author_id() == 1311906:
        return True

    if required_level <= ACCESS_LEVEL_BOT_ADMIN and msg.get_author_id() in admins:
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


def parse_roles(about: str) -> typing.List[str]:
    """
    Parse a user's About string for roles.

    Each row must be specified on its own line with the format <Role: ROLE>,
    where ROLE can be any combination of characters excluding spaces.
    """
    if not about:
        return []
    roles = []
    for line in about.split("\n"):
        if line.startswith("<Role: ") and line.endswith(">"):
            role = line[line.index(":") + 2:-1]
            # roles cannot have spaces
            if " " in role:
                continue
            roles.append(role)
    return roles


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
    a.replace(hour=0, minute=0, second=0, microsecond=0)
    b.replace(hour=0, minute=0, second=0, microsecond=0)
    return (a - b).days
