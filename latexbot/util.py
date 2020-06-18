import aiohttp
import config
import datetime
import json
import pyryver
import re
import typing
from textwrap import dedent


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


def log(*args, **kwargs):
    """
    Log a message.

    This function uses print() and flushes immediately.
    A timestamp is also added to each message.
    """
    print(current_time().strftime("%Y-%m-%d %H:%M:%S"), end=" ")
    print(*args, **kwargs, flush=True)


def preprocess_command(prefixes: typing.List[str], aliases: typing.List[typing.Dict[str, str]], 
                       command: str, is_dm: bool):
    """
    Preprocess a command.

    Separate the command into the command name and args and resolve aliases 
    if it is a command. Otherwise return None.

    If it encouters a recursive alias, it raises ValueError.
    """
    is_command = False
    for prefix in prefixes:
        # Check for a valid command prefix
        if command.startswith(prefix) and len(command) > len(prefix):
            is_command = True
            # Remove the prefix
            command = command[len(prefix):]
    
    # DMs don't require command prefixes
    if not is_command and not is_dm:
        return None
    
    # Repeat until all aliases are expanded
    used_aliases = set()
    while True:
        # Separate command from args
        # Find the first whitespace
        command = command.strip()
        space = None
        # Keep track of this for alias expansion
        space_char = ""
        for i, c in enumerate(command):
            if c.isspace():
                space = i
                space_char = c
                break
        
        if space:
            cmd = command[:space]
            args = command[space + 1:]
        else:
            cmd = command
            args = ""

        # Expand aliases
        command = None
        for alias in aliases:
            if alias["from"] == cmd:
                # Check for recursion
                if alias["from"] in used_aliases:
                    raise ValueError(f"Recursive alias: '{alias['from']}'!")
                used_aliases.add(alias["from"])
                # Expand the alias
                command = alias["to"] + space_char + args
                break
        # No aliases were expanded - return
        if not command:
            return (cmd.strip(), args.strip())
        # Otherwise go again until no more expansion happens


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


def caldays_diff(a: datetime.datetime, b: datetime.datetime) -> int:
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


def current_time() -> datetime:
    """
    Get the current time in a timezone specified by string.
    """
    return datetime.datetime.now(datetime.timezone.utc).astimezone(config.timezone)


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


async def send_json_data(chat: pyryver.Chat, data: typing.Any, message: str, filename: str, from_user: pyryver.User, msg_creator: pyryver.Creator):
    """
    Send a JSON to the chat. 

    If the JSON is less than 1000 characters, it will be sent as text.
    Otherwise it will be attached as a file.
    """
    json_data = json.dumps(data, indent=2)
    if len(json_data) < 1000:
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
            raise ValueError(f"Error while trying to GET file attachment: {e}")
        except UnicodeDecodeError as e:
            raise ValueError(f"File needs to be encoded with utf-8! The following decode error occurred: {e}")
    else:
        data = msg_contents
    
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON: {e}")
